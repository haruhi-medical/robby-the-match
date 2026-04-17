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


# === Block Kit ヘルパー（Phase 2 #45） ===
#
# 狙い:
# - 長文セクションを折りたたみ相当（section + divider + optional context）で整理
# - 50ブロック/50セクション等のSlack制限を超える前に自動分割
# - details（大量の詳細行）は抜粋＋「... 残り N件」の要約表示に圧縮
#
# Slack Block Kit公式制限:
# - 1メッセージあたり最大50ブロック
# - section textは最大3000文字
# - mrkdwn推奨

# 1セクションあたりの安全な最大文字数（3000は公式上限、2800で余裕を持たせる）
BLOCK_KIT_SECTION_MAX_CHARS = 2800
# 1メッセージあたりの安全な最大ブロック数（50は公式上限、45で余裕を持たせる）
BLOCK_KIT_MAX_BLOCKS = 45
# details配列を折りたたむ閾値（これを超えたら末尾を「... 残り N件」に圧縮）
BLOCK_KIT_DETAILS_INLINE_LIMIT = 8


def _truncate_for_section(text: str, limit: int = BLOCK_KIT_SECTION_MAX_CHARS) -> str:
    """section textが制限超過しないよう末尾を切り詰める。"""
    if text is None:
        return ""
    if len(text) <= limit:
        return text
    suffix = "\n_...（以下省略、logs/ を参照）_"
    return text[: max(0, limit - len(suffix))] + suffix


def _split_long_text_to_blocks(header: str, body: str) -> list:
    """1セクションに収まらない長文を、section blockへ分割する。
    header は先頭セクションのみに付与、以降は無印で続ける。"""
    if not body:
        return [{
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*{header}*\n_（本文なし）_"},
        }]

    blocks = []
    remaining = body
    is_first = True
    # 改行境界で安全に分割
    while remaining:
        chunk = remaining[:BLOCK_KIT_SECTION_MAX_CHARS]
        # 改行区切りで切り詰め（最後の\nまで）
        if len(remaining) > BLOCK_KIT_SECTION_MAX_CHARS:
            last_nl = chunk.rfind("\n")
            if last_nl > BLOCK_KIT_SECTION_MAX_CHARS // 2:
                chunk = chunk[:last_nl]
        remaining = remaining[len(chunk):].lstrip("\n")

        prefix = f"*{header}*\n" if is_first else ""
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": _truncate_for_section(prefix + chunk)},
        })
        is_first = False

    return blocks


def _collapse_details(details: list) -> str:
    """details配列を折りたたみ表示文字列に変換する。
    先頭 BLOCK_KIT_DETAILS_INLINE_LIMIT 件を表示し、残りは件数要約。"""
    if not details:
        return ""
    items = [str(d) for d in details]
    if len(items) <= BLOCK_KIT_DETAILS_INLINE_LIMIT:
        return "\n".join(f"• {i}" for i in items)
    shown = items[:BLOCK_KIT_DETAILS_INLINE_LIMIT]
    rest = len(items) - BLOCK_KIT_DETAILS_INLINE_LIMIT
    body = "\n".join(f"• {i}" for i in shown)
    body += f"\n_... 残り {rest} 件（詳細はlogs/またはスレッド返信を参照）_"
    return body


def build_block_kit_message(title: str, sections: list = None, details: list = None) -> list:
    """Block Kit blocks配列を組み立てる。

    Args:
        title: メッセージ見出し（必須）
        sections: [{"heading": str, "body": str}] or [{"heading": str, "details": list}]
        details: タイトル直下に折りたたみ表示する明細（長文阻止）

    Returns:
        list of Slack blocks（最大 BLOCK_KIT_MAX_BLOCKS 件）

    Example:
        blocks = build_block_kit_message(
            title="Watchdog v3.1 アラート",
            sections=[
                {"heading": "失敗ジョブ", "details": ["seo_batch: timeout", ...]},
                {"heading": "Workerヘルス", "body": "OK"},
            ],
            details=["5件のジョブが config_error"]
        )
    """
    blocks = []

    # ヘッダー
    # title は header blockだと150文字制限があるので section mrkdwn でも良い。
    # 短ければheader、長ければsection。
    safe_title = (title or "通知").strip() or "通知"
    if len(safe_title) <= 140:
        blocks.append({
            "type": "header",
            "text": {"type": "plain_text", "text": safe_title[:150], "emoji": True},
        })
    else:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*{_truncate_for_section(safe_title)}*"},
        })

    # タイトル直下の概要details（折りたたみ済み表示）
    if details:
        summary = _collapse_details(details)
        if summary:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": _truncate_for_section(summary)},
            })

    if sections:
        for sec in sections:
            if not isinstance(sec, dict):
                continue
            heading = str(sec.get("heading", "") or "").strip()
            body = sec.get("body")
            sec_details = sec.get("details")

            if sec_details:
                # detailsは折りたたみ処理
                body_text = _collapse_details(sec_details)
            elif body is not None:
                body_text = str(body)
            else:
                body_text = ""

            # ブロック上限に近づいたら打ち切り
            if len(blocks) >= BLOCK_KIT_MAX_BLOCKS - 2:
                blocks.append({
                    "type": "context",
                    "elements": [{
                        "type": "mrkdwn",
                        "text": "_（表示ブロック上限到達、以下省略）_",
                    }],
                })
                break

            # 区切り線
            blocks.append({"type": "divider"})
            # 本文は必要に応じて分割
            split_blocks = _split_long_text_to_blocks(heading or "詳細", body_text)
            for b in split_blocks:
                if len(blocks) >= BLOCK_KIT_MAX_BLOCKS:
                    break
                blocks.append(b)

    # フッターcontext
    if len(blocks) < BLOCK_KIT_MAX_BLOCKS:
        blocks.append({
            "type": "context",
            "elements": [{
                "type": "mrkdwn",
                "text": f"_生成: {datetime.now().strftime('%Y-%m-%d %H:%M')} / 詳細は logs/ 配下_",
            }],
        })

    return blocks


def send_slack(
    channel: str,
    text: str,
    *,
    blocks: list = None,
    thread_ts: str = None,
    use_block_kit: bool = False,
    title: str = None,
    sections: list = None,
    details: list = None,
) -> dict:
    """Slackメッセージ送信（Block Kit互換ラッパー）。

    互換性: 既存コードは `send_slack(channel, text)` で従来どおり動作する。
    Block Kitモード: `use_block_kit=True` または `blocks`指定で長文折りたたみが有効化される。

    Args:
        channel: 送信先チャンネルID
        text: プレーンテキスト（fallback表示および通知プレビュー用、常に必須）
        blocks: 既に組み立て済みのBlock Kit配列。指定時は sections/details/title は無視
        thread_ts: スレッド返信先
        use_block_kit: True の場合、title/sections/details から blocks を自動生成
        title/sections/details: build_block_kit_message() の引数

    Returns:
        {"ok": bool, "ts": str}
    """
    # Block Kitモード: blocks未指定なら組み立てる
    if use_block_kit and not blocks:
        blocks = build_block_kit_message(
            title=title or text,
            sections=sections,
            details=details,
        )

    # send_messageに委譲（text は notification fallback として必須）
    fallback = text if text else (title or "通知")
    return send_message(channel, fallback, blocks=blocks, thread_ts=thread_ts)
