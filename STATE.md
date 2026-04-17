# ナースロビー 状態ファイル
# 最終更新: 2026-04-17 10:00 by 競合分析

## 運用ルール
- 全PDCAサイクルはこのファイルを最初に読む（他を探し回るな）
- 作業完了後にこのファイルを更新する（次サイクルへ引き継ぎ）
- PROGRESS.mdには履歴として追記（こちらは状態のスナップショット）

## 現在のフェーズ
- マイルストーン: **Week 6**（2026-04-03〜）
- North Star: 看護師1名をA病院に紹介して成約
- 状態: **総点検完了（2026-04-17）→ Phase 1 実行待ち（社長承認3件）**

## 🟢 2026-04-17 総点検 + Phase 1 完遂
- 詳細: `docs/audit/2026-04-17/report.md`
- 3分要約: `docs/audit/2026-04-17/executive_summary.md`
- **82阻害要因 → 68独立項目 → Phase 1=28 / P2=22 / P3=13**

### ✅ Phase 1 実装完了（2026-04-17、ゲートキーパー5+残り23）
- #1 LP診断→LINE引き継ぎ復活（shindan.js/index.html→/api/line-start経由、session_id+5問の答え引継ぎ）
- #2 AI応答4段フォールバック（OpenAI→Claude Haiku→Gemini→Workers AI、15秒タイムアウト、日本語定型フォールバック）
- #3 Meta Pixel Lead+CAPI復旧（event_id dedup、テストevents_received:1成功、META_ACCESS_TOKEN + META_PIXEL_ID Worker secret登録）
- #5 prefecture 877件→0件（CITY_PREF_MAP 128件+東京23区追加、神奈川469→814件）
- #9 scripts/deploy_worker.sh 新設（secrets 7件検証+Slack通知）
- #10 SLACK_CHANNEL_ID 7ファイル C0AEG626EUW に統一
- #11 scripts/daily_snapshot_merge.py 新設（GA4/Meta/HW/Worker統合）
- #12-#28 LP CTA/welcome QR/派遣除外/保育園除外/電話マスク/area空欄/UTM/handoff自動フォロー等

### ⚠️ 社長手動対応（Phase 1 関連）
- S-01: `claude auth login` 実行（autoresearch復旧）
- S-02: TikTok bio差し替え承認
- S-04: Instagram 投稿頻度 3→2
- S-05: Meta広告 Lead目的継続の判断
- S-07: Search Console API 権限付与（odawara-nurse-jobs サービスアカウントに）
- S-08-10: 広告コピー3件差し替え（ミサキテスト通過率15-43%）

### 📊 期待される変化（48h以内に検証）
- Lead/LINE登録数の乖離 7.5倍→1-2倍
- AI応答成功率 85-95%→99.9%
- 求人ヒット率 神奈川+73.6%（翌朝06:30 cron反映）
- handoff 24h以内連絡の信頼性向上

### 📋 Phase 2（48h）/ Phase 3（1週間）残項目
- Phase 2: 22項目（facilities↔jobs リンク、CAPI完全実装、訪問看護ST追加、GBP登録等）
- Phase 3: 13項目（D1 phase遷移ログ、非公開求人、LCP改善、E-E-AT強化等）

### 📝 点検で判明した古い記述の訂正
- 「LINE登録0」→ 4/14 3人, 4/15 15人, 4/16 不明
- 「AI応答 4段フォールバック」→ 旧: 排他1段 / 新: 実装済み
- 「診療科100%」→ 病院1,498件サブセットのみ（DB全体24,488件では6.1%）
- 「prefecture空欄修正済」→ 旧: 877件残存 / 新: 0件
- 「area/21 + guide/41」→ 実際: area/32 + guide/48

## 2026-04-03 実施内容（1日で30+コミット）

### リブランド
- **ナースロビー**: LP/Worker/config/広告LP/about/salary-check/SEO全85ファイル 全面適用
- CTA全箇所「LINE」除去→「あなたに合う求人を見る」等
- 不安除去コピー追加（いつでもブロックOK/通知最小限）

