#!/usr/bin/env python3
"""
LINE Bot フロー テストシミュレータ

社長が自分で LINE 友だち追加できない場合の代替テスト手段。
LINE webhook に正規の署名付きで follow / message イベントをPOSTし、
Worker の反応をログで確認する。

【使い方】
  # 1) LP診断経由 → matching_preview フローをテスト
  python3 scripts/test_line_flow.py shindan_to_matching

  # 2) 通常の新規 follow → intake_qual をテスト
  python3 scripts/test_line_flow.py plain_follow

  # 3) 履歴書 API をテスト
  python3 scripts/test_line_flow.py resume

【確認方法】
- Slack #ロビー小田原人材紹介 に通知が飛ぶか確認
- Cloudflare Workers の tail ログを `wrangler tail` で追跡
- KVの該当セッションデータを確認

【注意】
- このスクリプトは Bot 側の動作を「本物のfollow/messageイベント」として実行する
- ブロック済みアカウントを解除する等の副作用はない
- テストユーザーIDは `U_TEST_` プレフィックスで固定（実ユーザーとは区別）
"""
import os
import sys
import json
import hmac
import hashlib
import base64
import time
import uuid
import urllib.request
import urllib.parse
from pathlib import Path

# .env 読み込み
env = {}
ENV_PATH = Path(__file__).parent.parent / ".env"
for line in ENV_PATH.read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()

LINE_CHANNEL_SECRET = env.get("LINE_CHANNEL_SECRET", "")
WORKER_BASE = "https://robby-the-match-api.robby-the-robot-2026.workers.dev"
TEST_USER_ID = "U_TEST_" + uuid.uuid4().hex[:24]  # 32文字のテストユーザーID


def sign_body(body: bytes) -> str:
    """LINE webhook 署名生成（X-Line-Signature ヘッダ用）"""
    h = hmac.new(LINE_CHANNEL_SECRET.encode(), body, hashlib.sha256).digest()
    return base64.b64encode(h).decode()


