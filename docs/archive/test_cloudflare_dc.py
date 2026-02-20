#!/usr/bin/env python3
"""
Cloudflare Workers AI テストスクリプト（改善版）
- レスポンスタイプ判定
- 詳細なエラー情報
"""

import os
import sys
import requests
import json

CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")

def test_cloudflare_api():
    """Cloudflare Workers AI API接続テスト（改善版）"""

    print("🧪 Cloudflare Workers AI 接続テスト開始...")

    if not CLOUDFLARE_API_TOKEN or not CLOUDFLARE_ACCOUNT_ID:
        print("❌ エラー: 環境変数が設定されていません")
        print("設定方法:")
        print("  export CLOUDFLARE_API_TOKEN='your-token'")
        print("  export CLOUDFLARE_ACCOUNT_ID='your-account-id'")
        return False

    print(f"   Account ID: {CLOUDFLARE_ACCOUNT_ID[:8]}...")
    print(f"   API Token: {CLOUDFLARE_API_TOKEN[:8]}...")

    # FLUX.1-schnellモデルでテスト
    MODEL = "@cf/black-forest-labs/flux-1-schnell"
    API_URL = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{MODEL}"

    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    # シンプルなテストプロンプト
    payload = {
        "prompt": "A beautiful Japanese hospital corridor with warm lighting, realistic photo style, vertical orientation",
        "num_steps": 4,
        "guidance": 7.5,
        "width": 512,  # テストなので小さめ
        "height": 768
    }

    print(f"\n📤 APIリクエスト送信...")
    print(f"   エンドポイント: {API_URL}")
    print(f"   プロンプト: {payload['prompt'][:50]}...")

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=90)

        print(f"📥 レスポンス受信: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('Content-Type', 'N/A')}")

        if response.status_code == 200:
            content_type = response.headers.get("Content-Type", "")
            image_bytes = response.content

            # レスポンスタイプを判定
            if "image" in content_type or len(image_bytes) > 10000:
                # 画像データ
                output_path = "/Users/robby2/robby_content/test_images/cloudflare_test.png"

                # ディレクトリが存在するか確認
                os.makedirs(os.path.dirname(output_path), exist_ok=True)

                with open(output_path, "wb") as f:
                    f.write(image_bytes)

                print(f"✅ 成功！画像生成できました")
                print(f"   保存先: {output_path}")
                print(f"   サイズ: {len(image_bytes) / 1024:.1f} KB")
                return True
            else:
                # JSONレスポンス
                print(f"⚠️  予期しないレスポンス（{len(image_bytes)} bytes）")
                try:
                    result = json.loads(response.content)
                    print(f"   JSON内容: {json.dumps(result, indent=2, ensure_ascii=False)}")
                except:
                    print(f"   内容: {response.content[:500]}")
                return False

        elif response.status_code == 429:
            print(f"❌ レート制限エラー（429）")
            print(f"   Retry-After: {response.headers.get('Retry-After', 'N/A')}秒")
            try:
                error_data = response.json()
                print(f"   詳細: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
            except:
                print(f"   レスポンス: {response.text[:500]}")
            return False

        else:
            print(f"❌ エラー: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   詳細: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
            except:
                print(f"   レスポンス: {response.text[:500]}")
            return False

    except requests.exceptions.Timeout:
        print(f"❌ タイムアウトエラー（90秒）")
        return False

    except Exception as e:
        print(f"❌ 例外エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_cloudflare_api()
    sys.exit(0 if success else 1)