### LIFF
- セッション引き継ぎ（LP→LIFF→LINE）テスト成功
- LIFF ID: 2009683996-7pCYfOP7
- 既友だちPush対応、follow時セッション復元

### Worker刷新
- **状態削減**: 50→20状態（858行削除）
- **アキネーター型UI**: エリア→施設タイプ(急性期/回復期/慢性期/クリニック/訪問/介護)→働き方(条件付き)→転職気持ち
- クリニック選択時: 働き方自動スキップ（日勤設定）
- エリア5県対応: 東京/神奈川/千葉/埼玉/その他
- 候補数表示: エリア+施設タイプ選択後のみ（温度感では非表示）

### マッチング5改善
- 0件撲滅（隣接エリア拡大+D1病院フォールバック）
- 施設タイプハードフィルタ（逆マッチ方式: 病院=訪問/クリニック/介護でないもの）
- Flexカルーセル5枚+フォローメッセージ
- 求人あり/なしカードデザイン統一（「募集中」/「空き確認可」）
- 個別施設選択→電話確認→handoff

### 電話確認フロー（NEW）
- 「お電話は控えた方が良いですか？」→ はい(LINE)/いいえ(電話OK→時間帯)
- Slack通知に電話可否+希望時間帯を含む

### FAQ全面刷新
- 企業FAQ→転職アドバイス5問（年収相場/夜勤と年収/有利な時期/バレずに活動/有給の見分け方）
- 全数字を厚労省データで検証済み
- 「年収を知りたい」→FAQ即回答、「まず相談したい」→直接handoff

### AI多層フォールバック
- OpenAI→Claude Haiku→Gemini Flash→Workers AI（4段階）

### D1施設DB（大規模強化）
- **24,488施設**（東京12,748+神奈川5,165+埼玉3,673+千葉2,902）
- **病院1,498件の品質**:
  - 診療科: **100%**（e-Gov診療科CSV 24万行から抽出）
  - 最寄駅: **99.5%**（HeartRails Express API）
  - 看護師数: **83.2%**（R6病床機能報告 1,247件マッチ）
  - 病床機能: **79.0%**（R5病棟票 急性期/回復期/慢性期）
  - DPC情報: **83.2%**
- 出典表示: LPフッターに追加済み

### フォローメッセージ
- カルーセル後「ナースロビーは病院側の負担が少ないシステムですので、内定に繋がりやすいです。気軽にお尋ねください！」

### ✅ 追加実施（セッション2）
- **診療科フィルタ**: 10診療科から選択（D1 100%紐付け済み）
- **ナビカード**: カルーセル末尾「もっと探す？」（3ボタン）
- **施設コメント自動生成**: buildAutoComment（駅チカ/看護体制充実/急性期 等）
- **全県DB品質向上**: 看護師数87-90%（積極的マッチング+96件）
- **8人チーム総点検**: HIGH3件+MEDIUM3件+LOW1件を修正
  - 千葉・埼玉AREA_ZONE_MAP追加
  - handoff中welcome postbackブロック
  - SQLインジェクション対策（バインドパラメータ化）
  - browsedJobIdsユニークキー化
  - handoffメッセージ統一

### DB品質（全1,498病院）
| データ | カバー率 |
|--------|---------|
| 診療科 | **100%** |
| 最寄駅 | **99.5%** |
| 看護師数 | **87-90%** |
| 病床機能 | **71-84%** |

## 2026-04-06〜07 実施内容（LINE Bot大規模改善+DB精査）

### Welcome訴求刷新
- **8パターン→1本に統一**（shindan/area_page除く）
- 新コピー: 「職場を変えたい」は、「もっと自分らしく働きたい」の裏返しだと思う。5つタップするだけ。名前も聞きません。LINEで静かに、転職活動。
- Quick Reply: 「求人を見てみる」1つだけ

