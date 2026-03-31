# Cowork スケジュールタスク: Instagram毎日投稿

## タスク名
Instagram毎日投稿

## プロンプト（コピペ用）

以下の手順でInstagramにカルーセル投稿を実行してください。

1. ~/robby-the-match/data/posting_queue.json から status: "ready" の次のコンテンツを取得
2. そのslide_dirフォルダ内のslide_01.png〜slide_08.pngを確認
3. Chromeで https://business.facebook.com/latest/composer/ を開く（Meta Business Suiteにログイン済みであること）
4. 「Add photo」→「Upload from desktop」をクリック
5. ファイルダイアログで上記スライド画像を全て選択してアップロード
6. キャプション欄にposting_queue.jsonのcaptionとhashtagsを入力
7. 「Publish」をクリック
8. 投稿成功を確認したら、posting_queue.jsonのstatusを"posted"に、posted_atに現在時刻を記録
9. python3 ~/robby-the-match/scripts/slack_bridge.py --send "Instagram投稿完了: {content_id}" で Slack報告

## 設定
- 頻度: Weekdays（月〜土）
- 時刻: 21:00
- モデル: Sonnet
- フォルダ: ~/robby-the-match/

## 注意事項
- Meta Business Suiteにログイン済みのChromeが必要
- Computer Useで画面操作するため、Mac Miniがスリープしていないこと（keepAwakeEnabled: true で対応済み）
- 日曜は投稿しない
