# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pydoll-python",
# ]
# ///
"""
微步在线威胁情报查询工具 (pydoll 版本)

完整流程：
1. 使用持久化 profile (~/.claude/plugins/data/.chrome-profiles/threatbook) 保留登录态
2. 访问主页检查登录状态
3. 未登录 → 微信扫码登录（自动化），持续监测直到登录成功
4. 已登录 → 在搜索框输入内容 → 点击搜索按钮 → 进入结果页
5. 截图 + 保存完整 HTML + 提取页面文本

使用方法：
    uv run threatbook_query.py -q 8.8.8.8
    uv run threatbook_query.py -q example.com
    uv run threatbook_query.py -q abc123def456...
    uv run threatbook_query.py -q 'ip="1.1.1.1" && port="80"'
"""

import argparse
import asyncio
import json
import os
import random
import signal
import subprocess
import sys
import time
from pathlib import Path

from pydoll.browser import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import Key, ScrollPosition


# ─── 常量 ─────────────────────────────────────────────
BASE_URL = "https://x.threatbook.com/"
LOGIN_URL = "https://passport.threatbook.cn/login?service=x"
OAUTH_URL = "https://passport.threatbook.cn/oauth"

# 持久化浏览器 profile 目录，保留登录态（cookies/session）
PROFILE_DIR = os.path.expanduser("~/.claude/plugins/data/.chrome-profiles/threatbook")


