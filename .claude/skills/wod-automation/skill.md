---
name: wod-automation
description: WoD (World of Dungeons) 游戏自动化操作 - 筛选耗材、批量移动、循环操作所有英雄
allowed-tools: Bash(playwright-cli:*) Bash(npx:*) Bash(npm:*)
---

# WoD 游戏自动化

这个 Skill 提供 World of Dungeons 游戏的自动化操作功能。

## 前置条件

确保 Edge 浏览器已启动远程调试：

```bash
powershell -Command "Stop-Process -Name msedge -Force -ErrorAction SilentlyContinue"
powershell -Command "Start-Process 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe' -ArgumentList '--remote-debugging-port=9222 --user-data-dir=C:\temp\edge-debug'"
playwright-cli attach --cdp=http://localhost:9222
```

## 可用功能

### 1. 筛选耗材物品

筛选当前英雄仓库中的耗材物品。

```bash
# 点击"耗材 - 是"
playwright-cli click "input[name=\"item_3usage_item\"][value=\"yes\"]"

# 点击"开始搜索"
playwright-cli click "text=开始搜索"
```

### 2. 批量移动到团队仓库

将筛选出的物品批量移动到团队仓库。

```bash
# 全选物品（勾选表头复选框）
playwright-cli eval "document.querySelector('thead input[type=\"checkbox\"]').click()"

# 选择团队仓库
playwright-cli select "thead select[name=\"dummy\"]" "go_group_2"

# 应用改动
playwright-cli eval "document.querySelector('.layout_left input[value=\"应用改动\"]').click()"
```

### 3. 切换英雄

切换到下一个活跃的英雄。

```bash
# 切换到下一个英雄
playwright-cli click "img[alt=\"切换到下一个活跃的英雄\"]"

# 获取当前英雄名称
playwright-cli eval "document.querySelector('h1').textContent"
```

### 4. 检测导师英雄

检测当前英雄是否为导师类（无仓库）。

```bash
# 返回 true 表示是导师英雄
playwright-cli eval "window.location.href.includes('reason=mentor')"
```

### 5. 循环操作所有英雄

批量处理所有英雄的耗材物品。

```bash
#!/bin/bash
# 记录第一个英雄
first_hero=$(playwright-cli eval "document.querySelector('h1').textContent")
count=0

while true; do
  current_hero=$(playwright-cli eval "document.querySelector('h1').textContent")

  # 检查循环结束
  if [ "$count" -gt 0 ] && [ "$current_hero" = "$first_hero" ]; then
    echo "循环结束，共处理 $count 个英雄"
    break
  fi

  # 检查导师英雄
  is_mentor=$(playwright-cli eval "window.location.href.includes('reason=mentor')")
  if [ "$is_mentor" = "true" ]; then
    echo "跳过导师英雄: $current_hero"
    playwright-cli click "img[alt=\"切换到下一个活跃的英雄\"]"
    sleep 2
    continue
  fi

  # 执行批量移动
  echo "处理英雄: $current_hero"
  playwright-cli click "input[name=\"item_3usage_item\"][value=\"yes\"]"
  sleep 1
  playwright-cli click "text=开始搜索"
  sleep 2
  playwright-cli eval "document.querySelector('thead input[type=\"checkbox\"]').click()"
  sleep 1
  playwright-cli select "thead select[name=\"dummy\"]" "go_group_2"
  sleep 1
  playwright-cli eval "document.querySelector('.layout_left input[value=\"应用改动\"]').click()"
  sleep 2

  # 切换英雄
  playwright-cli click "img[alt=\"切换到下一个活跃的英雄\"]"
  ((count++))
  sleep 2
done
```

## 位置选项说明

| 值 | 位置 |
|------|------|
| `go_lager` | 仓库 |
| `go_group_2` | 团队仓库 |
| `go_group` | 宝库 |
| `go_keller` | 贮藏室 |
| `go_tasche` | 口袋 |

## 使用示例

### 示例 1: 处理单个英雄的耗材

```
请帮我筛选当前英雄的耗材物品，并移动到团队仓库
```

### 示例 2: 处理所有英雄

```
请循环操作所有英雄，将耗材移动到团队仓库
```

### 示例 3: 切换英雄并查看

```
切换到下一个英雄，告诉我当前英雄的名字
```

## 注意事项

1. 确保 Edge 浏览器已启动远程调试
2. 导师类英雄会自动跳过
3. 循环会在回到第一个英雄时自动结束
4. 每次操作后需要等待页面加载完成

## 相关文档

项目中的详细文档：
- `consumable-filter-process.md` - 耗材筛选详细流程
- `bulk-move-process.md` - 批量移动详细流程
- `switch-hero-process.md` - 英雄切换详细流程
- `batch-all-heroes-script.md` - 完整批量操作脚本