### LINE Bot機能改善（20項目）
1. **千葉・埼玉サブエリア追加**: 千葉4エリア（船橋松戸柏/千葉市内房/成田印旛/外房房総）+ 埼玉4エリア（さいたま南部/東部春日部/西部川越所沢/北部熊谷）
2. **D1 jobs全件検索**: 2,936件のハローワーク求人をD1 SQLで直接検索（EXTERNAL_JOBS 215件→D1 2,936件）
3. **10件上限→担当者提案**: 5件×2ページ後に「担当者が直接お探しします。非公開求人や逆指名も可能」
4. **緊急キーワード検出**: 「死にたい」「パワハラ」等14語→即Slack通知+handoff+ホットライン案内
5. **自由テキストNLP**: 47都道府県+21都市名のキーワード検出→適切なフェーズに自動遷移
6. **エリア外正直メッセージ**: 「現在は東京・神奈川・千葉・埼玉のみ」+ 通知オプトイン
7. **matching_browseカルーセル化**: テキストリスト→Flexカルーセルカード
8. **電話番号収集**: handoff_phone_number新フェーズ（バリデーション付き）
9. **handoffメッセージ統一**: 「24時間以内にご連絡」+ 時間帯日本語化
10. **条件部分変更UI**: エリア/施設/働き方を個別変更可能（全リセット不要）
11. **クリニック+パート対応**: クリニック→働き方2択（常勤/パート）
12. **AI相談**: matching後テキスト入力→AI応答（QR再表示ではなく）
13. **「病院に直接聞く」廃止**: 全て担当者引き継ぎに統一
14. **非看護師求人除外**: 言語聴覚士/派遣/介護職/栄養士/放射線技師等
15. **給与幅表示**: 月給25.0〜38.0万円（上限のみ→下限〜上限）
16. **短時間勤務注記**: 月給17万以下に「※短時間勤務の可能性」
17. **同一事業所重複制限**: 1社最大2件
18. **区名重複防止**: 中央区→千葉市中央区の混入排除
19. **0件時導線改善**: 条件変更+担当者相談の2択
20. **非テキスト対応**: スタンプ/画像/動画/音声→適切な応答+Slack転送

### DB精査（65チェック項目、7専門家）
- **総合スコア**: 62点→修正後ALL PASS
- **施設DB**: 24,488件（病院1,498+クリニック22,978+介護12）
- **求人DB**: 2,936件（D1 jobsテーブルに全件格納）
- **修正**: 時給パースエラー21件解消/月給0.2万円バグ48件解消/prefecture空欄875件→0件/area空欄167件→14件
- **自動化**: hellowork_to_d1.py新規作成、毎朝06:30にD1 jobs自動更新

### Meta広告LINE直リンク対応
- /api/line-start: session_id自動生成（広告リンク対応）
- source=meta_ad用ウェルカムメッセージ→共通メッセージに統合
- campaign_guide.md v3: ¥2,000/日、LINE直リンク方式

### Slack !reply修正
- slack_commander: #claudecode + #ロビー小田原人材紹介の両チャンネル監視

### シミュレーション実施
- 全国400件（47都道府県）→ GEO_LOCK 63%で全国対応不可と判定
- 関東ミサキ400件（4県全サブエリア）→ CONDITIONAL PASS
- 流入テスト400件（修正20項目検証）→ CONDITIONAL PASS、致命的バグ0件

## 🔴 次にやること

### 優先度A（集客直結・社長手動）
| # | 内容 | 状態 |
|---|------|------|
| 1 | **Meta広告出稿**（¥2,000/日、LINE直リンク）| 社長がAds Managerで設定 |
| 2 | Meta広告ジオターゲティングを関東4都県に限定 | 社長手動 |

### 優先度B（中期改善）
| # | 内容 | 工数 |
|---|------|------|
| 3 | 訪問看護STデータ投入（facilities 0件→推定800件） | 8-12h |
| 4 | 介護施設データ拡充（facilities 12件→推定500件） | 8-12h |
| 5 | scoreアルゴリズム正社員/パート分離 | 4-6h |
| 6 | NLPひらがな/カタカナ対応 | 3h |
| 7 | リッチメニュー画像作成+設定 | 半日 |

