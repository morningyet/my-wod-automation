# -*- coding: utf-8 -*-
"""
WoD 定时自动化脚本
定时筛选耗材并批量移动到团队仓库
"""

# 导入 asyncio 库，用于异步编程
import asyncio
# 导入 schedule 库，用于定时任务
import schedule
# 导入 time 库，用于时间相关操作
import time
# 导入 logging 库，用于日志记录
import logging
# 导入 os 库，用于操作系统相关操作
import os
import re
import json
import datetime
import traceback
# 从 playwright.async_api 导入 async_playwright，用于浏览器自动化
from playwright.async_api import async_playwright
# 从 dotenv 导入 load_dotenv，用于加载 .env 文件
from dotenv import load_dotenv

# 加载 .env 文件，获取环境变量
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# 配置常量：调试端口号
DEBUG_PORT = 9222
# 配置常量：WoD 物品页面 URL
WOD_ITEM_URL = "https://delta.world-of-dungeons.org/wod/spiel/hero/items.php"
# 配置常量：WoD 登录页面 URL
WOD_LOGIN_URL = "https://delta.world-of-dungeons.org/wod/spiel/login.php"

# 从环境变量读取用户名，默认为空字符串
WOD_USERNAME = os.getenv('WOD_USERNAME', '')
# 从环境变量读取密码，默认为空字符串
WOD_PASSWORD = os.getenv('WOD_PASSWORD', '')

# ===== 卖出记录配置 =====
# 页面 localStorage 键（跨导航保留的采集缓冲）
SELL_STORAGE_KEY = "wod_sold_items"
# 输出的 JS 数据文件（类似 userItem 的 reserveItems/reItems）
SELL_JS_FILE = os.path.join(os.path.dirname(__file__), "js", "sellable-items.js")
# 收菜油猴脚本（清单同步目标：有增量时自动更新其 SELLABLE_ITEMS）
HARVEST_JS_FILE = os.path.join(os.path.dirname(__file__), "js", "wod-harvest", "wod-harvest.user.js")
# JS 数据文件表头
SELL_JS_HEADER = (
    "// 已确认可卖的物品清单（搜集阶段：自动采集 + 手动增删）\n"
    "// 类似 userItem 的 reserveItems/reItems；后续用于指导自动出售\n"
    "// 正则条目直接写字符串即可（参考 reItems 写法）\n"
    "const sellableItems = [\n"
)
# 注入到页面的卖出记录器（MutationObserver 主力 + Ajax 拦截兜底）：
# ① MutationObserver：DOM 变化时检测 sellconfirm 按钮 → 安装 OK 点击处理器（主力，覆盖原生 POST）
# ② hook XHR.send：拦截 AJAX 响应 → 检测确认页 → 解析物品名暂存 pending（兜底，覆盖 AJAX 场景）
# ③ OK 点击：从 DOM 解析物品名，兜底用 pending → 合并进最终清单（wod_sold_items）
INJECT_RECORDER_JS = r"""
(() => {
  const FINAL = 'wod_sold_items';
  const PENDING = 'wod_sold_pending';

  // ===== ① Ajax 拦截（兜底） =====
  if (!window.__wodXhrHooked) {
    window.__wodXhrHooked = true;
    const _send = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.send = function() {
      this.addEventListener('load', function() {
        try {
          const txt = this.responseText || '';
          if (!txt.includes('以下物品现在将以NPC价出售')) return;
          const doc = new DOMParser().parseFromString(txt, 'text/html');
          const names = [];
          doc.querySelectorAll('a[href*="item.php"]').forEach(a => {
            if (!a.href.includes('item_instance_id')) return;
            const n = (a.textContent || '').replace(/!/g, '').trim();
            if (n) names.push(n);
          });
          if (names.length) localStorage.setItem(PENDING, JSON.stringify(names));
          setTimeout(installOK, 300);
        } catch(_){}
      });
      return _send.apply(this, arguments);
    };
  }

  // ===== ② OK 点击处理器 =====
  function okHandler(e) {
    const ok = e.target && e.target.closest && e.target.closest('input[name="sellconfirm"]');
    if (!ok) return;
    window.__wodOkAttached = false;
    let names = [];
    document.querySelectorAll('a[href*="item.php"]').forEach(a => {
      if (!a.href.includes('item_instance_id')) return;
      const n = (a.textContent || '').replace(/!/g, '').trim();
      if (n) names.push(n);
    });
    if (!names.length) {
      try { names = JSON.parse(localStorage.getItem(PENDING) || '[]'); } catch(_){}
    }
    if (!names.length) return;
    let set = [];
    try { set = JSON.parse(localStorage.getItem(FINAL) || '[]'); } catch(_){}
    const merged = new Set(set);
    names.forEach(n => merged.add(n));
    localStorage.setItem(FINAL, JSON.stringify(Array.from(merged).sort((a,b)=>a.localeCompare(b,'zh'))));
    // 记录本次卖出件数（含重复），供 Python 读取
    localStorage.setItem('__wod_sell_count', String(names.length));
  }

  function installOK() {
    if (window.__wodOkAttached) return;
    if (!document.querySelector('input[name="sellconfirm"]')) return;
    window.__wodOkAttached = true;
    document.removeEventListener('click', okHandler, true);
    document.addEventListener('click', okHandler, true);
  }

  // ===== ③ MutationObserver（主力，覆盖原生 POST 全页跳转） =====
  if (window.__wodSellObs) { try { window.__wodSellObs.disconnect(); } catch(_){} }
  function check() {
    if (document.querySelector('input[name="sellconfirm"]')) installOK();
  }
  check();
  const obs = new MutationObserver(check);
  obs.observe(document.body, { childList: true, subtree: true, characterData: true });
  window.__wodSellObs = obs;

  return 'ok';
})();
"""

# 配置日志的基本设置
logging.basicConfig(
    level=logging.INFO,  # 日志级别为 INFO
    format='%(asctime)s - %(levelname)s - %(message)s'  # 日志格式
)
# 创建日志记录器
logger = logging.getLogger(__name__)


