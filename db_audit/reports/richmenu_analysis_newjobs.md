# 「本日の新着求人」機能 — 25視点 設計書

> 作成日: 2026-04-06
> 対象: ナースロビー LINE Bot / D1 jobs / hellowork パイプライン

---

## 現状の整理

| 項目 | 値 |
|------|-----|
| D1 jobs 件数 | 2,936件 |
| 更新頻度 | 毎朝06:30 cron (`pdca_hellowork.sh`) |
| 更新方式 | **DROP TABLE → CREATE → INSERT**（全件洗い替え） |
| synced_at | 全件同一タイムスタンプ（差分判別不可） |
| 差分検出 | `hellowork_diff.py` が **JSONスナップショット**で前日比較済み |
| スナップショット保管 | `data/hellowork_history/YYYY-MM-DD.json` |
| 既存ナーチャリング | Day3/7/14 Push通知あり（「新着が出ています」は固定文言で実際の新着とは非連動） |

**重要な発見**: `hellowork_diff.py` は既にkjno単位の差分（new/removed/continuing）を正確に算出している。ただしその結果はSlack報告のみで、D1やWorkerには一切反映されていない。

---

## A. データ設計（10視点）

### 1. 「新着」の定義

**推奨定義**: 前日のスナップショットに存在せず、本日初めて出現したkjno。

| 候補 | 判定 |
|------|------|
| 前日比で新しいkjno | **採用** — hellowork_diff.pyが既に算出 |
| 内容が更新された求人（給与変更等） | 不採用 — ハローワークAPIは更新検知不可（kjnoが同じまま内容だけ変わる） |
| synced_atの差分 | 不採用 — DROP→再INSERTのため全件同一値 |

**結論**: `hellowork_diff.py` の `new_kjnos = today_kjnos - yesterday_kjnos` をそのまま使う。追加実装コストほぼゼロ。

---

### 2. 差分検出の方法

**現状で最も合理的な方法**: hellowork_diff.py のスナップショット比較をそのまま活用。

```
data/hellowork_history/2026-04-05.json  ← 前日kjnoセット
data/hellowork_history/2026-04-06.json  ← 本日kjnoセット
差分 = 本日 - 前日
```

**別テーブル方式（不採用の理由）**: D1にjobs_historyテーブルを持つとD1容量が膨張する（2,936件 × 30日 = 88,080行）。JSONスナップショットは既に動いており、追加コストゼロ。

---

### 3. DROP→再INSERTを変えるべきか？

**結論: 変えない。ただしD1に `first_seen_at` カラムを追加する。**

| 方式 | メリット | デメリット |
|------|---------|-----------|
| 現状維持（DROP→INSERT） | 実装シンプル、データ整合性保証 | 差分取れない |
| UPSERT方式 | first_seen_at保持可能 | 2,936件のUPSERTは遅い、消えた求人の扱いが複雑 |
| **DROP→INSERT + first_seen_at注入** | シンプルかつ新着判別可能 | diffスクリプト結果を注入する1ステップ追加 |

**採用案**: hellowork_to_d1.py の INSERT時に `first_seen_at` を注入。値の算出は hellowork_diff.py のスナップショット履歴から逆算。

```python
# 疑似コード
history_kjnos = load_all_history_kjnos()  # 過去スナップショットからkjno→初出日マップ
for job in jobs:
    job["first_seen_at"] = history_kjnos.get(job["kjno"], today)
```

---

### 4. first_seen_at（初出日）カラム

**追加する（必須）。**

- 用途: 「新着」バッジ表示の判定（first_seen_at = 本日 → 新着）
- Worker側で `WHERE first_seen_at = DATE('now')` でフィルタ可能
- ユーザーが「新着求人を見る」と言った時のSQLフィルタに直結

---

### 5. last_seen_at（最終確認日）カラム

**追加する（推奨）。**

- 用途: 掲載終了の検出に使う
- DROP→再INSERTでは本日の値しか入らないが、掲載終了検出は別途diffで対応
- D1上では `last_seen_at = synced_at` と同義になるため、実質 synced_at で代用可能

**結論**: synced_at を last_seen_at として読み替える。新カラム追加は不要。

---

### 6. 消えた求人（掲載終了）の検出

