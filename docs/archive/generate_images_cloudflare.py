#!/usr/bin/env python3
"""
Cloudflare Workers AI (FLUX.1-schnell) を使った画像生成スクリプト
神奈川ナース転職 - SNS投稿用スライドショー画像生成

【改善版】
- レート制限対応
- 指数バックオフでのリトライ
- レスポンスタイプ判定
- 詳細なエラーログ
"""

import os
import json
import sys
import requests
import time
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import io
from typing import Optional, Tuple

# 設定
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")

if not CLOUDFLARE_API_TOKEN or not CLOUDFLARE_ACCOUNT_ID:
    print("❌ エラー: 環境変数が設定されていません")
    print("設定方法:")
    print("  export CLOUDFLARE_API_TOKEN='your-token'")
    print("  export CLOUDFLARE_ACCOUNT_ID='your-account-id'")
    sys.exit(1)

# Cloudflare Workers AI エンドポイント
MODEL = "@cf/black-forest-labs/flux-1-schnell"
API_URL = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{MODEL}"

# リトライ設定
MAX_RETRIES = 3  # 最大リトライ回数
INITIAL_RETRY_DELAY = 2  # 初期リトライ待機時間（秒）
MAX_RETRY_DELAY = 60  # 最大リトライ待機時間（秒）
REQUEST_INTERVAL = 3  # 連続リクエスト間の待機時間（秒）


