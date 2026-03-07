# Pydoll CF WAF Bypasser Skills

> 🛡️ GitHub Copilot / Claude 技能包 —— 教会 AI 编程助手使用 [Pydoll](https://github.com/autoscrape-labs/pydoll) 进行隐蔽浏览器自动化，**自动绕过 Cloudflare WAF、Turnstile 验证码及其他人机验证系统**。

## 这是什么？

这是一个 **Copilot Skills 扩展包**（也兼容 Claude Code），当你在 VS Code 中使用 GitHub Copilot Chat 或 Claude 编程助手时，它会自动注入 Pydoll 浏览器自动化的专业知识，让 AI 能够：

- 🔓 编写绕过 Cloudflare Turnstile / Managed Challenge 的脚本
- 🕵️ 生成反爬虫检测的隐蔽浏览器配置
- 🤖 使用人性化鼠标移动（贝塞尔曲线 + Fitts 定律）和键盘输入
- 🌐 处理 Shadow DOM、并发爬取、网络拦截等高级场景
- 📦 直接输出可用 `uv run` 运行的独立脚本（无需手动安装依赖）

## 快速开始

### 1. 安装到你的项目

将 `.claude/` 目录复制到你的项目根目录：

```bash
# 克隆仓库
git clone https://github.com/baidu/pydoll-cf-waf-bypasser-skills.git

# 复制 skills 目录到你的项目
cp -r pydoll-cf-waf-bypasser-skills/.claude /path/to/your/project/
```

或者作为 Git Submodule 引入：

```bash
cd /path/to/your/project
git submodule add https://github.com/baidu/pydoll-cf-waf-bypasser-skills.git .copilot-skills/pydoll
cp -r .copilot-skills/pydoll/.claude .claude
```

### 2. 在 VS Code 中使用

安装后，在 Copilot Chat 中直接提问即可触发技能：

```
帮我写一个绕过 Cloudflare 的爬虫脚本，爬取 https://example.com 的文章列表
```

```
用 pydoll 访问被 WAF 保护的网站并截图
```

```
写一个并发爬虫，同时爬取 5 个受 Cloudflare 保护的页面
```

AI 助手会自动引用技能包中的知识，生成正确的 Pydoll 代码。

## 项目结构

```
.claude/
└── skills/
    └── pydoll-browser/
        ├── SKILL.md              # 核心技能定义（API 参考 + 最佳实践）
        ├── knowledge/
        │   └── anti_detection.md # 反检测深度指南
        ├── examples/
        │   ├── bypass_cloudflare.py         # Cloudflare Turnstile 绕过
        │   ├── bypass_managed_challenge.py  # Managed Challenge 绕过（需 xvfb）
        │   ├── stealth_scraper.py           # 隐蔽爬虫
        │   ├── concurrent_scraper.py        # 并发爬取
        │   └── screenshot.py                # 截图工具
        └── scripts/
            └── templates.py      # 8 个可复用脚本模板
```

## 技能覆盖范围

### WAF / 人机验证绕过

| WAF 系统 | 支持状态 | 备注 |
|----------|----------|------|
| Cloudflare Turnstile | ✅ 完全支持 | 无头模式可用，内置自动处理 |
| Cloudflare JS Challenge | ✅ 支持 | 自动执行 JS 挑战 |
| Cloudflare Managed Challenge | ✅ 已验证 | 需 `headless=False` + xvfb |
| DataDome | ⚠️ 部分支持 | 需高质量代理 + 完整指纹 |
| PerimeterX | ⚠️ 部分支持 | 需随机化行为模式 |
| Akamai Bot Manager | ⚠️ 部分支持 | 建议使用轮换代理 |

### 核心能力

| 功能 | 说明 |
|------|------|
| 零 WebDriver 依赖 | 直接 CDP 连接，`navigator.webdriver` 为 `undefined` |
| 人性化鼠标 | 贝塞尔曲线路径 + Fitts 定律计时 + 生理震颤 |
| 人性化键盘 | 随机延迟 + 打字错误 + 思考停顿 |
| Shadow DOM | 完整 `closed shadow root` 访问 |
| 网络拦截 | 阻止资源加载 / 请求修改 / HAR 录制 |
| 混合自动化 | UI 登录 + API 调用（携带 Cookie） |
| 并发爬取 | 多标签页 + 隔离浏览器上下文 |
| 反检测指纹 | 浏览器历史伪造 / WebRTC 保护 / 代理支持 |

## 运行示例脚本

所有示例使用 [uv](https://docs.astral.sh/uv/) 内联脚本依赖，无需手动安装包：

```bash
# 安装 uv（如未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 绕过 Cloudflare Turnstile
uv run .claude/skills/pydoll-browser/examples/bypass_cloudflare.py https://nowsecure.nl

# 绕过 Managed Challenge（需 xvfb，适用于服务器环境）
xvfb-run -a uv run .claude/skills/pydoll-browser/examples/bypass_managed_challenge.py https://example.com

# 隐蔽爬虫
uv run .claude/skills/pydoll-browser/examples/stealth_scraper.py https://example.com

# 并发爬取
uv run .claude/skills/pydoll-browser/examples/concurrent_scraper.py https://a.com https://b.com

# 截图
xvfb-run -a uv run .claude/skills/pydoll-browser/examples/screenshot.py https://example.com

# 查看所有可用模板
uv run .claude/skills/pydoll-browser/scripts/templates.py list
```

## 模板列表

`templates.py` 提供 8 个即拿即用的脚本模板：

| 模板名 | 用途 |
|--------|------|
| `basic_browser` | 基础浏览器配置 |
| `bypass_cloudflare` | Cloudflare WAF 绕过 |
| `web_scraping` | 网页数据爬取（带请求拦截） |
| `form_filling` | 表单填写（人性化输入） |
| `hybrid_automation` | 登录后 API 调用 |
| `screenshot` | 批量截图 |
| `concurrent_scraping` | 多标签页并发爬取 |
| `stealth_browser` | 完整反检测配置 |

获取模板代码：

```bash
uv run .claude/skills/pydoll-browser/scripts/templates.py bypass_cloudflare > my_script.py
uv run my_script.py
```

## 环境要求

- **Python** >= 3.10
- **Chrome / Chromium** 浏览器已安装
- **uv**（推荐）或 pip
- **xvfb**（仅服务器环境运行 `headless=False` 时需要）

### Docker / 服务器环境

```bash
# 安装依赖
apt-get update && apt-get install -y \
    google-chrome-stable \
    xvfb \
    fonts-noto-cjk

# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 参考资源

- [Pydoll GitHub](https://github.com/autoscrape-labs/pydoll)
- [Pydoll 文档](https://pydoll.tech/)
- [uv 文档](https://docs.astral.sh/uv/)
- [Copilot Skills 开发指南](https://docs.github.com/en/copilot/building-copilot-extensions)

## 许可证

MIT License

---

> ⚠️ **免责声明**：本项目仅供学习和合法用途。使用时请遵守目标网站的服务条款和 robots.txt，合理控制请求频率，不要对目标服务器造成过大压力。