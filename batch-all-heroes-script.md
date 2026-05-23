# WoD 批量操作所有英雄的耗材物品

## 完整自动化脚本

```bash
#!/bin/bash
# 批量移动所有英雄的耗材物品到团队仓库

echo "=== WoD 批量移动耗材物品 ==="
echo "开始时间: $(date)"

# 记录第一个英雄名称（用于检测循环结束）
first_hero=$(playwright-cli eval "document.querySelector('h1').textContent")
echo "第一个英雄: $first_hero"

# 计数器
count=0
skipped=0

# 开始循环
while true; do
  current_hero=$(playwright-cli eval "document.querySelector('h1').textContent")
  echo "----------------------------------------"
  echo "当前英雄: $current_hero"

  # 检查是否回到第一个英雄（循环结束）
  if [ "$count" -gt 0 ] && [ "$current_hero" = "$first_hero" ]; then
    echo "========================================"
    echo "循环结束！已回到第一个英雄"
    echo "处理英雄数: $count"
    echo "跳过英雄数: $skipped"
    echo "结束时间: $(date)"
    break
  fi

  # 检查是否为导师类英雄（无仓库）
  is_mentor=$(playwright-cli eval "window.location.href.includes('reason=mentor')")
  if [ "$is_mentor" = "true" ]; then
    echo "→ 导师类英雄，无仓库，跳过"
    playwright-cli click "img[alt=\"切换到下一个活跃的英雄\"]"
    ((skipped++))
    sleep 2
    continue
  fi

  # 执行批量移动操作
  echo "→ 开始批量移动耗材..."

  # 1. 筛选耗材
  playwright-cli click "input[name=\"item_3usage_item\"][value=\"yes\"]"
  sleep 1

  # 2. 点击搜索
  playwright-cli click "text=开始搜索"
  sleep 2

  # 3. 全选物品
  playwright-cli eval "document.querySelector('thead input[type=\"checkbox\"]').click()"
  sleep 1

  # 4. 选择团队仓库
  playwright-cli select "thead select[name=\"dummy\"]" "go_group_2"
  sleep 1

  # 5. 应用改动
  playwright-cli eval "document.querySelector('.layout_left input[value=\"应用改动\"]').click()"
  sleep 2

  echo "✓ 完成"

  # 切换到下一个英雄
  playwright-cli click "img[alt=\"切换到下一个活跃的英雄\"]"
  ((count++))

  # 等待页面加载
  sleep 2
done

echo "=== 全部完成 ==="
```

## 循环检测逻辑说明

### 为什么检测重名英雄？

WoD 的英雄切换是**循环**的：
- 英雄 A → 英雄 B → 英雄 C → ... → 英雄 A

当切换回第一个英雄时，说明：
1. 所有英雄都已处理过
2. 循环已完整执行一遍

### 检测条件

```bash
# 必须满足两个条件：
# 1. count > 0（至少处理过一个英雄）
# 2. 当前英雄 = 第一个英雄（回到起点）

if [ "$count" -gt 0 ] && [ "$current_hero" = "$first_hero" ]; then
  break  # 结束循环
fi
```

## 特殊情况处理

### 1. 导师类英雄

导师类英雄的特点：
- URL 包含 `reason=mentor`
- 没有仓库栏目
- 无法进行物品操作

处理方式：**直接跳过**

```bash
if [ "$is_mentor" = "true" ]; then
  echo "→ 导师类英雄，跳过"
  playwright-cli click "img[alt=\"切换到下一个活跃的英雄\"]"
  continue
fi
```

### 2. 无耗材物品的英雄

有些英雄可能没有耗材物品：
- 搜索结果为空
- 不影响操作流程

处理方式：**继续执行，无需特殊处理**

### 3. 英雄重名

如果账号有多个同名英雄：
- 靠页面标题无法区分
- 可以通过 Hero ID 区分

```bash
# 获取 Hero ID
hero_id=$(playwright-cli eval "new URLSearchParams(window.location.search).get('session_hero_id')")
```

## 使用方法

### 1. 保存脚本

将脚本保存为 `batch-all-heroes.sh`

### 2. 运行脚本

```bash
# 确保已连接到 Edge
playwright-cli attach --cdp=http://localhost:9222

# 运行脚本
bash batch-all-heroes.sh
```

### 3. 监控进度

脚本会实时输出：
- 当前处理的英雄
- 跳过的英雄
- 完成数量

## 输出示例

```
=== WoD 批量移动耗材物品 ===
开始时间: 2026-05-20 10:00:00
第一个英雄: aa爱故乡的夏: 仓库
----------------------------------------
当前英雄: aa爱故乡的夏: 仓库
→ 开始批量移动耗材...
✓ 完成
----------------------------------------
当前英雄: BOOM~: 仓库
→ 开始批量移动耗材...
✓ 完成
----------------------------------------
当前英雄: 导师英雄
→ 导师类英雄，无仓库，跳过
----------------------------------------
...
========================================
循环结束！已回到第一个英雄
处理英雄数: 7
跳过英雄数: 1
结束时间: 2026-05-20 10:15:30
=== 全部完成 ===
```

## 注意事项

1. **首次运行**：确保第一个英雄有仓库页面
2. **网络延迟**：适当调整 sleep 时间
3. **异常处理**：如页面加载失败，需手动重试
4. **Hero ID 变化**：切换英雄后 session_hero_id 会变化

## 更新日期

- 2026-05-20: 初始版本，添加循环检测和导师英雄处理
