# ナースロビー 状態ファイル
# 最終更新: 2026-04-25 04:00 by SEO朝サイクル

## 🏁 2026-04-24 夜 Meta広告監査+クリエイティブ検討（別ターミナルセッション）

### Meta広告アクション
- 放置adset `kanagawa_nurse_25-40F` (120243048687870457) を APIで PAUSED化
- v7_ad2 は既に PAUSED 済み確認
- **STATE.mdの「Meta APIトークン無効化」は誤記** → 現行トークンは `ads_management` scope付きで永久有効。今後API経由で操作可能

### 時間帯別パフォーマンス（7日 04-17〜04-24、hourly breakdown）
- Lead発生: 00時/09時/18時に3件分散（通勤・帰宅・就寝前の"スイッチ時間"）
- CTR最強: 早朝04-07時（3.85-5.00%）→ 夜勤明けゾーン
- imp最多: 夜22-23時（471）だがLeadゼロ → 訴求が弱い
- 無駄配信: 昼14-17時 ¥2,507消化 / CTR 0-1.53% / Lead 0 → dayparting除外候補

### クリエイティブブレスト（途中で画像生成に移行）
- 社長制作の2クリエイティブ評価: 実写黒版採用、紫イラスト廃案
- 共通課題: AI訴求が前面、数字ゼロ、売り手視点、差別化弱い
- ChatGPT用プロンプト提供（Pattern A夜勤明け/Pattern B夜ソファ）
- **実データ確定（ハローワーク n=451、神奈川県看護師正社員）**
  - 月給中央値: 下限¥220,000 / 中点¥250,000 / 上限¥270,000
  - 病院のみ(n=122): 中点¥240,330
  - 夜勤あり(n=123): 中点¥239,700（基本給のみ、手当別）
- ⚠️ 架空数字「36万円」を初回提示して指摘で発覚→訂正、memory更新

### 判断待ち
- v7_ad1_bedtop_動画 停止可否（CPL ¥3,169 vs v7_ad3 ¥1,800）
- ChatGPT生成画像の納品（Pillowでテキスト焼き込み予定）
- 広告コピーに使う数字選択: 月給上限¥27万 / 賞与4.0ヶ月 / 求人451件 から

---

## 🏁 2026-04-24 夕 SEO全305ページにAI転職FABカード展開 (commit 467bab4)

### 成果物
- 画像FAB: `assets/fab-card-v1.png` (640×422 @2x, 127KB, Retina対応)
- 共通CSS: `assets/design-tokens.css` に `.nr-fab-wrap/.nr-fab-link/.nr-fab-close` 追加
- 共通JS: `assets/nr-fab.js` (閉じるボタン挙動, sessionStorage 記憶)
- FABデザイン: グリーン基調・看護師キャラ・「LINEでAI転職始める。」

### 展開範囲 (305ページ)
- blog/ 全記事 (sub + index)
- lp/job-seeker/area/ (sub + index, 地域別求人)
- lp/job-seeker/guide/ (sub + index, 転職ガイド)
- lp/job-seeker/index.html (LP-A)

### 進化の経緯
- v0: ピル「LINEで求人を相談する →」(既存)
- v1案: 3機能明示カード (CSS版、ワード検討) — 「忙しい看護師さんこそ、AIで効率化。」
- v2: 画像カード 320x211 (仮版、Retinaボケでrevert)
- v3: 画像カード 640x422 @2x (本番採用)

### 次のタスク候補
- 効果計測 (Meta広告CPA vs LINE登録率の乖離解消見込み)
- 別パターン画像のA/Bテスト
- 画像ブラッシュアップ (社長から改善版が来たら差し替え)

---

# 最終更新: 2026-04-25 04:00 by SEO朝サイクル

## 🏁 2026-04-24 午後 LINE Bot UX全面改修 (Worker 9f04af56)

全コミット: f7d1d9d → 6ab2892 → 769c0a5 → 4837668 → 5e29c6a

### 背景
社長指摘「初見ユーザーが初回3問で『資格選択ボタンがどこ？』と迷う」。
Quick Replyはキーボード上部に細く出るだけで初見では気づきにくい。
→ Flex Messageのインラインボタン化で根本解決。