### やらないリスト
- 全国展開（関東4都県で事業確立が先）
- DB自動更新cron（半年に1回手動で十分）
- 都県境通勤圏の常時ADJACENT_AREAS（大規模設計変更）

## KPI
| 指標 | 目標 | 現在 | 状態 |
|------|------|------|------|
| SEO子ページ数 | 50 | 56 | ✅ |
| ブログ記事数 | 10 | **18** | ✅ |
| sitemap URL数 | - | **87** | ✅ |
| 投稿数(TikTok) | Week3:10 | **9** | 🟡 |
| 投稿数(Instagram) | Week3:3 | **14** | ✅ |
| 投稿キュー(TikTok) | - | **61件ready** | ✅ |
| AI品質スコア | 6+ | **8.0/10** | ✅ |
| PV/日 | 100 | **~3（22/7日）** | 🔴 |
| TikTok視聴/週 | 1万 | **3.5K** | 🟡 |
| SCクリック/月 | - | **25** | 🟡 |
| インデックス数 | 87 | **17** | 🔴 |
| LINE登録数 | Month2:5 | 0 | ⏳ |
| 成約数 | Month3:1 | 0 | ⏳ |

## 完了していること
- LP-A + SEO 56ページ + ブログ18記事 + sitemap 87 URL
- Netlify独自ドメイン（quads-nurse.com）+ SSL + リダイレクト
- GA4 + Search Console + LINE公式 + Microsoft Clarity
- PDCA cron稼働（SEO/監視/競合/コンテンツ/レビュー/週次）
- Slack双方向連携（slack_bridge.py）
- 画像生成パイプライン（Cloudflare Workers AI + Pillow テキスト焼き込み）
- **施設DB（D1 facilities）**: **24,488件**（東京12,748/神奈川5,165/埼玉3,673/千葉2,902）— 厚労省公的データ5ソース
- **求人DB（D1 jobs）**: **2,936件**（ハローワーク看護師求人全件）— 毎朝06:30自動更新（hellowork_to_d1.py）
- **ハローワークAPI連携**: 4都県看護師求人自動取得 → ランク → D1投入 + EXTERNAL_JOBS更新
- AIチャットUX v2.0（Cloudflare Worker + 212施設Haversine距離計算 + 駅選択UI）
- AI自律コンテンツ生成（ai_content_engine.py + content_pipeline.py）
- **TikTok自動投稿パイプライン**: tiktok_post.py + pdca_sns_post.sh（7本投稿済み + 57本キュー待ち）
- **Instagram投稿開始**: auto_post.py v2.1 + generate_carousel.py Instagram対応済み（1本投稿済み: https://www.instagram.com/p/DVbDfg0k6vb/）
- **構築済みツール**: image_humanizer.py、instagram_engage.py、video_text_animator.py、tiktok_analytics v3.0
- **シン・AI転職 LP**: 全面リビルド（ミニ診断UI + jobs-summary.json + shindan.js）
- **SEO修正**: sitemap noindex削除、JobPosting削除、parentOrganization一括削除(63ファイル)
- **診断CTA一括挿入**: area/guide/blog 全68ページ
- **コンテンツ戦略v2.0**: robby_character.py v2.0 + ai_content_engine.py MIX改定（あるある35%/給与20%/業界裏側15%/地域15%/転職10%/トレンド5%）
- **ブランドシステム統合設定**: brand-system.md / design-tokens.css / content-rules.md / templates/base.html
- **転職診断UI v4.0**: 7問構成（エリア→年代→看護師歴→職種→働き方→重視点→時期）
- **Playwright画像生成オプション追加**: generate_carousel.py --renderer playwright
- **LP・LINE全体設計改善 Phase1**（2026-03-31 実装中）:
  - 共通LINE送客EP `/api/line-start` 実装（Worker: session_id+source+intent→KV保存→302リダイレクト）
  - LP全CTA（Hero/Sticky/Bottom）を共通EP経由に変更（session_id自動付与、CTA文言改善）
  - Worker welcome分岐実装（6パターン: hero/sticky/bottom/shindan/area_page/blog/salary_check/none）
  - Hero直下に安心バー追加（完全無料・電話なし・個人情報不要・許可番号）
  - Meta Lead二重計測修正（CTAクリックからfbq Lead削除）
  - GA4イベント名統一（5種のline_click系→click_cta）
  - Worker誤入力処理3段階化（再入力→フォールバック→HO）
  - Worker AI相談ターン上限5設定
  - Worker OpenAI失敗時日本語フォールバック

