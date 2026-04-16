#!/usr/bin/env python3
"""
TikTok直接アップロード（Playwright版）— TikTok Studio対応 v2.0
tiktok-uploader/tiktokautouploaderが壊れた時のフォールバック

使い方:
  .venv/bin/python3 scripts/tiktok_upload_playwright.py --video PATH --caption "テキスト"
  .venv/bin/python3 scripts/tiktok_upload_playwright.py --test  # 接続テストのみ

変更履歴:
  v2.0 (2026-04-16): URL変更 creator→tiktokstudio、セレクタ全面更新、
                      動画処理完了待ち追加、投稿完了検知修正
  v1.0: 初版（旧creator center UI向け）
"""

import argparse
import json
import sys
import time
from pathlib import Path

COOKIES_FILE = Path(__file__).parent.parent / "data" / ".tiktok_cookies.json"
# v2.0: TikTok Studio（旧creator centerは廃止されモバイル風UIにリダイレクトされる）
UPLOAD_URL = "https://www.tiktok.com/tiktokstudio/upload"

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


def _dismiss_overlays(page):
    """TikTok Studioのモーダル/オーバーレイ/ツアーガイドを除去"""
    page.evaluate("""() => {
        document.querySelectorAll(
            '.TUXModal-overlay, [data-floating-ui-portal], #react-joyride-portal, '
            + '.react-joyride__overlay, div[role="presentation"], '
            + '[class*="Modal-overlay"], [class*="modal-mask"]'
        ).forEach(el => el.remove());
    }""")
    # 閉じるボタン系を全部試す（日英両対応）
    # 注意: "オンにする"等の確認ダイアログも含む（コンテンツチェック設定等）
    dismiss_texts = [
        "Cancel", "Not now", "Turn on", "Skip", "Got it", "OK",
        "キャンセル", "後で", "スキップ", "閉じる", "了解",
        "オンにする",  # コンテンツ自動チェックダイアログ
    ]
    for text in dismiss_texts:
        try:
            btn = page.locator(f'button:has-text("{text}")').first
            if btn.is_visible(timeout=500):
                btn.click(timeout=2000)
                time.sleep(0.3)
        except:
            continue


