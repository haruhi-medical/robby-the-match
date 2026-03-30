# Cron棚卸し — 2026-03-29

## 全エントリ一覧（時刻順）

| 時刻 | 曜日 | スクリプト | 分類 | 依存Python | 状態 |
|------|------|----------|------|-----------|------|
| 02:00 | 毎日 | claude autoresearch | Generator | ai_content_engine.py | ⚠️ 要検討 |
| 04:00 | 月-土 | pdca_seo_batch.sh | Monitor | — (claude CLI) | ✅ |
| 05:00 | 日曜 | pdca_weekly_content.sh | **Planner+Generator** | content_pipeline.py | ✅ |
| 06:00 | 月-土 | pdca_ai_marketing.sh | **Planner+Generator** | content_pipeline.py | ✅ |
| 06:00 | 日曜 | pdca_weekly.sh | **Evaluator** | tiktok_analytics.py, slack_report.py | ✅ |
| 06:30 | 毎日 | pdca_hellowork.sh | Monitor | hellowork_fetch.py, hellowork_to_jobs.py | ✅ |
| 07:00 | 月-土 | pdca_healthcheck.sh | Monitor | — (curl/bash) | ✅ |
| 07:30 | 月-土 | cron_carousel_render.sh | Generator | generate_carousel_html.py | ✅ 新規 |
| 08:00 | 毎日 | meta_ads_report.py | Monitor | meta_ads_report.py | ✅ |
| 08:05 | 毎日 | ga4_report.py | Monitor | ga4_report.py | ✅ |
| 10:00 | 月-土 | pdca_competitor.sh | Monitor | — (claude CLI) | ✅ |
| 12:00 | 月-土 | instagram_engage.py | Generator | instagram_engage.py | ✅ 15いいね/日 |
| 12,17,18,20,21 | 月-土 | pdca_sns_post.sh | Generator | auto_post.py | ✅ IG2投稿/日 + TT🔴失敗 |
| 15:00 | 月-土 | pdca_content.sh | Generator | — (claude CLI) | ⚠️ 重複疑い |
| 16:00 | 月-土 | pdca_quality_gate.sh | **Evaluator** | quality_checker.py | ✅ |
| 19:00 | 月-土 | post_preview.py | Evaluator | post_preview.py | ✅ |
| 19:30,20:00,20:30 | 月-土 | slack_reply_check.py | Monitor | slack_reply_check.py | ✅ |
| 21:00 | 月-土 | cron_ig_post.sh | Generator | ig_post_meta_suite.py | ✅ |
| 23:00 | 月-土 | pdca_review.sh | **Evaluator** | tiktok_analytics.py, claude CLI | ✅ |
| */30 | 毎日 | watchdog.py | Monitor | watchdog.py | ✅ |

## Harness分類（Planner→Generator→Evaluator）

### Planner（何を作るか決める）
- `pdca_ai_marketing.sh` (06:00) — 投稿キュー分析→生成計画
- `pdca_weekly_content.sh` (日曜05:00) — 来週分7投稿のバッチ計画

### Generator（コンテンツを生成する）
- `pdca_ai_marketing.sh` (06:00) — content_pipeline.pyで台本+画像JSON生成
- `cron_carousel_render.sh` (07:30) — JSON→Playwright→PNG画像
- `pdca_content.sh` (15:00) — claude CLIでコンテンツ生成 ← **ai_marketingと重複**
- `pdca_sns_post.sh` (12,17,18,20,21) — TikTokアップロード
- `cron_ig_post.sh` (21:00) — Instagram投稿

### Evaluator（品質を検証する）
- `pdca_quality_gate.sh` (16:00) — quality_checker.pyで品質スコア
- `post_preview.py` (19:00) — Slackにプレビュー送信
- `pdca_review.sh` (23:00) — 日次振り返り
- `pdca_weekly.sh` (日曜06:00) — 週次パフォーマンス分析

### Monitor（外部データ収集・死活監視）
- `watchdog.py` (30分毎) — プロセス死活監視
- `pdca_healthcheck.sh` (07:00) — サイト/API死活確認
- `pdca_hellowork.sh` (06:30) — ハローワーク求人取得
- `meta_ads_report.py` (08:00) — Meta広告データ
- `ga4_report.py` (08:05) — GA4/SC データ
- `pdca_competitor.sh` (10:00) — 競合監視
- `pdca_seo_batch.sh` (04:00) — SEOチェック

## 問題点

### ✅ 当初BAN判定→実際は動作中
1. **instagram_engage.py** (12:00) — Chromeセッションcookie経由で動作中（15いいね/日）

### ⚠️ 重複・統合候補
2. **pdca_content.sh** (15:00) vs **pdca_ai_marketing.sh** (06:00)
   - 両方ともclaude CLI/content_pipeline.pyでコンテンツ生成
   - ai_marketing(06:00)が主力、content(15:00)は旧式
   - **提案: pdca_content.shを削除**

3. **pdca_sns_post.sh** (5時間帯) — posting_schedule.jsonで即exitする時間帯が多い
   - 実際に投稿するのは1-2枠だけ。無駄なcron起動が多い
   - **提案: posting_schedule.jsonの実際の投稿時間だけにcronを絞る**

4. **autoresearch** (02:00) — claude CLIをcronで直接呼ぶ
   - `--dangerously-skip-permissions`使用
   - 30ターン制限あるが、コスト管理が不透明
   - **提案: 実行頻度を週2回に減らす or 成果を確認してから判断**

### ⚡ Evaluator不在の箇所

5. **cron_carousel_render.sh** (07:30) の出力に品質チェックがない
   - Playwright画像生成 → 直接posting_queue.jsonに登録
   - quality_checker.pyは16:00だが、carousel_renderの出力を見ていない
   - **Gap: 07:30のPlaywright画像に対するEvaluatorがない**

6. **pdca_hellowork.sh** (06:30) — 取得データの品質検証なし
   - 求人データ取得→即デプロイ。異常データのチェックがない
   - **Gap: 求人データ件数の急変（0件や10倍増）を検知するEvaluatorがない**

7. **Instagram投稿** (21:00) — 投稿成功/失敗のフィードバックループなし
   - cron_ig_post.sh実行後、実際に投稿されたかの確認がない
   - **Gap: 投稿後Evaluatorがない**

## 1日のタイムライン

```
02:00  autoresearch（台本品質改善ループ）
04:00  SEO監査
05:00  [日曜] 週次コンテンツバッチ生成
06:00  AI日次PDCA（Planner+Generator）
06:00  [日曜] 週次パフォーマンス分析
06:30  ハローワーク求人更新
07:00  ヘルスチェック
07:30  カルーセル画像レンダリング ← Evaluatorなし ⚡
08:00  Meta広告レポート
08:05  GA4レポート
10:00  競合監視
12:00  [削除候補] Instagram engage ← BAN済み 🔴
12-21  SNS投稿（5枠中1-2枠だけ実行）
15:00  [削除候補] コンテンツ生成 ← ai_marketingと重複 ⚠️
16:00  品質ゲート（Evaluator）
19:00  投稿プレビュー（Evaluator）
19:30-20:30  Slackリプライチェック x3
21:00  Instagram投稿 ← 投稿後Evaluatorなし ⚡
23:00  日次レビュー（Evaluator）
```