## 次にやること（Phase1短期: 2-4週間）
- [ ] LP診断7問→3問に短縮（エリア・働き方・温度感）
- [ ] Worker intake_lightフロー実装（3問→即matching_preview）
- [ ] Worker matching_browse実装（「他の求人も見たい」）
- [ ] Worker nurture_warm/cold state実装
- [ ] Worker ハンドオフ後Bot補助メッセージ
- [ ] Worker Meta Conversion API連携（follow時にLead 1回だけ発火）
- [ ] LP ページ構成変更（安心バー→診断→Features→自分向け感→比較→Flow→FAQ→CTA）
- [ ] リッチメニュー4状態切り替え実装

## SNS状態
- **TikTok**: @nurse_robby — 7本投稿済み、キュー22件ready
- **Instagram**: @robby.for.nurse — 21本投稿済み、キュー22件ready
- Google認証: robby.the.robot.2026@gmail.com
- **⚠️ 投稿方式変更（2026-03-23）**:
  - 旧方式（instagrapi/tiktokautouploader）→ **BAN/CAPTCHAで停止。使うな**
  - 新方式: **Chrome CDP経由で公式UI操作**
  - Instagram: `scripts/ig_post_meta_suite.py`（Meta Business Suite経由）
  - TikTok: Chrome CDPでTikTok Studio操作（スクリプト化予定）
  - 前提: Chromeがデバッグモード(port 9222)で起動していること
  - 起動: `scripts/start_chrome_debug.sh`
  - デザイン: Kanagawa Coastal Calm（ティール+コーラル）
- 投稿スケジュール: 全日カルーセル（Instagram）、1日1本（TikTok）
- instagram_engage.py: 12:00（月-土）ランダム遅延付き

## Meta広告状態
- **Facebookページ**: 既存アカウント利用（Instagram: @robby.for.nurse）
- **Meta Pixel**: ✅ ID `2326210157891886` 埋め込み済み
- **campaign_guide.md**: **v3.0**（LINE直リンク方式、¥2,000/日）
- **広告コピー**: v5（3本: 年収診断型/共感型/数字インパクト型）— 全て「電話なし・無料・ブロックOK」明記
- **リンク先URL**: `https://robby-the-match-api.robby-the-robot-2026.workers.dev/api/line-start?source=meta_ad&intent=direct`
- **⏳ 出稿待ち**: 社長がAds Managerで `NR_2026-04_line_direct` キャンペーン作成
  - 日予算¥2,000 / CBO / Advantage+配置 / 24-38歳女性 / 関東4都県
- **⚠️ Meta API**: アクセストークン無効化。広告自体はAds Managerで手動管理

