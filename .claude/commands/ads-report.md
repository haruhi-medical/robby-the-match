# /ads-report — Meta広告パフォーマンスレポート

Meta Marketing APIから広告データを取得して表示する。

## 引数
- 指定なし: 直近7日のサマリ
- `daily`: 日別ブレイクダウン
- `3days`: 直近3日
- `slack`: Slackにレポート送信
- `campaigns`: キャンペーン一覧

## 手順

1. `python3 scripts/meta_ads_report.py` を実行（引数に応じてオプション変更）
2. 結果を分析:
   - CTR 1%以上 → 良好
   - CTR 0.5-1.0% → 要改善（クリエイティブ見直し）
   - CTR 0.5%未満 → 要対策（ターゲティングとクリエイティブ両方見直し）
3. AD1 vs AD3のA/Bテスト結果を比較
4. 改善提案を出す

## 未設定の場合
META_ACCESS_TOKEN等が.envに未設定なら、セットアップ手順を案内する:
1. https://developers.facebook.com/ でアプリ作成
2. Graph API Explorerでads_readトークン生成
3. `python3 scripts/meta_ads_report.py --accounts` でアカウントID確認
4. .envにMETA_ACCESS_TOKEN, META_AD_ACCOUNT_ID, META_APP_ID, META_APP_SECRETを設定
5. `python3 scripts/meta_ads_report.py --setup` でLong-livedトークンに交換
