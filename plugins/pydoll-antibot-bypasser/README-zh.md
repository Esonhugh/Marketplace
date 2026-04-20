# Pydoll Antibot Bypasser

一个用于隐蔽浏览器自动化的 Claude Code / Ducc 技能插件，基于 [Pydoll](https://github.com/autoscrape-labs/pydoll) 构建，专门用于绕过 Cloudflare WAF、Turnstile CAPTCHA 及其他反机器人检测系统。

当你的 AI 编程助手遇到 WAF 保护的网站时，本技能会自动激活并生成正确的绕过代码，无需手动查阅文档。

## 为什么选择本插件？

传统浏览器自动化工具（Selenium、Puppeteer）很容易被检测到，因为它们会设置 `navigator.webdriver = true`。Pydoll 采用了根本不同的方案：

- **零 WebDriver 依赖** — 通过 WebSocket 直连 CDP，`navigator.webdriver` 保持 `undefined`
- **拟人化交互** — 贝塞尔曲线鼠标移动、打字错误模拟、生理性抖动
- **内置 Cloudflare 绕过** — 自动检测并解决 Shadow DOM 中的 Turnstile CAPTCHA
- **100% 异步** — 原生 `asyncio` 支持并发抓取

## WAF 绕过支持

| WAF / 反机器人 | 状态 | 备注 |
|---|---|---|
| Cloudflare Turnstile | 完全支持 | 支持无头模式 |
| Cloudflare JS Challenge | 支持 | 自动执行 JS 挑战 |
| Cloudflare Managed Challenge | 已验证 | 需要 `headless=False` + xvfb |
| DataDome | 部分支持 | 需要高质量代理 |
| PerimeterX | 部分支持 | 需要随机化行为 |
| Akamai Bot Manager | 部分支持 | 代理 + TLS 指纹调优 |
| reCAPTCHA | 手动 | 通过 Shadow DOM 访问 |

## 安装

### 方式一：通过 Marketplace 安装（推荐）

首先，将本仓库添加为 marketplace 源：

```bash
claude plugin marketplace add Esonhugh/Marketplace
```

然后安装插件：

```bash
claude plugin install pydoll-antibot-bypasser
```

### 方式二：从 GitHub 克隆

克隆整个 marketplace 仓库，并指定插件目录：

```bash
git clone https://github.com/Esonhugh/Marketplace.git
claude --plugin-dir ./Marketplace/plugins/pydoll-antibot-bypasser
```

或仅克隆插件到插件目录：

```bash
git clone --depth 1 --filter=blob:none --sparse \
  https://github.com/Esonhugh/Marketplace.git /tmp/marketplace
cd /tmp/marketplace && git sparse-checkout set plugins/pydoll-antibot-bypasser
cp -r plugins/pydoll-antibot-bypasser ~/.claude/plugins/pydoll-antibot-bypasser
```

安装后，本技能会在以下情况自动激活：
- 你要求 agent 抓取 WAF 保护的网站
- `WebFetch` 或 `curl` 因 Cloudflare 403/503 失败
- 你明确提到绕过 WAF、CAPTCHA 或反机器人保护

## 快速开始

```python
# /// script
# requires-python = ">=3.10"
# dependencies = ["pydoll-python"]
# ///

import asyncio
import time
from pydoll.browser import Chrome
from pydoll.browser.options import ChromiumOptions

async def main():
    options = ChromiumOptions()
    options.headless = True

    # 反检测指纹（关键！）
    fake_engagement_time = int(time.time()) - (7 * 24 * 60 * 60)
    options.browser_preferences = {
        'profile': {
            'last_engagement_time': fake_engagement_time,
            'exit_type': 'Normal',
            'exited_cleanly': True,
        },
    }
    options.webrtc_leak_protection = True

    async with Chrome(options=options) as browser:
        tab = await browser.start()

        # 一行代码绕过 Cloudflare
        async with tab.expect_and_bypass_cloudflare_captcha():
            await tab.go_to('https://protected-site.com')

        print(await tab.title)

if __name__ == '__main__':
    asyncio.run(main())
```

使用 [uv](https://github.com/astral-sh/uv) 运行（自动安装依赖）：

```bash
uv run script.py
```

## 功能特性

### Cloudflare 绕过

```python
# 方式 1：上下文管理器（推荐）
async with tab.expect_and_bypass_cloudflare_captcha():
    await tab.go_to('https://protected-site.com')

# 方式 2：开关模式
await tab.enable_auto_solve_cloudflare_captcha()
await tab.go_to('https://protected-site.com')
await asyncio.sleep(5)
await tab.disable_auto_solve_cloudflare_captcha()
```

**Managed Challenge** 需要非无头模式配合虚拟显示器：

```bash
apt-get install -y xvfb
xvfb-run -a --server-args="-screen 0 1920x1080x24" uv run script.py
```

### 拟人化交互

```python
# 模拟真实打字（含错误和延迟）
await input_element.type_text('Hello World', humanize=True)

# 贝塞尔曲线鼠标移动 + 生理性抖动
await tab.mouse.move(500, 300, humanize=True)
await tab.mouse.click(500, 300, humanize=True)
```

### Shadow DOM 访问

```python
shadow_roots = await tab.find_shadow_roots(deep=True)
for sr in shadow_roots:
    checkbox = await sr.query('input[type="checkbox"]', raise_exc=False)
    if checkbox:
        await checkbox.click()
```

### 并发抓取

```python
async with Chrome(options=options) as browser:
    tab = await browser.start()
    tasks = [scrape_page(browser, url) for url in urls]
    results = await asyncio.gather(*tasks)
```

### 混合自动化（UI + API）

```python
# UI 登录后，复用认证 session 调用 API
response = await tab.request.get('https://example.com/api/profile')
data = response.json()
```

### 请求拦截

```python
from pydoll.protocol.fetch.events import FetchEvent, RequestPausedEvent
from pydoll.protocol.network.types import ErrorReason

async def block_resources(event: RequestPausedEvent):
    rid = event['params']['requestId']
    rtype = event['params']['resourceType']
    if rtype in ['Image', 'Stylesheet', 'Font', 'Media']:
        await tab.fail_request(rid, ErrorReason.BLOCKED_BY_CLIENT)
    else:
        await tab.continue_request(rid)

await tab.enable_fetch_events()
await tab.on(FetchEvent.REQUEST_PAUSED, block_resources)
```

## 示例

| 文件 | 说明 |
|---|---|
| `examples/bypass_cloudflare.py` | Cloudflare WAF 绕过 + 反检测配置 |
| `examples/bypass_managed_challenge.py` | Managed Challenge 绕过（headless=False + xvfb）|
| `examples/stealth_scraper.py` | 完整隐蔽抓取器 + 拟人行为模拟 |
| `examples/concurrent_scraper.py` | 批量并发抓取 + 速率限制 |
| `examples/screenshot.py` | 绕过 Cloudflare 后截图 |

8 个开箱即用的代码模板在 `scripts/templates.py` 中：

```bash
uv run scripts/templates.py list          # 列出所有模板
uv run scripts/templates.py stealth_browser  # 打印指定模板
```

## 反检测检查清单

| 检查项 | 默认状态 | 操作 |
|---|---|---|
| `navigator.webdriver` | undefined | Pydoll 自动处理 |
| 浏览器指纹 | 需要配置 | 设置 `browser_preferences` |
| WebRTC 泄露 | 需要配置 | 启用 `webrtc_leak_protection` |
| 鼠标轨迹 | 已拟人化 | 默认贝塞尔曲线 |
| 键盘输入 | 需手动开启 | 使用 `humanize=True` |
| 请求间隔 | 需要配置 | 添加随机延迟 |
| Cloudflare Turnstile | 自动 | 使用 `expect_and_bypass_cloudflare_captcha()` |

## 常见问题

| 问题 | 解决方案 |
|---|---|
| 找不到浏览器 | 设置 `options.binary_location = '/path/to/chrome'` |
| 启动超时 | 增大 `options.start_timeout = 30` |
| Docker 崩溃 | 添加 `--no-sandbox` 和 `--disable-dev-shm-usage` |
| 被识别为机器人 | 启用 `humanize=True`，配置 `browser_preferences` |
| Cloudflare 卡住 | 使用 `expect_and_bypass_cloudflare_captcha()` 上下文管理器 |
| Managed Challenge 失败 | 切换到 `headless=False` + xvfb |

## 项目结构

```
pydoll-antibot-bypasser/
├── .claude-plugin/
│   └── plugin.json              # 插件元数据
├── skills/
│   └── pydoll-antibot-bypasser/
│       ├── SKILL.md             # 技能定义（由 agent 加载）
│       ├── examples/            # 可运行的示例脚本
│       ├── knowledge/           # 反检测最佳实践
│       └── scripts/
│           └── templates.py     # 8 个开箱即用的代码模板
└── README.md
```

## 参考

- **Pydoll**: [github.com/autoscrape-labs/pydoll](https://github.com/autoscrape-labs/pydoll) | [pydoll.tech](https://pydoll.tech/)
- **uv**: [github.com/astral-sh/uv](https://github.com/astral-sh/uv) — 推荐的脚本运行器

## 许可证

MIT

## 作者

[Esonhugh](https://github.com/Esonhugh)

---

> **免责声明**：本工具仅用于授权的安全测试、Web 自动化测试和教育目的。请遵守目标网站的服务条款和 `robots.txt`。作者不对滥用行为承担责任。
