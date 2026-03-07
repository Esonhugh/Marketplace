# 反检测最佳实践

## 为什么需要反检测

现代网站使用多种技术检测自动化工具：
- `navigator.webdriver` 属性检测
- 浏览器指纹分析
- 行为分析（鼠标移动模式、打字速度）
- TLS 指纹检测
- WebRTC 泄露检测

Pydoll 通过以下方式解决这些问题：

## 1. 零 WebDriver 依赖

传统 Selenium/Puppeteer 会设置 `navigator.webdriver = true`，这是最明显的自动化检测标志。

Pydoll 直接通过 WebSocket 连接 Chrome DevTools Protocol，**不设置此标志**。

```python
# Pydoll 方式 - 无 webdriver 标志
async with Chrome() as browser:
    tab = await browser.start()
    # navigator.webdriver === undefined (未定义，而非 false)
```

## 2. 浏览器指纹伪装

### 基础配置

```python
import time
from pydoll.browser.options import ChromiumOptions

options = ChromiumOptions()

# 模拟已存在数月的浏览器（关键！）
fake_engagement_time = int(time.time()) - (7 * 24 * 60 * 60)

options.browser_preferences = {
    'profile': {
        # 浏览器历史记录时间戳
        'last_engagement_time': fake_engagement_time,
        'exit_type': 'Normal',
        'exited_cleanly': True,

        # 权限设置
        'default_content_setting_values': {
            'notifications': 2,      # 阻止通知
            'geolocation': 2,        # 阻止位置
            'media_stream_camera': 2,
            'media_stream_mic': 2,
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
```

### WebRTC 泄露保护

```python
# 防止真实 IP 通过 WebRTC 泄露
options.webrtc_leak_protection = True
```

### 代理配置

```python
# HTTP 代理
options.add_argument('--proxy-server=http://user:pass@proxy:8080')

# SOCKS5 代理
options.add_argument('--proxy-server=socks5://user:pass@proxy:1080')

# 隔离浏览器上下文（每个上下文独立代理）
context_id = await browser.create_browser_context(
    proxy_server='http://proxy:8080'
)
```

## 3. 人性化交互模拟

### 鼠标移动原理

Pydoll 的鼠标移动模拟真实人类行为：

1. **贝塞尔曲线路径** - 非直线移动，有自然弧度
2. **Fitts 定律计时** - 距离越远，时间越长
3. **生理震颤** - 高斯噪声模拟手部抖动
4. **过冲修正** - 约 70% 概率先过冲再回正

```python
# 人性化移动（默认配置已优化）
await tab.mouse.move(500, 300, humanize=True)
await tab.mouse.click(500, 300, humanize=True)

# 元素点击自动人性化
await button.click()  # 内部已使用人性化移动
```

### 键盘输入原理

人性化输入包含以下特性：

```python
# 启用人性化输入
await input.type_text('Hello World', humanize=True)
```

特性：
- **随机击键延迟** - 0.03-0.12 秒
- **标点符号额外延迟** - 更真实的停顿
- **思考停顿** - 2% 概率，0.3-0.7 秒
- **打字错误模拟**：
  - 相邻键错误
  - 字符交换
  - 双击
  - 跳过字符
  - 遗漏空格

## 4. 请求拦截优化

阻止不必要的资源加载可以：
- 加速页面加载
- 减少被检测的机会
- 节省带宽

```python
from pydoll.protocol.fetch.events import FetchEvent, RequestPausedEvent
from pydoll.protocol.network.types import ErrorReason

async def block_resources(event: RequestPausedEvent):
    request_id = event['params']['requestId']
    resource_type = event['params']['resourceType']

    # 可阻止的资源类型
    block_types = ['Image', 'Stylesheet', 'Font', 'Media']

    if resource_type in block_types:
        await tab.fail_request(request_id, ErrorReason.BLOCKED_BY_CLIENT)
    else:
        await tab.continue_request(request_id)

await tab.enable_fetch_events()
await tab.on(FetchEvent.REQUEST_PAUSED, block_resources)
await tab.go_to('https://example.com')
await tab.disable_fetch_events()
```

## 5. Cloudflare 绕过详解

### Cloudflare 检测机制

