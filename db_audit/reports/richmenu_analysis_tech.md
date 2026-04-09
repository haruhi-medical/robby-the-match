# リッチメニューv2 技術実現性分析（25視点）

> 分析日: 2026-04-06
> 対象: worker.js (7,348行) + schema.sql + wrangler.toml
> 分析者: 技術アーキテクトAI

---

## リッチメニュー4機能の概要

| # | 機能 | 状態 |
|---|------|------|
| 1 | お仕事探しをスタート | **既存** — `welcome=see_jobs` → `il_area` フロー |
| 2 | 本日の新着求人 | **新規** — D1 jobs テーブルの差分検出が必要 |
| 3 | 施設検索 | **新規** — D1 facilities 24,488件の検索UI |
| 4 | 履歴書作成（AI） | **半既存** — `buildResumeConfirmMessages()` が存在。独立起動が未実装 |

---

## A. 実装の複雑さ（5視点）

### 1. 各機能のworker.jsへの変更行数の見積もり

| 機能 | 変更行数 | 内訳 |
|------|---------|------|
| 機能1（既存） | **0行** | 変更不要。`welcome=see_jobs` postbackで`il_area`に遷移済み |
| 機能2（新着求人） | **150-200行** | 新phase `new_jobs` + D1クエリ + Flex Message生成 + postbackハンドラ |
| 機能3（施設検索） | **250-350行** | 新phase `facility_search` + テキスト入力受付 + D1 LIKE検索 + ページング + 結果表示 |
| 機能4（履歴書AI） | **80-120行** | 既存 `buildResumeConfirmMessages()` への導線追加 + 未ヒアリング時の入力誘導 |

**合計: 480-670行の追加**（現行7,348行の約7-9%増）

### 2. 既存フローへの影響範囲（破壊的変更はあるか）

**破壊的変更: なし。** 全て追加実装で対応可能。

根拠:
- 既存のpostbackハンドラ `handleLinePostback()` (L5064-5407) はURLSearchParams方式で、新しいキー（`newjobs=xxx`, `facility_search=xxx`, `resume_start=xxx`）を追加するだけ
- 既存のphase遷移ロジック `buildPhaseMessage()` (L3524) はswitch文で、新caseを追加するだけ
- リッチメニュー切り替え `getMenuStateForPhase()` (L3144) も新phaseの分岐追加のみ
- KVエントリ `createLineEntry()` のスキーマにフィールド追加は後方互換（既存ユーザーは `undefined` で問題なし）

**注意点**: `handleLineMessage()`のテキスト→postback推定ロジック (L5588) に新キーワードの追加が必要。

### 3. 新しいphaseの数と遷移の複雑さ

| 機能 | 新phase | 遷移パターン |
|------|---------|------------|
| 機能2 | `new_jobs_list` | リッチメニュータップ → 新着一覧表示 → `match=detail` (既存)に合流 |
| 機能3 | `facility_search_input`, `facility_search_result` | リッチメニュータップ → テキスト入力待ち → 結果表示 → 詳細/再検索 |
| 機能4 | `resume_standalone` | リッチメニュータップ → (入力済みなら)経歴書生成 / (未入力なら)ミニヒアリング → 既存resumeフローに合流 |

**遷移の複雑さ評価:**
- 機能2: **低** — 1phase、既存マッチングUIを再利用
- 機能3: **中** — 2phase、テキスト自由入力のパース処理が必要
- 機能4: **低** — 1phase、既存の `buildResumeConfirmMessages()` (L4339) に接続するだけ

### 4. D1クエリの追加数と性能への影響

| 機能 | 追加クエリ | 想定レイテンシ | インデックス状況 |
|------|-----------|-------------|--------------|
| 機能2 | `SELECT * FROM jobs WHERE last_synced_at >= ? ORDER BY last_synced_at DESC LIMIT 10` | **5-15ms** | `last_synced_at` にインデックス**なし** → 要追加 |
| 機能3 | `SELECT * FROM facilities WHERE name LIKE ? OR address LIKE ? LIMIT 10` | **20-80ms** | `name` にインデックス**なし**。LIKE '%keyword%' はフルスキャン。24,488件 |
| 機能4 | なし（既存データのみ） | **0ms** | — |

