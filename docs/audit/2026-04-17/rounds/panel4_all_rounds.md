# Panel 4: 基盤（Infra / SRE / Security / Cost）— 全Round生記録

> 日付: 2026-04-17
> 議長: メインエージェント（経営参謀AI）
> ゴール: 事業継続性・コスト・運用健全性を阻む基盤問題の抽出（30%枠・守り重視）

---

## Round 1 — 独立点検（6専門家）

### 専門家1: Cloudflare Worker専門家
#### パネル: P4 / Round: 1

#### 発見した阻害要因

**1-A. `wrangler deploy` 後のシークレット消失リスクが未対策（現実に起きる運用事故）**
- 根拠データ:
  - `STATE.md:L286` 「デプロイ後にシークレット消失する問題あり → 必ず `wrangler secret list` で確認」
  - MEMORY.md「wrangler deployで全secretsが消えることがある」
  - `api/wrangler.toml:L23-28` シークレット定義は手動（7件: LINE×3, Slack×2, OpenAI, ChatSecret）
  - 現状、自動検証する post-deploy hook は存在しない
- 改善案:
  - `scripts/deploy_worker.sh` を新設（コード化すべき手順を1か所に集約）。
    1. `cd api && unset CLOUDFLARE_API_TOKEN`
    2. `npx wrangler deploy --config wrangler.toml`
    3. `wrangler secret list --config wrangler.toml > /tmp/secrets_after.json`
    4. 必須7件が揃っているか検証 → 欠損ならSlackアラート + 非ゼロexit
- 想定インパクト: Worker失陥（全LINE Bot停止）を**30秒以内に検知**可能。現状は数時間〜1日気づかない可能性
- 実装コスト: 1h
- 依存関係: `--config wrangler.toml` 必須ルール（MEMORY.md既記載）の自動化に相当

**1-B. `SLACK_CHANNEL_ID` のハードコードとenv混在で誤送信リスク**
- 根拠データ:
  - 複数スクリプトで `os.getenv("SLACK_CHANNEL_ID", "C09A7U4TV4G")` と**旧チャンネル**がフォールバック（slack_bridge.py, notify_slack.py, slack_report.py, daily_ads_report.py, slack_commander.py, slack_utils.py, fetch_analytics.py）
  - MEMORY.md明記: 「SLACK_CHANNEL_IDは `C0AEG626EUW`（ロビー小田原人材紹介）※ C09A7U4TV4は旧チャンネル」
  - 一方 `ig_post_meta_suite.py:L363,L574` は `C0AEG626EUW` をハードコード
  - 結果: `.env` が読めない/ズレた場合、**LINE通知用の肝心なチャンネルではなく旧 #claudecode にフォールバック**
- 改善案: デフォルト値は安全側（LINE通知チャンネル `C0AEG626EUW`）に統一。ハードコード排除
- 想定インパクト: LINE登録者の最初の通知が入る/入らないに直結。集客のファネル末端の信頼性
- 実装コスト: 30min
- 依存関係: Worker側 `SLACK_CHANNEL_ID` secret は `C0AEG626EUW` を維持

**1-C. Worker `wrangler.toml` の `AI_PROVIDER` とコードの不一致リスク**
- 根拠データ:
  - `api/wrangler.toml:L38` `AI_PROVIDER = "openai"` / `CHAT_MODEL = "gpt-4o-mini"`
  - `api/worker.js` に OpenAI呼び出しが **13箇所（6つの `await fetch` サイト）**。全て直接 `env.OPENAI_API_KEY` チェック
  - `OPENAI_API_KEY` 未設定時の挙動: フォールバック（Claude → Gemini → Workers AI）
  - 問題: `OPENAI_API_KEY` が**切れているのに静かに続行**するため、LINE Bot応答品質が突然劣化しても気づかない
- 改善案: Worker起動時に `OPENAI_API_KEY` 有効性チェック（最初の `/api/health` 応答に `ai_ok: true/false` を入れる）
- 想定インパクト: AI応答の品質劣化（Workers AI Llama 3.3はミサキの拒絶ワードが多い）
- 実装コスト: 1h

