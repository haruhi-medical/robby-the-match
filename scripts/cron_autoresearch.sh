#!/bin/bash
# autoresearch cronラッパー
# utils.shで環境を整えてからclaude CLIを呼ぶ
set -euo pipefail
source ~/robby-the-match/scripts/utils.sh
init_log "autoresearch"

# Claude CLI認証チェック
ensure_env || {
  echo "[ABORT] Claude CLI認証エラー — autoresearchスキップ" >> "$LOG"
  update_agent_state "autoresearch" "config_error" 2>/dev/null || true
  exit $EXIT_CONFIG_ERROR
}

echo "[INFO] Claude CLI認証OK — autoresearch開始" >> "$LOG"

# autoresearch 1ラウンド実行
cd "$PROJECT_DIR"
claude --dangerously-skip-permissions \
  -p "docs/strategy-autoresearch.md に従い autoresearchを1ラウンド実行せよ" \
  --max-turns 30 \
  >> "$LOG" 2>&1

EXIT_CODE=$?
echo "[INFO] autoresearch完了 (exit=$EXIT_CODE)" >> "$LOG"

if [ "$EXIT_CODE" -ne 0 ]; then
  slack_notify "⚠️ autoresearch失敗 (exit=$EXIT_CODE) — ログ: logs/autoresearch_${TODAY}.log"
fi
