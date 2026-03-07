"""
Pydoll 常用模板脚本 - uv script 版本

使用方法：
1. 直接复制需要的模板保存为 .py 文件
2. 使用 uv run 运行: uv run script.py
3. uv 会自动安装依赖

uv script 格式说明：
- 在文件顶部使用 # /// script 块声明依赖
- requires-python: Python 版本要求
- dependencies: 所需包列表
"""

import asyncio
import time
import random
from pathlib import Path
from typing import Optional, List, Dict, Any

from pydoll.browser import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import Key, ScrollPosition
from pydoll.exceptions import ElementNotFound, PageLoadTimeout


# ============================================================
# 模板 1: 基础浏览器配置
# ============================================================

BASIC_BROWSER_TEMPLATE = '''# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pydoll-python",
# ]
# ///

import asyncio
from pydoll.browser import Chrome
from pydoll.browser.options import ChromiumOptions

async def main():
    options = ChromiumOptions()
    options.headless = True

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to('https://example.com')
        print(await tab.title)

if __name__ == '__main__':
    asyncio.run(main())
'''


# ============================================================
# 模板 2: 绕过 Cloudflare WAF
# ============================================================

BYPASS_CLOUDFLARE_TEMPLATE = '''# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pydoll-python",
# ]
# ///

import asyncio
import time
from pydoll.browser import Chrome
from pydoll.browser.options import ChromiumOptions

async def bypass_cloudflare(url: str, headless: bool = True):
    """绕过 Cloudflare 保护访问网站"""

    options = ChromiumOptions()
    options.headless = headless

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

        # 自动处理 Cloudflare Turnstile
        async with tab.expect_and_bypass_cloudflare_captcha():
            await tab.go_to(url)

        await asyncio.sleep(2)

        return {
            'title': await tab.title,
            'url': await tab.current_url,
            'html': await tab.page_source,
        }

async def main():
    result = await bypass_cloudflare('https://nowsecure.nl')
    print(f"Title: {result['title']}")
    print(f"URL: {result['url']}")

if __name__ == '__main__':
    asyncio.run(main())
'''


# ============================================================
# 模板 3: 网页爬取
# ============================================================

WEB_SCRAPING_TEMPLATE = '''# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pydoll-python",
# ]
# ///

import asyncio
import random
from pydoll.browser import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.protocol.fetch.events import FetchEvent, RequestPausedEvent
from pydoll.protocol.network.types import ErrorReason

async def scrape_website(
    url: str,
    selectors: dict,
    headless: bool = True,
    block_resources: bool = True,
):
    """爬取网页数据"""

    options = ChromiumOptions()
    options.headless = headless

    async with Chrome(options=options) as browser:
        tab = await browser.start()

        # 请求拦截（加速加载）
        if block_resources:
            async def block_handler(event: RequestPausedEvent):
                rid = event['params']['requestId']
                rtype = event['params']['resourceType']
                if rtype in ['Image', 'Stylesheet', 'Font', 'Media']:
                    await tab.fail_request(rid, ErrorReason.BLOCKED_BY_CLIENT)
                else:
                    await tab.continue_request(rid)

            await tab.enable_fetch_events()
            await tab.on(FetchEvent.REQUEST_PAUSED, block_handler)

        await tab.go_to(url)
        await asyncio.sleep(2)

        if block_resources:
            await tab.disable_fetch_events()

        # 提取数据
        result = {'url': url}
        for key, selector in selectors.items():
            try:
                elements = await tab.query(selector, find_all=True)
                if len(elements) > 1:
                    result[key] = [await e.text for e in elements]
                elif len(elements) == 1:
                    result[key] = await elements[0].text
                else:
                    result[key] = None
            except Exception:
                result[key] = None

        return result

async def main():
    data = await scrape_website(
        url='https://news.ycombinator.com',
        selectors={
            'titles': '.titleline > a',
            'scores': '.score',
        },
    )
    print(data)

if __name__ == '__main__':
    asyncio.run(main())
'''


# ============================================================
# 模板 4: 表单填写
# ============================================================

