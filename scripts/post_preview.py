#!/usr/bin/env python3
"""
投稿プレビュー送信 v1.0
投稿3時間前にキューから次の投稿データを取得してSlackにプレビュー送信。
スレッド返信で修正を受け付ける。

Usage: python post_preview.py --platform tiktok --slot 12:00
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from slack_utils import send_message, save_preview_ts, SLACK_CHANNEL_POST_REVIEW

QUEUE_FILE = PROJECT_ROOT / "data" / "posting_queue.json"


def get_next_post(platform: str) -> dict:
    """キューから次のready/pendingの投稿を取得"""
    if not QUEUE_FILE.exists():
        return {}
    try:
        data = json.loads(QUEUE_FILE.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

    posts = data.get("posts", [])
    for post in posts:
        status = post.get("status", "")
        if status in ("ready", "pending"):
            # プラットフォーム判定
            content_type = post.get("content_type", "").lower()
            slide_dir = post.get("slide_dir", "")

            if platform == "instagram":
                # Instagram用のキューエントリを探す
                if "instagram" in content_type or "ig_" in slide_dir:
                    return post
            else:
                # TikTok（デフォルト）
                if "instagram" not in content_type and "ig_" not in slide_dir:
                    return post
    return {}


def build_preview_blocks(post: dict, platform: str, slot: str) -> list:
    caption = post.get("caption", "(キャプションなし)")
    hashtags = " ".join(post.get("hashtags", []))
    content_id = post.get("content_id", "不明")
    cta_type = post.get("cta_type", "不明")

    platform_emoji = "🎵" if platform == "tiktok" else "📸"
    platform_name = "TikTok" if platform == "tiktok" else "Instagram"

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{platform_emoji} {platform_name} 投稿プレビュー"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*投稿時刻*\n{slot}"},
                {"type": "mrkdwn", "text": f"*コンテンツID*\n{content_id}"},
                {"type": "mrkdwn", "text": f"*CTA*\n{cta_type}"},
            ],
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*キャプション*\n```{caption}```"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*ハッシュタグ*\n{hashtags}"},
        },
        {"type": "divider"},
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "✏️ 修正はこのメッセージの *スレッド返信* で送ってください\n• `キャプション: 新テキスト` → キャプション変更\n• `ハッシュタグ: #tag1 #tag2` → タグ変更\n• `OK` / `👍` → そのまま投稿"},
            ],
        },
    ]
    return blocks


def main():
    parser = argparse.ArgumentParser(description="投稿プレビュー送信")
    parser.add_argument("--platform", required=True, choices=["tiktok", "instagram"])
    parser.add_argument("--slot", required=True, help="投稿予定時刻 (例: 12:00)")
    args = parser.parse_args()

    post = get_next_post(args.platform)

    if not post:
        platform_name = "TikTok" if args.platform == "tiktok" else "Instagram"
        send_message(
            SLACK_CHANNEL_POST_REVIEW,
            f"⚠️ {platform_name} {args.slot}の投稿プレビュー: キューにデータなし",
        )
        print(f"[INFO] {platform_name} {args.slot}: キューにデータなし")
        return

    blocks = build_preview_blocks(post, args.platform, args.slot)
    caption = post.get("caption", "")[:100]
    fallback = f"{'🎵' if args.platform == 'tiktok' else '📸'} 投稿プレビュー {args.slot}: {caption}..."

    result = send_message(SLACK_CHANNEL_POST_REVIEW, fallback, blocks=blocks)

    if result["ok"] and result["ts"]:
        save_preview_ts(args.platform, args.slot, result["ts"], SLACK_CHANNEL_POST_REVIEW)
        print(f"[OK] プレビュー送信 (ts={result['ts']})")
    else:
        print("[ERROR] プレビュー送信失敗", file=sys.stderr)


if __name__ == "__main__":
    main()
