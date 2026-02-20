#!/usr/bin/env python3
"""
Imagen 4 API テストスクリプト
"""

import os
import sys
import json
import requests
import base64

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

def test_imagen_generation():
    """Imagen 4で簡単な画像生成テスト"""

    print("🧪 Imagen 4 API テスト開始...")

    # APIエンドポイント（Imagen 4 Fast）
    model = "imagen-4.0-fast-generate-001"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateImages?key={GOOGLE_API_KEY}"

    # テストプロンプト
    test_prompt = """
    日本の病院の一般病棟。明るい照明。白い壁。
    ナースステーション前の廊下から撮影したような構図。
    奥にナースステーションのカウンター、電子カルテのPC画面が2台。
    壁に掲示板、シフト表。右手にワゴン。
    リアルなスマホ写真風の画質。やや暖かい照明。縦向き。
    アニメ調やイラスト調にしない。実写風。

    画面中央やや下に半透明の黒い帯があり、
    その上に白い太字ゴシック体で日本語テキスト
    「これはテストです」が表示されている。
    """

    # リクエストペイロード
    payload = {
        "prompt": test_prompt.strip(),
        "number_of_images": 1,
        "aspect_ratio": "9:16",  # 縦型
        "safety_filter_level": "block_some",
        "person_generation": "allow_adult"
    }

    headers = {
        "Content-Type": "application/json"
    }

    print(f"📤 APIリクエスト送信...")
    print(f"   モデル: {model}")
    print(f"   プロンプト長: {len(test_prompt)} 文字")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)

        print(f"📥 レスポンス受信: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ 成功！")
            print(f"レスポンス構造: {json.dumps(result, indent=2, ensure_ascii=False)[:500]}...")

            # 画像データを保存
            if "generatedImages" in result:
                images = result["generatedImages"]
                print(f"📸 生成された画像数: {len(images)}")

                for i, img_data in enumerate(images):
                    # base64デコードして保存
                    if "image" in img_data and "bytesBase64Encoded" in img_data["image"]:
                        image_b64 = img_data["image"]["bytesBase64Encoded"]
                        image_bytes = base64.b64decode(image_b64)

                        output_path = f"/Users/robby2/robby_content/test_images/test_{i+1}.png"
                        with open(output_path, "wb") as f:
                            f.write(image_bytes)

                        print(f"✅ 画像保存: {output_path}")
                        print(f"   サイズ: {len(image_bytes) / 1024:.1f} KB")

                return True
            else:
                print(f"⚠️  レスポンスに画像データが含まれていません")
                return False

        else:
            print(f"❌ エラー: {response.status_code}")
            print(f"レスポンス: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 例外エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_imagen_generation()
    sys.exit(0 if success else 1)
