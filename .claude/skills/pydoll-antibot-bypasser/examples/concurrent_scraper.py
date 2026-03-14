# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pydoll-python",
# ]
# ///
"""
并发爬取示例 - 使用多个标签页并发爬取

运行方式: uv run concurrent_scraper.py <url1> <url2> ...
示例: uv run concurrent_scraper.py https://example.com https://google.com
"""

import asyncio
import sys
import time
import random
from pydoll.browser import Chrome
from pydoll.browser.options import ChromiumOptions


async def scrape_page(browser, url: str, index: int) -> dict:
    """
    爬取单个页面

    Args:
        browser: 浏览器实例
        url: 目标 URL
        index: 页面索引

    Returns:
        爬取结果
    """
    tab = await browser.new_tab()

    try:
        print(f"[{index}] 正在访问: {url}")

        # Cloudflare 自动处理
        try:
            async with tab.expect_and_bypass_cloudflare_captcha():
                await tab.go_to(url)
        except Exception:
            await tab.go_to(url)

        await asyncio.sleep(random.uniform(1, 3))

        result = {
            'index': index,
            'url': url,
            'title': await tab.title,
            'final_url': await tab.current_url,
            'success': True,
        }

        print(f"[{index}] 完成: {result['title']}")
        return result

    except Exception as e:
        print(f"[{index}] 错误: {e}")
        return {
            'index': index,
            'url': url,
            'error': str(e),
            'success': False,
        }

    finally:
        await tab.close()


def get_browser_options(headless: bool = True) -> ChromiumOptions:
    """获取浏览器配置"""

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

    # 反检测配置
    fake_engagement_time = int(time.time()) - random.randint(7, 14) * 24 * 60 * 60

    options.browser_preferences = {
        'profile': {
            'last_engagement_time': fake_engagement_time,
            'exit_type': 'Normal',
            'exited_cleanly': True,
        },
    }
    options.webrtc_leak_protection = True

    return options


async def concurrent_scrape(
    urls: list,
    max_concurrent: int = 3,
    headless: bool = True,
) -> list:
    """
    并发爬取多个页面

    Args:
        urls: URL 列表
        max_concurrent: 最大并发数
        headless: 是否无头模式

    Returns:
        爬取结果列表
    """
    options = get_browser_options(headless=headless)
    results = []

    async with Chrome(options=options) as browser:
        # 第一个标签页
        initial_tab = await browser.start()

        # 分批并发
        total = len(urls)
        for i in range(0, total, max_concurrent):
            batch = urls[i:i + max_concurrent]
            batch_num = (i // max_concurrent) + 1
            total_batches = (total + max_concurrent - 1) // max_concurrent

            print(f"\n=== 批次 {batch_num}/{total_batches} ===")

            # 并发执行
            tasks = [
                scrape_page(browser, url, i + j + 1)
                for j, url in enumerate(batch)
            ]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # 收集结果
            for r in batch_results:
                if not isinstance(r, Exception):
                    results.append(r)

            # 批次间延迟
            if i + max_concurrent < total:
                delay = random.uniform(2, 5)
                print(f"\n等待 {delay:.1f} 秒后继续...")
                await asyncio.sleep(delay)

        # 关闭初始标签页
        await initial_tab.close()

    return results


async def main():
    if len(sys.argv) < 2:
        print("用法: uv run concurrent_scraper.py <url1> <url2> ...")
        print("示例: uv run concurrent_scraper.py https://example.com https://google.com")
        sys.exit(1)

    urls = sys.argv[1:]

    print(f"开始并发爬取 {len(urls)} 个页面...")
    start_time = time.time()

    results = await concurrent_scrape(urls, max_concurrent=3)

    elapsed = time.time() - start_time

    # 打印结果汇总
    print(f"\n{'='*60}")
    print("爬取结果汇总")
    print('='*60)

    success_count = sum(1 for r in results if r.get('success'))
    fail_count = len(results) - success_count

    print(f"成功: {success_count}, 失败: {fail_count}")
    print(f"耗时: {elapsed:.2f} 秒")
    print('-'*60)

    for r in results:
        if r.get('success'):
            print(f"[{r['index']}] {r['title'][:50]:<50} | {r['final_url'][:40]}")
        else:
            print(f"[{r['index']}] 失败: {r.get('error', 'Unknown error')}")

    print('='*60)


if __name__ == '__main__':
    asyncio.run(main())
