#!/usr/bin/env python3
"""
Slack送信失敗キューの再送（Phase 3 #63） v1.0

data/alert_queue.json に残っているアラートを再送する。
3回失敗したアイテムは削除する（無限に溜めない）。

cron:  */30 * * * * cd ~/robby-the-match && python3 scripts/slack_retry.py

Exit codes:
  0 正常（キュー空 or 全件処理完了）
  1 キューファイル破損など復旧不可
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from slack_utils import (  # type: ignore
    send_message,
    ALERT_QUEUE_FILE,
    ALERT_QUEUE_MAX_RETRIES,
)


def main() -> int:
    if not ALERT_QUEUE_FILE.exists():
        return 0

    try:
        queue = json.loads(ALERT_QUEUE_FILE.read_text() or "[]")
    except json.JSONDecodeError as e:
        sys.stderr.write(f"alert_queue.json 破損: {e}\n")
        # 壊れた場合はバックアップを残して空にする
        backup = ALERT_QUEUE_FILE.with_suffix(".json.corrupt")
        try:
            ALERT_QUEUE_FILE.rename(backup)
        except Exception:
            pass
        ALERT_QUEUE_FILE.write_text("[]")
        return 1

    if not isinstance(queue, list) or not queue:
        return 0

    still_pending = []
    attempted = 0
    succeeded = 0
    dropped = 0

    for item in queue:
        if not isinstance(item, dict):
            continue
        channel = item.get("channel")
        text = item.get("text")
        blocks = item.get("blocks")
        thread_ts = item.get("thread_ts")
        retries = int(item.get("retries", 0))
        if not channel or not text:
            # 欠損アイテムは削除
            dropped += 1
            continue

        attempted += 1
        result = send_message(channel, text, blocks=blocks, thread_ts=thread_ts, _from_retry=True)
        if result.get("ok"):
            succeeded += 1
            continue

        retries += 1
        if retries >= ALERT_QUEUE_MAX_RETRIES:
            dropped += 1
            continue  # 3回失敗で諦めて削除

        item["retries"] = retries
        item["last_retry_at"] = datetime.now().isoformat(timespec="seconds")
        item["last_error"] = result.get("error", "unknown")
        still_pending.append(item)

    ALERT_QUEUE_FILE.write_text(json.dumps(still_pending, ensure_ascii=False, indent=2))

    print(json.dumps({
        "attempted": attempted,
        "succeeded": succeeded,
        "dropped_after_max_retries": dropped,
        "still_pending": len(still_pending),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
