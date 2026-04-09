# Cronジョブ精査計画 — 8エージェント並列監査

> 作成日: 2026-04-06
> 対象: crontab登録済み27ジョブ + 関連スクリプト
> 目的: 全cronジョブの健全性を確認し、エラー・不整合・改善点を洗い出す

---

## 監査対象の全体像

| 区分 | ジョブ数 | 実行頻度 |
|------|---------|---------|
| 日次（月〜土） | 13 | 04:00〜23:00 |
| 毎日 | 6 | 02:00〜08:05 |
| 週次（日曜） | 2 | 05:00, 06:00 |
| 常時 | 2 | */30分, 毎時 |
| **合計** | **27** | — |

---

## 8エージェント割り当て

### Agent 1: SEO系（2スクリプト）

| # | cron時間 | スクリプト | 頻度 |
|---|---------|-----------|------|
| 1 | 04:00 月〜土 | `scripts/pdca_seo_batch.sh` | 日次 |
| 2 | 10:00 月〜土 | `scripts/pdca_competitor.sh` | 日次 |

**チェック対象ファイル:**
- `scripts/pdca_seo_batch.sh`
- `scripts/pdca_competitor.sh`
- 両スクリプトが呼び出すPythonスクリプト群（内部で特定）

**ログ確認先:**
- `logs/seo_batch_*.log`
- `logs/competitor_*.log`

---

### Agent 2: SNS投稿系（4スクリプト）

| # | cron時間 | スクリプト | 頻度 |
|---|---------|-----------|------|
| 3 | 12,17,18,20,21:00 月〜土 | `scripts/pdca_sns_post.sh` | 日次5回 |
| 4 | 21:00 月〜土 | `scripts/cron_ig_post.sh` | 日次 |
| 5 | 02:30 月〜土 | `scripts/cron_tiktok_post.sh` | 日次 |
| 6 | 07:30 月〜土 | `scripts/cron_carousel_render.sh` | 日次 |

**チェック対象ファイル:**
- `scripts/pdca_sns_post.sh` → `scripts/auto_post.py`, `scripts/sns_workflow.py`
- `scripts/cron_ig_post.sh` → `scripts/ig_post_meta_suite.py`
- `scripts/cron_tiktok_post.sh` → `scripts/post_to_tiktok.py` or `scripts/tiktok_upload_playwright.py`
- `scripts/cron_carousel_render.sh` → `scripts/generate_carousel_html.py`
- `data/posting_schedule.json`（投稿スケジュール設定）

**ログ確認先:**
- `logs/sns_post_*.log`
- `logs/ig_post_*.log`
- `logs/tiktok_post_*.log`
- `logs/carousel_render_*.log`

**特別注意:**
- Chrome debug mode（port 9223）が`cron_ig_post.sh`の前提条件
- TikTokは全方法失敗中（MEMORY.md記載）— 現状の失敗モードを記録
- `pdca_sns_post.sh`と`cron_ig_post.sh`の21:00重複問題

---

### Agent 3: AIマーケ + コンテンツ（3スクリプト）

| # | cron時間 | スクリプト | 頻度 |
|---|---------|-----------|------|
| 7 | 06:00 月〜土 | `scripts/pdca_ai_marketing.sh` | 日次 |
| 8 | 15:00 月〜土 | `scripts/pdca_content.sh` | 日次 |
| 9 | 02:00 毎日 | autoresearch（Claude CLI） | 毎日 |

**チェック対象ファイル:**
- `scripts/pdca_ai_marketing.sh` → `scripts/pdca_ai_engine.py`, `scripts/ai_content_engine.py`
- `scripts/pdca_content.sh` → `scripts/content_pipeline.py`
- autoresearch: `docs/strategy-autoresearch.md`
- Claude CLI (`/opt/homebrew/bin/claude`) の存在確認

**ログ確認先:**
- `logs/ai_engine_*.log`
- `logs/content_*.log`
- `logs/autoresearch/cron.log`

