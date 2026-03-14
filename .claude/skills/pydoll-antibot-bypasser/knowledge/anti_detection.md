# Anti-Detection Best Practices

## Why Anti-Detection is Needed

Modern websites use multiple techniques to detect automation tools:
- `navigator.webdriver` property detection
- Browser fingerprint analysis
- Behavioral analysis (mouse movement patterns, typing speed)
- TLS fingerprint detection
- WebRTC leak detection

Pydoll solves these problems through:

## 1. Zero WebDriver Dependency

Traditional Selenium/Puppeteer sets `navigator.webdriver = true`, which is the most obvious automation detection flag.

Pydoll connects directly to Chrome DevTools Protocol via WebSocket, **without setting this flag**.

```python
# Pydoll approach - no webdriver flag
async with Chrome() as browser:
    tab = await browser.start()
    # navigator.webdriver === undefined (undefined, not false)
```

## 2. Browser Fingerprint Spoofing

### Basic Configuration

```python
import time
from pydoll.browser.options import ChromiumOptions

options = ChromiumOptions()

# Simulate a browser that's existed for months (CRITICAL!)
fake_engagement_time = int(time.time()) - (7 * 24 * 60 * 60)

options.browser_preferences = {
    'profile': {
        # Browser history timestamp
        'last_engagement_time': fake_engagement_time,
        'exit_type': 'Normal',
        'exited_cleanly': True,

        # Permission settings
        'default_content_setting_values': {
            'notifications': 2,      # Block notifications
            'geolocation': 2,        # Block location
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
        'accept_languages': 'en-US,en',
    },
}
```

### WebRTC Leak Protection

```python
# Prevent real IP leak via WebRTC
options.webrtc_leak_protection = True
```

### Proxy Configuration

```python
# HTTP proxy
options.add_argument('--proxy-server=http://user:pass@proxy:8080')

# SOCKS5 proxy
options.add_argument('--proxy-server=socks5://user:pass@proxy:1080')

# Isolated browser context (independent proxy per context)
context_id = await browser.create_browser_context(
    proxy_server='http://proxy:8080'
)
```

## 3. Human-like Interaction Simulation

### Mouse Movement Principles

Pydoll's mouse movement simulates real human behavior:

1. **Bezier Curve Path** - Non-linear movement with natural curves
2. **Fitts' Law Timing** - Longer distance = longer time
3. **Physiological Tremor** - Gaussian noise simulating hand shake
4. **Overshoot Correction** - ~70% probability of overshooting then correcting

```python
# Human-like movement (default config is optimized)
await tab.mouse.move(500, 300, humanize=True)
await tab.mouse.click(500, 300, humanize=True)

# Element click automatically humanized
await button.click()  # Already uses humanized movement internally
```

### Keyboard Input Principles

Human-like input includes these features:

```python
# Enable humanized input
await input.type_text('Hello World', humanize=True)
```

Features:
- **Random keystroke delay** - 0.03-0.12 seconds
- **Extra punctuation delay** - More realistic pauses
- **Thinking pauses** - 2% probability, 0.3-0.7 seconds
- **Typo simulation**:
  - Adjacent key errors
  - Character swapping
  - Double-typing
  - Skipping characters
  - Missing spaces

## 4. Request Interception Optimization

Blocking unnecessary resources can:
- Speed up page loading
- Reduce detection opportunities
- Save bandwidth

```python
from pydoll.protocol.fetch.events import FetchEvent, RequestPausedEvent
from pydoll.protocol.network.types import ErrorReason

async def block_resources(event: RequestPausedEvent):
    request_id = event['params']['requestId']
    resource_type = event['params']['resourceType']

    # Blockable resource types
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

## 5. Cloudflare Bypass Explained

### Cloudflare Detection Mechanisms

Cloudflare uses multi-layer detection:
1. **JS Challenge** - Execute JavaScript calculation result
2. **Turnstile CAPTCHA** - Click checkbox verification
3. **Behavioral Analysis** - Mouse movement, typing patterns
4. **Fingerprinting** - Browser characteristics

### Pydoll Bypass Principles

```python
# Auto-detect and handle Turnstile
async with tab.expect_and_bypass_cloudflare_captcha():
    await tab.go_to('https://protected-site.com')
```

Internal mechanism:
1. Auto-detect Turnstile component in shadow root
2. Use humanized mouse movement to click checkbox
3. Wait for verification to complete
4. Continue normal operations

### Manual Handling (Advanced Scenarios)

```python
# Manually find and handle CAPTCHA
shadow_roots = await tab.find_shadow_roots(deep=True)
for sr in shadow_roots:
    checkbox = await sr.query('input[type="checkbox"]', raise_exc=False)
    if checkbox:
        # Humanized click
        await checkbox.click()
        break
