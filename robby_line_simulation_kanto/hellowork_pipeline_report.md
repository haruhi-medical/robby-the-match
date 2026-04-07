# ハローワーク求人パイプライン 全体像レポート

調査日: 2026-04-06

## 1. アーキテクチャ概要

### 言語/フレームワーク
- **Python 3**（標準ライブラリのみ、外部依存なし）
- **Bash**（cronオーケストレーション）
- **Cloudflare Worker**（worker.js — 求人データの配信先）

### DB/ストレージ
- **ファイルベース（JSON）** — データベース不使用
  - `data/hellowork_nurse_jobs.json` — API生データ
  - `data/hellowork_ranked.json` — ランク付きデータ
  - `api/worker.js` — EXTERNAL_JOBSオブジェクト（Cloudflare Workerに埋め込み）
- **ログ**: `logs/hellowork_fetch.log`

### 全体フロー図（テキスト）
```
[ハローワーク求人情報提供API]
       │ POST (XML)
       ▼
hellowork_fetch.py (--all-prefectures)
  東京/神奈川/埼玉/千葉の4県を取得
  看護師フィルタ適用
       │
       ▼
data/hellowork_nurse_jobs.json (生データ)
       │
       ▼
hellowork_diff.py (差分分析・前日比較)
       │
       ▼
hellowork_rank.py (スコアリング+ランク分け)
       │
       ▼
data/hellowork_ranked.json (ランク付きデータ)
       │
       ▼
hellowork_to_jobs.py (worker.js更新)
       │
       ▼
api/worker.js EXTERNAL_JOBS (JS埋め込み)
       │
       ▼
git commit + push (自動)
       │
       ▼
wrangler deploy --config wrangler.toml (自動)
       │
       ▼
Slack通知 (#claudecode)
```

---

## 2. データ取得（hellowork_fetch.py）

### APIエンドポイント
- **ベースURL**: `https://teikyo.hellowork.mhlw.go.jp/teikyo/api/2.0`
- **認証**: `POST /auth/getToken?id={id}&pass={pass}` → トークン発行
- **データ一覧**: `POST /kyujin?token={token}` → データID一覧取得
- **ページ取得**: `POST /kyujin/{DATA_ID}/{page}?token={token}` → 求人データ（XML）
- **トークン破棄**: `POST /auth/delToken?token={token}`

### 検索条件・パラメータ
- **DATA_ID**: 4県対応
  - `M113` = 東京都
  - `M114` = 神奈川県（デフォルト）
  - `M111` = 埼玉県
  - `M112` = 千葉県
- **`--all-prefectures`** フラグで4県全取得（cronではこれを使用）
- **User-Agent**: `HaruiMedical-HWClient/1.0`
- **認証情報**: `.env`の`HELLOWORK_USER_ID` / `HELLOWORK_PASSWORD`

### 看護師フィルタ（is_nurse_job）
- **除外**: 看護助手、看護補助、動物、獣医、リハビリ助手、派遣求人
- **第1優先（職種名）**: 看護師、看護職、看護業務、看護スタッフ、ナース、准看護、保健師、助産師、訪問看護
- **第2優先（必要資格）**: 看護師、准看護、保健師、助産師

### 出力ファイル
- **`data/hellowork_nurse_jobs.json`**
  - 構造: `{ fetched_at, data_ids, prefectures, total_nurse, jobs: [...] }`
  - 各求人: 求人番号、事業所情報、職種・仕事内容、勤務地、雇用条件、給与、勤務時間、休日、資格、福利厚生（計40+フィールド）
- **オプション**: `--save-raw` で生XMLも `data/hellowork_raw/` に保存

### エラーハンドリング
- リクエストごとにリトライ2回（5秒間隔）
- HTTP 503: メンテナンス中メッセージ（0-6時 or 月末21:30-翌6時）
- 空レスポンス時: トークン再取得して1回リトライ
- **3ページ連続失敗で中断**
- レートリミット対策: ページ間に2秒スリープ

---

## 3. ランキング・分類（hellowork_rank.py）

### 入力/出力
- **入力**: `data/hellowork_nurse_jobs.json`
- **出力**: `data/hellowork_ranked.json`
  - 構造: `{ ranked_at, total_scored, rank_counts: {S,A,B,C,D}, jobs: [...] }`

### 追加フィルタ（is_target_nurse_job）
- 職種名にNURSE_KEYWORDS（看護師/看護職/ナース/訪問看護）を含むこと
- NOISE_KEYWORDS（看護助手、事務、ケアマネ、理学療法、歯科、介護福祉士、薬剤等）を含まないこと

### スコアリング配点（6軸、100点満点）