## cron状態（実稼働中 — 2026-04-03 crontab -l と同期済み）
```
# 日次（月〜土）
0  4 * * 1-6  pdca_seo_batch.sh           # SEO改善
0  6 * * 1-6  pdca_ai_marketing.sh        # AI日次PDCA
0  7 * * 1-6  pdca_healthcheck.sh         # 障害監視
30 7 * * 1-6  cron_carousel_render.sh     # カルーセル画像生成（Playwright）
0 10 * * 1-6  pdca_competitor.sh          # 競合分析
0 12 * * 1-6  instagram_engage.py --daily # IG エンゲージメント（ランダム遅延付き）
0 12,17,18,20,21 * * 1-6 pdca_sns_post.sh # SNS投稿（スケジュール連動）
0 15 * * 1-6  pdca_content.sh             # コンテンツ生成
0 16 * * 1-6  pdca_quality_gate.sh        # 品質ゲート（投稿キュー検査）
0 19 * * 1-6  post_preview.py             # 投稿プレビュー送信（21:00投稿の2h前）
30 19 * * 1-6 slack_reply_check.py        # Slackリプライチェック①
0  20 * * 1-6 slack_reply_check.py        # Slackリプライチェック②
30 20 * * 1-6 slack_reply_check.py        # Slackリプライチェック③
0 21 * * 1-6  cron_ig_post.sh             # Instagram投稿（Meta Business Suite + CDP）
0 23 * * 1-6  pdca_review.sh              # 日次レビュー
# 週次（日曜）
0  5 * * 0    pdca_weekly_content.sh      # 週次バッチ生成 ⚠️ exit_code:78（Claude CLI認証エラー）
0  6 * * 0    pdca_weekly.sh              # 週次総括
# 毎日
0  2 * * *    autoresearch（Claude CLI）   # SNSスクリプト自動改善
0  3 * * *    log_rotate.sh               # ログローテーション
30 6 * * *    pdca_hellowork.sh           # ハローワーク求人全自動パイプライン
0  8 * * *    meta_ads_report.py --cron   # Meta広告日次レポート
5  8 * * *    ga4_report.py               # GA4/SC日次レポート
# 常時
*/30 * * * *  watchdog.py                 # システム監視（Worker健全性+ハートビート+自己修復）
```
※ slack_commander.py は現在crontabに未登録（Slack監視はslack_bridge.py手動実行で代替）

## 解決済みの問題
- cron "Not logged in" → ensure_env() 修正で解消
- Cloudflare token認証エラー → load_dotenv() 追加で解消
- healthcheck false CRITICAL → upload_verification方式に変更で解消
- watchdog Slackスパム → 4時間デdup + daily resetで解消
- TikTok投稿失敗 → **手動運用に移行**（全自動方式は未解決。healthcheckのTikTok誤検知は抑制済み）
- ANTHROPIC_API_KEY未設定 → Cloudflare Workers AI（Llama 3.3 70B）で代替

## デプロイ状態
- **GitHub Pages**: ✅ 公開中（quads-nurse.com）※Netlifyは帯域超過で停止、GitHub Pagesに移行済み
- **SSL**: ✅ Let's Encrypt自動発行
- **Cloudflare Worker**: ✅ robby-the-match-api デプロイ済み（LINE Bot + AIチャット）
  - シークレット7件設定済み（LINE×3 + Slack×2 + OpenAI + ChatSecret）
  - ⚠️ デプロイ後にシークレット消失する問題あり → 必ず `wrangler secret list` で確認
  - AI相談: OpenAI GPT-4o-mini優先 → ctx.waitUntilバックグラウンド + Push API
  - LINE通知先: C0AEG626EUW（ロビー小田原人材紹介）
- git remote: origin https://github.com/Quads-Inc/robby-the-match.git
- デプロイ: `git push origin main && git push origin main:master`

## SEO状態
- ドメイン: quads-nurse.com（Netlify）
- 子ページ: area/21 + guide/41 = 計62ページ + ブログ18記事
- sitemap.xml: 87 URL（lastmod 2026-02-28）
- 全ページSEOメタ完備（twitter:card, og:locale, meta robots）
- GA4: G-X4G2BYW13B / Search Console: 登録+sitemap送信済み
- 構造化データ: index.html(5種) + LP-A(4種) + area(2種) + guide(2種)
- 競合ゼロKW: 「神奈川県西部 看護師」「紹介料 10%」

## 次にやるべきこと（優先順）

### 🔴 即座に実行（残り: 手動作業のみ）
1. ~~worker_facilities.js再生成~~ → ✅ 既に212施設で同期済み
2. ~~posting_queue.json復旧~~ → ✅ 修復完了（101件クリーン）
3. **Search Console**: 優先10URLのインデックス登録リクエスト（手動）
4. **TikTokプロフィール更新**: 名前「神奈川ナース転職｜シン・AI転職」、リンクをLP URLに変更（手動）
5. **Instagramプロフィール更新**: 同上（手動）

