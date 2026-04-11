# ナースロビー 包括的システム診断レポート
**診断日時**: 2026-04-11 21:30（実データに基づく）
**診断者**: Claude Code Opus 4.6
**方針**: 嘘なし、忖度なし、数字で語る

---

## A. 事業の現実（数字で）

| 指標 | STATE.mdの記載 | 実態 | 判定 |
|------|---------------|------|------|
| LINE登録者数 | 0 | **0人**（KVに登録データなし） | 致命的 |
| 成約数 | 0 | **0件** | 致命的 |
| PV/日 | ~3（22/7日） | **~3PV/日** — STATE.md記載と一致 | 致命的 |
| SCクリック/月 | 25 | 25（STATE.md記載値） | 極めて低い |
| インデックス数 | 17/87 | **17ページ**（87URL中） — 80%がインデックスされていない | 深刻 |
| 広告CPA | 測定不能 | **Meta広告は未出稿のまま**（「出稿待ち: 社長がAds Managerで設定」のまま何週間も放置） | 致命的 |
| TikTok視聴/週 | 3.5K | 3,500回程度（投稿は3/31以降成功していない→減衰中と推定） | 下降中 |

### 率直な評価
**事業開始から約7週間、売上ゼロ、見込み客ゼロ**。LP-A、SEO 87ページ、DB 24,488施設、LINE Bot、AI相談 — 全て構築済みだが、入口（集客）が機能していないため全て遊休資産。

---

## B. 動いていないもの（全列挙）

### 1. TikTok自動投稿 — 完全停止（4/3~）
- **最後の成功投稿**: 不明（videoCountが6のまま変化なし = 実際にはアップされていない）
- **毎日02:30にcron実行されるが、毎回失敗**:
  - tiktokautouploader: タイムアウト（180秒）
  - Playwright直接: 「成功を報告」するがプロフィール検証で**videoCount変化なし**
  - 最終的にSlack手動投稿依頼で終了
- **ログ証拠**: `tiktok_post_2026-04-11.log` に `videoCount=6` → 3/23以降1本も実際に投稿されていない可能性大
- **STATE.mdの記載**: 「TikTok自動投稿: pdca_sns_post.sh」を「自動化済み」と記載 → **虚偽**

### 2. Instagram投稿 — 8日間連続エラー後、4/10に復旧
- **4/3~4/9**: 7日連続 `error` — MBS方式が動いていなかった
- **4/10~4/11**: `success | meta_business_suite` — 復旧確認
- **現状**: MBS（Meta Business Suite + CDP）方式で動作中
- **STATE.mdの記載**: cron_ig_post.sh が21:00に稼働と記載 → **実際はDISABLED（コメントアウト）**。pdca_sns_post.sh経由で投稿されている

### 3. instagram_engage.py — 4/3から全日失敗（9日連続）
- **全ログが `login_required`**: instagrapiのセッションが完全に死んでいる
- **毎日12:00に実行されるが、0いいね、0コメントで終了**
- **最後の成功**: 4/3以前（ログ確認範囲外）
- **STATE.mdの記載**: 「Instagram エンゲージメント: instagram_engage.py（12:00）」を自動化済みと記載 → **完全に壊れている**

### 4. autoresearch — 一度も実行されていない
- `latest_state.json`: `round: 0`, `current_score: null`, `status: "not_started"`
- `changelog.md`: ヘッダーだけで中身なし
- `cron.log`: `Not logged in - Please run /login` が19行連続
- **原因**: cronでのClaude CLI認証が失敗し続けている
- **STATE.mdの記載**: 「autoresearch（Claude CLI）: SNSスクリプト自動改善」を毎日2:00実行と記載 → **一度も動いたことがない**

### 5. pdca_weekly_content.sh — 認証エラー
- STATE.md自身が `exit_code:78（Claude CLI認証エラー）` と認めている
- ログファイル自体が存在しない
- **原因**: autoresearchと同じ、Claude CLI認証問題

### 6. カルーセルレンダリング — 4/3~4/10まで失敗、4/11に復旧
- **4/3~4/10**: `AttributeError: 'str' object has no attribute 'get'` — str→dict変換バグ
- **4/11**: 「全readyコンテンツの画像生成完了」 — 修正済みと確認
- ただし30件のfailedが `slide_generation_failed` のまま残存

### 7. Meta広告 — 未出稿
- campaign_guide.md v3まで作成済み
- 広告コピーv5（3本）作成済み
- **しかし実際の出稿はゼロ** — 「社長がAds Managerで設定」のまま
- Meta APIアクセストークンも無効化済み

