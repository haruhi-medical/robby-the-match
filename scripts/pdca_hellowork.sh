#!/bin/bash
# ============================================
# ハローワーク求人取得 → サイト更新 → デプロイ 全自動パイプライン
# cron: 30 6 * * * (毎朝06:30)
# ============================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/hellowork_fetch.log"
SLACK_BRIDGE="$PROJECT_DIR/scripts/slack_bridge.py"
PYTHON="/usr/bin/python3"
NPX="/opt/homebrew/bin/npx"

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

mkdir -p "$LOG_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

notify_slack() {
    $PYTHON "$SLACK_BRIDGE" --send "$1" 2>/dev/null || true
}

cd "$PROJECT_DIR"

log "=== ハローワーク求人パイプライン開始 ==="

# Step 1: API取得
log "Step 1: ハローワークAPI取得中..."
if $PYTHON scripts/hellowork_fetch.py >> "$LOG_FILE" 2>&1; then
    NURSE_COUNT=$(python3 -c "import json; d=json.load(open('data/hellowork_nurse_jobs.json')); print(d['total_nurse'])" 2>/dev/null || echo "?")
    log "✅ 取得完了: 看護師求人 ${NURSE_COUNT}件"
else
    log "❌ API取得失敗"
    notify_slack "❌ ハローワークAPI取得失敗。ログ確認: logs/hellowork_fetch.log"
    exit 1
fi

# Step 2: 求人ランク分け
log "Step 2: 求人ランク分け中..."
if $PYTHON scripts/hellowork_rank.py --summary >> "$LOG_FILE" 2>&1; then
    S_COUNT=$(python3 -c "import json; d=json.load(open('data/hellowork_ranked.json')); print(d['rank_counts'].get('S',0))" 2>/dev/null || echo "?")
    A_COUNT=$(python3 -c "import json; d=json.load(open('data/hellowork_ranked.json')); print(d['rank_counts'].get('A',0))" 2>/dev/null || echo "?")
    log "✅ ランク分け完了: S=${S_COUNT}件 A=${A_COUNT}件"
else
    log "⚠️ ランク分け失敗（続行）"
fi

# Step 3: worker.js EXTERNAL_JOBS更新
log "Step 3: worker.js更新中..."
if $PYTHON scripts/hellowork_to_jobs.py >> "$LOG_FILE" 2>&1; then
    log "✅ worker.js更新完了"
else
    log "❌ worker.js更新失敗"
    notify_slack "❌ ハローワーク→worker.js変換失敗"
    exit 1
fi

# Step 4: git commit + push
log "Step 4: git commit & push..."
cd "$PROJECT_DIR"
if git diff --quiet api/worker.js data/hellowork_nurse_jobs.json data/hellowork_ranked.json 2>/dev/null; then
    log "⏭️ 変更なし、スキップ"
else
    git add api/worker.js data/hellowork_nurse_jobs.json data/hellowork_ranked.json
    git commit -m "chore: ハローワーク求人データ自動更新 $(date '+%Y-%m-%d') (${NURSE_COUNT}件)" \
        --author="Hellowork Bot <bot@quads-nurse.com>" \
        >> "$LOG_FILE" 2>&1
    git push origin main >> "$LOG_FILE" 2>&1
    git push origin main:master >> "$LOG_FILE" 2>&1
    log "✅ git push完了"
fi

# Step 5: Cloudflare Worker デプロイ
log "Step 5: Cloudflare Worker デプロイ中..."
cd "$PROJECT_DIR"

# _redirectsが邪魔するので一時退避
REDIRECTS_BACKUP=""
if [ -f "_redirects" ]; then
    mv _redirects _redirects.bak
    REDIRECTS_BACKUP="1"
fi

if cd api && $NPX wrangler deploy >> "$LOG_FILE" 2>&1; then
    log "✅ Cloudflare Worker デプロイ完了"
else
    log "⚠️ Cloudflare Worker デプロイ失敗（求人データは更新済み）"
fi

cd "$PROJECT_DIR"
# _redirects復元
if [ -n "$REDIRECTS_BACKUP" ] && [ -f "_redirects.bak" ]; then
    mv _redirects.bak _redirects
fi

# Step 6: Slack通知
log "=== パイプライン完了 ==="
notify_slack "✅ ハローワーク求人自動更新完了: 看護師${NURSE_COUNT}件（S:${S_COUNT} A:${A_COUNT}）→ Worker デプロイ済み"
