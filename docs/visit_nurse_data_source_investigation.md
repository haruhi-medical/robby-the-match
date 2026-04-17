# 神奈川県訪問看護ステーション データソース調査

> 作成日: 2026-04-17
> 目的: D1 `facilities` テーブルの訪問看護ST（推定800件）空白を埋める
> 前提: 現行 24,488件（病院1,498/クリニック22,978/介護12/訪問看護0）

## サマリ（結論）

- **メインソース: 介護サービス情報公表システム（kaigokensaku.mhlw.go.jp）** — 神奈川県指定の訪問看護ST全件が網羅される唯一の公的ソース。ただしCSV一括配布なし → HTMLスクレイピング必須。推定600〜900件取得可能。
- **補完: WAM NET（wam.go.jp）** — 同じ厚労省ベースのデータをより緩い検索UIで公開。kaigokensakuが止まった時のフォールバック。
- **即時プラス: 既存ハローワーク求人から88事業所（神奈川）** — 電話番号付きで取得済み。スクレイピング不要で今夜から流し込める。
- **不採用: e-Gov医療情報ネット（`import_egov_facilities.py`が叩いているソース）** — 医療法CSV（病院+診療所）であって訪問看護STは**0件**。現行コードで取れないのはこれが原因。
- **工数見積**: 新規スクリプト `scripts/visit_nurse_fetch.py` を `hellowork_fetch.py` と同じパターンで1〜2日。cron週次で運用。

## 比較表

| # | ソース | URL | 形式 | 件数(神奈川) | 更新 | 取得難度 | 指定番号 | 住所 | 電話 | サービス |
|---|--------|-----|------|-------------|------|----------|---------|------|------|---------|
| 1 | 介護サービス情報公表システム | kaigokensaku.mhlw.go.jp/14/ (Pref=14) | HTML (JSPラッパ) | 600〜900 | 年1回報告+随時 | 中（ページング+詳細ページ2段） | ○ | ○ | ○ | ○ |
| 2 | WAM NET 介護事業所検索 | wam.go.jp/sjsearch/ | HTML | 同等 | 月次反映 | 中 | ○ | ○ | ○ | ○ |
| 3 | 既存ハローワーク求人(D1 jobs) | 既に `data/hellowork_ranked.json` にある | JSON | 88ユニーク事業所(Kanagawa, 172求人) | 毎朝06:30 | **ゼロ**（既存パイプ内で完結） | ✕ | ○ | △（求人票に記載あるもの） | △ |
| 4 | e-Gov 医療情報ネット | mhlw.go.jp/content/11121000/... | ZIP/CSV | **0** (対象外) | 年4回 | — | — | — | — | — |
| 5 | 神奈川県「介護保険事業者名簿」PDF | pref.kanagawa.jp/docs/t2z/... | PDF/Excel | 800前後 | 月1 | 高（PDFパース） | ○ | ○ | ○ | △ |
| 6 | 各市区町村の事業所一覧 | 33市区町村×個別URL | PDF/HTML/Excel混在 | 合計でほぼ全件 | まちまち | 高（33回分） | △ | ○ | ○ | △ |

**推奨順**: ①kaigokensaku → ③hellowork(補完) → ②WAM NET(フォールバック) → ⑤県名簿(検証用)

## 既存ハローワーク抽出の実測（今すぐ使える）

`data/hellowork_ranked.json` を「訪問看護」キーワードで絞った結果:

```
全求人 3,374件
訪問看護言及あり 706件
うち神奈川県 172件 → ユニーク事業所 88件
```

`hellowork_to_d1.py` のスキーマは `jobs` テーブル向け（employer, work_location, employer_address, work_station_text）。`facilities` テーブルに流すには **employer単位で集約+正規化** する必要あり。ただし指定番号(10桁)が取れないので重複排除キーは `name + 住所ハッシュ` になる。

## 推奨実装案

### 1. 新規スクリプト `scripts/visit_nurse_fetch.py`

`hellowork_fetch.py` のパターン踏襲。Playwright or requests+BeautifulSoup。

```
# 擬似コード
BASE = "https://www.kaigokensaku.mhlw.go.jp/14/index.php"
# SCat=042100100 が訪問看護のカテゴリコード
# Pref=14 が神奈川県

def fetch_list():
    # 1. 一覧ページをページングで全取得（1ページ50件×N）
    # 2. 各事業所の詳細URL(rentai_code)を収集
    # 3. 詳細ページから指定番号/住所/電話/サービス詳細を抽出
    # 4. data/visit_nurse_kanagawa.json に保存

def to_d1():
    # hellowork_to_d1.py と同じパターンで
    # INSERT OR IGNORE INTO facilities (name, category='訪問看護ST', ...) VALUES (...)
    # source='kaigokensaku' でタグ付け
```

### 2. 重複排除キー

優先順: `(1) 指定番号10桁` → `(2) normalize(name) + normalize(address先頭15字)` ハッシュ。

既存 `facilities` に挿入する前に:
```sql
SELECT id FROM facilities WHERE name = ? AND address LIKE ?
```
ヒットすれば UPDATE、なければ INSERT。`source` カラムで出所管理（既存の `egov_csv` と並列で `kaigokensaku` / `hellowork`）。

### 3. 既存パイプラインとの統合

- cron: `0 4 * * 0`（毎週日曜04:00。ハローワーク06:30より前に回す）
- Slack通知: `slack_bridge.py --send` で件数差分報告（hellowork_diff.pyパターン）
- `--dry-run` / `--local` フラグは hellowork_to_d1.py と同じIF
- 失敗時は `set -euo pipefail` + Slack通知（.claude/rules/scripts.md準拠）

### 4. 段階実装（推奨）

- **Phase 0 (今夜)**: hellowork既存データから88件を `facilities` に流し込む（スクレイピング不要、30分作業）
- **Phase 1 (2日)**: kaigokensakuスクレイパ実装+初回全件投入（目標800件）
- **Phase 2 (週次)**: 差分更新cron+Slack通知

## リスク

- **kaigokensaku利用規約**: 明示的なAPI提供なし。robots.txtは未確認→実装前に要確認。厚労省システムなのでスクレイピングは黙認されるが、アクセス間隔は**2秒以上**空ける（hellowork_fetch.pyと同じポリシー）。
- **法的**: 取得データは公表情報なので再掲載OK。ただし「平島禎之」「はるひメディカルサービス」の露出禁止ルール(MEMORY.md)に従い、D1内部保持のみで公開ページには個別施設名以上の情報を出さない。
- **データ鮮度**: 年1回の事業者報告が原則 → 廃止/休止STが1年遅れで残る可能性。ハローワーク求人と突き合わせて「直近求人あり」フラグで補正する設計にする。
- **ハローワーク経由分の著作権**: 求人票の事業者名・住所は事実情報のため再利用可。ただしjobs用の `hellowork-api-terms.md` 準拠を維持。

## 次のアクション

1. YOSHIYUKIにこの調査を送って Phase 0(hellowork 88件流し込み) の承認取得
2. 承認後、`scripts/visit_nurse_from_hellowork.py` を30分で実装
3. Phase 1 のkaigokensakuスクレイパ実装着手