**性能リスク:**
- 機能2: `last_synced_at` にインデックスを追加すれば問題なし。`CREATE INDEX idx_jobs_synced ON jobs(last_synced_at);`
- 機能3: **最大のリスク**。`LIKE '%keyword%'` は24,488件のフルテーブルスキャンになる。D1 SQLiteの実測では50-100ms程度だが、同時アクセス増加時に問題になる可能性あり。対策:
  - FTS5 (Full Text Search) の導入（SQLiteネイティブ対応）
  - または `prefecture + city` でプリフィルタしてからLIKE（件数を1/10に削減）

### 5. LINE Messaging APIの制約（リッチメニューの技術仕様）

**現行リッチメニュー実装の確認:**
```
RICH_MENU_STATES = { default, hearing, matched, handoff }  // 4状態
switchRichMenu() → POST /v2/bot/user/{userId}/richmenu/{menuId}
env変数: RICH_MENU_DEFAULT, RICH_MENU_HEARING, RICH_MENU_MATCHED, RICH_MENU_HANDOFF
```

**LINE Messaging API制約:**
- リッチメニュー作成上限: **1,000個/アカウント**（4状態なら問題なし）
- メニュー画像サイズ: **2500x1686px** または **2500x843px**
- タップ領域(action): **最大20個**
- アクション種別: postback / message / uri / richmenuswitch / datetimepicker / clipboard
- **ユーザー別切り替えはAPI必須** — 既にworker.jsで実装済み (`switchRichMenu()` L3160)

**v2で4機能に変更する場合:**
- 既存4状態のリッチメニュー画像を**全て作り直し**（4機能の配置変更）
- LINE Official Account Managerで新画像アップロード + エリア定義 + postback設定
- env変数のリッチメニューIDを更新

---

## B. データの準備状況（5視点）

### 6. 「新着求人」: D1 jobsテーブルにsynced_atがある。差分検出は可能か？

**結論: 可能だが、追加整備が必要。**

schema.sql確認結果:
```sql
-- jobs テーブル
last_synced_at TEXT  -- 最終同期日時（ISO 8601形式）
posted_at TEXT       -- 求人公開日
```

**現状の問題点:**
1. `last_synced_at` は hellowork_fetch.py のバッチ実行時刻。「今日新しく追加された求人」を正確に検出するには、**前回のバッチとの差分**（新規kjno）を記録する仕組みが必要
2. worker.js内のjobsクエリ (L4483) は `kjno, employer, title, rank, score...` を取得するが、`last_synced_at` は SELECT対象に含まれていない → 追加必要
3. `posted_at` （ハローワーク側の公開日）のほうが「新着」の定義としては適切

**推奨実装:**
```sql
-- 新着検出クエリ（posted_atベース、過去7日間）
SELECT * FROM jobs
WHERE posted_at >= date('now', '-7 days')
ORDER BY posted_at DESC
LIMIT 10;
```

**前提条件:**
- hellowork_fetch.py のcron（毎朝06:30）が正常稼働していること
- `posted_at` が正しくパースされていること（現在のデータ品質は未確認）

### 7. 「施設検索」: D1 facilitiesの検索性能。LIKE検索で24,488件は遅くないか？

**結論: 単純LIKEは遅い可能性あり。2段階フィルタで対策可能。**

| 検索方式 | 24,488件での推定速度 | 備考 |
|---------|-------------------|------|
| `WHERE name LIKE '%小田原%'` | 50-100ms | フルスキャン |
| `WHERE prefecture = '神奈川県' AND name LIKE '%小田原%'` | 10-20ms | インデックスで2,000件に絞ってからLIKE |
| `WHERE city = '小田原市'` | 2-5ms | 完全一致（インデックスあれば） |
| FTS5全文検索 | 3-10ms | 最速だが導入コストあり |

**現在のインデックス状況:**
```sql
idx_facilities_prefecture ON facilities(prefecture)  -- ✅ あり
idx_facilities_category ON facilities(category)      -- ✅ あり
idx_facilities_lat_lng ON facilities(lat, lng)       -- ✅ あり
-- name, city にはインデックスなし
```

