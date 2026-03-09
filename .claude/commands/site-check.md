# /site-check — サイト全体ヘルスチェック

quads-nurse.com の健全性を4エージェント並列でチェックする。

## チェック項目（4エージェント並列）

### Agent 1: フロントエンド品質
- トップページ（index.html）のHTML構文チェック
- LP-A（lp/job-seeker/index.html）の表示確認
- チャットウィジェット（chat.js）の動作確認
- モバイル表示の問題がないか
- Meta Pixel（ID: 2326210157891886）が正しく埋め込まれているか
- LINEリンク（lin.ee/oUgDB3x）が全箇所で正しいか

### Agent 2: SEO/メタデータ
- sitemap.xml のURL数と整合性
- 全ページのtitle/description/og:タグ
- 構造化データ（JSON-LD）の検証
- robots.txt の確認
- 「平島禎之」「はるひメディカルサービス」がメタデータに露出していないか

### Agent 3: コンテンツ整合性
- config.js の施設数とLP表示の一致
- chat.js のareaCities設定が全施設をカバーしているか
- 地域ページ（area/）とガイドページ（guide/）のリンク切れ
- ブログ記事のインデックス整合性

### Agent 4: インフラ/パフォーマンス
- Netlify/GitHub Pagesのデプロイ状態
- Cloudflare Workerの稼働状態
- SSL証明書の有効性
- cron ジョブの稼働状態（`crontab -l`）
- 直近のエラーログ確認

## 出力
- 問題点リスト（重要度順）
- 即座に修正すべき項目
- 修正が必要な場合は自動修正を提案
