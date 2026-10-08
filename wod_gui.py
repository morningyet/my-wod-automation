# -*- coding: utf-8 -*-
"""
WoD 自动化 GUI 控制面板
"""

# 导入 asyncio 库，用于异步编程
import asyncio
# 导入 threading 库，用于多线程
import threading
# 导入 customtkinter 库，用于现代化 GUI 界面
import customtkinter as ctk
# 从 tkinter 导入 scrolledtext（虽然未使用）
from tkinter import scrolledtext
# 从 wod_scheduler 导入 WoDAutomation 类
from wod_scheduler import WoDAutomation
# 从 wod_scheduler 导入卖出记录存储键
from wod_scheduler import SELL_STORAGE_KEY


# 定义 WoDGUI 类，创建 GUI 控制面板
class WoDGUI:
    # 初始化方法
    def __init__(self):
        # 设置外观模式为暗色主题
        ctk.set_appearance_mode("dark")
        # 设置默认颜色主题为蓝色
        ctk.set_default_color_theme("blue")

        # 创建主窗口
        self.root = ctk.CTk()
        # 设置窗口标题
        self.root.title("WoD 自动化控制面板")
        # 设置窗口大小为 900x600
        self.root.geometry("900x600")

        # 初始化状态变量
        self.connected = False  # 是否已连接浏览器
        self.auto_login = True  # 是否自动登录，默认开启
        self.automation = None  # 自动化对象
        self.loop = None  # asyncio 事件循环
        self.scheduler_running = False  # 定时任务是否运行中
        self.scheduler_timer = None  # 定时器对象
        self.next_run_time = None  # 下次执行时间
        self.sell_monitoring = False  # 卖出记录是否监听中

        # 创建界面组件
        self.create_widgets()

        # 启动事件循环线程
        self.start_event_loop()

    # 创建界面组件
    def create_widgets(self):
        """创建界面组件"""
        # 创建主容器 - 左右分栏布局
        self.main_container = ctk.CTkFrame(self.root)
        # 填充整个窗口，设置边距
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # 创建左侧面板 - 控制区域
        self.left_panel = ctk.CTkFrame(self.main_container)
        # 放在左侧，不自动扩展
        self.left_panel.pack(side="left", fill="both", expand=False, padx=(0, 5), pady=0)
        # 设置固定宽度为 300
        self.left_panel.configure(width=300)

        # 创建右侧面板 - 日志区域
        self.right_panel = ctk.CTkFrame(self.main_container)
        # 放在右侧，自动扩展填充剩余空间
        self.right_panel.pack(side="right", fill="both", expand=True, padx=(5, 0), pady=0)

        # 创建左侧控制面板的内容
        self.create_control_panel()

        # 创建右侧日志面板的内容
        self.create_log_panel()

    # 创建控制面板
    def create_control_panel(self):
        """创建控制面板"""
        # 创建标题标签
        title_label = ctk.CTkLabel(
            self.left_panel,  # 父容器
            text="控制面板",  # 标签文本
            font=ctk.CTkFont(size=20, weight="bold")  # 字体样式
        )
        # 添加到面板，设置上下边距
        title_label.pack(pady=(15, 10))

        # ===== 连接区域 =====
        # 创建连接区域的框架
        connection_frame = ctk.CTkFrame(self.left_panel)
        # 横向填充，设置边距
        connection_frame.pack(fill="x", padx=10, pady=5)

        # 创建连接标题
        conn_title = ctk.CTkLabel(connection_frame, text="连接", font=ctk.CTkFont(weight="bold"))
        conn_title.pack(pady=(10, 5))

        # 创建按钮行（连接按钮 + 自动登录复选框）
        btn_row = ctk.CTkFrame(connection_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=(0, 5))

        # 创建连接浏览器按钮（在左侧）
        self.btn_connect = ctk.CTkButton(
            btn_row,  # 父容器
            text="连接浏览器",  # 按钮文本
            command=self.connect_browser,  # 点击时调用的方法
            height=32  # 按钮高度
        )
        self.btn_connect.pack(side="left", padx=(0, 10))

        # 创建自动登录复选框（在右侧）
        self.chk_auto_login = ctk.CTkCheckBox(
            btn_row,  # 父容器
            text="自动登录",  # 复选框文本
            command=self.on_auto_login_toggle  # 点击时调用的方法
        )
        # 默认勾选自动登录
        self.chk_auto_login.select()
        self.chk_auto_login.pack(side="left")

        # 创建状态标签
        self.lbl_status = ctk.CTkLabel(
            connection_frame,  # 父容器
            text="状态: ● 未连接",  # 默认状态文本
            font=ctk.CTkFont(size=12)  # 字体大小
        )
        self.lbl_status.pack(pady=(0, 10))

        # ===== 单次收菜区域 =====
        # 创建单次收菜区域的框架
        harvest_frame = ctk.CTkFrame(self.left_panel)
        harvest_frame.pack(fill="x", padx=10, pady=5)

        # 创建单次收菜标题
        harvest_title = ctk.CTkLabel(harvest_frame, text="单次收菜", font=ctk.CTkFont(weight="bold"))
        harvest_title.pack(pady=(10, 5))

        # 创建开始收菜按钮
        self.btn_harvest = ctk.CTkButton(
            harvest_frame,  # 父容器
            text="开始收菜",  # 按钮文本
            command=self.start_harvest,  # 点击时调用的方法
            height=35,  # 按钮高度
            state="disabled"  # 初始状态为禁用
        )
        self.btn_harvest.pack(padx=10, pady=(0, 10))

        # ===== 手动操作区域 =====
        # 创建手动操作区域的框架
        manual_frame = ctk.CTkFrame(self.left_panel)
        manual_frame.pack(fill="x", padx=10, pady=5)

        # 创建手动操作标题
        manual_title = ctk.CTkLabel(manual_frame, text="手动操作", font=ctk.CTkFont(weight="bold"))
        manual_title.pack(pady=(10, 5))

        # 第一行：筛选耗材 + 全选
        row1 = ctk.CTkFrame(manual_frame, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=2)

        self.btn_filter = ctk.CTkButton(
            row1,
            text="筛选耗材",
            command=self.manual_filter,
            height=28,
            state="disabled"
        )
        self.btn_filter.pack(side="left", expand=True, fill="x", padx=(0, 3))

        self.btn_select_all = ctk.CTkButton(
            row1,
            text="全选",
            command=self.manual_select_all,
            height=28,
            state="disabled"
        )
        self.btn_select_all.pack(side="left", expand=True, fill="x", padx=(3, 0))

        # 第二行：移入仓库 + 切换英雄
        row2 = ctk.CTkFrame(manual_frame, fg_color="transparent")
        row2.pack(fill="x", padx=10, pady=(2, 2))

        self.btn_move = ctk.CTkButton(
            row2,
            text="移入仓库",
            command=self.manual_move,
            height=28,
            state="disabled"
        )
        self.btn_move.pack(side="left", expand=True, fill="x", padx=(0, 3))

        self.btn_next_hero = ctk.CTkButton(
            row2,
            text="切换英雄",
            command=self.manual_next_hero,
            height=28,
            state="disabled"
        )
        self.btn_next_hero.pack(side="left", expand=True, fill="x", padx=(3, 0))

        # 第三行：一键 仓库耗材全部入团仓（多轮移动，执行时间可能较长）
        self.btn_consumables_to_group = ctk.CTkButton(
            manual_frame,
            text="仓库耗材全部入团仓",
            command=self.manual_consumables_to_group,
            height=28,
            state="disabled"
        )
        self.btn_consumables_to_group.pack(fill="x", padx=10, pady=(2, 2))

        # 第四行：一键 镶嵌材料全部入团仓
        self.btn_pieces_to_group = ctk.CTkButton(
            manual_frame,
            text="镶嵌材料全部入团仓",
            command=self.manual_pieces_to_group,
            height=28,
            state="disabled"
        )
        self.btn_pieces_to_group.pack(fill="x", padx=10, pady=2)

        # 第五行：一键 团队物品全部入宝库
        self.btn_group_items_to_treasury = ctk.CTkButton(
            manual_frame,
            text="团队物品全部入宝库",
            command=self.manual_group_items_to_treasury,
            height=28,
            state="disabled"
        )
        self.btn_group_items_to_treasury.pack(fill="x", padx=10, pady=(2, 10))

        # ===== 自动出售区域 =====
        # 创建自动出售区域的框架
        sellable_frame = ctk.CTkFrame(self.left_panel)
        sellable_frame.pack(fill="x", padx=10, pady=5)

        # 创建自动出售标题
        sellable_title = ctk.CTkLabel(
            sellable_frame, text="自动出售", font=ctk.CTkFont(weight="bold")
        )
        sellable_title.pack(pady=(10, 5))

        # 一键出售按钮（按 js/sellable-items.js 清单圈选并确认卖出，仅当前英雄）
        self.btn_auto_sell = ctk.CTkButton(
            sellable_frame,
            text="出售可卖物品（当前英雄）",
            command=self.manual_auto_sell,
            height=32,
            state="disabled"
        )
        self.btn_auto_sell.pack(fill="x", padx=10, pady=(0, 5))

        # 轮询所有英雄出售按钮
        self.btn_auto_sell_all = ctk.CTkButton(
            sellable_frame,
            text="出售可卖物品（轮询所有英雄）",
            command=self.manual_auto_sell_all,
            height=32,
            state="disabled"
        )
        self.btn_auto_sell_all.pack(fill="x", padx=10, pady=(0, 5))

        # 刷新清单按钮（把浏览器缓冲的卖出记录合并进 sellable-items.js 并清空缓冲）
        self.btn_flush_sellable = ctk.CTkButton(
            sellable_frame,
            text="刷新清单",
            command=self.manual_flush_sellable,
            height=28,
            state="disabled"
        )
        self.btn_flush_sellable.pack(fill="x", padx=10, pady=(0, 10))

        # ===== 定时任务区域 =====
        # 创建定时任务区域的框架
        schedule_frame = ctk.CTkFrame(self.left_panel)
        schedule_frame.pack(fill="x", padx=10, pady=5)

        # 创建定时任务标题
        schedule_title = ctk.CTkLabel(schedule_frame, text="定时任务", font=ctk.CTkFont(weight="bold"))
        schedule_title.pack(pady=(10, 5))

        # 创建控制行（启动定时按钮 + 间隔设置）
        control_row = ctk.CTkFrame(schedule_frame, fg_color="transparent")
        control_row.pack(fill="x", padx=10, pady=(0, 5))

        # 创建启动定时按钮
        self.btn_schedule = ctk.CTkButton(
            control_row,
            text="启动定时",
            command=self.toggle_schedule,
            height=32,
            state="disabled"
        )
        self.btn_schedule.pack(side="left", padx=(0, 10))

        # 创建间隔设置
        ctk.CTkLabel(control_row, text="间隔:").pack(side="left", padx=(0, 3))
        self.interval_entry = ctk.CTkEntry(control_row, width=60, placeholder_text="240")
        self.interval_entry.insert(0, "240")
        self.interval_entry.pack(side="left", padx=(0, 3))
        ctk.CTkLabel(control_row, text="分钟").pack(side="left")

        # 创建下次执行时间标签
        self.lbl_next_run = ctk.CTkLabel(
            schedule_frame,
            text="下次执行: --",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.lbl_next_run.pack(pady=(0, 10))

        # ===== 卖出记录区域 =====
        sell_frame = ctk.CTkFrame(self.left_panel)
        sell_frame.pack(fill="x", padx=10, pady=5)

        sell_title = ctk.CTkLabel(sell_frame, text="卖出记录", font=ctk.CTkFont(weight="bold"))
        sell_title.pack(pady=(10, 5))

        sell_row = ctk.CTkFrame(sell_frame, fg_color="transparent")
        sell_row.pack(fill="x", padx=10, pady=(0, 10))

        self.btn_sell_monitor = ctk.CTkButton(
            sell_row,
            text="开始记录",
            command=self.toggle_sell_monitor,
            height=32,
            state="disabled"
        )
        self.btn_sell_monitor.pack(side="left", expand=True, fill="x", padx=(0, 3))

        self.btn_sell_clear = ctk.CTkButton(
            sell_row,
            text="清空清单",
            command=self.clear_sold,
            height=32,
            state="disabled"
        )
        self.btn_sell_clear.pack(side="left", expand=True, fill="x", padx=(3, 3))

        self.btn_sell_export = ctk.CTkButton(
            sell_row,
            text="导出清单",
            command=self.export_sold,
            height=32,
            state="disabled"
        )
        self.btn_sell_export.pack(side="left", expand=True, fill="x", padx=(3, 0))

    # 创建日志面板
    def create_log_panel(self):
        """创建日志面板"""
        # 创建标题标签
        title_label = ctk.CTkLabel(
            self.right_panel,  # 父容器
            text="操作日志",  # 标签文本
            font=ctk.CTkFont(size=20, weight="bold")  # 字体样式
        )
        title_label.pack(pady=(15, 10))

        # 创建日志文本框
        self.log_text = ctk.CTkTextbox(
            self.right_panel,  # 父容器
            font=ctk.CTkFont(family="Consolas", size=11),  # 使用等宽字体
            wrap="word"  # 按单词换行
        )
        # 填充剩余空间
        self.log_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # 可卖物品清单标题
        sold_title = ctk.CTkLabel(
            self.right_panel,
            text="可卖物品清单",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        sold_title.pack(pady=(0, 5))

        # 可卖物品清单文本框（实时显示当前新增卖出的物品）
        self.sold_text = ctk.CTkTextbox(
            self.right_panel,  # 父容器
            font=ctk.CTkFont(family="Consolas", size=11),  # 使用等宽字体
            wrap="word",  # 按单词换行
            height=150  # 固定高度
        )
        self.sold_text.pack(fill="x", padx=10, pady=(0, 10))

        # 创建清空按钮
        btn_clear = ctk.CTkButton(
            self.right_panel,  # 父容器
            text="清空日志",  # 按钮文本
            command=self.clear_log,  # 点击时调用的方法
            height=30,  # 按钮高度
            width=100  # 按钮宽度
        )
        btn_clear.pack(pady=(0, 10))

    # ===== 事件循环管理 =====
    # 启动事件循环
    def start_event_loop(self):
        """在后台线程启动 asyncio 事件循环"""
        # 定义运行事件循环的内部函数
        def run_loop():
            # 创建新的事件循环
            self.loop = asyncio.new_event_loop()
            # 设置为当前线程的事件循环
            asyncio.set_event_loop(self.loop)
            # 永久运行事件循环
            self.loop.run_forever()

        # 创建后台线程运行事件循环
        self.loop_thread = threading.Thread(target=run_loop, daemon=True)
        # 启动线程
        self.loop_thread.start()

    # 在后台线程中运行异步函数
    def run_async(self, coro):
        """在后台线程中运行异步函数"""
        # 检查事件循环是否存在
        if not self.loop:
            # 记录错误日志
            self.log("ERROR", "事件循环未启动")
            return None
        # 将协程提交到事件循环中运行
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future

    # ===== 日志功能 =====
    # 添加日志
    def log(self, level, message):
        """添加日志"""
        # 根据日志级别设置符号
        symbols = {
            "INFO": "✓",  # 信息级别用对勾
            "WARNING": "⚠",  # 警告级别用警告符号
            "ERROR": "✗"  # 错误级别用叉号
        }
        # 获取对应级别的符号，默认为圆点
        symbol = symbols.get(level, "•")

        # 格式化消息，添加时间戳
        import datetime
        # 获取当前时间并格式化为 HH:MM:SS
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        # 组合日志行
        log_line = f"[{timestamp}] {symbol} {message}\n"

        # 在主线程中更新 UI
        self.root.after(0, lambda: self._append_log(log_line))

    # 追加日志到文本框
    def _append_log(self, text):
        """追加日志到文本框"""
        # 在文本框末尾插入文本
        self.log_text.insert("end", text)
        # 滚动到文本框底部
        self.log_text.see("end")

    # 清空日志
    def clear_log(self):
        """清空日志"""
        # 删除文本框中所有内容
        self.log_text.delete("1.0", "end")

    # 自动登录复选框切换事件
    def on_auto_login_toggle(self):
        """自动登录复选框切换"""
        # 获取复选框的状态并更新变量
        self.auto_login = self.chk_auto_login.get()

    # ===== 连接功能 =====
    # 连接浏览器
    def connect_browser(self):
        """连接浏览器"""
        # 记录连接中的日志
        self.log("INFO", "正在连接浏览器...")
        # 禁用连接按钮
        self.btn_connect.configure(state="disabled")

        # 定义异步连接函数
        async def do_connect():
            try:
                # 清理旧连接：统一用 close() 释放（内部会调用 playwright.stop()
                # 终止 Node.js 驱动进程，避免内存泄漏）。
                # 注意：不能调用 browser.close()——connect_over_cdp 返回的 browser
                # 一旦 close() 会把用户正在使用的整个浏览器也一起关掉。
                if self.automation:
                    try:
                        await self.automation.close()
                    except Exception:
                        pass
                # 创建自动化对象，传入日志回调和自动登录标志
                self.automation = WoDAutomation(log_callback=self.log, auto_login=self.auto_login)
                # 执行连接，设置总超时 5 分钟
                await asyncio.wait_for(self.automation.connect(), timeout=300)
                # 在主线程中调用连接成功回调
                self.root.after(0, self._on_connected)
            except asyncio.TimeoutError:
                self.root.after(0, lambda: self._on_connect_error("连接超时（5分钟）"))
            except Exception as e:
                # 在主线程中调用连接失败回调
                self.root.after(0, lambda: self._on_connect_error(str(e)))

        # 在后台线程中运行异步函数
        self.run_async(do_connect())

    # 连接成功回调
    def _on_connected(self):
        """连接成功回调"""
        # 更新连接状态
        self.connected = True
        # 更新状态标签，显示已连接
        self.lbl_status.configure(text="状态: ● 已连接", text_color="green")
        # 禁用连接按钮并更改文本
        self.btn_connect.configure(state="disabled", text="已连接")

        # 启用其他操作按钮
        self.btn_harvest.configure(state="normal")
        self.btn_filter.configure(state="normal")
        self.btn_select_all.configure(state="normal")
        self.btn_move.configure(state="normal")
        self.btn_next_hero.configure(state="normal")
        self.btn_consumables_to_group.configure(state="normal")
        self.btn_pieces_to_group.configure(state="normal")
        self.btn_group_items_to_treasury.configure(state="normal")
        self.btn_auto_sell.configure(state="normal")
        self.btn_auto_sell_all.configure(state="normal")
        self.btn_flush_sellable.configure(state="normal")
        self.btn_schedule.configure(state="normal")
        self.btn_sell_monitor.configure(state="normal")
        self.btn_sell_clear.configure(state="normal")
        self.btn_sell_export.configure(state="normal")

        # 记录连接成功的日志
        self.log("INFO", "连接成功!")

        # 连接后自动启动卖出记录监听
        self.start_sell_monitor_ui()
        # 把已采集的可卖物品加载进清单框显示
        self._load_sold_list()

    # 连接失败回调
    def _on_connect_error(self, error):
        """连接失败回调"""
        # 重新启用连接按钮
        self.btn_connect.configure(state="normal")
        # 记录连接失败的日志
        self.log("ERROR", f"连接失败: {error}")

    # ===== 收菜功能 =====
    # 开始收菜
    def start_harvest(self):
        """开始收菜"""
        # 记录开始收菜的日志
        self.log("INFO", "开始收菜...")
        # 禁用所有操作按钮
        self._set_buttons_enabled(False)

        # 定义异步收菜函数
        async def do_harvest():
            try:
                # 每次收菜都重新连接，避免长时间未操作导致网页会话断开
                self.log("INFO", "正在连接浏览器...")
                # 【防内存泄漏】先关闭上一次的自动化对象：async_playwright().start()
                # 会派生一个 Node.js 驱动子进程，若不调用 close()→playwright.stop()，
                # 旧进程会一直挂在后台，多次定时运行后 Node 进程堆积导致内存暴涨。
                if self.automation:
                    try:
                        await self.automation.close()
                    except Exception:
                        pass
                self.automation = WoDAutomation(log_callback=self.log, auto_login=True)
                await self.automation.connect()

                # 处理所有英雄
                await self.automation.process_all_heroes()
                # 在主线程中调用收菜完成回调
                self.root.after(0, lambda: self._on_harvest_complete())
            # 如果出现异常
            except Exception as e:
                # 先捕获错误消息，避免 lambda 作用域问题
                error_msg = str(e)
                # 在主线程中调用收菜出错回调
                self.root.after(0, lambda: self._on_harvest_error(error_msg))

        # 在后台线程中运行异步函数
        self.run_async(do_harvest())

    # 收菜完成回调
    def _on_harvest_complete(self):
        """收菜完成回调"""
        # 重新启用所有操作按钮
        self._set_buttons_enabled(True)
        # 记录收菜完成的日志
        self.log("INFO", "收菜完成!")
        # 收菜会重建 automation，收完后重启卖出记录监听
        self.start_sell_monitor_ui()

    # 收菜出错回调
    def _on_harvest_error(self, error):
        """收菜出错回调"""
        # 重新启用所有操作按钮
        self._set_buttons_enabled(True)
        # 记录收菜出错的日志
        self.log("ERROR", f"收菜出错: {error}")
        # 收菜会重建 automation，出错后也重启卖出记录监听
        self.start_sell_monitor_ui()

    # ===== 手动操作 =====
    # 手动筛选耗材
    def manual_filter(self):
        """手动筛选耗材"""
        # 记录筛选耗材的日志
        self.log("INFO", "筛选耗材...")
        # 在后台线程中运行筛选耗材
        self.run_async(self.automation.filter_seconds())

    # 手动全选
    def manual_select_all(self):
        """手动全选"""
        # 记录全选物品的日志
        self.log("INFO", "全选物品...")
        # 在后台线程中运行全选
        self.run_async(self._manual_select_only())

    # 只执行全选，不移入仓库
    async def _manual_select_only(self):
        """只执行全选，不移入仓库"""
        try:
            # 调用 scheduler 的全选方法
            await self.automation._click_first_checkbox()
        # 如果出现异常
        except Exception as e:
            # 记录全选失败的日志
            self.log("ERROR", f"全选失败: {e}")

    # 手动移入仓库
    def manual_move(self):
        """手动移入仓库"""
        # 记录移入仓库的日志
        self.log("INFO", "移入仓库...")
        # 在后台线程中运行移入仓库（耗材→团队仓库）
        self.run_async(self.automation.move_to_warehouse("go_group_2", "团队仓库"))

    # ===== 一键批量操作（筛选+多轮移动，执行时间可能较长） =====
    # 一键：当前英雄仓库的耗材全部移入团队仓库
    def manual_consumables_to_group(self):
        """一键：仓库耗材全部入团仓"""
        self._run_onekey(
            self.automation.move_consumables_to_group2, "一键耗材入团仓"
        )

    # 一键：当前英雄仓库的镶嵌材料全部移入团队仓库
    def manual_pieces_to_group(self):
        """一键：镶嵌材料全部入团仓"""
        self._run_onekey(
            self.automation.move_pieces_to_group2, "一键镶嵌入团仓"
        )

    # 一键：当前英雄仓库的团队物品全部移入宝库
    def manual_group_items_to_treasury(self):
        """一键：团队物品全部入宝库"""
        self._run_onekey(
            self.automation.move_group_items_to_treasury, "一键团队物品入宝库"
        )

    # 一键操作通用执行器：禁用按钮 → 后台执行 → 恢复按钮
    def _run_onekey(self, coro_factory, title):
        """一键操作通用执行器

        coro_factory: 无参可调用，返回待执行的协程（每次调用生成新协程）
        title: 日志显示的操作名
        """
        # 记录日志并禁用所有操作按钮（多轮移动，执行时间可能较长）
        self.log("INFO", f"{title}开始...")
        self._set_buttons_enabled(False)

        # 定义异步任务
        async def do_onekey():
            try:
                # 执行一键操作（重置筛选 → 筛选 → 多轮移入 → 恢复页面）
                await coro_factory()
                # 在主线程中调用完成回调
                self.root.after(0, lambda: self._on_onekey_complete(title))
            # 如果出现异常
            except Exception as e:
                # 先捕获错误消息，避免 lambda 作用域问题
                error_msg = str(e)
                # 在主线程中调用出错回调
                self.root.after(0, lambda: self._on_onekey_error(title, error_msg))

        # 在后台线程中运行异步函数
        self.run_async(do_onekey())

    # 一键操作完成回调
    def _on_onekey_complete(self, title):
        """一键操作完成回调"""
        # 重新启用所有操作按钮
        self._set_buttons_enabled(True)
        # 记录完成日志
        self.log("INFO", f"{title}完成!")

    # 一键操作出错回调
    def _on_onekey_error(self, title, error):
        """一键操作出错回调"""
        # 重新启用所有操作按钮
        self._set_buttons_enabled(True)
        # 记录出错日志
        self.log("ERROR", f"{title}出错: {error}")

    # 手动切换英雄
    def manual_next_hero(self):
        """手动切换英雄"""
        # 记录切换英雄的日志
        self.log("INFO", "切换英雄...")
        # 在后台线程中运行切换英雄
        self.run_async(self.automation.switch_to_next_hero())

    # ===== 自动出售 =====
    # 一键：按 sellable-items.js 清单圈选并出售当前英雄的可卖物品
    def manual_auto_sell(self):
        """一键：自动出售当前英雄的可卖物品"""
        self._run_onekey(
            self.automation.sell_sellable_items, "自动出售"
        )

    # 一键：轮询所有英雄，逐个出售可卖物品
    def manual_auto_sell_all(self):
        """一键：轮询所有英雄自动出售可卖物品（耗时较长）"""
        self._run_onekey(
            self.automation.sell_all_heroes, "轮询所有英雄出售"
        )

    # 一键：刷新可卖清单（合并浏览器缓冲 → 写入 sellable-items.js → 清空缓冲）
    def manual_flush_sellable(self):
        """一键：刷新可卖物品清单"""
        self.log("INFO", "刷新清单...")
        self.btn_flush_sellable.configure(state="disabled")

        # 定义异步刷新函数
        async def do_flush():
            try:
                new_count, total = await self.automation.flush_sold_buffer()
                # 回主线程展示结果
                self.root.after(0, lambda: self._on_flush_complete(new_count, total))
            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda: self._on_flush_error(error_msg))

        self.run_async(do_flush())

    # 刷新清单完成回调
    def _on_flush_complete(self, new_count, total):
        """刷新清单完成：日志输出新增与总数"""
        self.btn_flush_sellable.configure(state="normal")
        if new_count:
            self.log("INFO", f"刷新清单完成：新增 {new_count} 条，清单共 {total} 条")
        else:
            self.log("INFO", f"刷新清单完成：缓冲无新物品，清单共 {total} 条")

    # 刷新清单出错回调
    def _on_flush_error(self, error):
        """刷新清单出错"""
        self.btn_flush_sellable.configure(state="normal")
        self.log("ERROR", f"刷新清单失败: {error}")

    # ===== 定时任务 =====
    # 切换定时任务状态
    def toggle_schedule(self):
        """切换定时任务状态"""
        # 如果定时任务正在运行
        if self.scheduler_running:
            # 停止定时任务
            self.stop_schedule()
        else:
            # 启动定时任务
            self.start_schedule()

    # 启动定时任务
    def start_schedule(self):
        """启动定时任务"""
        try:
            # 获取用户输入的间隔时间
            interval = float(self.interval_entry.get())
            # 检查间隔是否有效
            if interval <= 0:
                # 间隔必须大于0，抛出异常
                raise ValueError("间隔必须大于0")

            # 更新定时任务状态为运行中
            self.scheduler_running = True
            # 更新按钮文本为"停止定时"
            self.btn_schedule.configure(text="停止定时")
            # 记录定时任务启动的日志
            self.log("INFO", f"定时任务已启动，间隔 {interval} 分钟")

            # 计算并显示下次执行时间
            self._update_next_run_time(interval)

            # 立即执行一次收菜
            self.start_harvest()

            # 设置下一次执行的定时器（分钟转换为毫秒）
            self._schedule_next(int(interval * 60 * 1000))

        # 如果出现值错误异常
        except ValueError as e:
            # 记录无效间隔时间的日志
            self.log("ERROR", f"无效的间隔时间: {e}")

    # 设置下一次执行
    def _schedule_next(self, interval_ms):
        """设置下一次执行"""
        # 如果定时任务已停止
        if not self.scheduler_running:
            # 直接返回
            return

        # 设置定时器，在指定时间后触发
        self.scheduler_timer = self.root.after(
            interval_ms,  # 间隔时间（毫秒）
            lambda: self._on_schedule_trigger()  # 触发时调用的函数
        )

    # 定时器触发
    def _on_schedule_trigger(self):
        """定时器触发"""
        # 如果定时任务仍在运行
        if self.scheduler_running:
            # 执行收菜
            self.start_harvest()

            # 重新设置下一次定时器
            try:
                # 获取用户输入的间隔时间
                interval = float(self.interval_entry.get())
                # 计算并显示下次执行时间
                self._update_next_run_time(interval)
                # 设置下一次定时器（分钟转毫秒）
                self._schedule_next(int(interval * 60 * 1000))
            # 如果出现异常
            except:
                # 停止定时任务
                self.stop_schedule()

    # 更新下次执行时间显示
    def _update_next_run_time(self, interval_minutes):
        """更新下次执行时间显示"""
        import datetime
        next_time = datetime.datetime.now() + datetime.timedelta(minutes=interval_minutes)
        # 格式化时间为 HH:MM:SS
        time_str = next_time.strftime("%H:%M:%S")
        # 更新标签
        self.lbl_next_run.configure(text=f"下次执行: {time_str}")

    # 停止定时任务
    def stop_schedule(self):
        """停止定时任务"""
        # 更新定时任务状态为停止
        self.scheduler_running = False
        # 如果有定时器
        if self.scheduler_timer:
            # 取消定时器
            self.root.after_cancel(self.scheduler_timer)
            # 清空定时器变量
            self.scheduler_timer = None

        # 清空下次执行时间
        self.next_run_time = None
        self.lbl_next_run.configure(text="下次执行: --")

        # 更新按钮文本为"启动定时"
        self.btn_schedule.configure(text="启动定时")
        # 记录定时任务停止的日志
        self.log("INFO", "定时任务已停止")

    # ===== 卖出记录 =====
    # 切换卖出记录监听
    def toggle_sell_monitor(self):
        """切换卖出记录监听状态"""
        if self.sell_monitoring:
            self.log("INFO", "停止记录卖出物品...")
            self.sell_monitoring = False
            self.btn_sell_monitor.configure(text="开始记录")
            self.run_async(self.automation.stop_sell_monitor())
        else:
            self.log("INFO", "开始记录卖出物品...")
            self.start_sell_monitor_ui()

    # 启动卖出记录（可重复调用：automation 层有去重，自动/手动都走这里）
    def start_sell_monitor_ui(self):
        """启动卖出记录监听（连接后自动调用，也可手动触发）"""
        if not self.automation:
            return
        self.sell_monitoring = True
        self.btn_sell_monitor.configure(text="停止记录")
        self.automation.sold_items_callback = self._on_sold_items
        self.run_async(self.automation.start_sell_monitor())

    # 清单框只显示本次会话「新增」的物品（清单文件里已有的不显示）
    def _load_sold_list(self):
        """会话开始时清空清单框：只显示后续新增的物品"""
        self.sold_text.delete("1.0", "end")

    # 卖出记录回调（在后台线程触发，用 root.after 回主线程更新 UI）
    def _on_sold_items(self, new_names):
        """收到新增卖出的物品名，回主线程更新清单框"""
        self.root.after(0, lambda: self._append_sold_items(new_names))

    # 在主线程把新增名字插入清单框
    def _append_sold_items(self, new_names):
        """在主线程把新增名字插入清单框"""
        for name in new_names:
            self.sold_text.insert("end", name + "\n")
        self.sold_text.see("end")

    # 导出可卖物品清单
    def export_sold(self):
        """导出可卖物品清单到 txt 文件"""
        try:
            names = self.automation._read_existing_names() if self.automation else []
        except Exception:
            names = []
        if not names:
            self.log("INFO", "可卖物品清单为空，无内容导出")
            return
        # 弹出文件保存对话框
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            title="导出可卖物品清单",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            initialfile="可卖物品.txt",
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(names) + "\n")
        self.log("INFO", f"已导出 {len(names)} 个可卖物品到 {path}")

    # 清空卖出清单
    def clear_sold(self):
        """清空卖出清单（显示框 + localStorage + JS 文件）"""
        self.sold_text.delete("1.0", "end")
        if self.automation:
            self.run_async(self._clear_sold_async())

    async def _clear_sold_async(self):
        """清空 localStorage 与 JS 数据文件"""
        try:
            if self.automation.page:
                await self.automation.page.evaluate(f"localStorage.removeItem('{SELL_STORAGE_KEY}')")
            self.automation._clear_sell_js()
            self.log("INFO", "已清空卖出清单")
        except Exception as e:
            self.log("ERROR", f"清空卖出清单失败: {e}")

    # ===== 辅助方法 =====
    # 设置按钮状态
    def _set_buttons_enabled(self, enabled):
        """设置按钮状态"""
        # 根据是否启用决定状态
        state = "normal" if enabled else "disabled"
        # 更新所有操作按钮的状态（不包括定时按钮，因为收菜时仍需能停止定时）
        self.btn_harvest.configure(state=state)
        self.btn_filter.configure(state=state)
        self.btn_select_all.configure(state=state)
        self.btn_move.configure(state=state)
        self.btn_next_hero.configure(state=state)
        self.btn_consumables_to_group.configure(state=state)
        self.btn_pieces_to_group.configure(state=state)
        self.btn_group_items_to_treasury.configure(state=state)
        self.btn_auto_sell.configure(state=state)
        self.btn_auto_sell_all.configure(state=state)
        self.btn_flush_sellable.configure(state=state)
        # 注意：不修改 btn_schedule 的状态，允许收菜时仍能停止定时任务

    # 运行 GUI
    def run(self):
        """运行 GUI"""
        # 启动主窗口的消息循环
        self.root.mainloop()


# 主函数
def main():
    """主函数"""
    # 创建 GUI 应用
    app = WoDGUI()
    # 运行应用
    app.run()


# 程序入口
if __name__ == "__main__":
    # 调用主函数
    main()