#### ミサキテスト
- **1-A**: LINE Bot停止中はミサキは絶対止まる（LINE追加後の反応なし）→ Yes, 最重要
- **1-B**: ミサキは気づかないが**運営側が気づかない**ことが致命的 → Yes（間接）
- **1-C**: AI応答が「みんな悩んでます」的一般論に落ちるとミサキは離脱 → Yes

---

### 専門家2: cron運用専門家
#### パネル: P4 / Round: 1

#### 発見した阻害要因

**2-A. Claude CLI認証切れで `pdca_weekly_content`・`autoresearch` が4日以上連続失敗**
- 根拠データ:
  - `logs/autoresearch_2026-04-17.log`: 「[CONFIG_ERROR] Claude CLI 認証失敗」+ `refresh_claude_token.py` でKeychain読取失敗
  - `logs/pdca_weekly_content_2026-04-12.log`: 同じ `CONFIG_ERROR`（4/5, 4/12ともに失敗）
  - `data/agent_state.json`: `autoresearch: "config_error"` / `weekly_content_planner: "pending"` で `lastRun=2026-04-12`（5日前）
  - watchdog `logs/watchdog_20260417.log`: 01:00/01:30で `Claude CLI 未ログイン` をissuesに計上 → Slack送信済（既に通知されているのに未対応）
- 改善案:
  - 短期（Phase1）: `scripts/refresh_claude_token.py` の手動実行。社長に「claude auth login」依頼
  - 中期（Phase2）: `.env` に `ANTHROPIC_API_KEY` を正式設定し、`cron_autoresearch.sh` と `pdca_weekly_content.sh` をAPI Key優先に切替（CLI依存を削る）
- 想定インパクト: SNS台本自動改善ループが停止中 → 品質スコア横ばい → PV3/日の打開策が枯渇
- 実装コスト: API Key取得=社長30min / コード切替=2h

**2-B. `pdca_sns_post.sh` の21:00枠が `DISABLED`。一方 `cron_ig_post.sh`は21:00登録 → 仕様矛盾**
- 根拠データ:
  - crontab: `0 12,17,18,20,21 * * 1-6 pdca_sns_post.sh`（21時も含む）
  - crontab: `# DISABLED: 0 21 * * 1-6 cron_ig_post.sh`（コメントアウト）
  - STATE.md: 「投稿スケジュール: 全日カルーセル（Instagram）、1日1本（TikTok）」
  - 実態: 1日2投稿（A: instagrapi×2）になっている可能性とMEMORY.mdに記載
- 改善案: `posting_schedule.json` を読み込んで重複排除ロジックを `pdca_sns_post.sh` に追加 or 21:00枠をcronから除去
- 想定インパクト: 1日複数投稿 → Instagram BANリスク（MEMORY.md `feedback_ban_prevention.md` 必読）
- 実装コスト: 1h

**2-C. `watchdog.py` Slack通知の重複**
- 根拠データ:
  - `logs/watchdog_20260417.log` 01:00と01:30で **同じ `Claude CLI 未ログイン` issuesを2連続 Slack送信**
  - watchdog.py `ALERT_COOLDOWN_SECONDS = 24h` だが、**Claude CLI認証チェックは `mark_alert_sent` を通さず直接 `issues.append`** している（L794-801）
  - つまり重要アラートほど抑制が効かず、毎30分Slackに響く可能性
- 改善案: Claude CLI未ログインのissuesにも `should_send_alert` + `mark_alert_sent` を適用
- 想定インパクト: アラート疲労 → 重要通知を見逃す
- 実装コスト: 30min

**2-D. `pdca_healthcheck.sh` が毎日正常通知も送る仕様 → Slackノイズ**
- 根拠データ: `pdca_healthcheck.sh:L289-303` 「正常時も1行サマリーをSlackに送信（沈黙を避ける）」
- 改善案: 正常時の通知を平日1回に圧縮（例: 月曜のみ週次サマリー）
- 想定インパクト: 社長のSlack疲労軽減
- 実装コスト: 15min

#### ミサキテスト
- **2-A**: autoresearch停止 → SNS台本陳腐化 → ミサキがスワイプで止まらない → Yes
- **2-B**: Instagram BAN → 全SNS流入ストップ → Yes（致命）
- **2-C, 2-D**: ミサキには無関係。運営効率の話

---

