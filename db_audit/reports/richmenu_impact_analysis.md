# リッチメニュー3機能追加 — 影響分析レポート

> 調査対象: `api/worker.js` (7,348行)
> 調査日: 2026-04-06

---

## 1. 追加すべきコードの正確な挿入位置（行番号）

### A. Postbackハンドラ（handleLinePostback関数）

- **関数範囲**: L5062〜L5443
- **最後のelse節**: L5428〜L5440（`params.has("prep")`）
- **挿入位置: L5440の`}`の後、L5442の`return nextPhase;`の前**

```
L5440  }          ← prep ハンドラの閉じ括弧
--- ★ ここに richmenu postbackハンドラを追加 ---
L5442  return nextPhase;
```

提案コード構造:
```javascript
  // リッチメニュー: 新着求人
  else if (params.has("rm")) {
    const val = params.get("rm");
    entry.unexpectedTextCount = 0;
    if (val === "new_jobs") {
      // intake済みならそのまま新着検索、未intakeならil_area開始
      if (entry.area && entry.workStyle) {
        nextPhase = "rm_new_jobs";
      } else {
        nextPhase = "il_area";
      }
    } else if (val === "consult") {
      nextPhase = "handoff_phone_check";
    } else if (val === "resume") {
      nextPhase = "rm_resume_start";
    }
  }
```

### B. buildPhaseMessage関数（switch文）

- **関数範囲**: L3524〜L4299
- **最後のcase（default前）**: L4275〜L4294（`case "handoff"`）
- **default**: L4296〜L4298
- **挿入位置: L4294の`}`の後、L4296の`default:`の前**

```
L4294    }          ← case "handoff" の閉じ括弧
--- ★ ここに新しいcase文を追加 ---
L4296    default:
```

追加するcase:
- `case "rm_new_jobs":` — D1 jobsから新着求人を検索して表示
- `case "rm_resume_start":` — 履歴書作成の導入メッセージ

### C. getMenuStateForPhase関数

- **関数範囲**: L3144〜L3158
- **変更不要** — 新phaseは既存のmenuState分類に収まる:
  - `rm_new_jobs` → `matched` or `default`（ユーザーのintake状態による）
  - `rm_resume_start` → `matched`（L3149の配列に追加）
  - `rm=consult` → `handoff_phone_check`に遷移するので既存で対応

ただし `rm_new_jobs` を `matched` グループに含めたい場合:
- **L3148〜3150の配列に `"rm_new_jobs", "rm_resume_start"` を追加**

### D. Phase遷移ハンドラ（メインイベントループ）

- **範囲**: L6090〜L6146（nextPhaseに応じたentry.phase設定+メッセージ生成）
- **最後の名前付きelse if**: L6126（`nextPhase === "handoff"`）
- **汎用フォールバック**: L6144（`else if (nextPhase)`）
- **挿入位置: L6143の`}`の後、L6144の`else if (nextPhase)`の前**

```
L6143        }
--- ★ ここに rm_new_jobs / rm_resume_start の遷移ロジックを追加 ---
L6144        } else if (nextPhase) {
```

**ただし**: L6144の汎用フォールバックが `buildPhaseMessage(nextPhase)` を呼ぶので、buildPhaseMessageにcase文を追加するだけで **ここの変更は省略可能**。明示的に特別処理が必要な場合のみ追加。

### E. PHASE_FLOW_LIGHT（フロー定義）

- **範囲**: L2860〜L2876
- **変更の必要性**: 低。リッチメニュー機能はフロー途中に挿入するのではなく、独立した「横道」として動作させるべき。PHASE_FLOW_LIGHTはintake_light→handoffの本線フローなので **変更不要**。

### F. エントリ初期状態

- **範囲**: L3300〜L3339
- 新しいフィールドが必要な場合のみ追加（例: `lastNewJobsViewedAt: null`）
- **挿入位置: L3339の後**

---

## 2. 触ってはいけないコードの範囲

| 範囲 | 理由 |
|------|------|
| L4463〜L4560 `generateLineMatching()` | 既存のマッチングロジック。新着求人はこの関数を**呼び出す**が改変しない |
| L4302〜L4395 `buildTemplateResume()` + `buildResumeConfirmMessages()` | 既存の履歴書生成。流用するが改変しない |
| L3424〜L3477 `generateAnonymousProfile()` | 匿名プロフィール生成。career_sheetフロー専用 |
| L3160〜L3183 `switchRichMenu()` | LINE API呼び出し。変更不要 |
| L5062〜L5440 既存のpostbackハンドラ全体 | else-if連鎖の既存分岐は触らない |
| L6126〜L6143 handoffフェーズ遷移 | Slack通知・KV書き込み含む複雑なロジック |

---

## 3. 新しいpostbackキー名とphase名の提案

### Postbackキー（`params.has()` で使用）

| キー | 値 | 用途 |
|------|-----|------|
| `rm` | `new_jobs` | リッチメニュー: 新着求人 |
| `rm` | `consult` | リッチメニュー: 担当に相談 |
| `rm` | `resume` | リッチメニュー: 履歴書作成 |
| `rm_nj` | `more` / `detail` / `save` | 新着求人の追加アクション |
| `rm_rs` | `start` / `skip` | 履歴書作成の追加アクション |

**理由**: 1つの`rm`キーに集約することで、既存のpostback名前空間（`il_*`, `match`, `welcome`等）と衝突しない。

### Phase名

| Phase | 説明 |
|-------|------|
| `rm_new_jobs` | 新着求人表示（D1 jobsからsynced_at降順で取得） |
| `rm_resume_start` | 履歴書作成の導入（intake未完了→ヒアリング誘導、完了→buildResumeConfirmMessages呼び出し） |

**`rm=consult`は新Phase不要** — 既存の`handoff_phone_check`に直接遷移させる。

