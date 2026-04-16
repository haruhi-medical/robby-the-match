# Gatekeeper #2: Worker API AI応答フォールバック実装

**日付**: 2026-04-17
**対象ファイル**: `/Users/robby2/robby-the-match/api/worker.js`
**対象範囲**: `handleChat()` (LP `/api/chat` エンドポイント)
**段数**: 4段（OpenAI → Anthropic Claude Haiku → Google Gemini Flash → Cloudflare Workers AI Llama 3.3 70B）

---

## 実装サマリ

LP チャット（`handleChat`）の AI 応答を、従来の「if/else 排他分岐（1段のみ失敗したら 502 エラー）」から
「多段 try/catch フォールバック（1つでも成功すれば応答）」に改修した。

### 追加した関数

`callChatAIWithFallback(systemPrompt, sanitizedMessages, env)` を
`handleChat` の直前（`worker.js` L1615）に新規追加。

- 各プロバイダごとに `try{}catch{}` で内部関数 `tryOpenAI / tryAnthropic / tryGemini / tryWorkersAI` を定義
- 各呼び出しに **15秒の AbortController タイムアウト**（Workers AI は `Promise.race` でタイムアウト）
- 失敗時は `null` を返し、次のプロバイダへ進む
- 各段階の失敗は `console.error` で記録（どのプロバイダが落ちたか分かる）
- 返り値: `{ aiText, provider }`（全失敗時は `{ aiText: "", provider: null }`）

### 呼び出し順の制御

`env.AI_PROVIDER` で先頭プロバイダを変更可能（後方互換）:
- `"openai"` or 未設定 → OpenAI → Anthropic → Gemini → Workers AI（デフォルト）
- `"anthropic"` → Anthropic → OpenAI → Gemini → Workers AI
- `"gemini"` → Gemini → OpenAI → Anthropic → Workers AI
- `"workers"` → Workers AI → OpenAI → Anthropic → Gemini

### 既存呼び出し箇所の置換

L1945-1961（旧 L1775-1856）の if/else if/else ブロックを、ヘルパー呼び出し 1回に置き換え。
全プロバイダ失敗時には日本語定型メッセージを返す（502 エラーは返さない）:

```js
aiText = "申し訳ございません、ただいま混み合っておりAIがお返事できません。
         LINE担当者におつなぎしますので、画面下部のLINEボタンからご連絡ください。";
```

---

## 変更行数

- **追加**: +175 行（ヘルパー関数 `callChatAIWithFallback`）
- **削減**: -73 行（旧 if/else if/else ブロック）
- **置換**: +23 行（ヘルパー呼び出し + 最終フォールバック）
- **実質差分**: +125 行前後

`node --check api/worker.js` で構文 OK を確認済み。

---

## 既存挙動への互換性

### 維持された挙動
- `env.AI_PROVIDER` 環境変数のセマンティクスは維持（先頭プロバイダの切り替え）
- `env.CHAT_MODEL`（OpenAIモデル切替）も維持
- レスポンス形式 `{ reply, done }` は不変
- レート制限・トークン検証・セッション管理は全て不変
- `ctx.waitUntil` / Push API は handleChat 外の処理なので影響なし
- 「AI応答が短すぎる or JSON 風」の場合の既定応答も維持

### 変更された挙動
- **OpenAI が落ちても 502 を返さず、次のプロバイダに進む**（ここがゴール）
- **全失敗時は 502 ではなく 200 + 日本語定型メッセージ**（UXを壊さない）
- 各呼び出しに 15 秒タイムアウトが付く（以前は無限待ち）
- `env.ANTHROPIC_API_KEY` が設定されていれば、OpenAI が落ちたときに自動で使われる
- `env.GOOGLE_AI_KEY` が設定されていれば Gemini にも自動フォールバック
- `env.AI`（Workers AI バインディング）があれば最終段で使われる

### 環境変数の追加は不要
- 新規契約は禁止の制約に従い、**既存 env のみを使用**
- Anthropic / Gemini の API Key が無ければ、その段階は自動でスキップされる（関数冒頭で `return null`）

---

## デプロイ時の注意点

1. **デプロイコマンド**（MEMORY.md 準拠）:
   ```bash
   cd api && unset CLOUDFLARE_API_TOKEN && npx wrangler deploy --config wrangler.toml
   ```
   `--config wrangler.toml` を省略すると別 Worker にデプロイされる。

