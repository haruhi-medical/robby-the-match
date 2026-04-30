# 課金事故防止ルール v9.4 詳細

**発行**: 2026-04-30
**起点**: 統合パッチ指示書（社長発行）
**位置づけ**: CLAUDE.md v9.4 の詳細補足。CLAUDE.md 200行制限のため要点のみ本体、詳細はここ

---

## 0. 現状の防御

- ✅ OpenAI Hard Limit: $50/月（dashboard側で設定済）
- ✅ Cloudflare Billing Alert: $10/$25/$50（dashboard側で設定済予定。社長手作業）
- 月初〜月末で$50到達時、OpenAI APIが自動停止

---

## 1. 🔴 実装前の社長承認ルール（最重要）

以下に該当する変更は**実装前に必ず社長承認を得る**:

1. **AI API 呼び出しを増やす変更**（OpenAI/Anthropic/Gemini）
   - 例: 「全員aica_turn1起動」「全handoffをAI継続化」
2. **既存ユーザー導線を変更する変更**
   - 例: welcome文言、リッチメニュー、postback挙動
3. **コスト構造に影響する変更**
   - 例: 新cron追加、ポーリング間隔変更
4. **業務フローに影響する変更**
   - 例: handoff削減、自動応答範囲拡大

### 承認プロセス

1. Slack #claudecode に「これからXXを実装したい。理由はYY、想定コストZZ」と投稿
2. 社長から「OK」「進めて」等の明示承認を得る
3. 承認後にデプロイ
4. デプロイ後に Slack #claudecode に「✅ XX 完了 v <hash>」報告

---

## 2. QA監査システム（scripts/audit/）の運用ルール

### ❌ 絶対禁止
1. crontab への登録
2. git pre-push hook への組み込み
3. GitHub Actions での自動実行
4. 失敗時の自動リトライ（無限ループの温床）
5. 社長承認なしでの再実行

### ✅ 必須プロセス
1. 実行前に Slack #claudecode に「QA監査実行します（推定コスト $15）」と告知
2. 社長から「OK」のリアクション or 返信を得る
3. 実行
4. 完了後に Slack #claudecode に結果報告（Pass/Fail件数、実消費額）

### 月次予算
- QA監査用予算: 月$30まで（月2回実行が上限）
- 残り$20は通常運用バッファ

---

## 3. AICA / OpenAI 呼び出しのガードレール

### 実装済 or 実装予定

| 項目 | 値 | 状態 |
|---|---|---|
| AICA MAX_TURNS_PER_PHASE | 20（1フェーズ20ターン） | 実装予定（v9.4 Patch C） |
| AICA MAX_TURNS_TOTAL | 100（1ユーザー100ターン） | 実装予定 |
| AICA DAILY_TURN_CAP | 50（1日50ターン） | 実装予定 |
| /api/chat IP rate limit | 1分10回 / 1時間100回 | 実装予定（v9.4 Patch D） |
| /api/line-push idempotency | 5分以内重複送信ブロック | 実装予定（v9.4 Patch H） |

---

## 4. 緊急時の対応

### OpenAI 異常請求時
1. OpenAI dashboard で当該 API key を無効化
2. Hard Limit を $0 に変更（即停止）
3. Slack #claudecode に状況報告

### Cloudflare 異常請求時
1. Cloudflare dashboard で Workers を一時停止
   - dashboard → Workers & Pages → robby-the-match-api → Settings → Pause
2. Slack #claudecode に状況報告

### LINE 5,000通超過時
1. /api/line-push の rate を確認
2. 必要に応じて KV キーで一時停止フラグ設定

---

## 5. 自動化提案時のチェックリスト

新しい cron / 自動化を追加する前に必ず確認:

- [ ] AI API（OpenAI/Anthropic/Gemini）を呼ぶか？
- [ ] 呼ぶなら、1実行あたりの推定コストは？
- [ ] 月間の総コスト見積もりは？
- [ ] 失敗時のリトライポリシーは？（無限リトライ禁止）
- [ ] 社長承認を得たか？
- [ ] CLAUDE.md にコスト見積もりを記載したか？

→ 1つでも No / 不明なら **実装しない**。

---

## 6. 既存21cron の月次レビュー

毎月初に以下を確認:
- 各cronの実行頻度
- AI呼び出しの有無
- 月間コスト寄与
- 不要なcronの停止判断

責任者: ロビーちゃん（社長レビュー必須）

---

## 7. v9.4 に至る経緯

### Phase B（全員AICA起動）デプロイ後の課題発覚
- 2026-04-30 中に Patch 2 Phase A〜D を進めた結果、全ユーザーが AICA に流入する設計に変わった
- AICA は OpenAI gpt-4o ベースで、1ターンあたり$0.01〜0.05のコスト
- ユーザー数 × ターン数 × 軸別の組み合わせで暴走リスクあり

### 社長決定（4/30 夜）
- 統合パッチ指示書発行
- CLAUDE.md v9.4 で「実装前社長承認ルール」を明文化
- AICA MAX_TURNS / rate limit / idempotency をガードレールとして実装

### 結果オーライだった理由
- F5調査結果（実ユーザー14/14名がAICAバイパス）と整合する妥当な対策
- OpenAI使用額は本日$0.01で暴走していない
- Phase B 後の効果測定でデータが取れる

ただし「結果オーライ」を許すと次回も同じパターン。本ルールが今後の保険。
