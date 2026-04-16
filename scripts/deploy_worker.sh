#!/bin/bash
# ============================================
# deploy_worker.sh — Cloudflare Worker 安全デプロイ + シークレット消失自動検知
# ============================================
# 背景: wrangler deploy でWorker secretsが消えることが過去にあった。
# 本スクリプトはデプロイ後に必須7件のsecretを検証し、欠損があればSlack通知+非ゼロ終了。
#
# 必須遵守:
#   - CLOUDFLARE_API_TOKEN は権限不足のためOAuthで。デプロイ時にunset。
#   - `--config wrangler.toml` を絶対に省略しない（ルートのwrangler.jsoncへの誤デプロイ防止）
# 呼び出し例:
#   bash scripts/deploy_worker.sh
# ============================================
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$HOME/robby-the-match}"
API_DIR="$PROJECT_DIR/api"
WRANGLER_CONFIG="wrangler.toml"

# 必須シークレット（worker_secrets.md / feedback_worker_deploy.md 準拠）
REQUIRED=(
  "LINE_CHANNEL_SECRET"
  "LINE_CHANNEL_ACCESS_TOKEN"
  "LINE_PUSH_SECRET"
  "SLACK_BOT_TOKEN"
  "SLACK_CHANNEL_ID"
  "OPENAI_API_KEY"
  "CHAT_SECRET_KEY"
)

# .env 読み込み（Slack通知トークン取得用）
if [ -f "$PROJECT_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$PROJECT_DIR/.env"
  set +a
fi

SLACK_BOT_TOKEN="${SLACK_BOT_TOKEN:-}"
SLACK_CHANNEL_ID="${SLACK_CHANNEL_ID:-C0AEG626EUW}"

notify_slack() {
  local text="$1"
  if [ -z "$SLACK_BOT_TOKEN" ]; then
    echo "[deploy_worker] SLACK_BOT_TOKEN 未設定のためSlack通知スキップ" >&2
    return 0
  fi
  curl -sS -X POST https://slack.com/api/chat.postMessage \
    -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
    -H "Content-Type: application/json; charset=utf-8" \
    --data "$(python3 -c 'import json,sys; print(json.dumps({"channel": sys.argv[1], "text": sys.argv[2]}))' "$SLACK_CHANNEL_ID" "$text")" \
    >/dev/null || echo "[deploy_worker] Slack通知送信失敗" >&2
}

cd "$API_DIR"

echo "[deploy_worker] === Worker deploy 開始 ==="
echo "[deploy_worker] 作業ディレクトリ: $API_DIR"
echo "[deploy_worker] config: $WRANGLER_CONFIG"

# 権限不足トークンを排除してOAuth使用
unset CLOUDFLARE_API_TOKEN

# デプロイ実行
if ! npx wrangler deploy --config "$WRANGLER_CONFIG"; then
  MSG=":rotating_light: *Worker deploy 失敗*
\`npx wrangler deploy --config $WRANGLER_CONFIG\` が非ゼロ終了。
ログを確認してください（デプロイ未完了、secretsは未変更の可能性あり）。"
  notify_slack "$MSG"
  echo "[deploy_worker] ERROR: wrangler deploy 失敗" >&2
  exit 2
fi

echo "[deploy_worker] deploy 成功。secrets検証を開始..."

# secret list 取得（JSON出力）
# 注: wranglerのバージョンによりtext形式とJSON形式がある。両対応のためgrep検査。
SECRETS_OUTPUT=$(npx wrangler secret list --config "$WRANGLER_CONFIG" 2>&1 || true)

MISSING=()
for s in "${REQUIRED[@]}"; do
  # JSON形式 `"name": "X"` とテキスト形式 `X (secret_text)` のどちらでも検知
  if echo "$SECRETS_OUTPUT" | grep -qE "(\"name\"[[:space:]]*:[[:space:]]*\"$s\"|^$s[[:space:]]|\|[[:space:]]*$s[[:space:]]*\|)"; then
    echo "[deploy_worker] OK: $s"
  else
    echo "[deploy_worker] MISSING: $s" >&2
    MISSING+=("$s")
  fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
  MISSING_LIST=$(printf ' • %s\n' "${MISSING[@]}")
  MSG=":rotating_light: *Worker secret 欠損検知*
デプロイ後の \`wrangler secret list\` で以下のsecretが欠損しています:
$MISSING_LIST
即時復旧してください:
\`\`\`
cd $API_DIR
echo \"<value>\" | npx wrangler secret put <NAME> --config $WRANGLER_CONFIG
\`\`\`
.env にマスターが保存されています。"
  notify_slack "$MSG"
  echo "[deploy_worker] ERROR: secret欠損 ${#MISSING[@]}件" >&2
  exit 1
fi

echo "[deploy_worker] === 全secret 確認OK（7/7） ==="
notify_slack ":white_check_mark: Worker deploy 完了 — secrets 7/7 健全。"
exit 0
