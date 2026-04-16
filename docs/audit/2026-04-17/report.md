# 神奈川ナース転職 総点検レポート — 2026-04-17

> **発注者**: 平島禎之（社長）
> **実施体制**: 4パネル×6専門家+議長=28人 + 品質監督 + 戦略監督 = 30人
> **成果**: 82阻害要因 → 重複排除 68項目 → Phase 1=28 / Phase 2=22 / Phase 3=13 / やらない=5 / 社長判断待ち=6
> **品質スコア**: 8.5/10（品質監督）/ 禁止事項違反=なし（戦略監督）

---

## 経営サマリ（3分で読む）

### 現状診断
- PV/日 **3**、インデックス **17/87**、成約 **0**
- **LINE登録は既に発生している**（4/14 3人 / 4/15 15人 / 4/16 確認不可）— STATE.mdが古い
- Meta広告v7は **合格圏**（¥7,064/3日、CPA¥642-1,306）だが計測不安定
- **Lead計測と実LINE登録が7.5倍乖離**（4/15: Lead 2件 vs LINE 15人）

### 最大のボトルネック3つ
1. **LP診断→LINE引き継ぎの穴**: session_id直リンク化でファネル中盤が断裂（ファネル30-50%漏れ試算）
2. **AI応答「4段フォールバック」が虚偽**: worker.js L1779-1851 は排他分岐でOpenAI落ちたら全停止
3. **prefecture空欄877件(29.6%)**: 神奈川検索で3割の求人が脱落 → ミサキ「0件」→離脱

### 24時間で直す5つのゲートキーパー（NS寄与度9-10）
| # | 項目 | コスト | 実行 |
|---|-----|-------|------|
| 1 | LP診断→LINE引き継ぎ復活 | 2-3h | Claude |
| 2 | AI応答 try/catchフォールバック実装 | 3h | Claude |
| 3 | Meta Pixel Lead復旧+CAPI | 0.5h+4h | Claude |
| 4 | SNS投稿パイプライン復旧 | 4-6h | 社長認証+Claude |
| 5 | prefecture空欄877件修正 | 3h | Claude |

**Phase 1合計**: 28項目 / 30-38h / 並列着手で**1.5日**

---

## 社長に今すぐ承認お願い（3件・10分で完結）

| # | 承認依頼 | 判断理由 |
|---|---------|---------|
| **S-01** | Claude CLI 認証復旧 (`claude auth login` 実行) | autoresearch+pdca_weekly_content が5日連続失敗。SNS改善ループ停止中 |
| **S-02** | TikTok プロフィール bio 差し替え承認 | 「神奈川の看護師転職 / 手数料10% / LINE相談」で良いか |
| **S-07** | Search Console API 権限付与（odawara-nurse-jobs サービスアカウントにGSCフル権限） | SEO健康状態が全く追えない。ga4-credentials.json の email をGSC管理画面で追加 |

この3件承認後、Claudeが残り25項目を並列着手可能。

---

## Phase 1（即時実行・28項目）

### ゲートキーパー級（NS寄与度 9-10）

#### 1. LP診断→LINE引き継ぎ復活 ★最優先
- **NS寄与**: 10
- **根拠**: `shindan.js:460-473`（直リンク化）/ `worker.js:3110-3125`（受け口は生存）/ `index.html:1837`
- **改善**: shindan.js / index.html のCTAを `/api/line-start?source=shindan&session_id=${sid}&answers=${encoded}` 経由に戻す
- **インパクト**: ファクト§3 "Lead2 vs LINE登録15" 乖離の主原因と仮説。ファネル中盤30-50%改善
- **コスト**: 2-3h
- **実行**: Claude自動

#### 2. AI応答 try/catchフォールバック実装 ★最優先
- **NS寄与**: 10
- **根拠**: `worker.js L1779-L1851`（if/else if/elseの排他分岐）/ STATE.md記載「4段フォールバック」は虚偽
- **改善**: try/catchで順次試行（openai→workers-ai 最低2段）。Workers AI Llama 3.3 70B は既設・無料
- **インパクト**: AI応答成功率 85-95% → 99.9%
- **コスト**: 3h
- **実行**: Claude自動