**必要（ただしD1外で処理）。**

hellowork_diff.py の `removed_kjnos` が既にこれを算出している。

| 用途 | 対応 |
|------|------|
| 掲載終了求人を非表示にする | DROP→再INSERTで自動的に消える（対応済み） |
| 「応募済み求人が消えた」通知 | entry.interestedFacility のkjnoが消えたらPush通知 |
| 統計（掲載日数の平均等） | hellowork_history から算出可能 |

**即時対応**: 応募関心を示した求人の掲載終了通知は Phase 2 以降。現時点では不要。

---

### 7. ユーザーごとの「既読」管理

**不要（現時点では）。**

| 理由 |
|------|
| LINE Botの会話フロー上、新着は「今日の新着○件」→ 条件に合うものを5件表示、で完結 |
| 既読管理にはKVにuser別の `seen_kjnos` セットを保持する必要があり、KV書き込み回数が爆増 |
| ユーザー数が少ない段階（LINE友だち < 100人）では過剰設計 |

**将来対応**: LINE友だち500人超になったら `entry.lastNewJobsViewedAt` タイムスタンプを追加し、それ以降の新着のみ表示。

---

### 8. 新着0件の日のフォールバック

**発生頻度の推定**: hellowork_diff.py の過去実績によるが、ハローワークは毎日更新されるため0件は稀（週末を除く）。

| 0件時の対応案 | 判定 |
|-------------|------|
| 「今日は新着なし」+「おすすめ求人」表示 | **採用** |
| 直近3日間の新着をまとめて表示 | **採用（併用）** |
| 「条件を広げてみませんか？」提案 | Phase 2 |

```
新着0件の場合:
「今日は新しい求人の更新はありませんでした。
 直近3日間で○件の新着がありますよ。
 見てみますか？」
→ Quick Reply: [直近の新着を見る] [条件を変えて探す]
```

---

### 9. Push通知の要否と頻度

**条件付きで送る。**

| 条件 | 通知 |
|------|------|
| nurtureSubscribed = true + 条件一致の新着あり | **送る（1日1回、10:00 JST）** |
| nurtureSubscribed = null | 送らない（明示的オプトインのみ） |
| nurtureSubscribed = false | 絶対送らない |
| 新着0件 | 送らない |

**既存ナーチャリング（Day3/7/14）との統合**:
- ナーチャリングPushは「新着がある」と嘘を言っている現状を改善
- nurtureSubscribed = true のユーザーには、ナーチャリングの代わりに実際の新着Pushを送る
- これにより「新着出ています」が事実になる

**LINE Push通知コスト**: 無料メッセージ枠（月200通）内で運用。友だち50人 × 月20日 = 1,000通は超過するため、S/Aランクの新着のみに限定する。

---

### 10. 新着求人のスコアリング

**既存スコアリングをそのまま使う。**

hellowork_rank.py のスコア（S/A/B/C/D）は新着求人にも適用済み（全件ランク付けしてからD1に投入するため）。

**新着通知に含める求人のフィルタ**:
- Push通知: S/Aランクの新着のみ（ノイズ防止）
- Bot内表示: 全ランクの新着を表示（ユーザーが能動的に見る場合）

---

## B. UX設計（10視点）

### 11. 表示形式

**LINE Flex Message カード形式（既存のマッチング結果と同一フォーマット）。**

| 形式 | 判定 | 理由 |
|------|------|------|
| カルーセル（横スワイプ） | **採用** | 既存 `generateLineMatching()` のFlex Messageをそのまま流用 |
| リスト（縦並び） | 不採用 | LINE上で見づらい |
| 件数だけ | Push通知のサマリには使う | 「今日は横浜エリアにS/Aランク新着3件！」 |

```
Push通知（テキスト）:
「横浜エリアに新着3件の看護師求人が出ました！
 見てみますか？」
→ Quick Reply: [新着を見る] [あとで]

↓「新着を見る」タップ

Flex Message カルーセル（既存マッチングカードと同じ形式）
```

---

### 12. 「新着○件」バッジ

**LINE標準のバッジ機能は存在しない。**

