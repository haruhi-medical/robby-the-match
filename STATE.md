# ROBBY THE MATCH 状態ファイル
# 最終更新: 2026-02-21 15:00 by Agent Team構築

## 運用ルール
- 全PDCAサイクルはこのファイルを最初に読む（他を探し回るな）
- 作業完了後にこのファイルを更新する（次サイクルへ引き継ぎ）
- PROGRESS.mdには履歴として追記（こちらは状態のスナップショット）

## 現在のフェーズ
- マイルストーン: Week 1（2026-02-19〜03-01）
- North Star: 看護師1名をA病院に紹介して成約
- 状態: **基盤完了 → マーケティング出力開始フェーズ**

## 戦略診断（2026-02-21実施）

### 完了していること ✅
- LP-A + SEO 50ページ + ブログ10記事 + sitemap
- GitHub Pages公開・GA4・Search Console・LINE公式
- PDCA cron 7ジョブ稼働
- Slack双方向連携（送受信・レポート5種・5分監視）
- コンテンツ素材14本分生成済み（A01スライド6枚 + weekly 7本 + week2 7本）
- 画像生成パイプライン（Cloudflare Workers AI + Pillow テキスト焼き込み）
- LP-A品質強化（ソーシャルプルーフ・比較表強化・モバイルCTA・LocalBusiness構造化データ）
- 医療機関DB: 97施設（51病院 + 25訪問看護 + 10クリニック + 10介護施設）
- 求人DB: 看護師36件 + PT9件（訪問看護・クリニック・介護重点追加）
- Agent Team基盤: agent_state.json + 障害自動復旧 + ロール定義7エージェント
- TikTok/Instagram作成指示をSlack送信済み（平島禎之の手動作業待ち）

### 2/21に修正した致命的問題 🔧
1. ~~timeout未対応でcronのClaude実行が全失敗~~ → macOS互換fallback実装
2. ~~cron環境でgit push認証失敗~~ → GH_TOKEN credential helper方式に修正
3. ~~slack_report.pyが50ページ超でBlock Kit制限エラー~~ → サマリ表示に修正
4. ~~Slack双方向連携が機能していない~~ → slack_bridge.py新規作成

### ミッション達成への最大ボトルネック 🔴
**看護師の目に何も届いていない。SNS投稿ゼロ、PVゼロ。**

## KPI
| 指標 | 目標 | 現在 | 状態 |
|------|------|------|------|
| SEO子ページ数 | 50 | 50 | ✅ |
| ブログ記事数 | 10 | 10 | ✅ |
| sitemap URL数 | - | 65 | ✅ |
| 投稿数(TikTok) | Week2:5 | **0** | 🔴 |
| 投稿数(Instagram) | Week2:3 | **0** | 🔴 |
| PV/日 | 100 | **0** | 🔴 |
| LINE登録数 | Month2:5 | 0 | ⏳ |
| 成約数 | Month3:1 | 0 | ⏳ |

## 次にやるべきこと（優先順 — 変更厳禁）

### 🔴 平島禎之の手動作業（AIではできない）— Slack指示送信済み
1. **TikTokアカウント作成** → Slack手順送信済み。アカウント名を報告後、即投稿可能。
2. **Instagramアカウント作成** → Slack手順送信済み。TikTokと並行。
3. **生成済みコンテンツの初回投稿**（A01スライド6枚 + 全14セット84枚が画像生成済み）
4. Mac Miniスリープ無効化（sudo pmset -a sleep 0）

### 🟡 AIが自律でやること
5. PDCA cronの実稼働確認（修正済み、次回04:00のseo_batchで検証）
6. 生成済み週次バッチのスライド画像化（JSONはあるが画像未生成のもの）
7. Search Consoleでsitemap再送信の自動化
8. LP-AのCTAボタン・導線の改善（LINE登録率最適化）
9. コンテンツ品質の自動チェック（ペルソナ適合度スコアリング）

### ⏳ 後回し
- Googleビジネスプロフィール登録（手動）
- 独自ドメイン取得（SEO効果が出てから）
- LP-B施設向け（Phase2）

## デプロイ状態
- GitHub Pages: ✅ 公開中
- 公開URL: https://haruhi-medical.github.io/robby-the-match/
- git remote: origin https://github.com/haruhi-medical/robby-the-match.git
- デプロイブランチ: master（mainからpush）
- 最新push: 2026-02-21 15:00

## SEO状態
- 子ページ: area/9 + guide/41 = 計50ページ
- ブログ: 10記事 + index
- sitemap.xml: 65 URL
- GA4: ✅ G-X4G2BYW13B
- Search Console: ✅ 登録済み
- 構造化データ: index.html(5種) + LP-A(4種) + area(2種) + guide(2種)
- 競合ゼロKW: 「神奈川県西部 看護師」「紹介料 10%」
- **課題**: github.ioサブドメインはドメイン権威ゼロ。独自ドメインがないとランキングは厳しい。

## SNS状態
- TikTok: ❌ アカウント未作成（手動必要）
- Instagram: ❌ アカウント未作成（手動必要）
- 生成済み素材:
  - content/generated/20260220_A01/ — スライド6枚（投稿可能）
  - content/generated/weekly_batch_20260220/ — 7本分JSON（画像生成必要）
  - content/generated/week2_batch_20260227/ — 7本分JSON（画像生成必要）

## Slack状態
- ✅ 双方向連携稼働中（2026-02-21構築完了）
- slack_bridge.py: セッション開始/終了/送受信
- slack_commander.py: cron 5分間隔監視
- slack_report.py: daily/kpi/content/seo/team

## cron状態（2026-02-21修正済み）
```
0  4 * * 1-6 pdca_seo_batch.sh      # SEO改善
0  7 * * 1-6 pdca_healthcheck.sh    # 障害監視
0 10 * * 1-6 pdca_competitor.sh     # 競合分析
0 15 * * 1-6 pdca_content.sh        # コンテンツ生成
0 23 * * 1-6 pdca_review.sh         # 日次レビュー
0  6 * * 0   pdca_weekly.sh         # 週次総括
*/5 * * * *  slack_commander.py      # Slack監視
```
- **修正履歴**: timeout未対応→fallback実装、git push認証→GH_TOKEN方式

## 問題・ブロッカー
- **TikTok/Instagramアカウント未作成**: 全てのマーケティング出力がブロック
- **github.ioサブドメイン**: SEO効果限定的。独自ドメインが必要
- **Postiz API Key未設定**: 自動投稿不可。当面手動アップロード

## 戦略メモ
- 競合ゼロKW: 「神奈川県西部 看護師」「紹介料 10%」
- 3軸: 手数料破壊(10%) x 地域密着(9市) x 転職品質
- 大手の隙間: TikTokオーガニック未参入
- **最優先**: SNSアカウント作成 → 素材投稿 → データ取得 → 改善ループ開始
