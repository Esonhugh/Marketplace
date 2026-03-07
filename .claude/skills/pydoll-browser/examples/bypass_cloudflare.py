# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pydoll-python",
# ]
# ///
"""
Cloudflare WAF 绕过示例

运行方式: uv run bypass_cloudflare.py <url>
示例: uv run bypass_cloudflare.py https://nowsecure.nl
"""

import asyncio
import sys
import time
from pydoll.browser import Chrome
from pydoll.browser.options import ChromiumOptions


async def bypass_cloudflare(url: str, headless: bool = True) -> dict:
    """
    绕过 Cloudflare 保护访问网站

    Args:
        url: 目标 URL
        headless: 是否无头模式

    Returns:
        包含页面信息的字典
    """
    options = ChromiumOptions()
    options.headless = headless

    # 服务器/Docker 环境必需参数
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')

    # 指定 Chrome 路径
    options.binary_location = '/usr/bin/google-chrome-stable'

    # 增加启动超时
    options.start_timeout = 30

    # 反检测配置 - 模拟真实用户浏览器
    fake_engagement_time = int(time.time()) - (7 * 24 * 60 * 60)

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
    }

    # WebRTC 泄露保护
    options.webrtc_leak_protection = True

    async with Chrome(options=options) as browser:
        tab = await browser.start()

        print(f"[+] 正在访问: {url}")

        # 自动检测并处理 Cloudflare Turnstile
        async with tab.expect_and_bypass_cloudflare_captcha():
            await tab.go_to(url)

        print("[+] Cloudflare 验证已通过")

        # 等待页面完全加载
        await asyncio.sleep(3)

        result = {
            'title': await tab.title,
            'url': await tab.current_url,
            'html': await tab.page_source,
        }

        # 保存截图
        await tab.take_screenshot('cloudflare_bypass_result.png')
        print("[+] 截图已保存: cloudflare_bypass_result.png")

        return result


async def main():
    if len(sys.argv) < 2:
        print("用法: uv run bypass_cloudflare.py <url>")
        print("示例: uv run bypass_cloudflare.py https://nowsecure.nl")
        sys.exit(1)

    url = sys.argv[1]
    result = await bypass_cloudflare(url)

    print(f"\n{'='*50}")
    print(f"页面标题: {result['title']}")
    print(f"最终 URL: {result['url']}")
    print(f"HTML 长度: {len(result['html'])} 字符")
    print('='*50)


if __name__ == '__main__':
    asyncio.run(main())