### 1. 選択式UIをFlex Messageに全面移行
- 共通ヘルパー追加: `buildChoiceFlexBubble(title, hint, opts, backOpts?)`
- 変換した11フロー:
  - 初回3問: Q1資格選択(5肢)/Q2年代選択(6肢、inputOption保持)
  - welcome: area_page 4肢 / default 3肢
  - intake_light: il_area/il_subarea(東京・神奈川・千葉・埼玉・other・default)/il_department/il_workstyle/il_urgency/il_facility_type

### 2. デザイントークン確立（リッチメニューv3ピンク統一）
- ヘッダーBG: `#E8756D` (--nr-color-secondary) + 白太字
- primaryボタン: `#E8756D`
- 戻る系: `link` style（控えめ）
- 色理由: richmenu v3 BG=#F3B7BD〜#FDB1AE の濃い版で同系統
- memory保存: `feedback_line_flex_colors.md`（次回Flex作成時必読）

### 3. 新着求人フローの丁寧語統一（11箇所）
- 社長指摘「小田原エリアは本日の新着求人なし。」が失礼
- 主な修正:
  - 0件時: 「本日の新着なし」→「本日の新着求人がございませんでした。直近1週間の新着求人を○件お届けします」
  - 通常時: 「新着 ○件」→「新着求人を○件お届けします」
  - CTA: 「ここに出るのは一部」→「表示しているのは一部です」
  - Opt-in: 体言止め「1日1通まで」→「1日1通までのお届けです」等
  - 「見ますか？」→「ご覧になりますか？」
  - 「停止しました」→「停止いたしました」
- 適用範囲: richmenu新着求人タップ時の表示＋毎朝Push通知

### 残課題（指示待ち）
- 他のLINE Flex（会員登録/mypage誘導/CTA等）はまだ teal/緑 配色のまま
  → 全面ピンク統一するか社長判断
- matching結果後の contextual QR（「他の求人も見る」「条件を変える」等）もQRのまま
  → 全選択式をFlex化するか判断
- matching/resume/handoff フローの丁寧語チェック未実施

---

## 🏁 2026-04-24 午前 SEO記事→LINE送客 右下FAB導入 (commit 80ee5e6)

### 背景
- SC実データ: 「退職交渉」は流入ゼロ（社長の認識誤り判明）
- 「横浜 看護師 給料」順位1.0 / 「神奈川 看護師 給料」順位7.1 が真の武器
- ただし4週間でサイト全体クリック2件のみ。流入絶対量不足
- 既存 `.mobile-sticky-cta` はモバイルのみ下部フルバー

### 実装（B: 右下固定LINEボタン PC+モバイル両対応）
- `assets/design-tokens.css` の `.mobile-sticky-cta` を右下ピル型FABに改修
- LINE公式アイコン(SVG data-URI) + テキスト、LINE緑グラデ、0.8s遅延フェードイン
- CSS-only アニメで JS非搭載22ページでも表示
- 全305ページに即時反映（実機Chrome DevTools PC:1920x800で確認済）
- モバイル CSS値確認済 (223x50px, bottom:16px, right:12px) / スクショはタイムアウト未取得

### 🔴 次回継続タスク（社長ワード選定待ち）
現状のボタン文言「LINEで求人を相談する →」は情報収集フェーズの読者に重い。
社長に以下5案を提示、選定待ち:
- A: 「AIで無料・転職相談」（推奨）
- B: 「30秒で無料・AI転職診断」
- C: 「LINEで気軽に・無料AI相談」
- D: 「AI転職、まず無料相談」
- E: 「無料・AIが合う求人を探す」

