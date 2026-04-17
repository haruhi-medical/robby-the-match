#!/usr/bin/env python3
"""
Slack通知スクリプト
台本JSONの内容をSlackに通知（承認依頼）
Bot Token使用版

【DEPRECATED】(Phase 3 #60 判定)
このスクリプトは 11+ のスクリプトから subprocess 経由で呼ばれているため、
完全統合は影響範囲が広すぎる（NS寄与度2に対してコストが高い）。
新規開発では scripts/slack_utils.py の send_message() を直接使うこと。
"""

import argparse
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import requests

# プロジェクトルート
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")

# Slack Bot Token
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID", "C0AEG626EUW")

if not SLACK_BOT_TOKEN:
    print("❌ エラー: SLACK_BOT_TOKEN が.envに設定されていません")
    sys.exit(1)


# ノイズ抑制フィルター: これらのパターンを含むメッセージはSlack送信しない
SUPPRESSED_PATTERNS = [
    "タスク完了（未コミット変更あり）",
    "タスク完了(未コミット変更あり)",
    "diagnostic test",
]


def send_slack_notification(json_path: Path = None, message: str = None):
    """
    Slackに通知を送信

    Args:
        json_path: 台本JSONファイルパス（台本通知の場合）
        message: カスタムメッセージ（シンプル通知の場合）
    """
    # ノイズ抑制
    if message:
        for pattern in SUPPRESSED_PATTERNS:
            if pattern in message:
                print(f"[SUPPRESSED] {message[:60]}")
                return

    if json_path:
        # 台本JSONを読み込んで詳細通知
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        content_id = data.get("id", "UNKNOWN")
        category = data.get("category", "不明")
        hook = data.get("hook", "")
        caption = data.get("caption", "")
        hashtags = " ".join(data.get("hashtags", []))
        slides = data.get("slides", [])
        base_image = data.get("base_image", "")

        # スライドパス
        today = json_path.stem.split('_')[0]  # JSONファイル名から日付を抽出
        slides_dir = project_root / "content" / "generated" / f"{today}_{content_id}"

        # Slack Block Kit形式で通知
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📱 ROBBY 投稿準備完了"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*ID:* {content_id}\n*カテゴリ:* {category}\n*フック:* {hook}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*キャプション:*\n{caption}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*ハッシュタグ:* {hashtags}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*ベース画像:* {base_image}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*スライド:* 6枚生成済み\n📂 `{slides_dir.relative_to(project_root)}`"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*6枚のテキスト:*"
                }
            }
        ]

        # 各スライドのテキストを追加
        for i, slide_text in enumerate(slides, start=1):
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"`{i}枚目:` {slide_text}"
                }
            })

        payload = {"blocks": blocks}

    elif message:
        # シンプルなメッセージ通知
        payload = {"text": message, "channel": SLACK_CHANNEL_ID}

    else:
        print("❌ エラー: --json または --message のいずれかが必要です")
        sys.exit(1)

    # Slackに送信（Bot Token使用）
    last_error = ""
    try:
        headers = {
            "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
            "Content-Type": "application/json"
        }

        # chat.postMessage APIエンドポイント
        if "blocks" in payload:
            payload["channel"] = SLACK_CHANNEL_ID

        response = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers=headers,
            json=payload,
            timeout=10
        )

        data = response.json()
        if data.get("ok"):
            print("✅ Slack通知送信完了")
            if json_path:
                print(f"   ID: {content_id}")
            return True
        last_error = f"slack_api_{data.get('error', 'unknown')}"
        print(f"❌ Slack通知失敗: {data.get('error', 'unknown')}")

    except Exception as e:
        last_error = f"exception_{type(e).__name__}"
        print(f"❌ エラー: {type(e).__name__}: {e}")

    # Phase 3 #63: 送信失敗時は alert_queue.json にキュー（slack_retry.py が再送）
    try:
        from slack_utils import _enqueue_alert  # type: ignore
        text_for_queue = payload.get("text") or "(台本通知)"
        _enqueue_alert(
            payload.get("channel") or SLACK_CHANNEL_ID,
            text_for_queue,
            blocks=payload.get("blocks"),
            thread_ts=None,
            last_error=last_error,
        )
    except Exception as e:
        print(f"alert_queue.json enqueue 失敗: {e}")
    return False


def main():
    parser = argparse.ArgumentParser(description="Slackに通知を送信")
    parser.add_argument("--json", help="台本JSONファイルパス")
    parser.add_argument("--message", help="カスタムメッセージ")

    args = parser.parse_args()

    json_path = Path(args.json) if args.json else None
    message = args.message

    if json_path and not json_path.exists():
        print(f"❌ エラー: JSONファイルが見つかりません: {json_path}")
        sys.exit(1)

    success = send_slack_notification(json_path=json_path, message=message)

    if success:
        print("\n✅ 処理完了")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