def generate_base_image(prompt: str, width: int = 1024, height: int = 1536) -> Optional[bytes]:
    """
    Cloudflare Workers AIで画像生成（リトライ機能付き）

    Args:
        prompt: 画像生成プロンプト
        width: 画像幅（デフォルト: 1024）
        height: 画像高さ（デフォルト: 1536）

    Returns:
        bytes: 生成された画像のバイトデータ（失敗時はNone）
    """
    print(f"🎨 画像生成中...")
    print(f"   プロンプト: {prompt[:50]}...")

    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "prompt": prompt,
        "num_steps": 4,  # FLUX.1-schnellは4ステップ推奨
        "guidance": 7.5,
        "width": width,
        "height": height
    }

    # リトライループ
    for attempt in range(MAX_RETRIES):
        try:
            print(f"   試行 {attempt + 1}/{MAX_RETRIES}")

            response = requests.post(API_URL, headers=headers, json=payload, timeout=90)

            # Content-Typeをチェック
            content_type = response.headers.get("Content-Type", "")

            # 成功（200 OK）
            if response.status_code == 200:
                # 画像データかJSONレスポンスか判定
                if "image" in content_type or len(response.content) > 10000:
                    image_bytes = response.content
                    print(f"✅ 画像生成成功（{len(image_bytes) / 1024:.1f} KB）")
                    return image_bytes
                else:
                    # JSONレスポンスの場合
                    try:
                        result = response.json()
                        print(f"⚠️  予期しないJSONレスポンス: {result}")
                        return None
                    except:
                        print(f"❌ レスポンスが小さすぎます（{len(response.content)} bytes）")
                        return None

            # レート制限（429 Too Many Requests）
            elif response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", INITIAL_RETRY_DELAY * (2 ** attempt)))
                retry_after = min(retry_after, MAX_RETRY_DELAY)

                print(f"⏳ レート制限検知（429）- {retry_after}秒待機...")

                try:
                    error_data = response.json()
                    print(f"   詳細: {error_data}")
                except:
                    pass

                if attempt < MAX_RETRIES - 1:
                    time.sleep(retry_after)
                    continue
                else:
                    print(f"❌ 最大リトライ回数に達しました")
                    return None

            # サーバーエラー（5xx）- リトライ可能
            elif 500 <= response.status_code < 600:
                delay = INITIAL_RETRY_DELAY * (2 ** attempt)
                delay = min(delay, MAX_RETRY_DELAY)

                print(f"⚠️  サーバーエラー（{response.status_code}）- {delay}秒後にリトライ...")

                try:
                    error_data = response.json()
                    print(f"   詳細: {error_data}")
                except:
                    print(f"   レスポンス: {response.text[:200]}")

                if attempt < MAX_RETRIES - 1:
                    time.sleep(delay)
                    continue
                else:
                    print(f"❌ 最大リトライ回数に達しました")
                    return None

            # その他のエラー（4xx）- リトライしない
            else:
                print(f"❌ APIエラー: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   詳細: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
                except:
                    print(f"   レスポンス: {response.text[:500]}")
                return None

        except requests.exceptions.Timeout:
            print(f"⏰ タイムアウト（90秒）")
            if attempt < MAX_RETRIES - 1:
                delay = INITIAL_RETRY_DELAY * (2 ** attempt)
                print(f"   {delay}秒後にリトライ...")
                time.sleep(delay)
                continue
            else:
                print(f"❌ 最大リトライ回数に達しました")
                return None

        except requests.exceptions.RequestException as e:
            print(f"⚠️  リクエストエラー: {e}")
            if attempt < MAX_RETRIES - 1:
                delay = INITIAL_RETRY_DELAY * (2 ** attempt)
                print(f"   {delay}秒後にリトライ...")
                time.sleep(delay)
                continue
            else:
                print(f"❌ 最大リトライ回数に達しました")
                return None

        except Exception as e:
            print(f"❌ 予期しないエラー: {e}")
            import traceback
            traceback.print_exc()
            return None

    return None


def add_text_overlay(image_bytes: bytes, text: str, output_path: str):
    """
    画像にテキストオーバーレイを追加

    Args:
        image_bytes: 元画像のバイトデータ
        text: オーバーレイするテキスト
        output_path: 保存先パス
    """
    print(f"📝 テキストオーバーレイ追加中...")
    print(f"   テキスト: {text[:30]}...")

    try:
        # バイトデータから画像を開く
        image = Image.open(io.BytesIO(image_bytes))

        # RGBA変換（透明度対応）
        if image.mode != 'RGBA':
            image = image.convert('RGBA')

        # オーバーレイ用の透明レイヤー作成
        overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # フォント設定（Macのシステムフォント）
        font_paths = [
            "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
            "/Library/Fonts/Arial Unicode.ttf",
        ]

        font = None
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    font = ImageFont.truetype(font_path, 80)  # サイズ80
                    break
                except:
                    continue

        if not font:
            print("⚠️  システムフォントが見つからないため、デフォルトフォント使用")
            font = ImageFont.load_default()

        # テキストのバウンディングボックス取得
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # 画像中央やや下に配置
        x = (image.width - text_width) // 2
        y = int(image.height * 0.6)  # 画面の60%位置

        # 半透明の黒背景を描画
        padding = 40
        bg_bbox = [
            x - padding,
            y - padding,
            x + text_width + padding,
            y + text_height + padding
        ]
        draw.rectangle(bg_bbox, fill=(0, 0, 0, 180))  # 黒・透明度180/255

        # 白文字でテキスト描画
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))

        # オーバーレイを元画像に合成
        image = Image.alpha_composite(image, overlay)

        # RGB変換して保存
        image = image.convert('RGB')
        image.save(output_path, 'PNG')

        print(f"✅ 保存完了: {output_path}")
        return True

    except Exception as e:
        print(f"❌ テキストオーバーレイエラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_slide_image(prompt: str, text_overlay: str, output_path: str):
    """
    画像生成 + テキストオーバーレイの統合処理

    Args:
        prompt: 画像生成プロンプト
        text_overlay: オーバーレイするテキスト
        output_path: 保存先パス
    """
    # Step 1: 画像生成
    image_bytes = generate_base_image(prompt, width=1024, height=1536)

    if not image_bytes:
        return False

    # Step 2: テキストオーバーレイ
    success = add_text_overlay(image_bytes, text_overlay, output_path)

    return success


def generate_slides_from_json(json_path: str, output_dir: str):
    """
    JSONファイルから6枚のスライド画像を生成

    Args:
        json_path: slide_prompts.json のパス
        output_dir: 画像保存先ディレクトリ
    """
    print(f"\n🚀 スライド生成開始")
    print(f"📂 入力: {json_path}")
    print(f"📂 出力: {output_dir}")
    print(f"⚙️  設定: リトライ{MAX_RETRIES}回、スライド間待機{REQUEST_INTERVAL}秒")
    print("-" * 60)

    # JSONファイル読み込み
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 出力ディレクトリ作成
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # 各スライド画像を生成
    slides = data["slides"]
    success_count = 0
    failed_slides = []

    start_time = time.time()

    for i, slide in enumerate(slides):
        slide_num = slide["slide_number"]
        text_overlay = slide["text_overlay"]
        image_prompt = slide["image_prompt"]

        # 出力ファイル名
        output_path = f"{output_dir}/slide_{slide_num:02d}.png"

        print(f"\n📸 スライド {slide_num}/{len(slides)} 生成中...")

        # 画像生成
        success = generate_slide_image(
            prompt=image_prompt,
            text_overlay=text_overlay,
            output_path=output_path
        )

        if success:
            success_count += 1
        else:
            failed_slides.append(slide_num)

        print("-" * 60)

        # 次のスライドまで待機（最後のスライド以外）
        if i < len(slides) - 1:
            print(f"⏳ 次のスライドまで {REQUEST_INTERVAL}秒待機...")
            time.sleep(REQUEST_INTERVAL)

    elapsed_time = time.time() - start_time

    print(f"\n✅ 完了: {success_count}/{len(slides)} 枚の画像を生成しました")
    print(f"⏱️  処理時間: {elapsed_time:.1f}秒")

    if failed_slides:
        print(f"❌ 失敗したスライド: {failed_slides}")

    if success_count == len(slides):
        print("🎉 すべての画像生成に成功しました！")
        return True
    else:
        print(f"⚠️  {len(slides) - success_count} 枚の画像生成に失敗しました")
        return False


if __name__ == "__main__":
    # コマンドライン引数
    if len(sys.argv) < 3:
        print("使用方法: python generate_images_cloudflare.py <slide_prompts.json> <output_dir>")
        print("例: python generate_images_cloudflare.py ~/robby_content/post_001/slide_prompts.json ~/robby_content/post_001/images/")
        sys.exit(1)

    json_path = sys.argv[1]
    output_dir = sys.argv[2]

    if not os.path.exists(json_path):
        print(f"❌ エラー: {json_path} が見つかりません")
        sys.exit(1)

    # 画像生成実行
    success = generate_slides_from_json(json_path, output_dir)

    sys.exit(0 if success else 1)
