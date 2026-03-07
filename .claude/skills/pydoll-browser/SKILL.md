---
name: pydoll-browser
description: 使用 pydoll 库进行隐蔽的无头浏览器自动化操作，专门用于绕过 Cloudflare WAF、Turnstile 验证码及其他人机验证系统。**当用户需要绕过人机 WAF（如 Cloudflare、DataDome、PerimeterX 等）时，务必调用此 skill。** 也适用于：反爬虫检测绕过、拟真浏览器操作、爬取受保护网站、处理 Shadow DOM、模拟人类用户行为、Web 自动化测试。
---

# Pydoll 浏览器自动化 Skill

Pydoll 是一个**异步原生、零 WebDriver 依赖**的 Chromium 浏览器自动化库，专为**隐蔽性和拟真交互**设计，能够有效绕过 Cloudflare 等人机验证系统。

## 核心优势

1. **零 WebDriver 依赖** - 直接通过 WebSocket 连接 CDP，无 `navigator.webdriver` 标志
2. **拟真用户行为** - 人性化鼠标移动（贝塞尔曲线 + Fitts 定律）、人性化键盘输入（打字错误模拟）
3. **完整 Shadow DOM 支持** - 可访问 closed shadow roots
4. **Cloudflare 自动绕过** - 内置 Turnstile 验证码处理
5. **异步高性能** - 100% 异步设计，支持并发操作

## 快速开始

### 使用 uv script 运行（推荐）