| 軸 | 配点 | 詳細 |
|----|------|------|
| **年収推定（sal）** | 30点 | 月給35万+→30点 / 30万+→25点 / 27万+→20点 / 23万+→15点 / 20万+→10点 / それ以下→5点。時給の場合は年収換算（時給×8h×22日×12ヶ月）で判定（350万+→25点 / 300万+→20点 / 250万+→15点 / それ以下→8点） |
| **年間休日（hol）** | 20点 | 125日+→20点 / 120日+→17点 / 115日+→14点 / 110日+→10点 / 105日+→7点 / それ以下→3点 |
| **賞与（bon）** | 15点 | 4ヶ月+→15点 / 3ヶ月+→12点 / 2ヶ月+→9点 / 1ヶ月+→6点 / 「あり」→4点 |
| **雇用安定性（emp）** | 15点 | 正社員→15点 / 正社員以外+正社員登用あり→10点 / パート→5点 / その他→7点 |
| **福利厚生（wel）** | 10点 | 託児所あり+4 / 退職金あり+3 / 車通勤可+1 / 住宅手当・寮+2（上限10点） |
| **勤務地利便性（loc）** | 10点 | 人気エリア（横浜/川崎/藤沢/鎌倉）+3 / 徒歩5分以内+5 / 徒歩10分以内+3 / 駅表記あり+2（上限10点） |

### ランク判定基準

| ランク | スコア | 説明 |
|--------|--------|------|
| **S** | 80点以上 | 即応募レベル |
| **A** | 65-79点 | 好条件 |
| **B** | 50-64点 | 標準的な求人 |
| **C** | 35-49点 | 条件やや物足りない |
| **D** | 35点未満 | 魅力に乏しい |

### エリア分類ロジック（classify_area）

**AREA_MAP**: 関東4都県を26エリアに分類

- **神奈川（16エリア）**: 横浜、川崎、相模原、横須賀（逗子・三浦・葉山含む）、鎌倉、藤沢、茅ヶ崎（寒川含む）、平塚、大磯（二宮含む）、秦野、伊勢原、厚木（愛川・清川含む）、大和（綾瀬含む）、海老名（座間含む）、小田原、南足柄・開成（松田・山北・大井・中井・箱根・真鶴・湯河原含む）
- **東京（2エリア）**: 23区、多摩
- **埼玉（6エリア）**: さいたま、川口・戸田、所沢・入間、川越・東松山、越谷・草加、埼玉その他
- **千葉（4エリア）**: 千葉、船橋・市川、柏・松戸、千葉その他

**マッチングロジック**:
1. 勤務地（work_location + work_address + employer_address）を結合
2. 関東4都県以外はスキップ（None返却）
3. **長い市区町村名を優先的にマッチ**（例: 「東大和市」を「大和市」より先に検出）
4. AREA_MAPの全エントリを文字列長の降順でソートしてから検索

---

## 4. worker.js更新（hellowork_to_jobs.py）

### 入力/出力
- **入力**: `data/hellowork_ranked.json`
- **出力**: `api/worker.js`（EXTERNAL_JOBSブロックを正規表現で置換）

### EXTERNAL_JOBSの構造
```javascript
const EXTERNAL_JOBS = {
  nurse: {
    "横浜": [
      {n:"事業所名", t:"職種", r:"S", s:85,
       d:{sal:30, hol:20, bon:15, emp:15, wel:5, loc:0},
       sal:"月給35万円", sta:"横須賀中央", hol:"126日",
       bon:"3ヶ月", emp:"正社員", wel:"託児所",
       desc:"仕事内容(150字)", loc:"勤務地", shift:"勤務時間"},
      // ...
    ],
    "川崎": [...],
    // 全26エリア
  },
  pt: { /* 既存のPT求人（変更しない） */ },
};
```

### エリアごとの最大件数
- **デフォルト: 8件/エリア**（`--max-per-area`で変更可能）
- エリア内でスコア順ソート
- **同一事業所の重複除去**（事業所名が同じ求人は最高スコアのもののみ採用）

### 更新方法
1. worker.jsを読み込み
2. 正規表現 `// ---------- 外部公開求人データ.*?const EXTERNAL_JOBS = \{.*?\};\n` でブロックを検索
3. 新しいEXTERNAL_JOBSブロックを生成（日付コメント付き）
4. PT求人セクションは既存のまま維持（正規表現で抽出して再挿入）
5. ブロック全体を置換してファイルに書き戻し

---

## 5. 自動化（cron）

### 実行スケジュール
```
30 6 * * * /bin/bash ~/robby-the-match/scripts/pdca_hellowork.sh
```
- **毎朝06:30**に実行

### pdca_hellowork.shの処理順序

