# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pydoll-python",
# ]
# ///
"""
截图工具 - 绕过 Cloudflare 并截图

运行方式: xvfb-run -a uv run screenshot.py <url>
"""

import asyncio
import sys
import time
import random
from pydoll.browser import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import ScrollPosition


async def screenshot_page(url: str, output: str = 'screenshot.png'):
    """访问页面并截图"""

    options = ChromiumOptions()
    options.headless = False  # 非无头模式绕过检测

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

        print(f"[+] 访问: {url}")

        # 启用 Cloudflare 自动绕过
        await tab.enable_auto_solve_cloudflare_captcha()

        await tab.go_to(url)

        # 等待页面加载
        print("[+] 等待页面加载...")

        for i in range(20):
            title = await tab.title
            if 'moment' not in title.lower() and 'wait' not in title.lower() and '稍候' not in title:
                print(f"[+] 页面已加载: {title}")
                break
            print(f"  [{i*2}s] 等待中... 标题: {title}")
            await asyncio.sleep(2)

        # 模拟滚动
        await tab.scroll.by(ScrollPosition.DOWN, 500, smooth=True)
        await asyncio.sleep(1)

        # 截图
        await tab.take_screenshot(output)
        print(f"[+] 截图已保存: {output}")

        # 页面信息
        print(f"[+] 标题: {await tab.title}")
        print(f"[+] URL: {await tab.current_url}")

        html = await tab.page_source
        print(f"[+] HTML 长度: {len(html)} 字符")

        await tab.disable_auto_solve_cloudflare_captcha()

        return {
            'title': await tab.title,
            'url': await tab.current_url,
            'html_length': len(html),
            'screenshot': output,
        }


async def main():
    if len(sys.argv) < 2:
        print("用法: xvfb-run -a uv run screenshot.py <url> [output.png]")
        sys.exit(1)

    url = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else 'screenshot.png'

    result = await screenshot_page(url, output)
    print(f"\n{'='*50}")
    print("结果:")
    for k, v in result.items():
        print(f"  {k}: {v}")


if __name__ == '__main__':
    asyncio.run(main())
