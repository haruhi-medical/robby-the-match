# ROBBY THE MATCH - 環境状況レポート
生成日時: 2026-02-17

---

## 🖥️ システム環境

| 項目 | 詳細 |
|------|------|
| **Mac** | Mac mini M4 (16GB RAM) |
| **OS** | macOS 15.6 |
| **コンピュータ名** | ROBBYのMac mini |
| **Python** | 3.9.6 |
| **Node.js** | v25.5.0 |
| **npm** | 11.8.0 |
| **Homebrew** | インストール済み |

---

## 📂 既存プロジェクト構造

### メインプロジェクト: `/Users/robby2/Desktop/claude/`

```
claude/
├── MANUAL.md                    # ✅ 完全運用マニュアル v2.0（存在確認）
├── config/
│   ├── agent_config.json        # ✅ エージェント設定
│   └── content_strategy.json    # ✅ コンテンツ戦略設定
├── content/
│   ├── drafts/                  # 下書きフォルダ（空）
│   ├── approved/                # 承認済みフォルダ（空）
│   ├── published/               # 公開済みフォルダ（空）
│   └── templates/               # テンプレートフォルダ（空）
├── images/
│   ├── generated/               # 生成画像フォルダ（空）
│   └── base_prompts/            # ベースプロンプトフォルダ（空）
├── scripts/                     # ⚠️ 空（これから作成）
├── workflows/                   # ⚠️ 空（これから作成）
├── logs/                        # ログフォルダ
└── data/                        # データフォルダ
```

### 新規作成フォルダ: `/Users/robby2/robby_content/`

```
robby_content/
└── post_001/
    ├── slide_prompts.json       # ✅ 今日作成（投稿#1の画像プロンプト）
    └── caption.txt              # ✅ 今日作成（投稿#1のキャプション）
```

---

## 🔌 統合設定の状況（agent_config.json より）

| サービス | 状態 | APIキー環境変数 | 備考 |
|---------|------|----------------|------|
| **Claude API** | ✅ enabled | ANTHROPIC_API_KEY | 台本・キャプション生成用 |
| **OpenAI API** | ✅ enabled | OPENAI_API_KEY | 画像生成用（gpt-image-1） |
| **Postiz** | ❌ disabled | POSTIZ_API_KEY | SNS投稿スケジューリング |
| **Slack** | ❌ disabled | SLACK_WEBHOOK_URL | 承認通知用 |

---

## 🔑 APIキー設定状況

| 環境変数 | 設定状況 | 確認方法 |
|---------|---------|---------|
| `OPENAI_API_KEY` | ❌ 未設定 | env確認済み |
| `ANTHROPIC_API_KEY` | 不明 | （Claude Code内部で使用中の可能性） |
| `POSTIZ_API_KEY` | ❌ 未設定 | - |
| `SLACK_WEBHOOK_URL` | ❌ 未設定 | - |
| `GOOGLE_APPLICATION_CREDENTIALS` | ❌ 未設定 | - |

---

## 🐍 Python環境（Google API対応）

**✅ Google関連パッケージがインストール済み！**

| パッケージ | バージョン | 用途 |
|-----------|----------|------|
| google-auth | 2.48.0 | Google認証 |
| google-auth-oauthlib | 1.2.4 | OAuth認証 |
| gspread | 6.2.1 | Google Sheets連携 |

→ **Google APIへの接続準備は整っている**

---

## 📱 インストール済みアプリ

- ✅ Google Chrome
- ✅ Claude Code (brew)
- ✅ Visual Studio Code (brew)

---

## 🎯 画像生成の選択肢（Option B）

### Option B-1: **Google Gemini API（推奨）**
- **メリット**: Googleアカウント所有済み。Imagen 3対応。無料枠あり。
- **デメリット**: APIキー取得＋課金設定が必要
- **手順**:
  1. [Google AI Studio](https://aistudio.google.com/) でAPIキー取得
  2. `export GOOGLE_API_KEY="..."` で環境変数設定
  3. Python経由で画像生成

### Option B-2: **Stability AI（Stable Diffusion）**
- **メリット**: 高品質。商用利用可能。
- **デメリット**: APIキー取得＋課金必要
- **手順**: [DreamStudio](https://beta.dreamstudio.ai/) でAPIキー取得

### Option B-3: **Cloudflare Workers AI（無料枠大きい）**
- **メリット**: 無料枠が大きい（1日10,000リクエスト）
- **デメリット**: Cloudflareアカウント必要
- **手順**: Cloudflareアカウント作成 → Workers AI有効化

### Option B-4: **ローカル生成（Stable Diffusion）**
- **メリット**: 完全無料。APIコストゼロ。
- **デメリット**: M4 Macでも生成に時間がかかる（1枚30秒〜2分）
- **手順**: Stable Diffusion WebUIをインストール

---

## ✅ 今日の進捗

1. ✅ トピック選定完了（投稿#1: 「年収交渉」）
2. ✅ 台本生成完了（6枚構成）
3. ✅ 画像プロンプト作成完了（詳細JSON保存済み）
4. ✅ キャプション生成完了（180文字、ハッシュタグ5個）
5. ⏸️ 画像生成（APIキー設定待ち）
6. ⏸️ Postiz連携（API設定待ち）

---

## 🚀 次のアクション提案

### 最優先（画像生成環境の確立）

1. **Google Gemini APIキー取得**（推奨）
   - 理由: Googleアカウント所有済み。無料枠あり。
   - 時間: 5分

2. **または OpenAI APIキー設定**
   - 理由: 既に設定ファイルに組み込み済み
   - 時間: 3分

### 次点（SNS連携）

3. **Postiz アカウント作成＋APIキー取得**
   - 理由: TikTok/Instagram下書き自動アップロードに必要
   - 時間: 10分

### オプション（通知）

4. **Slack Webhook設定**（任意）
   - 理由: 承認依頼通知の自動化
   - 時間: 5分

---

## 💡 推奨フロー

```
今すぐ → Google Gemini APIキー取得
     ↓
     画像6枚生成（投稿#1完成）
     ↓
     人間承認（YOSHIYUKIさん）
     ↓
     TikTok/Instagram手動投稿（初回）
     ↓
     データ収集・効果測定
     ↓
     Postiz連携（自動化）
```

初回は手動投稿でOK。効果が確認できてから自動化に移行する方が安全。

---

## 🔧 即実行可能なコマンド例

### Google Gemini APIキー設定（取得後）
```bash
echo 'export GOOGLE_API_KEY="your-api-key-here"' >> ~/.zshrc
source ~/.zshrc
```

### OpenAI APIキー設定（取得後）
```bash
echo 'export OPENAI_API_KEY="sk-..."' >> ~/.zshrc
source ~/.zshrc
```

### 画像生成スクリプト作成（次ステップ）
```bash
# Python + Google Gemini で画像生成
# または
# curl + OpenAI API で画像生成
```

---

**次にどれを進めますか？**