### 専門家3: Pythonスクリプト監査専門家
#### パネル: P4 / Round: 1

#### 発見した阻害要因

**3-A. `scripts/` 100ファイル — 重複と世代違いバージョンの氾濫**
- 根拠データ:
  - 画像生成: `generate_image.py`, `generate_image_cloudflare.py`, `generate_image_imagen.py`（3つ）
  - Meta広告生成: `generate_meta_ads.py`, `generate_meta_ads_v3.py`, `generate_meta_ads_v4.py`（3世代）
  - ハローワーク: `hellowork_fetch.py`, `hellowork_rank.py`, `hellowork_to_d1.py`, `hellowork_to_jobs.py`, `hellowork_diff.py`（5分割。`pdca_hellowork.sh` から呼ばれるのは `hellowork_to_d1.py`のみ）
  - TikTok投稿: `tiktok_post.py`, `tiktok_carousel.py`, `tiktok_upload_playwright.py`, `post_to_tiktok.py`, `tiktok_auth.py`（5つ。どれが現役か不明瞭）
  - `fix_meta_tags.py`, `fix_ready_posts.py`（ワンショット修正スクリプト、残置）
- 改善案:
  - `scripts/deprecated/` フォルダを作り旧バージョンを隔離（削除ではなく）
  - `CLAUDE.md` か `scripts/README.md` に「現役スクリプト一覧」を明記
- 想定インパクト: 新規開発時の誤選択防止（例: `tiktok_post.py` を直して実は別が動いていたという時間浪費）
- 実装コスト: 2h

**3-B. `tiktok_upload_playwright.py` に `bare except:` が10箇所 → エラー握りつぶし**
- 根拠データ: `grep except: scripts/*.py` → **10件全てこのファイル**
- 改善案: `except Exception as e:` + `logger.warning(f"...: {e}")` に置換
- 想定インパクト: TikTok投稿失敗の真因が隠され、デバッグ時間増大
- 実装コスト: 1h（ただし現在手動運用中なので優先度低）

**3-C. `notify_slack.py` と `slack_bridge.py --send` の両立 → `.claude/rules/scripts.md` 違反**
- 根拠データ:
  - `.claude/rules/scripts.md`: 「Slack通知: `slack_bridge.py --send` を使え（notify_slack.pyは旧式）」
  - 実装: `watchdog.py:L111` は `scripts/notify_slack.py` を呼んでいる（旧式）
- 改善案: `notify_slack.py` を `slack_bridge.py` のラッパーに置換 or watchdog.pyを `slack_bridge.py --send` 呼び出しに変更
- 想定インパクト: 設定のブレでアラートが届かないリスク
- 実装コスト: 30min

**3-D. `data/metrics/` 空ディレクトリ — STATE.md想定と現実のズレ**
- 根拠データ: `ls data/metrics/` → 空。しかし `CLAUDE.md:L66` には `data/daily_snapshot.json` が「日次統合先」とある。実在せず
- 改善案: `ga4_report.py` と `meta_ads_report.py` の出力を `data/daily_snapshot.json` に**必ず**書き出す処理を追加
- 想定インパクト: データドリブン運用の土台（統合スナップショット）が機能していない
- 実装コスト: 2h

#### ミサキテスト
- **3-A/B/C**: ミサキには無関係（運用効率）
- **3-D**: ミサキの投稿施策の判断ベースが欠落 → 間接Yes

---

### 専門家4: セキュリティ専門家
#### パネル: P4 / Round: 1

#### 発見した阻害要因

**4-A. Worker側のSlack通知 userId 8文字トランケートは良好。ただし他ルートが不明瞭**
- 根拠データ:
  - `api/worker.js:L41` `userId.slice(0, 12) + "..."` （良好）
  - `api/worker.js:L64` `userId.slice(0, 8) + '...'` （良好）
  - STATE.md: 「電話番号収集: handoff_phone_number新フェーズ」→ 電話番号はhandoff時にSlackへ全文送信される（職業安定法上は必要情報）
- 改善案: Slack通知で電話番号は下4桁 `****-****-1234` にマスク（担当者が詳細を必要な時だけ別経路で参照）
- 想定インパクト: Slackログ漏洩時のPII流出抑止
- 実装コスト: 1h
- 備考: 法令対象外と指示あり。だが運用上の予防策として提示

