# Cron/常駐プロセス点検レポート — Agent 8
**実施日:** 2026-04-09

---

## 1. instagram_engage.py（Instagramエンゲージメント）

### cron設定
```
0 12 * * 1-6 sleep $((RANDOM % 3600)) && cd ~/robby-the-match && /usr/bin/python3 scripts/instagram_engage.py --daily >> logs/instagram_engage_$(date +%Y-%m-%d).log 2>&1
```
- 月-土 12:00（ランダム遅延0-60分）— 正常

### 構文チェック
- **OK** — `ast.parse` 通過

### 依存モジュール
- `instagrapi` — インポート成功（/usr/bin/python3）
- `requests` / `dotenv` — OK

### ログ確認（直近8日分）
| 日付 | likes | comments | 結果 |
|------|-------|----------|------|
| 04-01 | 14 | 1 | 正常動作 |
| 04-02 | 0 | 0 | **login_required** |
| 04-03 | 0 | 0 | **login_required** |
| 04-04 | 0 | 0 | **login_required** |
| 04-05 | — | — | 日曜（cron 1-6でスキップ、正常） |
| 04-06 | 0 | 0 | **login_required** |
| 04-07 | 0 | 0 | **login_required** |
| 04-08 | 0 | 0 | **login_required** |
| 04-09 | 0 | 0 | **login_required** |

### 致命的問題: login_required が8日間連続
- **04-02以降、全セッションで `login_required` エラー**
- セッションファイル `/data/.instagram_session.json` は存在する（最終更新 04-09 12:00）が、認証が無効
- スクリプトのlogin処理はセッションリロード → 失敗時に新規ログイン試行だが、パスワードが正しくないかInstagram側でアカウントがロック/チャレンジ要求されている可能性が高い
- **engagement_log.json** でも 04-02 以降 likes=0, comments=0 が連続

### BAN回避策の確認
- MAX_ACTIONS_PER_SESSION = 15 — 適切
- LIKE_PROBABILITY = 80%, COMMENT_PROBABILITY = 10% — 適切
- アクション間遅延: 15-45秒（いいね）、30-90秒（コメント） — 適切
- ハッシュタグ間休憩: 10-30秒 — 適切
- ブロック検知: `"blocked" in str(e).lower()` で安全停止 — 実装済み
- コメントテンプレは5種、短文で自然 — 適切

### 対処が必要な項目
1. **[P0] Instagramセッション再認証が必要** — パスワード変更 or チャレンジ解除（手動作業）
2. **[P2] セッションファイルが認証失敗後も上書きされている** — L217で `cl.dump_settings()` がtotal_actions=0のケースでも実行される。認証失敗時はダンプしないようにすべき

---

## 2. slack_commander.py（Slack常駐監視）

### LaunchAgent設定
- plist: `~/Library/LaunchAgents/com.robby.slack-commander.plist`
- 実行: `/usr/bin/python3 slack_commander.py --poll --interval 3`
- RunAtLoad: true / KeepAlive: true
- ログ: `logs/slack_commander.log` / `logs/slack_commander_error.log`

### プロセス確認
```
PID 32404 — 稼働中（月曜05PM起動、CPU累計50分）
```
- `launchctl list` でも `com.robby.slack-commander` 確認済み（exit code -15 = 正常再起動履歴）

### 構文チェック
- **OK** — `ast.parse` 通過

### 依存モジュール
- `requests` / `dotenv` — OK

### 監視チャンネル
- `C09A7U4TV4G`（#claudecode）— 主チャンネル
- `C0AEG626EUW`（#ロビー小田原人材紹介）— LINE通知チャンネル
- **両チャンネル監視が有効**（ログに「LINE通知チャンネルも監視: C0AEG626EUW」と表示）

### ログ確認
- 指示保存 #10, #11, #12 が記録されている — コマンド処理は正常
- **Slack APIタイムアウトエラーが17件**（Read timeout / Connection reset / DNS解決失敗）
  - 一時的なネットワーク不安定が原因と推定
  - スクリプトは `interval * 2` の待機でリカバリーしている — 正常な挙動

### エラーログ（stderr）
- urllib3の `NotOpenSSLWarning` のみ（LibreSSL 2.8.3使用）
- **致命的エラーなし**

### !reply機能の確認
- コードレビュー結果: 正常に実装されている
  - `!reply <userID> メッセージ` のパース: L663-670でスペース区切り3分割
  - LINE Push APIへのPOST: worker_url + `/api/line-push`
  - 成功/失敗をスレッド返信で報告
  - LINE_PUSH_SECRET未設定時のガード処理あり
- **ログに!reply実行記録なし** — 実際に使われた形跡はないが、コード上は正常

### 注意事項
- plistは `--interval 3`（3秒間隔）だが、ログに過去の `30秒間隔` 起動記録も残っている。現在のプロセスは3秒間隔で正常
- 3秒間隔 x 2チャンネル = 毎3秒にSlack API 2回呼び出し。レートリミット（Tier 3: 50+/分）内だが余裕は少ない

---

## 総合判定

| 項目 | 状態 | 緊急度 |
|------|------|--------|
| instagram_engage.py cron | 正常動作（月-土12:00） | — |
| instagram_engage.py 認証 | **8日間 login_required** | **P0** |
| instagram_engage.py BAN回避策 | 適切に実装 | — |
| slack_commander.py プロセス | 稼働中（PID 32404） | — |
| slack_commander.py 両チャンネル監視 | 有効 | — |
| slack_commander.py !reply | コード正常（未使用） | — |
| LaunchAgent plist | 正常（KeepAlive有効） | — |
| Slack APIエラー | 散発的タイムアウト17件 | P2 |

### 必要なアクション
1. **[P0] Instagram再認証** — ブラウザでInstagramにログインしてチャレンジ解除 → セッションファイル再生成
2. **[P2] instagram_engage.py L217修正** — `if total_likes + total_comments > 0:` のガードを追加し、認証失敗時にセッションファイルを無効な状態で上書きしないようにする
3. **[P2] urllib3 OpenSSL警告** — `pip install pyOpenSSL` または Python 3.9 → 3.12 アップグレードで解消可能