**推奨:** `city` カラムにインデックスを追加 + ユーザー入力を「エリア選択→施設名キーワード」の2段階にする（LIKE検索の対象を県内施設に限定）。

### 8. 「履歴書作成」: 必要な入力データと生成プロンプトの設計

**既存実装の確認 (L4339-4395):**

`buildResumeConfirmMessages()` が既に以下のデータを使って経歴書を生成:
- `entry.qualification` — 資格（看護師/准看護師/保健師/助産師）
- `entry.experience` — 経験年数
- `entry.workplace` — 直近の職場タイプ
- `entry.workHistoryText` — 職歴テキスト
- `entry.strengths` — 得意分野（配列）
- `entry.change` — 転職理由
- `entry.concern` — 不安点

**AI生成部分 (L4344-4369):**
- OpenAI GPT-4o-mini使用（8秒タイムアウト）
- プロンプト: 500文字以内のプレーンテキスト職務経歴書
- フォールバック: テンプレート生成 `buildTemplateResume()` (L4302)

**リッチメニューから直接起動する場合の課題:**
- intakeフローを経ていないユーザーは `entry.qualification` 等が全て `null`
- → ミニヒアリング（3問: 資格/経験年数/転職理由）を挟む必要あり
- → 既存のintakeフローの一部を再利用可能（`il_*` phaseの設計パターンを踏襲）

### 9. 各機能で必要な新しいKVデータ

| 機能 | 新KVキー | 用途 | TTL |
|------|---------|------|-----|
| 機能2 | `newjobs:last_checked:{userId}` | ユーザー別の最終閲覧日時（既読管理） | 30日 |
| 機能3 | なし | 検索は都度実行。セッションデータは既存 `line:{userId}` に格納 |  |
| 機能4 | なし | `entry.resumeDraft` は既存KVエントリ内に保存済み (L3315) | |

**KV使用量への影響: 最小限。** 機能2のみ新キーが追加されるが、アクティブユーザー数×1キーなので無料プラン上限（100,000 reads/day）には影響なし。

### 10. リッチメニュー画像のLINE仕様（サイズ/アクション定義/状態切り替え）

**画像仕様:**
- サイズ: **2500x1686px**（大）または **2500x843px**（小） — JPEG/PNG
- 容量上限: **1MB**
- 推奨: 大サイズ（4分割しやすい）

**4機能配置案（2×2グリッド）:**
```
┌─────────────────┬─────────────────┐
│  お仕事探しを    │  NEW            │
│  スタート        │  本日の新着求人  │
│  (既存)         │  (新規)         │
├─────────────────┼─────────────────┤
│  SEARCH         │  SUPPORT        │
│  施設検索        │  履歴書作成(AI) │
│  (新規)         │  (新規)         │
└─────────────────┴─────────────────┘
```

**アクション定義（各領域）:**
```json
{
  "areas": [
    { "bounds": {"x":0,"y":0,"width":1250,"height":843}, "action": {"type":"postback","data":"welcome=see_jobs"} },
    { "bounds": {"x":1250,"y":0,"width":1250,"height":843}, "action": {"type":"postback","data":"newjobs=today"} },
    { "bounds": {"x":0,"y":843,"width":1250,"height":843}, "action": {"type":"postback","data":"facility_search=start"} },
    { "bounds": {"x":1250,"y":843,"width":1250,"height":843}, "action": {"type":"postback","data":"resume_start=standalone"} }
  ]
}
```

**状態切り替え:**
- 現行4状態（default/hearing/matched/handoff）は維持
- **全4状態の画像を作り直す必要あり**（下段2ボタンの追加）
- `getMenuStateForPhase()` の変更は不要（phase→state マッピングは既存ロジックのまま）

---

## C. コストとリスク（5視点）

### 11. OpenAI APIコスト（履歴書1件あたり）

**現行コスト（L4354-4367）:**
- モデル: `gpt-4o-mini`
- max_tokens: 400
- 入力: システムプロンプト(~200 tokens) + ユーザーデータ(~100 tokens) = ~300 tokens
- 出力: ~400 tokens

