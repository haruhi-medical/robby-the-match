#!/bin/bash
# ============================================
# cron_carousel_render.sh — HTML/CSSカルーセル画像生成（毎日07:00）
# posting_queue.json内のreadyコンテンツからPlaywright経由でPNG画像を生成
# ============================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/carousel_render_$(date +%Y-%m-%d).log"
SLACK_SCRIPT="$SCRIPT_DIR/slack_bridge.py"

mkdir -p "$LOG_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

slack_notify() {
    /usr/bin/python3 "$SLACK_SCRIPT" --send "$1" >> "$LOG_FILE" 2>&1 || true
}

log "=== カルーセル画像生成パイプライン開始 ==="

cd "$PROJECT_DIR"

# Playwright用環境変数（headless Chromium）
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-$HOME/Library/Caches/ms-playwright}"

# posting_queue.jsonからreadyコンテンツを取得し、画像未生成のものをレンダリング
RENDER_COUNT=0
FAIL_COUNT=0

/usr/bin/python3 -c "
import json, sys
from pathlib import Path

q = json.loads(Path('data/posting_queue.json').read_text())
for post in q.get('posts', []):
    if post.get('status') != 'ready':
        continue
    slide_dir = Path(post.get('slide_dir', ''))
    json_path = Path(post.get('json_path', ''))
    # 画像が既に存在すればスキップ
    if slide_dir.exists() and list(slide_dir.glob('slide_*.png')):
        continue
    # JSONファイルがあれば出力
    if json_path.exists():
        print(f'{json_path}|{slide_dir}')
" 2>/dev/null | while IFS='|' read -r JSON_PATH SLIDE_DIR; do
    log "レンダリング: $JSON_PATH → $SLIDE_DIR"

    if /usr/bin/python3 scripts/generate_carousel_html.py \
        --json "$JSON_PATH" \
        --output-dir "$SLIDE_DIR" \
        >> "$LOG_FILE" 2>&1; then
        PNG_COUNT=$(ls "$SLIDE_DIR"/slide_*.png 2>/dev/null | wc -l | tr -d ' ')
        log "  成功: ${PNG_COUNT}枚生成"
        RENDER_COUNT=$((RENDER_COUNT + 1))
    else
        log "  失敗: $JSON_PATH"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
done

# generate_carousel.py経由のフォールバック（ai_content_engineが使うパス）
# readyだがslide_dirにPNGがないものを再チェック
MISSING=$(/usr/bin/python3 -c "
import json
from pathlib import Path

q = json.loads(Path('data/posting_queue.json').read_text())
missing = 0
for post in q.get('posts', []):
    if post.get('status') != 'ready':
        continue
    slide_dir = Path(post.get('slide_dir', ''))
    if not slide_dir.exists() or not list(slide_dir.glob('*.png')):
        missing += 1
print(missing)
" 2>/dev/null || echo "0")

if [ "$MISSING" -gt 0 ]; then
    log "画像未生成のreadyコンテンツが${MISSING}件残存"
    slack_notify "⚠️ [cron] カルーセル画像生成: ${MISSING}件が画像未生成。JSONファイル不足の可能性。ログ: $LOG_FILE"
else
    log "全readyコンテンツの画像生成完了"
    slack_notify "[cron] カルーセル画像生成完了。全readyコンテンツの画像が準備済み。"
fi

log "=== カルーセル画像生成パイプライン終了 ==="