#### 3. M-01 Meta Pixel Lead復旧+CAPI
- **NS寄与**: 9
- **根拠**: ファクト§3（4/14 Lead4 / 4/15 Lead2 vs LINE15 / 4/16 Lead0）
- **改善**: Events Managerで発火テスト(30min) + Worker側CAPI有効化（既存実装あり、要起動）
- **インパクト**: 広告最適化AIの再学習 / CPA真値化
- **コスト**: 0.5h + 4h
- **実行**: Claude自動（**予算は一切動かさない**）

#### 4. M-03 SNS投稿パイプライン復旧
- **NS寄与**: 9
- **根拠**: TikTok 7投稿/キュー41ready/失敗24% + autoresearch 4/14-17 CONFIG_ERROR連続 + IG過密（A×2+B×1）
- **改善**: S-01後に pdca_sns_post.sh 失敗ログ精査 + TikTok Studio CDP復旧 + IG 1日1投稿に整理
- **インパクト**: 週1→週5本、再生3.5K→10K目標
- **コスト**: 認証30min（社長）+ 4-6h（Claude）
- **実行**: 混合（S-01後）

#### 5. prefecture空欄877件（29.6%）修正
- **NS寄与**: 9
- **根拠**: `hellowork_jobs.sqlite: SELECT COUNT(*) WHERE prefecture=''` = 877 / `worker.js L4702-4707`
- **改善**: `hellowork_to_d1.py L110-L130` の `AREA_PREF_REVERSE` を2段拡張（area→pref + 市区町村→pref）+ work_address抽出追加
- **インパクト**: 求人ヒット率 29.6pt↑、神奈川469件のうち100件以上復活
- **コスト**: 3h
- **実行**: Claude自動

### 高寄与級（NS寄与度 7-8）— 10項目

| # | 項目 | NS | コスト | 実行 |
|---|-----|----|-------|------|
| 6 | welcome QR 3択化（相場/相談/求人） | 8 | 30min | Claude |
| 7 | SC API 403 権限付与 | 8 | 15min | 社長 |
| 8 | M-07 ミサキテスト一気通貫（広告3本+Hero+welcome） | 8 | 1-2h | Claude |
| 9 | deploy_worker.sh シークレット消失自動検知 | 8 | 1h | Claude |
| 10 | SLACK_CHANNEL_ID デフォルト修正（7ファイル） | 8 | 30min | Claude |
| 11 | M-02 daily_snapshot.json 生成ヘルパー | 7 | 2-4h | Claude |
| 12 | Hero CTA「1分で診断する（電話なし）」**緑維持** | 7 | 30min | Claude |
| 13 | welcomeコピー短縮＋感情訴求分離（実測75-85文字を約50文字に） | 7 | 30min | Claude |
| 14 | M-05 handoff後24h自動フォロー＋Slackリマインダー | 7 | 2-3h | Claude |
| 15 | FAQ「神奈川のみ」vs 関東4都県矛盾解消 | 7 | 10min | Claude |

### 中寄与級（NS寄与度 4-6）— 13項目

| # | 項目 | NS | コスト |
|---|-----|----|-------|
| 16 | hellowork派遣 emp_type 除外フィルタ | 7 | 30min |
| 17 | 保育園/幼稚園/学校求人の除外フィルタ | 7 | 1h |
| 18 | Dランク低品質求人除外（エリア15件以上時） | 6 | 1h |
| 19 | クリニック検索時 departments フィルタbypass | 6 | 1h |
| 20 | M-04 Slack電話番号マスク（末尾4桁） | 6 | 1h |
| 21 | M-06 UTM命名規則＋click_cta GA4イベント | 6 | 2.5h |
| 22 | area空欄167件の市区町村逆引き | 6 | 2h |
| 23 | 「いつでもブロックOK」Final CTA 1箇所集約 | 5 | 10min |
| 24 | Final CTA文言差別化「匿名で相談」 | 5 | 20min |
| 25 | hero-note 視認性UP | 5 | 15min |
| 26 | 緊急キーワード粒度調整（「限界」降格） | 5 | 30min |
| 27 | 希望時間帯QR追加（夜勤明け午前/週末のみ） | 4 | 30min |
| 28 | 安心バー許可番号サイズ調整 | 4 | 15min |

