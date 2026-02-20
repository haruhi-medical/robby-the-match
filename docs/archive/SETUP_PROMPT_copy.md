# Mac Mini M4 初期セットアップ — Claude Code投入プロンプト

> このプロンプトをClaude Codeに投入せよ。順番に実行される。

---

## Step 0: まずこれをコピペしてClaude Codeに投入

```
CLAUDE.mdを読め。お前はROBBY THE MATCHの経営参謀だ。

今からMac Mini M4にSNSマーケティング自動化パイプラインを構築する。
ゴールは「毎日、看護師向けTikTokスライドショーを自動生成し、
Slackに承認通知を送り、Postiz経由でTikTokに下書きアップロードする」こと。

以下の順番で進めろ。各ステップ完了後に結果を報告し、次に進め。
エラーが出たら自分で調べて解決を試みろ。3回失敗したら代替案を提示しろ。

=== Phase 1: 環境構築（今日中に完了させろ） ===

1-1. プロジェクトディレクトリを作成
  mkdir -p ~/robby-the-match/{content/{stock,base-images,generated,templates},scripts,data,docs,lp/{job-seeker,facility}}
  CLAUDE.mdをプロジェクトルートにコピー
  PROGRESS.mdをテンプレートから作成

1-2. Python環境セットアップ
  Python 3.11+が入っているか確認。なければbrew install python
  必要パッケージをインストール:
    pip install Pillow requests anthropic openai python-dotenv

1-3. 環境変数ファイル作成
  ~/robby-the-match/.env を作成（.gitignoreに追加）
  以下のキーのプレースホルダーを用意:
    ANTHROPIC_API_KEY=（Claude API）
    OPENAI_API_KEY=（gpt-image-1用）
    SLACK_WEBHOOK_URL=（Slack通知用）
    POSTIZ_API_KEY=（Postiz用）
  
  各キーが未設定なら、取得手順をステップバイステップで教えろ。

1-4. APIキー動作確認
  各APIに最小限のテストリクエストを送って疎通確認:
    - Claude API: "Hello"を送って応答確認
    - OpenAI API: gpt-image-1で100x100の最小テスト画像1枚生成
    - Slack Webhook: テストメッセージ送信
    - Postiz: integrations:list で接続確認

=== Phase 2: 画像生成パイプライン構築 ===

2-1. ベース画像生成スクリプト（scripts/generate_image.py）
  gpt-image-1を使って以下のベース画像を生成:
    - 病棟のナースステーション（テキストなし、1024×1536）
    - スマホ画面にAIチャットが表示されている場面（テキストなし、1024×1536）
    - 看護師の休憩室（テキストなし、1024×1536）
  生成した画像は content/base-images/ に保存
  ファイル名: base_nurse_station.png, base_ai_chat.png, base_breakroom.png

2-2. テキスト焼き込みスクリプト（scripts/overlay_text.py）
  Pillowで日本語テキストをベース画像に焼き込む:
    - フォント: Mac標準のヒラギノ角ゴシック W6（なければNotoSansJP）
    - フォントサイズ: 画像幅の1/8以上（最低128px）
    - 位置: 中央〜やや下（上部150pxはTikTok UIで隠れるので避ける）
    - 背景: 半透明黒帯（RGBA 0,0,0,160）
    - 文字色: 白
  テスト: ベース画像1枚に「師長にAIで見せたら黙った」を焼き込んで確認

2-3. 6枚スライド一括生成スクリプト（scripts/generate_slides.py）
  入力: コンテンツID、6枚分のテキストリスト、ベース画像パス
  出力: content/generated/{日付}_{ID}/ に slide_1.png 〜 slide_6.png
  処理:
    1. ベース画像を読み込む（毎回新規生成しない。使い回し）
    2. 各スライドにテキストを焼き込む
    3. 1枚目: フックテキスト（20文字以内、大きめフォント）
    4. 2-5枚目: ストーリー展開（各30文字以内）
    5. 6枚目: オチ + ソフトCTA（「保存してね」等）

=== Phase 3: コンテンツ生成パイプライン ===

3-1. 台本生成スクリプト（scripts/generate_content.py）
  Claude APIを使って台本を生成:
    入力: カテゴリ（あるある/転職/給与）、コンテンツストックのID（任意）
    出力: JSON形式で以下を返す
      {
        "id": "A01",
        "hook": "師長にAIで見せたら黙った",
        "slides": ["1枚目テキスト", "2枚目", ..., "6枚目"],
        "caption": "キャプション200文字以内",
        "hashtags": ["#看護師", "#転職", "#AI", "#看護師あるある", "#神奈川"],
        "category": "あるある",
        "base_image": "base_nurse_station.png"
      }
  
  Claude APIへのシステムプロンプトには以下を含めろ:
    - ペルソナ「ミサキ（28歳、経験5-8年、神奈川県西部）」
    - フックの公式「[他者]+[対立]→AIで見せた→[相手の反応]」
    - 1枚目は20文字以内
    - 各スライド30文字以内
    - 架空設定のみ（実在人物・施設なし）
    - CTA 8:2ルール（8割ソフトCTA）

3-2. Slack通知スクリプト（scripts/notify_slack.py）
  Slack Webhookで承認依頼を送信:
    - コンテンツID
    - キャプション全文
    - ハッシュタグ
    - 6枚のスライド画像（Slackにアップロード or プレビューリンク）
    - 「承認」ボタン（Slack Block Kitのボタン。押したら次のステップへ）

  ※ Slackボタン連携が複雑すぎるなら、最初はメッセージ送信のみでOK。
    YOSHIYUKIがSlackで「OK」と返信したら次へ進む形でもいい。

3-3. Postiz投稿スクリプト（scripts/post_to_tiktok.py）
  Postiz Agent CLIを使ってTikTokに下書きアップロード:
    1. 6枚の画像をPostizにアップロード（postiz upload）
    2. スライドショーとして投稿作成（postiz posts:create）
    3. スケジュール時間を設定（17:30 JST）
    4. 結果をSlackに通知

  ※ PostizのTikTokスライドショー対応がバグで動かない場合:
    代替案A: 画像をSlackに直接送信。YOSHIYUKIが手動アップロード。
    代替案B: Instagram Reelsに先に注力（Postizの対応がより安定）

=== Phase 4: 日次自動実行 ===

4-1. メインパイプラインスクリプト（scripts/daily_pipeline.py）
  上記の全スクリプトを1つにまとめる:
    1. コンテンツMIX比率に従ってカテゴリ選択
    2. 台本生成（generate_content.py）
    3. スライド生成（generate_slides.py）
    4. Slack通知（notify_slack.py）
    5. 承認待ち
    6. Postiz投稿（post_to_tiktok.py）
    7. PROGRESS.mdに記録

4-2. cronまたはlaunchdで毎日16:00 JSTに自動実行
  （17:30投稿に間に合うよう、1.5時間前に生成開始）
  Mac Miniなので24時間稼働前提。スリープ設定をオフにしろ。

=== 完了条件 ===

以下がすべて動いたら Phase 1-4 完了:
  □ gpt-image-1でベース画像3枚が生成されている
  □ テキスト焼き込みが日本語で正しく読める
  □ Claude APIで台本が生成される
  □ 6枚スライドが自動生成される
  □ Slackにプレビュー付き通知が届く
  □ Postiz経由でTikTokに下書きが入る（or 代替案が動く）
  □ cronで毎日自動実行される
  □ PROGRESS.mdに記録される

各ステップ完了したらPROGRESS.mdに記録しろ。
エラーが出たらCLAUDE.mdの失敗ログに追記しろ。
コスト計算を忘れるな。

まずPhase 1-1から始めろ。
```
