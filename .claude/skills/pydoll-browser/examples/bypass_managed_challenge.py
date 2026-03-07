# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pydoll-python",
# ]
# ///
"""
Cloudflare Managed Challenge 绕过工具

关键：必须使用 headless=False 配合 xvfb 运行

运行方式:
    xvfb-run -a --server-args="-screen 0 1920x1080x24" uv run bypass_managed_challenge.py <url>
示例:
    xvfb-run -a uv run bypass_managed_challenge.py https://dash.cloudflare.com/login
"""

import asyncio
import sys
import time
import random
from pydoll.browser import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import ScrollPosition


async def human_delay(min_sec: float = 0.5, max_sec: float = 2):
    """随机延迟，模拟人类行为"""
    await asyncio.sleep(random.uniform(min_sec, max_sec))


async def bypass_managed_challenge(
    url: str,
    output_screenshot: str = 'result.png',
    max_wait: int = 120,
):
    """
    绕过 Cloudflare Managed Challenge

    Args:
        url: 目标 URL
        output_screenshot: 截图保存路径
        max_wait: 最大等待时间（秒）

    Returns:
        dict: 包含页面信息的字典
    """
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
            'default_content_setting_values': {
                'notifications': 2,
                'geolocation': 2,
            },
        },
        'session': {
            'restore_on_startup': 1,
        },
        'intl': {
            'accept_languages': 'en-US,en',
        },
    }
    options.webrtc_leak_protection = True

    print(f"[+] 目标 URL: {url}")
    print("[+] 模式: headless=False (非无头模式)")

    async with Chrome(options=options) as browser:
        tab = await browser.start()

        # 启用 Cloudflare 自动绕过
        await tab.enable_auto_solve_cloudflare_captcha()

        print("[+] 正在访问页面...")
        await tab.go_to(url)

        # 模拟人类行为
        print("[+] 模拟人类行为...")
        for _ in range(3):
            await tab.scroll.by(ScrollPosition.DOWN, random.randint(100, 300), smooth=True)
            await human_delay(0.3, 0.8)
            await tab.scroll.by(ScrollPosition.UP, random.randint(50, 150), smooth=True)
            await human_delay(0.3, 0.8)

        # 等待验证完成
        print("[+] 等待 Cloudflare 验证...")

        elapsed = 0
        check_interval = 2

        while elapsed < max_wait:
            title = await tab.title
            url_now = await tab.current_url

            # 检查是否通过验证
            if 'moment' not in title.lower() and 'challenge' not in url_now.lower():
                print(f"\n[+] 验证通过! 耗时: {elapsed}秒")
                break

            if elapsed % 10 == 0:
                print(f"  [{elapsed}s] 等待中... 标题: {title[:50]}")

            await asyncio.sleep(check_interval)
            elapsed += check_interval

        # 截图
        await tab.take_screenshot(output_screenshot)
        print(f"[+] 截图已保存: {output_screenshot}")

        # 获取页面信息
        result = {
            'title': await tab.title,
            'url': await tab.current_url,
            'html_length': len(await tab.page_source),
            'elapsed': elapsed,
            'screenshot': output_screenshot,
        }

        await tab.disable_auto_solve_cloudflare_captcha()

        return result


async def main():
    if len(sys.argv) < 2:
        print("用法: xvfb-run -a uv run bypass_managed_challenge.py <url> [output.png]")
        print()
        print("示例:")
        print("  xvfb-run -a uv run bypass_managed_challenge.py https://stackoverflow.com")
        print("  xvfb-run -a uv run bypass_managed_challenge.py https://dash.cloudflare.com/login result.png")
        sys.exit(1)

    url = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else 'managed_challenge_result.png'

    result = await bypass_managed_challenge(url, output)

    print(f"\n{'='*60}")
    print("结果:")
    print(f"  标题: {result['title']}")
    print(f"  URL: {result['url']}")
    print(f"  HTML 长度: {result['html_length']} 字符")
    print(f"  耗时: {result['elapsed']} 秒")
    print(f"  截图: {result['screenshot']}")

    # 判断是否成功
    if 'moment' not in result['title'].lower():
        print("\n✅ 成功绕过 Cloudflare!")
    else:
        print("\n❌ 可能仍在验证页面")


if __name__ == '__main__':
    asyncio.run(main())
