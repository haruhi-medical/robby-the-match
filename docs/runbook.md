# 神奈川ナース転職 — 障害対応ランブック

> **作成**: 2026-04-17 / **対応範囲**: Phase 2 #50 / **根拠**: panel4_infra P4-008
> **対象読者**: Claude Code（経営参謀AI）+ YOSHIYUKI（社長）
> **原則**: 破壊的操作禁止（`rm -rf` / `pkill -f "Google Chrome"` / `git reset --hard` は除外）。迷ったら社長に聞け

---

## 目次

1. [Worker障害（Cloudflare `robby-the-match-api`）](#1-worker障害cloudflare-robby-the-match-api)
2. [cron失敗（pdca_*.sh / watchdog.py / sns_post）](#2-cron失敗pdca_sh--watchdogpy--sns_post)
3. [Slack通知途絶（bridge / webhook / bot）](#3-slack通知途絶bridge--webhook--bot)
4. [LINE Bot応答停止（ハンドオフ/AI応答）](#4-line-bot応答停止ハンドオフai応答)
5. [Meta広告 Lead計測異常（Pixel / CAPI）](#5-meta広告-lead計測異常pixel--capi)
6. [SEOインデックス異常（GSC / sitemap / Pages）](#6-seoインデックス異常gsc--sitemap--pages)
7. [共通エスカレーションフロー](#共通エスカレーションフロー)

---

## 1. Worker障害（Cloudflare `robby-the-match-api`）

### 検知方法
- **自動**: `scripts/watchdog.py` が `/api/health` を30分ごとに叩く。3連続200以外で `Worker 3連続失敗` アラート発火
- **手動**: 以下でも確認可能
  ```bash
  curl -s -o /dev/null -w "%{http_code}\n" https://robby-the-match-api.robby-the-robot-2026.workers.dev/api/health
  ```
- **症状の二次確認**: LINE Bot無応答・LP診断完了後のLINE遷移がタイムアウト

### 一次対応
1. **原因切り分け**（5分以内）
   - Cloudflare Dashboard → Workers → `robby-the-match-api` のログ/メトリクスでエラー率確認
   - `logs/watchdog_$(date +%Y%m%d).log` の末尾で `Worker: <error>` 詳細を見る
2. **シークレット欠損の可能性が高い場合**（直近デプロイ後）
   ```bash
   cd ~/robby-the-match/api
   unset CLOUDFLARE_API_TOKEN
   npx wrangler secret list --config wrangler.toml
   ```
   必須7件が揃っているか確認: `LINE_CHANNEL_SECRET`, `LINE_CHANNEL_ACCESS_TOKEN`, `LINE_PUSH_SECRET`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`, `OPENAI_API_KEY`, `CHAT_SECRET_KEY`
3. **欠損があれば `.env` から再設定**
   ```bash
   cd ~/robby-the-match/api
   unset CLOUDFLARE_API_TOKEN
   echo "$VALUE" | npx wrangler secret put <KEY> --config wrangler.toml
   ```
4. **再デプロイ**
   ```bash
   cd ~/robby-the-match/api
   unset CLOUDFLARE_API_TOKEN
   npx wrangler deploy --config wrangler.toml
   ```
   **`--config wrangler.toml` を省略するな**（ルートの wrangler.jsonc が優先されて誤Worker更新）

### エスカレーション先
- シークレット全欠損・OAuth切れ: 社長に Slack（C0AEG626EUW）で認証依頼
- Cloudflare側の障害: Cloudflare Status（<https://www.cloudflarestatus.com/>）確認、回復待ち

### 復旧確認
```bash
curl -s https://robby-the-match-api.robby-the-robot-2026.workers.dev/api/health | head -c 200
```
→ `{"status":"ok"}` もしくは `200` 応答。LINE Botにテストメッセージ送信し返信があるか検証。

---

## 2. cron失敗（pdca_*.sh / watchdog.py / sns_post）

### 検知方法
- **自動**: `watchdog.py` が `data/heartbeats/<job>.json` と `logs/pdca_<job>_<date>.log` を監視
- 失敗時 Slack `#claudecode` または `#ロビー小田原人材紹介` に `[Watchdog v3.0] アラート` 通知
- 手動確認: `data/recovery_log.json` で `status: retrying / retry_exhausted / config_error`

### 一次対応（ジョブ種別で分岐）
1. **CONFIG_ERROR系**（リトライしても無駄）
   - ログ末尾に `CLOUDFLARE_API_TOKEN` / `authentication failed` 等
   - 対応: `.env` の該当キーを確認・更新。`watchdog.py --reset` で翌日再試行
2. **TRANSIENT系**（タイムアウト・ネット揺れ）
   - `watchdog.py` が自動リトライ（最大3回）
   - 3回失敗後は翌日までリトライ停止（`ALERT_COOLDOWN_SECONDS` = 24h）
3. **手動で再実行する場合**
   ```bash
   /bin/bash ~/robby-the-match/scripts/pdca_<job>.sh
   # または
   cd ~/robby-the-match && /usr/bin/python3 scripts/watchdog.py
   ```
4. **リトライカウンタを手動リセット**
   ```bash
   cd ~/robby-the-match && /usr/bin/python3 scripts/watchdog.py --reset
   ```

### 個別ジョブの注意点
- **sns_post**: 投稿時間帯を過ぎた場合（`posting_schedule.json` の時刻+2時間以降）は翌日回し。手動でも安全（スクリプト内で時刻チェック）
- **instagram_engage**: 12:00-14:00の範囲外は翌日回し（アカウント安全策）
- **pdca_hellowork**: 失敗しても求人データは前日分が残る。当日再実行しても冪等
- **autoresearch**: Claude CLI認証切れが恒常的な原因。社長に `claude auth login` 依頼（S-01）
  - ⚠️ **watchdog管理外**（heartbeat未送出）— `data/heartbeats/autoresearch.json` は存在しない。失敗検知は `logs/autoresearch_YYYY-MM-DD.log` の目視確認のみ
  - 代替復旧: `.env` に `ANTHROPIC_API_KEY` を追加すると、Keychain非依存でclaude CLIが動作可能（`ensure_env` がフォールバック対応済）

### エスカレーション先
- 3連続リトライ失敗 + CONFIG_ERROR: 社長に Slack で認証情報確認依頼
- 複数ジョブ同時失敗: インフラ（Mac Mini）疑い、`uptime` / `df -h` / `ps aux` で状態確認

### 復旧確認
```bash
cat ~/robby-the-match/data/heartbeats/<job>.json   # date/exit_code=0
cat ~/robby-the-match/data/recovery_log.json | python3 -m json.tool
```

---

## 3. Slack通知途絶（bridge / webhook / bot）

### 検知方法
- **症状**: Slackに `watchdog` / `pdca_*` / 投稿プレビューが来ない
- **クロスチェック**: Slack Bot Tokenが無効なら全通知が消える。Webhookだけなら一部のみ
- **ログ**: `logs/watchdog_*.log` / `logs/notify_slack.log` に `Slack Bot送信エラー` / `Webhook送信エラー`

### 一次対応
1. **チャンネルIDを確認**（最重要：MEMORY.md の既知落とし穴）
   - Claude Code用: `C09A7U4TV4G` (#claudecode)
   - LINE通知用: `C0AEG626EUW` (#ロビー小田原人材紹介)
   - `slack_utils.py` 等のデフォルトが旧IDになっていないか確認（Phase 1 #10 参照）
2. **Bot Token の有効性確認**
   ```bash
   cd ~/robby-the-match && python3 -c "
   from dotenv import load_dotenv; load_dotenv()
   import os, requests
   r = requests.get('https://slack.com/api/auth.test',
       headers={'Authorization': f'Bearer {os.getenv(\"SLACK_BOT_TOKEN\")}'})
   print(r.json())"
   ```
   `ok: true` でなければ社長にトークン再発行依頼
3. **送信テスト**
   ```bash
   cd ~/robby-the-match && python3 scripts/slack_bridge.py --send "runbook test"
   ```
4. **フォールバック**: Webhook URL（`.env` の `SLACK_WEBHOOK_URL`）が生きていればそちら経由で飛ぶ。両方死んだら通知停止

### エスカレーション先
- Token無効 → 社長にSlack App画面で再生成依頼
- Slack API自体の障害 → <https://status.slack.com/>

### 復旧確認
- `#claudecode` にテスト通知 → 返答あり → `cat ~/robby-the-match/data/preview_messages.json` で ts が記録されていれば正常

---

## 4. LINE Bot応答停止（ハンドオフ/AI応答）

### 検知方法
- **ユーザー側症状**: LINEでメッセージ送っても既読無視（あるいは「エラーが発生しました」返答）
- **ログ**: Cloudflare Worker → `tail` or Dashboard で `line-webhook` ハンドラのエラー確認
- **GA4**: `chat_open` 発火あっても `line_click` 後の `LINE登録` イベントが増えない

### 一次対応
1. **Workerが生きているか**（§1 参照）
2. **LINE Webhookの疎通確認**
   - LINE Developers Console → Messaging API → Webhook URL → 「Verify」ボタン
   - URL: `https://robby-the-match-api.robby-the-robot-2026.workers.dev/api/line-webhook`（実URLは `api/worker.js` 参照）
3. **OpenAI API Key 失効チェック**
   ```bash
   grep OPENAI_API_KEY ~/robby-the-match/.env | head -1
   # Worker secret側も
   cd ~/robby-the-match/api && npx wrangler secret list --config wrangler.toml | grep OPENAI
   ```
   失効なら社長にキー再発行依頼
4. **AI応答フォールバック**: Phase 1 #2 で try/catch 実装後は OpenAI → Workers AI に自動切替。未実装時はOpenAIが落ちると沈黙
5. **handoff後の沈黙**: Phase 1 #14 の自動フォロー未実装時は担当者待ち。`scripts/slack_commander.py` の常駐状況を確認
   ```bash
   launchctl list | grep slack_commander
   ```
   - **現状**: LaunchAgent 未登録が正常（STATE.md 315行目参照、`slack_bridge.py` 手動実行で代替運用中）
   - handoff後の返信は `!reply` コマンドをSlackスレッド内で打つ運用。`!reply` が届かない時のみ Worker の `/api/line-webhook` を疑う

### エスカレーション先
- LINE側障害: <https://developers.line.biz/> の Status ページ
- Worker修復不能: 社長に Dispatch 連絡

### 復旧確認
- LINE公式アカウント宛にテストメッセージ送信 → 5秒以内に応答
- `data/heartbeats/` に webhook関連ログがあれば日時確認

---

## 5. Meta広告 Lead計測異常（Pixel / CAPI）

### 検知方法
- **指標**: Meta Events Manager で `Lead` 日次カウント = 0、または LINE登録数との乖離（例: 4/15 Lead=2 vs LINE登録=15）
- **日次レポート**: `logs/meta_report_$(date +%Y%m%d).log` / Slack 08:00日次
- **症状**: 広告最適化AIが誤学習 → CPA異常値（>¥69,200でアラート）

### 一次対応
1. **手動発火テスト**（30分）
   - Events Manager → Test Events → URL `https://quads-nurse.com/` でLINE CTAクリック → Leadイベント受信確認
   - 受信しない場合は `index.html` の `fbq('track', 'Lead')` 周辺コード確認（L1855-1880 近辺）
2. **Pixel ID確認**: `index.html` の `2326210157891886` が正しいか
3. **CAPI（サーバーサイド）の有効化確認**
   - `api/worker.js` で `/api/line-start` に対する CAPI送信コードが実装されているか
   - 未実装なら Phase 1 #3 / Phase 2 #31 で対応
4. **ブラウザ側ブロック**: AdBlockユーザーはPixelが発火しない。CAPIで補完する設計が必要
5. **⚠️ 絶対にやるな**: Meta広告の予算・入札額の変更（`feedback_meta_ads_no_budget.md`）。**人間のみ可能**

### エスカレーション先
- Events Manager でLead受信0 → 社長に Dispatch 連絡、Pixel再発行検討
- CPA > ¥69,200 が3日連続 → 社長に Slack で広告停止判断依頼（金額変更は社長）

### 復旧確認
- Test Eventsで 5分以内にLead発火
- 翌日の Meta広告日次レポートで Lead / LINE登録 の差が < 30% に収束

---

## 6. SEOインデックス異常（GSC / sitemap / Pages）

### 検知方法
- **GSC**: Coverage レポートで除外/エラー急増、インプレッション急減
- **watchdog**: SC API権限切れで 403（Phase 1 #7 未解決だと `pdca_seo_batch.sh` が失敗）
- **quads-nurse.com**: `curl -I https://quads-nurse.com/sitemap.xml` で 200以外

### 一次対応
1. **GitHub Pages ビルド確認**
   - <https://github.com/Quads-Inc/robby-the-match/actions> で `deploy-pages.yml` の直近ステータス
   - 失敗してたら `.github/workflows/deploy-pages.yml` と `master` ブランチの最新コミット確認
   - `fetch-depth: 1` 設定済み（リポ肥大化対策）
2. **sitemap.xml 実在確認**
   ```bash
   curl -sI https://quads-nurse.com/sitemap.xml | head -5
   curl -s https://quads-nurse.com/sitemap.xml | grep -c '<url>'
   ```
   87 URL前後あれば正常
3. **GSC API 403** → `ga4-credentials.json` のサービスアカウントに GSC プロパティの「フル」権限を付与（社長手動、Phase 1 #7）
4. **インデックス除外急増時**
   - `pdca_seo_batch.sh` の直近ログで URL Inspectionの結果確認
   - `robots.txt` / `noindex` の誤設定なし確認
   - `privacy.html` / `terms.html` / `proposal.html` だけ `noindex` が正
5. **IndexNow ping**
   ```bash
   cd ~/robby-the-match && /usr/bin/python3 scripts/indexnow_ping.py --all
   ```

### エスカレーション先
- GA4/GSC APIの権限変更 → 社長（Googleアカウント所有者）
- quads-nurse.com DNS異常 → Netlify管理画面（ドメインはNetlify経由取得）

### 復旧確認
- GSC で新規URLが「インデックス登録」に移行（数時間〜数日）
- `curl -s https://quads-nurse.com/sitemap.xml | wc -l` が前日比±10%以内

---

## 共通エスカレーションフロー

### Level 1: Claude自動対応（0-30分）
- `watchdog.py` の自動リトライ
- ログ確認 → 既知パターン（CONFIG_ERROR）なら即Slack報告
- `.env` / `wrangler secret` の整合性チェック

### Level 2: Claude + 人間併走（30分-2時間）
- Slack `#claudecode` or `#ロビー小田原人材紹介` にアラート + 診断結果
- 社長に判断材料を提示（「どっちを選ぶか」形式）

### Level 3: 社長対応待ち（2時間-）
- OAuth再認証（Claude CLI / Google / Meta / LINE）
- トークン再発行（Slack Bot / OpenAI / Cloudflare）
- 予算・配信設定変更（Meta広告）
- ドメイン・DNS変更

### 連絡先
- Slack: `#ロビー小田原人材紹介` (`C0AEG626EUW`) — LINE通知＋緊急連絡
- Slack: `#claudecode` (`C09A7U4TV4G`) — Claude Codeセッション
- Dispatch: 社長スマホ → 短文指示

### 記録
すべての障害対応後は **PROGRESS.md** に以下を追記:
```
## YYYY-MM-DD 障害対応: <サービス名>
- 検知時刻: HH:MM
- 原因: ...
- 復旧時刻: HH:MM
- 対応内容: ...
- 再発防止: ...
```

---

## 禁止事項（runbook全体に適用）

- `rm -rf` / `git reset --hard` / `git push --force` は**原則禁止**。緊急時でも社長確認必須
- `pkill -f "Google Chrome"` 禁止（Chrome Remote Desktopが死ぬ）
- Meta広告の予算・入札額変更は**人間のみ**（Claudeは絶対にやらない）
- 新規ツール契約（月3万円超）は社長承認必須
- 「平島禎之」「はるひメディカルサービス」をHTML公開ページに書くな

---

## 関連ドキュメント

- `docs/audit/2026-04-17/supervisors/strategy_review.md`（優先順位表）
- `docs/audit/2026-04-17/panels/panel4_infra.md`（基盤阻害要因18件）
- `.claude/rules/scripts.md`（Slack通知は `slack_bridge.py` を使え）
- MEMORY.md: `feedback_deploy_checklist.md` / `feedback_worker_deploy.md` / `worker_secrets.md`
- `PDCA_SETUP.md`（cron全体像）

**最終更新**: 2026-04-17（Claude / Phase 2 #50）
