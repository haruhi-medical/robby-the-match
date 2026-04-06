# AI相談/UX品質 監査レポート

> 監査日: 2026-04-06
> 対象ファイル: `api/worker.js`
> 監査者: Specialist 5 (AI相談/UX品質)

---

## Area 1: AI Consultation Flow

### 入口

ユーザーがAI相談に入る経路は複数:

1. **matching_preview後** → `ai_consultation` phase (line 4153): 求人カード表示後、「相談したいことがある」(`consult=start`) をタップ
2. **consult=start** (line 5193) → `ai_consultation_waiting` → テキスト入力待ち
3. **consult=continue** (line 5195) → 追加質問待ち
4. **prep=question** (line 5301) → 面接対策中から自由相談に戻す
5. **apply_confirm後** (line 4234) → 「転職の相談をする」(`consult=start`)

### AI Provider Fallback Chain (4段階)

| 優先度 | プロバイダ | モデル | タイムアウト |
|--------|-----------|--------|------------|
| 1 | OpenAI | gpt-4o-mini | 8秒 |
| 2 | Anthropic | claude-haiku-4-5-20251001 | 8秒 |
| 3 | Google | gemini-2.0-flash | 8秒 |
| 4 | Cloudflare Workers AI | llama-3.1-8b-instruct | 5秒 |

**所見**: フォールバックチェーンは健全。各段階で `AbortController` + `setTimeout` でタイムアウト制御あり。

### 5ターン制限 (FIX-08)

- `MAX_TURNS = 5` (初期上限)
- `EXTENDED_MAX = 8` (延長後上限)
- `consult=extend` で +3ターン延長可能 (1回限り)
- 2回目以降の延長リクエスト → `consult_handoff_choice` にリダイレクト

**所見**: 適切に実装されている。延長の無限ループ防止も `entry.consultExtended` フラグで対処済み。

### 全AI失敗時のエラーハンドリング

全プロバイダ失敗時 (line 6635-6648):
- userメッセージを `pop()` してターンカウントずれ防止 (良い設計)
- 「回答の生成に時間がかかっています」メッセージ + Quick Reply
- 「もう一度試す」(`consult=retry`) / 「担当者に相談する」(`consult=handoff`)

**所見**: 適切に実装。ユーザーが行き詰まらない。

### 3往復後のハンドオフ提案

- `consultCount >= 3` で Quick Reply に「担当者と話したい」を追加 (line 6671)
- 3往復未満でも「担当者と話したい」は常に表示

**所見**: 自然なタイミングで担当者提案が出る。問題なし。

---

## Area 2: System Prompt Quality

### 2つのシステムプロンプト

1. **`buildSystemPrompt()`** (line 1180-1281): chat.js (Web) 用。非常に詳細。
2. **`handleLineAIConsultation()` 内** (line 6543): LINE Bot AI相談用。簡潔版。

### [FIXED] LINE Bot AI相談プロンプトの問題

| 項目 | 修正前 | 修正後 |
|------|--------|--------|
| エリア言及 | 「神奈川県の給与・求人データを使う」(ハードコード) | ユーザーのエリアに応じて動的に変更（東京/千葉/埼玉もカバー） |
| 紹介可能施設の区別 | なし (重大な欠落) | 小林病院のみ直接紹介可能、それ以外は一般情報として伝える旨を追加 |
| 断定表現の禁止 | なし | 「最高」「No.1」「絶対」「必ず」等の禁止を追加 |
| プロンプトインジェクション防御 | なし | システムプロンプト開示拒否ルールを追加 |

**修正内容** (api/worker.js line 6543付近):
- `神奈川県の` → ユーザーエリアに応じた動的文字列 (`${areaContext}`)
- 紹介可能施設ルール追加
- 断定表現禁止ルール追加
- プロンプトインジェクション防御追加

### Web Chat (`buildSystemPrompt`) の品質

- ブランド名: 「ナースロビー」 -- 正しい
- キャラクター名: 「ロビー」 -- 正しい
- エリア: 「神奈川県10エリア」がデフォルトだが、ユーザーのprefection/areaに応じて東京等のデータも注入される (line 1256-1261)
- 紹介可能施設の区別: 明確に記載 (line 1232-1236) -- 良い
- 行動経済学フェーズ別プロンプト注入: 実装済み (line 1271-1278)
- プロンプトインジェクション防御: 実装済み (line 1251-1253)

**所見**: Web Chat用プロンプトは非常に充実。LINE Bot用が簡潔すぎて重要ルールが欠落していた（修正済み）。

---

## Area 3: Post-Matching UX

### 「この施設について聞く」タップ時

**通常求人カード** (line 3860):
- postback: `match=detail&idx=${idx}`
- → `entry.interestedFacility` に施設名を保存 (line 5107)
- → `handoff_phone_check` phase (line 5117)
- → 「お電話は控えた方が良いですか？」Quick Reply

**フォールバック施設カード** (line 3933):
- postback: `handoff=ok&facility=${name}`
- → `entry.interestedFacility` に施設名を保存 (line 5152)
- → `handoff_phone_check` phase (line 5154)

