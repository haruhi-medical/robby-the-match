# Claude Desktop Scheduled Tasks 設定

## Claude Desktop Coworkに以下をコピペして送信する

### タスク1: Instagram毎日投稿

```
毎日17:30にInstagramカルーセル投稿を自動実行して。
手順:
1. ~/robby-the-match/data/posting_queue.json から次のreadyコンテンツを選ぶ
2. スライド画像8枚を取得
3. Chromeで Meta Business Suite を開いてカルーセル投稿
4. キャプション+ハッシュタグを入力して公開
5. posting_queue.json のステータスを posted に更新
6. Slack #ロビー小田原人材紹介 に投稿完了を報告
日曜は休み。
```

### タスク2: TikTok毎日投稿（準備できたら）

```
毎日18:30にTikTok動画投稿を自動実行して。
手順:
1. ~/robby-the-match/data/posting_queue.json から次のreadyコンテンツを選ぶ
2. scripts/tiktok_post.py で動画を生成（content/temp_videos/に保存）
3. Chromeで TikTok Studio (https://www.tiktok.com/tiktokstudio/upload) を開く
4. 動画をアップロード
5. キャプション+ハッシュタグを入力
6. 公開設定を「誰でも」にして投稿
7. Slack #ロビー小田原人材紹介 に投稿完了を報告
日曜は休み。
```

### タスク3: 日次メトリクス取得

```
毎朝9:00に全プラットフォームのメトリクスを取得して。
手順:
1. python3 ~/robby-the-match/scripts/computer_use/daily_loop.py phase1 でAPI取得を試す
2. 失敗したプラットフォームはChromeで画面から読み取る
   - TikTok: https://www.tiktok.com/tiktokstudio/analytics
   - Instagram: Meta Business Suite → Insights
   - GA4: https://analytics.google.com/
3. 結果を ~/robby-the-match/data/metrics/ に保存
4. Slack #ロビー小田原人材紹介 に日次レポートを投稿
```
