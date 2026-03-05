# ナースロビー 状態ファイル
# 最終更新: 2026-03-05 23:00 by 日次レビュー

## 運用ルール
- 全PDCAサイクルはこのファイルを最初に読む（他を探し回るな）
- 作業完了後にこのファイルを更新する（次サイクルへ引き継ぎ）
- PROGRESS.mdには履歴として追記（こちらは状態のスナップショット）

## 現在のフェーズ
- マイルストーン: **Week 3**（2026-03-03〜03-09）
- North Star: 看護師1名をA病院に紹介して成約
- 状態: **コンテンツ戦略v2.0移行完了 + SNS自動投稿パイプライン稼働中 + Meta広告準備中**

## KPI
| 指標 | 目標 | 現在 | 状態 |
|------|------|------|------|
| SEO子ページ数 | 50 | 56 | ✅ |
| ブログ記事数 | 10 | **18** | ✅ |
| sitemap URL数 | - | **87** | ✅ |
| 投稿数(TikTok) | Week3:10 | **7** | 🟡 |
| 投稿数(Instagram) | Week3:3 | **2** (投稿中+1) | 🟡 |
| 投稿キュー(TikTok) | - | **57件待機** | ✅ |
| AI品質スコア | 6+ | **8.0/10** | ✅ |
| PV/日 | 100 | **0** | 🔴 |
| LINE登録数 | Month2:5 | 0 | ⏳ |
| 成約数 | Month3:1 | 0 | ⏳ |

## 完了していること
- LP-A + SEO 56ページ + ブログ18記事 + sitemap 87 URL
- Netlify独自ドメイン（quads-nurse.com）+ SSL + リダイレクト
- GA4 + Search Console + LINE公式 + Microsoft Clarity
- PDCA cron稼働（SEO/監視/競合/コンテンツ/レビュー/週次）
- Slack双方向連携（slack_bridge.py）
- 画像生成パイプライン（Cloudflare Workers AI + Pillow テキスト焼き込み）
- 医療機関DB: 97施設 / 求人DB: 看護師36件+PT9件
- AIチャットUX v2.0（Cloudflare Worker + 97施設Haversine距離計算 + 駅選択UI）
- AI自律コンテンツ生成（ai_content_engine.py + content_pipeline.py）
- **TikTok自動投稿パイプライン**: tiktok_post.py + pdca_sns_post.sh（7本投稿済み + 57本キュー待ち）
- **Instagram投稿開始**: auto_post.py v2.1 + generate_carousel.py Instagram対応済み（1本投稿済み: https://www.instagram.com/p/DVbDfg0k6vb/）
- **構築済みツール**: image_humanizer.py、instagram_engage.py、video_text_animator.py、tiktok_analytics v3.0
- **コンテンツ戦略v2.0**: robby_character.py v2.0 + ai_content_engine.py MIX改定（あるある35%/給与20%/業界裏側15%/地域15%/転職10%/トレンド5%）

## SNS状態
- **TikTok**: @robby15051 — 7本投稿済み、57本キュー待ち、自動投稿パイプライン稼働中
- **Instagram**: @robby.for.nurse — 1本投稿済み、auto_post.py v2.1対応済み
- Google認証: robby.the.robot.2026@gmail.com
- 投稿スケジュール: pdca_sns_post.sh が12:00/17:00/18:00/20:00/21:00（月-土）で実行
- instagram_engage.py: 12:00（月-土）ランダム遅延付き

## Meta広告状態
- **Facebookページ**: 既存アカウント利用（Instagram: @robby.for.nurse）
- **Meta Pixel**: ✅ ID `2326210157891886` 埋め込み済み（index.html + LP-A）
- **Pixelイベント**: ✅ PageView（自動）+ Lead（LINEクリック9箇所）+ ChatOpen（チャット開封）
- **イベントマネージャ**: ✅ PageView受信確認済み
- **campaign_guide.md**: v2.0改訂済み（神奈川県全域版、Ads Manager方式）
- **広告画像v3**: ✅ 6枚生成済み（content/meta_ads/v3/）— 神奈川県全域版
- **広告コピー**: ✅ ad_copy.md 全域版更新済み
- **次のステップ**: Ads Managerでキャンペーン作成（AD1 vs AD3のA/Bテスト、¥500/日×5日）