### LINE Postback data文字列

リッチメニューのaction設定:
```
新着求人:   postback data="rm=new_jobs"
担当に相談: postback data="rm=consult"
履歴書作成: postback data="rm=resume"
```

---

## 4. 既存コードとの衝突リスク

### 低リスク
- **`rm`キーは未使用** — 既存のpostbackキー（`il_pref`, `il_area`, `match`, `welcome`, `consult`, `resume`, `sheet`, `prep`等）と衝突なし
- **Phase名`rm_*`は未使用** — 既存phase名と衝突なし

### 中リスク
- **「担当に相談」→ `handoff_phone_check`** は既存フローと同じ遷移先。ただし `entry.handoffRequestedByUser = true` のセットが L6091 でのみ行われているため、**リッチメニュー経由でもこのフラグをセットする処理が必要**。忘れるとSlack通知のハンドオフ理由が「自動判定」になる
- **「履歴書作成」→ intake未完了ユーザー** の場合、experience/strengths/change等がnullで `buildTemplateResume()` が「不明」だらけの履歴書を生成する。**intake完了チェックが必須**

### 要注意
- **LINE Reply API 5メッセージ制限** — `buildResumeConfirmMessages()` は内部でslice(0, 5)しているが、リッチメニューから呼ぶ場合に前段メッセージを追加すると超過する可能性あり
- **リッチメニュー切り替えタイミング** — `rm_new_jobs` phaseに遷移した際、`getMenuStateForPhase()` がdefaultを返す可能性。意図的にmatchedメニューを表示したい場合はL3148の配列に追加が必要

---

## 5. career_sheet流用可能範囲

### 完全流用可能

| 関数 | 行 | 流用方法 |
|------|-----|----------|
| `buildTemplateResume(entry)` | L4302〜L4336 | そのまま呼び出し。entryにqualification/experience/strengths等があれば動作 |
| `buildResumeConfirmMessages(entry, env)` | L4339〜L4395 | そのまま呼び出し。AI生成→テンプレートフォールバック→確認Quick Reply付き |
| `splitText(text, maxLen)` | L3185〜 | テキスト分割ユーティリティ |

### 条件付き流用

| 関数 | 条件 |
|------|------|
| `generateAnonymousProfile(entry)` | L3424。履歴書ではなく「病院確認用プロフィール」なので、目的が異なる。履歴書作成には`buildTemplateResume`を使うべき |
| `callLineAI(prompt, [], env)` | AI経歴書生成で内部使用。直接呼ぶ必要はなく、`buildResumeConfirmMessages`経由で自動的に使われる |

### 流用不可（新規実装が必要）

| 機能 | 理由 |
|------|------|
| intake未完了時の誘導メッセージ | 現在のcareer_sheetフローはapply_consent経由なのでintake完了が前提 |
| 新着求人のD1クエリ | 既存の`generateLineMatching()`はscore順。新着は`synced_at DESC`が必要 |

### 推奨実装パターン

```
rm=resume → intake完了チェック
  ├─ 完了: buildResumeConfirmMessages(entry, env) をそのまま呼ぶ
  └─ 未完了: 「まず簡単な質問に答えてね」→ il_area に遷移
```

---

## 6. D1テーブルの変更要否

### 変更不要

- **jobsテーブル**: `synced_at`カラムが既に存在（実データ: `2026-04-09 06:48:38`、3,096件）
- 新着求人は `ORDER BY synced_at DESC LIMIT 5` で取得可能
- スキーマ上の`last_synced_at`とは別に`synced_at`カラムが実テーブルに存在（schema.sqlと実DBに乖離あり。migration時に追加されたと推定）

### 新着求人クエリ案

```sql
SELECT kjno, employer, title, salary_display, station_text, emp_type, synced_at
FROM jobs
WHERE prefecture = ? AND synced_at >= date('now', '-7 days')
ORDER BY synced_at DESC
LIMIT 5 OFFSET ?
```

- エリアフィルタは既存の`generateLineMatching()`のロジック（L4490〜L4505）を流用
- ユーザーのintake条件（area/workStyle/department）があれば追加フィルタ

### facilitiesテーブル: 変更不要

### KV (LINE_SESSIONS): 変更不要
- 既存のentryオブジェクトに`lastNewJobsViewedAt`等を追加するだけでKVスキーマ変更は不要（JSONシリアライズ）

---

## 7. 実装優先度と工数見積もり

| 機能 | 優先度 | 工数 | 備考 |
|------|--------|------|------|
| 担当に相談 | ★★★ | 小（5行） | 既存handoff_phone_checkへの直接遷移のみ |
| 新着求人 | ★★★ | 中（50-80行） | D1クエリ新規 + buildPhaseMessage case追加 |
| 履歴書作成 | ★★ | 小（20-30行） | buildResumeConfirmMessages流用 + intake未完了チェック |

### 総変更行数の見積もり: 約100〜120行追加、既存コード変更0行

---

## 8. 挿入位置サマリ

| 変更箇所 | 行番号 | 追加/変更 |
|----------|--------|-----------|
| handleLinePostback: rm handler | L5440後 | 追加（15-20行） |
| buildPhaseMessage: rm_new_jobs | L4294後 | 追加（30-50行） |
| buildPhaseMessage: rm_resume_start | L4294後 | 追加（15-20行） |
| getMenuStateForPhase: matched配列 | L3148 | 変更（2語追加） |
| Phase遷移ハンドラ | L6143後（任意） | 汎用フォールバックL6144で対応可能なら不要 |
| エントリ初期状態 | L3339後（任意） | `lastNewJobsViewedAt: null` 追加 |
| PHASE_FLOW_LIGHT | 変更不要 | — |
| D1テーブル | 変更不要 | — |