def send_webhook(event: dict) -> None:
    """LINE webhook 形式のイベントを Worker に POST"""
    payload = {
        "destination": "TEST_BOT",
        "events": [event],
    }
    body = json.dumps(payload).encode()
    sig = sign_body(body)
    req = urllib.request.Request(
        f"{WORKER_BASE}/api/line-webhook",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Line-Signature": sig,
            "User-Agent": "LineBotWebhook/2.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            print(f"  HTTP {res.status} | {res.read().decode()[:100]}")
    except urllib.error.HTTPError as e:
        print(f"  ❌ HTTP {e.code} | {e.read().decode()[:200]}")


def make_line_start_session(answers: dict) -> str:
    """LP診断回答を /api/line-start に渡してセッション作成→session_id を返す"""
    sid = str(uuid.uuid4())
    params = urllib.parse.urlencode({
        "session_id": sid,
        "source": "shindan",
        "intent": "diagnose",
        "area": answers.get("area", ""),
        "answers": json.dumps(answers),
        "page_type": "paid_lp",
    })
    req = urllib.request.Request(
        f"{WORKER_BASE}/api/line-start?{params}",
        method="GET",
        headers={"User-Agent": "Mozilla/5.0 (LineBot Test)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            # 302 redirect を受け取る（follow前段）
            print(f"  /api/line-start: HTTP {res.status}")
    except urllib.error.HTTPError as e:
        if e.code in (302, 303):
            print(f"  /api/line-start: HTTP {e.code} (redirect) OK")
        else:
            print(f"  /api/line-start ERROR: {e.code}")
    return sid


def test_shindan_to_matching():
    """LP診断完了 → follow → matching_preview フロー"""
    print("=" * 60)
    print("🧪 テスト: LP診断経由 → follow → matching_preview")
    print(f"   TestUserId: {TEST_USER_ID}")
    print("=" * 60)

    # Step 1: LP診断回答を session 保存
    answers = {
        "prefecture": "kanagawa",
        "area": "yokohama_kawasaki",
        "areaLabel": "横浜・川崎",
        "facilityType": "hospital",
        "workstyle": "day",
        "urgency": "three_months",
    }
    print("\n[Step 1] LP /api/line-start で診断回答を保存")
    sid = make_line_start_session(answers)
    print(f"  session_id: {sid}")

    # Step 2: LIFFリンクシミュレート (/api/link-session)
    print("\n[Step 2] LIFF で userId と session を紐付け")
    body = json.dumps({
        "session_id": sid,
        "user_id": TEST_USER_ID,
        "already_friend": False,
    }).encode()
    req = urllib.request.Request(
        f"{WORKER_BASE}/api/link-session",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (LineBot Test)",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            print(f"  HTTP {res.status} | {res.read().decode()[:150]}")
    except urllib.error.HTTPError as e:
        print(f"  ❌ HTTP {e.code} | {e.read().decode()[:200]}")

    time.sleep(1)

    # Step 3: LINE follow イベント送信
    print("\n[Step 3] follow イベントを webhook に送信")
    follow_event = {
        "type": "follow",
        "timestamp": int(time.time() * 1000),
        "source": {"type": "user", "userId": TEST_USER_ID},
        "replyToken": "test-reply-token-" + uuid.uuid4().hex[:16],
        "mode": "active",
        "webhookEventId": "test-" + uuid.uuid4().hex,
        "deliveryContext": {"isRedelivery": False},
    }
    send_webhook(follow_event)

    print("\n✅ 送信完了")
    print("  Slack #ロビー小田原人材紹介 を確認:")
    print(f"    - 💬 LINE新規友だち追加（ユーザーID: {TEST_USER_ID}）")
    print("    - 📝 Q2/Q3回答 等のトラッキング")
    print("    - matching_preview Flex カード送信試行（replyToken無効なので失敗するが、KV保存は行われる）")
    print(f"\n  KV確認: line:{TEST_USER_ID} にエントリー作成されているはず")


def test_plain_follow():
    """LP経由なしの新規follow → intake_qual"""
    print("=" * 60)
    print("🧪 テスト: 新規友だち追加 → intake_qual（資格QR）")
    print(f"   TestUserId: {TEST_USER_ID}")
    print("=" * 60)

    print("\n[Step 1] follow イベントを webhook に送信（LIFF session なし）")
    follow_event = {
        "type": "follow",
        "timestamp": int(time.time() * 1000),
        "source": {"type": "user", "userId": TEST_USER_ID},
        "replyToken": "test-reply-token-" + uuid.uuid4().hex[:16],
        "mode": "active",
        "webhookEventId": "test-" + uuid.uuid4().hex,
        "deliveryContext": {"isRedelivery": False},
    }
    send_webhook(follow_event)

    print("\n✅ 送信完了")
    print("  Slack 確認: 💬 LINE新規友だち追加 + 💼 保有資格Q 送信試行")


def test_resume():
    """履歴書作成APIテスト"""
    print("=" * 60)
    print("🧪 テスト: 履歴書作成 API")
    print("=" * 60)

    data = {
        "lastName": "看護", "firstName": "太郎",
        "lastNameFurigana": "かんご", "firstNameFurigana": "たろう",
        "birthDate": "1990-05-20", "gender": "男", "phone": "080-0000-0000",
        "postalCode": "231-0001", "address": "神奈川県横浜市中区本町1-1-1",
        "addressFurigana": "かながわけん よこはまし なかく ほんちょう",
        "education": [{"edu_year": "2012", "edu_month": "3", "edu_desc": "○○看護大学 卒業"}],
        "career": [{"car_start_year": "2012", "car_start_month": "4", "car_facility": "△△病院",
                    "car_detail": "急性期内科病棟 配属"}],
        "licenses": [{"lic_year": "2012", "lic_month": "3", "lic_name": "正看護師免許 取得"}],
        "hint_change": "夜勤が多くて体力的にキツい",
        "hint_strengths": "急性期判断力、チームリーダー経験",
        "hint_wishes": "ワークライフバランス重視",
        "wishes": "横浜市内・日勤中心",
    }
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        f"{WORKER_BASE}/api/resume-generate",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (LineBot Test)",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            d = json.loads(res.read().decode())
            print(f"\n✅ HTTP {res.status}")
            print(f"  履歴書ID: {d.get('id')}")
            print(f"  URL: {d.get('url')}")
            print(f"\n  ブラウザで開いて確認してください:")
            print(f"  {d.get('url')}")
    except urllib.error.HTTPError as e:
        print(f"  ❌ HTTP {e.code} | {e.read().decode()[:200]}")


def main():
    if not LINE_CHANNEL_SECRET:
        print("❌ LINE_CHANNEL_SECRET が .env に無い")
        sys.exit(1)

    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "shindan_to_matching":
        test_shindan_to_matching()
    elif cmd == "plain_follow":
        test_plain_follow()
    elif cmd == "resume":
        test_resume()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