2. **既存シークレットの維持確認**（wrangler deploy で secrets が消えることがある）:
   ```bash
   wrangler secret list --config wrangler.toml
   ```
   以下が残っていることを必ず確認:
   - `OPENAI_API_KEY`（必須）
   - `LINE_CHANNEL_SECRET` / `LINE_CHANNEL_ACCESS_TOKEN` / `LINE_PUSH_SECRET`
   - `SLACK_BOT_TOKEN` / `SLACK_CHANNEL_ID`
   - `CHAT_SECRET_KEY`

3. **Workers AI バインディング**: `wrangler.toml` の `[ai] binding = "AI"` が有効であること。

4. **デプロイ後の生存確認**: LP（https://quads-nurse.com/）のチャットで「こんにちは」を送り、
   Cloudflare ダッシュボードの Logs で `[Chat] AI provider success: openai` が出ることを確認。

5. **障害演習**（任意）: 一時的に `OPENAI_API_KEY` を無効値に差し替えて、ログに
   `[Chat] AI provider openai failed, trying next` → `[Chat] AI provider workers success` が出るかを確認。

---

## 懸念点・残タスク

### 懸念点
1. **レイテンシ最大値**: 全プロバイダが順次 15 秒タイムアウトすると最大 60 秒。
   Cloudflare Workers の CPU 時間制限（通常プラン 30秒 / 有料プラン 5分）に注意。
   実運用では 1 段目が数秒で返るはずなので問題なしと判断。

2. **Workers AI のコンテキスト長**: 既存 LINE 側では `systemPrompt.slice(0, 2000)` にしていた。
   LP 側は最大 4000 文字に設定（LP は会話が長めのため）。将来的には動的調整が必要かも。

3. **Anthropic モデル指定**: 旧コードは `env.CHAT_MODEL || "claude-haiku-4-5-20251001"` だったが、
   新コードでは Anthropic 側は固定 `"claude-haiku-4-5-20251001"`。
   `CHAT_MODEL` は OpenAI 用に限定される（紛らわしい共用を解消）。
   Anthropic のモデルを変えたい場合は別の env を追加する必要あり（今回は新規 env を増やさず）。

4. **Gemini の Workers 実行環境**: `fetch` ベースなので問題なし。要 `GOOGLE_AI_KEY`。

### 残タスク
- [ ] メインエージェントがデプロイ実行
- [ ] 本番環境での生存確認（Cloudflare ダッシュボード Logs）
- [ ] STATE.md の「4段フォールバック」記述を事実と整合させる（実装済みとなったので虚偽ではなくなる）
- [ ] LINE 側 `handleLineAIConsultation` (L7287〜) は既に 4 段実装済みなので変更不要
- [ ] `callLineAI` (L7477〜) は経歴書生成/修正用の 2 段実装（OpenAI → Workers AI）。
      必要なら同様に 4 段に拡張できるが今回スコープ外

---

## テスト手順（本番デプロイ後）

**注**: Workers は本番環境依存のためローカル自動テスト不可。以下は手動確認項目。

1. **正常系**（OpenAI 疎通あり）:
   - LP チャットで「こんにちは、転職相談です」と送信
   - 通常応答が返ることを確認
   - Logs に `[Chat] AI provider success: openai` が出る

2. **フォールバック発動**（OpenAI 擬似障害）:
   - 一時的に `OPENAI_API_KEY` を `wrangler secret put` で無効値に変更
   - LP チャットで送信
   - Workers AI または Anthropic が応答することを確認
   - Logs に `[Chat] AI provider openai failed, trying next` → 次段成功のログ

3. **完全失敗**（全プロバイダ停止 - 演習）:
   - 全 API キーを無効化し `env.AI` バインディングを一時外す（実施は慎重に）
   - LP チャットで送信 → 「申し訳ございません、ただいま混み合っており…」の定型メッセージが返る
   - HTTP ステータスは 200（502 エラーは返さない = UX 維持）

4. **タイムアウト**: 外部から検証困難。ログでタイムアウトが記録されることを確認。

---

## 変更前後の挙動比較

| シナリオ | 変更前 | 変更後 |
|---------|--------|--------|
| OpenAI 成功 | OpenAI応答 | OpenAI応答（同じ） |
| OpenAI 502/429 | **502 エラー** | Anthropic/Gemini/Workers AI に自動フォールバック |
| OpenAI タイムアウト | **無限待ち** | 15秒でタイムアウト → 次段 |
| OpenAI API Key 未設定 | Workers AI にフォールバック | Workers AI にフォールバック（同じ） |
| 全プロバイダ失敗 | **502 エラー** | 200 + 日本語定型メッセージ |

`handleChat` のレスポンスが 502 を返すケースが実質なくなり、ユーザ体験が大幅に改善する。
