# -*- coding: utf-8 -*-
"""
WoD 定时自动化脚本
定时筛选耗材并批量移动到团队仓库
"""

import asyncio
import schedule
import time
import logging
import os
import re
from playwright.async_api import async_playwright
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# 配置
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
DEBUG_PORT = 9222
WOD_URL = "https://delta.world-of-dungeons.org/wod/spiel/hero/items.php"
WOD_LOGIN_URL = "https://delta.world-of-dungeons.org/wod/spiel/login.php"

# 从 .env 读取账号密码
WOD_USERNAME = os.getenv('WOD_USERNAME', '')
WOD_PASSWORD = os.getenv('WOD_PASSWORD', '')

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WoDAutomation:
    def __init__(self):
        self.browser = None
        self.page = None
        self.first_hero = None
        self.processed_count = 0

    async def is_logged_in(self):
        """检查是否已登录"""
        # 等待页面加载完成
        await self.page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(1)

        title = await self.page.title()
        url = self.page.url

        # 多种检测方式
        if "登陆过期" in title or "cookies disabled" in title.lower():
            return False
        if "login" in url.lower():
            return False
        if "登录" in title or "login" in title.lower():
            return False

        return True

    async def login(self):
        """登录 WoD"""
        if not WOD_USERNAME or not WOD_PASSWORD:
            raise Exception("未配置登录信息，请在 .env 文件中设置 WOD_USERNAME 和 WOD_PASSWORD")

        logger.info("开始登录...")
        logger.info(f"  用户名: {WOD_USERNAME}")

        # 导航到登录页面
        await self.page.goto(WOD_LOGIN_URL)
        await self.page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)

        # 打印页面信息用于调试
        url = self.page.url
        title = await self.page.title()
        logger.info(f"  登录页面 URL: {url}")
        logger.info(f"  登录页面标题: {title}")

        # 尝试多种可能的用户名输入框选择器
        username_selectors = [
            'input[name="login_name"]',
            'input[name="username"]',
            'input[type="text"]',
            'input#login_name',
        ]

        password_selectors = [
            'input[name="login_password"]',
            'input[name="password"]',
            'input[type="password"]',
            'input#login_password',
        ]

        # 查找并填写用户名
        username_filled = False
        for selector in username_selectors:
            try:
                await self.page.wait_for_selector(selector, timeout=3000)
                await self.page.fill(selector, WOD_USERNAME)
                logger.info(f"  ✓ 已填写用户名 (选择器: {selector})")
                username_filled = True
                break
            except:
                continue

        if not username_filled:
            logger.error("无法找到用户名输入框")
            logger.info("请手动登录后按 Ctrl+C 继续...")
            # 等待用户手动登录
            await self.page.wait_for_url("**/items.php", timeout=300000)
            return

        # 查找并填写密码
        password_filled = False
        for selector in password_selectors:
            try:
                await self.page.wait_for_selector(selector, timeout=3000)
                await self.page.fill(selector, WOD_PASSWORD)
                logger.info(f"  ✓ 已填写密码 (选择器: {selector})")
                password_filled = True
                break
            except:
                continue

        if not password_filled:
            raise Exception("无法找到密码输入框")

        # 点击登录按钮 - 尝试多种选择器
        submit_selectors = [
            'input[type="submit"]',
            'button[type="submit"]',
            'input[value*="登录"]',
            'input[value*="Login"]',
        ]

        clicked = False
        for selector in submit_selectors:
            try:
                await self.page.click(selector)
                logger.info(f"  ✓ 已点击登录按钮")
                clicked = True
                break
            except:
                continue

        if not clicked:
            raise Exception("无法找到登录按钮")

        # 等待登录完成
        await self.page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(3)

        # 检查登录是否成功
        new_title = await self.page.title()
        new_url = self.page.url

        if "登陆过期" in new_title or "cookies disabled" in new_title.lower() or "login" in new_url.lower():
            logger.error(f"登录可能失败")
            logger.error(f"  当前标题: {new_title}")
            logger.error(f"  当前 URL: {new_url}")
            raise Exception("登录失败，请检查用户名和密码")

        logger.info("✓ 登录成功!")

    async def connect(self):
        """连接到已启动的 Edge 浏览器"""
        logger.info(f"尝试连接到 Edge 调试端口 http://localhost:{DEBUG_PORT}")
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.connect_over_cdp(
                f"http://localhost:{DEBUG_PORT}"
            )
            # 获取所有上下文
            contexts = self.browser.contexts

            # 查找 WoD 页面
            wod_page = None
            for context in contexts:
                for page in context.pages:
                    if "world-of-dungeons" in page.url:
                        wod_page = page
                        logger.info(f"找到 WoD 页面: {page.url}")
                        break
                if wod_page:
                    break

            if wod_page:
                self.page = wod_page
            else:
                # 没有 WoD 页面，创建新页面
                if contexts:
                    self.page = await contexts[0].new_page()
                else:
                    raise Exception("无法获取浏览器上下文")

            # 检查登录状态
            if not await self.is_logged_in():
                logger.info("未登录，开始自动登录...")
                await self.login()
            else:
                logger.info("已登录")

            # 确保在物品页面
            if "items.php" not in self.page.url:
                logger.info(f"导航到物品页面: {WOD_URL}")
                await self.page.goto(WOD_URL)
                await self.page.wait_for_load_state("networkidle")

            logger.info("已连接到 Edge 浏览器")
            logger.info(f"  当前 URL: {self.page.url}")
            logger.info(f"  标题: {await self.page.title()}")
        except Exception as e:
            logger.error(f"连接失败: {e}")
            logger.error(f"  请确保 Edge 浏览器已用 --remote-debugging-port={DEBUG_PORT} 启动")
            logger.error(f"  启动命令: msedge.exe --remote-debugging-port={DEBUG_PORT}")
            raise

    async def get_hero_name(self):
        """获取当前英雄名称"""
        return await self.page.locator("h1").text_content()

    async def is_mentor_hero(self):
        """检测是否为导师英雄"""
        url = self.page.url
        return "reason=mentor" in url

    async def filter_consumables(self):
        """筛选耗材物品"""
        await self.page.locator('input[name="item_3usage_item"][value="yes"]').click()
        await self.page.locator("text=开始搜索").click()
        await self.page.wait_for_timeout(2000)

    async def select_all_and_move_to_warehouse(self):
        """全选并移动到团队仓库"""
        # 全选 - 使用更灵活的选择器
        try:
            checkboxes = self.page.locator('input[type="checkbox"]')
            count = await checkboxes.count()
            if count > 0:
                # 点击第一个复选框（通常是全选）
                await checkboxes.nth(0).click()
        except:
            logger.warning("全选复选框未找到，跳过")

        await self.page.wait_for_timeout(500)

        # 选择团队仓库 - 等待选择框出现
        try:
            # 等待选择框加载
            await self.page.wait_for_selector('select[name="dummy"]', timeout=5000)
            await self.page.locator('select[name="dummy"]').select_option("go_group_2")
        except Exception as e:
            logger.warning(f"选择团队仓库失败: {e}")
            return

        await self.page.wait_for_timeout(500)

        # 应用改动 - 使用 text 选择器而不是 Unicode 转义
        try:
            # 等待按钮可点击
            await self.page.wait_for_selector('input[value="应用改动"]', timeout=5000)
            await self.page.locator('input[value="应用改动"]').click()
        except Exception as e:
            logger.warning(f"应用改动失败: {e}")

        await self.page.wait_for_timeout(2000)

    async def switch_to_next_hero(self):
        """切换到下一个英雄"""
        await self.page.locator('img[alt="切换到下一个活跃的英雄"]').click()
        await self.page.wait_for_timeout(2000)

    async def process_hero(self):
        """处理单个英雄"""
        hero_name = await self.get_hero_name()
        logger.info(f"处理英雄: {hero_name}")

        # 检查导师英雄
        if await self.is_mentor_hero():
            logger.info(f"  -> 跳过导师英雄")
            await self.switch_to_next_hero()
            return False

        # 筛选耗材
        await self.filter_consumables()

        # 全选并移动
        await self.select_all_and_move_to_warehouse()

        # 切换到下一个英雄
        await self.switch_to_next_hero()
        return True

    async def process_all_heroes(self):
        """循环处理所有英雄"""
        self.first_hero = await self.get_hero_name()
        self.first_url = self.page.url  # 记录起始 URL
        self.processed_count = 0
        logger.info(f"起始英雄: {self.first_hero}")
        logger.info(f"起始 URL: {self.first_url}")

        # 记录已处理的英雄
        processed_heroes = set()

        while True:
            current_hero = await self.get_hero_name()
            current_url = self.page.url

            # 生成唯一标识（英雄名 + URL）
            hero_id = f"{current_hero}|{current_url}"

            # 检查是否回到起点或已处理过
            if hero_id in processed_heroes:
                logger.info(f"回到已处理英雄: {current_hero}")
                logger.info(f"循环结束，共处理 {len(processed_heroes)} 个英雄")
                break

            # 处理当前英雄
            try:
                success = await self.process_hero()
                if success:
                    processed_heroes.add(hero_id)
                    self.processed_count += 1
            except Exception as e:
                logger.error(f"处理英雄 {current_hero} 时出错: {e}")
                import traceback
                traceback.print_exc()
                # 出错后仍然尝试切换到下一个英雄
                try:
                    await self.switch_to_next_hero()
                except:
                    pass

            await self.page.wait_for_timeout(1000)

    async def run(self):
        """执行自动化任务"""
        try:
            await self.connect()
            await self.process_all_heroes()
            logger.info("任务完成!")
        except Exception as e:
            logger.error(f"执行出错: {e}")
            import traceback
            traceback.print_exc()


async def run_once():
    """执行一次任务"""
    automation = WoDAutomation()
    await automation.run()


def run_scheduled():
    """定时执行任务"""
    # 每 4 小时执行一次
    schedule.every(4).hours.do(lambda: asyncio.run(run_once()))

    logger.info("定时任务已启动，每4小时执行一次...")
    logger.info("首次立即执行，然后每4小时执行一次")
    logger.info("按 Ctrl+C 停止")

    # 首次立即执行
    asyncio.run(run_once())

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        # 立即执行一次
        asyncio.run(run_once())
    else:
        # 定时执行
        run_scheduled()