**4-B. Search Console 403 の裏返し — サービスアカウント権限過小だが、逆に過剰な場合を確認せず**
- 根拠データ:
  - FACT_PACK.md §4: `project: odawara-nurse-jobs` のサービスアカウントがSC権限なし
  - 一方、同アカウントがGA4権限を持っていて、そのJSONが `data/ga4-credentials.json` に配置
  - リスク: もし `ga4-credentials.json` が漏洩した場合、GA4閲覧 + （権限次第で）その他Google APIへアクセス可能
- 改善案:
  - `data/ga4-credentials.json` が `.gitignore` に入っているか再確認（メイン側タスク）
  - サービスアカウントのIAM権限を「GA4閲覧のみ」に絞り込む（過剰権限排除）
- 想定インパクト: 漏洩時の二次被害抑制
- 実装コスト: 社長依頼30min（GCPコンソール）

**4-C. `.env` の多様さ — INSTAGRAM_PASSWORD/GOOGLE_PASSWORD 平文**
- 根拠データ:
  - `.env` 構造推定（キー名のみ）: `INSTAGRAM_PASSWORD`, `GOOGLE_PASSWORD` が記録されている
  - `scripts/start_chrome_debug.sh` で利用想定。Chrome CDP経由での自動ログイン用
- 改善案:
  - 短期: `.env` の権限確認（`chmod 600 .env`）
  - 中期: Keychain統合（Mac）に移す
- 想定インパクト: Mac盗難時の被害（ただしMac Miniは自宅固定機の想定）
- 実装コスト: 30min / 4h（中期）

**4-D. ログ内に機微な認証エラー内容を出力する箇所**
- 根拠データ: `autoresearch_2026-04-17.log` に `Keychain read failed: security: SecKeychainSearchCopyNext` など内部挙動が残る（致命的リークではないが、Gitに混入する可能性）
- 改善案: `logs/` が `.gitignore` に入っているか再確認
- 想定インパクト: 小
- 実装コスト: 5min

#### ミサキテスト
- **4-A**: ミサキは気づかないが、漏洩事件は信頼喪失 → Yes（運営リスク）
- **4-B/C/D**: 運営リスク中心

---

### 専門家5: コスト監査専門家
#### パネル: P4 / Round: 1

#### 発見した阻害要因

**5-A. `content/generated/` 787MB + `data/` 479MB — 開発ストレージ肥大（GitHub Pages Actions履歴肥大の再発リスク）**
- 根拠データ:
  - `du -sh content/` → 787M（うち `generated/` 518M）
  - `du -sh data/` → 479M。`public_data/ 100M` `byosho/ 105M` `egov/ 111M` `hellowork_history/ 113M`
  - MEMORY.md: 「大容量ファイル(data/egov,byosho等)はgit管理外に」（対処済みのはず）
  - `content/generated/week2_batch_20260227 36M` など2月分の古いバッチが残存
- 改善案:
  - `content/generated/` 内で30日以上前のバッチを `tar.gz` → 外部（Google Drive等）へアーカイブ
  - 新規 `scripts/archive_old_content.sh` を月次cronで実行
- 想定インパクト: ローカル開発速度、バックアップコスト抑制
- 実装コスト: 1h

**5-B. Worker `gpt-4o-mini` 13箇所呼び出し — フォールバック順で余分な課金の可能性**
- 根拠データ:
  - `api/worker.js` OpenAI呼び出し6サイト（13ヒット）
  - CLAUDE.md: 「OpenAI→Claude Haiku→Gemini Flash→Workers AI（4段階）」
  - LINE登録4/14-16計18人 → AI応答が1人平均10ターン仮定で180リクエスト/3日 = ¥60想定（gpt-4o-mini 入出力200トークン/回）
  - リスク: LINE登録者が急増した場合の線形コスト増（Workers AIは無料）
- 改善案:
  - `wrangler.toml` の `AI_PROVIDER` を `workers-ai` に切替える検討（Llama 3.3 70B無料）
  - ただし品質劣化リスクあり → A/Bテストが必要
- 想定インパクト: 月¥500-3,000のOpenAIコスト抑制 or 品質維持
- 実装コスト: A/Bテスト設計2h。切替は1行

