#!/bin/bash
cd "/Users/tianbokai/Downloads/你是我的眼儿"
echo "=== 抖音登录助手 ==="
echo "即将打开浏览器，请在浏览器窗口中扫码登录抖音。"
echo "登录完成后，浏览器会自动关闭。"
echo ""
python3 -c "
import sys, asyncio, os
sys.path.insert(0, '.')
from playwright.async_api import async_playwright
PROFILE = os.path.expanduser('~/.ni_shi_wo_de_yaner/douyin_profile')
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'

async def main():
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            PROFILE, headless=False, user_agent=UA,
            viewport={'width': 1280, 'height': 720})
        page = await ctx.new_page()
        await page.goto('https://www.douyin.com', wait_until='domcontentloaded', timeout=30000)
        print('浏览器已打开，请扫码登录...', flush=True)
        for i in range(200):
            await asyncio.sleep(3)
            try:
                ok = await page.evaluate('() => document.cookie.includes(\"sessionid\") || document.cookie.includes(\"sid_guard\")')
                if ok:
                    print('登录成功！', flush=True)
                    break
            except: pass
        else:
            print('等待超时，请确认是否已登录', flush=True)
        await ctx.close()
        print('登录态已保存。', flush=True)

asyncio.run(main())
"
echo ""
echo "按任意键关闭此窗口..."
read