| 代替案 | 実現性 |
|--------|--------|
| リッチメニューの画像を動的に変更（「新着3件」テキスト入り画像） | 技術的に可能だが画像生成が必要。コスト高。 |
| リッチメニュータップ時に件数を応答 | **採用** — 最小コスト |
| Push通知で件数を伝える | 採用（上記#9と統合） |

**採用案**: リッチメニューに「本日の新着」ボタンを追加。タップすると `postback: action=new_jobs` → Workerが本日の新着件数を即応答。

---

### 13. 新着を見た後の導線

```
[新着求人カルーセル表示]
  ├→「この求人が気になる」→ job_detail → consultation → handoff
  ├→「他の新着も見る」→ 次の5件表示（ページング）
  ├→「条件を変えて探す」→ il_area（intake再開）
  └→「今日はいいです」→ nurture_warm
```

既存の `matching_preview` / `matching_browse` フローをほぼそのまま流用。差分は `generateLineMatching()` に `WHERE first_seen_at = ?` フィルタを追加するだけ。

---

### 14. 前回の条件を覚えて絞り込むか？

**覚える（既に覚えている）。**

KV上の `entry.area` / `entry.workStyle` / `entry.workplace` はintake_light回答後に永続保持されている。新着表示時にこの条件でフィルタする。

```sql
SELECT * FROM jobs
WHERE first_seen_at = '2026-04-06'
  AND area = '横浜'            -- entry.area
  AND emp_type LIKE '%常勤%'   -- entry.workStyle
ORDER BY score DESC
LIMIT 5
```

---

### 15. 条件を聞くか、いきなり全件か？

| ユーザー状態 | 挙動 |
|------------|------|
| intake_light完了済み（area/workStyle あり） | **条件で絞り込んだ新着を表示** |
| intake未完了（area = null） | 「まずエリアを教えてください」→ il_area |
| intake済みだが新着0件 | 条件を外して全新着のサマリ表示 |

---

### 16. 1日の理想的な新着件数

**hellowork_diff.py の実績から逆算すべき。** 推定値:

| 全体 | ユーザーの条件絞り込み後 |
|------|----------------------|
| 30〜100件/日（神奈川+東京+埼玉+千葉） | 3〜10件/日 |

ユーザー体験として:
- **3〜5件**: 理想的。「厳選感」がある
- **0件**: 許容（フォールバック対応済み）
- **10件超**: 多すぎ。S/Aランクのみに絞る
- **20件超**: 「新着が多すぎて見きれない」→ 自動的にSランクのみに絞る

---

### 17. 週次サマリー

**有効。ただし Phase 2。**

| 配信タイミング | 内容 |
|-------------|------|
| 毎週月曜 10:00 | 「先週の新着○件。あなたの条件に合う求人は○件でした」 |

既存の nurture cron（`0 1 * * *`）に週次判定を追加すれば実装可能。現時点ではDay3/7/14のナーチャリングで十分カバーされている。

---

### 18. LINE Push通知のタイミング

| 時刻 | 理由 |
|------|------|
| **10:00 JST** | 看護師の日勤開始後の休憩時間帯。夜勤明けの帰宅時間帯 |
| 06:30は不可 | データ更新直後はまだ早い。cron完了は07:00頃 |
| 12:00も候補 | 昼休み。ただし10:00で十分 |

**既存cronとの統合**: `0 1 * * *`（10:00 JST）のナーチャリングcronに新着Push配信を統合。

---

### 19. 「この求人を保存」機能

**不要（現時点では）。**

| 理由 |
|------|
| `entry.interestedFacility` が既に「気になる求人」を1件保存している |
| LINEのトーク履歴自体が「保存」の代替になっている |
| お気に入りリスト機能はユーザー数100人超になってから |

---

### 20. 新着がない日の体験

```
ユーザー: 「新着求人」タップ（リッチメニュー）
Bot:
  「今日は新しい求人の更新はありませんでした。

   でも、あなたの条件に合う求人は
   現在○件あります！

   見てみますか？」

  Quick Reply:
  [おすすめ求人を見る] [条件を変えて探す] [大丈夫です]
```

- 「おすすめ求人を見る」→ 既存のマッチングフロー（generateLineMatching）
- 「条件を変えて探す」→ il_area
- 「大丈夫です」→ nurture_warm