**特別注意:**
- autoresearchは`--dangerously-skip-permissions`使用 — セキュリティリスク確認
- Claude CLIの`--max-turns 30`が適切か

---

### Agent 4: 求人パイプライン（4スクリプト）

| # | cron時間 | スクリプト | 頻度 |
|---|---------|-----------|------|
| 10 | 06:30 毎日 | `scripts/pdca_hellowork.sh` | 毎日 |
| — | （内部呼出） | `scripts/hellowork_rank.py` | — |
| — | （内部呼出） | `scripts/hellowork_to_d1.py` | — |
| — | （内部呼出） | `scripts/hellowork_to_jobs.py` | — |

**チェック対象ファイル:**
- `scripts/pdca_hellowork.sh`（パイプラインオーケストレータ）
- `scripts/hellowork_fetch.py`（API取得）
- `scripts/hellowork_rank.py`（ランキング生成）
- `scripts/hellowork_to_d1.py`（D1データベース投入）
- `scripts/hellowork_to_jobs.py`（Worker用JSON生成）
- `scripts/hellowork_diff.py`（差分検出）

**ログ確認先:**
- `logs/hellowork_*.log`

**特別注意:**
- ハローワークAPI（teikyo.hellowork.mhlw.go.jp）の接続確認
- Worker再デプロイの手動ステップが必要（自動化されていないか確認）
- D1データベースへの書き込み権限

---

### Agent 5: 監視 + レポート（4スクリプト）

| # | cron時間 | スクリプト | 頻度 |
|---|---------|-----------|------|
| 11 | */30分 | `scripts/watchdog.py` | 常時 |
| 12 | 07:00 月〜土 | `scripts/pdca_healthcheck.sh` | 日次 |
| 13 | 08:00 毎日 | `scripts/meta_ads_report.py` | 毎日 |
| 14 | 08:05 毎日 | `scripts/ga4_report.py` | 毎日 |

**チェック対象ファイル:**
- `scripts/watchdog.py`
- `scripts/pdca_healthcheck.sh`
- `scripts/meta_ads_report.py`（`.venv/bin/python3`で実行）
- `scripts/ga4_report.py`（`.venv/bin/python3`で実行）
- `scripts/slack_bridge.py`（通知送信用、依存確認）

**ログ確認先:**
- `logs/watchdog.log`
- `logs/healthcheck_*.log`
- `logs/meta_report_*.log`
- `logs/ga4_report_*.log`

**特別注意:**
- `.venv/bin/python3`の存在確認（meta_ads_report.py, ga4_report.pyはvenv経由）
- Meta APIアクセストークンの有効期限
- GA4サービスアカウント認証ファイルの存在
- watchdog.pyが30分間隔で蓄積するログの肥大化

---

### Agent 6: 投稿品質（3スクリプト）

| # | cron時間 | スクリプト | 頻度 |
|---|---------|-----------|------|
| 15 | 16:00 月〜土 | `scripts/pdca_quality_gate.sh` | 日次 |
| 16 | 19:00 月〜土 | `scripts/post_preview.py` | 日次 |
| 17 | 19:30,20:00,20:30 月〜土 | `scripts/slack_reply_check.py` | 日次3回 |

**チェック対象ファイル:**
- `scripts/pdca_quality_gate.sh` → `scripts/quality_checker.py`
- `scripts/post_preview.py`
- `scripts/slack_reply_check.py`
- `scripts/slack_utils.py`（共通Slack送信ユーティリティ）

**ログ確認先:**
- `logs/quality_gate.log`
- `logs/post_preview_*.log`
- `logs/slack_reply_*.log`

**特別注意:**
- quality_gateは「Opus 4.6画像点検」— AI API呼び出しコスト確認
- post_preview → slack_reply_check → cron_ig_post の連携フロー整合性
- Slackリプライ未検出時のフォールバック動作

---

### Agent 7: 週次 + インフラ（5スクリプト）

