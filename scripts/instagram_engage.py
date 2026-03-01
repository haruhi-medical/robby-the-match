#!/usr/bin/env python3
"""
instagram_engage.py -- Instagram日常エンゲージメント自動化 v2.0

看護師系ハッシュタグの投稿にいいね・コメントを行い、
アカウントの「人間らしさ」を維持 + コミュニティ接点を作る。

cron: 毎日12:00-13:00（ランダム遅延付き）
  0 12 * * * sleep $((RANDOM \% 3600)) && python3 ~/robby-the-match/scripts/instagram_engage.py --daily

v2.0 改善:
  - ハッシュタグ20投稿取得、最大15アクション/セッション
  - コメント確率10%、Robbyキャラボイス5テンプレ
  - アトミックJSON書き込み（tmpfile + fsync + os.replace）
  - アクションブロック検知 + 安全停止

使い方:
  python3 scripts/instagram_engage.py --daily
  python3 scripts/instagram_engage.py --daily --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

PROJECT_DIR = Path(__file__).parent.parent
SESSION_FILE = PROJECT_DIR / "data" / ".instagram_session.json"
ENGAGE_LOG_FILE = PROJECT_DIR / "data" / "engagement_log.json"
ENV_FILE = PROJECT_DIR / ".env"

# Target hashtags (nursing community) -- primary 4 always included
PRIMARY_HASHTAGS = ["看護師", "ナース", "看護師あるある", "転職看護師"]
SECONDARY_HASHTAGS = [
    "夜勤あるある", "看護師の日常", "神奈川看護師", "病棟あるある",
    "看護師ママ", "ナースライフ",
]

# Comment templates (Robby character voice)
COMMENT_TEMPLATES = [
    "わかる...!",
    "夜勤お疲れさまです！",
    "共感しかない\U0001f97a",
    "本当にそう！",
    "応援してます！",
]

# Safety limits
MAX_ACTIONS_PER_SESSION = 15
LIKE_PROBABILITY = 0.80
COMMENT_PROBABILITY = 0.10
ACTION_DELAY_MIN = 15
ACTION_DELAY_MAX = 45
HASHTAG_PAUSE_MIN = 10
HASHTAG_PAUSE_MAX = 30
POSTS_PER_HASHTAG = 20


def atomic_json_write(filepath: Path, data, indent: int = 2):
    """Atomic JSON write (tempfile + fsync + os.replace)."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=filepath.parent, suffix=".tmp", prefix=filepath.stem + "_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, filepath)
    except Exception:
        try:
            os.unlink(tmp_path)
        except (OSError, UnboundLocalError):
            pass
        raise