**Phase 1合計: 28項目 / 30-38h / 並列着手で1.5日**

**実行順序（依存関係考慮）**:
`#10 → #15 → #12 → #13 → #6 → #16,17 → #2 → #1 → #5 → #3 → #9 → #11 → 残り`

---

## Phase 2（48時間以内・22項目）

| # | 項目 | 出典 | NS | コスト |
|---|-----|-----|----|-------|
| 29 | facilities↔jobs リンク再統合（has_active_jobs更新） | P3 | 8 | 6h |
| 30 | 診断Q5「情報収集」時の給与相場PDF導線 | P2 | 8 | 3-4h |
| 31 | Meta CAPI サーバーサイド完全実装 | P2 | 7 | 3-4h |
| 32 | scoreFacilities LP側 D1 24,488件対応 | P3 | 7 | 8h |
| 33 | 訪問看護ST データ投入（800件推定） | P3 | 7 | 8-12h |
| 34 | is_partner フラグ＋マッチング優先スコア | P3 | 7 | 3h |
| 35 | 逆指名フロー実装（施設名→Slack→24h回答） | P3 | 6 | 6h |
| 36 | sitemap lastmod動的化＋手動インデックス＋内部リンク強化 | P1 | 7 | 4-6h |
| 37 | GBP登録申請（住所非公開・サービスエリア）【社長要】 | P1 | 7 | 30min+認証葉書2週 |
| 38 | 診断Q1 `other` 選択時の早期離脱ルート | P2 | 6 | 1h |
| 39 | jobs-summary.json blurred 3枚保証 | P2 | 6 | 2h |
| 40 | 各 il_* フェーズ「前に戻る」QR追加 | P2 | 5 | 2-3h |
| 41 | follow時Push失敗Slack通知＋再送cron | P2 | 5 | 3-4h |
| 42 | shindan引き継ぎ待機短縮（事前生成） | P2 | 5 | 2h |
| 43 | welcome「5つタップ」→正直表記 | P2 | 4 | 1h |
| 44 | ADJACENT_AREAS越境同意QR | P3 | 5 | 3h |
| 45 | Slack Block Kit化（長文折りたたみ） | P3 | 4 | 3h |
| 46 | carousel_to_reel.py 復旧＋リール投稿 | P1 | 6 | 2h |
| 47 | IG エンゲージメント週1集計 | P1 | 4 | 2h |
| 48 | watchdog 重複排除修正 | P4 | 3 | 30min |
| 49 | scripts/deprecated/ 分離整備 | P4 | 3 | 2h |
| 50 | runbook.md 作成 | P4 | 4 | 2h |

---

## Phase 3（1週間以内・13項目）

| # | 項目 | 出典 | NS | コスト |
|---|-----|-----|----|-------|
| 51 | phase遷移ログをD1に記録＋週次レポート | P2 | 6 | 4-6h |
| 52 | 非公開求人テーブル＋バッジ表示 | P3 | 6 | 8h+運用 |
| 53 | 逆指名カードをフェーズB向けに | P2 | 4 | 1-2h |
| 54 | criticalCSS分離でLCP改善 | P2 | 4 | 4-6h |
| 55 | Hero画像テキスト→HTMLオーバーレイ | P2 | 3 | 3-4h |
| 56 | プログレスバー「1/5」ラベル明示 | P2 | 2 | 30min |
| 57 | E-E-AT強化（許可番号/編集方針/著者） | P1 | 5 | 4-6h |
| 58 | 競合ベンチマーク初回取得＋cron化 | P1 | 4 | 3h |
| 59 | UptimeRobot導入（5分監視・無料） | P4 | 4 | 15min |
| 60 | notify_slack.py を slack_bridge.py に統合 | P4 | 2 | 30min |
| 61 | content/generated/ 787MB アーカイブ月次化 | P4 | 2 | 2h |
| 62 | /api/health に ai_ok フィールド | P4 | 3 | 1h |
| 63 | Slack送信失敗時の alert_queue.json | P4 | 3 | 2h |

