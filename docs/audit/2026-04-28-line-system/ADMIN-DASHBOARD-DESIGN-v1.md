# 管理ダッシュボード v1 設計書（実装スペック）

> 2026-04-28 / v0 → 3エージェント並列レビュー → v1 確定
> 致命的指摘を全て反映。これが実装の唯一スペック。

## 0. v0からの主要変更

| # | 変更 | 理由 |
|---|------|------|
| 1 | `humanRepliedAt` 全削除 | 実装に存在しない。phase === "handoff" が真実（Agent B指摘） |
| 2 | `admin:bot_off` 独立KV廃止 | 既存 `phase === "handoff"` を再利用。webhook既存ロジックを壊さない |
| 3 | 全件 `kvListAll('line:')` 廃止 | CPU timeout危険。`ver:${userId}` 軽量キー＋ `recent_activities` 単一キー |
| 4 | timingSafeEqual を hex固定長版に | 既存 worker.js:4099 のバグ修正含む |
| 5 | PBKDF2 (600k iter) password hash | 平文比較廃止 |
| 6 | HttpOnly + SameSite=Strict cookie | LocalStorage廃止 |
| 7 | HMAC に nonce 必須 | リプレイ防止 |
| 8 | 監査ログ Slack 外部ミラー | 「改竄不可」は自己欺瞞。多重化 |
| 9 | パスワード preview 10char ハッシュに含める | デバッグ性確保 |
| 10 | CF-Connecting-IP 明示 | X-Forwarded-For 偽装防止 |
| 11 | `/admin/*` HTML を Worker で配信 | GitHub Pages はBasic不可、Cookieも別ドメインで複雑化 |

## 1. アーキテクチャ

```
[社長スマホ Safari]
   ↓ HTTPS
[Cloudflare Worker (robby-the-match-api)]
   ├─ GET  /admin/                    → ログイン HTML
   ├─ GET  /admin/app                 → SPA HTML (Cookie認証必要)
   ├─ POST /api/admin/login           → password検証, session発行
   ├─ POST /api/admin/logout          → session削除
   ├─ GET  /api/admin/dashboard       → メトリクス
   ├─ GET  /api/admin/conversations   → 一覧 (ver: list)
   ├─ GET  /api/admin/user/:userId    → 詳細 (line: get)
   ├─ POST /api/admin/user/:userId/bot-toggle  → entry.phase 切替
   ├─ POST /api/admin/user/:userId/reply       → LINE Push
   └─ GET  /api/admin/audit-log       → 監査ログ閲覧
   
KV書き込み:
   admin:session:${token}       (12h, login時)
   admin:audit:${ts}:${rand}    (180日, 全admin操作)
   admin:lockout:${ip}:${min}   (10分窓, login失敗カウンタ)
   admin:nonce:${nonce}         (10分, リプレイ防止)
   admin:recent:activities      (単一キー, 最大100件, webhook時に追記)
   line:${userId}               (既存, BOT toggle時に entry.phase 上書き)

外部ミラー:
   Slack #claudecode (C09A7U4TV4G) ← 全admin操作転送
```

## 2. データモデル変更（既存entryのみ）

### 既存フィールド再利用
- `entry.phase` = `"handoff"` を BOT沈黙の唯一の真実とする
- `entry.handoffAt` = 既存

### 新規フィールド（entry内）
- `entry.adminMutedAt: number | null` — admin操作でhandoff化した時刻（監査用）
- `entry.adminMutedReason: string | null` — 管理画面で入力した理由
- `entry.adminMutedBy: string | null` — actor識別子（"admin"固定）

これにより、既存 webhook の handoff_silent ロジック（worker.js:8888他）がそのまま動く。

### entry.phase 切替の挙動
```
[BOT OFF]
  entry.phase ← "handoff"
  entry.handoffAt ← Date.now()
  entry.handoffReason ← "admin_muted"
  entry.adminMutedAt ← Date.now()
  entry.adminMutedReason ← <理由>
  entry.adminMutedBy ← "admin"

[BOT ON]
  entry.phase ← 元の phase（OFF時に保存しておく）or "free_consult"
  entry.handoffAt ← null
  entry.adminMutedAt ← null
  // 過去の adminMutedReason は監査用にlogへ
```

### 復元用フィールド
- `entry.phaseBeforeMute: string | null` — OFF時の phase を保存

## 3. API仕様（実装の正本）