FORM_FILLING_TEMPLATE = '''# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pydoll-python",
# ]
# ///

import asyncio
import random
from pydoll.browser import Chrome
from pydoll.browser.options import ChromiumOptions

async def fill_form(
    url: str,
    form_data: dict,
    submit_selector: str,
    headless: bool = False,  # 表单填写建议可视化调试
    humanize: bool = True,
):
    """填写并提交表单"""

    options = ChromiumOptions()
    options.headless = headless

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(url)
        await asyncio.sleep(1)

        # 填写表单
        for selector, value in form_data.items():
            try:
                element = await tab.query(selector)
                await element.clear()
                await element.type_text(value, humanize=humanize)
                await asyncio.sleep(random.uniform(0.3, 0.8))
            except Exception as e:
                return {'success': False, 'error': f'Error with {selector}: {e}'}

        # 提交
        submit_btn = await tab.query(submit_selector)
        await submit_btn.click()
        await asyncio.sleep(2)

        return {
            'success': True,
            'final_url': await tab.current_url,
            'title': await tab.title,
        }

async def main():
    # 示例：填写登录表单
    result = await fill_form(
        url='https://example.com/login',
        form_data={
            '#username': 'your_username',
            '#password': 'your_password',
        },
        submit_selector='button[type="submit"]',
    )
    print(result)

if __name__ == '__main__':
    asyncio.run(main())
'''


# ============================================================
# 模板 5: 登录后 API 调用（混合自动化）
# ============================================================

HYBRID_AUTOMATION_TEMPLATE = '''# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pydoll-python",
# ]
# ///

import asyncio
from pydoll.browser import Chrome
from pydoll.browser.options import ChromiumOptions

async def login_and_request(
    login_url: str,
    username: str,
    password: str,
    username_selector: str,
    password_selector: str,
    submit_selector: str,
    api_url: str,
):
    """登录后调用 API（混合自动化）"""

    options = ChromiumOptions()
    options.headless = True

    async with Chrome(options=options) as browser:
        tab = await browser.start()

        # UI 登录
        await tab.go_to(login_url)
        await asyncio.sleep(1)

        username_input = await tab.query(username_selector)
        await username_input.type_text(username, humanize=True)

        password_input = await tab.query(password_selector)
        await password_input.type_text(password, humanize=True)

        submit_btn = await tab.query(submit_selector)
        await submit_btn.click()

        await asyncio.sleep(3)

        # API 调用（携带登录态）
        response = await tab.request.get(api_url)
        return response.json()

async def main():
    result = await login_and_request(
        login_url='https://example.com/login',
        username='your_username',
        password='your_password',
        username_selector='#username',
        password_selector='#password',
        submit_selector='button[type="submit"]',
        api_url='https://example.com/api/user/profile',
    )
    print(result)

if __name__ == '__main__':
    asyncio.run(main())
'''


# ============================================================
# 模板 6: 批量截图
# ============================================================

SCREENSHOT_TEMPLATE = '''# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pydoll-python",
# ]
# ///

import asyncio
import time
import random
from pathlib import Path
from pydoll.browser import Chrome
from pydoll.browser.options import ChromiumOptions

async def take_screenshots(
    urls: list,
    output_dir: str,
    full_page: bool = False,
    headless: bool = True,
):
    """批量截图"""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    options = ChromiumOptions()
    options.headless = headless

    saved_files = []

    async with Chrome(options=options) as browser:
        tab = await browser.start()

        for i, url in enumerate(urls):
            await tab.go_to(url)
            await asyncio.sleep(2)

            filename = f"screenshot_{i}_{int(time.time())}.png"
            filepath = output_path / filename
            await tab.take_screenshot(path=str(filepath), full_page=full_page)
            saved_files.append(str(filepath))

            await asyncio.sleep(random.uniform(1, 3))

    return saved_files

async def main():
    files = await take_screenshots(
        urls=[
            'https://example.com',
            'https://google.com',
        ],
        output_dir='./screenshots',
        full_page=True,
    )
    print(f"Saved {len(files)} screenshots")
    for f in files:
        print(f"  - {f}")

if __name__ == '__main__':
    asyncio.run(main())
'''


# ============================================================
# 模板 7: 并发爬取
# ============================================================