| # | cron時間 | スクリプト | 頻度 |
|---|---------|-----------|------|
| 18 | 06:00 日曜 | `scripts/pdca_weekly.sh` | 週次 |
| 19 | 05:00 日曜 | `scripts/pdca_weekly_content.sh` | 週次 |
| 20 | 23:00 月〜土 | `scripts/pdca_review.sh` | 日次 |
| 21 | 03:00 毎日 | `scripts/log_rotate.sh` | 毎日 |
| 22 | 毎時 :00 | `scripts/kill_zombie_chrome.sh` | 常時 |

**チェック対象ファイル:**
- `scripts/pdca_weekly.sh`
- `scripts/pdca_weekly_content.sh`
- `scripts/pdca_review.sh`
- `scripts/log_rotate.sh`
- `scripts/kill_zombie_chrome.sh`

**ログ確認先:**
- `logs/weekly_*.log`
- `logs/weekly_content_*.log`
- `logs/review_*.log`
- `logs/log_rotate.log`（存在確認）

**特別注意:**
- `pdca_weekly_content.sh`(05:00) → `pdca_weekly.sh`(06:00) の実行順序依存
- `log_rotate.sh`のローテーション日数設定（ディスク容量）
- `kill_zombie_chrome.sh`がPlaywright/CDP関連プロセスを誤killしないか

---

### Agent 8: エンゲージ + Slack（2スクリプト）

| # | cron時間 | スクリプト | 頻度 |
|---|---------|-----------|------|
| 23 | 12:00 月〜土 | `scripts/instagram_engage.py` | 日次 |
| 24 | LaunchAgent常駐 | `scripts/slack_commander.py` | 常時 |

**チェック対象ファイル:**
- `scripts/instagram_engage.py`
- `scripts/slack_commander.py`
- LaunchAgent plistファイル（`~/Library/LaunchAgents/`内）

**ログ確認先:**
- `logs/instagram_engage_*.log`
- `logs/slack_commander*.log`

**特別注意:**
- `instagram_engage.py`は`sleep $((RANDOM % 3600))`で最大1時間遅延 — 13:00超過リスク
- instagrapiセッションcookieの有効性
- `slack_commander.py`のLaunchAgent登録状態と稼働確認
- BAN回避ルール（`memory/feedback_ban_prevention.md`参照）

---

## 各エージェント共通チェック項目

全エージェントは担当スクリプトに対して以下の8項目を必ず検証する:

### 1. ファイル存在確認
```bash
test -f ~/robby-the-match/scripts/<SCRIPT> && echo "OK" || echo "MISSING"
```

### 2. 構文チェック
```bash
# bashスクリプト
bash -n ~/robby-the-match/scripts/<SCRIPT>.sh

# Pythonスクリプト
python3 -c "import py_compile; py_compile.compile('scripts/<SCRIPT>.py', doraise=True)"
```

### 3. 依存ファイル/コマンド確認
- スクリプト内の`source`, `.`, `import`, `require`を抽出
- 外部コマンド（`claude`, `npx`, `wrangler`, `playwright`等）のPATH存在確認
- `which <command>` または `command -v <command>`

### 4. 環境変数の参照チェック
- スクリプト内の`$VAR`, `${VAR}`, `os.environ`, `os.getenv`を抽出
- `.env`ファイルに該当キーが存在するか照合
- **注意: .envの値そのものは出力しない（セキュリティ）**

### 5. ログ出力先の確認
```bash
# ログディレクトリの存在
ls -la ~/robby-the-match/logs/

# crontabで指定されたログパスが書き込み可能か
touch ~/robby-the-match/logs/test_write && rm ~/robby-the-match/logs/test_write
```

### 6. 最新ログのエラー確認
```bash
# 直近3日分のログからERROR/FAIL/Traceback/Exceptionを検索
grep -i "error\|fail\|traceback\|exception" ~/robby-the-match/logs/<LOG_PREFIX>_2026040{4,5,6}*.log
```

### 7. 実行権限の確認
```bash
ls -la ~/robby-the-match/scripts/<SCRIPT>
# -rwxr-xr-x であること（shスクリプト）
# Pythonスクリプトはcrontabで /usr/bin/python3 指定なら実行権限不要
```

