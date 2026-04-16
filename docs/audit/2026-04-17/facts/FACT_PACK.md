# ファクトパック — 神奈川ナース転職 総点検 2026-04-17

> **全専門家パネルへの共通入力。このファイルの数字以外を引用する場合は必ず根拠ファイル/ログを明示すること。**
> 推測で数字を作ることは禁止。データがない項目は「データ不足」と明記。

## 1. North Star
看護師1名をSNS/SEO経由で獲得し、A病院に紹介して成約する。
現状: **成約0件**（Month3目標: 1件）

## 2. STATE.md のKPI（2026-04-17 時点）
- SEO子ページ数: 56目標 / 実績 area/32 + guide/48 = **80ページ**（⚠️ STATE.md記載 "62" とズレ）
- ブログ記事数: 10目標 / 実績 **19**（index含む）
- sitemap URL: **87** URL（lastmod 2026-02-28 や 2026-04-01 等混在）
- TikTok投稿: 7本済・キュー41件ready・48件posted
- Instagram投稿: 21本済
- AI品質スコア: 7.82-9.12（直近 #125-155）
- PV/日: **~3**（GA4 API取得、直近7日平均）🔴
- TikTok視聴/週: **~3.5K**（目標1万）🟡
- SCクリック/月: **25**🟡
- インデックス数: **17/87**🔴（80%がまだインデックスされていない）
- LINE登録数: 🔴 **STATE.md "0" は古い。広告ログで4/14 3人・4/15 15人の登録実績あり**
- 成約数: **0**

## 3. Meta広告（v7）— 直近3日実績

| 日付 | 消化 | リーチ | imp | クリック | CTR | CPC | LP閲覧 | Lead | CPA | LINE登録 |
|------|------|--------|-----|--------|-----|-----|--------|------|-----|----------|
| 2026-04-14 | ¥2,567 | 389 | 494 | 19 | 3.85% | ¥135 | 12 | 4件 | ¥642 | 3人 |
| 2026-04-15 | ¥2,613 | 366 | 489 | 20 | 4.09% | ¥131 | 15 | 2件 | ¥1,306 | 15人 |
| 2026-04-16 | ¥1,884 | 230 | 309 | 14 | 4.53% | ¥135 | 9 | 0件 | - | 確認不可 |

**3日合計**: ¥7,064 / 6 Lead / ~18 LINE登録
**観察事項**:
- CTR 3.85-4.53% は業界平均1-2%より高い（クリエイティブは効いている）
- Leadの数字とLINE登録数が乖離（4/15: Lead 2件 vs LINE 15人）→ 計測経路に問題の可能性
- 4/16はLeadゼロ→「Lead発火の設定が壊れた可能性」を要調査
- CPA基準: ¥69,200以下。現状は余裕で合格。ただし母数少ない

**リンク先**: `https://robby-the-match-api.robby-the-robot-2026.workers.dev/api/line-start?source=meta_ad&intent=direct`
（Worker経由でLINE直リンク）

## 4. Search Console — 計測不能
```
[WARN] SC API error: 403 Forbidden
User does not have sufficient permission for site 'https://quads-nurse.com/'
```
**観察事項**: ga4-credentials.json のサービスアカウント（project: odawara-nurse-jobs）が
Search Consoleのサイト権限を持っていない。日次SCレポートが全日 `[WARN]` で失敗。

**結果**: ロジック上「SEOの健康状態が全く追えていない」→ 流入パネルは補助データ（手動SCアクセス想定）で代替判断。

## 5. GA4
GA4 日次レポート（ga4_report.py）は稼働中だが、Slack送信までしか確認できない。
data/daily_snapshot.json は **存在しない**（CLAUDE.md上は存在するはずだが未生成）

**観察事項**:
- data/metrics/ 以下にファイルなし（STATE.md上で統合先とされているが機能していない）
- 実PV/日 3 は極小。有機流入はほぼなし

## 6. LP（lp/job-seeker/index.html）
- **サイズ**: 85,749バイト / **2,000行**（単一ファイル、重い）
- **内容構成**: Hero→安心バー→診断UI→Features→比較→Flow→FAQ→CTA→求人データ→逆指名
- **JSコード**: shindan.js（7問→3問未検討）
- **CTA**: LINE緑ボタン維持（社長フィードバック: コーラルオレンジ禁止）
- **Meta Pixel**: ID 2326210157891886 埋め込み済

## 7. LINE Bot / Worker
- **api/worker.js**: 7,848行（状態マシン + マッチング + AI応答）
- **状態**: 50→20状態に削減済（2026-04-03）
- **アキネーター型**: エリア→施設タイプ→働き方→転職気持ち
- **AI応答**: OpenAI GPT-4o-mini → Claude Haiku → Gemini Flash → Workers AI の4段フォールバック
- **シークレット**: 7件（LINE×3, Slack×2, OpenAI, ChatSecret）
- **LINE通知先**: #ロビー小田原人材紹介（C0AEG626EUW）
- **LIFF**: ID 2009683996-7pCYfOP7（セッション引き継ぎ機能）
- **LINE直リンク問題**: Meta広告WebView内で lin.ee が開かない→ LP経由必須に変更済

