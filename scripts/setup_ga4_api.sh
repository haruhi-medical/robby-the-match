#!/bin/bash
# GA4 Data API + Search Console API セットアップガイド
# 使い方: bash scripts/setup_ga4_api.sh

set -euo pipefail
cd "$(dirname "$0")/.."

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[!!]${NC} $1"; }
fail() { echo -e "${RED}[NG]${NC} $1"; }

echo "========================================"
echo " GA4 + Search Console API セットアップ"
echo "========================================"
echo ""

# --- Step 1: Python packages ---
echo "--- Step 1: Pythonパッケージ確認 ---"
MISSING=()
python3 -c "from google.analytics.data_v1beta import BetaAnalyticsDataClient" 2>/dev/null && ok "google-analytics-data" || { fail "google-analytics-data"; MISSING+=("google-analytics-data"); }
python3 -c "from google.oauth2.service_account import Credentials" 2>/dev/null && ok "google-auth" || { fail "google-auth"; MISSING+=("google-auth"); }
python3 -c "from googleapiclient.discovery import build" 2>/dev/null && ok "google-api-python-client" || { fail "google-api-python-client"; MISSING+=("google-api-python-client"); }
python3 -c "from dotenv import load_dotenv" 2>/dev/null && ok "python-dotenv" || { fail "python-dotenv"; MISSING+=("python-dotenv"); }

if [ ${#MISSING[@]} -gt 0 ]; then
  echo ""
  warn "不足パッケージをインストール:"
  echo "  pip3 install ${MISSING[*]}"
  echo ""
fi

# --- Step 2: Credentials file ---
echo ""
echo "--- Step 2: 認証ファイル確認 ---"
CREDS_PATH="data/ga4-credentials.json"
if [ -f "$CREDS_PATH" ]; then
  ok "認証ファイルあり: $CREDS_PATH"
  # Validate JSON
  python3 -c "import json; json.load(open('$CREDS_PATH'))" 2>/dev/null && ok "JSONフォーマット正常" || fail "JSONフォーマットエラー"
else
  fail "認証ファイルなし: $CREDS_PATH"
  echo ""
  echo "  以下の手順でサービスアカウントキーを取得してください:"
  echo ""
fi

# --- Step 3: .env ---
echo ""
echo "--- Step 3: .env 確認 ---"
if [ -f ".env" ]; then
  GA4_ID=$(grep -oP 'GA4_PROPERTY_ID=\K.+' .env 2>/dev/null || grep 'GA4_PROPERTY_ID=' .env | cut -d= -f2)
  if [ -n "$GA4_ID" ] && [ "$GA4_ID" != "" ]; then
    ok "GA4_PROPERTY_ID=$GA4_ID"
  else
    fail "GA4_PROPERTY_ID が未設定"
  fi
  GA4_CREDS=$(grep 'GA4_CREDENTIALS_PATH=' .env | cut -d= -f2)
  if [ -n "$GA4_CREDS" ]; then
    ok "GA4_CREDENTIALS_PATH=$GA4_CREDS"
  else
    fail "GA4_CREDENTIALS_PATH が未設定"
  fi
  SC_URL=$(grep 'SC_SITE_URL=' .env | cut -d= -f2)
  if [ -n "$SC_URL" ]; then
    ok "SC_SITE_URL=$SC_URL"
  else
    fail "SC_SITE_URL が未設定"
  fi
else
  fail ".env ファイルが存在しません"
fi

# --- Step 4: .gitignore ---
echo ""
echo "--- Step 4: .gitignore 確認 ---"
if grep -q "ga4-credentials" .gitignore 2>/dev/null; then
  ok "ga4-credentials.json は .gitignore に含まれている"
else
  fail "ga4-credentials.json が .gitignore に含まれていません！"
  echo "  echo 'data/ga4-credentials.json' >> .gitignore"
fi

# --- Instructions ---
echo ""
echo "========================================"
echo " ブラウザでの手動セットアップ手順"
echo "========================================"
echo ""
echo "1. Google Cloud Console にアクセス"
echo "   https://console.cloud.google.com/"
echo "   (ログイン: robby.the.robot.2026@gmail.com)"
echo ""
echo "2. プロジェクト作成（または既存プロジェクト選択）"
echo "   - 左上「プロジェクトを選択」→「新しいプロジェクト」"
echo "   - プロジェクト名: kanagawa-nurse-転職 (任意)"
echo ""
echo "3. API を有効化（2つ）"
echo "   - Google Analytics Data API:"
echo "     https://console.cloud.google.com/apis/library/analyticsdata.googleapis.com"
echo "   - Search Console API:"
echo "     https://console.cloud.google.com/apis/library/searchconsole.googleapis.com"
echo ""
echo "4. サービスアカウント作成"
echo "   https://console.cloud.google.com/iam-admin/serviceaccounts"
echo "   - 「サービスアカウントを作成」をクリック"
echo "   - 名前: ga4-reporter"
echo "   - ID: ga4-reporter (自動生成)"
echo "   - 「作成して続行」→ 役割不要 →「完了」"
echo ""
echo "5. JSONキーをダウンロード"
echo "   - 作成したサービスアカウントをクリック"
echo "   - 「キー」タブ →「鍵を追加」→「新しい鍵を作成」→ JSON"
echo "   - ダウンロードしたファイルを以下に配置:"
echo "     ~/robby-the-match/data/ga4-credentials.json"
echo ""
echo "6. GA4 にサービスアカウントを追加"
echo "   - GA4 管理画面 (https://analytics.google.com/) へ"
echo "   - 管理 → プロパティ → プロパティのアクセス管理"
echo "   - 「+」→ ユーザーを追加"
echo "   - メール: サービスアカウントのメール"
echo "     (例: ga4-reporter@PROJECT_ID.iam.gserviceaccount.com)"
echo "   - 役割: 「閲覧者」でOK"
echo ""
echo "7. Search Console にサービスアカウントを追加"
echo "   - https://search.google.com/search-console/"
echo "   - 設定 → ユーザーと権限 → 「ユーザーを追加」"
echo "   - メール: 同じサービスアカウントのメール"
echo "   - 権限: 「制限付き」でOK"
echo ""
echo "8. GA4 プロパティID（数値）を確認"
echo "   - GA4 管理画面 → 管理 → プロパティ設定"
echo "   - 「プロパティID」欄の数値（例: 123456789）"
echo "   - .env の GA4_PROPERTY_ID= に設定"
echo "   - ※ G-X4G2BYW13B は測定IDであり、プロパティIDではない"
echo ""
echo "9. 接続テスト"
echo "   python3 scripts/test_ga4_connection.py"
echo ""
echo "========================================"