---

## C. 実装（5視点）

### 21. hellowork_to_d1.py の改修

**変更点**: `first_seen_at` カラムの追加 + スナップショット履歴からの初出日注入。

```python
# 追加する処理（build_sql関数内）

def load_first_seen_map():
    """過去のスナップショットからkjno→初出日のマップを構築"""
    first_seen = {}
    if not HISTORY_DIR.exists():
        return first_seen
    for f in sorted(HISTORY_DIR.glob("*.json")):
        date_str = f.stem  # "2026-04-05"
        snap = json.loads(f.read_text())
        for j in snap.get("jobs", []):
            kjno = j.get("kjno")
            if kjno and kjno not in first_seen:
                first_seen[kjno] = date_str
    return first_seen

# CREATE TABLE に追加:
#   first_seen_at TEXT,
# CREATE INDEX IF NOT EXISTS idx_jobs_first_seen ON jobs(first_seen_at);

# INSERT時:
#   first_seen_at = first_seen_map.get(kjno, today)
```

**工数見積**: 30分。テスト込みで1時間。

---

### 22. worker.js の新phase設計

**新規追加するphase**: なし。既存フローに統合。

**新規追加する関数**:

```javascript
// generateLineNewJobs(entry, env) — 新着求人表示
async function generateLineNewJobs(entry, env) {
  if (!env?.DB) return null;

  const today = new Date().toISOString().slice(0, 10); // "2026-04-06"
  const baseArea = (entry.area || '').replace('_il', '');

  let sql = `SELECT * FROM jobs WHERE first_seen_at = ?`;
  const params = [today];

  // エリアフィルタ（entry.areaがある場合）
  if (baseArea && baseArea !== 'undecided') {
    const cities = AREA_CITY_MAP[baseArea] || [];
    if (cities.length > 0) {
      sql += ` AND (${cities.map(() => 'work_location LIKE ?').join(' OR ')})`;
      cities.forEach(c => params.push(`%${c}%`));
    } else {
      sql += ' AND area = ?';
      params.push(baseArea);
    }
  }

  sql += ' ORDER BY score DESC LIMIT 5';
  const result = await env.DB.prepare(sql).bind(...params).all();

  if (!result?.results?.length) {
    // 新着0件フォールバック
    return buildNoNewJobsMessage(entry, env);
  }

  // 既存のFlex Messageカード形式で返す（generateLineMatchingと同じ形式）
  return buildNewJobsCarousel(result.results, entry);
}
```

**postback追加**:
```javascript
// リッチメニュー or テキスト「新着求人」のハンドリング
if (data === "action=new_jobs" || textLower === "新着求人" || textLower === "新着") {
  const newJobsMsg = await generateLineNewJobs(entry, env);
  // 応答を返す
}
```

**工数見積**: 2時間。既存のgenerateLineMatchingのコードを80%流用。

---

### 23. D1テーブルの変更（マイグレーション）

**方式**: hellowork_to_d1.py が毎日DROP→CREATEするため、マイグレーション不要。CREATE TABLE文を変更するだけ。

```sql
CREATE TABLE jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kjno TEXT UNIQUE,
  employer TEXT NOT NULL,
  title TEXT,
  rank TEXT,
  score INTEGER,
  area TEXT,
  prefecture TEXT,
  work_location TEXT,
  salary_form TEXT,
  salary_min INTEGER,
  salary_max INTEGER,
  salary_display TEXT,
  bonus_text TEXT,
  holidays INTEGER,
  emp_type TEXT,
  station_text TEXT,
  shift1 TEXT,
  shift2 TEXT,
  description TEXT,
  welfare TEXT,
  score_sal INTEGER,
  score_hol INTEGER,
  score_bon INTEGER,
  score_emp INTEGER,
  score_wel INTEGER,
  score_loc INTEGER,
  synced_at TEXT,
  first_seen_at TEXT    -- ★追加: この求人が初めて出現した日（YYYY-MM-DD）
);

-- ★追加: 新着検索用インデックス
CREATE INDEX IF NOT EXISTS idx_jobs_first_seen ON jobs(first_seen_at);
```

---

### 24. cronの変更

