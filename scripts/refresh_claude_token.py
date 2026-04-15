#!/usr/bin/env python3
"""
Claude CLI OAuthトークンリフレッシュ
====================================
cron環境でClaude CLIのOAuthアクセストークンが期限切れになる問題を解決。
macOS Keychainから認証情報を読み、refreshTokenで新しいaccessTokenを取得し、
Keychainに書き戻す。

使い方:
  python3 scripts/refresh_claude_token.py
  → 成功: exit 0 + "REFRESHED" or "STILL_VALID"
  → 失敗: exit 1 + エラーメッセージ
"""

import json
import subprocess
import sys
import time
import urllib.request
import urllib.error
import urllib.parse

KEYCHAIN_SERVICE = "Claude Code-credentials"
KEYCHAIN_ACCOUNT = None  # auto-detect from whoami
TOKEN_ENDPOINT = "https://platform.claude.com/v1/oauth/token"
CLIENT_ID = "https://claude.ai/oauth/claude-code-client-metadata"
# トークン期限の余裕: 5分前にリフレッシュ
EXPIRY_BUFFER_SEC = 300


def get_keychain_account():
    """Keychainのアカウント名を取得"""
    global KEYCHAIN_ACCOUNT
    if KEYCHAIN_ACCOUNT:
        return KEYCHAIN_ACCOUNT
    try:
        result = subprocess.run(["whoami"], capture_output=True, text=True)
        KEYCHAIN_ACCOUNT = result.stdout.strip()
        return KEYCHAIN_ACCOUNT
    except Exception:
        return "robby2"


def read_keychain():
    """Keychainからクレデンシャルを読む"""
    account = get_keychain_account()
    try:
        result = subprocess.run(
            ["security", "find-generic-password",
             "-s", KEYCHAIN_SERVICE,
             "-a", account,
             "-w"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return None, f"Keychain read failed: {result.stderr.strip()}"
        data = json.loads(result.stdout.strip())
        return data, None
    except json.JSONDecodeError as e:
        return None, f"Keychain data is not valid JSON: {e}"
    except subprocess.TimeoutExpired:
        return None, "Keychain read timed out (keychain locked?)"
    except Exception as e:
        return None, f"Keychain read error: {e}"


def write_keychain(data):
    """Keychainにクレデンシャルを書き戻す"""
    account = get_keychain_account()
    json_str = json.dumps(data, separators=(',', ':'))

    # 既存のエントリを削除してから再作成（security コマンドは上書き非対応）
    subprocess.run(
        ["security", "delete-generic-password",
         "-s", KEYCHAIN_SERVICE,
         "-a", account],
        capture_output=True, timeout=10
    )
    result = subprocess.run(
        ["security", "add-generic-password",
         "-s", KEYCHAIN_SERVICE,
         "-a", account,
         "-w", json_str,
         "-U"],  # Update if exists
        capture_output=True, text=True, timeout=10
    )
    if result.returncode != 0:
        return f"Keychain write failed: {result.stderr.strip()}"
    return None


def refresh_token(refresh_tok):
    """OAuth refresh_tokenで新しいaccess_tokenを取得"""
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_tok,
        "client_id": CLIENT_ID,
    }).encode("utf-8")

    req = urllib.request.Request(
        TOKEN_ENDPOINT,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body, None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return None, f"HTTP {e.code}: {body}"
    except Exception as e:
        return None, f"Request failed: {e}"


def main():
    # Step 1: Keychainから読む
    creds, err = read_keychain()
    if err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 1

    oauth = creds.get("claudeAiOauth")
    if not oauth:
        print("ERROR: claudeAiOauth not found in keychain", file=sys.stderr)
        return 1

    # Step 2: 期限チェック
    expires_at = oauth.get("expiresAt", 0)
    now_ms = int(time.time() * 1000)

    if expires_at > now_ms + (EXPIRY_BUFFER_SEC * 1000):
        remaining_min = (expires_at - now_ms) / 60000
        print(f"STILL_VALID (expires in {remaining_min:.0f} min)")
        return 0

    # Step 3: リフレッシュ
    refresh_tok = oauth.get("refreshToken")
    if not refresh_tok:
        print("ERROR: No refreshToken in keychain", file=sys.stderr)
        return 1

    print(f"Token expired ({(now_ms - expires_at) / 60000:.0f} min ago). Refreshing...",
          file=sys.stderr)

    result, err = refresh_token(refresh_tok)
    if err:
        print(f"ERROR: Token refresh failed: {err}", file=sys.stderr)
        return 1

    # Step 4: 新トークンをKeychainに書き戻す
    new_access = result.get("access_token")
    new_refresh = result.get("refresh_token")
    expires_in = result.get("expires_in", 28800)  # default 8h

    if not new_access:
        print(f"ERROR: No access_token in response: {json.dumps(result)}", file=sys.stderr)
        return 1

    oauth["accessToken"] = new_access
    if new_refresh:
        oauth["refreshToken"] = new_refresh
    oauth["expiresAt"] = now_ms + (expires_in * 1000)

    # scopes等の追加フィールドがあれば保持
    if "scope" in result:
        oauth["scopes"] = result["scope"].split(" ") if result["scope"] else oauth.get("scopes", [])

    creds["claudeAiOauth"] = oauth
    err = write_keychain(creds)
    if err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 1

    remaining_min = expires_in / 60
    print(f"REFRESHED (new token valid for {remaining_min:.0f} min)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