def load_env():
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def load_engage_log() -> List[Dict]:
    if ENGAGE_LOG_FILE.exists():
        try:
            return json.loads(ENGAGE_LOG_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
    return []


def instagram_login():
    """Login with session reuse (shares session with auto_post.py)."""
    from instagrapi import Client

    cl = Client()
    cl.delay_range = [2, 5]
    username = os.environ.get("INSTAGRAM_USERNAME", "robby.for.nurse")
    password = os.environ.get("INSTAGRAM_PASSWORD", "")

    if SESSION_FILE.exists():
        try:
            cl.load_settings(str(SESSION_FILE))
            cl.login(username, password)
            return cl
        except Exception:
            pass

    cl.set_settings({
        "user_agent": "Instagram 302.1.0.36.111 Android (34/14; 420dpi; 1080x2400; Google/google; Pixel 8; shiba; shiba; en_JP; 533450710)",
        "country": "JP", "country_code": 81, "locale": "ja_JP", "timezone_offset": 32400,
    })
    cl.login(username, password)
    cl.dump_settings(str(SESSION_FILE))
    return cl


def daily_engagement(dry_run: bool = False) -> Dict:
    """Browse 2-3 hashtags, like/comment on recent posts. Max 15 actions."""
    print(f"[ENGAGE] Starting daily engagement ({datetime.now().strftime('%H:%M')})")

    session = {
        "date": datetime.now().isoformat(),
        "actions": [],
        "total_likes": 0,
        "total_comments": 0,
        "hashtags_browsed": [],
        "dry_run": dry_run,
    }

    # Pick 2-3 hashtags: at least 1 primary + rest mixed
    pick_count = random.randint(2, 3)
    primary_pick = random.sample(PRIMARY_HASHTAGS, min(1, len(PRIMARY_HASHTAGS)))
    remaining = [h for h in PRIMARY_HASHTAGS + SECONDARY_HASHTAGS if h not in primary_pick]
    extra = random.sample(remaining, min(pick_count - 1, len(remaining)))
    hashtags = primary_pick + extra

    if dry_run:
        print("[ENGAGE] DRY RUN mode")
        for tag in hashtags:
            est_likes = int(min(POSTS_PER_HASHTAG, MAX_ACTIONS_PER_SESSION) * LIKE_PROBABILITY)
            print(f"  [DRY] Would browse #{tag} ({POSTS_PER_HASHTAG} posts), ~{est_likes} likes")
        session["hashtags_browsed"] = hashtags
        return session

    try:
        cl = instagram_login()
    except Exception as e:
        print(f"[ENGAGE] Login failed: {e}")
        return {"error": str(e)}

    total_actions = 0
    total_likes = 0
    total_comments = 0

    for tag in hashtags:
        if total_actions >= MAX_ACTIONS_PER_SESSION:
            break
        print(f"[ENGAGE] Browsing #{tag}...")
        session["hashtags_browsed"].append(tag)

        try:
            medias = cl.hashtag_medias_recent(tag, amount=POSTS_PER_HASHTAG)
            time.sleep(random.uniform(2, 5))
        except Exception as e:
            print(f"[ENGAGE] Failed to fetch #{tag}: {e}")
            continue

        for media in medias:
            if total_actions >= MAX_ACTIONS_PER_SESSION:
                break

            # Like
            if random.random() < LIKE_PROBABILITY:
                try:
                    cl.media_like(media.id)
                    total_likes += 1
                    total_actions += 1
                    session["actions"].append({"type": "like", "hashtag": tag, "media_id": str(media.id)})
                    print(f"  [LIKE] #{tag} ({total_likes} likes)")
                    time.sleep(random.uniform(ACTION_DELAY_MIN, ACTION_DELAY_MAX))
                except Exception as e:
                    print(f"  [LIKE] Failed: {e}")
                    if "blocked" in str(e).lower():
                        print("[ENGAGE] Action blocked! Stopping.")
                        total_actions = MAX_ACTIONS_PER_SESSION
                        break

            # Comment (10% probability)
            if total_actions < MAX_ACTIONS_PER_SESSION and random.random() < COMMENT_PROBABILITY:
                comment = random.choice(COMMENT_TEMPLATES)
                try:
                    cl.media_comment(media.id, comment)
                    total_comments += 1
                    total_actions += 1
                    session["actions"].append({"type": "comment", "hashtag": tag, "media_id": str(media.id), "text": comment})
                    print(f'  [COMMENT] "{comment}" on #{tag}')
                    time.sleep(random.uniform(ACTION_DELAY_MIN * 2, ACTION_DELAY_MAX * 2))
                except Exception as e:
                    print(f"  [COMMENT] Failed: {e}")

        time.sleep(random.uniform(HASHTAG_PAUSE_MIN, HASHTAG_PAUSE_MAX))

    session["total_likes"] = total_likes
    session["total_comments"] = total_comments
    cl.dump_settings(str(SESSION_FILE))

    # Persist log (atomic, keep last 30 days)
    log = load_engage_log()
    log.append(session)
    if len(log) > 30:
        log = log[-30:]
    atomic_json_write(ENGAGE_LOG_FILE, log)

    print(f"[ENGAGE] Done: {total_likes} likes, {total_comments} comments across {len(hashtags)} hashtags")
    return session


def main():
    parser = argparse.ArgumentParser(description="Instagram エンゲージメント自動化 v2.0")
    parser.add_argument("--daily", action="store_true", help="日次エンゲージメント実行")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン（API呼び出しなし）")
    args = parser.parse_args()

    load_env()

    if args.daily:
        result = daily_engagement(dry_run=args.dry_run)
        if "error" not in result:
            print(f"Total: {result.get('total_likes', 0)} likes, {result.get('total_comments', 0)} comments")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
