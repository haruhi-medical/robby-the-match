#!/usr/bin/env python3
"""Chromium をヘッドレスで起動して /admin/ のスクショを取得"""
import asyncio
import os
from datetime import datetime
from playwright.async_api import async_playwright

BASE = "https://robby-the-match-api.robby-the-robot-2026.workers.dev"
PASSWORD = "cZKgDRMZWabCvUE7"
OUT_DIR = os.path.expanduser("~/robby-the-match/logs/admin-dashboard-build/2026-04-28/screenshots")
os.makedirs(OUT_DIR, exist_ok=True)


async def shoot(page, name):
    path = os.path.join(OUT_DIR, f"{name}.png")
    await page.screenshot(path=path, full_page=True)
    print(f"  ✓ {name}.png ({os.path.getsize(path)} bytes)")
    return path


async def main():
    async with async_playwright() as p:
        # スマホ375px幅でエミュレート
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            viewport={"width": 375, "height": 700},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1",
            ignore_https_errors=False,
        )
        page = await ctx.new_page()

        print(f"[{datetime.now().strftime('%H:%M:%S')}] navigate /admin/")
        await page.goto(f"{BASE}/admin/", wait_until="networkidle", timeout=30000)
        await shoot(page, "01_login_375px")

        print(f"[{datetime.now().strftime('%H:%M:%S')}] login")
        await page.fill('input[type="password"]', PASSWORD)
        await page.click('button[type="submit"]')
        await page.wait_for_url("**/admin/app", timeout=30000)
        await page.wait_for_selector(".metric", timeout=15000)
        await shoot(page, "02_dashboard_375px")

        print("navigate -> conversations")
        await page.click('a[data-tab="conversations"]')
        await page.wait_for_selector(".list-item", timeout=15000)
        await shoot(page, "03_conversations_375px")

        # 1人クリックして詳細
        first = await page.query_selector(".list-item")
        if first:
            print("click first conversation")
            await first.click()
            await page.wait_for_timeout(2000)
            await shoot(page, "04_user_detail_375px")

        print("navigate -> audit log")
        await page.click('a[data-tab="audit"]')
        await page.wait_for_selector(".audit-row", timeout=15000)
        await shoot(page, "05_audit_log_375px")

        # 600px+ で再撮影（PCサイズ）
        await ctx.close()
        ctx2 = await browser.new_context(viewport={"width": 1024, "height": 800})
        page2 = await ctx2.new_page()
        await page2.goto(f"{BASE}/admin/", wait_until="networkidle")
        await page2.fill('input[type="password"]', PASSWORD)
        await page2.click('button[type="submit"]')
        await page2.wait_for_url("**/admin/app")
        await page2.wait_for_selector(".metric")
        await shoot(page2, "06_dashboard_1024px")
        await page2.click('a[data-tab="audit"]')
        await page2.wait_for_selector(".audit-row")
        await shoot(page2, "07_audit_log_1024px")

        await browser.close()
        print("\n全スクショ保存先: " + OUT_DIR)


if __name__ == "__main__":
    asyncio.run(main())
