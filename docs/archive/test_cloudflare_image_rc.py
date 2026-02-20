#!/usr/bin/env python3
"""
Cloudflare Workers AIで画像生成テスト
"""
import os
import requests
import base64
from pathlib import Path

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
print(f"URL: {url}")

response = requests.post(url, headers=headers, json=payload)

print(f"Status Code: {response.status_code}")
print(f"Response Headers: {dict(response.headers)}")

if response.status_code == 200:
    # バイナリデータとして保存
    output_dir = Path("/Users/robby2/robby_content/test_images")
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / "cloudflare_test_raw.png"

    with open(output_file, "wb") as f:
        f.write(response.content)

    print(f"✅ 画像を保存しました: {output_file}")
    print(f"ファイルサイズ: {len(response.content)} bytes")

    # ファイルの最初の数バイトを確認（PNGヘッダー確認）
    print(f"ファイル先頭バイト: {response.content[:20].hex()}")

else:
    print(f"❌ Error: {response.status_code}")
    print(f"Response: {response.text}")