| 項目 | 金額 |
|------|------|
| 入力 (300 tokens × $0.15/1M) | ¥0.007 |
| 出力 (400 tokens × $0.60/1M) | ¥0.036 |
| **1件あたり合計** | **約¥0.04（0.04円）** |
| 月100件生成した場合 | **約¥4** |

**結論: コストは無視できるレベル。** GPT-4o-miniの価格は極めて安価。フォールバックのWorkers AI (Llama 3.3) は無料。

### 12. D1の読み取り制限（無料プランの上限）

**Cloudflare D1 無料プラン:**
- 読み取り: **5,000,000行/日**
- 書き込み: **100,000行/日**
- ストレージ: **5GB**

**現在の推定使用量:**
- マッチング検索: 1回あたり15行 × ユーザー数/日
- 施設カウント: 1回あたり1行 × フェーズ遷移ごと

**機能追加後の追加読み取り:**
| 機能 | 1回あたりの行数 | 日次想定回数 | 日次合計 |
|------|---------------|------------|---------|
| 機能2（新着） | 10行 | 50回 | 500行 |
| 機能3（施設検索） | 10行 | 30回 | 300行 |
| **追加合計** | | | **800行/日** |

**結論: 日次5,000,000行に対して余裕あり。** 現状のトラフィック規模（日次LINE友だち数十人）では制限に達する心配はない。

### 13. Worker実行時間の増加（CPU時間制限）

**Cloudflare Workers制限:**
- CPU時間: **10ms/リクエスト**（無料プラン）, **30ms**（有料$5/月）
- Wall time: **30秒**

**各機能の追加CPU負荷:**
| 機能 | 追加CPU時間 | リスク |
|------|-----------|-------|
| 機能2 | D1クエリ1回 (~2ms CPU) | **低** |
| 機能3 | D1 LIKE検索1回 (~5ms CPU) | **中** — フルスキャン時に10ms超えの可能性 |
| 機能4 | OpenAI API呼び出し (~1ms CPU + 待機) | **低** — API待機はwall timeのみ消費 |

**注意:** 機能3のLIKE検索は CPU時間ではなくwall timeに影響。D1クエリのCPU時間自体はWorkerのCPU制限にカウントされない（D1はサブリクエスト扱い）。

### 14. リッチメニュー状態切り替え（4状態）の複雑さ

**現行:** 4状態（default/hearing/matched/handoff） × 1メニュー画像 = **4画像**

**v2:** 同じ4状態を維持するなら、**4画像の作り直し**のみ。

**複雑さのポイント:**
1. 4状態×4機能ボタン = 各状態ごとにボタンの有効/無効を変えるか？
   - 推奨: **全状態で4機能ボタンは共通表示**。状態による変更はボタンのハイライト（色変え）程度
   - 理由: 「新着求人」「施設検索」はどのphaseでも使えるべき（ユーザーの自由度向上）
2. postbackデータを受けた時に「現在のphaseに応じて振る舞いを変える」ロジックは、既存の `handleLinePostback()` パターンを踏襲すれば対応可能

**結論:** リッチメニュー画像制作が最大の工数。コード側の切り替えロジックは既存のまま。

### 15. テスト工数（各機能×各フェーズ）

| 機能 | テスト項目数 | 工数見積もり |
|------|-----------|-----------|
| 機能2（新着求人） | 5項目: 新着あり/なし/D1エラー/ページング/postback遷移 | **2時間** |
| 機能3（施設検索） | 8項目: キーワード検索/0件/多数件/ページング/エリア絞り込み/D1エラー/特殊文字/既存phase復帰 | **4時間** |
| 機能4（履歴書AI） | 6項目: 入力済み/未入力/AI成功/AIタイムアウト/テンプレートフォールバック/修正フロー | **2時間** |
| リッチメニュー切り替え | 4項目: 各状態での全ボタン動作確認 | **1時間** |
| 統合テスト | 3項目: 複合遷移(新着→応募→経歴書)/ハンドオフ中のガード/ナーチャリング復帰 | **2時間** |
| **合計** | **26項目** | **約11時間** |

---

## D. 安全な実装順序（5視点）

### 16. フェーズ分けの最適な順序

