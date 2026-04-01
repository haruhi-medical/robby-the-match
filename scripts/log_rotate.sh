#!/bin/bash
# ログローテーション: 7日超の日付付きログを削除、累積ログは100KBでトランケート
LOG_DIR="$HOME/robby-the-match/logs"

# 7日以上前の日付付きログを削除
find "$LOG_DIR" -name "*_20[0-9][0-9]-[0-9][0-9]-[0-9][0-9]*.log" -mtime +7 -delete 2>/dev/null

# 累積ログ（日付なし）が100KB超ならテール1000行に切り詰め
for f in "$LOG_DIR"/*.log; do
  [ -f "$f" ] || continue
  # 日付付きファイルはスキップ
  echo "$f" | grep -qE '_20[0-9]{2}-[0-9]{2}-[0-9]{2}' && continue
  size=$(stat -f%z "$f" 2>/dev/null || stat -c%s "$f" 2>/dev/null)
  if [ "$size" -gt 102400 ] 2>/dev/null; then
    tail -1000 "$f" > "${f}.tmp" && mv "${f}.tmp" "$f"
  fi
done

echo "$(date '+%Y-%m-%d %H:%M') log_rotate done" >> "$LOG_DIR/rotate.log"
