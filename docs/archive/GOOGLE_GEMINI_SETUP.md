# Google Gemini API セットアップガイド

## Step 1: APIキー取得

1. **Google AI Studio にアクセス**
   - URL: https://aistudio.google.com/
   - Googleアカウントでログイン

2. **APIキーを作成**
   - 左サイドバーから「Get API key」をクリック
   - 「Create API key」ボタンをクリック
   - プロジェクトを選択（新規作成も可能）
   - APIキーが表示される → **コピーして保存**

   ⚠️ APIキーは一度しか表示されないので必ずコピーしてください

3. **課金設定（必要な場合）**
   - 無料枠: テキスト生成は無料枠大きい
   - 画像生成（Imagen）: 課金が必要な可能性あり
   - Google Cloud Console で課金アカウントをリンク

---

## Step 2: 画像生成モデルの選択

### Option A: Imagen 3（Google AI Studio経由）
- 最新の画像生成モデル
- 2026年2月時点で利用可能

### Option B: Vertex AI Imagen
- Google Cloud Platform経由
- より詳細な設定が可能

---

## 取得したAPIキーを私に伝えてください

形式: `AIza...` で始まる文字列

セキュリティ上、APIキーは環境変数に保存します。
チャット履歴には残りますが、外部には公開されません。

---

**APIキーを取得したら、このチャットに貼り付けてください！**
