#!/usr/bin/env python3
"""
TikTok直接アップロード（Playwright版）
tiktok-uploader/tiktokautouploaderが壊れた時のフォールバック

使い方:
  .venv/bin/python3 scripts/tiktok_upload_playwright.py --video PATH --caption "テキスト"
  .venv/bin/python3 scripts/tiktok_upload_playwright.py --test  # 接続テストのみ
"""

import argparse
import json
import sys
import time
from pathlib import Path

COOKIES_FILE = Path(__file__).parent.parent / "data" / ".tiktok_cookies.json"
UPLOAD_URL = "https://www.tiktok.com/creator#/upload?scene=creator_center"

def load_cookies():
    with open(COOKIES_FILE) as f:
        cookies = json.load(f)
    # Playwright形式に変換
    pw_cookies = []
    for c in cookies:
        pc = {
            "name": c["name"],
            "value": c["value"],
            "domain": c.get("domain", ".tiktok.com"),
            "path": c.get("path", "/"),
        }
        if c.get("expires") and c["expires"] > 0:
            pc["expires"] = c["expires"]
        if c.get("secure"):
            pc["secure"] = True
        if c.get("sameSite"):
            ss = c["sameSite"].capitalize()
            if ss in ("Strict", "Lax", "None"):
                pc["sameSite"] = ss
        pw_cookies.append(pc)
    return pw_cookies