**所見**: 両方とも正しく `handoff_phone_check` に遷移。施設名も保持される。問題なし。

### 「もっと求人を見る」

- postback: `matching_preview=more` (line 3971)
- → `matching_browse` phase (line 5039)
- → 追加のFlex Messageカルーセルを表示

**所見**: 問題なし。

### 「条件を変えて探す」

- postback: `welcome=see_jobs` (line 3973)
- → intake_lightフィールドをリセット (line 5161-5170: `delete entry.prefecture/area/areaLabel/workStyle/urgency/facilityType` 等)
- → `il_area` phase (line 5177)

**所見**: 適切にリセットされてから再度エリア選択に戻る。問題なし。

### 「直接相談する」→ ハンドオフ

- postback: `handoff=ok` (line 3975)
- → `handoff_phone_check` (line 5154)
- → 「お電話は控えた方が良いですか？」
  - 「はい（LINEでお願いします）」→ `handoff` (line 5137)
  - 「いいえ（電話OK）」→ `handoff_phone_time` (line 5135) → 時間帯確認 → `handoff`
- handoff完了時: Slack通知 + KVにハンドオフインデックス登録 (7日TTL)

**所見**: 完全に機能している。電話/LINE選択 → 時間帯確認 → Slack通知 の流れは丁寧。

---

## Area 4: Nurture Flow

### 「まだ早いかも」/ 情報収集

複数の入口:
- `match=later` (line 5125) → `nurture_warm`
- `matching_preview=later` (line 5044) → `nurture_warm`
- `matching_browse=done` (line 5058) → `nurture_warm`
- `consult=done` (line 5209) → `nurture_warm`
- `apply=cancel` (line 5247) → `nurture_warm`
- `il_urg=info` (低温度感, line 5158) → `nurture_warm`

### nurture_warm メッセージ (line 4051)

```
了解です！
必要な時にいつでも話しかけてくださいね。

新着求人が出たらお知らせすることもできます。
```
Quick Reply: 「新着をお知らせして」(`nurture=subscribe`) / 「大丈夫です」(`nurture=no`)

### フォローアップメカニズム

**Cron Trigger** (line 6815-6860+): `handleScheduledNurture()`
- 毎日10:00 JST (`0 1 * * *` UTC)
- KV `nurture:` prefix でナーチャリング対象を走査
- 配信スケジュール: **Day 3, Day 7, Day 14** (月3回まで)
  - Day 3: エリア新着情報（動的求人数付き）
  - Day 7: 転職市場データ
  - Day 14: 限定感のあるリマインド
- D1から動的求人数を取得してメッセージに含める

### 再入口

- nurture_warm中の自由テキスト → Quick Reply再表示 (line 5343)
- `nurture_subscribed` phase: 「今すぐ求人を探す」(`welcome=see_jobs`) で再入口
- いつでも「求人を探す」とテキスト入力で復帰可能

**所見**: ナーチャリングフローは完成度が高い。Day 3/7/14の段階的フォロー + 動的求人数 + 再入口あり。

---

## 修正サマリ

### 実施した修正 (1件)

| # | ファイル | 行 | 内容 | 重要度 |
|---|---------|-----|------|--------|
| 1 | api/worker.js | ~6543 | AI相談システムプロンプト改善: エリア動的化 + 紹介可能施設ルール + 断定表現禁止 + プロンプトインジェクション防御 | 高 |

### 未修正（問題なし or 軽微）

| # | 項目 | 状態 |
|---|------|------|
| 1 | AI Provider Fallback Chain | 問題なし（4段階、タイムアウト制御あり） |
| 2 | 5ターン制限 | 問題なし（延長1回+無限ループ防止） |
| 3 | 全AI失敗時エラーハンドリング | 問題なし（メッセージpop + リトライUI） |
| 4 | post-matching UX全般 | 問題なし（全選択肢が正しく遷移） |
| 5 | ハンドオフフロー | 問題なし（電話/LINE選択→Slack通知→KV登録） |
| 6 | ナーチャリングフロー | 問題なし（Day 3/7/14 + 再入口あり） |
| 7 | ブランド名「ナースロビー」 | 正しく使用されている |
| 8 | キャラクター「ロビー」 | 正しく定義されている |

### 注意点（修正不要だが記録）

1. **LINE Bot AI相談プロンプトとWeb Chat用プロンプトの品質差**: Web Chat用 `buildSystemPrompt()` は ~100行の詳細プロンプト（行動経済学フェーズ、施設DB注入、経験年数別給与等）。LINE Bot AI相談は ~20行の簡潔版。意図的な設計と思われるが（LINEは短い回答が好まれる）、将来的に施設DB情報の注入を検討してもよい。

2. **Claude Haiku モデルID**: `claude-haiku-4-5-20251001` を使用中。モデルバージョンの更新があれば追従が必要。

3. **Workers AI モデル**: `@cf/meta/llama-3.1-8b-instruct` は日本語能力が限定的。フォールバックの最終手段としては妥当だが、日本語品質は期待できない。