## 8. D1 データベース
- **施設DB**: **24,488件**（東京12,748 / 神奈川5,165 / 埼玉3,673 / 千葉2,902）
- **求人DB**: **2,936件**（ハローワーク看護師求人全件、毎朝06:30自動更新）
- **品質**: 診療科100% / 最寄駅99.5% / 看護師数87-90% / 病床機能71-84%
- **ソース**: 厚労省公的データ5ソース + HeartRails Express API
- **手動ローカルバックアップ**: data/nurse_robby_db.sqlite

## 9. SNS自動化
- **投稿キュー**: posting_queue.json — 48 posted / 41 ready
- **投稿方式**:
  - Instagram: ig_post_meta_suite.py（Chrome CDP経由、Meta Business Suite）
  - TikTok: Chrome CDPでTikTok Studio操作
  - 旧方式（instagrapi/tiktokautouploader）はBAN/CAPTCHAで停止
- **デザイン**: Playwright HTML/CSS → PNG（Pillow互換も残存）
- **カテゴリMIX**: あるある35% / 給与20% / 業界裏側15% / 地域15% / 転職10% / トレンド5%

## 10. cron状態（実稼働）
```
毎日4:00  pdca_seo_batch.sh
毎日6:00  pdca_ai_marketing.sh
毎日6:30  pdca_hellowork.sh
毎日7:00  pdca_healthcheck.sh
毎日8:00  meta_ads_report.py --cron
毎日8:05  ga4_report.py
毎日10:00 pdca_competitor.sh
毎日12:00 instagram_engage.py --daily
毎日12,17,18,20,21時 pdca_sns_post.sh
毎日15:00 pdca_content.sh
毎日16:00 pdca_quality_gate.sh
毎日23:00 pdca_review.sh
毎日02:00 autoresearch
毎日03:00 log_rotate.sh
日曜5:00  pdca_weekly_content.sh ⚠️ exit_code 78（Claude CLI認証エラー）
日曜6:00  pdca_weekly.sh
30分おき  watchdog.py
DISABLED: cron_ig_post.sh（21:00枠）
```

**直近cron失敗**: GA4レポートのSC部分（403）、pdca_weekly_content（exit 78）

## 11. SNSメトリクス — 公開データのみ
- **TikTok @nurse_robby**: 7投稿済み、再生/週 ~3.5K（目標1万）🟡
- **Instagram @robby.for.nurse**: 21投稿済み、エンゲージメント数値は API 未接続のため手動取得要
- **data/metrics/sns_*** ファイルなし → 定期的なメトリクス保存は機能していない

## 12. LP / SEO 構造
- area/: 32ページ
- guide/: 48ページ
- blog/: 19ページ（index含む）
- sitemap URL: 87（lastmod混在、要確認）

## 13. ペルソナ「ミサキ」v2 抜粋
（全文: /Users/robby2/.claude/projects/-Users-robby2/memory/persona_misaki_v2.md）
- 28歳女性、横浜市、正看護師6年目、急性期内科混合病棟、二交代制
- 年収430万 / 夜勤月5回 / 奨学金月2万返済中
- **核心感情**: 「辞めたいわけじゃない。でも、このままは嫌だ。」
- **最大タッチポイント**: 日勤後21:00-23:00 ソファでSNS
- **フェーズA（潜在）**: 転職自覚なし。スワイプされない刺激が要
- **フェーズB（気づき）**: 「私の給料普通？」検索。具体数字と安心感が要
- **フェーズC（比較）**: 他社と比較。差別化体現が要
- **優先順位**: C > B > A

**ミサキが求めるもの**: 相場データ / 夜勤減の影響 / 自分のペース / 電話なし / 具体数字 / モヤモヤ言語化
**ミサキが拒絶するもの**: 電話 / 押し付け / AIの一般論 / 大量情報 / 「辞めましょう」 / 「みんな悩んでます」

## 14. 制約（遵守必須）

### 9行動原則
1. 絶対に嘘をつくな（推測を事実のように言うな・架空データ禁止）
2. データドリブン最優先
3. コストを常に意識
4. ペルソナで判断
5. 調べてから動け
6. 完璧な商品水準に高めろ
7. 法律を最優先
8. 数字で判断
9. 平島禎之に聞け（迷ったら勝手に決めるな）

### 禁止事項
- React SPA禁止
- マッチングアルゴリズム新規構築禁止
- 月3万超の新規契約禁止
- 「平島禎之」「はるひメディカルサービス」HTML公開ページ露出禁止
- 架空データ・ダミーデータ禁止
- カテゴリMIX比率の勝手な変更禁止
- Meta広告予算・入札額の勝手な変更禁止（人間のみ）
- ロゴ・デザイン素材の勝手な変更禁止
- 派遣求人は除外必須
- CTAコーラルオレンジ禁止（LINE緑維持）
- Pillow→Playwright移行の試み禁止（現段階）

### 法令
遵守済。本点検の対象外。

## 15. 本点検の方向性
1. **本質的ボトルネック**: 流入（PV3/日・SC不能）+ 計測（SCブロック・GA4スナップショット生成されず）
2. **広告は回っている**: CPA¥642-1,306で合格圏。ただしLead計測の不安定性（4/16=0件）要調査
3. **LINE登録は既に発生**: STATE.mdが古い。登録者のハンドオフ後動線と成約への橋渡しが未検証
4. **資産は揃っている**: 24,488施設 + 2,936求人 + Worker 7,848行 + LP 2,000行。使いこなしに課題
5. **SNS/SEO**: キュー41件readyなのに投稿48件だけ（スロットル問題可能性）、ブログ19本でPV3/日（SEOが刺さっていない）
