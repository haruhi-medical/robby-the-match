#!/usr/bin/env python3
"""
Google Gemini API (Imagen) を使った画像生成スクリプト
神奈川ナース転職 - SNS投稿用スライドショー画像生成
"""

import os
import json
import sys
import requests
from pathlib import Path
from datetime import datetime

# 設定
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("❌ エラー: GOOGLE_API_KEY 環境変数が設定されていません")
    print("設定方法: export GOOGLE_API_KEY='your-api-key'")
    sys.exit(1)

# Imagen 3 API エンドポイント（Vertex AI経由）
# 注: 実際のエンドポイントはAPIキー取得後に確認する必要があります
IMAGEN_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0:generateImage"

# または Google AI Studio 経由の場合
GEMINI_API_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent?key={GOOGLE_API_KEY}"


def generate_image_with_text_overlay(prompt: str, text_overlay: str, output_path: str, size: str = "1024x1536"):
    """
    画像生成 + テキストオーバーレイ

    Args:
        prompt: 画像生成プロンプト
        text_overlay: 画像上に表示するテキスト
        output_path: 保存先パス
        size: 画像サイズ（デフォルト: 1024x1536）
    """
    print(f"🎨 画像生成中: {output_path}")
    print(f"📝 テキスト: {text_overlay[:30]}...")

    # プロンプトにテキストオーバーレイの指示を追加
    full_prompt = f"{prompt}\n\n画像中央に半透明の黒い帯があり、その上に白い太字ゴシック体で以下の日本語テキストが表示されている：\n\n「{text_overlay}」"

    # Google Imagen API呼び出し
    # 注: 実際のAPI仕様に合わせて修正が必要
    headers = {
        "Content-Type": "application/json",
    }

    payload = {
        "prompt": full_prompt,
        "num_images": 1,
        "size": size,
        "response_format": "url"  # または "b64_json"
    }

    try:
        # APIリクエスト
        # 注: エンドポイントとペイロード形式は実際のAPIドキュメントに従って調整
        response = requests.post(
            f"{IMAGEN_API_ENDPOINT}?key={GOOGLE_API_KEY}",
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code == 200:
            result = response.json()
            # 画像URLまたはbase64データを取得
            image_url = result.get("images", [{}])[0].get("url")

            if image_url:
                # 画像をダウンロード
                img_response = requests.get(image_url, timeout=30)
                if img_response.status_code == 200:
                    with open(output_path, "wb") as f:
                        f.write(img_response.content)
                    print(f"✅ 保存完了: {output_path}")
                    return True
            else:
                print(f"❌ エラー: 画像URLが取得できませんでした")
                return False
        else:
            print(f"❌ API エラー: {response.status_code}")
            print(f"レスポンス: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 例外エラー: {e}")
        return False


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
    print("-" * 60)

    # JSONファイル読み込み
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 出力ディレクトリ作成
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # 各スライド画像を生成
    slides = data["slides"]
    success_count = 0

    for slide in slides:
        slide_num = slide["slide_number"]
        text_overlay = slide["text_overlay"]
        image_prompt = slide["image_prompt"]

        # 出力ファイル名
        output_path = f"{output_dir}/slide_{slide_num:02d}.png"

        # 画像生成
        success = generate_image_with_text_overlay(
            prompt=image_prompt,
            text_overlay=text_overlay,
            output_path=output_path,
            size="1024x1536"
        )

        if success:
            success_count += 1

        print("-" * 60)

    print(f"\n✅ 完了: {success_count}/{len(slides)} 枚の画像を生成しました")

    if success_count == len(slides):
        print("🎉 すべての画像生成に成功しました！")
        return True
    else:
        print(f"⚠️  {len(slides) - success_count} 枚の画像生成に失敗しました")
        return False


if __name__ == "__main__":
    # コマンドライン引数
    if len(sys.argv) < 3:
        print("使用方法: python generate_images_gemini.py <slide_prompts.json> <output_dir>")
        print("例: python generate_images_gemini.py ~/robby_content/post_001/slide_prompts.json ~/robby_content/post_001/images/")
        sys.exit(1)

    json_path = sys.argv[1]
    output_dir = sys.argv[2]

    if not os.path.exists(json_path):
        print(f"❌ エラー: {json_path} が見つかりません")
        sys.exit(1)

    # 画像生成実行
    success = generate_slides_from_json(json_path, output_dir)

    sys.exit(0 if success else 1)