**5-C. Meta広告 ¥2,000/日 × 30 = ¥60,000/月 — 許容範囲内だが計測連携が壊れている**
- 根拠データ:
  - FACT_PACK.md §3: 4/15 Lead=2件 vs LINE登録=15人（計測乖離）/ 4/16 Lead=0件
  - CPA基準 ¥69,200以下は余裕
  - 禁止事項: 「Meta広告予算・入札額の勝手な変更禁止（人間のみ）」
- 改善案（調査のみ）: Lead発火経路（LP上の `fbq('track','Lead')`）を社長に調査依頼
- 想定インパクト: 広告ROAS最適化ができない
- 実装コスト: 調査0h / 社長承認後の修正1h
- 備考: **金額変更は提案しない**（禁止事項遵守）

**5-D. Cloudflare D1 24,488施設 + 2,936求人 — 無料枠超えリスクは低いが利用状況未把握**
- 根拠データ: FACT_PACK.md §8。Cloudflare D1の読み書き量・Worker Requests数の監視が未確認
- 改善案: `wrangler d1 info nurse-robby-db` と Workers Analytics を日次レポートに追加
- 想定インパクト: 予防的。無料枠1日500万Readは当面超えない見込み
- 実装コスト: 1h

#### ミサキテスト
- 全項目ミサキには直接無関係。守り施策

---

### 専門家6: SRE（Site Reliability Engineer）
#### パネル: P4 / Round: 1

#### 発見した阻害要因

**6-A. Workerダウン検知は `watchdog.py` で30分間隔 — MTTD 最大30分**
- 根拠データ:
  - `watchdog.py:L754-777` Worker `/api/health` ヘルスチェック（30分間隔）
  - 3連続失敗で `issues.append`
  - つまり最悪 **90分気づかない**（しかもSlack送信時刻はその後）
- 改善案:
  - Cloudflareの標準「Worker Health Check + Email/Webhook」を有効化（追加コストなし）
  - または UptimeRobot無料枠で5分間隔モニタリング
- 想定インパクト: LINE登録者が1時間反応なしの体験を受ける確率低減
- 実装コスト: UptimeRobot無料設定15min

**6-B. 障害プレイブックが存在しない**
- 根拠データ:
  - `docs/audit/`, `docs/strategy-*`, `PROGRESS.md` いずれにも「Worker落ちた時の手順」「Instagram BAN時の手順」等が未整備
  - `STATE.md:L273-279` に「解決済みの問題」が並ぶが、未来の再発時の対処は書かれていない
- 改善案: `docs/runbook.md` を新設
  - Worker 503 → `unset CLOUDFLARE_API_TOKEN && npx wrangler deploy --config wrangler.toml`
  - Secretsチェック → `wrangler secret list --config wrangler.toml`
  - Instagram CDP失敗 → `start_chrome_debug.sh` 再起動
  - Claude CLI切れ → `refresh_claude_token.py`
- 想定インパクト: MTTR短縮（社長1人運用時の生命線）
- 実装コスト: 2h

**6-C. 復旧の冪等性テストがない — `watchdog.py` 自動リトライは3回だが、リトライで状態破壊する可能性**
- 根拠データ:
  - `watchdog.py:L512-580` `attempt_recovery` はスクリプトを再実行するだけ
  - 例: `pdca_seo_batch.sh` が途中で死んでgit差分残したままリトライすると、同じエラーで3回失敗→リトライ上限
  - `recovery_log.json` より `seo_batch: retry_exhausted (2026-04-01)` が**既に発生**
- 改善案: スクリプト側で「前回中断検知→クリーンアップ→再開」フックを `utils.sh` に追加
- 想定インパクト: 自動復旧率向上
- 実装コスト: 4h

**6-D. Slackが単一障害点 — Slack障害時にwatchdogアラートが飛ばない**
- 根拠データ:
  - `watchdog.py:L108-116` Slack通知失敗時は `pass`（握りつぶし）
  - CLAUDE.md「異常検知→即時停止: Slack通知失敗（監視系の生命線が切れた状態）」とあるが、実装は失敗を記録しない