# 定义 WoDAutomation 类，处理 WoD 游戏的自动化操作
class WoDAutomation:
    # 初始化方法，创建对象时调用
    def __init__(self, log_callback=None, auto_login=True):
        self.browser = None
        self.page = None
        self.playwright = None
        self.first_hero = None
        self.processed_count = 0
        self.log_callback = log_callback
        self.auto_login = auto_login
        self.sold_items_callback = None   # GUI 回调（传新增名字列表）
        self._sell_monitor_stop = None    # asyncio.Event
        self._sell_monitor_task = None    # 监控任务
        self._sell_last_seen = None       # 已见过清单（避免跨会话/跨清空重复记录）

    # 日志方法，向 GUI 和标准日志输出信息
    def log(self, level, message):
        """日志输出，支持回调"""
        # 如果有日志回调函数，调用它
        if self.log_callback:
            # 调用回调函数，传递日志级别和消息
            self.log_callback(level, message)
        # 同时输出到标准日志系统
        # 如果是 INFO 级别，使用 logger.info
        if level == "INFO":
            logger.info(message)
        # 如果是 WARNING 级别，使用 logger.warning
        elif level == "WARNING":
            logger.warning(message)
        # 如果是 ERROR 级别，使用 logger.error
        elif level == "ERROR":
            logger.error(message)

    async def close(self):
        """释放浏览器连接和 Playwright 资源"""
        if self.browser:
            try:
                self.browser = None
            except:
                pass
        if self.playwright:
            try:
                await self.playwright.stop()
            except:
                pass
            self.playwright = None
        self.page = None

    # ===== 卖出记录 =====
    def _read_existing_names(self):
        """读取 JS 数据文件里已有的物品名（含手动增删的条目/正则）"""
        try:
            with open(SELL_JS_FILE, "r", encoding="utf-8") as f:
                text = f.read()
        except FileNotFoundError:
            return []
        return re.findall(r'"([^"]*)"', text)

    def _write_sell_js_names(self, names):
        """按给定名字列表重写 JS 数据文件（不做合并）"""
        body = "".join(f'  "{n}",\n' for n in names)
        with open(SELL_JS_FILE, "w", encoding="utf-8") as f:
            f.write(SELL_JS_HEADER + body + "];\n")

    def _write_sell_js(self, names):
        """合并已有条目（含手动增删）与本次采集，去重排序后重写 JS 数据文件"""
        merged = sorted(set(self._read_existing_names()) | set(names))
        self._write_sell_js_names(merged)

    def _clear_sell_js(self):
        """清空浏览器采集缓冲（不动清单文件，sellableItems 由用户维护）"""
        self._sell_last_seen = set()

    def _sync_harvest_script(self, total):
        """把清单同步进 wod-harvest.user.js 的 SELLABLE_ITEMS 常量

        仅在有增量（total 与脚本内条数不一致）时重写；同步后更新
        脚本头部注释里的条数与日期。
        """
        try:
            with open(HARVEST_JS_FILE, "r", encoding="utf-8") as f:
                src = f.read()
        except FileNotFoundError:
            self.log("WARNING", f"未找到收菜脚本，跳过同步: {HARVEST_JS_FILE}")
            return

        m = re.search(r"const SELLABLE_ITEMS = \[([\s\S]*?)\];", src)
        if not m:
            self.log("WARNING", "收菜脚本内未找到 SELLABLE_ITEMS，跳过同步")
            return

        old_count = len(re.findall(r'"([^"]*)"', m.group(1)))
        if old_count == total:
            return  # 无增量

        body = "".join(f'  "{n}",\n' for n in self._read_existing_names())
        new_block = f"const SELLABLE_ITEMS = [\n{body}    ];"
        src = src[:m.start()] + new_block + src[m.end():]

        # 更新头部注释的条数与日期（兼容首次注入与既往同步两种格式）
        src = re.sub(
            r"// 可卖物品清单（拷贝自 js/sellable-items\.js，\d+ 条 @(?:同步于)?[\d-]+）",
            f"// 可卖物品清单（拷贝自 js/sellable-items.js，{total} 条 @同步于{datetime.date.today()}）",
            src,
        )
        # 自动 bump 补丁版本号（0.4.0 -> 0.4.1），触发油猴更新
        src = re.sub(
            r"// @version      (\d+)\.(\d+)\.(\d+)",
            lambda m: f"// @version      {m.group(1)}.{m.group(2)}.{int(m.group(3)) + 1}",
            src,
        )
        try:
            with open(HARVEST_JS_FILE, "w", encoding="utf-8") as f:
                f.write(src)
            self.log("INFO", f"已同步可卖清单到收菜脚本（{old_count} -> {total} 条），版本号已更新")
        except Exception as e:
            self.log("ERROR", f"同步收菜脚本失败: {e}")

    async def flush_sold_buffer(self):
        """刷新可卖清单：把浏览器缓冲的卖出记录合并进 sellable-items.js，
        然后清空浏览器缓冲。返回 (新增条数, 清单总条数)。
        有增量时自动同步到 wod-harvest.user.js。
        """
        new_names = []
        if self.page:
            try:
                raw = await self.page.evaluate(
                    f"localStorage.getItem('{SELL_STORAGE_KEY}')"
                )
                cur = json.loads(raw) if raw else []
                existing = set(self._read_existing_names())
                new_names = [n for n in cur if n not in existing]
            except Exception as e:
                self.log("ERROR", f"读取浏览器卖出缓冲失败: {e}")
        # 合并去重排序后重写清单文件
        merged = sorted(set(self._read_existing_names()) | set(new_names))
        self._write_sell_js_names(merged)
        # 清空浏览器缓冲
        if self.page:
            try:
                await self.page.evaluate(
                    f"localStorage.removeItem('{SELL_STORAGE_KEY}')"
                )
                await self.page.evaluate("localStorage.removeItem('__wod_sell_count')")
            except Exception:
                pass
        # 有增量时同步到收菜脚本
        if new_names:
            self._sync_harvest_script(len(merged))
        return len(new_names), len(merged)

    async def _inject_and_read(self):
        """注入记录器 + 读取已记录物品"""
        try:
            await self.page.evaluate(INJECT_RECORDER_JS)
        except Exception:
            return  # 页面跳转中，跳过本轮，下一轮重试
        try:
            raw = await self.page.evaluate(f"localStorage.getItem('{SELL_STORAGE_KEY}')")
            cur = json.loads(raw) if raw else []
            if not cur:
                return
            # 以清单文件为准判断新增：文件里已有的不重复记录（尊重手动删改）
            existing = set(self._read_existing_names())
            new = [n for n in cur if n not in existing]
            if new:
                for n in new:
                    self.log("INFO", f"记录卖出物品：{n}")
                # 读本次卖出总件数（含已收录的）
                try:
                    cnt_raw = await self.page.evaluate("localStorage.getItem('__wod_sell_count')")
                    sell_cnt = int(cnt_raw) if cnt_raw else len(new)
                except Exception:
                    sell_cnt = len(new)
                self.log("INFO", f"本次卖出 {sell_cnt} 件；新增 {len(new)} 件")
                if self.sold_items_callback:
                    self.sold_items_callback(new)
                # 只把「新增」追加进清单文件
                self._write_sell_js(new)
            self._sell_last_seen = set(cur)
        except asyncio.CancelledError:
            raise
        except Exception:
            pass  # 页面跳转中，跳过本轮

    async def monitor_sold_items(self):
        """轮询监听：每1秒注入记录器+读取结果（记录器端 MutationObserver 自动判断是否在确认页）"""
        if self._sell_last_seen is None:
            self._sell_last_seen = set(self._read_existing_names())
        self.log("INFO", f"开始监听卖出记录...（已收录 {len(self._sell_last_seen)} 个物品）")
        done = self._sell_monitor_stop
        while not done.is_set():
            try:
                if not self.page:
                    await asyncio.sleep(1)
                    continue
                await self._inject_and_read()
            except asyncio.CancelledError:
                raise
            except Exception:
                pass
            await asyncio.sleep(1)
        self.log("INFO", "已停止监听卖出记录")

    async def start_sell_monitor(self):
        """启动卖出记录监控任务"""
        if self._sell_monitor_task and not self._sell_monitor_task.done():
            return
        # 启动时清掉浏览器采集缓冲：以清单文件为基准，只采集本次会话的新卖出
        if self.page:
            try:
                await self.page.evaluate(f"localStorage.removeItem('{SELL_STORAGE_KEY}')")
            except Exception:
                pass
        self._sell_last_seen = set()
        self._sell_monitor_stop = asyncio.Event()
        self._sell_monitor_task = asyncio.create_task(self.monitor_sold_items())

    async def stop_sell_monitor(self):
        """停止卖出记录监控任务"""
        if self._sell_monitor_stop:
            self._sell_monitor_stop.set()
        if self._sell_monitor_task:
            try:
                await self._sell_monitor_task
            except (asyncio.CancelledError, Exception):
                pass
        self._sell_monitor_task = None
        self._sell_monitor_stop = None

    # ===== 自动出售（按 sellable-items.js 清单） =====
    def _read_sellable_patterns(self):
        """读取 sellable-items.js 里的可卖物品条目

        条目即物品名（精确匹配）；若以 .* 开头等正则写法则按正则匹配。
        """
        patterns = []
        try:
            with open(SELL_JS_FILE, "r", encoding="utf-8") as f:
                text = f.read()
        except FileNotFoundError:
            self.log("WARNING", f"未找到可卖物品清单: {SELL_JS_FILE}")
            return patterns
        for name in re.findall(r'"([^"]*)"', text):
            if not name:
                continue
            try:
                patterns.append((name, re.compile(name)))
            except re.error:
                # 不是合法正则就当普通名字（re.escape 后精确匹配）
                patterns.append((name, re.compile(re.escape(name))))
        return patterns

    async def _check_sellable_page(self, patterns):
        """在当前物品页圈选匹配清单的物品，返回勾选明细列表

        匹配所有出售区（仓库 Store / 装备 Equipped / 口袋 Tasche / 徽章 Orden）
        中的物品行；同名多件全部勾选。只勾选不替换已有勾选（保留用户手动勾选）。
        """
        return await self.page.evaluate(
            r"""(patterns) => {
              const pats = patterns.map(p => new RegExp(p));
              const match = (t) => pats.some(p => p.test(t));
              const picked = [];
              document.querySelectorAll('input[type=checkbox][name^="SellItems"]').forEach(cb => {
                if (cb.name.includes('setter') || cb.checked || cb.disabled) return;
                const row = cb.closest('tr');
                if (!row) return;
                const a = row.querySelector('a[href*="item_instance_id"]');
                if (!a) return;
                const t = (a.textContent || '').replace(/!/g, '').trim();
                if (t && match(t)) { cb.checked = true; picked.push(t); }
              });
              return picked;
            }""",
            [pat.pattern for _, pat in patterns],
        )

    async def sell_sellable_items(self, max_rounds=40):
        """自动出售：按清单圈选当前英雄所有匹配物品并确认卖出

        流程：确保出售选项展开(marketview) → 圈选 → 应用改动 → 确认页点 OK
        → 剩余物品补位，循环直到没有匹配物品。
        只操作当前英雄的物品页；由 GUI 按钮触发（单英雄），收菜流程不调用。
        """
        patterns = self._read_sellable_patterns()
        if not patterns:
            self.log("WARNING", "可卖物品清单为空，跳过自动出售")
            return 0

        await self.wait_for_page(extra_wait=1)
        await self.ensure_page_valid()

        hero_name = await self.get_hero_name()
        self.log("INFO", f"【自动出售】开始处理 {hero_name}（清单 {len(patterns)} 条）...")

        total_sold = 0
        stall = 0
        for round_no in range(1, max_rounds + 1):
            # 出售确认页的 OK 提交后回到物品页；确保在物品页
            if "items.php" not in self.page.url:
                await self.navigate_to_items()

            # 每次浏览器操作之间等待 3 秒，避免操作过快
            await asyncio.sleep(3)

            # 圈选本轮匹配物品（不清除已有勾选）
            picked = await self._check_sellable_page(patterns)
            if not picked:
                if round_no == 1:
                    self.log("INFO", f"【自动出售】{hero_name} 没有匹配清单的物品")
                break

            self.log("INFO", f"【自动出售】第{round_no}轮圈选 {len(picked)} 件: "
                             f"{', '.join(sorted(set(picked))[:8])}{'...' if len(set(picked)) > 8 else ''}")

            # 提交：应用改动 → 出现"以下物品现在将以NPC价出售"确认页
            await self.page.locator('input[value="应用改动"]').first.click(timeout=600000)
            try:
                await self.page.wait_for_selector('input[name="sellconfirm"]', timeout=30000)
            except Exception:
                # 没弹确认页（可能物品实际不可卖被服务器拒绝），返回物品页重试
                self.log("WARNING", "【自动出售】未出现出售确认页，回到物品页继续")
                await self.navigate_to_items()
                stall += 1
                if stall >= 2:
                    self.log("WARNING", "【自动出售】连续无确认页，停止")
                    break
                continue

            # 确认页点 OK（这一步真正卖出）：先等页面加载完再等 3 秒
            await self.wait_for_page(extra_wait=3)
            await self.page.locator('input[name="sellconfirm"]').first.click(timeout=600000)
            await self.wait_for_page(extra_wait=3)
            total_sold += len(picked)
            stall = 0
            self.log("INFO", f"【自动出售】第{round_no}轮已确认卖出 {len(picked)} 件（累计 {total_sold}）")

        if total_sold:
            self.log("INFO", f"【自动出售】{hero_name} 完成，共卖出 {total_sold} 件")
        else:
            self.log("INFO", f"【自动出售】{hero_name} 完成，无需卖出")
        return total_sold

    async def sell_all_heroes(self):
        """轮询所有英雄自动出售：参考 process_all_heroes 的循环结构

        记住起始英雄 → 当前英雄出售 → 切换下一个 → 直到回到起始英雄。
        每个英雄出售后物品页停留原处，切换英雄自带跳转，无需额外导航。
        """
        self.log("INFO", "【自动出售】开始轮询所有英雄...")

        # 获取第一个英雄的名字
        self.first_hero = await self.get_hero_name()
        # 记录起始英雄的日志
        self.log("INFO", f"起始英雄: {self.first_hero}")

        # 创建集合记录已处理的英雄（只用英雄名字）
        processed_heroes = set()
        # 总卖出件数
        grand_total = 0

        # 无限循环
        while True:
            # 获取当前英雄名称
            current_hero = await self.get_hero_name()

            # 检查是否已处理过（英雄名字重复）
            if current_hero in processed_heroes:
                # 记录回到已处理英雄的日志
                self.log("INFO", f"回到已处理英雄: {current_hero}")
                # 记录循环结束的日志，包含英雄名字列表
                hero_list = list(processed_heroes)
                self.log("INFO", f"循环结束，共处理 {len(processed_heroes)} 个英雄: {', '.join(hero_list)}")
                # 跳出循环
                break

            # 处理当前英雄
            try:
                # 出售当前英雄的可卖物品
                sold = await self.sell_sellable_items()
                grand_total += sold
                # 将英雄添加到已处理集合
                processed_heroes.add(current_hero)
            # 如果出现异常
            except Exception as e:
                # 记录错误日志
                self.log("ERROR", f"出售英雄 {current_hero} 时出错: {e}")
                traceback.print_exc()
                # 出错后仍然尝试切换到下一个英雄
                try:
                    # 切换到下一个英雄
                    await self.switch_to_next_hero()
                # 如果切换失败
                except:
                    # 忽略异常
                    pass

            # 出错分支里已切换；正常分支需要主动切换到下一个英雄
            if current_hero not in processed_heroes:
                continue

            # 判断切换后是否回到起点（回到起点即循环结束，不用再切）
            await self.switch_to_next_hero()
            await self.page.wait_for_timeout(1000)

        self.log("INFO", f"【自动出售】全部英雄完成，共卖出 {grand_total} 件")
        return grand_total

    async def wait_for_page(self, extra_wait=2, timeout=30000):
        """等待页面加载完成（网络空闲 + DOM加载 + 额外等待）"""
        # 先等待网络空闲
        try:
            await self.page.wait_for_load_state("networkidle", timeout=timeout)
        except:
            pass
        # 再等待 DOM 内容加载完成
        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=timeout)
        except:
            pass
        # 额外等待指定秒数，确保页面稳定
        await asyncio.sleep(extra_wait)
        # 确保页面有效
        await self.ensure_page_valid()

    async def ensure_page_valid(self, retry_times=3):
        """确保页面有效，如果检测到错误页面则刷新

        检测以下错误情况：
        - 页面标题包含"无法访问此页面"
        - URL 以 chrome-error:// 或 edge-error:// 开头
        - 页面内容包含"已重置连接"
        """
        for i in range(retry_times):
            # 检查是否为错误页面
            is_error = await self.page.evaluate("""() => {
                const title = document.title;
                const url = window.location.href;
                const bodyText = document.body.textContent;

                // 检查标题
                if (title.includes("无法访问此页面")) return true;
                // 检查 URL
                if (url.startsWith("chrome-error://")) return true;
                if (url.startsWith("edge-error://")) return true;
                // 检查页面内容
                if (bodyText.includes("已重置连接")) return true;
                return false;
            }""")

            if not is_error:
                # 页面正常，直接返回
                return True

            # 检测到错误页面，记录日志并刷新
            self.log("WARNING", f"检测到错误页面，尝试刷新 ({i+1}/{retry_times})...")
            self.log("WARNING", f"  当前 URL: {self.page.url}")
            self.log("WARNING", f"  当前标题: {await self.page.title()}")

            await self.page.reload(wait_until="domcontentloaded", timeout=60000)
            await self.wait_for_page(extra_wait=2)

        # 重试次数用尽，抛出异常
        raise Exception("页面持续加载失败，请检查网络连接")

    async def navigate_to_items(self):
        """导航到物品页面并等待加载完成"""
        # 记录导航日志
        self.log("INFO", f"正在导航到物品页面: {WOD_ITEM_URL}")
        # 导航到物品页面
        await self.page.goto(WOD_ITEM_URL, wait_until="domcontentloaded", timeout=300000)
        # 等待页面加载完成，额外等待 2 秒
        await self.wait_for_page(extra_wait=2)
        # 记录导航完成日志
        self.log("INFO", f"导航完成，当前 URL: {self.page.url}")

    async def _has_login_form(self):
        """统一检测页面是否有登录表单，返回表单信息字典"""
        # 检查是否存在用户名输入框（使用 ID 精确定位，避免匹配到 hidden 字段）
        has_username = await self.page.locator('input#USERNAME[type="text"]').count() > 0
        # 检查是否存在密码输入框（使用 ID 精确定位，避免匹配到 hidden 字段）
        has_password = await self.page.locator('input#PASSWORT[type="password"]').count() > 0
        # 检查是否存在登录按钮（WoD 登录按钮特征）
        has_login_button = await self.page.locator('input[name="LOGIN_BUTTON"][value="登陆"]').count() > 0

        # 构建返回结果字典
        # 两个规则满足一个即可：
        # 规则1：有用户名+密码输入框
        # 规则2：有登录按钮
        result = {
            "has_form": (has_username and has_password) or has_login_button,
            # 用户名输入框定位器（用于后续填入）
            "username_input": self.page.locator('input#USERNAME[type="text"]').first if has_username else None,
            # 密码输入框定位器（用于后续填入）
            "password_input": self.page.locator('input#PASSWORT[type="password"]').first if has_password else None,
            # 用户名输入框当前值（自动填充检测）
            "username_value": "",
            # 密码输入框当前值（自动填充检测）
            "password_value": "",
        }

        # 如果存在用户名输入框，尝试获取其当前值
        if has_username:
            try:
                result["username_value"] = await result["username_input"].input_value()
            except:
                # 获取失败则忽略
                pass
        # 如果存在密码输入框，尝试获取其当前值
        if has_password:
            try:
                result["password_value"] = await result["password_input"].input_value()
            except:
                # 获取失败则忽略
                pass

        # 返回表单信息字典
        return result

    # 异步方法：检查是否已登录
    async def is_logged_in(self):
        """检查是否已登录"""
        # 确保页面有效
        await self.ensure_page_valid()
        # 等待页面加载完成，额外等待 3 秒
        await self.wait_for_page(extra_wait=3)

        # 获取当前页面的 URL
        url = self.page.url

        # 检查 URL 中是否包含 WoD 域名
        if "world-of-dungeons" not in url:
            # 不在 WoD 页面，记录日志并返回 False
            self.log("INFO", f"不在 WoD 页面: {url}")
            return False

        # 检查 URL 中是否包含 login.php（登录页面）
        if "login.php" in url:
            # 在登录页面，记录日志并返回 False
            self.log("INFO", "在登录页面")
            return False

        # 检查是否被重定向到首页（通常是未登录的标志）
        # 首页 URL 格式类似: https://delta.world-of-dungeons.org/
        # 去除 URL 末尾的斜杠
        parsed_url = url.rstrip("/")
        # 提取基础 URL（协议 + 域名）
        base_url = f"https://{parsed_url.split('/')[2]}"
        # 判断是否被重定向到首页
        if parsed_url == base_url or parsed_url == base_url + "/wod" or parsed_url == base_url + "/wod/":
            # 被重定向到首页，判定为未登录
            self.log("INFO", "被重定向到首页，判定为未登录")
            return False

        # 检查页面是否有登录表单
        try:
            # 调用统一方法检测登录表单
            form_info = await self._has_login_form()
            # 如果存在登录表单，说明未登录
            if form_info["has_form"]:
                # 记录检测到登录表单
                self.log("INFO", "检测到登录表单")
                # 检查是否有自动填充的内容
                if form_info["username_value"] or form_info["password_value"]:
                    # 记录用户名框是否有内容
                    self.log("INFO", f"  用户名框有内容: {'是' if form_info['username_value'] else '否'}")
                    # 记录密码框是否有内容
                    self.log("INFO", f"  密码框有内容: {'是' if form_info['password_value'] else '否'}")
                # 有登录表单说明未登录，返回 False
                return False
        except Exception:
            # 检测过程中出现异常，忽略继续
            pass

        # 检查是否有已登录的标志（英雄切换按钮）
        try:
            # 检查是否存在英雄切换按钮
            has_hero_switch = await self.page.locator('img[alt="切换到下一个活跃的英雄"]').count() > 0
            # 如果存在切换按钮，说明已登录
            if has_hero_switch:
                # 记录检测到已登录状态
                self.log("INFO", "检测到已登录状态（英雄切换按钮存在）")
                return True
        # 如果检查过程中出现异常
        except:
            # 忽略异常，继续后续检查
            pass

        # 检查是否有"物品"相关的游戏内容
        try:
            # 已登录的物品页面应该有筛选耗材的选项
            has_consumable_filter = await self.page.locator('input[name="item_3usage_item"][value="yes"]').count() > 0
            # 如果存在耗材筛选框，说明已登录
            if has_consumable_filter:
                # 记录检测到已登录状态
                self.log("INFO", "检测到已登录状态（物品筛选框存在）")
                return True
        # 如果检查过程中出现异常
        except:
            # 忽略异常，继续后续检查
            pass

        # 其他情况默认认为未登录
        # 记录未检测到登录状态
        self.log("INFO", f"未检测到登录状态，当前 URL: {url}")
        return False

    async def login(self):
        """登录 WoD"""
        # 打印开始登录的日志
        self.log("INFO", "开始登录...")
        # 确保页面有效
        await self.ensure_page_valid()
        # 等待页面加载完成
        await self.wait_for_page()

        # 打印检查登录表单的日志
        self.log("INFO", "检查登录表单...")
        # 调用统一方法检测登录表单
        form_info = await self._has_login_form()

        # 如果没有找到登录表单，抛出异常
        if not form_info["has_form"]:
            raise Exception("未找到登录表单")

        # 打印找到登录表单的日志
        self.log("INFO", "  找到登录表单")

        # 打印检查自动填充的日志
        self.log("INFO", "检查是否有自动填充...")
        # 从表单信息中获取用户名输入框
        username_input = form_info["username_input"]
        # 从表单信息中获取密码输入框
        password_input = form_info["password_input"]
        # 从表单信息中获取用户名自动填充值
        auto_username = form_info["username_value"]
        # 从表单信息中获取密码自动填充值
        auto_password = form_info["password_value"]

        # 判断是否有自动填充的用户名和密码
        if auto_username and auto_password:
            # 有自动填充，打印检测到自动填充的日志
            self.log("INFO", f"  检测到自动填充")
            # 打印自动填充的用户名
            self.log("INFO", f"  用户名: {auto_username}")
        else:
            # 没有自动填充，需要从 .env 文件读取
            self.log("INFO", "  无自动填充，从配置文件读取...")
            # 检查 .env 文件中是否配置了用户名和密码
            if not WOD_USERNAME or not WOD_PASSWORD:
                # 没有配置，抛出异常提示用户
                raise Exception("未配置登录信息，请在 .env 文件中设置 WOD_USERNAME 和 WOD_PASSWORD")

            # 打印从配置文件读取的用户名
            self.log("INFO", f"  用户名: {WOD_USERNAME}")
            # 将用户名填入输入框
            await username_input.fill(WOD_USERNAME)
            # 将密码填入输入框
            await password_input.fill(WOD_PASSWORD)
            # 等待 1 秒，确保填入完成
            await self.wait_for_page(extra_wait=1)

        # 选择世界
        self.log("INFO", "选择世界: 4 Delta")
        await self.page.locator('select#world').select_option("CD")
        await self.wait_for_page(extra_wait=0.5)

        # 打印点击登录按钮的日志
        self.log("INFO", "点击登录按钮...")
        # 点击登录按钮（使用精确选择器）
        await self.page.locator('input[name="LOGIN_BUTTON"][value="登陆"]').click()

        # 等待登录后的页面加载完成，额外等待 3 秒
        await self.wait_for_page(extra_wait=3)

        # 获取登录后页面的 URL
        new_url = self.page.url
        # 获取登录后页面的标题
        new_title = await self.page.title()

        # 检查是否仍在登录页面（登录失败的标志）
        if "login" in new_url.lower() or "登陆" in new_title or "登录" in new_title:
            # 打印登录失败的日志
            self.log("ERROR", "登录失败，仍在登录页面")
            # 打印当前页面标题
            self.log("ERROR", f"  当前标题: {new_title}")
            # 打印当前页面 URL
            self.log("ERROR", f"  当前 URL: {new_url}")
            # 抛出登录失败异常
            raise Exception("登录失败")

        # 打印登录成功的日志
        self.log("INFO", "✓ 登录成功!")

    # 异步方法：连接到已启动的 Edge 浏览器
    async def connect(self):
        """连接到已启动的 Edge 浏览器"""
        # 记录正在连接浏览器的日志
        self.log("INFO", "正在连接浏览器...")
        # 第一阶段：连接浏览器
        try:
            # 记录尝试连接到调试端口的日志
            logger.info(f"尝试连接到浏览器调试端口 http://localhost:{DEBUG_PORT}")
            # 启动 Playwright
            self.playwright = await async_playwright().start()
            # 通过 CDP 连接到浏览器
            self.browser = await self.playwright.chromium.connect_over_cdp(
                f"http://localhost:{DEBUG_PORT}"
            )
            # 记录连接成功的日志
            self.log("INFO", "已连接到浏览器")
        # 如果连接过程中出现异常
        except Exception as e:
            # 记录连接失败的日志
            self.log("ERROR", f"连接浏览器失败: {e}")
            # 提示用户确保浏览器已启动
            self.log("ERROR", f"  请确保浏览器已用 --remote-debugging-port={DEBUG_PORT} 启动")
            # 提示启动命令
            self.log("ERROR", f"  启动命令: <浏览器路径> --remote-debugging-port={DEBUG_PORT}")
            # 【防内存泄漏】连接失败时也要释放已启动的 playwright（它会调
            # playwright.stop() 终止 Node.js 驱动子进程），否则每次失败的连接
            # 都会留下一个僵尸 Node 进程。
            await self.close()
            # 重新抛出异常
            raise

        # 第二阶段：后续操作
        try:
            # 获取浏览器的所有上下文
            contexts = self.browser.contexts

            # 查找 WoD 页面
            # 初始化 WoD 页面变量为 None
            wod_page = None
            # 遍历每个上下文
            for context in contexts:
                # 遍历上下文中的每个页面
                for page in context.pages:
                    # 检查页面 URL 是否包含 WoD 域名
                    if "world-of-dungeons" in page.url:
                        # 找到 WoD 页面
                        wod_page = page
                        # 记录找到的页面 URL
                        self.log("INFO", f"找到 WoD 页面: {page.url}")
                        # 跳出内层循环
                        break
                # 如果已找到 WoD 页面，跳出外层循环
                if wod_page:
                    break

            # 判断是否找到了 WoD 页面
            if wod_page:
                # 使用找到的页面
                self.page = wod_page
            else:
                # 没有 WoD 页面，创建新页面
                if contexts:
                    # 在第一个上下文中创建新页面
                    self.page = await contexts[0].new_page()
                else:
                    # 无法获取浏览器上下文，抛出异常
                    raise Exception("无法获取浏览器上下文")

            # 直接导航到物品页面（利用可能的缓存）
            # 记录正在导航的日志
            await self.navigate_to_items()

            # 检查是否能访问物品页面（有缓存或已登录）
            logged_in = await self.is_logged_in()

            # 如果未登录
            if not logged_in:
                # 检查是否开启自动登录
                if self.auto_login:
                    # 记录开始自动登录的日志
                    self.log("INFO", "未登录，开始自动登录...")
                    # 执行登录
                    await self.login()
                    # 记录登录完成的日志
                    self.log("INFO", "登录完成")
                    # 登录后再次导航到物品页面
                    await self.navigate_to_items()
                    self.log("INFO", "已到达物品页面")
                else:
                    # 自动登录已关闭，记录警告
                    self.log("WARNING", "未登录，且自动登录已关闭")
                    # 提示用户手动登录或勾选自动登录
                    self.log("INFO", "请手动登录后重新连接，或勾选自动登录")
                    # 抛出未登录状态异常
                    raise Exception("未登录状态")
            else:
                # 已登录（或使用缓存）
                self.log("INFO", "已登录（或使用缓存）")

            # 记录当前 URL
            self.log("INFO", f"当前 URL: {self.page.url}")
            # 记录当前页面标题
            self.log("INFO", f"标题: {await self.page.title()}")
        # 如果操作过程中出现异常
        except Exception as e:
            # 记录操作失败的日志
            self.log("ERROR", f"操作失败: {e}")
            # 重新抛出异常
            raise

    # 异步方法：获取当前英雄名称
    async def get_hero_name(self):
        """获取当前英雄名称（去掉": 仓库"等后缀）"""
        # 定位页面中的 h1 标签并获取其文本内容（取第一个，避免多元素报错）
        full_name = await self.page.locator("h1").first.text_content()
        # 去掉": 仓库"等后缀，只保留英雄名字
        return full_name.split(":")[0]

    # 异步方法：检测是否为导师英雄
    async def is_mentor_hero(self):
        """检测是否为导师英雄"""
        # 获取当前页面的 URL
        url = self.page.url
        # 检查 URL 中是否包含 "reason=mentor"
        return "reason=mentor" in url

    async def clean_backpack(self):
        """清理超载的背包"""
        self.log("INFO", "检查背包是否超载...")

        # 检查是否有超载提示
        has_overload = await self.page.evaluate("""() => {
            return document.body.textContent.includes("不得不抛弃");
        }""")

        if not has_overload:
            self.log("INFO", "背包未超载，无需清理")
            return

        self.log("INFO", "检测到背包超载，开始清理...")

        # 第3步：观察背包页面信息
        info = await self.page.evaluate("""() => {
            const row = document.querySelector("td.paginator_row");
            if (!row) return {error: "无paginator_row"};

            const pageBtns = row.querySelectorAll("input[name^='ITEMS_GEFUNDEN_PAGE'], input[name='dummy']");
            const totalPages = pageBtns.length;

            const currentBtn = row.querySelector(".paginator_selected");
            const currentPage = currentBtn?.getAttribute("value")?.match(/=(\\d+)=/)?.[1] || "unknown";

            const perPageInput = row.querySelector("input[name='ITEMS_GEFUNDEN_PSNR[1]']");
            const perPage = perPageInput?.value || "unknown";

            const sortBtn = document.querySelector("input[value*='价格']");
            const sortValue = sortBtn?.value || "unknown";
            const sortOrder = sortValue.includes("↑") ? "降序" : "升序";

            return {
                totalPages: totalPages,
                currentPage: currentPage,
                perPage: perPage,
                sortOrder: sortOrder
            };
        }""")

        self.log("INFO", f"页面信息: 总页数={info['totalPages']}, 当前页=第{info['currentPage']}页, "
                        f"每页条数={info['perPage']}, 排序={info['sortOrder']}")

        # 第5步：切换到第二页（价格降序时，低价物品在第2页）
        if info['currentPage'] != '2':
            self.log("INFO", "切换到第2页")
            await self.page.click('input[name="ITEMS_GEFUNDEN_PAGE[2]"]')
            await self.wait_for_page(extra_wait=1)

        # 第6步：确认第二页页面信息
        current = await self.page.evaluate("""() => {
            const currentBtn = document.querySelector(".paginator_selected");
            return currentBtn?.getAttribute("value")?.match(/=(\\d+)=/)?.[1] || "unknown";
        }""")

        if current != '2':
            self.log("WARNING", f"当前页不是第2页，而是第{current}页")
            return

        # 第7步和第8步：重复两次（点击丢弃全选 + 应用改动）
        for i in range(2):
            # 检查是否还在背包页面（有"不把沉重的背包清理一番"字样）
            is_backpack_page = await self.page.evaluate("""() => {
                return document.body.textContent.includes("不把沉重的背包清理一番");
            }""")

            if not is_backpack_page:
                self.log("INFO", "已进入仓库页面，无需继续清理")
                return

            self.log("INFO", f"第{i+1}次：点击丢弃全选按钮")
            await self.page.click('input[name="SellItemsFound_setter[1]"]')
            await self.wait_for_page(extra_wait=1)

            self.log("INFO", f"第{i+1}次：点击应用改动")
            await self.page.click('input[value="应用改动"]')
            await self.wait_for_page(extra_wait=2)

        # 第9步：回到第一页，读取页面信息
        self.log("INFO", "两次清理完成，回到第一页查看是否仍需丢弃物品")
        await self.page.click('input[name="ITEMS_GEFUNDEN_PAGE[1]"]')
        await self.wait_for_page(extra_wait=1)

        # 获取需要丢弃的数量
        # 注意：只用"不得不抛弃N件物品"这一段来提取，避免依赖前半句文案，
        # 也避免 document.body.textContent 含换行使正则的 .* 跨不过去而失配。
        need_drop = await self.page.evaluate("""() => {
            const body = document.body.textContent;
            const match = body.match(/不得不抛弃(\\d+)件物品/);
            if (match) {
                return parseInt(match[1]);
            }
            return 0;
        }""")

        if need_drop == 0:
            self.log("INFO", "不需要再丢弃物品")
            return

        self.log("INFO", f"需要丢弃{need_drop}件物品")

        # 第10步：从下向上选择N件物品
        picked = await self.page.evaluate(f"""() => {{
            const paragraphs = document.querySelectorAll("p");
            let targetParagraph = null;
            for (let p of paragraphs) {{
                if (p.textContent.includes("不把沉重的背包清理一番")) {{
                    targetParagraph = p;
                    break;
                }}
            }}

            let current = targetParagraph.nextElementSibling;
            while (current) {{
                if (current.tagName === "TABLE" && current.classList.contains("content_table")) {{
                    break;
                }}
                current = current.nextElementSibling;
            }}

            const rows = Array.from(current.querySelectorAll("tr"));
            let rowsWithCheckbox = [];

            rows.forEach(row => {{
                const checkbox = row.querySelector("input[name^='SellItemsFound[']:not([name*='setter'])");
                if (checkbox) {{
                    rowsWithCheckbox.push({{ checkbox: checkbox, name: checkbox.name }});
                }}
            }});

            const picked = [];
            for (let i = 1; i <= {need_drop} && i <= rowsWithCheckbox.length; i++) {{
                const item = rowsWithCheckbox[rowsWithCheckbox.length - i];
                item.checkbox.checked = true;
                const rowText = (item.checkbox.closest("tr")?.textContent || "").replace(/\\s+/g, " ").trim();
                picked.push({{ index: rowsWithCheckbox.length - i, name: item.name, text: rowText }});
            }}

            return picked;
        }}""")

        if picked:
            self.log("INFO", f"从下往上勾选了 {len(picked)} 件物品：")
            for idx, item in enumerate(picked, 1):
                self.log("INFO", f"  {idx}. [序号{item.get('index')}] {item.get('text', '')}")
        else:
            self.log("WARNING", f"未能勾选任何物品（need_drop={need_drop}）")

        # 第11步：点击应用改动
        self.log("INFO", "点击应用改动")
        await self.page.click('input[value="应用改动"]')
        await self.wait_for_page(extra_wait=2)

        # 第12步：检查是否成功进入仓库页面
        has_overload = await self.page.evaluate("""() => {
            return document.body.textContent.includes("不得不抛弃");
        }""")

        if has_overload:
            self.log("WARNING", "清理后仍然超载")
        else:
            self.log("INFO", "清理背包完成，已进入仓库页面")

    # 异步方法：筛选耗材物品
    async def filter_seconds(self):
        """筛选耗材物品"""
        # 确保页面有效
        await self.wait_for_page(extra_wait=2)
        # 记录正在筛选耗材的日志
        self.log("INFO", "正在筛选耗材...")
        try:
            # 等待耗材筛选复选框出现，超时 30 秒
            await self.page.wait_for_selector('input[name="item_3usage_item"][value="yes"]', timeout=30000)
            # 点击耗材筛选复选框
            await self.page.locator('input[name="item_3usage_item"][value="yes"]').click()
            await self.wait_for_page(extra_wait=1)
        # 如果出现异常
        except Exception as e:
            # 记录警告日志
            self.log("WARNING", f"筛选复选框未找到: {e}")
            # 提前返回
            return

        try:
            # 等待搜索按钮出现，超时 30 秒
            await self.page.wait_for_selector("text=开始搜索", timeout=30000)
            # 点击搜索按钮
            await self.page.locator("text=开始搜索").click()
        # 如果出现异常
        except Exception as e:
            # 记录警告日志
            self.log("WARNING", f"搜索按钮未找到: {e}")
            # 提前返回
            return

        # 等待页面加载完成（搜索后页面会刷新）
        await self.wait_for_page(extra_wait=2)
        # 记录筛选完成的日志
        self.log("INFO", "筛选耗材完成")

    async def filter_pieces(self):
        """筛选镶嵌材料物品"""
        await self.wait_for_page(extra_wait=2)
        self.log("INFO", "正在筛选镶嵌材料...")
        try:
            await self.page.wait_for_selector('input[name="item_3usage_item"][value=""]', timeout=30000)
            await self.page.locator('input[name="item_3usage_item"][value=""]').click()
            await self.page.wait_for_selector('select[name="item_3sockets"]', timeout=30000)
            await self.page.locator('select[name="item_3sockets"]').select_option("-1")
            await self.wait_for_page(extra_wait=1)
        except Exception as e:
            self.log("WARNING", f"镶嵌材料筛选框未找到: {e}")
            return

        try:
            await self.page.wait_for_selector("text=开始搜索", timeout=30000)
            await self.page.locator("text=开始搜索").click()
        except Exception as e:
            self.log("WARNING", f"搜索按钮未找到: {e}")
            return

        await self.wait_for_page(extra_wait=2)
        self.log("INFO", "筛选镶嵌材料完成")

    async def _click_first_checkbox(self):
        """点击位置列全选复选框，返回是否成功"""
        # 记录正在点击全选复选框的日志
        try:
            # 使用 XPath 精确定位 thead 中的位置列全选框
            # thead 和 tfoot 都有同名复选框，需要指定 thead
            checkbox = self.page.locator('xpath=//thead//input[@name="doEquipItem_setter[2]"]')
            # 检查复选框是否存在
            if await checkbox.count() > 0:
                # 点击复选框（超时10分钟：该点击触发表单提交跳转，
                # 服务器繁忙时跳转响应可能远超默认30秒）
                await checkbox.click(timeout=600000)
                await self.wait_for_page(extra_wait=1)
                # 记录点击成功的日志
                # 返回 True 表示成功
                return True
            else:
                # 页面上没有复选框，说明没有可操作的物品
                self.log("INFO", "当前页面没有可操作的物品，跳过全选")
                # 返回 False 表示没有物品
                return False
        except:
            # 未找到复选框，记录警告日志
            self.log("WARNING", "全选位置复选框未找到，跳过")
            # 返回 False 表示失败
            return False

    async def _get_lager_count(self):
        """读取当前筛选视图的物品总数（表单隐藏域 ITEMS_LAGER_COUNT，读取失败返回 None）"""
        try:
            return await self.page.evaluate("""() => {
                const el = document.querySelector('input[name="ITEMS_LAGER_COUNT"]');
                return el ? (parseInt(el.value) || 0) : null;
            }""")
        except Exception:
            return None

    async def move_to_warehouse(self, target, target_name):
        """全选并移动到指定仓库（筛选结果可能超过一页：循环"全选→移动→应用"直到移完）

        物品被移走后，后续页的物品会自动补位到第1页，因此停留在第1页循环即可；
        全部移完后全选复选框消失（_click_first_checkbox 返回 False），循环结束。
        """
        self.log("INFO", f"准备将选中物品移动到{target_name}")
        # 每轮最多移动当前页（50件）；上限防止异常时死循环（400轮=2万件）
        max_rounds = 400
        stall_count = 0  # 连续"应用后物品总数未减少"的轮次
        for i in range(1, max_rounds + 1):
            # 全选当前页：无全选框 = 筛选后已无剩余物品，正常结束
            self.log("INFO", f">>>全选(第{i}轮)")
            if not await self._click_first_checkbox():
                self.log("INFO", f"没有可操作的物品，全选并移动到{target_name}结束（共{i - 1}轮）")
                return
            await self.wait_for_page(extra_wait=0.5)

            # 记录应用前的物品总数，用于判断本轮是否真的移走了物品
            count_before = await self._get_lager_count()

            self.log("INFO", f">>>移动...(第{i}轮)")
            await self.page.wait_for_selector('thead select[name="dummy"]', timeout=30000)
            await self.page.locator('thead select[name="dummy"]').select_option(target)
            await self.wait_for_page(extra_wait=0.5)

            self.log("INFO", f">>>应用...(第{i}轮)")
            await self.page.wait_for_selector('input[value="应用改动"]', timeout=30000)
            # 点击超时放宽到10分钟：一次移动50件物品，服务器繁忙时
            # 表单提交的跳转响应可能远超默认30秒（点击本身已成功，
            # 卡住的是等待页面跳转完成）
            await self.page.locator('input[value="应用改动"]').first.click(timeout=600000)
            await self.wait_for_page(extra_wait=2)

            # 防卡死：应用后物品总数未减少（物品均不可移入或操作未生效），
            # 连续 2 轮无进展则停止循环，避免死循环
            count_after = await self._get_lager_count()
            if count_after is not None:
                self.log("INFO", f"第{i}轮完成，筛选视图剩余约{count_after}件")
                if count_before is not None and count_after >= count_before:
                    stall_count += 1
                    self.log("WARNING", f"第{i}轮应用后物品数未减少（{count_before} -> {count_after}），连续无进展{stall_count}次")
                    if stall_count >= 2:
                        self.log("WARNING", f"连续{stall_count}轮无进展，停止移动到{target_name}")
                        return
                else:
                    stall_count = 0

        self.log("WARNING", f"移动到{target_name}已达轮次上限{max_rounds}，提前结束")

    async def filter_group_items(self):
        """筛选团队物品（radio: item_3group_item 选"是"）"""
        await self.wait_for_page(extra_wait=2)
        self.log("INFO", "正在筛选团队物品...")
        try:
            radio = self.page.locator('input[name="item_3group_item"][value="yes"]')
            await self.page.wait_for_selector('input[name="item_3group_item"][value="yes"]', timeout=30000)
            # radio 勾选即触发表单提交刷新；若点击引发导航，等待新页面
            if not await radio.is_checked():
                await radio.click()
                await self.wait_for_page(extra_wait=1)
        except Exception as e:
            self.log("WARNING", f"团队物品筛选框未找到: {e}")
            return

        try:
            await self.page.wait_for_selector("text=开始搜索", timeout=30000)
            await self.page.locator("text=开始搜索").click()
        except Exception as e:
            self.log("WARNING", f"搜索按钮未找到: {e}")
            return

        await self.wait_for_page(extra_wait=2)
        self.log("INFO", "筛选团队物品完成")

    async def _move_filtered_to(self, title, filter_coro, target, target_name):
        """一键通用流程：重置筛选 → 筛选 → 多轮移动 → 恢复页面

        筛选状态跨页面保留，必须先导航回物品页重置，避免残留上一次的
        筛选视图（如耗材筛选）导致误移。
        """
        self.log("INFO", f"【{title}】重置物品页筛选状态...")
        await self.navigate_to_items()
        # 执行筛选（传入的协程函数）
        await filter_coro()
        # 多轮全选-应用直到移完
        await self.move_to_warehouse(target, target_name)
        self.log("INFO", f"【{title}】完成")
        # 收尾：再次导航回物品页清除筛选，恢复默认视图
        await self.navigate_to_items()

    async def move_consumables_to_group2(self):
        """一键：当前英雄仓库的全部耗材移入团队仓库"""
        await self._move_filtered_to(
            "耗材入团仓", self.filter_seconds, "go_group_2", "团队仓库"
        )

    async def move_pieces_to_group2(self):
        """一键：当前英雄仓库的全部镶嵌材料移入团队仓库"""
        await self._move_filtered_to(
            "镶嵌入团仓", self.filter_pieces, "go_group_2", "团队仓库"
        )

    async def move_group_items_to_treasury(self):
        """一键：当前英雄仓库的全部团队物品移入宝库"""
        await self._move_filtered_to(
            "团队物品入宝库", self.filter_group_items, "go_group", "宝库"
        )


    # 异步方法：切换到下一个英雄
    async def switch_to_next_hero(self):
        """切换到下一个英雄"""
        # 确保页面有效
        await self.ensure_page_valid()
        # 记录正在切换英雄的日志
        self.log("INFO", "正在切换到下一个英雄...")
        try:
            # 等待切换英雄按钮出现，超时 30 秒
            await self.page.wait_for_selector('img[alt="切换到下一个活跃的英雄"]', timeout=30000)
            # 点击切换英雄按钮
            await self.page.locator('img[alt="切换到下一个活跃的英雄"]').click()
            await self.wait_for_page(extra_wait=1)
        # 如果出现异常
        except Exception as e:
            # 记录警告日志
            self.log("WARNING", f"切换英雄按钮未找到: {e}")
            # 重新抛出异常
            raise

        # 等待页面加载完成
        await self.wait_for_page(extra_wait=1)
        # 记录切换完成的日志
        self.log("INFO", "切换英雄完成")

    # 异步方法：设置地城时间
    async def set_dungeon_time(self):
        """设置地城时间（点击 reduce_dungeon_time 按钮）"""
        # 等待页面加载完成
        await self.wait_for_page(extra_wait=1)

        # 判断是否存在减少地城时间按钮
        btn = self.page.locator('input[name="reduce_dungeon_time"]')
        has_btn = await btn.is_visible()

        # 执行减少地城时间操作
        time_before = await self.page.evaluate("() => { const el = document.getElementById('gadgetNextdungeonTime'); return el ? el.textContent : ''; }")
        self.log("INFO", f"  -> 地城时间（设置前）: {time_before}")

        if not has_btn:
            self.log("INFO", "  -> 跳过设置地城时间: 无减少时间按钮")
            return

        # 获取 onclick 属性中的 URL 并发送 AJAX 请求用于日志
        onclick = await btn.get_attribute("onclick", timeout=2000)
        match = re.search(r"ajaxFetchUrl\(\s*'([^']+)'", onclick)
        if match:
            url = match.group(1)
            self.log("INFO", f"  -> AJAX 请求 URL: {url}")
            result = await self.page.evaluate(f"fetch('{url}').then(r => r.text())")
            if len(result) <= 500:
                self.log("INFO", f"  -> AJAX 响应: {result}")
            else:
                self.log("INFO", f"  -> AJAX 响应(前500字符): {result[:500]}")

        await btn.click()
        await self.wait_for_page(extra_wait=1)

        # 检查页面元素是否有变化
        time_after = await self.page.evaluate("() => { const el = document.getElementById('gadgetNextdungeonTime'); return el ? el.textContent : ''; }")

        if time_after:
            self.log("INFO", f"  -> 地城时间（设置后）: {time_after}")

        btn_visible = await self.page.locator('input[name="reduce_dungeon_time"]').is_visible()
        if not btn_visible:
            self.log("INFO", "  -> 加速成功")

    # 异步方法：处理单个英雄
    async def process_hero(self):
        """处理单个英雄"""
        # 获取英雄名称
        hero_name = await self.get_hero_name()
        # 记录处理英雄的日志
        self.log("INFO", f"处理英雄: {hero_name}")

        # 检查是否为导师英雄
        if await self.is_mentor_hero():
            # 记录跳过导师英雄的日志
            self.log("INFO", f"  -> 跳过导师英雄")
            # 切换到下一个英雄
            await self.switch_to_next_hero()
            # 返回 False 表示未处理
            return False

        # 清理超载的背包
        await self.clean_backpack()
        
        # 筛选耗材
        await self.filter_seconds()
        # 全选并移动
        await self.move_to_warehouse("go_group_2", "团队仓库")

        # 筛选镶嵌物品
        await self.filter_pieces()
        # 全选并移动
        await self.move_to_warehouse("go_group", "宝库")

        # 设置地城时间
        await self.set_dungeon_time()

        # 切换到下一个英雄
        await self.switch_to_next_hero()
        # 记录处理完成的日志
        self.log("INFO", f"处理英雄完成: {hero_name}")
        # 返回 True 表示处理成功
        return True

    # 异步方法：循环处理所有英雄
    async def process_all_heroes(self):
        """循环处理所有英雄"""
        # 记录正在处理所有英雄的日志
        self.log("INFO", "正在处理所有英雄...")

        # 获取第一个英雄的名字
        self.first_hero = await self.get_hero_name()
        # 记录起始英雄的日志
        self.log("INFO", f"起始英雄: {self.first_hero}")

        # 创建集合记录已处理的英雄（只用英雄名字）
        processed_heroes = set()
        # 初始化已处理计数
        self.processed_count = 0

        # 无限循环
        while True:
            # 获取当前英雄名称
            current_hero = await self.get_hero_name()

            # 检查是否已处理过（英雄名字重复）
            if current_hero in processed_heroes:
                # 记录回到已处理英雄的日志
                self.log("INFO", f"回到已处理英雄: {current_hero}")
                # 记录循环结束的日志，包含英雄名字列表
                hero_list = list(processed_heroes)
                self.log("INFO", f"循环结束，共处理 {len(processed_heroes)} 个英雄: {', '.join(hero_list)}")
                # 跳出循环
                break

            # 处理当前英雄
            try:
                # 处理英雄并获取结果
                success = await self.process_hero()
                # 如果处理成功
                if success:
                    # 将英雄添加到已处理集合
                    processed_heroes.add(current_hero)
                    # 增加已处理计数
                    self.processed_count += 1
            # 如果出现异常
            except Exception as e:
                # 记录错误日志
                self.log("ERROR", f"处理英雄 {current_hero} 时出错: {e}")
                traceback.print_exc()
                # 出错后仍然尝试切换到下一个英雄
                try:
                    # 切换到下一个英雄
                    await self.switch_to_next_hero()
                # 如果切换失败
                except:
                    # 忽略异常
                    pass

            # 等待 1 秒
            await self.page.wait_for_timeout(1000)

    # 异步方法：执行自动化任务
    async def run(self):
        """执行自动化任务"""
        # 记录正在执行任务的日志
        self.log("INFO", "正在执行自动化任务...")
        try:
            # 连接浏览器
            await self.connect()
            # 处理所有英雄
            await self.process_all_heroes()
            # 记录任务完成的日志
            self.log("INFO", "任务完成!")
        # 如果出现异常
        except Exception as e:
            # 记录错误日志
            self.log("ERROR", f"执行出错: {e}")
            traceback.print_exc()
        finally:
            await self.close()


# 异步函数：执行一次任务
async def run_once():
    """执行一次任务"""
    # 创建自动化对象
    automation = WoDAutomation()
    try:
        # 运行自动化任务
        await automation.run()
    finally:
        await automation.close()


# 函数：定时执行任务
def run_scheduled():
    """定时执行任务"""
    # 每 240 分钟执行一次
    schedule.every(240).minutes.do(lambda: asyncio.run(run_once()))

    # 记录定时任务已启动的日志
    logger.info("定时任务已启动，每240分钟执行一次...")
    # 记录首次立即执行的日志
    logger.info("首次立即执行，然后每240分钟执行一次")
    # 记录停止方式的日志
    logger.info("按 Ctrl+C 停止")

    # 首次立即执行
    asyncio.run(run_once())

    # 无限循环
    while True:
        # 运行待定的计划任务
        schedule.run_pending()
        # 休眠 60 秒
        time.sleep(60)


# 主程序入口
if __name__ == "__main__":
    # 导入 sys 模块
    import sys

    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        # 如果参数是 --once，立即执行一次
        asyncio.run(run_once())
    else:
        # 否则定时执行
        run_scheduled()