Cloudflare 使用多层检测：
1. **JS 挑战** - 执行 JavaScript 计算结果
2. **Turnstile 验证码** - 点击复选框验证
3. **行为分析** - 鼠标移动、打字模式
4. **指纹识别** - 浏览器特征

### Pydoll 绕过原理

```python
# 自动检测并处理 Turnstile
async with tab.expect_and_bypass_cloudflare_captcha():
    await tab.go_to('https://protected-site.com')
```

内部机制：
1. 自动检测 shadow root 中的 Turnstile 组件
2. 使用人性化鼠标移动点击复选框
3. 等待验证完成
4. 继续正常操作

### 手动处理（高级场景）

```python
# 手动查找并处理验证码
shadow_roots = await tab.find_shadow_roots(deep=True)
for sr in shadow_roots:
    checkbox = await sr.query('input[type="checkbox"]', raise_exc=False)
    if checkbox:
        # 人性化点击
        await checkbox.click()
        break
```

## 6. 行为模式建议

### 随机化延迟

```python
import random
import asyncio

async def human_delay(min_sec=1, max_sec=3):
    """随机延迟，模拟人类思考时间"""
    await asyncio.sleep(random.uniform(min_sec, max_sec))

# 使用
await tab.go_to(url)
await human_delay()
await element.click()
await human_delay(0.5, 1.5)
```

### 随机化操作顺序

```python
import random

async def random_scroll(tab):
    """随机滚动，模拟浏览行为"""
    actions = [
        lambda: tab.scroll.by(ScrollPosition.DOWN, random.randint(200, 500)),
        lambda: tab.scroll.by(ScrollPosition.UP, random.randint(100, 300)),
        lambda: tab.scroll.to_bottom(smooth=True),
    ]
    await random.choice(actions)()
    await human_delay()
```

### 分散请求时间

```python
# 避免固定频率请求
import random

for url in urls:
    await tab.go_to(url)
    # 随机等待 3-8 秒
    await asyncio.sleep(random.uniform(3, 8))
```

## 7. Docker 环境配置

```python
options = ChromiumOptions()
options.headless = True

# Docker 必需参数
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')

# 容器化环境优化
options.add_argument('--disable-extensions')
options.add_argument('--disable-software-rasterizer')
options.add_argument('--disable-setuid-sandbox')
```

## 8. 检测清单

使用 Pydoll 时检查以下项目：

| 检查项 | 状态 | 说明 |
|--------|------|------|
| `navigator.webdriver` | ✅ 未定义 | Pydoll 默认处理 |
| 浏览器指纹 | ⚠️ 需配置 | 设置 browser_preferences |
| WebRTC 泄露 | ⚠️ 需配置 | 启用 webrtc_leak_protection |
| 鼠标轨迹 | ✅ 人性化 | 默认贝塞尔曲线 |
| 键盘输入 | ⚠️ 需启用 | 使用 humanize=True |
| 请求间隔 | ⚠️ 需配置 | 添加随机延迟 |
| Cloudflare | ✅ 自动处理 | 使用 expect_and_bypass |

## 9. 常见检测绕过

### DataDome

```python
# DataDome 检测较严格，建议：
# 1. 使用高质量代理
# 2. 完整的浏览器指纹配置
# 3. 人性化交互
options.add_argument('--proxy-server=high-quality-proxy:port')
# ... 完整的 browser_preferences 配置
```

### PerimeterX

```python
# PerimeterX 行为分析较强
# 建议：
# 1. 随机化操作顺序
# 2. 添加随机延迟
# 3. 模拟真实浏览行为（滚动、移动等）
```

### Akamai Bot Manager

```python
# Akamai TLS 指纹检测
# 使用代理可能更有帮助
options.add_argument('--proxy-server=rotating-proxy:port')
```

## 10. 最佳实践总结

1. **始终配置浏览器指纹** - 模拟真实用户浏览器历史
2. **使用人性化输入** - `type_text(..., humanize=True)`
3. **添加随机延迟** - 避免固定模式
4. **使用高质量代理** - 避免被 IP 封禁
5. **分散请求时间** - 避免高频请求
6. **模拟真实行为** - 滚动、移动鼠标、随机点击
7. **使用隔离上下文** - 每个任务独立浏览器上下文
8. **处理异常** - 重试机制 + 错误恢复