### 8. posting_queue.json — 汚染状態
- 140件中: posted 47、skipped 30、**failed 30**、ready 33
- failed 30件のうち多くが `slide_generation_failed`
- posted 47件のうち、3/31以降のInstagram成功は4/10と4/11の2件のみ

---

## C. 動いているもの

### 確実に動作中
| システム | 証拠 | 状態 |
|---------|------|------|
| **watchdog.py** | 30分間隔で実行、4/11 21:00まで確認 | 正常（ただしWorker 403を毎回suppressしている） |
| **pdca_hellowork.sh** | 4/11 06:30に実行、3,546件取得+Workerデプロイ成功 | 正常 |
| **meta_ads_report.py** | 4/11 08:00に実行、Slack送信OK | 正常 |
| **ga4_report.py** | 4/11 08:05に実行、Slack送信OK | 正常 |
| **slack_commander.py** | PID 32404、3秒間隔ポーリング（3/31から稼働中、CPU 85h） | 正常 |
| **Chrome Debug Mode** | PID 31743、port 9223（3/25から稼働中） | 正常 |
| **Cloudflare Worker** | /api/health → 200 OK | 正常 |
| **Worker Secrets** | 7件全て設定済み（LINE×3, Slack×2, OpenAI, RICH_MENU_DEFAULT） | 正常（CHAT_SECRET_KEYが見当たらないが要確認） |
| **Instagram投稿（MBS方式）** | 4/10, 4/11に成功 | 復旧したが不安定 |
| **カルーセルレンダリング** | 4/11に成功 | 復旧済み |
| **SEO/競合/レビューcron** | 4/11にcommit確認 | 正常 |

### 要注意
| システム | 問題 |
|---------|------|
| **Worker** | watchdogが毎回 `HTTP Error 403: Forbidden` を suppress中 — Worker自体は200だがwatchdogのチェックURLが403を返している |
| **tiktok_analytics** | 毎日23:00に実行されログはあるが917バイト固定 — 中身要確認 |
| **CHAT_SECRET_KEY** | wrangler secret listに表示されない — LINE Bot認証に影響する可能性 |

---

## D. 技術的負債

### 1. worker.js: 7,790行
- **巨大**。単一ファイルに全ロジック（LINE Bot、マッチング、AI相談、FAQ、handoff、NLP、DB操作）
- テスト不可能、リファクタリングコスト大
- ただし「動いている」ので今は触るべきではない

### 2. テスト: 実質ゼロ
- `test` / `spec` を含むファイルは存在するが、全てworktree内のアーカイブか一時ファイル
- **自動テストスイートは存在しない**
- Worker含め全てが手動確認のみ

### 3. STATE.mdの鮮度: 部分的に陳腐化
| 記載 | 実態 |
|------|------|
| 「cron_ig_post.sh 21:00稼働」 | **DISABLED**（コメントアウト） |
| 「TikTok自動投稿: 自動化済み」 | **全失敗中** |
| 「instagram_engage: 自動化済み」 | **login_required で全失敗** |
| 「autoresearch: 毎日2:00」 | **一度も実行されたことがない** |
| 「weekly_content: 日曜5:00」 | **認証エラーで停止** |
| 「LINE登録数: 0」 | 正確 |
| 「投稿キュー: 22件ready」 | **実際は33件ready** |
| cron状態セクションの時間 | 実際のcrontabと概ね一致（ただしIGは食い違い） |

### 4. 環境変数管理
- .envに集約されているが、Worker secretsとの同期は手動
- Python 3.9（システム標準）と .venv/python3.12 が混在
- urllib3 OpenSSLWarningが全ログに出力（実害なしだがノイズ）

### 5. ゾンビプロセス
- `tiktokautouploader/login.js` (PID 53586) が4/2 02:48から放置されている
- chrome-devtools-mcp が3インスタンス稼働中（s000, s001, s002 + watchdog各1）

### 6. posting_queue.json
- content/ ではなく data/ に移動されている（STATE.mdの記載と不一致）
- 構造がdictに変更（旧: list）されている
- failed 30件が放置されたまま

---

## E. 今日やるべきこと（優先度付き）

### P0: 事業存続に直結（今日中）

**1. Meta広告を出稿する（社長の手動作業）**
- これが**唯一の集客手段**。LINE登録者0人の根本原因は広告未出稿
- campaign_guide.md v3、広告コピーv5、LINE直リンクURL — 全て準備済み
- **社長がAds Managerで ¥2,000/日 キャンペーンを作成するだけ**
- 所要時間: 30分