```
Phase 1（Day 1-2）: 機能4 — 履歴書作成（AI）
  理由: 既存コードの再利用率が最も高い。buildResumeConfirmMessages()に
        導線を追加するだけ。リスク最小。
  成果物: resume_start postbackハンドラ + ミニヒアリング3問

Phase 2（Day 3-5）: 機能2 — 本日の新着求人
  理由: D1クエリ1本追加 + Flex Message生成。既存マッチングUIのパターンを
        流用できる。インデックス追加が前提。
  成果物: newjobs postbackハンドラ + D1クエリ + last_synced_atインデックス

Phase 3（Day 6-9）: 機能3 — 施設検索
  理由: テキスト自由入力のパースが最も複雑。D1性能チューニングも必要。
        Phase 2でD1クエリパターンを確立してから着手。
  成果物: facility_search phaseペア + 2段階検索UI + cityインデックス

Phase 4（Day 10-11）: リッチメニュー画像差し替え + 統合テスト
  理由: 全機能のpostbackデータが確定してから画像を作る。
        LINE Official Account Managerでの設定作業。
  成果物: 4状態×新画像 + env変数更新 + 統合テスト完了
```

### 17. フィーチャーフラグで段階リリースは可能か

**結論: 可能。2つの方法がある。**

**方法A: env変数フラグ（推奨）**
```javascript
// worker.js 冒頭
const FEATURE_FLAGS = {
  NEW_JOBS: env.FF_NEW_JOBS === "true",      // 新着求人
  FACILITY_SEARCH: env.FF_FACILITY_SEARCH === "true", // 施設検索
  RESUME_STANDALONE: env.FF_RESUME === "true", // 履歴書独立起動
};
```
- wrangler.toml の `[vars]` に追加するだけ
- Worker再デプロイなしで `wrangler secret put` で切り替え可能

**方法B: ユーザーID制限（カナリアリリース）**
```javascript
const BETA_USERS = ["U1234...", "U5678..."]; // テスター
if (!BETA_USERS.includes(userId) && !FEATURE_FLAGS.NEW_JOBS) {
  // 新機能をスキップ
}
```

**推奨:** 方法Aで十分。事業規模（月数人のLINE友だち）を考えると、カナリアリリースは過剰。

### 18. ロールバック手順

```bash
# 1. コードのロールバック
git log --oneline -10  # ロールバック先のcommit hashを確認
git revert HEAD         # 直前のcommitを打ち消し
git push origin main && git push origin main:master

# 2. Workerのデプロイ
cd ~/robby-the-match/api
unset CLOUDFLARE_API_TOKEN
npx wrangler deploy --config wrangler.toml

# 3. リッチメニューのロールバック（画像を差し替え済みの場合）
# → LINE Official Account Managerで旧メニュー画像を再設定
# → env変数 RICH_MENU_DEFAULT 等を旧IDに戻す
# → wrangler secret put RICH_MENU_DEFAULT <旧ID>

# 4. D1インデックスは削除不要（パフォーマンスに悪影響なし）
```

**ロールバック時間:** コード+デプロイ 5分 / リッチメニュー画像 15分

### 19. 既存ユーザー（広告経由）への影響を0にする方法

**保証すべきポイント:**
1. **既存の `welcome=see_jobs` postback** はそのまま動作する → 変更しない
2. **ヒアリング中のユーザー** — リッチメニュー画像が変わっても、既存のpostbackデータは互換維持
3. **handoff中のユーザー** — `handoff_guard` (L5808-5817) が新postbackもブロックする → `handoff=ok` 以外は無視されるので安全
4. **ナーチャリング中のユーザー** — Cron配信ロジック (L7152) は新機能と独立

**具体策:**
- 新postbackキー（`newjobs=*`, `facility_search=*`, `resume_start=*`）を追加するだけで、既存キーは一切変更しない
- `handleLinePostback()` の既存分岐の**後**に新分岐を追加（既存マッチが優先される）
- `STATE_CATEGORIES` (L118) に新カテゴリを追加（既存カテゴリは変更しない）

### 20. リッチメニュー画像の切り替えタイミング

**推奨タイミング:**

