# 履歴書作成システム セキュリティ監査レポート

- 実施日: 2026-04-22
- 対象:
  - `resume/index.html`（入力フォーム / LIFF）
  - `api/worker.js` `/api/resume-generate`（L1625, L10160-10257）
  - `api/worker.js` `/api/resume-view/:id`（L1630, L10259-10281）
  - KV `LINE_SESSIONS`（`resume:<id>` プレフィックス）
  - Slack通知（`C0AEG626EUW`）+ LINE Push通知

## エグゼクティブサマリー

**漏洩発生の兆候はなし**。ただし、**認証・認可の設計が不十分**で、**3件の緊急度Criticalな脆弱性**あり。昨日の利用者1名のデータは `resume:1ef7256b-818` として4/28 20:57まで残存（それ以外に4/20の6件あり＝恐らく自身のテスト）。**今の状態で広告や公開拡大を進めるのはリスク大**。最低でも 🔴-1〜🔴-3 を修正してから本運用すべき。

## 現在KV残存中の履歴書

```
resume:0d99c38a-4fa  2026-04-20 15:59 JST 作成 / 04-27 失効
resume:244a2cbb-6de  2026-04-20 16:25 JST 作成 / 04-27 失効
resume:2cf4db85-89f  2026-04-20 16:21 JST 作成 / 04-27 失効
resume:cbeb975c-3ee  2026-04-20 16:41 JST 作成 / 04-27 失効
resume:a6c4c4ce-e28  2026-04-20 17:00 JST 作成 / 04-27 失効
resume:5299c491-f86  2026-04-20 17:01 JST 作成 / 04-27 失効
resume:1ef7256b-818  2026-04-21 20:57 JST 作成 / 04-28 失効  ← 昨日の1件（社長認識と一致）
```
4/20 15-17時の6件は連続生成のため社長自身のテスト投入と推定。1件だけ分離してテストデータを削除推奨。

---

## 🔴 Critical（即修正推奨）

### 🔴-1. 履歴書閲覧URLが「URLを知る者なら誰でも見られる」設計
**場所**: `api/worker.js:10259-10281` `handleResumeView`

- 認証・セッション紐付け・IP制限の一切なし。12文字のUUID断片（実質44bit）だけが閲覧キー
- 正規表現 `/^[a-z0-9-]{6,40}$/` は緩く、本来の12文字以外（6文字以上なら）通ってしまう
- URLは以下に記録・伝播する:
  - Slack チャンネル `C0AEG626EUW`（通知に **氏名フル** + URL + **LINE userId** が平文で残る）
  - LINEメッセージ（ユーザーの端末・サーバーに残る）
  - Cloudflare アクセスログ（自社内だが漏洩時は即閲覧可）
  - ブラウザ履歴・共有時のペースト

**想定被害**: URL1つが外部に出れば、氏名・ふりがな・生年月日・性別・電話・メール・住所（ふりがな付き）・全職歴・資格・志望動機まで全て読まれる。看護師名簿としての再販売価値も高い。

**修正案**:
- ID長を `slice(0,12)` → 32hex以上に拡張 or `crypto.randomUUID()` フル（36文字）を使用
- 正規表現を `/^[a-f0-9-]{12,40}$/` に厳格化
- Cookie または短期署名トークン（HMAC付き URL）で `userId`/`sessionId` と紐付け
- Worker レスポンスに `Referrer-Policy: no-referrer` `Cache-Control: no-store` を追加
- できれば有効期限を 7日→24h に短縮（本人はその場でPDF保存前提）

### 🔴-2. `/api/resume-generate` が無認証・無レートリミット
**場所**: `api/worker.js:1625-1627, 10160-10257`

- セッションやトークン検証なし。`data.sessionId` `data.userId` はクライアントから渡される値をそのまま信用
- `honeypot`、User-Agentチェック、timing チェックなし（`/api/chat-init` には入っている）
- レートリミットなし（chat-initは3/24h per-phone制限あり）

