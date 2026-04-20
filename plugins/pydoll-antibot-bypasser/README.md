# Pydoll Antibot Bypasser

A Claude Code / Ducc skill plugin for stealth browser automation using [Pydoll](https://github.com/autoscrape-labs/pydoll), specialized in bypassing Cloudflare WAF, Turnstile CAPTCHA, and other bot detection systems.

When your AI coding agent encounters a WAF-protected website, this skill automatically kicks in and generates the right bypass code — no manual lookup needed.

## Why This Skill?

Traditional browser automation tools (Selenium, Puppeteer) are easily detected because they set `navigator.webdriver = true`. Pydoll takes a fundamentally different approach:

- **Zero WebDriver dependency** — connects directly via WebSocket to CDP, leaving `navigator.webdriver` as `undefined`
- **Human-like interaction** — Bezier curve mouse movement, typing error simulation, physiological tremor
- **Built-in Cloudflare bypass** — auto-detects and solves Turnstile CAPTCHA in Shadow DOM
- **100% async** — native `asyncio` support with concurrent scraping

## WAF Bypass Support

| WAF / Anti-bot | Status | Notes |
|---|---|---|
| Cloudflare Turnstile | Fully Supported | Works in headless mode |
| Cloudflare JS Challenge | Supported | Auto-executes JS challenges |
| Cloudflare Managed Challenge | Verified | Requires `headless=False` + xvfb |
| DataDome | Partial | Needs high-quality proxy |
| PerimeterX | Partial | Needs randomized behavior |
| Akamai Bot Manager | Partial | Proxy + TLS fingerprint tuning |
| reCAPTCHA | Manual | Via Shadow DOM access |

## Installation

### Method 1: Via Marketplace (Recommended)

First, add this repository as a marketplace source:

```bash
claude plugin marketplace add Esonhugh/Marketplace
```

Then install the plugin:

```bash
claude plugin install pydoll-antibot-bypasser
```

### Method 2: Clone from GitHub

Clone the entire marketplace repo and point Claude Code to the plugin directory:

```bash
git clone https://github.com/Esonhugh/Marketplace.git
claude --plugin-dir ./Marketplace/plugins/pydoll-antibot-bypasser
```

Or clone just the plugin into your plugins directory:

```bash
git clone --depth 1 --filter=blob:none --sparse \
  https://github.com/Esonhugh/Marketplace.git /tmp/marketplace
cd /tmp/marketplace && git sparse-checkout set plugins/pydoll-antibot-bypasser
cp -r plugins/pydoll-antibot-bypasser ~/.claude/plugins/pydoll-antibot-bypasser
```

Once installed, the skill activates automatically when:
- You ask your agent to scrape a WAF-protected site
- A `WebFetch` or `curl` fails with Cloudflare 403/503
- You explicitly mention bypassing WAF, CAPTCHA, or anti-bot protection

## Quick Start

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

    # Anti-detection fingerprint (critical!)
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

        # One-liner Cloudflare bypass
        async with tab.expect_and_bypass_cloudflare_captcha():
            await tab.go_to('https://protected-site.com')

        print(await tab.title)

if __name__ == '__main__':
    asyncio.run(main())
```

Run with [uv](https://github.com/astral-sh/uv) (auto-installs dependencies):

```bash
uv run script.py
```

## Features

### Cloudflare Bypass

```python
# Method 1: Context manager (recommended)
async with tab.expect_and_bypass_cloudflare_captcha():
    await tab.go_to('https://protected-site.com')

# Method 2: Toggle on/off
await tab.enable_auto_solve_cloudflare_captcha()
await tab.go_to('https://protected-site.com')
await asyncio.sleep(5)
await tab.disable_auto_solve_cloudflare_captcha()
```

**Managed Challenge** requires non-headless mode with a virtual display:

```bash
apt-get install -y xvfb
xvfb-run -a --server-args="-screen 0 1920x1080x24" uv run script.py
```

### Human-like Interaction

```python
# Typing with realistic errors and delays
await input_element.type_text('Hello World', humanize=True)

# Mouse movement with Bezier curves and physiological tremor
await tab.mouse.move(500, 300, humanize=True)
await tab.mouse.click(500, 300, humanize=True)
```

### Shadow DOM Access

```python
shadow_roots = await tab.find_shadow_roots(deep=True)
for sr in shadow_roots:
    checkbox = await sr.query('input[type="checkbox"]', raise_exc=False)
    if checkbox:
        await checkbox.click()
```

### Concurrent Scraping

```python
async with Chrome(options=options) as browser:
    tab = await browser.start()
    tasks = [scrape_page(browser, url) for url in urls]
    results = await asyncio.gather(*tasks)
```

### Hybrid Automation (UI + API)

```python
# After UI login, make API calls with the authenticated session
response = await tab.request.get('https://example.com/api/profile')
data = response.json()
```

### Request Interception

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

## Examples

| File | Description |
|---|---|
| `examples/bypass_cloudflare.py` | Cloudflare WAF bypass with anti-detection config |
| `examples/bypass_managed_challenge.py` | Managed Challenge bypass (headless=False + xvfb) |
| `examples/stealth_scraper.py` | Full stealth scraper with human behavior simulation |
| `examples/concurrent_scraper.py` | Batch concurrent scraping with rate limiting |
| `examples/screenshot.py` | Screenshot tool that bypasses Cloudflare first |

8 ready-to-use code templates are available in `scripts/templates.py`:

```bash
uv run scripts/templates.py list          # List all templates
uv run scripts/templates.py stealth_browser  # Print a specific template
```

## Anti-Detection Checklist

| Check | Default Status | Action |
|---|---|---|
| `navigator.webdriver` | Undefined | Handled by Pydoll |
| Browser fingerprint | Needs config | Set `browser_preferences` |
| WebRTC leak | Needs config | Enable `webrtc_leak_protection` |
| Mouse trajectory | Humanized | Bezier curves by default |
| Keyboard input | Opt-in | Use `humanize=True` |
| Request intervals | Needs config | Add random delays |
| Cloudflare Turnstile | Auto | Use `expect_and_bypass_cloudflare_captcha()` |

## Troubleshooting

| Problem | Solution |
|---|---|
| Browser not found | Set `options.binary_location = '/path/to/chrome'` |
| Startup timeout | Increase `options.start_timeout = 30` |
| Docker crash | Add `--no-sandbox` and `--disable-dev-shm-usage` |
| Detected as bot | Enable `humanize=True`, configure `browser_preferences` |
| Cloudflare stuck | Use `expect_and_bypass_cloudflare_captcha()` context manager |
| Managed Challenge fails | Switch to `headless=False` + xvfb |

## Project Structure

```
pydoll-antibot-bypasser/
├── .claude-plugin/
│   └── plugin.json              # Plugin metadata
├── skills/
│   └── pydoll-antibot-bypasser/
│       ├── SKILL.md             # Skill definition (loaded by the agent)
│       ├── examples/            # Runnable example scripts
│       ├── knowledge/           # Anti-detection best practices
│       └── scripts/
│           └── templates.py     # 8 ready-to-use code templates
└── README.md
```

## References

- **Pydoll**: [github.com/autoscrape-labs/pydoll](https://github.com/autoscrape-labs/pydoll) | [pydoll.tech](https://pydoll.tech/)
- **uv**: [github.com/astral-sh/uv](https://github.com/astral-sh/uv) — recommended script runner

## License

MIT

## Author

[Esonhugh](https://github.com/Esonhugh)

---

> **Disclaimer**: This tool is intended for authorized security testing, web automation testing, and educational purposes. Please comply with target websites' Terms of Service and `robots.txt`. The authors are not responsible for misuse.
