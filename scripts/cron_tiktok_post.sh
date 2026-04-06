#!/bin/bash
set -euo pipefail
# ===========================================
# TikTok深夜自動投稿 v1.0
# cron: 30 2 * * 1-6（月〜土 深夜02:30）
#
# 深夜帯に実行する理由:
# - tiktokautouploaderのタイムアウト(300秒)がInstagram投稿と干渉しない
# - TikTokのbot検出が深夜は緩い傾向
# - 失敗しても翌朝に確認可能
# ===========================================

source "$(dirname "$0")/utils.sh"
init_log "tiktok_post"

echo "[INFO] TikTok深夜投稿 v1.0 開始" >> "$LOG"

# ランダム遅延（0-15分）— 深夜帯は短めでOK
RANDOM_DELAY=$((RANDOM % 900))
echo "[INFO] ランダム遅延: ${RANDOM_DELAY}秒" >> "$LOG"
sleep $RANDOM_DELAY

# エージェント状態更新
update_agent_state "tiktok_poster" "running"

# TikTok自動投稿
echo "[INFO] TikTok動画投稿 (tiktokautouploader)..." >> "$LOG"
python3 "$PROJECT_DIR/scripts/tiktok_post.py" --post-next >> "$LOG" 2>&1
TK_EXIT=$?

if [ $TK_EXIT -eq 0 ]; then
    echo "[INFO] TikTok動画投稿処理完了" >> "$LOG"
else
    echo "[WARN] TikTok動画投稿失敗 (exit=$TK_EXIT)" >> "$LOG"
    # フォールバック: Upload-Post.com APIキーがあればカルーセル投稿を試行
    if grep -q "UPLOADPOST_API_KEY" "$PROJECT_DIR/.env" 2>/dev/null; then
        echo "[INFO] フォールバック: TikTokカルーセル投稿 (Upload-Post.com API)..." >> "$LOG"
        python3 "$PROJECT_DIR/scripts/tiktok_carousel.py" --post-next >> "$LOG" 2>&1
        TK_EXIT=$?
        if [ $TK_EXIT -eq 0 ]; then
            echo "[INFO] TikTokカルーセル投稿処理完了" >> "$LOG"
        else
            echo "[WARN] TikTokカルーセル投稿も失敗 (exit=$TK_EXIT)" >> "$LOG"
        fi
    else
        echo "[INFO] UPLOADPOST_API_KEY未設定のためカルーセルフォールバックをスキップ" >> "$LOG"
    fi
fi

# 進捗記録
update_progress "tiktok_post" "TikTok深夜投稿: TK=$TK_EXIT"
update_agent_state "tiktok_poster" "completed"

write_heartbeat "tiktok_post" $TK_EXIT
echo "=== [$TODAY $NOW] tiktok_post 完了 (TK=$TK_EXIT) ===" >> "$LOG"