**変更なし。** 既存の `pdca_hellowork.sh` の実行順序で対応可能。

```
06:30 pdca_hellowork.sh
  Step 1:   hellowork_fetch.py      ← API取得
  Step 1.5: hellowork_diff.py       ← スナップショット保存 + 差分算出 ★ここでfirst_seenマップが確定
  Step 2:   hellowork_rank.py       ← ランク付け
  Step 3:   hellowork_to_jobs.py    ← worker.js EXTERNAL_JOBS更新
  Step 3.5: hellowork_to_d1.py      ← D1全件投入（★first_seen_at注入）
  Step 4:   git commit + push
  Step 5:   wrangler deploy

10:00 JST (0 1 * * * UTC): scheduled cron
  ← 既存ナーチャリング配信に「新着Push」を統合
```

**ポイント**: hellowork_diff.py（Step 1.5）が hellowork_to_d1.py（Step 3.5）より先に実行されるため、first_seenマップは必ず最新状態でD1に注入される。既存の実行順序が完璧に整合。

---

### 25. テスト方法

#### a. ローカルテスト（hellowork_to_d1.py --local）

```bash
# 1. first_seen_at が正しく注入されるか確認
python3 scripts/hellowork_to_d1.py --local
sqlite3 data/hellowork_jobs.sqlite "SELECT first_seen_at, COUNT(*) FROM jobs GROUP BY first_seen_at"
# 期待: 大半が過去日付、新着分のみ本日日付

# 2. 新着フィルタが機能するか
sqlite3 data/hellowork_jobs.sqlite "SELECT COUNT(*) FROM jobs WHERE first_seen_at = date('now')"
# 期待: hellowork_diff.py のnew_countと一致
```

#### b. Worker ローカルテスト

```bash
cd api && npx wrangler dev --config wrangler.toml
# → curl で /api/line-webhook に「新着求人」テキストを送信
# → Flex Message応答を確認
```

#### c. 差分整合性テスト

```bash
# hellowork_diff.py の new_count と D1 の first_seen_at = today の件数が一致するか
python3 scripts/hellowork_diff.py --dry-run 2>&1 | grep "新着"
python3 scripts/hellowork_to_d1.py --local
sqlite3 data/hellowork_jobs.sqlite \
  "SELECT COUNT(*) FROM jobs WHERE first_seen_at = '$(date +%Y-%m-%d)'"
```

#### d. Push通知テスト

```bash
# nurtureSubscribed = true のテストユーザーに新着Pushが届くか
# → Worker scheduled cron をローカルで発火
cd api && npx wrangler dev --config wrangler.toml --test-scheduled
```

#### e. 新着0件テスト

```bash
# 全求人のfirst_seen_atを昨日に設定してテスト
sqlite3 data/hellowork_jobs.sqlite \
  "UPDATE jobs SET first_seen_at = date('now', '-1 day')"
# → 「新着求人」をリクエスト → フォールバックメッセージを確認
```

---

## 実装優先順位

| 優先度 | タスク | 工数 |
|--------|--------|------|
| P0 | hellowork_to_d1.py に first_seen_at 追加 | 30min |
| P0 | worker.js に generateLineNewJobs 追加 | 2h |
| P0 | リッチメニュー or postback に「新着求人」追加 | 30min |
| P1 | 新着0件フォールバック実装 | 30min |
| P1 | ナーチャリングcronに新着Push統合 | 1h |
| P2 | 週次サマリー | 1h |
| P2 | 「応募関心求人の掲載終了」通知 | 2h |

**合計工数: P0 = 3時間、P0+P1 = 4.5時間、全体 = 7.5時間**

---

## リスクと注意点

1. **hellowork_history が存在しない日**: 差分が取れないため全件が「新着」扱いになる。初回実行時は前日スナップショットがあることを確認
2. **LINE Push通知の無料枠**: 月200通。新着Push開始前にユーザー数 × 配信日数を試算
3. **D1 first_seen_at の精度**: スナップショットが欠損した日があると、その日に出現した求人のfirst_seen_atが翌日以降にずれる。許容範囲
4. **ハローワークAPI障害時**: hellowork_fetch.py が失敗すると差分0件になる。既存のエラーハンドリング（Slack通知）で対応済み