Pydoll 推荐使用 [uv](https://docs.astral.sh/uv/) 作为包管理器，通过内联脚本依赖声明直接运行：

```python
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pydoll-python",
# ]
# ///

import asyncio
from pydoll.browser import Chrome

async def main():
    async with Chrome() as browser:
        tab = await browser.start()
        await tab.go_to('https://example.com')
        print(await tab.title)

if __name__ == '__main__':
    asyncio.run(main())
```

**运行方式：**

```bash
uv run script.py
```

uv 会自动创建虚拟环境并安装依赖，无需手动 `pip install`。

### 传统安装方式

```bash
pip install pydoll-python
```

## 浏览器配置

### 基本配置

```python
# /// script
# requires-python = ">=3.10"
# dependencies = ["pydoll-python"]
# ///

from pydoll.browser import Chrome
from pydoll.browser.options import ChromiumOptions

options = ChromiumOptions()
options.headless = True                    # 无头模式
options.add_argument('--window-size=1920,1080')
options.add_argument('--proxy-server=http://user:pass@proxy:port')
options.start_timeout = 20                 # 启动超时（秒）

# 服务器/Docker 环境必需参数
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')

# 指定 Chrome 路径（如需要）
options.binary_location = '/usr/bin/google-chrome-stable'

async with Chrome(options=options) as browser:
    tab = await browser.start()
```

### 反检测配置（绕过人机验证必需）

```python
# /// script
# requires-python = ">=3.10"
# dependencies = ["pydoll-python"]
# ///

import time
from pydoll.browser import Chrome
from pydoll.browser.options import ChromiumOptions

options = ChromiumOptions()

# 模拟已存在数月的浏览器（重要反检测措施）
fake_engagement_time = int(time.time()) - (7 * 24 * 60 * 60)

options.browser_preferences = {
    'profile': {
        'last_engagement_time': fake_engagement_time,
        'exit_type': 'Normal',
        'exited_cleanly': True,
        'default_content_setting_values': {
            'notifications': 2,      # 阻止通知
            'geolocation': 2,        # 阻止位置
        },
        'password_manager_enabled': False,
    },
    'session': {
        'restore_on_startup': 1,
        'startup_urls': ['https://www.google.com']
    },
    'intl': {
        'accept_languages': 'zh-CN,zh,en-US,en',
    },
}

# WebRTC 泄露保护
options.webrtc_leak_protection = True

# Docker 环境必需
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
```

## Cloudflare WAF 绕过

### 方法一：上下文管理器（推荐）

```python
# /// script
# requires-python = ">=3.10"
# dependencies = ["pydoll-python"]
# ///

import asyncio
from pydoll.browser import Chrome

async def main():
    async with Chrome() as browser:
        tab = await browser.start()
        # 自动检测并处理 Cloudflare Turnstile
        async with tab.expect_and_bypass_cloudflare_captcha():
            await tab.go_to('https://protected-site.com')
        # 验证码处理完成后继续操作
        print(await tab.title)

if __name__ == '__main__':
    asyncio.run(main())
```

运行：
```bash
uv run bypass_cloudflare.py
```

### 方法二：启用/禁用方式

```python
async with Chrome() as browser:
    tab = await browser.start()
    await tab.enable_auto_solve_cloudflare_captcha()
    await tab.go_to('https://protected-site.com')
    await asyncio.sleep(5)  # 等待自动处理
    await tab.disable_auto_solve_cloudflare_captcha()
```

### Shadow DOM 支持

Pydoll 可访问 closed shadow roots（CDP 级别操作）：

```python
# 获取单个 shadow root
shadow = await element.get_shadow_root()
button = await shadow.query('.internal-btn')
await button.click()

# 发现页面所有 shadow roots
shadow_roots = await tab.find_shadow_roots()
for sr in shadow_roots:
    checkbox = await sr.query('input[type="checkbox"]', raise_exc=False)
    if checkbox:
        await checkbox.click()

# 跨域 iframe 内的 shadow roots
shadow_roots = await tab.find_shadow_roots(deep=True, timeout=10)
```

## 元素查找与交互

### 元素查找

```python
# 通过属性查找（推荐方式）
button = await tab.find(
    tag_name='button',
    class_name='btn-primary',
    text='Submit'
)

# 通过 ID 查找
username = await tab.find(id='username')

# 查找多个元素
links = await tab.find(tag_name='a', find_all=True)

# CSS 选择器
nav = await tab.query('nav.main-menu')

# XPath 查询
item = await tab.query('//div[@data-testid="item-123"]')

# 自定义属性
element = await tab.find(
    data_testid='submit-button',
    aria_label='Submit form'
)

# 带超时和错误处理
element = await tab.find(
    class_name='dynamic-content',
    timeout=10,
    raise_exc=False  # 找不到返回 None
)
```

### 元素交互

```python
# 点击
await button.click()

# 人性化输入文本（带错误和延迟模拟，绕过人机验证关键）
await input_element.type_text('Hello World', humanize=True)

# 直接设置值（快速）
await input_element.insert_text('value')

# 清空
await input_element.clear()

# 文件上传
async with tab.expect_file_chooser() as file_chooser:
    await upload_button.click()
await file_chooser.upload_file('/path/to/file')

# 获取元素属性
text = await element.text
is_visible = await element.is_visible()
is_interactable = await element.is_interactable()

# 等待元素状态
await element.wait_until(is_visible=True, timeout=5)
```

## 键盘操作

```python
from pydoll.constants import Key

# 单个按键
await tab.keyboard.press(Key.ENTER)
await tab.keyboard.press(Key.TAB)

# 组合键（最多 3 个键）
await tab.keyboard.hotkey(Key.CONTROL, Key.A)  # 全选
await tab.keyboard.hotkey(Key.CONTROL, Key.C)  # 复制
await tab.keyboard.hotkey(Key.CONTROL, Key.V)  # 粘贴

# 手动控制修饰键
await tab.keyboard.down(Key.SHIFT)
await tab.keyboard.press(Key.ARROWRIGHT)
await tab.keyboard.up(Key.SHIFT)
```

## 鼠标操作

```python
# 人性化鼠标移动（贝塞尔曲线 + Fitts 定律）
await tab.mouse.move(500, 300, humanize=True)

# 点击（带人性化移动）
await tab.mouse.click(500, 300, humanize=True)

# 双击
await tab.mouse.double_click(500, 300)

# 拖拽
await tab.mouse.drag(100, 200, 500, 400, humanize=True)
```

## 滚动操作

```python
from pydoll.constants import ScrollPosition

# 平滑滚动
await tab.scroll.by(ScrollPosition.DOWN, 500, smooth=True)

# 滚动到特定位置
await tab.scroll.to_bottom(smooth=True)
await tab.scroll.to_top(smooth=True)

# 快速滚动
await tab.scroll.by(ScrollPosition.UP, 300, smooth=False)
```

## 标签页管理

```python
# 创建新标签页
tab2 = await browser.new_tab(url='https://example.com')

# 创建隔离的浏览器上下文（类似隐身）
context_id = await browser.create_browser_context(
    proxy_server='http://proxy:8080'
)
tab3 = await browser.new_tab(browser_context_id=context_id)

# 获取所有打开的标签页
tabs = await browser.get_opened_tabs()

# 关闭标签页
await tab.close()
```

## 网络控制

### 混合自动化（UI + API）

```python
# 通过 UI 登录
await tab.go_to('https://example.com/login')
await (await tab.find(id='username')).type_text('user')
await (await tab.find(id='password')).type_text('pass')
await (await tab.find(id='login-btn')).click()

# 使用浏览器会话发出 API 请求（携带登录态）
response = await tab.request.get('https://example.com/api/user/profile')
user_data = response.json()

# POST 请求
response = await tab.request.post(
    'https://example.com/api/settings',
    json={'theme': 'dark'}
)
```

### 请求拦截（阻止资源）

```python
from pydoll.protocol.fetch.events import FetchEvent, RequestPausedEvent
from pydoll.protocol.network.types import ErrorReason

async def block_resources(event: RequestPausedEvent):
    request_id = event['params']['requestId']
    resource_type = event['params']['resourceType']

    # 阻止图片和样式表加载（加速爬取）
    if resource_type in ['Image', 'Stylesheet', 'Font', 'Media']:
        await tab.fail_request(request_id, ErrorReason.BLOCKED_BY_CLIENT)
    else:
        await tab.continue_request(request_id)

await tab.enable_fetch_events()
await tab.on(FetchEvent.REQUEST_PAUSED, block_resources)
await tab.go_to('https://example.com')
await tab.disable_fetch_events()
```

### HAR 网络录制

```python
from pydoll.protocol.network.types import ResourceType

async with tab.request.record(
    resource_types=[ResourceType.FETCH, ResourceType.XHR]
) as capture:
    await tab.go_to('https://example.com')

capture.save('flow.har')
print(f'Captured {len(capture.entries)} requests')

# 重放录制的请求
responses = await tab.request.replay('flow.har')
```

## 截图与导出

```python
# 截图
await tab.take_screenshot(path='screenshot.png')
await tab.take_screenshot(path='full.png', full_page=True)

# 元素截图
await element.take_screenshot(path='element.png')

# PDF
await tab.print_to_pdf(path='page.pdf')

# 页面打包（保存所有资源）
await tab.save_bundle('page.zip')
```

## 文件下载

```python
from pathlib import Path

target_dir = Path('/tmp/my-downloads')
async with tab.expect_download(keep_file_at=target_dir, timeout=10) as dl:
    await (await tab.find(text='Download')).click()
    data = await dl.read_bytes()
    print(f"Downloaded {len(data)} bytes to: {dl.file_path}")
```

## 异常处理

```python
from pydoll.exceptions import (
    ElementNotFound,
    BrowserNotRunning,
    PageLoadTimeout,
    NetworkError,
)

try:
    element = await tab.find(id='button', timeout=5)
except ElementNotFound:
    print("Element not found")
except PageLoadTimeout:
    print("Page load timeout")
```

## 重试装饰器

```python
from pydoll.decorators import retry
from pydoll.exceptions import ElementNotFound, NetworkError

@retry(
    max_retries=3,
    exceptions=[ElementNotFound, NetworkError],
    delay=2.0,
    exponential_backoff=True
)
async def scrape_page(tab, url):
    await tab.go_to(url)
    return await tab.title
```

## 并发爬取

```python
async def scrape_page(url, tab):
    await tab.go_to(url)
    return await tab.title

async def concurrent_scraping():
    async with Chrome() as browser:
        tab1 = await browser.start()
        tab2 = await browser.new_tab()

        results = await asyncio.gather(
            scrape_page('https://site1.com/', tab1),
            scrape_page('https://site2.com/', tab2)
        )
        return results
```

## 完整示例：绕过 Cloudflare 爬取

```python
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pydoll-python",
# ]
# ///

import asyncio
import time
from pydoll.browser import Chrome
from pydoll.browser.options import ChromiumOptions

async def scrape_protected_site(url: str):
    """绕过 Cloudflare 爬取受保护网站"""

    options = ChromiumOptions()
    options.headless = True

    # 反检测配置
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

        # 自动处理 Cloudflare
        async with tab.expect_and_bypass_cloudflare_captcha():
            await tab.go_to(url)

        # 等待页面加载
        await asyncio.sleep(2)

        # 获取页面内容
        title = await tab.title
        content = await tab.page_source

        # 爬取数据
        elements = await tab.find(tag_name='article', find_all=True)
        data = []
        for el in elements:
            text = await el.text
            data.append(text)

        return {
            'title': title,
            'data': data,
            'html': content
        }

async def main():
    result = await scrape_protected_site('https://protected-site.com')
    print(result)

if __name__ == '__main__':
    asyncio.run(main())
```

**运行：**

```bash
uv run scrape_cloudflare.py
```

## 常见问题排查

| 问题 | 解决方案 |
|------|----------|
| 找不到浏览器 | `options.binary_location = '/path/to/chrome'` |
| 启动超时 | `options.start_timeout = 20` |
| Docker 环境崩溃 | 添加 `--no-sandbox` 和 `--disable-dev-shm-usage` |
| 元素找不到 | 增加 `timeout` 参数或使用 `raise_exc=False` |
| 检测为机器人 | 启用 `humanize=True` 输入，配置浏览器指纹 |
| Cloudflare 验证码未通过 | 确保使用 `expect_and_bypass_cloudflare_captcha()` |

## 支持绕过的 WAF/人机验证

| WAF 系统 | 支持状态 | 备注 |
|----------|----------|------|
| Cloudflare Turnstile | ✅ 完全支持 | 无头模式可用，内置自动处理 |
| Cloudflare JS Challenge | ✅ 支持 | 自动执行 JS |
| **Cloudflare Managed Challenge** | ✅ **已验证支持** | **必须 `headless=False` + xvfb** |
| DataDome | ⚠️ 部分支持 | 需高质量代理 + 完整指纹 |
| PerimeterX | ⚠️ 部分支持 | 需随机化行为 |
| Akamai Bot Manager | ⚠️ 部分支持 | 建议使用轮换代理 |
| reCAPTCHA v2/v3 | ⚠️ 手动处理 | 通过 Shadow DOM 访问 |

### Managed Challenge 绕过指南（已验证）

**关键发现：Managed Challenge 检测无头模式，必须使用 `headless=False`**

| 模式 | 结果 | 证明 |
|------|------|------|
| `headless=True` | ❌ 被检测 | "Just a moment..." 无限等待 |
| `headless=False` | ✅ 成功绕过 | Stack Overflow 364,096 字符 |

**服务器环境运行方式：**

```bash
# 1. 安装 xvfb（虚拟显示）
apt-get install -y xvfb

# 2. 使用 xvfb-run 运行脚本
xvfb-run -a --server-args="-screen 0 1920x1080x24" uv run your_script.py
```

**完整配置示例：**

```python
# /// script
# requires-python = ">=3.10"
# dependencies = ["pydoll-python"]
# ///

import asyncio
import time
import random
from pydoll.browser import Chrome
from pydoll.browser.options import ChromiumOptions

async def bypass_managed_challenge(url: str):
    options = ChromiumOptions()
    options.headless = False  # 关键！必须非无头模式

    # 服务器环境参数
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.binary_location = '/usr/bin/google-chrome-stable'
    options.start_timeout = 60
    options.add_argument('--window-size=1920,1080')

    # 反检测配置
    fake_engagement_time = int(time.time()) - random.randint(7, 30) * 24 * 60 * 60
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
        await tab.enable_auto_solve_cloudflare_captcha()
        await tab.go_to(url)

        # 等待验证完成
        for _ in range(30):
            title = await tab.title
            if 'moment' not in title.lower():
                break
            await asyncio.sleep(3)

        return await tab.page_source

# 运行: xvfb-run -a uv run script.py
```

## 参考资源

- GitHub: https://github.com/autoscrape-labs/pydoll
- 文档: https://pydoll.tech/
- 中文文档: https://autoscrape-labs.github.io/pydoll/
- uv 文档: https://docs.astral.sh/uv/

---

**重要提示**：使用此库进行爬虫操作时，请遵守目标网站的 robots.txt 和服务条款，合理设置请求频率，避免对服务器造成过大压力。