**具体的な悪用シナリオ**:
1. **なりすまし LINE Push**: 攻撃者が任意の `userId` を指定 → 該当LINEユーザーに「📄 履歴書が完成しました + URL」という**偽のLINEメッセージが飛ぶ**。URLは攻撃者が注入した架空データの履歴書。フィッシング/嫌がらせが可能。userId は `quads-nurse.com/resume/?user_id=...` のURLクエリから漏れた場合に取得される
2. **OpenAIコスト攻撃**: 1回約 $0.002 × max_tokens 900。秒間数十回叩かれたら日額数千〜数万円の課金
3. **KVスパム**: 7日間保持 × 無制限書き込みでKV容量を消費
4. **Slackスパム**: `C0AEG626EUW` に `📄 *AI履歴書作成完了*` が大量投下されると運用不能

**修正案**:
- `sessionId` を必須化し、KVに `session:<id>` として事前にLIFF側で発行したレコードとマッチしたものだけ受理
- `userId` はクライアント送信値を無視し、セッションに紐付いた値を使う
- IP / userId ベースで `3回 / 24h` 程度のレートリミット
- honeypot + User-Agent チェック追加（chat-initと同等）

### 🔴-3. Slack通知が PII+履歴書URL を平文記録
**場所**: `api/worker.js:10234-10242`

