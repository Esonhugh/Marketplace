# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pydoll-python",
# ]
# ///
"""
隐蔽爬虫示例 - 使用人性化交互绕过反爬检测

运行方式: uv run stealth_scraper.py <url>
"""

import asyncio
import sys
import time
import random
from pydoll.browser import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import ScrollPosition


async def human_delay(min_sec: float = 1, max_sec: float = 3):
    """随机延迟，模拟人类思考时间"""
    await asyncio.sleep(random.uniform(min_sec, max_sec))


async def simulate_human_behavior(tab):
    """模拟人类浏览行为"""
    # 随机滚动
    scroll_actions = [
        lambda: tab.scroll.by(ScrollPosition.DOWN, random.randint(200, 500), smooth=True),
        lambda: tab.scroll.by(ScrollPosition.UP, random.randint(100, 300), smooth=True),
    ]

    for _ in range(random.randint(2, 4)):
        await random.choice(scroll_actions)()
        await human_delay(0.5, 1.5)


def get_stealth_options(headless: bool = True, proxy: str = None) -> ChromiumOptions:
    """获取隐蔽浏览器配置"""

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

    # 模拟已存在数周的浏览器
    fake_engagement_time = int(time.time()) - random.randint(7, 21) * 24 * 60 * 60

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

    # 代理
    if proxy:
        options.add_argument(f'--proxy-server={proxy}')

    return options


async def stealth_scrape(url: str, selectors: dict = None, headless: bool = True) -> dict:
    """
    隐蔽爬取网页

    Args:
        url: 目标 URL
        selectors: 要提取的选择器字典
        headless: 是否无头模式

    Returns:
        爬取结果
    """
    if selectors is None:
        selectors = {
            'title': 'h1',
            'description': 'meta[name="description"]',
        }

    options = get_stealth_options(headless=headless)

    async with Chrome(options=options) as browser:
        tab = await browser.start()

        print(f"[+] 正在隐蔽访问: {url}")

        # Cloudflare 自动绕过
        try:
            async with tab.expect_and_bypass_cloudflare_captcha():
                await tab.go_to(url)
            print("[+] Cloudflare 验证已通过")
        except Exception as e:
            print(f"[!] Cloudflare 处理: {e}")
            await tab.go_to(url)

        await human_delay()

        # 模拟人类行为
        await simulate_human_behavior(tab)

        # 提取数据
        result = {
            'url': url,
            'final_url': await tab.current_url,
            'page_title': await tab.title,
        }

        for key, selector in selectors.items():
            try:
                element = await tab.query(selector, raise_exc=False)
                if element:
                    # 获取属性或文本
                    if selector.startswith('meta'):
                        result[key] = element.value or await element.text
                    else:
                        result[key] = await element.text
                else:
                    result[key] = None
            except Exception:
                result[key] = None

        # 保存页面源码
        result['html'] = await tab.page_source

        # 截图
        await tab.take_screenshot('stealth_scrape_result.png')
        print("[+] 截图已保存: stealth_scrape_result.png")

        return result


async def main():
    if len(sys.argv) < 2:
        print("用法: uv run stealth_scraper.py <url>")
        print("示例: uv run stealth_scraper.py https://example.com")
        sys.exit(1)

    url = sys.argv[1]
    result = await stealth_scrape(url)

    print(f"\n{'='*50}")
    print(f"页面标题: {result['page_title']}")
    print(f"最终 URL: {result['final_url']}")
    print(f"HTML 长度: {len(result['html'])} 字符")
    print('='*50)

    # 打印提取的数据
    for key, value in result.items():
        if key not in ['url', 'final_url', 'page_title', 'html']:
            print(f"{key}: {value}")


if __name__ == '__main__':
    asyncio.run(main())