| Step | 処理 | 失敗時の挙動 |
|------|------|-------------|
| **Step 1** | `hellowork_fetch.py --all-prefectures`（4県API取得） | Slack通知 + `exit 1`（中断） |
| **Step 1.5** | `hellowork_diff.py`（差分分析・前日比較） | 警告ログのみ（続行） |
| **Step 2** | `hellowork_rank.py --summary`（ランク分け） | 警告ログのみ（続行） |
| **Step 3** | `hellowork_to_jobs.py`（worker.js更新） | Slack通知 + `exit 1`（中断） |
| **Step 4** | git add + commit + push（main→master両方） | 変更なしならスキップ |
| **Step 5** | `wrangler deploy --config wrangler.toml`（Worker再デプロイ） | 警告ログのみ（続行、求人データは更新済み） |
| **Step 6** | Slack通知（最終結果） | — |

### エラー時の挙動
- `set -euo pipefail` で未定義変数・パイプエラーを検知
- **致命的エラー**（API取得失敗、worker.js変換失敗）: Slack通知 + exit 1
- **非致命的エラー**（差分分析失敗、ランク分け失敗、Workerデプロイ失敗）: ログに記録して続行
- git差分なし: コミット・プッシュをスキップ

### Slack通知
- `scripts/slack_bridge.py --send` を使用
- チャンネル: #claudecode（C09A7U4TV4G）
- 通知内容: 看護師求人件数、Sランク件数、Aランク件数

### git commit
- 対象ファイル: `api/worker.js`, `data/hellowork_nurse_jobs.json`, `data/hellowork_ranked.json`
- author: `Hellowork Bot <bot@quads-nurse.com>`
- メッセージ例: `chore: ハローワーク求人データ自動更新 2026-04-06 (1364件)`
- push先: `origin main` + `origin main:master`

---

## 6. データフロー図

```
Step 1: ハローワークAPI (XML/POST)
         ↓ hellowork_fetch.py --all-prefectures
         ↓ 東京(M113) + 神奈川(M114) + 埼玉(M111) + 千葉(M112)
         ↓ 看護師フィルタ（職種名 or 必要資格）
         ↓ 除外: 看護助手/派遣/動物
         ↓
Step 1.5: data/hellowork_nurse_jobs.json
         ↓ hellowork_diff.py（前日スナップショットと比較）
         ↓
Step 2: data/hellowork_nurse_jobs.json
         ↓ hellowork_rank.py
         ↓ 6軸スコアリング(100点) → S/A/B/C/Dランク
         ↓ 26エリアに分類
         ↓
Step 3: data/hellowork_ranked.json
         ↓ hellowork_to_jobs.py
         ↓ エリア別8件上限 × 事業所重複除去
         ↓ JSオブジェクトリテラルに変換
         ↓ worker.js EXTERNAL_JOBSを正規表現で置換
         ↓
Step 4: api/worker.js（更新済み）
         ↓ git add + commit + push
         ↓ wrangler deploy --config wrangler.toml
         ↓
Step 5: Cloudflare Worker（本番反映）
         ↓
Step 6: Slack通知（#claudecode）
```

---

## 7. 注意点・既知の問題

### API制限
- **メンテナンス時間帯**: 毎日0:00-6:00、月末21:30-翌6:00はAPI利用不可（HTTP 503）
- cron実行が06:30のため、メンテナンス終了直後で不安定な可能性あり

### Cloudflare Worker デプロイ
- **`--config wrangler.toml` を絶対に省略するな**（ルートのwrangler.jsoncが優先されて別Workerにデプロイされる）
- `unset CLOUDFLARE_API_TOKEN` が必要（権限不足のため、OAuth認証を使用）
- デプロイ後にシークレットが消えることがある → `wrangler secret list --config wrangler.toml` で確認推奨

### データ品質
- 時給判定が `low_num < 10000` で行われているため、低月給（10万未満）が時給と誤判定される可能性あり
- 賞与月数は正規表現 `(\d+\.?\d*)ヶ月` で抽出。記載がない場合は0扱い
- エリア分類不能な求人はworker.jsに含まれない（Noneの場合スキップ）

### PT求人の扱い
- EXTERNAL_JOBSの `pt:` セクションは正規表現で既存データを抽出して維持
- このパイプラインではPT求人の更新は行われない

### hellowork_diff.py
- pdca_hellowork.shのStep 1.5で呼ばれるが、失敗しても続行する（非致命的）
- 前日のスナップショットとの差分分析+Slack送信を行う

### cronの前提条件
- Mac Miniがスリープしていないこと
- `.env` にHELLOWORK_USER_ID / HELLOWORK_PASSWORD が設定されていること
- `/opt/homebrew/bin/npx` が存在すること（wrangler実行用）
- gitの認証情報が設定済みであること（push用）