## cron状態（実稼働中）
```
0  4 * * 1-6  pdca_seo_batch.sh          # SEO改善
0  5 * * 0    pdca_weekly_content.sh      # 週次バッチ生成
0  6 * * 1-6  pdca_ai_marketing.sh        # AI日次PDCA
0  6 * * 0    pdca_weekly.sh              # 週次総括
0  7 * * 1-6  pdca_healthcheck.sh         # 障害監視
0 10 * * 1-6  pdca_competitor.sh          # 競合分析
0 12 * * 1-6  instagram_engage.py --daily # IG エンゲージメント（ランダム遅延付き）
0 12,17,18,20,21 * * 1-6 pdca_sns_post.sh # SNS投稿（5回/日）
0 15 * * 1-6  pdca_content.sh             # コンテンツ生成
0 23 * * 1-6  pdca_review.sh              # 日次レビュー
*/30 * * * *  watchdog.py                 # システム監視（4hデdup + daily reset）
```
※ slack_commander.py は現在crontabに未登録（Slack監視はslack_bridge.py手動実行で代替）

## 解決済みの問題
- cron "Not logged in" → ensure_env() 修正で解消
- Cloudflare token認証エラー → load_dotenv() 追加で解消
- healthcheck false CRITICAL → upload_verification方式に変更で解消
- watchdog Slackスパム → 4時間デdup + daily resetで解消
- TikTok投稿失敗（Python 3.9非互換） → Cookie認証 + venv環境で解消
- ANTHROPIC_API_KEY未設定 → Cloudflare Workers AI（Llama 3.3 70B）で代替

## デプロイ状態
- **Netlify**: ✅ 公開中（quads-nurse.com）
- **SSL**: ✅ Let's Encrypt自動発行
- **Cloudflare Worker**: ✅ デプロイ済み（AIチャット）
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

### 🔴 即座に実行
1. ~~**コンテンツ戦略v2.0移行**~~: ✅ 完了（robby_character.py v2.0 + ai_content_engine.py改定）
2. **新戦略でコンテンツ再生成**: キュー内の旧コンテンツを新ルールで差し替え
3. **Meta広告**: Facebookページ承認待ち → 承認後にPixel設定 → 広告開始
4. **Instagramオーガニック投稿増やす**: 週3本ペースへ
5. **Instagram投稿頻度を上げる**: auto_post.pyをcronに追加して自動化（現在手動実行）

### 🟢 自動化済み（人間の操作不要）
- TikTok自動投稿: pdca_sns_post.sh（12:00/17:00/18:00/20:00/21:00）
- AIコンテンツ生成: pdca_ai_marketing.sh（06:00）
- 週次バッチ: pdca_weekly_content.sh（日曜05:00）
- Instagram エンゲージメント: instagram_engage.py（12:00）
- システム監視: watchdog.py（30分間隔）
- SEO/障害/競合/コンテンツ/レビュー: 各cronジョブ稼働中

### ⏳ 後回し
- Googleビジネスプロフィール登録（手動）
- LP-B施設向け（Phase2）
- TikTokプロフィール設定（ユーザー名・画像・リンク変更）

## 戦略メモ
- 3軸: 手数料破壊(10%) x 地域密着(9市) x 転職品質
- 大手の隙間: TikTokオーガニック未参入
- 全97施設DB + Haversine距離計算 + AIチャットUX稼働
- AI自動化: ai_content_engine.py（品質スコア8.0/10）+ 日次/週次PDCA
- 投稿方式: カルーセル（+81%エンゲージメント）+ 自動投稿パイプライン

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
