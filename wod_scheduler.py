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
# 导入 re 库，用于正则表达式（当前未使用）
import re
# 从 playwright.async_api 导入 async_playwright，用于浏览器自动化
from playwright.async_api import async_playwright
# 从 dotenv 导入 load_dotenv，用于加载 .env 文件
from dotenv import load_dotenv

# 加载 .env 文件，获取环境变量
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# 配置常量：Edge 浏览器路径
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
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
        # 浏览器对象，初始为 None
        self.browser = None
        # 页面对象，初始为 None
        self.page = None
        # 第一个英雄的名字，初始为 None
        self.first_hero = None
        # 已处理的英雄数量，初始为 0
        self.processed_count = 0
        # 日志回调函数，用于向 GUI 发送日志
        self.log_callback = log_callback
        # 是否自动登录，默认为 True
        self.auto_login = auto_login

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

    async def navigate_to_items(self):
        """导航到物品页面并等待加载完成"""
        # 记录导航日志
        self.log("INFO", f"正在导航到物品页面: {WOD_ITEM_URL}")
        # 导航到物品页面
        await self.page.goto(WOD_ITEM_URL)
        # 等待页面加载完成，额外等待 2 秒
        await self.wait_for_page(extra_wait=2)
        # 记录导航完成日志
        self.log("INFO", f"导航完成，当前 URL: {self.page.url}")

    async def _has_login_form(self):
        """统一检测页面是否有登录表单，返回表单信息字典"""
        # 检查是否存在用户名输入框
        has_username = await self.page.locator('input[name="login_name"]').count() > 0
        # 检查是否存在密码输入框
        has_password = await self.page.locator('input[name="login_password"]').count() > 0
        # 检查是否存在提交按钮
        has_submit = await self.page.locator('input[type="submit"], button[type="submit"]').count() > 0

        # 构建返回结果字典
        result = {
            # 三个条件都满足才认为有登录表单
            "has_form": has_username and has_password and has_submit,
            # 用户名输入框定位器（用于后续填入）
            "username_input": self.page.locator('input[name="login_name"]').first if has_username else None,
            # 密码输入框定位器（用于后续填入）
            "password_input": self.page.locator('input[name="login_password"]').first if has_password else None,
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
            await asyncio.sleep(1)

        # 打印点击登录按钮的日志
        self.log("INFO", "点击登录按钮...")
        # 找到第一个提交按钮并点击
        await self.page.locator('input[type="submit"], button[type="submit"]').first.click()

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
            logger.info(f"尝试连接到 Edge 调试端口 http://localhost:{DEBUG_PORT}")
            # 启动 Playwright
            playwright = await async_playwright().start()
            # 通过 CDP 连接到浏览器
            self.browser = await playwright.chromium.connect_over_cdp(
                f"http://localhost:{DEBUG_PORT}"
            )
            # 记录连接成功的日志
            self.log("INFO", "已连接到 Edge 浏览器")
        # 如果连接过程中出现异常
        except Exception as e:
            # 记录连接失败的日志
            self.log("ERROR", f"连接浏览器失败: {e}")
            # 提示用户确保浏览器已启动
            self.log("ERROR", f"  请确保 Edge 浏览器已用 --remote-debugging-port={DEBUG_PORT} 启动")
            # 提示启动命令
            self.log("ERROR", f"  启动命令: msedge.exe --remote-debugging-port={DEBUG_PORT}")
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
        # 定位页面中的 h1 标签并获取其文本内容
        full_name = await self.page.locator("h1").text_content()
        # 去掉": 仓库"等后缀，只保留英雄名字
        return full_name.split(":")[0]

    # 异步方法：检测是否为导师英雄
    async def is_mentor_hero(self):
        """检测是否为导师英雄"""
        # 获取当前页面的 URL
        url = self.page.url
        # 检查 URL 中是否包含 "reason=mentor"
        return "reason=mentor" in url

    # 异步方法：筛选耗材物品
    async def filter_consumables(self):
        """筛选耗材物品"""
        # 记录正在筛选耗材的日志
        self.log("INFO", "正在筛选耗材...")
        try:
            # 等待耗材筛选复选框出现，超时 30 秒
            await self.page.wait_for_selector('input[name="item_3usage_item"][value="yes"]', timeout=30000)
            # 点击耗材筛选复选框
            await self.page.locator('input[name="item_3usage_item"][value="yes"]').click()
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

    async def _click_first_checkbox(self):
        """点击位置列全选复选框，返回是否成功"""
        # 记录正在点击全选复选框的日志
        self.log("INFO", "正在点击全选复选框...")
        try:
            # 使用 XPath 精确定位 thead 中的位置列全选框
            # thead 和 tfoot 都有同名复选框，需要指定 thead
            checkbox = self.page.locator('xpath=//thead//input[@name="doEquipItem_setter[2]"]')
            # 检查复选框是否存在
            if await checkbox.count() > 0:
                # 点击复选框
                await checkbox.click()
                # 记录点击成功的日志
                self.log("INFO", "全选复选框点击完成")
                # 返回 True 表示成功
                return True
            else:
                # 页面上没有复选框，说明没有可操作的物品
                self.log("INFO", "当前页面没有可操作的物品，跳过全选")
                # 返回 False 表示没有物品
                return False
        except:
            # 未找到复选框，记录警告日志
            self.log("WARNING", "全选复选框未找到，跳过")
            # 返回 False 表示失败
            return False

    async def _retry_action(self, action_fn, on_retry_fn, error_msg, max_retries=2):
        """通用重试模式：执行操作，失败则刷新页面并恢复"""
        # 循环重试
        for attempt in range(max_retries):
            try:
                # 执行目标操作
                await action_fn()
                # 操作成功，返回 True
                return True
            except Exception as e:
                # 如果还有重试机会
                if attempt < max_retries - 1:
                    # 记录警告日志，准备刷新页面重试
                    self.log("WARNING", f"{error_msg}，刷新页面重试...")
                    # 刷新页面，等待 DOM 内容加载完成
                    await self.page.reload(wait_until="domcontentloaded")
                    # 等待 2 秒，确保页面稳定
                    await self.page.wait_for_timeout(2000)
                    # 执行恢复操作（重新设置之前已完成步骤的状态）
                    restore_result = await on_retry_fn()
                    # 如果恢复操作返回 False，说明页面状态无法恢复，不再重试
                    if restore_result is False:
                        self.log("WARNING", f"{error_msg}，恢复失败，不再重试")
                        return False
                else:
                    # 重试次数用尽，记录失败日志
                    self.log("WARNING", f"{error_msg}: {e}")
                    # 返回 False 表示操作失败
                    return False

    async def select_all_and_move_to_warehouse(self):
        """全选并移动到团队仓库"""
        # 记录正在全选并移动的日志
        self.log("INFO", "正在全选并移动到团队仓库...")
        # 步骤1：点击第一个复选框（全选），如果没有物品则直接返回
        if not await self._click_first_checkbox():
            # 没有可操作的物品，记录日志并提前返回
            self.log("INFO", "没有可操作的物品，跳过移动到团队仓库")
            return
        # 等待 500 毫秒
        await self.page.wait_for_timeout(500)

        # 步骤2：选择团队仓库
        # 定义选择仓库的操作
        async def select_warehouse():
            # 等待选择框加载，超时 30 秒（指定 thead 避免匹配多个）
            await self.page.wait_for_selector('thead select[name="dummy"]', timeout=30000)
            # 选择团队仓库选项（使用 first 避免匹配多个）
            await self.page.locator('thead select[name="dummy"]').select_option("go_group_2")

        # 定义刷新后需要执行的恢复操作（重新全选）
        async def restore_after_select():
            return await self._click_first_checkbox()

        # 执行选择仓库操作（带重试），失败则提前返回
        if not await self._retry_action(select_warehouse, restore_after_select, "选择框加载超时"):
            return

        # 等待 500 毫秒
        await self.page.wait_for_timeout(500)

        # 步骤3：点击应用改动按钮
        # 定义应用改动的操作
        async def apply_changes():
            # 等待按钮可点击，超时 30 秒
            await self.page.wait_for_selector('input[value="应用改动"]', timeout=30000)
            # 点击应用改动按钮（使用 first 因为页面上有多个）
            await self.page.locator('input[value="应用改动"]').first.click()

        # 定义刷新后需要执行的恢复操作（重新全选 + 重新选仓库）
        async def restore_after_apply():
            # 重新全选，如果失败则直接返回 False
            if not await self._click_first_checkbox():
                return False
            # 等待 500 毫秒
            await self.page.wait_for_timeout(500)
            try:
                # 等待选择框加载（指定 thead 避免匹配多个）
                await self.page.wait_for_selector('thead select[name="dummy"]', timeout=30000)
                # 重新选择团队仓库（使用 thead 避免匹配多个）
                await self.page.locator('thead select[name="dummy"]').select_option("go_group_2")
                # 等待 500 毫秒
                await self.page.wait_for_timeout(500)
            except:
                # 恢复失败则忽略
                pass

        # 执行应用改动操作（带重试），失败则提前返回
        if not await self._retry_action(apply_changes, restore_after_apply, "应用改动按钮加载超时"):
            return

        # 等待页面加载完成（应用改动后页面会刷新）
        await self.wait_for_page(extra_wait=2)
        # 记录移动完成的日志
        self.log("INFO", "全选并移动到团队仓库完成")

    # 异步方法：切换到下一个英雄
    async def switch_to_next_hero(self):
        """切换到下一个英雄"""
        # 记录正在切换英雄的日志
        self.log("INFO", "正在切换到下一个英雄...")
        try:
            # 等待切换英雄按钮出现，超时 30 秒
            await self.page.wait_for_selector('img[alt="切换到下一个活跃的英雄"]', timeout=30000)
            # 点击切换英雄按钮
            await self.page.locator('img[alt="切换到下一个活跃的英雄"]').click()
        # 如果出现异常
        except Exception as e:
            # 记录警告日志
            self.log("WARNING", f"切换英雄按钮未找到: {e}")
            # 重新抛出异常
            raise

        # 等待 2 秒
        await self.page.wait_for_timeout(2000)
        # 记录切换完成的日志
        self.log("INFO", "切换英雄完成")

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

        # 筛选耗材
        await self.filter_consumables()

        # 全选并移动
        await self.select_all_and_move_to_warehouse()

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
                # 导入 traceback 模块
                import traceback
                # 打印异常堆栈
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
            # 导入 traceback 模块
            import traceback
            # 打印异常堆栈
            traceback.print_exc()


# 异步函数：执行一次任务
async def run_once():
    """执行一次任务"""
    # 创建自动化对象
    automation = WoDAutomation()
    # 运行自动化任务
    await automation.run()


# 函数：定时执行任务
def run_scheduled():
    """定时执行任务"""
    # 每 4 小时执行一次
    schedule.every(4).hours.do(lambda: asyncio.run(run_once()))

    # 记录定时任务已启动的日志
    logger.info("定时任务已启动，每4小时执行一次...")
    # 记录首次立即执行的日志
    logger.info("首次立即执行，然后每4小时执行一次")
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