選定後、305ページを一括置換予定（grep対象: 既存文言7パターン）。
関連ファイル: blog/*.html, lp/job-seeker/{area,guide}/*.html, lp/job-seeker/index.html

### 次に検討する集客施策（FAB反映後）
- A案: 給料ページ（順位1位・7位）にリードマグネット「AI年収診断」設置
- C案: 給料系タイトル/メタ最適化でCTR底上げ
- D案: エリア×転職ページ(順位40前後)の内部リンク強化で1ページ目押上げ

---

# 最終更新: 2026-04-25 04:00 by SEO朝サイクル

## 🏁 2026-04-23 夜 セッション総括 (LINE Bot 大改修) — 最終 Worker `bc3d8589`

全コミット: 52bbad1 → ad3c60c → f024ba7 → 9cbfe6e → c0479fc → 6c65f6a → 66eb6a4 → 4b11ad8 → d6018a2 → 943de01

### マイページ
- 認証失敗フォールバック画面を auth.html デザインに統一 (絵文字全廃、SVGアイコン化)
- 全5画面 (index/preferences/favorites/resume/edit) でロゴヘッダー保持
- スクショ: `docs/audit/2026-04-22-resume-security/screenshots/v3_*.png`

### 「気になる求人」(旧お気に入り)
- ⭐保存 postback ボタンを4種カルーセル全部に追加
  (matching / 新着Push / リッチメニュー新着 / フォールバック施設)
- fav_add ハンドラを3段検索化 (matchingResults→lastShownJobs→D1直引き)
- 「お気に入り」→「気になる」業界標準語に一斉リネーム
  (LINE Bot ボタン文言/返信/マイページUI 全部 / KV/API/パスは保持)

### リッチメニューv3 (richmenu-51903fc26a2da8f99bb7ae769c285b35)
- 画像: `assets/richmenu/richmenu_v3_20260423.png` (2500x1686, 753KB)
- 5タイル: お仕事探しスタート / NEW新着求人 / **MYPAGE** / CONTACT / SUPPORT
- areas座標 Pillow解析でピクセル単位測定
- rm=mypage postback inline ハンドラ追加 (会員→HMAC URL / 非会員→30秒登録Flex)
- 7ペルソナ静的解析テスト 14項目全PASS (`scripts/test_richmenu_personas.py`)

### LINE Bot UX 統一・改修
- 新着カード「この施設について聞く」→「読み取れませんでした」バグ修正
  (handleFreeTextInput 最先頭に「○○について相談したい」全フェーズ共通マッチ追加)
- 「担当者に引き継ぎました」メッセージを buildHandoffConfirmationText() に集約
  (5パターン散在を全経路統一)
- 年収相場(info_detour)導線をBotから全廃 (7箇所削除)
  → 全ユーザー matching_preview 直行に統一
- 3問完了サンクス画面のQR (rm=start/welcome=newjobs_optin) 削除
  → リッチメニュー誘導文言に変更 (毎朝→定期的に / お仕事探しスタート説明追加)
- rm=start を賢くして entry.area 保持時は il_facility_type 直行
  (「別システム稼働した感」根本解消)

### 残課題 (緊急度低)
- salary-check/index.html リファクタ (相場比較→求人件数段階表示) 未着手
  → 22日前のメモ参照 `~/.claude/projects/-Users-robby2/memory/project_next_task.md`
  → Bot動線ゼロになったので緊急度低
- 4状態リッチメニュー (hearing/matched/handoff) は当面 default 流用
  → 必要なら専用画像作成
- lineReply 失敗時 (LINE API 5xx) のリカバリ try/catch なし → 監視で観察

---

## 🏁 2026-04-23 夕方 Meta広告監査+計測修復+Clarity統合 (前セッション)

## 🏁 2026-04-23 夕方 Meta広告監査 → 計測修復 → Clarity日次レポート

### Meta広告監査 (docs/audit/2026-04-23-meta/META-ADS-REPORT.md)
- 総合スコア 34/100 (F)
- v7キャンペーン7日 (04-16〜04-22): ¥13,909 / Lead(CTAクリック)2件 / 本物Lead(CompleteRegistration) 広告レポート上0件
- Pixel本体は CompleteRegistration 受信確認済み (4/22に14件、4/23に1件)
- 明日2026-04-24が1週間テスト判定日。現時点では🔴破綻確定ゾーンだが、計測バグ排除後に真の判定

### 計測修復 (commit df217e7)
- 真因: LP(quads-nurse.com)↔Worker(workers.dev) クロスドメインで _fbp/_fbc Cookie が伝わらず、CAPI送信時に attribution 失敗
- 修正1: LP側で document.cookie から _fbp/_fbc を読み、/api/line-start の URL param に付与
- 修正2: Worker 側で URL param を優先、Cookieフォールバック
- 修正3: CAPI user_data に phone/email を SHA256 hash 送信 (EMQ向上)、external_id もhash送信
- 修正4: meta_ads_report.py に CompleteRegistration 列追加、CPA 2種 (クリック/登録) 表示
- Worker version: 0cc2647a-e88f-4b5c-a421-991760fe9030
- 効果: 今後24-48hの新規クリックから fbp/fbc が流れ、数日以内に広告レポートに本物Lead反映見込み

### Clarity 日次レポート (commit a9ac69c)
- scripts/clarity_report.py 新規追加 (284行)
- cron: 毎朝 08:15 JST に #ロビー小田原人材紹介 へ自動配信
- 取得: セッション/Bot比率/スクロール/レイジ/デッドクリック/Quick Back/JSエラー/ページ別Top5/UTM別Top5
- 閾値アラート: RageClick≥10, DeadClick≥20, ScrollDepth<40%, BotRatio≥30%
- **残作業 (社長手動1分)**: clarity.microsoft.com → Settings → Data Export → API token生成 → .envのCLARITY_API_TOKENに記入
- .env に CLARITY_PROJECT_ID=vmaobifgm0 プリセット済み、CLARITY_API_TOKEN 空欄

### 追加検出 (判断待ち)
- ACTIVE広告セットがもう1つ放置: `kanagawa_nurse_25-40F` (LANDING_PAGE_VIEWS最適化、配信¥0)
- 現広告セット `nurse_kanagawa_lead_IG+FB` の optimization_goal=LEAD (LPクリック最適化) → 本物LeadのCompleteRegistration最適化に変えたいが学習リセット伴う

---

## 🏁 2026-04-23 マイページUI統一 微調整 (commit 52bbad1)
- mypage.js の認証失敗フォールバックを auth.html デザインに統一
  - `document.body.innerHTML` 全置換 → `renderMypageNotice()` ヘルパーに集約
  - 5画面 (index/preferences/favorites/resume/resume/edit) でロゴヘッダー保持
  - 🔒🔌 絵文字 → SVG (lock/wifi-off/user-plus/clock) に置換、絵文字全廃完遂
  - body 直下の hero/form/loading/app/sticky-bar を一括非表示 (edit.html漏れ対応)
- 検証: Playwright iPhoneビューポートで全6URL再撮影、全画面でデザイン統一確認
- スクショ: `docs/audit/2026-04-22-resume-security/screenshots/v3_*.png`

## 🏁 2026-04-23 別セッション作業: 会員制ナースロビー完全構築 + UI整備
- 履歴書作成画面 UI完璧化 (絵文字全廃・ロゴ入り・ヒーロー・信頼フッター)
- 郵便番号→住所自動入力(zipcloud API)
- 学歴フォームに入学/卒業両方の年月
- マイページ群8ファイル UI統一 (commit 87d898d)
- **次回起動時必読**: `docs/audit/2026-04-22-resume-security/handoff-next-session.md`
- 次のタスク: 代表の実機LINEで認証付き全フロー確認 (履歴書→マイページ→編集→希望条件→お気に入り)

## 🏁 2026-04-23 本日の成果（AICA MVP2 + キャリアシート）

### AICA 大型アップデート（全14/20フェーズ完了）
- ✅ **キャリアシート自動生成 Layer 1**（commit 2e641b4 / 3e46789 / 55491de）
  - 条件ヒアリング完了でバックグラウンド自動生成
  - AI推薦コメント3段落250-400字（魅力的かつ嘘なし）
  - 禁止語検出→リトライ→伏せ字マスクのハルシネーション対策3段構え
  - A4縦1枚HTML、FAX返信欄付き、印刷対応
  - 社長Slackに候補者サマリ+URL通知
  - Worker endpoint: GET /career-sheet/:serial（noindex）
  - 既存候補者手動生成: POST /admin/career-sheet/generate（AICA_ADMIN_KEY認証）
- ✅ **Phase 14 病院推薦文送付準備**（commit 3a62649）
- ✅ **P0改善3件**（commit 9480793）：電話番号後回し / Q&A文言 / PAUSED cron
- ✅ **P1改善2件**（commit 4876b12）：/health deep / 志望動機フッター

### 最終 Worker Version: `ce57e3ce-760d-43c7-bb40-c7dd3524dc65`
### 次回セッション必読
- `docs/audit/2026-04-23-aica/HANDOFF.md` ← **AICA最新引継ぎ**
- `docs/audit/2026-04-22-aica/misaki_demo_walkthrough.md` ← ミサキ+6人パネル評価

### AICA 経営判断待ち
- キャリアシート送信元情報（電話・メール・許可番号）
- 履歴書フロー方針（AICA並走 / ナースロビー誘導）
- Layer 2（候補者opt-in配信）進むか否か

---

## 🏁 2026-04-22 本日の成果（新着求人システム完全実装）

### 核心機能
- ✅ **D1 jobs に `first_seen_at` カラム追加**（31日分スナップショット履歴から逆算、毎朝06:30 cron で自動更新）
- ✅ **リッチメニュー「本日の新着求人」**: エリア別検索 + 本日初出優先 → 0件時7日フォールバック + 非公開求人CTAバブル
- ✅ **LINE友だち追加で `newjobs_notify` KV 自動登録**（完全 opt-out 設計、ブロックで自動解除）
- ✅ **エリア自動推定**: LP診断 → 郵便番号(POSTAL_PREFIX_TO_AREA 3桁) → 駅名テキスト(AREA_CITY_MAP 逆引き) → 神奈川全域デフォルト
- ✅ **毎朝10時JST Push cron**: 購読エリアの本日初出 S/A/B ランク求人を最大3件Push（0件なら送らない）
- ✅ **管理用手動発火エンドポイント**: POST `/api/admin/trigger-newjobs-push` (secret+fallbackDays option)
- ✅ **3問intake完了で entry.area も郵便番号/駅名から上書き**
- ✅ **エリア選択優先ルール統一**: 最後のユーザー選択を優先（LP → 郵便番号 → 「エリアを変える」QR → リッチメニュー新着エリア選択、全て entry.area を上書き）

### バグ修正（同日対応）
- ✅ 5箇所のローカル AREA_LABELS マップを `getAreaLabel()` に一元化（tokyo_south 等の英字表示バグ根治）
- ✅ ブロック後のKV残存 entry.area を郵便番号/駅名が上書きするよう resolveNotifyAreaKey() 追加
- ✅ handoff guard で「この施設について聞く」message が沈黙していた問題→ 正規表現で検出して即返信 + entry.interestedFacility 保存
- ✅ 新着求人Push 末尾QR をリッチメニューが覆い隠していた → 末尾テキスト+QR削除
- ✅ Pushカードの「[Sランク]」表示削除、検索カードと項目完全統一（月給/賞与/勤務時間/駅/休日/契約期間/加入保険/施設名）
- ✅ Welcome・待機画面・登録完了メッセージから「朝10時」「1日1通」等の説明削除 → 『定期的に新着求人も配信しております』に簡素化
- ✅ カルーセル末尾「ハローワーク公開求人の一部」注釈削除

### Worker / commit
- 最終 Worker Version: `f7aeba79`
- 最終 commit: `3a26bd4` (main/master 両branch 同期)
- デプロイ回数: 約10回（段階的改善）

### 詳細メモリ
- [新着求人通知システム](.claude/projects/-Users-robby2/memory/project_newjobs_notify.md)

## 🏁 2026-04-18 本日の成果（セッション中）
- ✅ Phase 2 #33 訪問看護ST投入: facilities 24,488→29,549件（訪問看護ST +5,061件、関東4都県、厚労省関東信越厚生局 ZIP）
- ✅ UXバグ修正: sub_type '訪問看護' 統一 / 重複 -2 / city空欄 -162 / worker.js 変更不要
- ✅ GBPやらない決定をMEMORY/STATE/HANDOFFに反映、登録ガイドは revert
- ✅ runbook §2/§4 実地検証で不整合2箇所修正（autoresearch watchdog外 / slack_commander未登録が正常）
- ✅ Editorial Calm Japan デザイン策定 + area 31ページ v2展開（編集部誌面風、モバイル2段ブレイク対応）
- ✅ ロビー裏方ルール策定（🤖絵文字禁止・キャラ一人称禁止、署名=編集部）
- 📝 SEOボリューム戦略策定 → docs/seo_volume_strategy.md（社長判断3件待ち）

## 判断待ち（社長）
- guide 48ページ外装v2化 / 新規ロングテールguide / area×条件 124ページ 等のSEO量的施策
- Meta広告 S-04〜S-10（実機ペルソナテスト結果は docs/audit/2026-04-17/implementations/misaki_test.md）
- autoresearch復旧方式（claude auth login vs .envにANTHROPIC_API_KEY）

---
# 最終更新: 2026-04-25 04:00 by SEO朝サイクル

## 運用ルール
- 全PDCAサイクルはこのファイルを最初に読む（他を探し回るな）
- 次回セッションは `docs/audit/2026-04-17/HANDOFF.md` を必ず読め
- PROGRESS.mdには履歴として追記（こちらは状態のスナップショット）

## 現在のフェーズ
- マイルストーン: **Week 6**（2026-04-03〜）
- North Star: 看護師1名をA病院に紹介して成約
- 状態: **総点検+Phase1-3+優先度A手動対応 全完了 → 効果検証フェーズ**

## 🎯 2026-04-17 Meta広告 1週間計測期間 (〜04-24)

### 社長決定
- **現状維持で1週間計測** (設定変更しない)
- 判定日: 2026-04-24

### 今日実装完了 (計測修復)
- LP修正 commit 3b5c599: session_id永続化 / utm継承 / Lead発火1回制限
- LP修正 commit 56121ea: hero-text-overlay削除 (FVにCTA復元)
- LP修正 commit 4459e81: CTA "LINEで求人を見る(無料)" + LINEロゴ
- meta_ads_report.py: 自動判定 _auto_judge() 追加 (毎朝08:00 cron)
- ターゲティング: 25-49F / 関東4都県 / Advantage+ OFF / IG 3面
- 監査レポート: `docs/audit/2026-04-17-meta/` 6本

### 未完 (4/24判定後に再検討)
- 設計欠陥2 dm_text LIFF化 (工数2h)
- Ads最適化目標 Lead→CompleteRegistration 変更
- Custom Audience / Lookalike (ToS承諾後)
- クリエイティブ刷新 (具体病院名+月給訴求)

### 判断基準 (7日累計CompleteRegistration)
- 0件 → 🔴 広告停止 → ¥60,000/月を別投資
- 1-3件 → 🟡 希望あり、調整継続
- 4件以上 → 🟢 スケール検討

### 詳細
`~/.claude/projects/-Users-robby2/memory/project_meta_ads_1week_test.md`

## 🏁 2026-04-17 総点検 + Phase 1-3 + 社長優先度A全完了

### 引き継ぎ資料
- **次回必読**: `docs/audit/2026-04-17/HANDOFF.md`
- 詳細レポート: `docs/audit/2026-04-17/report.md`
- 3分要約: `docs/audit/2026-04-17/executive_summary.md`
- 82阻害要因 → 68独立項目 → **66項目実装完了**

### ✅ 社長手動完了（優先度A）
- S-01 Claude CLI auth ✅
- S-07 Search Console API 権限付与 ✅（GA4レポート403解消確認済）
- S-02 TikTok bio 差し替え ✅
- UptimeRobot 3モニター5分間隔稼働 ✅

### 🟡 社長判断待ち（優先度B・急がない）
- S-04 Instagram投稿頻度 3→2
- S-05 Meta広告 Lead目的継続判断
- S-06 LINE Bot内「10%」訴求非表示判断
- S-08-10 広告コピー3本差し替え（ミサキテスト結果: implementations/misaki_test.md）

### ⏳ 保留（優先度C・任意）
- #33 訪問看護STデータ投入（要データソース調査、8-12h）
- ~~#37 GBP登録申請~~ — **やらない**（2026-04-17 社長決定）

### 📊 48時間以内に検証する数字
- Meta Lead vs LINE登録 乖離: 7.5倍 → 1-2倍に収束見込み
- AI応答成功率: 85-95% → 99.9% 見込み
- 求人ヒット率（神奈川）: 469 → 814件（+73.6%）、明日06:30 cron反映
- Search Console データ取得: 明日08:05で復活
- autoresearch: 明日02:00で復活

### 📝 点検で判明した古い記述の訂正（本セッションで修正済）
- 「LINE登録0」→ 4/14 3人, 4/15 15人, 4/16 不明
- 「AI応答 4段フォールバック」→ 旧: 排他1段 / 新: 実装済み（OpenAI→Claude→Gemini→Workers AI）
- 「診療科100%」→ 病院1,498件サブセットのみ（DB全体24,488件では6.1%）
- 「prefecture空欄修正済」→ 旧: 877件残存 / 新: 0件（814件、神奈川+73.6%）
- 「area/21 + guide/41」→ 実際: area/32 + guide/48

### 🚀 本番反映済み
- Worker Version: 54957ab3（/api/health?deep=1 で AI稼働確認済）
- D1 スキーマ: confidential_jobs + phase_transitions + 7インデックス追加
- git: main / master 両branch 最新（commit b12d098）
- cron: */15 15min handoff follow-up 追加

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
