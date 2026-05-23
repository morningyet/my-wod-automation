
翻墙小工具--一般用不到
```bash
魔法云 https://cf02.magic.lat/#/register?code=MZnq09Se
```

安装nvm  --直接装node也不是不行
```shell
# linux 环境  一行搞定   注意：执行后重启当前的shell/bash
bash -c "$(curl -fsSL https://gitee.com/RubyMetric/nvm-cn/raw/main/install.sh)"

# win 环境，先安装，再配置国内镜像
https://gh-proxy.org/https://github.com/coreybutler/nvm-windows/releases/download/1.2.2/nvm-setup.zip
#这两行放到 setting 安装目录里  默认 C:\Users\Administrator\Downloads\nvm-setup.zip
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


一些工具：
```
7-zip： 
https://gitee.com/gitsharp/7zip/releases/tag/26.00

icu.dll：
https://www.dll-files.com/download/8dfbaf2e92aac3d4d94ee60406230ed5/icu.dll.html?c=YnhaTE5wLzRDK2ZWbElWbElwUWFJZz09

git-for-win：
https://registry.npmmirror.com/-/binary/git-for-windows/v2.51.0.windows.1/Git-2.51.0-64-bit.exe

ndd: 
https://gitee.com/cxasm/notepad--
```