### 🟡 早めに対応（残り1件）
1. ~~sitemap.xml lastmod更新~~ → ✅ 全88URL を2026-04-01に更新済み
2. ~~ログローテーション整備~~ → ✅ log_rotate.sh + cron毎日3:00
3. **TikTok投稿キュー差し替え**: 上位20件のCTAを「30秒AI診断」に変更
4. **LINE Bot初回メッセージ改修**: UTMパラメータ対応（worker.js）

### 🟢 自動化済み（人間の操作不要）
- TikTok自動投稿: pdca_sns_post.sh（12:00/17:00/18:00/20:00/21:00）
- AIコンテンツ生成: pdca_ai_marketing.sh（06:00）
- 週次バッチ: pdca_weekly_content.sh（日曜05:00）
- Instagram エンゲージメント: instagram_engage.py（12:00）
- Instagram 自動投稿: auto_post.py（17:30、ランダム遅延付き）
- システム監視: watchdog.py（30分間隔）
- ハローワーク求人取得: pdca_hellowork.sh（06:30）
- Meta広告レポート: meta_ads_report.py（08:00）
- GA4/SCレポート: ga4_report.py（08:05）
- 投稿プレビュー+承認: post_preview.py（16:00）+ slack_reply_check.py（16:30/17:00/17:15）
- SEO/障害/競合/コンテンツ/レビュー: 各cronジョブ稼働中

### ⏳ 後回し
- Googleビジネスプロフィール登録（手動）
- LP-B施設向け（Phase2）
- TikTokプロフィール設定（ユーザー名・画像・リンク変更）

## 戦略メモ
- 3軸: 手数料破壊(10%) x 地域密着(関東4都県) x 転職品質
- 訴求: 「LINEで静かに、転職活動。」— 電話なし・名前不要・ブロックOK
- 導線: SNS/広告 → LINE友だち追加 → 5問タップ → 求人10件 → 担当者引き継ぎ
- DB: 施設24,488件 + 求人2,936件（毎朝自動更新）
- AI自動化: ai_content_engine.py（品質スコア8.0/10）+ 日次/週次PDCA

---

<details>
<summary>過去の構築履歴（2/21〜2/24）</summary>

### 2/21: SNS自動化 + Agent Team基盤
- tiktok_post.py / tiktok_auth.py / pdca_sns_post.sh / posting_queue.json
- cron致命的問題4件修正（timeout/git push/Block Kit/Slack双方向）
- Agent Team強化（gtimeout/tiktok_analytics/analyze_performance/KPIデータ）
- エージェント自律能力（content_pipeline.py/エージェント間通信/自己修復）
- AI対話後UX（施設DB 15件/extractPreferences/scoreFacilities/レコメンドUI）

### 2/22: AI対話サービス品質最大化
- Value-First変換（Phone gate後方移動）/ LP-Aチャットウィジェット統合
- AIプロンプト品質強化 / メッセージ制限UX / モバイル最適化
- 全97施設DB + Haversine距離計算 + 駅選択UI構築
- Cloudflare Worker複数回デプロイ

### 2/23: AIチャットUX v2.0 全面改修
- 6エージェント世界水準リサーチ → chat.js/css 大幅軽量化
- ゼロ摩擦開始 / 3問会話形式 / 施設カード→LINE誘導
- ブログ3記事追加（計18記事）

### 2/24: Netlify独自ドメイン + SNS再構築
- Netlify移行 / quads-nurse.com取得 / 全96ファイルURL移行
- SEOヘッダー / Search Console / Microsoft Clarity
- TikTok投稿失敗根本修正 → カルーセル方式転換
- generate_carousel.py / sns_workflow.py / ai_content_engine.py構築
- Instagramアカウント作成（@robby.for.nurse）

</details>
