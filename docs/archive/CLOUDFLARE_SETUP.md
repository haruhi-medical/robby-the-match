# Cloudflare Workers AI セットアップガイド

## Step 1: Cloudflareアカウント作成

1. **Cloudflareにアクセス**
   - URL: https://dash.cloudflare.com/sign-up
   - メールアドレスとパスワードで登録
   - メール認証を完了

2. **ダッシュボードにログイン**
   - https://dash.cloudflare.com/

---

## Step 2: Workers AIを有効化

1. **左サイドバーから「Workers & Pages」を選択**

2. **「Overview」タブで「Workers AI」セクションを探す**
   - または直接アクセス: https://dash.cloudflare.com/?to=/:account/ai/workers-ai

3. **「Enable Workers AI」ボタンをクリック**
   - 無料プランで開始できます
   - クレジットカード不要（無料枠内なら）

---

## Step 3: APIトークン取得

1. **右上のプロフィールアイコン → 「My Profile」**

2. **左サイドバーから「API Tokens」を選択**

3. **「Create Token」ボタンをクリック**

4. **トークンテンプレート選択**
   - 「Edit Cloudflare Workers」テンプレートを使用
   - または「Create Custom Token」で以下の権限を設定：
     - Account: Workers R2 Storage:Edit
     - Account: Workers Scripts:Edit
     - Zone: Workers Routes:Edit

5. **トークンが表示される → コピーして保存**
   ⚠️ 一度しか表示されないので必ずコピー

6. **Account IDも取得**
   - ダッシュボードの右サイドバーに表示されている
   - 形式: `1234567890abcdef1234567890abcdef`

---

## 必要な情報（コピーしてください）

取得したら以下の形式で教えてください：

```
CLOUDFLARE_API_TOKEN: (トークン)
CLOUDFLARE_ACCOUNT_ID: (アカウントID)
```

---

## 利用可能な画像生成モデル

Cloudflare Workers AIで使えるモデル：

| モデル | 品質 | 速度 | 推奨度 |
|--------|------|------|--------|
| **@cf/black-forest-labs/flux-1-schnell** | ⭐⭐⭐⭐⭐ | 高速 | ✅ 推奨 |
| @cf/stabilityai/stable-diffusion-xl-base-1.0 | ⭐⭐⭐⭐ | 中速 | ⭕ |
| @cf/lykon/dreamshaper-8-lcm | ⭐⭐⭐ | 超高速 | ⭕ |

**FLUX.1-schnell** を使用します（最新・最高品質）

---

## 無料枠の詳細

- **1日10,000リクエスト無料**
- 月300,000リクエスト = 完全無料
- ROBBYプロジェクトは月240枚 = 0.08%使用 → **余裕**

---

**APIトークンとAccount IDを取得したら、このチャットに貼り付けてください！**