def upload_video(video_path: str, caption: str, headless: bool = False, timeout: int = 120):
    from playwright.sync_api import sync_playwright

    print(f"[TikTok Upload] 動画: {video_path}")
    print(f"[TikTok Upload] キャプション: {caption[:50]}...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="ja-JP",
        )

        # Cookie設定
        cookies = load_cookies()
        context.add_cookies(cookies)

        page = context.new_page()

        # アップロードページに遷移
        print("[TikTok Upload] アップロードページに遷移中...")
        page.goto(UPLOAD_URL, wait_until="networkidle", timeout=60000)
        time.sleep(3)

        # ログイン状態確認
        url = page.url
        if "login" in url.lower():
            print("[TikTok Upload] ❌ ログインが必要です。Cookieが無効かもしれません。")
            browser.close()
            return False

        print(f"[TikTok Upload] ページ: {url}")

        # ファイルアップロード（input[type=file]を探す）
        print("[TikTok Upload] ファイルアップロード中...")
        try:
            # 方法1: input[type=file]に直接セット
            file_input = page.locator('input[type="file"]').first
            file_input.set_input_files(video_path, timeout=30000)
            print("[TikTok Upload] ✅ ファイル選択完了")
        except Exception as e:
            print(f"[TikTok Upload] input[type=file]が見つからない: {e}")
            # 方法2: iframe内のinput
            try:
                for frame in page.frames:
                    fi = frame.locator('input[type="file"]')
                    if fi.count() > 0:
                        fi.first.set_input_files(video_path, timeout=30000)
                        print("[TikTok Upload] ✅ iframe内のファイル入力で成功")
                        break
                else:
                    print("[TikTok Upload] ❌ ファイル入力が見つかりません")
                    page.screenshot(path="/tmp/tiktok_upload_debug.png")
                    browser.close()
                    return False
            except Exception as e2:
                print(f"[TikTok Upload] ❌ iframe方式も失敗: {e2}")
                page.screenshot(path="/tmp/tiktok_upload_debug.png")
                browser.close()
                return False

        # アップロード処理待ち
        print("[TikTok Upload] 動画処理中...")
        time.sleep(10)

        # 全オーバーレイ/モーダル/ツアーガイドを強制削除
        print("[TikTok Upload] オーバーレイを除去中...")
        page.evaluate("""() => {
            // TikTokのモーダルオーバーレイ
            document.querySelectorAll('.TUXModal-overlay, [data-floating-ui-portal], #react-joyride-portal, .react-joyride__overlay').forEach(el => el.remove());
            // pointer-events を邪魔するオーバーレイ全般
            document.querySelectorAll('div[role="presentation"]').forEach(el => el.remove());
        }""")
        time.sleep(1)

        # モーダルの閉じボタンも試す
        for sel in ['button:has-text("Cancel")', 'button:has-text("Not now")', 'button:has-text("Turn on")', 'button:has-text("Skip")']:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=1000):
                    btn.click(timeout=3000)
                    print(f"[TikTok Upload] ボタンクリック: {sel}")
                    time.sleep(0.5)
            except:
                continue

        # キャプション入力
        print("[TikTok Upload] キャプション入力中...")
        try:
            # TikTokのキャプションエディタを探す
            # 複数のセレクタを試す（DOM変更対応）
            caption_selectors = [
                '[data-text="true"]',
                '.public-DraftEditor-content',
                '[contenteditable="true"]',
                '.notranslate',
                'div[role="textbox"]',
            ]
            caption_el = None
            for sel in caption_selectors:
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=5000):
                        caption_el = el
                        print(f"[TikTok Upload] キャプション要素: {sel}")
                        break
                except:
                    continue

            if caption_el:
                caption_el.click()
                time.sleep(0.5)
                # 既存テキストをクリア
                page.keyboard.press("Meta+a")
                page.keyboard.press("Backspace")
                time.sleep(0.3)
                # キャプションを入力（日本語対応）
                for line in caption.split('\n'):
                    page.keyboard.type(line, delay=30)
                    page.keyboard.press("Enter")
                print("[TikTok Upload] ✅ キャプション入力完了")
            else:
                print("[TikTok Upload] ⚠️ キャプション要素が見つからない。スキップ。")
        except Exception as e:
            print(f"[TikTok Upload] ⚠️ キャプション入力エラー: {e}")

        # 投稿前: オーバーレイを再度除去 + Got itボタン等を閉じる
        print("[TikTok Upload] 投稿前のオーバーレイ除去...")
        time.sleep(3)
        for sel in ['button:has-text("Got it")', 'button:has-text("OK")', 'button:has-text("Skip")', 'button:has-text("Cancel")']:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=1000):
                    btn.click(timeout=3000)
                    print(f"[TikTok Upload] ポップアップ閉じ: {sel}")
                    time.sleep(0.5)
            except:
                continue

        page.evaluate("""() => {
            document.querySelectorAll('.TUXModal-overlay, [data-floating-ui-portal], #react-joyride-portal, .react-joyride__overlay, div[role="presentation"]').forEach(el => el.remove());
        }""")
        time.sleep(1)

        # 投稿ボタンを探してクリック
        print("[TikTok Upload] 投稿ボタンを探しています...")

        post_selectors = [
            'button:has-text("Post")',
            'button:has-text("投稿")',
            'button:has-text("公開")',
            'button[data-e2e="post_video_button"]',
            '.btn-post',
        ]
        posted = False
        for sel in post_selectors:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=5000):
                    # force: trueでオーバーレイを無視してクリック
                    btn.click(force=True, timeout=10000)
                    print(f"[TikTok Upload] ✅ 投稿ボタンクリック: {sel}")
                    posted = True
                    break
            except:
                continue

        if not posted:
            print("[TikTok Upload] ❌ 投稿ボタンが見つかりません")
            page.screenshot(path="/tmp/tiktok_upload_debug.png")
            print("[TikTok Upload] デバッグスクショ: /tmp/tiktok_upload_debug.png")
            browser.close()
            return False

        # 投稿完了待ち
        print("[TikTok Upload] 投稿完了待ち（最大60秒）...")
        try:
            page.wait_for_url("**/creator**", timeout=60000)
            time.sleep(3)
        except:
            pass

        # 成功判定
        final_url = page.url
        print(f"[TikTok Upload] 最終URL: {final_url}")

        page.screenshot(path="/tmp/tiktok_upload_result.png")
        browser.close()

        if "upload" not in final_url.lower() or "manage" in final_url.lower():
            print("[TikTok Upload] ✅ 投稿成功！")
            return True
        else:
            print("[TikTok Upload] ⚠️ 投稿結果不明。スクショを確認してください。")
            return True  # 楽観的に成功とみなす


def test_connection():
    from playwright.sync_api import sync_playwright

    print("[TikTok Test] 接続テスト...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            locale="ja-JP",
        )
        cookies = load_cookies()
        context.add_cookies(cookies)

        page = context.new_page()
        page.goto("https://www.tiktok.com/@nurse_robby", wait_until="networkidle", timeout=30000)
        time.sleep(3)

        url = page.url
        title = page.title()
        print(f"[TikTok Test] URL: {url}")
        print(f"[TikTok Test] Title: {title}")

        if "login" in url.lower():
            print("[TikTok Test] ❌ ログインが必要。Cookieが無効。")
        else:
            print("[TikTok Test] ✅ Cookie有効。ログイン状態確認OK。")

        page.screenshot(path="/tmp/tiktok_test.png")
        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TikTok Playwright直接アップロード")
    parser.add_argument("--video", help="動画ファイルパス")
    parser.add_argument("--caption", help="キャプション", default="")
    parser.add_argument("--test", action="store_true", help="接続テストのみ")
    parser.add_argument("--headless", action="store_true", help="ヘッドレスモード")
    args = parser.parse_args()

    if args.test:
        test_connection()
    elif args.video:
        success = upload_video(args.video, args.caption, headless=args.headless)
        sys.exit(0 if success else 1)
    else:
        parser.print_help()