CONCURRENT_SCRAPING_TEMPLATE = '''# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pydoll-python",
# ]
# ///

import asyncio
import random
from pydoll.browser import Chrome
from pydoll.browser.options import ChromiumOptions

async def scrape_one(browser, url: str) -> dict:
    """爬取单个页面"""
    tab = await browser.new_tab()
    try:
        await tab.go_to(url)
        await asyncio.sleep(2)
        return {
            'url': url,
            'title': await tab.title,
            'html': await tab.page_source,
        }
    finally:
        await tab.close()

async def concurrent_scrape(urls: list, max_concurrent: int = 3):
    """并发爬取多个页面"""

    options = ChromiumOptions()
    options.headless = True

    results = []

    async with Chrome(options=options) as browser:
        # 分批并发
        for i in range(0, len(urls), max_concurrent):
            batch = urls[i:i + max_concurrent]
            tasks = [scrape_one(browser, url) for url in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            results.extend([r for r in batch_results if not isinstance(r, Exception)])

            # 批次间延迟
            if i + max_concurrent < len(urls):
                await asyncio.sleep(random.uniform(2, 5))

    return results

async def main():
    urls = [
        'https://example.com',
        'https://google.com',
        'https://github.com',
    ]
    results = await concurrent_scrape(urls, max_concurrent=2)
    for r in results:
        print(f"{r['url']}: {r['title']}")

if __name__ == '__main__':
    asyncio.run(main())
'''


# ============================================================
# 模板 8: 完整反检测配置
# ============================================================

STEALTH_BROWSER_TEMPLATE = '''# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pydoll-python",
# ]
# ///

import asyncio
import time
import random
from pydoll.browser import Chrome
from pydoll.browser.options import ChromiumOptions

def get_stealth_options(
    headless: bool = True,
    proxy: str = None,
    download_dir: str = None,
) -> ChromiumOptions:
    """获取隐蔽浏览器的配置选项"""

    options = ChromiumOptions()
    options.headless = headless

    # 模拟已存在数月的浏览器
    fake_engagement_time = int(time.time()) - random.randint(3, 14) * 24 * 60 * 60

    options.browser_preferences = {
        'profile': {
            'last_engagement_time': fake_engagement_time,
            'exit_type': 'Normal',
            'exited_cleanly': True,
            'default_content_setting_values': {
                'notifications': 2,
                'geolocation': 2,
                'media_stream_camera': 2,
                'media_stream_mic': 2,
            },
            'password_manager_enabled': False,
        },
        'session': {
            'restore_on_startup': 1,
        },
        'intl': {
            'accept_languages': 'zh-CN,zh,en-US,en',
        },
    }

    # WebRTC 泄露保护
    options.webrtc_leak_protection = True

    # 代理配置
    if proxy:
        options.add_argument(f'--proxy-server={proxy}')

    # 下载目录
    if download_dir:
        options.set_default_download_directory(download_dir)

    return options

async def human_delay(min_sec: float = 1, max_sec: float = 3):
    """随机延迟，模拟人类思考时间"""
    await asyncio.sleep(random.uniform(min_sec, max_sec))

async def main():
    options = get_stealth_options(
        headless=True,
        # proxy='http://user:pass@proxy:port',
    )

    async with Chrome(options=options) as browser:
        tab = await browser.start()

        # 绕过 Cloudflare
        async with tab.expect_and_bypass_cloudflare_captcha():
            await tab.go_to('https://nowsecure.nl')

        await human_delay()

        print(f"Title: {await tab.title}")
        print(f"URL: {await tab.current_url}")

if __name__ == '__main__':
    asyncio.run(main())
'''


# ============================================================
# 输出所有模板
# ============================================================

TEMPLATES = {
    'basic_browser': BASIC_BROWSER_TEMPLATE,
    'bypass_cloudflare': BYPASS_CLOUDFLARE_TEMPLATE,
    'web_scraping': WEB_SCRAPING_TEMPLATE,
    'form_filling': FORM_FILLING_TEMPLATE,
    'hybrid_automation': HYBRID_AUTOMATION_TEMPLATE,
    'screenshot': SCREENSHOT_TEMPLATE,
    'concurrent_scraping': CONCURRENT_SCRAPING_TEMPLATE,
    'stealth_browser': STEALTH_BROWSER_TEMPLATE,
}


def print_template(name: str):
    """打印指定模板"""
    if name in TEMPLATES:
        print(TEMPLATES[name])
    else:
        print(f"Unknown template: {name}")
        print(f"Available templates: {list(TEMPLATES.keys())}")


def list_templates():
    """列出所有可用模板"""
    print("Available templates:")
    for name in TEMPLATES:
        print(f"  - {name}")


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == 'list':
            list_templates()
        else:
            print_template(sys.argv[1])
    else:
        print("Usage: uv run templates.py <template_name>")
        print("       uv run templates.py list")
        list_templates()
