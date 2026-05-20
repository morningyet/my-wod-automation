
翻墙小工具--一般用不到
```bash
魔法云 https://cf02.magic.lat/#/register?code=MZnq09Se
```

安装nvm
```shell
# linux 环境  一行搞定
bash -c "$(curl -fsSL https://gitee.com/RubyMetric/nvm-cn/raw/main/install.sh)"

# win 环境，先安装，再配置国内镜像
https://gh-proxy.org/https://github.com/coreybutler/nvm-windows/releases/download/1.2.2/nvm-setup.zip
#这两行放到 setting 安装目录里
node_mirror: https://npmmirror.com/mirrors/node/ 
npm_mirror: https://npmmirror.com/mirrors/npm/
```

验证安装 NVM 是否安装成功：
```shell
nvm --version
```

 安装 node
```shell
# 重要
nvm install 22
nvm use 22
node -v 
npm -v
```

安装 claude-code
```shell
npm install -g @anthropic-ai/claude-code
```

安装glm工具（如果你用智普模型）
```bash
# 进入命令行界面，执行如下运行 Coding Tool Helper 
npx @z_ai/coding-helper
```

如果不安装glm工具，baseUrl改为这个（glm)
```shell
https://open.bigmodel.cn/api/anthropic
```

ccwitch
```shell
# 这是linux 的 ，win可以找界面版的

curl -fsSL https://fastly.jsdelivr.net/gh/DoBestone/cc-switch-cli@main/install.sh | bash
or
curl -fsSL https://cdn.gh-proxy.org/raw.githubusercontent.com/DoBestone/cc-switch-cli/main/install.sh | bash
```

安装一些常用skill
```shell
npx skills add https://github.com/anthropics/skills --skill docx
npx skills add https://github.com/anthropics/skills --skill pdf
npx skills add https://github.com/anthropics/skills --skill pptx
npx skills add https://github.com/anthropics/skills --skill xlsx
npx skills add https://github.com/nextlevelbuilder/ui-ux-pro-max-skill --skill ui-ux-pro-max
npx skills add https://github.com/op7418/Humanizer-zh.git
npx skills add https://github.com/anthropics/skills --skill skill-creator
npx skills add https://github.com/vercel-labs/skills --skill find-skills
npx skills add vercel-labs/agent-browser --skill agent-browser
```


浏览器edge自动化
```bash
# 在浏览器图标-目标后 添加启动命令
 --remote-debugging-port=9222
 
# 验证 localhost:9222/json 报错就是没生效
```