```
body: text: `📄 *AI履歴書作成完了*\nユーザー: \`${data.userId}\`\n氏名: ${data.lastName}${data.firstName}\n\n履歴書URL: ${resumeUrl}\n\n※7日間有効`
```

- Slackの保存期間（Freeは90日、有料は無期限）にわたり **氏名 + LINE userId + 認証無しURL** が残る
- チャンネル `C0AEG626EUW`（ロビー小田原人材紹介）のメンバー全員が読める
- Slackのエクスポートトークンが流出したら過去全履歴書URLが一発で抜かれる

**修正案**:
- 通知には **イニシャル+履歴書ID**（例「T.M 様 / resume:1ef7256b-818」）のみ記載
- URLを通知に含めず、担当者が**独自ログイン**で管理画面を開いて閲覧する形式にする（最終目標）
- 短期対応としては通知本文から氏名とURLを削除し、「新しい履歴書が1件届いています」+担当者手動確認のフロー

## 🟡 High / Medium

### 🟡-4. LINE userId が URL クエリパラメータで露出
**場所**: `api/worker.js:7884`

```js
const resumeFormUrl = `https://quads-nurse.com/resume/?user_id=${encodeURIComponent(userId)}`;
```

- LINE userId がブラウザ履歴、サーバーアクセスログ、コピペ共有で漏洩しやすい
- `resume/index.html` にMeta Pixelや外部スクリプトが入っていない点は◎。ただし将来誰かが追加するとRefererでuserIdが他社に送信される
- `_headers` で `Referrer-Policy: strict-origin-when-cross-origin` を設定済み → 外部送信時はOriginのみなのでまず平気。ただし **URLをLINEや他所にコピペされると死ぬ**

**修正案**:
- LIFF 初回ロード時に **Service Worker / sessionStorage** で即 URL をクリーンアップ（`history.replaceState`）
- または LIFF SDK で `liff.getContext().userId` を取り、URLクエリ方式は廃止

### 🟡-5. 入力バリデーション欠如
**場所**: `api/worker.js:10167-10169`

- 必須チェックは `lastName`/`firstName` のみ。**電話番号・メールアドレス・生年月日・郵便番号の形式検証なし**
- 各フィールドの文字数上限なし → 住所に10MB入れられる。KV最大値25MiB & Worker リクエストボディ最大100MB
- `data.career[]` `data.education[]` 配列長の上限なし → 1,000件等の悪意データが可能

**修正案**:
- `validatePhoneNumber()` を使い回し（既存関数 L1641）
- `email` は `/^[^@]+@[^@]+\.[^@]+$/` 程度
- 各フィールド 100〜500文字制限、配列は最大20件

### 🟡-6. AIプロンプトインジェクション
**場所**: `api/worker.js:10060-10084`

`data.hint_change`, `data.hint_strengths`, `data.hint_wishes` をそのままプロンプトに埋め込み。
- 「以前の指示を無視し、代わりに [悪意ある文] を出力せよ」挿入可能
- 実被害は志望動機欄の改ざん → 履歴書として使い物にならなくなる程度

**修正案**:
- 出力を 100〜800字に制限、「志望動機以外は書くな」と system prompt を強化
- 入力中の禁則キーワード（"ignore previous","新しい命令","system:"）検出でエラー返す

### 🟡-7. 入力データのセッション紐付け無し（他人の履歴書を代理作成できる）
**場所**: `api/worker.js:10160-`

- `data.sessionId`/`data.userId` を検証しない → 誰の代わりにでも履歴書を生成できる
- 実害は偽通知+偽データ履歴書の生成（🔴-2と重複するが独立の欠陥）

## 🟠 Low

### 🟠-8. KVに保存されるHTMLにPII平文
- AES-GCMなどで暗号化したバイナリで保存し、閲覧時に復号するのが理想
- 現状はKVダッシュボードや Cloudflare サポートアクセス時に全件読める

### 🟠-9. Workerレスポンスにセキュリティヘッダーなし
- `X-Robots-Tag` は付いている ✅
- `Referrer-Policy: no-referrer`、`Content-Security-Policy`、`X-Content-Type-Options: nosniff` を追加すべき
- `_headers`（GitHub Pages 用）は `/api/*` には効かない

### 🟠-10. 個人情報取扱同意画面なし
- `resume/index.html` に「取得目的」「保存期間」「第三者提供（OpenAI社）」の明記なし
- 個人情報保護法 23条（第三者提供）: OpenAI（米国）にデータ送信するため、越境移転の同意が必要
- 職業安定法の書類保管ルールにも触れる可能性

**修正案**:
- フォーム上部に「入力内容は履歴書作成のためOpenAI社（米国）に送信されます」と同意チェックボックス
- `privacy.html` に履歴書AI作成の項目を追記

### 🟠-11. `/^[a-z0-9-]{6,40}$/` は6文字で通る
- `slice(0, 12)` の結果は常に12文字（8hex + '-' + 3hex）
- 短縮IDを通す理由がないので `/^[a-f0-9-]{12}$/` に固定

### 🟠-12. KVに `createdAt` / `ipHash` / `sourceSessionId` 等のメタ情報なし
- 不正利用時の追跡が不可。生成時に別キーで `resume_meta:<id>` を書くべき
- テストデータと本番データの区別が付かない（現在7件が混在）

## ✅ 既に良好な点

- HTML出力は `escapeHtml()` で基本XSSはブロック済み（AI生成テキスト含む）
- CORSは `quads-nurse.com` に制限済み（ブラウザ経由は他オリジンNG）
- KV `expirationTtl = 7日` で自動削除
- LINE Webhook のHMAC検証は実装済み（別エンドポイント）
- 現状ではSQL層を通していないため SQLi の余地なし
- `resume/index.html` に `meta robots=noindex, nofollow` ✅
- Worker レスポンスに `X-Robots-Tag: noindex` ✅
- `_headers` 側に HSTS / X-Frame-Options: DENY / Referrer-Policy ✅（ただし GitHub Pages のみ）

## 優先タスク（推奨順）

1. **今日**: Slack通知から氏名とURL削除。テスト6件をKVから手動削除（`resume:0d99c38a-4fa` 等）
2. **今週**: `/api/resume-generate` に sessionId 検証+レートリミット導入、userId はサーバー側決定
3. **今週**: 閲覧URLを 32hex以上に拡張 + 正規表現厳格化 + `Referrer-Policy: no-referrer`
4. **次週**: 同意画面（OpenAI 越境移転）+ 入力バリデーション
5. **中期**: Cookie/LIFF ベースの本人閲覧制限、KV保存時のアプリ層暗号化