### 共通仕様
- 認証Cookie: `admin_session=<token>; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=43200`
- 認証なしリクエスト → 401
- 全エンドポイントで `Cache-Control: no-store`
- 全エラー応答は `{ error: string }`

### POST /api/admin/login
- body: `{ password: string }`
- 処理:
  1. IP取得（CF-Connecting-IP）
  2. lockout チェック（10分窓5回）
  3. PBKDF2(password, env.ADMIN_SALT, 600k) を env.ADMIN_PASSWORD_HASH と timingSafeEqualHex
  4. 失敗 → admin:lockout:${ip}:${min} +1 → 401
  5. 成功 → token = randomUUID() → admin:session:${token} put 12h → Set-Cookie
  6. 監査ログ: `login` (result: ok/fail)
- response: `{ ok: true }` + Set-Cookie ヘッダ

### POST /api/admin/logout
- 処理:
  1. Cookie の token 取得
  2. admin:session:${token} delete
  3. 監査ログ: `logout`
  4. Set-Cookie で expire=0
- response: `{ ok: true }`

### GET /api/admin/dashboard
- 認証必要（cookie）
- 処理:
  1. `event:${today}:line_follow` get → newFollowers
  2. `admin:recent:activities` get → 最新100件
  3. recent_activities から phase別カウント:
     - aiConsulting: phase が AI_CONSULT/AICA に含まれる
     - applyIntent: appliedAt or applyStep != null
     - emergency: phase === "handoff" かつ handoffAt > 24h前
- response: `{ today: {newFollowers, aiConsulting, applyIntent, emergency}, recent: [...10件] }`

### GET /api/admin/conversations?limit=30&offset=0
- 認証必要
- 処理:
  1. kvListAll('ver:') で全件取得（軽量キー、< 100B/件）
  2. 各 ver:${userId} の value (JSON: phase, updatedAt) を get
  3. updatedAt 降順ソート
  4. limit/offset でページング
  5. 各エントリの最新メッセージ概要は `admin:recent:activities` から引く（無ければプレースホルダ）
- response: `{ items: [{userId, phase, updatedAt, lastMessage?}], total }`

### GET /api/admin/user/:userId
- 認証必要
- 処理:
  1. line:${userId} get → entry
  2. member:${userId} get → member
  3. member:${userId}:resume_data get → resumeData
  4. handoff:${userId} get → handoffMeta
- response: `{ entry, member, resumeData, handoffMeta }`
- entry内には aicaCareerSheet, careerSheet, messages, consultMessages, aicaMessages 等あり、そのまま返す

### POST /api/admin/user/:userId/bot-toggle
- 認証必要 + HMAC署名 + nonce
- body: `{ enabled: boolean, reason?: string }`
- 処理:
  - enabled=false:
    1. line:${userId} get → entry
    2. entry.phaseBeforeMute = entry.phase
    3. entry.phase = "handoff"
    4. entry.handoffAt = now, entry.handoffReason = "admin_muted"
    5. entry.adminMutedAt = now, entry.adminMutedReason = body.reason
    6. line:${userId} put + ver:${userId} put
  - enabled=true:
    1. line:${userId} get → entry
    2. entry.phase = entry.phaseBeforeMute || "free_consult"
    3. entry.phaseBeforeMute = null
    4. entry.handoffAt = null
    5. entry.adminMutedAt = null
    6. put
  - 監査ログ: `bot_toggle` (target, payload: {enabled, reason})
  - Slack 外部ミラー
- response: `{ ok: true, phase: <new phase> }`

### POST /api/admin/user/:userId/reply
- 認証必要 + HMAC署名 + nonce
- body: `{ text: string }`
- 処理:
  1. text.length チェック (1〜5000)
  2. URL個数 ≤ 3 チェック
  3. LINE Push API 呼び出し
  4. 成功時:
     - entry.adminLastReplyAt = now
     - entry.phase = "handoff"（自動沈黙化）
     - entry.handoffAt = now
     - put
  5. 監査ログ: `reply_sent` (payload: {fingerprint, length, preview, lineApiStatus})
  6. Slack 外部ミラー
- response: `{ ok: true, lineStatus: 200 }`

### GET /api/admin/audit-log?limit=100&action=...
- 認証必要
- 処理:
  1. kvListAll('admin:audit:') 直近100件
  2. action フィルタ
  3. ts降順
  4. 監査ログ閲覧自体も `audit_view` action で記録
- response: `{ items: [...] }`

## 4. 認証実装詳細