# ─── 工具函数 ──────────────────────────────────────────
def kill_stale_chrome_processes():
    """清理使用同一 profile 目录的残留 Chrome 进程，避免 profile 锁冲突"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", f"user-data-dir={PROFILE_DIR}"],
            capture_output=True, text=True,
        )
        pids = result.stdout.strip().split("\n")
        pids = [p for p in pids if p]
        if pids:
            print(f"[*] 发现 {len(pids)} 个残留 Chrome 进程，正在清理...")
            for pid in pids:
                try:
                    os.kill(int(pid), signal.SIGTERM)
                except (ProcessLookupError, ValueError):
                    pass
            time.sleep(1)
    except FileNotFoundError:
        pass


async def human_delay(min_sec: float = 1.0, max_sec: float = 2.5):
    """随机延迟，模拟人类操作间隔"""
    await asyncio.sleep(random.uniform(min_sec, max_sec))


def build_options() -> ChromiumOptions:
    """构建浏览器配置 (headless=False 以绕过反爬检测，使用持久化 profile)"""
    options = ChromiumOptions()
    options.headless = False

    # 使用固定的 user-data-dir 持久化登录态（cookies/localStorage/session）
    # 同时创建 Default 子目录，确保 browser_preferences 写入 Preferences 文件时目录已存在
    default_dir = os.path.join(PROFILE_DIR, "Default")
    os.makedirs(default_dir, exist_ok=True)
    # pydoll 关闭时会尝试 copy2 Preferences.backup，若文件不存在会报错
    prefs_backup = os.path.join(default_dir, "Preferences.backup")
    if not os.path.exists(prefs_backup):
        Path(prefs_backup).write_text("{}", encoding="utf-8")
    options.add_argument(f"--user-data-dir={PROFILE_DIR}")

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.start_timeout = 60

    fake_engagement_time = int(time.time()) - random.randint(7, 30) * 86400
    options.browser_preferences = {
        "profile": {
            "last_engagement_time": fake_engagement_time,
            "exit_type": "Normal",
            "exited_cleanly": True,
            "default_content_setting_values": {
                "notifications": 2,
                "geolocation": 2,
            },
        },
        "intl": {
            "accept_languages": "zh-CN,zh,en-US,en",
        },
    }
    options.webrtc_leak_protection = True
    return options


def extract_cdp_value(raw):
    """从 CDP 包装对象中提取实际值"""
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        if "result" in raw:
            inner = raw["result"]
            if isinstance(inner, dict) and "result" in inner:
                deepest = inner["result"]
                if isinstance(deepest, dict) and "value" in deepest:
                    return deepest["value"]
            if isinstance(inner, dict) and "value" in inner:
                return inner["value"]
    return raw


async def wait_for_page_ready(tab, timeout: int = 30) -> bool:
    """等待页面内容就绪（跳过 Cloudflare / loading 等待页）"""
    for i in range(timeout // 2):
        title = await tab.title
        lower_title = title.lower()
        if any(
            kw in lower_title
            for kw in ("moment", "wait", "just a moment", "checking")
        ) or "稍候" in title:
            print(f"  [{i * 2}s] 页面加载中... 标题: {title}")
            await asyncio.sleep(2)
            continue
        return True
    return False


async def take_screenshot(tab, name: str) -> str:
    """截图并返回路径"""
    path = f"/tmp/threatbook_{name}_{int(time.time())}.png"
    await tab.take_screenshot(path)
    print(f"[+] 截图已保存: {path}")
    return path


async def save_page_html(tab, name: str) -> str:
    """保存页面完整 HTML 源码到文件"""
    try:
        html = await tab.page_source
        path = f"/tmp/threatbook_{name}_{int(time.time())}.html"
        Path(path).write_text(html, encoding="utf-8")
        print(f"[+] HTML 已保存: {path} ({len(html)} bytes)")
        return path
    except Exception as e:
        print(f"[!] HTML 保存失败: {e}")
        return ""


async def extract_page_text(tab, max_chars: int = 8000) -> str:
    """从页面提取纯文本内容"""
    try:
        raw = await tab.execute_script(
            f"return document.body ? document.body.innerText.substring(0, {max_chars}) : '';"
        )
        val = extract_cdp_value(raw)
        if isinstance(val, str):
            return val
        return json.dumps(val, ensure_ascii=False)[:max_chars]
    except Exception as e:
        print(f"[!] 文本提取失败: {e}")
        return ""


# ─── 登录功能 ─────────────────────────────────────────
async def check_login_status(tab) -> bool:
    """
    检查微步登录状态
    原理：已登录时页面右上角无"登录"按钮，有用户头像
    """
    try:
        raw = await tab.execute_script(
            """
            (() => {
                const els = Array.from(document.querySelectorAll('button, a, span, div'));
                const hasLoginBtn = els.some(el => el.textContent.trim() === '登录');
                return hasLoginBtn ? 'not_logged_in' : 'logged_in';
            })()
            """
        )
        text = extract_cdp_value(raw)
        return text == "logged_in"
    except Exception:
        return False


async def login_with_wechat(tab) -> str:
    """
    微信扫码登录流程

    流程：
    1. 导航到 https://passport.threatbook.cn/login?service=x
    2. 点击微信登录图标 (.wx)
    3. 页面跳转到 /oauth
    4. 点击同意隐私协议 (.checkbox) — 二维码才能显示清晰
    5. 截图二维码发送给用户
    """
    print("[*] ═══ 微信登录流程开始 ═══")

    # 1. 导航到登录页面
    print("[*] 步骤1: 访问登录页面...")
    await tab.go_to(LOGIN_URL)
    await wait_for_page_ready(tab)
    await human_delay(2, 3)
    await take_screenshot(tab, "login_page")

    # 2. 点击微信登录图标
    print("[*] 步骤2: 点击微信登录图标 (div.wx)...")
    wx_btn = await tab.query("div.wx", raise_exc=False)
    if not wx_btn:
        wx_btn = await tab.query(".wx", raise_exc=False)
    if wx_btn:
        try:
            await wx_btn.click()
        except Exception:
            await tab.execute_script(
                "document.querySelector('.wx, div.wx')?.click();"
            )
        print("[+] 已点击微信登录图标")
    else:
        print("[-] 未找到微信登录图标，直接跳转 OAuth 页面")
        await tab.go_to(OAUTH_URL)
    await human_delay(2, 3)

    # 3. 确认到达 OAuth 页面
    current_url = await tab.current_url
    print(f"[*] 步骤3: 当前URL: {current_url}")
    if "/oauth" not in current_url:
        print("[-] 未到达微信登录页面")
        return await take_screenshot(tab, "login_not_oauth")

    # 4. 点击同意隐私协议（关键！二维码初始是模糊的）
    print("[*] 步骤4: 点击同意隐私协议 (span.checkbox)...")
    await human_delay(1, 2)
    checkbox = await tab.query("span.checkbox", raise_exc=False)
    if not checkbox:
        checkbox = await tab.query(".checkbox", raise_exc=False)
    if checkbox:
        try:
            await checkbox.click()
        except Exception:
            await tab.execute_script(
                "document.querySelector('span.checkbox, .checkbox')?.click();"
            )
        print("[+] 已点击隐私协议")
        await human_delay(1.5, 2.5)
    else:
        print("[!] 未找到隐私协议 checkbox (可能已勾选)")

    # 5. 截图二维码
    print("[*] 步骤5: 截取微信登录二维码...")
    await human_delay(1, 2)
    qr_path = await take_screenshot(tab, "wechat_qrcode")

    print("[*] ═══ 请使用微信扫描二维码登录 ═══")
    return qr_path


async def wait_for_login_complete(tab, timeout: int = 120) -> bool:
    """
    持续监测页面，等待用户完成微信扫码登录
    检测方式：URL 从 passport 跳转回 x.threatbook.com
    """
    print(f"[*] 持续监测登录状态... (超时 {timeout}s)")
    for i in range(timeout // 3):
        current_url = await tab.current_url
        if "x.threatbook.com" in current_url and "passport" not in current_url:
            print("[+] 检测到登录成功！已跳转回主站")
            await take_screenshot(tab, "login_success")
            return True
        if i % 5 == 0:
            print(f"  [{i * 3}s] 监测中... URL: {current_url[:60]}")
        await asyncio.sleep(3)
    print("[-] 登录监测超时")
    return False


# ─── 搜索框交互 ──────────────────────────────────────
async def focus_visible_search_box(tab) -> bool:
    """
    聚焦页面上**可见的**搜索框 textarea

    页面有两个 textarea.x-searchBar-input（顶部小栏 + 中间大栏），
    顶部那个初始不可见，需要选择 offsetWidth > 100 的可见那个。
    """
    raw = await tab.execute_script("""
        JSON.stringify((() => {
            const textareas = document.querySelectorAll('textarea.x-searchBar-input');
            for (const ta of textareas) {
                if (ta.offsetWidth > 100) {
                    ta.focus();
                    ta.click();
                    return { found: true, width: ta.offsetWidth };
                }
            }
            return { found: false };
        })())
    """)
    val = extract_cdp_value(raw)
    if isinstance(val, str):
        data = json.loads(val)
    else:
        data = val
    if isinstance(data, dict) and data.get("found"):
        print(f"[+] 聚焦到搜索框 (宽度: {data.get('width')}px)")
        return True
    print("[-] 未找到可见的搜索框")
    return False


async def type_in_search_box(tab, query_text: str):
    """
    在搜索框（textarea）中输入查询内容

    前置条件：已通过 focus_visible_search_box 聚焦搜索框
    流程：清空 → 输入文本
    """
    await human_delay(0.3, 0.6)

    # 全选已有内容并清空
    await tab.keyboard.hotkey(Key.META, Key.A)
    await human_delay(0.1, 0.2)
    await tab.keyboard.press(Key.BACKSPACE)
    await human_delay(0.2, 0.4)

    # 逐字输入查询内容（模拟人类打字）
    print(f"[*] 在搜索框输入: {query_text}")
    await tab.keyboard.type_text(query_text, humanize=True)
    await human_delay(0.5, 1.0)


async def click_search_confirm(tab) -> bool:
    """
    点击**可见的**搜索确认按钮（放大镜图标）

    页面有两个确认按钮，需要选可见的那个（offsetWidth > 0）
    """
    raw = await tab.execute_script("""
        JSON.stringify((() => {
            const btns = document.querySelectorAll('.x-searchBar-input-confirm-btn');
            for (const btn of btns) {
                if (btn.offsetWidth > 0) {
                    btn.click();
                    return 'clicked';
                }
            }
            return '';
        })())
    """)
    val = extract_cdp_value(raw)
    if isinstance(val, str) and "clicked" in val:
        print("[+] 点击搜索确认按钮")
        return True

    # 兜底：按 Enter 提交
    print("[*] 未找到确认按钮，使用 Enter 提交")
    await tab.keyboard.press(Key.ENTER)
    return True


async def wait_for_navigation(tab, original_url: str, timeout: int = 15) -> bool:
    """等待页面导航到新 URL（搜索结果页）"""
    for i in range(timeout):
        current_url = await tab.current_url
        if current_url != original_url:
            print(f"[+] 页面已导航到: {current_url}")
            return True
        await asyncio.sleep(1)
    print("[-] 等待页面导航超时")
    return False


# ─── 查询功能 ─────────────────────────────────────────
async def query_threatbook(tab, query_text: str) -> dict:
    """
    通过搜索框在微步上执行威胁情报查询

    流程：
    1. 确保在主页
    2. 找到搜索框并输入查询内容
    3. 点击搜索按钮
    4. 等待结果页加载
    5. 截图 + 提取文本
    """
    print(f"[*] 查询: {query_text}")

    # 确保在主页
    current_url = await tab.current_url
    if "x.threatbook.com" not in current_url:
        print("[*] 导航回主页...")
        await tab.go_to(BASE_URL)
        await wait_for_page_ready(tab)
        await human_delay(1, 2)

    original_url = await tab.current_url

    # 聚焦搜索框
    print("[*] 定位并聚焦搜索框...")
    focused = await focus_visible_search_box(tab)
    if not focused:
        await take_screenshot(tab, "no_search_box")
        return {
            "status": "error",
            "message": "无法找到搜索框",
            "screenshot": f"/tmp/threatbook_no_search_box_{int(time.time())}.png",
        }

    # 输入查询内容
    await type_in_search_box(tab, query_text)

    # 点击搜索确认按钮（放大镜）
    print("[*] 点击搜索确认按钮...")
    await click_search_confirm(tab)

    # 等待页面导航
    await human_delay(1, 2)
    navigated = await wait_for_navigation(tab, original_url, timeout=15)

    # 等待页面就绪
    await wait_for_page_ready(tab)
    await human_delay(2, 3)

    # 检查是否被重定向到登录页面
    current_url = await tab.current_url
    print(f"[*] 结果页 URL: {current_url}")

    if "passport.threatbook.cn" in current_url:
        screenshot = await take_screenshot(tab, "need_login")
        html_file = await save_page_html(tab, "need_login")
        return {
            "status": "need_login",
            "message": "需要登录才能查询",
            "login_url": current_url,
            "screenshot": screenshot,
            "html_file": html_file,
        }

    # 等待内容动态渲染
    await human_delay(2, 3)

    # 模拟滚动加载更多内容
    await tab.scroll.by(ScrollPosition.DOWN, 400, smooth=True)
    await human_delay(0.5, 1)
    await tab.scroll.by(ScrollPosition.UP, 200, smooth=True)
    await human_delay(0.5, 1)

    # 截图 + 保存 HTML
    screenshot_path = await take_screenshot(tab, "result")
    html_path = await save_page_html(tab, "result")

    # 获取页面元信息
    page_title = await tab.title
    final_url = await tab.current_url
    html = await tab.page_source
    html_length = len(html)

    # 提取文本摘要
    text_summary = await extract_page_text(tab)

    return {
        "status": "success",
        "query": query_text,
        "page_title": page_title,
        "url": final_url,
        "html_length": html_length,
        "screenshot": screenshot_path,
        "html_file": html_path,
        "text_summary": text_summary,
    }


# ─── 主流程 ───────────────────────────────────────────
async def run(query_text: str) -> dict:
    """
    完整流程：
    1. 访问主页 → 检查登录状态
    2. 未登录 → 微信扫码登录（持续监测直到成功）
    3. 已登录 → 搜索框输入 → 点击搜索 → 获取结果
    """
    options = build_options()

    # 清理上次可能残留的 Chrome 进程，防止 profile 锁冲突
    kill_stale_chrome_processes()

    try:
        async with Chrome(options=options) as browser:
            tab = await browser.start()

            # 启用 Cloudflare 自动绕过
            await tab.enable_auto_solve_cloudflare_captcha()

            # ── 第1步：访问主页检查登录状态 ──
            print("[*] ═══ 第1步: 访问主页检查登录状态 ═══")
            await tab.go_to(BASE_URL)
            await wait_for_page_ready(tab)
            await human_delay(1, 2)

            is_logged_in = await check_login_status(tab)
            print(f"[*] 登录状态: {'已登录' if is_logged_in else '未登录'}")

            # ── 第2步：未登录则执行微信登录 ──
            if not is_logged_in:
                print("[*] ═══ 第2步: 执行微信登录 ═══")
                qr_path = await login_with_wechat(tab)

                # 持续监测直到登录成功
                logged_in = await wait_for_login_complete(tab)
                if not logged_in:
                    return {
                        "status": "login_timeout",
                        "message": "微信扫码登录超时，请重试",
                        "qr_screenshot": qr_path,
                    }

                # 登录成功后回到主页
                print("[*] 登录成功，导航回主页...")
                await tab.go_to(BASE_URL)
                await wait_for_page_ready(tab)
                await human_delay(1, 2)
            else:
                print("[*] 已登录，直接进入搜索")

            # ── 第3步：通过搜索框执行查询 ──
            print("[*] ═══ 第3步: 搜索框查询 ═══")
            result = await query_threatbook(tab, query_text)

            # 如果查询过程中 session 失效
            if result.get("status") == "need_login":
                print("[!] 查询时 session 失效，重新登录...")
                qr_path = await login_with_wechat(tab)
                logged_in = await wait_for_login_complete(tab)
                if logged_in:
                    await tab.go_to(BASE_URL)
                    await wait_for_page_ready(tab)
                    await human_delay(1, 2)
                    result = await query_threatbook(tab, query_text)

            await tab.disable_auto_solve_cloudflare_captcha()
            return result
    except Exception as e:
        print(f"[!] 浏览器异常: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        # 确保异常退出时也清理残留进程
        kill_stale_chrome_processes()


def main():
    parser = argparse.ArgumentParser(
        description="微步在线威胁情报查询工具 (pydoll 版)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  uv run threatbook_query.py -q 8.8.8.8
  uv run threatbook_query.py -q example.com
  uv run threatbook_query.py -q abc123def456
  uv run threatbook_query.py -q 'ip="1.1.1.1" && port="80"'
  uv run threatbook_query.py -q 'country="中国" && city="北京" && port="443"'
        """,
    )
    parser.add_argument(
        "--query", "-q", required=True, help="查询内容（IP/域名/哈希/X语法，任意格式）"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="将结果输出到 JSON 文件",
    )

    args = parser.parse_args()

    result = asyncio.run(run(query_text=args.query))

    # 输出结果
    output_json = json.dumps(result, indent=2, ensure_ascii=False)
    print(f"\n{'=' * 60}")
    print(output_json)
    print("=" * 60)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output_json, encoding="utf-8")
        print(f"[+] 结果已保存到: {args.output}")


if __name__ == "__main__":
    main()