### 8. 前提条件の確認
- Chrome debug mode: `lsof -i :9223` or `ps aux | grep chrome.*debug`
- .venv: `test -f ~/robby-the-match/.venv/bin/python3`
- Claude CLI: `test -f /opt/homebrew/bin/claude`
- Playwright: `npx playwright --version`
- ネットワーク接続: 外部API依存のスクリプトはURLの疎通確認

---

## 実行手順

### Phase 1: 並列監査（8エージェント同時実行）

各エージェントは以下のプロンプトテンプレートで起動:

```
あなはAgent{N}です。以下のcronジョブスクリプトを精査してください。

担当スクリプト:
{スクリプトリスト}

チェック項目（8項目全て実施）:
1. ファイル存在確認
2. 構文チェック（bash -n / py_compile）
3. 依存ファイル/コマンドの存在確認
4. .env変数の参照チェック
5. ログ出力先の存在確認
6. 最新ログ（直近3日）のエラー確認
7. 実行権限の確認
8. 前提条件（Chrome debug mode, .venv等）の確認

出力形式:
- スクリプトごとに8項目の結果を [OK] / [WARN] / [ERROR] で表示
- 発見した問題は具体的な修正案とともに報告
- 報告先: db_audit/reports/cron_audit_agent{N}.md
```

### Phase 2: 統合レポート

全エージェント完了後、管理者が統合:
1. 各エージェントの報告を集約
2. 問題を重要度別に分類（P0: 即時対応 / P1: 今週中 / P2: 改善推奨）
3. 修正アクションプランを策定
4. `db_audit/reports/cron_audit_final.md` に最終レポート出力

### Phase 3: 修正実行

P0問題から順に修正を実施し、各修正後に該当cronジョブの手動テスト実行で動作確認。

---

## 既知の問題（事前把握済み）

| 問題 | 影響 | 該当Agent |
|------|------|----------|
| TikTok自動投稿は全方法失敗中 | cron_tiktok_post.sh が毎回エラー | Agent 2 |
| 1日3投稿（A x2 + B x1）が意図的か不明 | Instagram過剰投稿リスク | Agent 2, 8 |
| pdca_sns_post.sh 21:00枠とcron_ig_post.sh 21:00が重複 | 二重投稿の可能性 | Agent 2 |
| Meta APIアクセストークンの有効期限管理 | レポート取得失敗 | Agent 5 |
| instagram_engage.py のRANDOM遅延最大1時間 | 12:00開始→最大13:00開始 | Agent 8 |

---

## ファイル権限サマリ（事前調査済み）

| ステータス | スクリプト |
|-----------|-----------|
| 実行権限あり (rwx) | pdca_seo_batch.sh, pdca_competitor.sh, pdca_sns_post.sh, cron_ig_post.sh, cron_tiktok_post.sh, cron_carousel_render.sh, pdca_ai_marketing.sh, pdca_content.sh, pdca_hellowork.sh, hellowork_to_jobs.py, pdca_healthcheck.sh, pdca_quality_gate.sh, pdca_weekly.sh, pdca_weekly_content.sh, pdca_review.sh, log_rotate.sh, kill_zombie_chrome.sh |
| 実行権限なし (rw-) | hellowork_rank.py, hellowork_to_d1.py, watchdog.py, meta_ads_report.py, ga4_report.py, post_preview.py, slack_reply_check.py, instagram_engage.py, slack_commander.py |

> 注: Pythonスクリプトはcrontab上で `/usr/bin/python3` or `.venv/bin/python3` を明示しているため、実行権限なしでも動作する。ただし`pdca_hellowork.sh`内部で直接呼ぶ場合は要確認。

---

## スケジュール見積もり

| フェーズ | 所要時間 | 備考 |
|---------|---------|------|
| Phase 1: 並列監査 | 15〜20分 | 8エージェント同時 |
| Phase 2: 統合レポート | 5分 | 自動集約 |
| Phase 3: 修正実行 | 問題数次第 | P0のみ即時 |
| **合計** | **約25分** | — |