### timingSafeEqualHex (hex固定長)
```js
function timingSafeEqualHex(a, b) {
  if (typeof a !== "string" || typeof b !== "string") return false;
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) {
    diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return diff === 0;
}
```
**既存の worker.js:4099 timingSafeEqual も合わせて修正。**

### PBKDF2 password
```js
async function hashPassword(password, saltHex) {
  const salt = hexToBytes(saltHex);
  const key = await crypto.subtle.importKey("raw",
    new TextEncoder().encode(password),
    { name: "PBKDF2" }, false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits(
    { name: "PBKDF2", salt, iterations: 600000, hash: "SHA-256" },
    key, 256);
  return bytesToHex(new Uint8Array(bits));
}
```
- env.ADMIN_PASSWORD_HASH (hex 64文字)
- env.ADMIN_SALT (hex 32文字)

### HMAC + nonce
```js
async function verifyAdminHmac(request, env, body) {
  const sig = request.headers.get("X-Admin-Sig");
  const ts = request.headers.get("X-Admin-Ts");
  const nonce = request.headers.get("X-Admin-Nonce");
  if (!sig || !ts || !nonce) return false;
  if (Math.abs(Date.now() - parseInt(ts, 10)) > 5*60*1000) return false;
  const nonceKey = `admin:nonce:${nonce}`;
  if (await env.LINE_SESSIONS.get(nonceKey)) return false;
  await env.LINE_SESSIONS.put(nonceKey, "1", { expirationTtl: 600 });
  const payload = `${ts}.${nonce}.${body}`;
  const expected = await hmacHex(env.ADMIN_HMAC_KEY, payload);
  return timingSafeEqualHex(expected, sig);
}
```

### messageFingerprint (keyed hash)
```js
async function messageFingerprint(text, userId, env) {
  const h = await hmacHex(env.AUDIT_HASH_KEY, `${userId}|${text}`);
  return h.slice(0, 16);
}
// preview: 24文字以下なら "(short)"、超なら "先頭10..."+末尾10
```

## 5. recent_activities の追記実装

webhook末尾（メッセージ処理後）で追記。
```js
async function pushRecentActivity(env, userId, summary, phase) {
  const cur = JSON.parse((await env.LINE_SESSIONS.get("admin:recent:activities")) || "[]");
  cur.unshift({ userId, summary: summary.slice(0, 50), phase, ts: Date.now() });
  await env.LINE_SESSIONS.put("admin:recent:activities", JSON.stringify(cur.slice(0, 100)));
}
```
ダッシュボードはこれを読むだけで一覧が成立。`list('line:')` 不要。

## 6. 必要なWorker secrets

```
ADMIN_PASSWORD_HASH    （PBKDF2出力 hex 64文字）
ADMIN_SALT             （hex 32文字）
ADMIN_HMAC_KEY         （hex 64文字）
AUDIT_HASH_KEY         （hex 64文字）
SLACK_AUDIT_CHANNEL_ID （C09A7U4TV4G を再利用 or 専用作成）
```

## 7. フロントエンド実装

### ファイル
- Worker内に文字列で埋め込み（admin:HTMLを直接return）
- ログイン: `/admin/` (HTML)
- SPA本体: `/admin/app` (HTML, Cookie必須)
- manifest: `/admin/manifest.json`
- service worker: `/admin/sw.js`

### SPAルータ（hashchange）
- `#dashboard` (default)
- `#conversations`
- `#user/:userId`
- `#audit`

### スタイル
- 1ファイル内 `<style>` ブロック
- システムフォント、シンプル
- 375px〜600px最適化
- タップ可能要素 ≥ 44×44px

## 8. 品質ゲート（強化版）— 70点満点・63点（90%）合格

### 配点
| Gate | 項目 | 重み | 最大 |
|------|------|------|------|
| G1 | セキュリティ 8項目 | ×3 | 24 |
| G2 | 機能 7項目 | ×3 | 21 |
| G3 | 監査ログ 5項目 | ×2 | 10 |
| G4 | UX 5項目 | ×1 | 5 |
| G5 | ログ完全性 5項目 | ×2 | 10 |
| **合計** | | | **70** |

