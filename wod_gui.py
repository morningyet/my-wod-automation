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
        row2.pack(fill="x", padx=10, pady=(2, 10))

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
        self.interval_entry = ctk.CTkEntry(control_row, width=50, placeholder_text="4")
        self.interval_entry.insert(0, "4")
        self.interval_entry.pack(side="left", padx=(0, 3))
        ctk.CTkLabel(control_row, text="小时").pack(side="left")

        # 创建下次执行时间标签
        self.lbl_next_run = ctk.CTkLabel(
            schedule_frame,
            text="下次执行: --",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.lbl_next_run.pack(pady=(0, 10))

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
                # 创建自动化对象，传入日志回调和自动登录标志
                self.automation = WoDAutomation(log_callback=self.log, auto_login=self.auto_login)
                # 执行连接
                await self.automation.connect()
                # 在主线程中调用连接成功回调
                self.root.after(0, self._on_connected)
            # 如果出现异常
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
        self.btn_schedule.configure(state="normal")

        # 记录连接成功的日志
        self.log("INFO", "连接成功!")

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
                # 检查页面是否仍然可用
                page_alive = False
                try:
                    page_alive = (
                        self.automation.page is not None
                        and not self.automation.page.is_closed()
                        and self.automation.browser is not None
                        and self.automation.browser.is_connected()
                    )
                except Exception:
                    page_alive = False

                # 页面已断开，重新走完整连接流程
                if not page_alive:
                    self.log("WARNING", "浏览器连接已断开，正在重新连接...")
                    self.automation = WoDAutomation(log_callback=self.log, auto_login=True)
                    await self.automation.connect()
                    self.log("INFO", "重新连接成功")

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

    # 收菜出错回调
    def _on_harvest_error(self, error):
        """收菜出错回调"""
        # 重新启用所有操作按钮
        self._set_buttons_enabled(True)
        # 记录收菜出错的日志
        self.log("ERROR", f"收菜出错: {error}")

    # ===== 手动操作 =====
    # 手动筛选耗材
    def manual_filter(self):
        """手动筛选耗材"""
        # 记录筛选耗材的日志
        self.log("INFO", "筛选耗材...")
        # 在后台线程中运行筛选耗材
        self.run_async(self.automation.filter_consumables())

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
        # 在后台线程中运行移入仓库
        self.run_async(self.automation.select_all_and_move_to_warehouse())

    # 手动切换英雄
    def manual_next_hero(self):
        """手动切换英雄"""
        # 记录切换英雄的日志
        self.log("INFO", "切换英雄...")
        # 在后台线程中运行切换英雄
        self.run_async(self.automation.switch_to_next_hero())

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
            self.log("INFO", f"定时任务已启动，间隔 {interval} 小时")

            # 计算并显示下次执行时间
            self._update_next_run_time(interval)

            # 立即执行一次收菜
            self.start_harvest()

            # 设置下一次执行的定时器（将小时转换为毫秒，转为整数）
            self._schedule_next(int(interval * 3600 * 1000))

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
                # 设置下一次定时器（转为整数）
                self._schedule_next(int(interval * 3600 * 1000))
            # 如果出现异常
            except:
                # 停止定时任务
                self.stop_schedule()

    # 更新下次执行时间显示
    def _update_next_run_time(self, interval_hours):
        """更新下次执行时间显示"""
        import datetime
        # 计算下次执行时间
        next_time = datetime.datetime.now() + datetime.timedelta(hours=interval_hours)
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