```
Step 1: 新postbackハンドラをデプロイ（画像はまだ旧版）
  → 新postbackが来ても正しく処理できる状態にする

Step 2: LINE Official Account Managerで新リッチメニュー画像を作成
  → 新メニューIDを取得するが、まだデフォルトに設定しない

Step 3: env変数を新メニューIDに更新
  wrangler secret put RICH_MENU_DEFAULT <新ID>
  wrangler secret put RICH_MENU_HEARING <新ID>
  wrangler secret put RICH_MENU_MATCHED <新ID>
  wrangler secret put RICH_MENU_HANDOFF <新ID>

Step 4: 再デプロイ → 新規followユーザーから新メニューが適用
  ※既存ユーザーは次回のphase遷移時にswitchRichMenu()で自動切り替え
```

**重要:** Step 1→Step 3の順序を守ること。画像を先に変えるとpostbackが未定義のまま飛んでくるリスクがある。

---

## E. LINE技術仕様（5視点）

### 21. リッチメニューのアクション種別（postback/uri/message）の選択

| 機能 | 推奨アクション | 理由 |
|------|-------------|------|
| お仕事探しをスタート | **postback** | 既存実装が `welcome=see_jobs` postback。変更不要 |
| 本日の新着求人 | **postback** | `newjobs=today` → worker.js内で処理。URIだとWorker外にリダイレクトが必要 |
| 施設検索 | **postback** | `facility_search=start` → テキスト入力待ちphaseに遷移 |
| 履歴書作成（AI） | **postback** | `resume_start=standalone` → 既存経歴書フロー起動 |

**message方式を使わない理由:**
- messageは「ユーザーがテキスト送信した」として扱われ、既存のテキスト→postback推定ロジック (L5588) と干渉する
- postbackなら `event.type === "postback"` で明確に分岐可能
- postbackの `displayText` でユーザーのトーク画面には自然なテキストが表示される

### 22. リッチメニューの画像サイズと分割エリアの定義方法

**推奨レイアウト:**

```
画像サイズ: 2500 x 1686 px（大サイズ、2×2分割に最適）

┌───────────────────────┬───────────────────────┐
│ x:0, y:0              │ x:1250, y:0           │
│ w:1250, h:843         │ w:1250, h:843         │
│                       │                       │
│  🔍 お仕事探しを      │  🆕 本日の新着求人     │
│     スタート          │                       │
│                       │                       │
├───────────────────────┼───────────────────────┤
│ x:0, y:843            │ x:1250, y:843         │
│ w:1250, h:843         │ w:1250, h:843         │
│                       │                       │
│  🏥 施設検索          │  📝 履歴書作成(AI)    │
│                       │                       │
│                       │                       │
└───────────────────────┴───────────────────────┘
```

**JSON定義:**
```json
{
  "size": { "width": 2500, "height": 1686 },
  "selected": true,
  "name": "ナースロビー v2 - default",
  "chatBarText": "メニューを開く",
  "areas": [
    {
      "bounds": { "x": 0, "y": 0, "width": 1250, "height": 843 },
      "action": { "type": "postback", "data": "welcome=see_jobs", "displayText": "お仕事を探す" }
    },
    {
      "bounds": { "x": 1250, "y": 0, "width": 1250, "height": 843 },
      "action": { "type": "postback", "data": "newjobs=today", "displayText": "新着求人を見る" }
    },
    {
      "bounds": { "x": 0, "y": 843, "width": 1250, "height": 843 },
      "action": { "type": "postback", "data": "facility_search=start", "displayText": "施設を検索する" }
    },
    {
      "bounds": { "x": 1250, "y": 843, "width": 1250, "height": 843 },
      "action": { "type": "postback", "data": "resume_start=standalone", "displayText": "履歴書を作成する" }
    }
  ]
}
```

### 23. LINE Official Account Managerでの設定手順

