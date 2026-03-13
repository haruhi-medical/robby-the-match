#!/usr/bin/env python3
"""
Slack返信チェック v1.0
投稿30分前にプレビューメッセージのスレッド返信を確認し、修正があればキューに反映。

Usage: python slack_reply_check.py --platform tiktok --slot 12:00
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from slack_utils import send_message, get_thread_replies, get_preview_ts

QUEUE_FILE = PROJECT_ROOT / "data" / "posting_queue.json"

# 「修正なし」と判定するパターン
APPROVE_PATTERNS = re.compile(
    r"^(OK|ok|Ok|👍|いいね|そのまま|LGTM|lgtm|承認|問題なし|良い|よし|大丈夫)$",
    re.IGNORECASE,
)


def find_post_in_queue(platform: str) -> tuple:
    """キューから次のready/pendingの投稿を見つけてインデックスとともに返す"""
    if not QUEUE_FILE.exists():
        return None, -1
    try:
        data = json.loads(QUEUE_FILE.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return None, -1

    for i, post in enumerate(data.get("posts", [])):
        status = post.get("status", "")
        if status in ("ready", "pending"):
            content_type = post.get("content_type", "").lower()
            slide_dir = post.get("slide_dir", "")
            if platform == "instagram":
                if "instagram" in content_type or "ig_" in slide_dir:
                    return post, i
            else:
                if "instagram" not in content_type and "ig_" not in slide_dir:
                    return post, i
    return None, -1


def apply_modification(post: dict, reply_text: str) -> dict:
    """返信テキストをパースしてキューのpostを修正"""
    text = reply_text.strip()
    modifications = {}

    # 「キャプション: 新テキスト」
    cap_match = re.match(r"^(?:キャプション|caption)\s*[:：]\s*(.+)", text, re.IGNORECASE | re.DOTALL)
    if cap_match:
        new_caption = cap_match.group(1).strip()
        modifications["caption"] = new_caption
        return modifications

    # 「ハッシュタグ: #tag1 #tag2」
    tag_match = re.match(r"^(?:ハッシュタグ|hashtag|tags?)\s*[:：]\s*(.+)", text, re.IGNORECASE)
    if tag_match:
        tags_str = tag_match.group(1).strip()
        tags = [t.strip() for t in re.findall(r"#\S+", tags_str)]
        if tags:
            modifications["hashtags"] = tags
        return modifications

    # 承認パターン
    if APPROVE_PATTERNS.match(text):
        return {}  # 修正なし

    # 5文字以上のテキスト → キャプション全体の置き換え
    if len(text) >= 5:
        modifications["caption"] = text
        return modifications

    return {}


def update_queue(post_index: int, modifications: dict):
    """キューファイルに修正を書き戻す"""
    data = json.loads(QUEUE_FILE.read_text())
    post = data["posts"][post_index]

    if "caption" in modifications:
        if "caption_original" not in post:
            post["caption_original"] = post.get("caption", "")
        post["caption"] = modifications["caption"]

    if "hashtags" in modifications:
        if "hashtags_original" not in post:
            post["hashtags_original"] = post.get("hashtags", [])
        post["hashtags"] = modifications["hashtags"]

    data["updated"] = datetime.now().isoformat()
    QUEUE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Slack返信チェック")
    parser.add_argument("--platform", required=True, choices=["tiktok", "instagram"])
    parser.add_argument("--slot", required=True, help="投稿予定時刻 (例: 12:00)")
    args = parser.parse_args()

    preview = get_preview_ts(args.platform, args.slot)
    if not preview:
        print(f"[INFO] {args.platform} {args.slot}: プレビューメッセージなし（スキップ）")
        return

    ts = preview.get("ts", "")
    channel = preview.get("channel", "")
    if not ts or not channel:
        print("[INFO] ts/channel情報なし（スキップ）")
        return

    replies = get_thread_replies(channel, ts)

    post, post_index = find_post_in_queue(args.platform)
    if not post:
        print(f"[INFO] キューに対象投稿なし")
        return

    if not replies:
        # 返信なし → そのまま投稿
        send_message(channel, "✅ 修正なし、予定通り投稿します", thread_ts=ts)
        print(f"[OK] 返信なし → 予定通り投稿")
        return

    # 最新の返信をパース
    latest_reply = replies[-1]
    reply_text = latest_reply.get("text", "")
    user = latest_reply.get("user", "不明")

    if APPROVE_PATTERNS.match(reply_text.strip()):
        send_message(channel, f"✅ 承認確認（{user}）— 予定通り投稿します", thread_ts=ts)
        print(f"[OK] 承認: {reply_text}")
        return

    modifications = apply_modification(post, reply_text)
    if modifications:
        update_queue(post_index, modifications)
        mod_summary = ", ".join(f"{k}更新" for k in modifications.keys())
        send_message(channel, f"✅ 修正反映しました（{mod_summary}）", thread_ts=ts)
        print(f"[OK] 修正反映: {mod_summary}")
    else:
        send_message(channel, "✅ 返信を確認しました — 予定通り投稿します", thread_ts=ts)
        print(f"[OK] 修正なし判定: {reply_text[:50]}")


if __name__ == "__main__":
    main()