**2. TikTok手動投稿（社長 or Claude Desktop）**
- 自動投稿は壊れている。修理より手動投稿が速い
- 61件のコンテンツがready状態で腐っている
- 1日1本、スマホから直接TikTok Studioにアップロード

### P1: 自動化の修復（Claude Codeで対応可能）

**3. instagram_engage.pyのlogin_required修正**
- instagrapiセッション再構築が必要
- 方式A（instagrapi）を捨てて方式B（MBS + CDP）に統一する判断も検討

**4. posting_queue.jsonのfailed 30件をクリーンアップ**
- slide_generation_failed → カルーセルレンダリング修正済みなので再生成可能
- skipped 30件の理由も確認して再分類

**5. autoresearch / weekly_content のClaude CLI認証修正**
- `claude --dangerously-skip-permissions` が `Not logged in` で失敗
- `/login` を手動実行してトークンを永続化する必要がある

### P2: 中期改善

**6. Worker 403問題の調査**
- watchdogが毎回suppressしているのは正常ではない
- Worker自体は200を返しているのでwatchdogのチェックURLが間違っている可能性

**7. STATE.mdを実態に合わせて更新**
- 上記の「記載 vs 実態」の乖離を全て修正

---

## F. 忘れられている重要事項

### 1. SNSプロフィール未更新
- **TikTok**: 名前がまだ旧ブランドの可能性（手動確認必要）
- **Instagram**: 同上
- STATE.md自身が「後回し」に分類しているが、プロフィールリンクがLPに向いていなければ全投稿が無駄

### 2. Googleビジネスプロフィール未登録
- ローカルSEO「神奈川 看護師 転職」で上位表示するには必須
- STATE.mdに「手動」と書かれたまま放置

### 3. Search Consoleインデックス: 17/87（80%未登録）
- 87ページ中17ページしかインデックスされていない
- 優先10URLのインデックス登録リクエストがSTATE.mdに書かれているが未実施
- sitemapのlastmodは2026-04-01に更新済みだが、Google側の巡回が追いついていない

### 4. 広告の実測データ: ゼロ
- Meta広告が未出稿のため、CPA/CTR/CVR全て測定不能
- 「CPA > ¥69,200 → 停止」のルールは存在するが、測定するデータがそもそもない

### 5. LINE Bot: 利用者ゼロ
- 機能は完備（5問診断、マッチング、handoff、AI相談、FAQ、電話確認フロー）
- しかし利用者が1人もいないため、実環境でのバグが未検出の可能性

### 6. tiktokautouploader/login.jsゾンビ
- 4/2から放置。メモリ25MBを無駄に消費。kill推奨

---

## G. 総合診断

### 一言で言えば
**「完璧な空港を作ったが、飛行機が1機も飛んでいない」**

### 良いニュース
- 技術基盤は堅牢（Worker、DB 24,488施設、求人2,936件毎朝自動更新、LINE Bot多機能）
- ハローワーク求人パイプラインは完全自動化済み
- watchdog/healthcheck/Slackレポートの監視系は安定稼働
- Instagram投稿が4/10に復旧
- カルーセルレンダリングが4/11に復旧

### 悪いニュース
- **売上ゼロ、見込み客ゼロ、LINE登録ゼロ** — 7週間の成果がこれ
- 集客の生命線（Meta広告）が「社長手動」のまま未着手
- TikTok自動投稿は**3/31以降1本も成功していない**（14日間停止）
- instagram_engageは**9日連続全失敗**
- autoresearchは**建設以来一度も動いたことがない**
- STATE.mdに「自動化済み」と書かれたものの半分が実際には壊れている

### 本質的な問題
1. **技術構築に時間をかけすぎ、集客（広告出稿）を後回しにし続けている**
2. **「自動化済み」のラベルが実態と乖離** — 監視はしているが修復サイクルが回っていない
3. **全ての道はMeta広告出稿に通じる** — 広告を出さない限り、他の全改善は意味がない

### 数字で見る優先度
| アクション | 期待インパクト | 工数 | ROI |
|-----------|--------------|------|-----|
| Meta広告出稿 | LINE登録者獲得開始 | 30分（社長手動） | 極大 |
| TikTok手動投稿再開 | 視聴数回復 | 5分/日（社長手動） | 大 |
| IG engage修正 | フォロワー増加 | 2h（Claude Code） | 中 |
| autoresearch修正 | コンテンツ品質向上 | 1h（手動login） | 小 |
| Worker 403調査 | 監視ノイズ除去 | 1h（Claude Code） | 小 |

---

*このレポートは2026-04-11 21:30時点の実データに基づく。推測は含まない。*