- 改善案: Slack送信失敗時にローカルファイル `data/alert_queue.json` に積み、次回成功時に追送
- 想定インパクト: Slack障害時の見逃し防止
- 実装コスト: 1h

#### ミサキテスト
- **6-A**: Worker落ちてLINE反応なし → ミサキ離脱 → Yes
- **6-B/C/D**: 間接的だが運営継続性の要

---

## Round 2 — 相互批判

### 専門家1（Worker）→ 他専門家への反論・補強
- **[専門家2]への補強**: 2-Aの Claude CLI認証切れは、Workerではなくローカルcron側の問題だが、副次効果としてSNS台本品質劣化→流入減→LINE登録減→Worker処理減、というファネル全体のコネクト。Worker健全でもSNSが枯れたら意味がない
- **[専門家5]への反論**: 5-B の OpenAI→Workers AI切替は、LINE Bot応答品質が致命的に落ちるリスクあり（Llama 3.3はミサキ拒絶ワード多め）。試すなら**AI相談ターンの1-2ターン目だけ**Workers AIでA/Bテストが安全

### 専門家2（cron）→ 他専門家への反論・補強
- **[専門家3]への補強**: 3-Aの重複スクリプト問題は、cron側では既に現役スクリプトが確定している（`pdca_hellowork.sh` が `hellowork_to_d1.py` のみ呼ぶ等）。`scripts/README.md` よりまず `crontab -l` を正本として、そこから呼ばれていないファイルを旧扱いにするのが速い
- **[専門家6]への補強**: 6-Bのrunbookは、crontabに書かれている全ジョブの失敗時対応を含めるべき

### 専門家3（Python）→ 他専門家への反論・補強
- **[専門家2]への反論**: 2-Dの正常時通知削減は、CLAUDE.md「異常検知→即時停止: Slack通知失敗（監視系の生命線が切れた状態）」と矛盾する可能性。「沈黙はアラート」という思想で現仕様になっている。変更するなら社長承認必須
- **[専門家4]への補強**: 4-AのSlack電話番号マスクは同意。ただし**担当者のワークフローに影響**するため、Slack通知本文では末尾4桁、フルはボタンで別API呼ぶ設計が良い

### 専門家4（Security）→ 他専門家への反論・補強
- **[専門家1]への補強**: 1-Bの `SLACK_CHANNEL_ID` デフォルト `C09A7U4TV4G` は、**漏洩したら当該チャンネル（#claudecode）のログが攻撃者に見られる**。単なる運用ミスではなくセキュリティ側面もある
- **[専門家5]への反論**: 5-AのアーカイブはGoogle Drive等「外部」に移すと、逆に漏洩経路が増える。**外付けHDDや NAS への移動が安全**

### 専門家5（Cost）→ 他専門家への反論・補強
- **[専門家6]への補強**: 6-A UptimeRobot無料枠で事足りる（月額¥0）。ただし5分間隔は無料プラン上限。1分間隔は有料¥700/月 → 現段階では5分でOK
- **[専門家1]への反論**: 1-Cの `OPENAI_API_KEY` 有効性チェックは、起動時に毎回呼ぶとOpenAIの軽微な課金（Ping代）が発生する。`/api/health` を1日1回cronで叩く設計が最適

### 専門家6（SRE）→ 他専門家への反論・補強
- **[専門家2]への補強**: 2-C watchdogの重複アラートは、Claude CLI認証チェックの特別扱いが原因。**一時的な修正**としてallertsに `should_send_alert` を追加すべき。ただし根本対処は2-A（認証自体の修復）
- **[専門家3]への補強**: 3-Dの `data/daily_snapshot.json` 未生成は、SREとして観測可能性の欠損。これがないと障害時の「何が正常だったか」の比較ができない

### Round 2 サマリー
- 最頻出の補強: **2-A（Claude CLI認証）** と **1-A（wrangler secret消失検知）** が複数専門家から重要度「最上位」と評価
- 反論が解決したもの: 2-D削減は「社長判断」、5-B切替は「A/Bテスト前提」に条件付け
- 新発見: 4-Aの電話番号マスクは担当者ワークフロー考慮が必要（末尾4桁+別API）

---

## Round 3 — 議長統合（下記 `panels/panel4_infra.md` に正式版を別ファイルで）
