#!/usr/bin/env python3
"""
抖音登录助手 - 单独打开浏览器完成登录，保存登录态到 ~/.ni_shi_wo_de_yaner/douyin_profile/
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from playwright.async_api import async_playwright

PROFILE_DIR = os.path.expanduser("~/.ni_shi_wo_de_yaner/douyin_profile")
os.makedirs(PROFILE_DIR, exist_ok=True)

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"


async def check_login(page):
    """检测是否已登录"""
    try:
        await page.goto("https://www.douyin.com", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)
        logged_in = await page.evaluate("""
            () => {
                const sid = localStorage.getItem('sid_guard');
                const loginSid = localStorage.getItem('login_sid_guard');
                if ((sid || loginSid) && document.cookie.includes('sessionid')) return true;
                return false;
            }
        """)
        return logged_in
    except Exception:
        return False


async def main():
    print("正在启动浏览器...")
    print(f"Profile 目录: {PROFILE_DIR}")
    print()

    async with async_playwright() as p:
        # 先检查是否已有登录态
        print("检查现有登录态...")
        context = await p.chromium.launch_persistent_context(
            PROFILE_DIR,
            headless=True,
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 720},
        )
        page = await context.new_page()
        already_logged_in = await check_login(page)
        await context.close()

        if already_logged_in:
            print("已检测到有效登录态，无需重新登录！")
            return

        # 打开可视浏览器登录
        print("未检测到登录态，正在打开浏览器...")
        print("请在浏览器窗口中扫码登录抖音（不限时，完成后按 Ctrl+C 或关闭浏览器即可）")
        print()

        context = await p.chromium.launch_persistent_context(
            PROFILE_DIR,
            headless=False,
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 720},
            ignore_https_errors=True,
        )
        page = await context.new_page()
        await page.goto("https://www.douyin.com", wait_until="domcontentload", timeout=30000)

        print("浏览器已打开，请扫码登录...")
        print("登录完成后，按 Enter 键继续...")

        # 等待用户按 Enter
        input()

        # 验证登录态
        logged_in = await check_login(page)
        if logged_in:
            print("\n登录态验证成功！")
        else:
            print("\n警告：未检测到有效登录态，请确认已扫码登录。")

        await context.close()
        print("浏览器已关闭，登录态已保存。")


if __name__ == "__main__":
    asyncio.run(main())
