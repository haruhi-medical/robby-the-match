#!/usr/bin/env python3
"""
post_001の背景画像を6枚生成
Cloudflare Workers AI (FLUX.1-schnell) を使用
"""
import os
import requests
import base64
import json
from pathlib import Path
from PIL import Image
from io import BytesIO
import time

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

# 背景画像用のプロンプト（テキストオーバーレイを除外）
# 全て同じ病院の廊下の背景を使用
background_prompt = """
Japanese hospital general ward. Bright lighting. White walls. Shot from hospital hallway in front of nurses' station.
Nurses' station counter in the background, 2 electronic medical record PC screens visible.
Bulletin board and shift schedule on the wall. Medical cart on the right side.
Realistic smartphone photo quality. Slightly warm lighting. Vertical orientation (portrait).
Photorealistic style, NOT anime or illustration style. Real photo look.
High quality, 4k, professional photography.
"""

# 出力ディレクトリ
output_dir = Path("/Users/robby2/robby_content/post_001/backgrounds")
output_dir.mkdir(parents=True, exist_ok=True)

print("=" * 60)
print("Post #001 背景画像生成スタート")
print("=" * 60)
print(f"出力先: {output_dir}")
print(f"モデル: FLUX.1-schnell (Cloudflare Workers AI)")
print()

# 6枚の画像を生成
for i in range(1, 7):
    print(f"[{i}/6] スライド{i}の背景画像を生成中...")

    payload = {
        "prompt": background_prompt.strip()
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)

        if response.status_code == 200:
            data = response.json()

            if "result" in data and "image" in data["result"]:
                # base64デコード
                base64_image = data["result"]["image"]
                image_bytes = base64.b64decode(base64_image)

                # Pillowで開いてPNG形式で保存
                img = Image.open(BytesIO(image_bytes))

                # 縦向き（1024x1536）にリサイズ
                # FLUX.1-schnellは正方形（1024x1024）で生成するので、縦長に調整
                if img.size != (1024, 1536):
                    print(f"  サイズ調整: {img.size} -> (1024, 1536)")
                    # 中央クロップして縦長に
                    # とりあえず上下に余白を追加する方式
                    new_img = Image.new('RGB', (1024, 1536), (255, 255, 255))
                    # 中央に配置
                    offset = (1536 - 1024) // 2
                    new_img.paste(img, (0, offset))
                    img = new_img

                output_file = output_dir / f"slide_{i:02d}_bg.png"
                img.save(output_file, "PNG")

                print(f"  ✅ 保存完了: {output_file.name}")
                print(f"  サイズ: {img.size}, フォーマット: PNG")
            else:
                print(f"  ❌ エラー: 予期しないJSON構造")
                print(f"  Response: {json.dumps(data, indent=2)[:200]}")
        else:
            print(f"  ❌ HTTPエラー: {response.status_code}")
            print(f"  Response: {response.text[:200]}")

    except Exception as e:
        print(f"  ❌ 例外発生: {e}")

    # レート制限対策（少し待つ）
    if i < 6:
        time.sleep(2)

    print()

print("=" * 60)
print("✅ 背景画像生成完了！")
print("=" * 60)
print(f"保存先: {output_dir}")
print()
print("次のステップ:")
print("1. 生成された背景画像を確認")
print("2. Pillowで日本語テキストを合成")
