#!/usr/bin/env python3
"""
LINEリッチメニュー登録スクリプト (v3: 5タイル - 大バナー/NEW/MYPAGE/CONTACT/SUPPORT)

手順:
1. richmenu作成 → richMenuId取得
2. 画像アップロード (PNG 2500x1686)
3. デフォルトに設定
4. 新richMenuIdを出力 (Cloudflare Workerの RICH_MENU_DEFAULT secret に設定)
"""
import os
import sys
import json
from pathlib import Path

# .env読み込み
ENV_PATH = Path(__file__).parent.parent / ".env"
if ENV_PATH.exists():
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

import urllib.request
import urllib.error

TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
if not TOKEN:
    print("ERROR: LINE_CHANNEL_ACCESS_TOKEN not set in .env", file=sys.stderr)
    sys.exit(1)

IMAGE_PATH = Path(__file__).parent.parent / "assets/richmenu/richmenu_v3_20260423.png"
if not IMAGE_PATH.exists():
    print(f"ERROR: image not found: {IMAGE_PATH}", file=sys.stderr)
    sys.exit(1)

# リッチメニュー定義 (2500x1686 5タイル)
richmenu = {
    "size": {"width": 2500, "height": 1686},
    "selected": True,
    "name": "NurseLobby_Default_v3_20260423",
    "chatBarText": "メニュー",
    "areas": [
        {
            "bounds": {"x": 0, "y": 0, "width": 1648, "height": 884},
            "action": {"type": "postback", "data": "rm=start", "displayText": "お仕事探しをスタート"}
        },
        {
            "bounds": {"x": 1648, "y": 0, "width": 852, "height": 884},
            "action": {"type": "postback", "data": "rm=new_jobs", "displayText": "本日の新着求人"}
        },
        {
            "bounds": {"x": 0, "y": 884, "width": 832, "height": 802},
            "action": {"type": "postback", "data": "rm=mypage", "displayText": "マイページ"}
        },
        {
            "bounds": {"x": 832, "y": 884, "width": 809, "height": 802},
            "action": {"type": "postback", "data": "rm=contact", "displayText": "担当に相談する"}
        },
        {
            "bounds": {"x": 1641, "y": 884, "width": 859, "height": 802},
            "action": {"type": "postback", "data": "rm=resume", "displayText": "履歴書作成"}
        },
    ]
}

def api_request(method, url, data=None, headers=None, is_data_api=False):
    headers = dict(headers or {})
    headers["Authorization"] = f"Bearer {TOKEN}"
    if isinstance(data, dict):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        headers.setdefault("Content-Type", "application/json; charset=utf-8")
    else:
        body = data  # bytes or None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            raw = res.read().decode("utf-8")
            return res.status, raw
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}", file=sys.stderr)
        sys.exit(1)

# Step 1: 既存デフォルトメニューを取得して一覧表示
print("[1/5] 既存リッチメニュー一覧")
code, body = api_request("GET", "https://api.line.me/v2/bot/richmenu/list")
data = json.loads(body)
for m in data.get("richmenus", []):
    print(f"  - {m['richMenuId']}  name={m['name']}")

# Step 2: 新規リッチメニュー作成
print("\n[2/5] 新規リッチメニュー作成")
code, body = api_request("POST", "https://api.line.me/v2/bot/richmenu", data=richmenu)
new_menu_id = json.loads(body)["richMenuId"]
print(f"  ✅ richMenuId: {new_menu_id}")

# Step 3: 画像アップロード
print("\n[3/5] 画像アップロード")
img_bytes = IMAGE_PATH.read_bytes()
print(f"  size: {len(img_bytes):,} bytes")
code, body = api_request(
    "POST",
    f"https://api-data.line.me/v2/bot/richmenu/{new_menu_id}/content",
    data=img_bytes,
    headers={"Content-Type": "image/png"},
    is_data_api=True,
)
print(f"  ✅ uploaded (HTTP {code})")

# Step 4: デフォルトに設定
print("\n[4/5] デフォルトリッチメニューに設定")
code, body = api_request("POST", f"https://api.line.me/v2/bot/user/all/richmenu/{new_menu_id}")
print(f"  ✅ default set (HTTP {code})")

# Step 5: 新IDを出力
print("\n[5/5] 完了")
print(f"\n=== 新リッチメニューID ===")
print(new_menu_id)
print("\n次にやること:")
print(f"  cd api && unset CLOUDFLARE_API_TOKEN && \\")
print(f"    echo -n '{new_menu_id}' | npx wrangler secret put RICH_MENU_DEFAULT --config wrangler.toml")
print(f"\nその後Worker再デプロイは不要（secret更新で自動反映）")