### 拒否権項目（1つでもFailなら全体Fail）
- G1-1: 認証なしで /api/admin/* 全エンドポイント 401
- G1-3: HMAC欠落POSTで403、HMAC不正でも403
- G2-3: BOT OFFで実LINEに本当に応答しない
- G3-3: append-only証明（kv.delete on audit が grep -c で 0）
- G5-1: 実E2E 動作証拠（curlログ束 + 実画面スクショ）

### G1: セキュリティ
- [ ] 認証なし /api/admin/* 全エンドポイント 401（curlログ）【拒否権】
- [ ] timingSafeEqualHex を **HMAC比較・password比較で使用**（grep証明）
- [ ] HMAC欠落/不正/ts超過/nonce再利用 全て403（curlログ）【拒否権】
- [ ] PBKDF2(600k) でpassword hash（コード grep）
- [ ] login 5回失敗→6回目403→10分後成功（実機ログ）
- [ ] HttpOnly + SameSite=Strict cookie（curl -v ログ）
- [ ] CF-Connecting-IP 使用（grep）
- [ ] 監査ログKVに削除APIが存在しない（grep -c で `kv.delete.*admin:audit` = 0）

### G2: 機能
- [ ] ダッシュボード4指標が実KVから取得（コード grep + 数値突合）
- [ ] 会話一覧が ver: 経由（line: のlistAll をしない）
- [ ] BOT OFF実機5ステップ（送信→OFF→沈黙→ON→復帰、各スクショ）【拒否権】
- [ ] 返信が5秒以内にLINE着信
- [ ] entry.phaseBeforeMute による正しい復元
- [ ] 既存webhookフローを壊していない（友だち追加→ヒアリング→マッチング 通常フロー1回成功）
- [ ] アクションマトリクス（Cookie OK/NG × HMAC OK/NG = 4パターン）の curl結果

### G3: 監査ログ
- [ ] login/logout/bot_toggle/reply_sent/audit_view 5種が記録
- [ ] payload に messageHash と preview のみ、本文なし（生JSON公開）
- [ ] append-only証明: grep -c で kv.delete on `admin:audit` = 0【拒否権】
- [ ] Slack #claudecode に外部ミラーが届く
- [ ] TTL 180日が各エントリに付与

### G4: UX
- [ ] 375px幅で横スクロールゼロ（DevTools emulate スクショ）
- [ ] タップ要素 ≥ 44×44px
- [ ] PWA manifest valid + icon 192/512
- [ ] Service Worker でログイン画面オフライン表示
- [ ] レスポンス時間 ≤ 2秒（DevTools Network ログ）

### G5: ログ完全性
- [ ] curl 全14ライン（7エンドポイント × 認証あり/なし）【拒否権】
- [ ] wrangler kv:key list 出力（admin:audit, admin:session）
- [ ] wrangler deploy 最終ライン
- [ ] wrangler secret list（既存secret消失なし）
- [ ] BOT OFF→ON E2E スクリーン録画 or スクショ束（最低6枚）

### スコアと判定
- **63点以上 + 拒否権全Pass**: 完了OK
- **57〜62点**: Conditional → 修正→再監査
- **56点以下**: Fail → 修正→再監査
- **拒否権1項目でもFail**: 即Fail、再監査

## 9. 完了の厳格な定義（Agent C 15項目）

完了宣言には以下**全て**真:

1. wrangler deploy 成功ログ
2. 4新規secrets が wrangler secret list に存在
3. 既存7secrets 消失なし
4. curl 14ライン
5. ホーム画面追加スクショ
6. BOT OFF→ON E2E 動画 or スクショ束
7. 監査ログ画面に5種actionスクショ
8. wrangler kv:key list で admin:audit ≥ 5件
9. G1〜G5 全項目チェック済み
10. 監査スコア 63点以上
11. Slack デプロイ通知着弾
12. STATE.md / PROGRESS.md 更新
13. 既存BOT機能リグレッションなし
14. 監査ログに異常エントリなし
15. logs/admin-dashboard-build/2026-04-28/ にコミット

## 10. 工数（v1）

- 設計v1完成: 完了
- Worker API実装: 90分
- フロントエンド: 90分
- 既存timingSafeEqual修正: 10分
- secrets生成と設定: 30分
- デプロイ + 既存BOT動作確認: 30分
- E2Eテスト + ログ収集: 60分
- コードレビュー（並列2agent）: 30分
- 監査agent: 30分
- 修正バッファ: 60分

**合計: 約7時間**（Agent Cの10時間より圧縮、機能を最小化＋ Cloudflare Access等は v2へ）

## 11. v2 への持ち越し

- Cloudflare Access移行（社長Google SSO）
- Web Push通知
- 検索/絞り込み高度化
- 複数admin対応