```
1. https://manager.line.biz/ にログイン
2. 「トークルーム管理」→「リッチメニュー」→「作成」
3. テンプレートを選択:「大きいテンプレート」→ 2×2グリッド
4. 画像をアップロード（2500x1686px）
5. 各エリアのアクションを設定:
   - 左上: postback → data: "welcome=see_jobs"
   - 右上: postback → data: "newjobs=today"
   - 左下: postback → data: "facility_search=start"
   - 右下: postback → data: "resume_start=standalone"
6. 「表示期間」を設定（常時表示推奨）
7. 保存

⚠️ 注意: LINE Official Account Manager（GUI）では postback アクションを
設定できない場合がある。その場合は Messaging API で直接作成する:

POST https://api.line.me/v2/bot/richmenu
Authorization: Bearer {channel_access_token}
Content-Type: application/json
Body: 上記JSON

→ レスポンスの richMenuId を env変数に設定
→ 画像アップロード:
POST https://api-data.line.me/v2/bot/richmenu/{richMenuId}/content
Authorization: Bearer {channel_access_token}
Content-Type: image/png
Body: <画像バイナリ>
```

**状態別に4回繰り返す必要がある。** スクリプト化推奨:
```bash
python3 scripts/setup_richmenu.py  # 4状態分を一括作成
```

### 24. リッチメニューのユーザー別切り替え（APIが必要か）

**結論: API必須。既に実装済み。**

worker.js `switchRichMenu()` (L3160-3183):
```javascript
POST /v2/bot/user/{userId}/richmenu/{menuId}
```

**既存の切り替えタイミング:**
- followイベント時 → `RICH_MENU_STATES.default` (L5750)
- phaseが変わるたび → `getMenuStateForPhase()` で判定 → 対応するメニューに切り替え

**v2で変更が必要な点: なし。**
- `getMenuStateForPhase()` は phase → state(default/hearing/matched/handoff) のマッピングのみ
- 新phaseを既存stateに割り当てるだけ:
  - `new_jobs_list` → `default`（閲覧系なので）
  - `facility_search_input/result` → `hearing`（入力待ち系なので）
  - `resume_standalone` → `matched`（応募系なので）

### 25. リッチメニューとQuick Replyの共存ルール

**LINE公式仕様:**
- リッチメニューは**常時表示**（トーク画面下部に固定）
- Quick Replyは**メッセージ受信時にのみ表示**（キーボードの上に一時表示）
- **両方同時に表示可能** — 干渉しない

**現行worker.jsの挙動:**
- 全フェーズでQuick Reply付きメッセージを返信 (例: L3982 `qrItem("新着を待つ", "matching_browse=done")`)
- リッチメニューはフェーズに応じて切り替え

**v2での注意点:**
1. リッチメニューの「施設検索」をタップ → Quick Replyで「エリアを選んでください」と表示 → **ユーザーがリッチメニューを再タップ**した場合
   - Quick Replyは消えず、新しいpostbackが処理される
   - → phase管理で「施設検索中にリッチメニューの別ボタンを押した」ケースを考慮する必要あり
   - → 対策: phase遷移時にprevPhaseを記録し、中断復帰可能にする（既存パターン踏襲）

2. Quick Replyのアクション数制限: **最大13個**
   - 現行は最大6個程度使用 → 余裕あり

3. リッチメニューのボタンが増えてもQuick Replyの役割は変わらない
   - リッチメニュー = **グローバルナビゲーション**（いつでもアクセス可能）
   - Quick Reply = **コンテキストナビゲーション**（今のフェーズに適した選択肢）

---

## 総合判定

| 機能 | 実現性 | 工数 | リスク | 優先度 |
|------|-------|------|-------|-------|
| 機能1（既存） | ✅ 実装済み | 0 | なし | — |
| 機能4（履歴書AI） | ✅ 容易 | 1-2日 | 低 | **Phase 1** |
| 機能2（新着求人） | ✅ 可能 | 2-3日 | 低-中 | **Phase 2** |
| 機能3（施設検索） | ⚠️ 可能（性能注意） | 3-4日 | 中 | **Phase 3** |
| リッチメニュー画像 | ✅ 可能 | 1日 | 低 | **Phase 4** |

**総工数: 7-10日**（テスト含む）

**最大リスク:** 機能3の施設検索におけるD1フルスキャン性能。`city` インデックス追加 + 2段階検索UIで対策可能。

**推奨:** Phase 1（履歴書AI）から着手し、既存コード資産を最大活用。Phase 2-3は並行してD1インデックス整備を進める。
