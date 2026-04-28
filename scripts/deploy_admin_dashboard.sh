#!/bin/bash
# 管理ダッシュボード デプロイスクリプト
# 使い方: bash scripts/deploy_admin_dashboard.sh
# 前提: wrangler login 済み

set -e

LOG_DIR=~/robby-the-match/logs/admin-dashboard-build/2026-04-28
mkdir -p "$LOG_DIR"

cd ~/robby-the-match/api
unset CLOUDFLARE_API_TOKEN

echo "===== Step 1: Secrets投入 ====="
echo "5fd5e22767ce4b6ce246d5956ea7e457" | npx wrangler secret put ADMIN_SALT --config wrangler.toml 2>&1 | tee "$LOG_DIR/secret_salt.log"

echo "c9a9816c1c90203e71cd996c572ba11b08c17bb463b6a40c042c33bbcc0a7272" | npx wrangler secret put ADMIN_HMAC_KEY --config wrangler.toml 2>&1 | tee "$LOG_DIR/secret_hmac.log"

echo "5b3ca6ec4da06e04d599281d359c88e6c1f443e205c594d04bc04d152eef7a17" | npx wrangler secret put AUDIT_HASH_KEY --config wrangler.toml 2>&1 | tee "$LOG_DIR/secret_audit.log"

echo "4d4ebd15ca2ed3ec43c9f563d11b0022624b1e5e9cacb673ecbe926cbf22742a" | npx wrangler secret put ADMIN_PASSWORD_HASH --config wrangler.toml 2>&1 | tee "$LOG_DIR/secret_pw.log"

echo "===== Step 2: Worker Deploy ====="
npx wrangler deploy --config wrangler.toml 2>&1 | tee "$LOG_DIR/deploy.log"

echo "===== Step 3: Secrets確認 ====="
npx wrangler secret list --config wrangler.toml 2>&1 | tee "$LOG_DIR/secret_list_after.log"

echo ""
echo "===== Deploy 完了 ====="
echo "管理画面: https://robby-the-match-api.robby-the-robot-2026.workers.dev/admin/"
echo "初期パスワード: cZKgDRMZWabCvUE7"
echo "（重要: ログイン後すぐに変更してください。.envのADMIN_DEFAULT_PASSWORD参照）"
echo ""
echo "ログ全部: $LOG_DIR"
