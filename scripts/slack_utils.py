#!/usr/bin/env python3
"""
Slack共通ユーティリティ v1.0
Bot Token対応でメッセージ送信・スレッド返信読み取り・プレビューts保存を行う。
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
import requests

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
SLACK_CHANNEL_REPORT = os.getenv("SLACK_CHANNEL_REPORT", os.getenv("SLACK_CHANNEL_ID", "C0AEG626EUW"))
SLACK_CHANNEL_POST_REVIEW = os.getenv("SLACK_CHANNEL_POST_REVIEW", os.getenv("SLACK_CHANNEL_ID", "C0AEG626EUW"))

PREVIEW_TS_FILE = PROJECT_ROOT / "data" / "preview_messages.json"


def _headers():
    return {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json",
    }


def send_message(channel: str, text: str, blocks: list = None, thread_ts: str = None) -> dict:
    """Slack Bot Tokenでメッセージ送信。失敗時はWebhookフォールバック。tsを返す。"""
    if SLACK_BOT_TOKEN:
        payload = {"channel": channel, "text": text}
        if blocks:
            payload["blocks"] = blocks
        if thread_ts:
            payload["thread_ts"] = thread_ts
        try:
            resp = requests.post(
                "https://slack.com/api/chat.postMessage",
                headers=_headers(),
                json=payload,
                timeout=15,
            )
            data = resp.json()
            if data.get("ok"):
                return {"ok": True, "ts": data.get("ts", "")}
            print(f"Slack Bot送信エラー: {data.get('error')}", file=sys.stderr)
        except Exception as e:
            print(f"Slack Bot接続エラー: {e}", file=sys.stderr)

    # Webhookフォールバック
    if SLACK_WEBHOOK_URL:
        try:
            payload = {"text": text}
            resp = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=15)
            if resp.status_code == 200:
                return {"ok": True, "ts": ""}
        except Exception as e:
            print(f"Webhook送信エラー: {e}", file=sys.stderr)

    return {"ok": False, "ts": ""}


def get_thread_replies(channel: str, thread_ts: str) -> list:
    """Bot以外のスレッド返信を取得"""
    if not SLACK_BOT_TOKEN:
        return []
    try:
        resp = requests.get(
            "https://slack.com/api/conversations.replies",
            headers=_headers(),
            params={"channel": channel, "ts": thread_ts},
            timeout=15,
        )
        data = resp.json()
        if not data.get("ok"):
            print(f"スレッド取得エラー: {data.get('error')}", file=sys.stderr)
            return []
        # Bot自身の投稿を除外（親メッセージも除外）
        bot_id = _get_bot_id()
        replies = []
        for msg in data.get("messages", []):
            if msg.get("ts") == thread_ts:
                continue  # 親メッセージをスキップ
            if msg.get("bot_id") == bot_id:
                continue  # Bot自身の返信をスキップ
            replies.append(msg)
        return replies
    except Exception as e:
        print(f"スレッド取得エラー: {e}", file=sys.stderr)
        return []


_cached_bot_id = None


def _get_bot_id() -> str:
    global _cached_bot_id
    if _cached_bot_id:
        return _cached_bot_id
    try:
        resp = requests.get(
            "https://slack.com/api/auth.test",
            headers=_headers(),
            timeout=10,
        )
        data = resp.json()
        _cached_bot_id = data.get("bot_id", data.get("user_id", ""))
        return _cached_bot_id
    except Exception:
        return ""


def save_preview_ts(platform: str, slot: str, ts: str, channel: str):
    """プレビューメッセージのtsを保存"""
    data = {}
    if PREVIEW_TS_FILE.exists():
        try:
            data = json.loads(PREVIEW_TS_FILE.read_text())
        except (json.JSONDecodeError, FileNotFoundError):
            pass

    today = datetime.now().strftime("%Y-%m-%d")
    key = f"{today}_{platform}_{slot}"
    data[key] = {"ts": ts, "channel": channel, "saved_at": datetime.now().isoformat()}

    # 7日以上前のエントリを削除
    cutoff = datetime.now().strftime("%Y-%m-")
    cleaned = {k: v for k, v in data.items() if k[:7] >= cutoff[:7]}
    PREVIEW_TS_FILE.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2))


def get_preview_ts(platform: str, slot: str) -> dict:
    """今日のプレビューメッセージのtsを取得"""
    if not PREVIEW_TS_FILE.exists():
        return {}
    try:
        data = json.loads(PREVIEW_TS_FILE.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return {}
    today = datetime.now().strftime("%Y-%m-%d")
    key = f"{today}_{platform}_{slot}"
    return data.get(key, {})


# === フォーマッター ===

def format_number(n) -> str:
    if n is None:
        return "-"
    if isinstance(n, float):
        if n >= 10000:
            return f"{n/10000:.1f}万"
        return f"{n:,.0f}"
    if isinstance(n, int):
        if n >= 10000:
            return f"{n/10000:.1f}万"
        return f"{n:,}"
    return str(n)


def format_currency(n) -> str:
    if n is None:
        return "-"
    return f"¥{n:,.0f}"


def format_percent(n) -> str:
    if n is None:
        return "-"
    return f"{n:.2f}%"


def trend_emoji(current, previous) -> str:
    if current is None or previous is None or previous == 0:
        return ""
    change = (current - previous) / previous * 100
    if change > 5:
        return f" (+{change:.1f}%)"
    elif change < -5:
        return f" ({change:.1f}%)"
    else:
        return f" ({change:+.1f}%)"