def upload_video(video_path: str, caption: str, headless: bool = False, timeout: int = 180):
    from playwright.sync_api import sync_playwright

    print(f"[TikTok Upload] 動画: {video_path}")
    print(f"[TikTok Upload] キャプション: {caption[:50]}...")
    print(f"[TikTok Upload] URL: {UPLOAD_URL}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
        ])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
            locale="ja-JP",
        )

        # Cookie設定
        cookies = load_cookies()
        context.add_cookies(cookies)

        page = context.new_page()

        # アップロードページに遷移
        print("[TikTok Upload] TikTok Studioアップロードページに遷移中...")
        page.goto(UPLOAD_URL, wait_until="domcontentloaded", timeout=60000)
        time.sleep(5)

        # ログイン状態確認
        url = page.url
        if "login" in url.lower():
            print("[TikTok Upload] ログインが必要です。Cookieが無効かもしれません。")
            page.screenshot(path="/tmp/tiktok_upload_debug.png")
            browser.close()
            return False

        # TikTok Studioにリダイレクトされたか確認
        if "tiktokstudio" not in url.lower() and "studio" not in url.lower():
            print(f"[TikTok Upload] 想定外のリダイレクト: {url}")
            page.screenshot(path="/tmp/tiktok_upload_debug.png")
            browser.close()
            return False

        print(f"[TikTok Upload] ページ到達: {url}")

        # オーバーレイ除去
        _dismiss_overlays(page)

        # ===== Step 1: ファイルアップロード =====
        # Reactアプリのレンダリング完了を待つ（input[type=file]が出現するまで）
        print("[TikTok Upload] アップロードフォームの描画待ち...")
        file_input_ready = False
        for _ in range(15):  # 最大45秒
            if page.locator('input[type="file"]').count() > 0:
                file_input_ready = True
                break
            time.sleep(3)
        if not file_input_ready:
            print("[TikTok Upload] アップロードフォームが描画されない（45秒タイムアウト）")
            page.screenshot(path="/tmp/tiktok_upload_debug.png")
            browser.close()
            return False

        print("[TikTok Upload] ファイルアップロード中...")
        file_uploaded = False
        try:
            # TikTok Studio: input[type=file][accept="video/*"]
            file_input = page.locator('input[type="file"][accept="video/*"]').first
            if file_input.count() == 0:
                file_input = page.locator('input[type="file"]').first
            file_input.set_input_files(video_path, timeout=30000)
            file_uploaded = True
            print("[TikTok Upload] ファイル選択完了")
        except Exception as e:
            print(f"[TikTok Upload] input[type=file]直接方式失敗: {e}")
            # フォールバック: iframe内のinput
            try:
                for frame in page.frames:
                    fi = frame.locator('input[type="file"]')
                    if fi.count() > 0:
                        fi.first.set_input_files(video_path, timeout=30000)
                        file_uploaded = True
                        print("[TikTok Upload] iframe内のファイル入力で成功")
                        break
            except Exception as e2:
                print(f"[TikTok Upload] iframe方式も失敗: {e2}")

        if not file_uploaded:
            print("[TikTok Upload] ファイル入力が見つかりません")
            page.screenshot(path="/tmp/tiktok_upload_debug.png")
            browser.close()
            return False

        # ===== Step 2: 動画処理完了を待つ =====
        # TikTok Studioは動画アップロード後に処理時間が必要
        # キャプション入力欄（contenteditable）が表示されるまで待つ
        print("[TikTok Upload] 動画処理完了待ち（最大90秒）...")
        caption_editor_found = False
        caption_selectors = [
            '[contenteditable="true"]',
            'div[role="textbox"]',
            '[data-text="true"]',
            '.public-DraftEditor-content',
            '.notranslate[contenteditable]',
            '[class*="caption"] [contenteditable]',
            '[class*="description"] [contenteditable]',
        ]

        start_wait = time.time()
        while time.time() - start_wait < 90:
            # オーバーレイが出たら消す
            _dismiss_overlays(page)

            for sel in caption_selectors:
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=2000):
                        caption_editor_found = True
                        print(f"[TikTok Upload] 動画処理完了。キャプション要素検出: {sel}")
                        break
                except:
                    continue
            if caption_editor_found:
                break

            # 投稿ボタン(data-e2e)の出現でも判定（キャプション欄がない場合のフォールバック）
            try:
                post_btn = page.locator('button[data-e2e="post_video_button"]').first
                if post_btn.count() > 0:
                    print("[TikTok Upload] 投稿ボタン(data-e2e)検出。フォーム表示済み。")
                    break
            except:
                pass

            time.sleep(3)
            elapsed = int(time.time() - start_wait)
            if elapsed % 15 == 0:
                print(f"[TikTok Upload] 処理中... {elapsed}秒経過")
                page.screenshot(path="/tmp/tiktok_upload_processing.png")

        if not caption_editor_found:
            # 90秒経過してもキャプション欄が出ない場合、スクショを撮って状況確認
            page.screenshot(path="/tmp/tiktok_upload_debug.png")
            print("[TikTok Upload] 動画処理タイムアウト。スクショ: /tmp/tiktok_upload_debug.png")
            # 投稿ボタン(data-e2e)が存在すれば続行
            try:
                post_check = page.locator('button[data-e2e="post_video_button"]')
                if post_check.count() == 0:
                    print("[TikTok Upload] 投稿ボタンも見つからない。中断。")
                    browser.close()
                    return False
                print("[TikTok Upload] 投稿ボタン(data-e2e)は存在する。続行。")
            except:
                browser.close()
                return False

        # ===== Step 3: キャプション入力 =====
        print("[TikTok Upload] キャプション入力中...")
        time.sleep(2)
        try:
            caption_el = None
            for sel in caption_selectors:
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=3000):
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
                # typeではなくfill or クリップボード経由で入力（日本語安定性向上）
                for line in caption.split('\n'):
                    page.keyboard.type(line, delay=30)
                    page.keyboard.press("Enter")
                print("[TikTok Upload] キャプション入力完了")
            else:
                print("[TikTok Upload] キャプション要素が見つからない。スキップ。")
        except Exception as e:
            print(f"[TikTok Upload] キャプション入力エラー（続行）: {e}")

        # ===== Step 4: オーバーレイ再除去 =====
        time.sleep(2)
        _dismiss_overlays(page)
        time.sleep(1)

        # ===== Step 5: 投稿ボタンクリック =====
        print("[TikTok Upload] 投稿ボタンを探しています...")

        # ページ下部にスクロール（投稿ボタンはビューポート外にあることが多い）
        page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)
        page.screenshot(path="/tmp/tiktok_upload_before_post.png")

        # TikTok Studio投稿ボタンセレクタ（日英両対応）
        post_selectors = [
            'button[data-e2e="post_video_button"]',
            'button[data-e2e="publish_button"]',
        ]

        posted = False

        # まず data-e2e 属性のボタンを試す（最も信頼性が高い）
        for sel in post_selectors:
            try:
                btn = page.locator(sel).first
                # scroll_into_view_if_neededでビューポート内に入れる
                btn.scroll_into_view_if_needed(timeout=5000)
                time.sleep(0.5)
                btn.click(timeout=10000)
                print(f"[TikTok Upload] 投稿ボタンクリック（data-e2e）: {sel}")
                posted = True
                break
            except Exception as e:
                print(f"[TikTok Upload] data-e2eボタン試行失敗 ({sel}): {e}")
                continue

        # data-e2eで見つからない場合、テキストベースで探す（位置でサイドバーを除外）
        if not posted:
            text_selectors = [
                'button:has-text("投稿")',
                'button:has-text("公開")',
                'button:has-text("Post")',
                'button:has-text("Publish")',
            ]
            for sel in text_selectors:
                try:
                    buttons = page.locator(sel).all()
                    for btn in buttons:
                        try:
                            btn.scroll_into_view_if_needed(timeout=3000)
                        except:
                            continue
                        box = btn.bounding_box()
                        if not box:
                            continue
                        # サイドバーのナビ(x<100)とプレビュー内ボタン(x>800)を除外
                        if 100 < box["x"] < 800:
                            btn.click(timeout=10000)
                            print(f"[TikTok Upload] 投稿ボタンクリック（テキスト, x={box['x']:.0f}）: {sel}")
                            posted = True
                            break
                    if posted:
                        break
                except:
                    continue

        if not posted:
            print("[TikTok Upload] 投稿ボタンが見つかりません")
            page.screenshot(path="/tmp/tiktok_upload_debug.png")
            print("[TikTok Upload] デバッグスクショ: /tmp/tiktok_upload_debug.png")
            browser.close()
            return False

        # ===== Step 6: 投稿完了待ち =====
        print("[TikTok Upload] 投稿完了待ち（最大90秒）...")
        time.sleep(5)

        # 成功パターン:
        # 1. URLが /tiktokstudio/content に変わる（管理画面にリダイレクト）
        # 2. 「投稿が完了しました」的なメッセージが表示される
        # 3. アップロードエリアが再表示される（新規アップロード画面に戻る）
        success = False
        start_post = time.time()
        while time.time() - start_post < 90:
            current_url = page.url
            # content管理ページにリダイレクトされたら成功
            if "content" in current_url and "upload" not in current_url:
                print(f"[TikTok Upload] 投稿管理ページにリダイレクト: {current_url}")
                success = True
                break
            # manage ページ
            if "manage" in current_url:
                print(f"[TikTok Upload] 管理ページにリダイレクト: {current_url}")
                success = True
                break
            # 成功メッセージ検出
            try:
                for text in ["投稿が完了", "アップロードが完了", "Successfully", "posted", "published"]:
                    if page.locator(f'text="{text}"').first.is_visible(timeout=500):
                        print(f"[TikTok Upload] 成功メッセージ検出: {text}")
                        success = True
                        break
                if success:
                    break
            except:
                pass
            # アップロード画面に戻った（=前の投稿が完了して新規アップロード画面）
            try:
                select_btn = page.locator('button[data-e2e="select_video_button"]').first
                if select_btn.is_visible(timeout=500):
                    # 動画選択ボタンが再表示 = 投稿完了してリセットされた
                    print("[TikTok Upload] アップロード画面がリセットされた（投稿完了）")
                    success = True
                    break
            except:
                pass

            time.sleep(3)

        # 最終判定
        final_url = page.url
        print(f"[TikTok Upload] 最終URL: {final_url}")

        page.screenshot(path="/tmp/tiktok_upload_result.png")
        browser.close()

        if success:
            print("[TikTok Upload] 投稿成功！")
            return True
        else:
            print("[TikTok Upload] 投稿結果不明。スクショを確認: /tmp/tiktok_upload_result.png")
            return False


