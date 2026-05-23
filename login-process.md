# 登录操作流程

## 自动登录逻辑

### 勾选"自动登录"
连接浏览器后直接执行登录操作。

### 未勾选"自动登录"
连接浏览器后，检查当前登录状态，仅报告状态不执行登录。

## 登录操作步骤

**注意**: 网页加载较慢，每步操作后需等待页面完全加载完成。

### 步骤 1: 遍历标签页
```bash
playwright-cli tab-list
```
**判断**: 找到 WoD 所在的标签页索引

### 步骤 2: 切换到 WoD 标签页
```bash
playwright-cli tab-select <索引>
```
**判断**: 标签页变为 (current) 状态

### 步骤 3: 检查是否有登录表单
```bash
# 检查文本输入框
document.querySelectorAll('input[type="text"]').length > 0

# 检查密码输入框
document.querySelectorAll('input[type="password"]').length > 0

# 检查提交按钮
document.querySelectorAll('input[type="submit"], button[type="submit"]').length > 0
```
**判断**: 三个条件都为 true = 存在登录表单

### 步骤 4: 检查输入框是否有自动填充值
```bash
# 获取用户名
document.querySelector('input[type="text"]').value

# 获取密码
document.querySelector('input[type="password"]').value
```

#### 情况 A: 有自动填充值
直接执行步骤 5

#### 情况 B: 无自动填充值
读取 `.env` 文件，填入用户名和密码：
```bash
# 填入用户名
document.querySelector('input[type="text"]').value = "<用户名>"

# 填入密码
document.querySelector('input[type="password"]').value = "<密码>"
```

### 步骤 5: 执行登录
```bash
document.querySelector('input[type="submit"]').click()
```

### 步骤 6: 验证登录成功
等待页面加载完成后检查：
- 页面标题是否包含 "World of Dungeons"
- URL 是否不再包含 "login.php"

## 代码实现要点

1. **等待页面加载**: 每步操作后等待 `networkidle` 状态
2. **延迟等待**: 国外网站加载慢，额外等待 2-3 秒
3. **回退机制**: 自动填充失败时才读取 .env 文件
