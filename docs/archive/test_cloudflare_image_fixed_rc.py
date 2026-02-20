#!/usr/bin/env python3
"""
Cloudflare Workers AIで画像生成テスト（修正版）
JSONをパースしてbase64デコード
"""
import os
import requests
import base64
import json
from pathlib import Path
from PIL import Image
from io import BytesIO

# Cloudflare APIの設定
CLOUDFLARE_API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID")

if not CLOUDFLARE_API_TOKEN or not CLOUDFLARE_ACCOUNT_ID:
    print("Error: CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID must be set")
    exit(1)

# Workers AI エンドポイント
url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/@cf/black-forest-labs/flux-1-schnell"

headers = {
    "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
    "Content-Type": "application/json"
}

# テスト用のシンプルなプロンプト
payload = {
    "prompt": "A simple blue sky with white clouds, photorealistic, 4k quality"
}

print("Cloudflare Workers AIで画像生成中...")

response = requests.post(url, headers=headers, json=payload)

print(f"Status Code: {response.status_code}")

if response.status_code == 200:
    # JSONをパース
    try:
        data = response.json()
        print(f"Response keys: {data.keys()}")

        # base64エンコードされた画像データを取得
        if "result" in data and "image" in data["result"]:
            base64_image = data["result"]["image"]
            print(f"Base64画像データの長さ: {len(base64_image)} 文字")
            print(f"Base64先頭: {base64_image[:50]}...")

            # base64デコード
            image_bytes = base64.b64decode(base64_image)
            print(f"デコード後のバイトサイズ: {len(image_bytes)} bytes")
            print(f"ファイル先頭バイト: {image_bytes[:20].hex()}")

            output_dir = Path("/Users/robby2/robby_content/test_images")
            output_dir.mkdir(exist_ok=True)

            # 1. まずそのまま保存（元のフォーマット）
            output_file_raw = output_dir / "cloudflare_test_decoded.jpg"
            with open(output_file_raw, "wb") as f:
                f.write(image_bytes)
            print(f"✅ デコード済み画像を保存: {output_file_raw}")

            # 2. Pillowで開いてPNGとして保存し直す
            img = Image.open(BytesIO(image_bytes))
            print(f"画像情報: フォーマット={img.format}, サイズ={img.size}, モード={img.mode}")

            output_file_png = output_dir / "cloudflare_test_fixed.png"
            img.save(output_file_png, "PNG")
            print(f"✅ PNG形式で保存: {output_file_png}")

            print("\n✅ 成功！Pillowで開き直してPNGとして保存しました")

        else:
            print(f"❌ Error: 予期しないJSON構造")
            print(f"Response: {json.dumps(data, indent=2)}")

    except json.JSONDecodeError as e:
        print(f"❌ JSONパースエラー: {e}")
        print(f"Response (先頭500文字): {response.text[:500]}")

else:
    print(f"❌ Error: {response.status_code}")
    print(f"Response: {response.text}")