def test_connection():
    from playwright.sync_api import sync_playwright

    print("[TikTok Test] 接続テスト...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            locale="ja-JP",
        )
        cookies = load_cookies()
        context.add_cookies(cookies)

        page = context.new_page()

        # TikTok Studioに遷移してログイン状態とUI確認
        print("[TikTok Test] TikTok Studioに遷移中...")
        page.goto(UPLOAD_URL, wait_until="domcontentloaded", timeout=60000)
        # Reactアプリの描画完了を待つ
        time.sleep(3)

        url = page.url
        title = page.title()
        print(f"[TikTok Test] URL: {url}")
        print(f"[TikTok Test] Title: {title}")

        if "login" in url.lower():
            print("[TikTok Test] ログインが必要。Cookieが無効。")
        elif "tiktokstudio" in url.lower():
            print("[TikTok Test] TikTok Studio到達。Cookie有効。")
            # ファイル入力の出現を最大30秒待つ（Reactレンダリング待ち）
            file_input_found = False
            for _ in range(10):
                file_inputs = page.locator('input[type="file"]').count()
                if file_inputs > 0:
                    file_input_found = True
                    print(f"[TikTok Test] input[type=file]要素数: {file_inputs}")
                    break
                time.sleep(3)
            if not file_input_found:
                print("[TikTok Test] input[type=file]が30秒以内に出現しなかった")
            # 動画選択ボタン
            try:
                sel_btn = page.locator('button[data-e2e="select_video_button"]')
                if sel_btn.is_visible(timeout=5000):
                    print("[TikTok Test] 動画選択ボタン(data-e2e): 表示あり")
                else:
                    print("[TikTok Test] 動画選択ボタン(data-e2e): なし")
            except:
                print("[TikTok Test] 動画選択ボタン(data-e2e): なし")
        else:
            print(f"[TikTok Test] 想定外のURL: {url}")

        page.screenshot(path="/tmp/tiktok_test.png")
        print("[TikTok Test] スクショ: /tmp/tiktok_test.png")
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