---

## やらないリスト（5項目・理由付き）

| # | 却下項目 | 却下理由 |
|---|---------|---------|
| X-01 | LPヒーローコピー A/Bテスト実装 | 社長承認が必要。Phase 1で即実行不可 |
| X-02 | Meta広告配信面拡張（リール/ストーリー追加） | 金額変更禁止ルールに抵触の懸念 |
| X-03 | Meta広告予算・入札額変更 | **禁止事項**（feedback_meta_ads_no_budget.md） |
| X-04 | OpenAI→Workers AI 全面切替 | 品質劣化リスク大。A/Bテスト未実施 |
| X-05 | Claude CLI全廃→ANTHROPIC_API_KEY直使い | API使用量ベース月コスト不明。月3万超新規契約禁止に触れる可能性 |

---

## 社長判断待ち項目（Phase 1から分離）

| # | 内容 | 判断ポイント |
|---|------|------------|
| S-01 | Claude CLI認証復旧 or ANTHROPIC_API_KEY 設定 | 運用継続方法 |
| S-02 | TikTok bio コピー | 文言承認 |
| S-03 | Instagram 投稿頻度 3→2 | 方式A停止可否 |
| S-04 | GBP登録申請 | 電話番号・認証葉書受取先 |
| S-05 | Meta広告 Lead目的の継続 vs 他目的 | CPA推移判断 |
| S-06 | 紹介フィー10%訴求のLINE側非表示 | 病院向け/求職者向け分離 |
| S-07 | Search Console API 権限付与 | GSC管理画面でサービスアカウントに権限付与 |

---

## 品質監督からの申し送り

- **ファクト検証スコア**: 17項目中15項目PASS（8.5/10）
- **架空データ検出**: 1件のみ（C-04 welcome文字数誇張 → 実測75-85文字。本レポートで訂正済）
- **ミサキテスト**: Phase 1候補10/10 PASS
- **差し戻し推奨**: なし
- **申し送り**: 計測系3件（SC権限 / daily_snapshot / GA4書き出し）を先行すべき

## 戦略監督からの申し送り

- **禁止事項違反**: なし
- **9原則**: 全PASS
- **ドキュメント虚偽3件を発見**（将来的にSTATE.md/CLAUDE.md要修正）:
  1. AI 4段フォールバックは未実装（排他分岐のみ）
  2. 診療科100%は病院1,498件サブセットのみ（DB全体では6.1%）
  3. prefecture空欄「修正済」は虚偽（実際は877件残存）
- **ボトルネック1点**: Claude CLI認証切れ1つがSNS自動改善ループ全停止の根本原因

---

## 24時間後チェックポイント

- ゲートキーパー5項目（#1-5）の実装完了
- Lead計測正常化（Meta Events Manager発火確認）
- prefecture空欄→0件確認
- AI応答フォールバック発火テスト成功
- SNSパイプライン再始動確認

---

## 48時間後チェックポイント

- Phase 2着手
- Phase 1効果検証（Lead数/LINE登録数/AI応答成功率の前後比較）
- daily_snapshot.json 生成開始

---

## 成果物インデックス

| ファイル | 内容 |
|---------|------|
| DESIGN.md | 点検フレーム設計書 |
| facts/FACT_PACK.md | ファクトパック（共通入力・全数値に根拠付） |
| panels/panel1_inflow.md | 流入パネル議長統合（17件） |
| panels/panel2_conversion.md | コンバージョンパネル議長統合（25件） |
| panels/panel3_matching.md | マッチング品質パネル議長統合（22件） |
| panels/panel4_infra.md | 基盤パネル議長統合（18件） |
| rounds/panel1-4_all_rounds.md | Round 1+2 生レポート（監査可能） |
| supervisors/quality_review.md | 品質監督レビュー（8.5/10） |
| supervisors/strategy_review.md | 戦略監督レビュー（優先順位付き） |
| **report.md** | **本レポート（統合ロードマップ）** |
| executive_summary.md | 3分要約版 |

---

**点検完了**: 2026-04-17
**次アクション**: 社長がS-01, S-02, S-07を承認 → Claudeが残り25項目並列着手