```

## 6. Behavior Pattern Recommendations

### Randomized Delays

```python
import random
import asyncio

async def human_delay(min_sec=1, max_sec=3):
    """Random delay simulating human thinking time"""
    await asyncio.sleep(random.uniform(min_sec, max_sec))

# Usage
await tab.go_to(url)
await human_delay()
await element.click()
await human_delay(0.5, 1.5)
```

### Randomized Operation Order

```python
import random

async def random_scroll(tab):
    """Random scrolling simulating browsing behavior"""
    actions = [
        lambda: tab.scroll.by(ScrollPosition.DOWN, random.randint(200, 500)),
        lambda: tab.scroll.by(ScrollPosition.UP, random.randint(100, 300)),
        lambda: tab.scroll.to_bottom(smooth=True),
    ]
    await random.choice(actions)()
    await human_delay()
```

### Distributed Request Timing

```python
# Avoid fixed frequency requests
import random

for url in urls:
    await tab.go_to(url)
    # Random wait 3-8 seconds
    await asyncio.sleep(random.uniform(3, 8))
```

## 7. Docker Environment Configuration

```python
options = ChromiumOptions()
options.headless = True

# Docker required parameters
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')

# Containerized environment optimization
options.add_argument('--disable-extensions')
options.add_argument('--disable-software-rasterizer')
options.add_argument('--disable-setuid-sandbox')
```

## 8. Detection Checklist

Check these items when using Pydoll:

| Check Item | Status | Description |
|------------|--------|-------------|
| `navigator.webdriver` | ✅ Undefined | Pydoll handles by default |
| Browser Fingerprint | ⚠️ Needs Config | Set browser_preferences |
| WebRTC Leak | ⚠️ Needs Config | Enable webrtc_leak_protection |
| Mouse Trajectory | ✅ Humanized | Default Bezier curve |
| Keyboard Input | ⚠️ Enable Required | Use humanize=True |
| Request Intervals | ⚠️ Needs Config | Add random delays |
| Cloudflare | ✅ Auto Handled | Use expect_and_bypass |

## 9. Common Detection Bypass

### DataDome

```python
# DataDome has stricter detection, recommend:
# 1. Use high-quality proxy
# 2. Complete browser fingerprint configuration
# 3. Humanized interaction
options.add_argument('--proxy-server=high-quality-proxy:port')
# ... complete browser_preferences configuration
```

### PerimeterX

```python
# PerimeterX has strong behavioral analysis
# Recommend:
# 1. Randomize operation order
# 2. Add random delays
# 3. Simulate real browsing behavior (scrolling, moving, etc.)
```

### Akamai Bot Manager

```python
# Akamai TLS fingerprint detection
# Using proxy may help more
options.add_argument('--proxy-server=rotating-proxy:port')
```

## 10. Best Practices Summary

1. **Always configure browser fingerprint** - Simulate real user browser history
2. **Use humanized input** - `type_text(..., humanize=True)`
3. **Add random delays** - Avoid fixed patterns
4. **Use high-quality proxy** - Avoid IP blocking
5. **Distribute request timing** - Avoid high-frequency requests
6. **Simulate real behavior** - Scroll, move mouse, random clicks
7. **Use isolated contexts** - Independent browser context per task
8. **Handle exceptions** - Retry mechanism + error recovery

## 11. Advanced Techniques (2024+)

### Canvas Fingerprint Noise

```python
# Add noise to canvas fingerprint (requires custom script injection)
await tab.execute_script('''
    const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function() {
        // Add noise to canvas data
        return originalToDataURL.apply(this, arguments);
    };
''')
```

### WebGL Fingerprint Spoofing

```python
# Spoof WebGL renderer info
await tab.execute_script('''
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) return 'Intel Inc.';
        if (parameter === 37446) return 'Intel Iris OpenGL Engine';
        return getParameter.apply(this, arguments);
    };
''')
```

### Audio Context Fingerprint

```python
# Normalize audio context behavior
await tab.execute_script('''
    const originalCreateAnalyser = AudioContext.prototype.createAnalyser;
    AudioContext.prototype.createAnalyser = function() {
        const analyser = originalCreateAnalyser.apply(this, arguments);
        // Normalize float frequency data
        return analyser;
    };
''')
```

### Timing Attack Prevention

```python
# Add jitter to timing-sensitive operations
import random

async def jittered_click(element):
    await asyncio.sleep(random.uniform(0.05, 0.15))
    await element.click()
    await asyncio.sleep(random.uniform(0.1, 0.3))
```
