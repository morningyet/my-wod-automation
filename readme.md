  0. 项目依赖安装
  pip install -r requirements.txt 
  ```bash
  # 在浏览器图标-目标后 添加启动命令
  --remote-debugging-port=9222
  
  # 验证 localhost:9222/json 报错就是没生效
```
  
  1. 连接浏览器

    - 连接到本地 Edge 浏览器调试端口 (9222)
    - 查找或创建 WoD 游戏页面
  2. 登录检测

    - 自动检测是否已登录
    - 未登录时使用 .env 中的账号密码自动登录
  3. 循环处理所有英雄

    - 获取当前英雄名称
    - 跳过导师英雄 (URL 中包含 reason=mentor)
    - 筛选耗材物品 - 勾选"只显示耗材"
    - 全选物品 - 点击第一个复选框
    - 移动到团队仓库 - 选择"go_group_2"并应用改动
    - 切换到下一个英雄 - 点击"切换到下一个活跃的英雄"
    - 重复直到回到起点
  4. 运行模式

    - python wod_scheduler.py - 定时模式，每 4 小时执行一次
    - python wod_scheduler.py --once - 立即执行一次

  依赖

  - Playwright (浏览器自动化)
  - 需要手动启动 Edge 并开启调试端口: msedge.exe --remote-debugging-port=9222