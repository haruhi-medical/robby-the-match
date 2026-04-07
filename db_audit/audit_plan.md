# データベース精査計画書 v1.0

> 作成日: 2026-04-06
> 対象: D1 `nurse-robby-db`（facilities: 24,488件 / jobs: 2,944件）
> 監督者: 監査AI

---

## 1. 精査目標

ナースロビーの施設マスタ（facilities）とハローワーク求人（jobs）の**データ品質を定量的に評価**し、以下を達成する:

1. **正確性**: 住所・緯度経度・給与・施設分類が現実と一致しているか
2. **完全性**: 転職判断に必要な情報が欠損なく揃っているか
3. **一貫性**: facilities と jobs の間でデータが矛盾していないか
4. **有用性**: ペルソナ「ミサキ」が実際に転職判断できるデータか
5. **純度**: 非看護師求人の混入、重複、ゴミデータがないか

最終成果物: `/db_audit/reports/final_report.md`（全項目の PASS/WARN/FAIL 一覧 + 修正SQL）

---

## 2. 各専門家のチェック項目

### 共通: D1 実行コマンド

```bash
cd ~/robby-the-match/api && unset CLOUDFLARE_API_TOKEN && npx wrangler d1 execute nurse-robby-db --config wrangler.toml --remote --json --command "SQL文"
```

---

### 2-1. データアナリスト（統計・欠損・分布）

**ログファイル**: `/db_audit/logs/01_analyst.md`

#### facilities テーブル

| # | チェック項目 | SQL |
|---|------------|-----|
| A1 | 全体件数と県別分布 | `SELECT prefecture, COUNT(*) as cnt FROM facilities GROUP BY prefecture;` |
| A2 | カテゴリ別分布 | `SELECT category, COUNT(*) as cnt FROM facilities GROUP BY category;` |
| A3 | sub_type の分布と NULL率 | `SELECT sub_type, COUNT(*) as cnt FROM facilities GROUP BY sub_type ORDER BY cnt DESC;` |
| A4 | bed_count の統計値 | `SELECT category, MIN(bed_count) as min_bed, MAX(bed_count) as max_bed, AVG(bed_count) as avg_bed, COUNT(*) - COUNT(bed_count) as null_cnt FROM facilities GROUP BY category;` |
| A5 | nurse_fulltime/parttime の NULL率 | `SELECT COUNT(*) as total, COUNT(nurse_fulltime) as has_ft, COUNT(nurse_parttime) as has_pt FROM facilities;` |
| A6 | 各カラムの NULL率一覧 | `SELECT COUNT(*) as total, COUNT(name) as has_name, COUNT(category) as has_cat, COUNT(sub_type) as has_subtype, COUNT(city) as has_city, COUNT(address) as has_addr, COUNT(lat) as has_lat, COUNT(lng) as has_lng, COUNT(nearest_station) as has_station, COUNT(station_minutes) as has_min, COUNT(bed_count) as has_bed, COUNT(departments) as has_dept FROM facilities;` |
| A7 | source別件数 | `SELECT source, COUNT(*) as cnt FROM facilities GROUP BY source;` |
| A8 | has_active_jobs が 1 の件数 | `SELECT has_active_jobs, COUNT(*) as cnt FROM facilities GROUP BY has_active_jobs;` |
| A9 | dpc_group 分布 | `SELECT dpc_group, COUNT(*) as cnt FROM facilities WHERE dpc_group IS NOT NULL GROUP BY dpc_group ORDER BY cnt DESC LIMIT 20;` |

#### jobs テーブル

| # | チェック項目 | SQL |
|---|------------|-----|
| A10 | 全体件数と area 別分布 | `SELECT area, COUNT(*) as cnt FROM jobs GROUP BY area ORDER BY cnt DESC;` |
| A11 | prefecture 別分布 | `SELECT prefecture, COUNT(*) as cnt FROM jobs GROUP BY prefecture;` |
| A12 | score の分布（10刻み） | `SELECT (score/10)*10 as score_band, COUNT(*) as cnt FROM jobs GROUP BY score_band ORDER BY score_band;` |
| A13 | 給与の統計値 | `SELECT salary_form, MIN(salary_min) as min_sal, MAX(salary_max) as max_sal, AVG(salary_min) as avg_min, AVG(salary_max) as avg_max, COUNT(*) as cnt FROM jobs GROUP BY salary_form;` |
| A14 | 各カラムの NULL率 | `SELECT COUNT(*) as total, COUNT(kjno) as has_kjno, COUNT(employer) as has_emp, COUNT(title) as has_title, COUNT(area) as has_area, COUNT(salary_min) as has_smin, COUNT(salary_max) as has_smax, COUNT(holidays) as has_hol, COUNT(station_text) as has_sta, COUNT(shift1) as has_s1, COUNT(description) as has_desc FROM jobs;` |
| A15 | rank 分布 | `SELECT rank, COUNT(*) as cnt FROM jobs GROUP BY rank ORDER BY cnt DESC;` |
| A16 | emp_type 分布 | `SELECT emp_type, COUNT(*) as cnt FROM jobs GROUP BY emp_type ORDER BY cnt DESC;` |
| A17 | synced_at の日付分布 | `SELECT DATE(synced_at) as sync_date, COUNT(*) as cnt FROM jobs GROUP BY sync_date ORDER BY sync_date DESC LIMIT 10;` |

---

### 2-2. ミサキ（28歳看護師・ユーザー視点）

**ログファイル**: `/db_audit/logs/02_misaki.md`

| # | チェック項目 | SQL | 判断基準 |
|---|------------|-----|---------|
| M1 | 給与が表示できない求人 | `SELECT COUNT(*) FROM jobs WHERE salary_display IS NULL OR salary_display = '';` | 0件が理想 |
| M2 | 勤務地が不明な求人 | `SELECT COUNT(*) FROM jobs WHERE work_location IS NULL OR work_location = '';` | 0件が理想 |
| M3 | シフト情報なしの求人 | `SELECT COUNT(*) FROM jobs WHERE shift1 IS NULL AND shift2 IS NULL;` | 夜勤有無が判断できないのは致命的 |
| M4 | 休日数なしの求人 | `SELECT COUNT(*) FROM jobs WHERE holidays IS NULL;` | ワークライフバランス判断不可 |
| M5 | 賞与情報なしの求人 | `SELECT COUNT(*) FROM jobs WHERE bonus_text IS NULL OR bonus_text = '';` | 年収計算不可 |
| M6 | 最寄駅なしの施設 | `SELECT category, COUNT(*) as cnt FROM facilities WHERE nearest_station IS NULL GROUP BY category;` | 通勤判断不可 |
| M7 | 診療科なしの病院 | `SELECT COUNT(*) FROM facilities WHERE category = '病院' AND (departments IS NULL OR departments = '');` | 配属先が分からない |
| M8 | 病床数なしの病院 | `SELECT COUNT(*) FROM facilities WHERE category = '病院' AND bed_count IS NULL;` | 規模感が分からない |
| M9 | 求人があるのに施設情報が乏しい | `SELECT j.employer, f.name, f.nearest_station, f.bed_count, f.departments FROM jobs j LEFT JOIN facilities f ON j.employer = f.name WHERE f.nearest_station IS NULL AND f.id IS NOT NULL LIMIT 20;` | 施設ページに情報不足 |
| M10 | description が短すぎる求人 | `SELECT COUNT(*) FROM jobs WHERE LENGTH(description) < 50;` | 仕事内容が判断できない |

---

### 2-3. 地理エキスパート

**ログファイル**: `/db_audit/logs/03_geo.md`

| # | チェック項目 | SQL | 判断基準 |
|---|------------|-----|---------|
| G1 | 緯度経度がNULLの施設 | `SELECT prefecture, COUNT(*) as cnt FROM facilities WHERE lat IS NULL OR lng IS NULL GROUP BY prefecture;` | 地図表示不可 |
| G2 | 緯度経度が日本の範囲外 | `SELECT id, name, lat, lng FROM facilities WHERE lat IS NOT NULL AND (lat < 24 OR lat > 46 OR lng < 122 OR lng > 154);` | 明らかなエラー |
| G3 | 緯度経度が関東圏外 | `SELECT id, name, prefecture, lat, lng FROM facilities WHERE lat IS NOT NULL AND (lat < 34.5 OR lat > 36.5 OR lng < 138.5 OR lng > 140.5) LIMIT 30;` | 要確認 |
| G4 | station_minutes の異常値 | `SELECT id, name, nearest_station, station_minutes FROM facilities WHERE station_minutes IS NOT NULL AND (station_minutes < 0 OR station_minutes > 60) LIMIT 20;` | 60分超は疑わしい |
| G5 | 住所に県名が含まれない | `SELECT id, name, prefecture, address FROM facilities WHERE address IS NOT NULL AND address NOT LIKE '%' \|\| prefecture \|\| '%' LIMIT 20;` | 住所フォーマット確認 |
| G6 | city が NULL の施設 | `SELECT prefecture, COUNT(*) as cnt FROM facilities WHERE city IS NULL GROUP BY prefecture;` | エリア検索に影響 |
| G7 | 同一住所の重複施設 | `SELECT address, COUNT(*) as cnt FROM facilities WHERE address IS NOT NULL GROUP BY address HAVING cnt > 3 ORDER BY cnt DESC LIMIT 20;` | 同一ビル内or重複 |
| G8 | jobs の work_location に県名が含まれるか | `SELECT COUNT(*) as total, SUM(CASE WHEN work_location LIKE '%神奈川%' OR work_location LIKE '%東京%' OR work_location LIKE '%埼玉%' OR work_location LIKE '%千葉%' THEN 1 ELSE 0 END) as has_pref FROM jobs WHERE work_location IS NOT NULL;` | エリア判定の信頼性 |
| G9 | jobs の area が NULL | `SELECT COUNT(*) FROM jobs WHERE area IS NULL;` | エリア分類漏れ |
| G10 | jobs の station_text パターン | `SELECT station_text, COUNT(*) as cnt FROM jobs WHERE station_text IS NOT NULL GROUP BY station_text ORDER BY cnt DESC LIMIT 20;` | フォーマット統一性 |

---

### 2-4. 給与・労働条件エキスパート

**ログファイル**: `/db_audit/logs/04_salary.md`

| # | チェック項目 | SQL | 判断基準 |
|---|------------|-----|---------|
| S1 | salary_min > salary_max | `SELECT id, kjno, employer, salary_min, salary_max FROM jobs WHERE salary_min > salary_max;` | 0件であるべき |
| S2 | 月給が極端に低い（< 15万） | `SELECT id, kjno, employer, salary_form, salary_min, salary_max FROM jobs WHERE salary_form = '月給' AND salary_min < 150000;` | パート混入の可能性 |
| S3 | 月給が極端に高い（> 60万） | `SELECT id, kjno, employer, salary_form, salary_min, salary_max FROM jobs WHERE salary_form = '月給' AND salary_max > 600000;` | 管理職or入力ミス |
| S4 | 時給の範囲チェック | `SELECT id, kjno, employer, salary_form, salary_min, salary_max FROM jobs WHERE salary_form = '時給' AND (salary_min < 800 OR salary_max > 5000);` | 異常値 |
| S5 | salary_form の分布 | `SELECT salary_form, COUNT(*) as cnt, AVG(salary_min) as avg_min, AVG(salary_max) as avg_max FROM jobs GROUP BY salary_form;` | 全体把握 |
| S6 | holidays の分布 | `SELECT holidays, COUNT(*) as cnt FROM jobs GROUP BY holidays ORDER BY holidays;` | 年間休日の妥当性 |
| S7 | holidays が極端（< 80 or > 140） | `SELECT id, kjno, employer, holidays FROM jobs WHERE holidays IS NOT NULL AND (holidays < 80 OR holidays > 140);` | 異常値 |
| S8 | score と個別スコアの整合性 | `SELECT id, kjno, score, score_sal, score_hol, score_bon, score_emp, score_wel, score_loc FROM jobs WHERE score != (score_sal + score_hol + score_bon + score_emp + score_wel + score_loc) LIMIT 20;` | score = 各スコアの合計か |
| S9 | 各スコアの範囲チェック | `SELECT MIN(score_sal) as min_s, MAX(score_sal) as max_s, MIN(score_hol) as min_h, MAX(score_hol) as max_h, MIN(score_bon) as min_b, MAX(score_bon) as max_b, MIN(score_emp) as min_e, MAX(score_emp) as max_e, MIN(score_wel) as min_w, MAX(score_wel) as max_w, MIN(score_loc) as min_l, MAX(score_loc) as max_l FROM jobs;` | 想定範囲内か |
| S10 | emp_type に「派遣」が含まれる | `SELECT id, kjno, employer, emp_type FROM jobs WHERE emp_type LIKE '%派遣%';` | 派遣は紹介対象外 |

---

### 2-5. 施設分類エキスパート

**ログファイル**: `/db_audit/logs/05_classification.md`

| # | チェック項目 | SQL | 判断基準 |
|---|------------|-----|---------|
| C1 | category の全種類 | `SELECT category, COUNT(*) FROM facilities GROUP BY category;` | 想定カテゴリのみか |
| C2 | sub_type の全種類 | `SELECT sub_type, COUNT(*) FROM facilities GROUP BY sub_type ORDER BY COUNT(*) DESC;` | 想定値のみか |
| C3 | クリニックに bed_count > 19 | `SELECT id, name, category, bed_count FROM facilities WHERE category = 'クリニック' AND bed_count > 19;` | 20床以上は「病院」であるべき |
| C4 | 病院に bed_count < 20 | `SELECT id, name, category, bed_count FROM facilities WHERE category = '病院' AND bed_count IS NOT NULL AND bed_count < 20;` | 19床以下は「クリニック」 |
| C5 | departments に看護系以外のみ | `SELECT id, name, departments FROM facilities WHERE departments IS NOT NULL AND departments NOT LIKE '%科%' LIMIT 20;` | 分類ミスの可能性 |
| C6 | setter_type の分布 | `SELECT setter_type, COUNT(*) FROM facilities GROUP BY setter_type;` | 開設者の種類 |
| C7 | is_tokutei / is_chiiki_shien の分布 | `SELECT is_tokutei, is_chiiki_shien, COUNT(*) FROM facilities GROUP BY is_tokutei, is_chiiki_shien;` | 特定機能・地域支援病院 |
| C8 | 名前に「クリニック」を含む病院 | `SELECT id, name, category FROM facilities WHERE category = '病院' AND (name LIKE '%クリニック%' OR name LIKE '%診療所%');` | 分類ミスの可能性 |
| C9 | 名前に「病院」を含むクリニック | `SELECT id, name, category FROM facilities WHERE category = 'クリニック' AND name LIKE '%病院%';` | 分類ミスの可能性 |
| C10 | 介護施設の詳細 | `SELECT id, name, sub_type, address, bed_count FROM facilities WHERE category = '介護施設';` | 12件の内容確認 |

---

### 2-6. 求人フィルタエキスパート

**ログファイル**: `/db_audit/logs/06_filter.md`

| # | チェック項目 | SQL | 判断基準 |
|---|------------|-----|---------|
| F1 | title に看護師を含まない求人 | `SELECT id, kjno, title, employer FROM jobs WHERE title NOT LIKE '%看護%' AND title NOT LIKE '%ナース%' LIMIT 30;` | 非看護師求人の混入 |
| F2 | title に「准看護」を含む求人数 | `SELECT COUNT(*) FROM jobs WHERE title LIKE '%准看護%';` | 准看護師の割合 |
| F3 | description に「派遣」を含む | `SELECT id, kjno, employer FROM jobs WHERE description LIKE '%派遣%' LIMIT 20;` | 派遣求人の混入 |
| F4 | kjno の重複チェック | `SELECT kjno, COUNT(*) as cnt FROM jobs GROUP BY kjno HAVING cnt > 1;` | UNIQUE制約あるが念のため |
| F5 | employer名の表記揺れ | `SELECT employer, COUNT(*) as cnt FROM jobs GROUP BY employer HAVING cnt > 3 ORDER BY cnt DESC LIMIT 20;` | 同一施設の複数求人は正常 |
| F6 | area に該当しない prefecture | `SELECT DISTINCT area, prefecture FROM jobs WHERE area IS NOT NULL ORDER BY prefecture, area;` | area と prefecture の整合性 |
| F7 | rank の分布と意味 | `SELECT rank, COUNT(*) as cnt, AVG(score) as avg_score FROM jobs GROUP BY rank ORDER BY avg_score DESC;` | rank とスコアの関係 |
| F8 | synced_at が古い求人 | `SELECT COUNT(*) FROM jobs WHERE synced_at < '2026-03-01';` | 期限切れの可能性 |
| F9 | title パターン分析 | `SELECT CASE WHEN title LIKE '%正看護師%' THEN '正看護師' WHEN title LIKE '%准看護師%' THEN '准看護師' WHEN title LIKE '%看護師%' THEN '看護師(種別不明)' ELSE 'その他' END as title_type, COUNT(*) as cnt FROM jobs GROUP BY title_type;` | 分類の精度 |
| F10 | score = 0 or NULL の求人 | `SELECT COUNT(*) FROM jobs WHERE score IS NULL OR score = 0;` | スコアリング漏れ |

---

### 2-7. 整合性チェッカー（facilities - jobs 間）

**ログファイル**: `/db_audit/logs/07_integrity.md`

| # | チェック項目 | SQL | 判断基準 |
|---|------------|-----|---------|
| I1 | jobs.employer が facilities.name に存在するか | `SELECT COUNT(*) as total, SUM(CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END) as matched FROM jobs j LEFT JOIN facilities f ON j.employer = f.name;` | マッチ率 |
| I2 | マッチしない employer リスト | `SELECT DISTINCT j.employer FROM jobs j LEFT JOIN facilities f ON j.employer = f.name WHERE f.id IS NULL ORDER BY j.employer LIMIT 30;` | 表記揺れ or 未登録 |
| I3 | has_active_jobs = 1 だが対応する job がない | `SELECT f.id, f.name FROM facilities f WHERE f.has_active_jobs = 1 AND NOT EXISTS (SELECT 1 FROM jobs j WHERE j.employer = f.name);` | フラグの不整合 |
| I4 | active_job_count と実際の件数の不一致 | `SELECT f.id, f.name, f.active_job_count, COUNT(j.id) as actual_count FROM facilities f INNER JOIN jobs j ON f.name = j.employer GROUP BY f.id HAVING f.active_job_count != actual_count LIMIT 20;` | カウントの不整合 |
| I5 | jobs の prefecture と facilities の prefecture の不一致 | `SELECT j.id, j.kjno, j.employer, j.prefecture as j_pref, f.prefecture as f_pref FROM jobs j INNER JOIN facilities f ON j.employer = f.name WHERE j.prefecture != f.prefecture LIMIT 20;` | 県の矛盾 |
| I6 | facilities の name 重複 | `SELECT name, COUNT(*) as cnt FROM facilities GROUP BY name HAVING cnt > 1 ORDER BY cnt DESC LIMIT 20;` | 同名施設 or 重複登録 |
| I7 | facilities で求人がある施設の割合 | `SELECT category, COUNT(*) as total, SUM(has_active_jobs) as with_jobs, ROUND(100.0 * SUM(has_active_jobs) / COUNT(*), 1) as pct FROM facilities GROUP BY category;` | 求人カバー率 |
| I8 | jobs に対応する facility が複数マッチ | `SELECT j.employer, COUNT(DISTINCT f.id) as facility_cnt FROM jobs j INNER JOIN facilities f ON j.employer = f.name GROUP BY j.employer HAVING facility_cnt > 1 ORDER BY facility_cnt DESC LIMIT 20;` | 同名施設問題 |

---

## 3. ログ記録ルール

### ディレクトリ構成

```
/db_audit/
├── audit_plan.md          ← この計画書
├── logs/
│   ├── 01_analyst.md      ← データアナリスト
│   ├── 02_misaki.md       ← ミサキ（ユーザー視点）
│   ├── 03_geo.md          ← 地理エキスパート
│   ├── 04_salary.md       ← 給与・労働条件
│   ├── 05_classification.md ← 施設分類
│   ├── 06_filter.md       ← 求人フィルタ
│   └── 07_integrity.md    ← 整合性チェック
└── reports/
    └── final_report.md    ← 監督者の最終レポート
```

### 各ログの記載フォーマット

```markdown
# [専門家名] 精査ログ

> 実行日: YYYY-MM-DD
> 対象テーブル: facilities / jobs

## チェック結果

### [チェックID] [チェック項目名]

- **判定**: PASS / WARN / FAIL
- **SQL**: （実行したSQL）
- **結果**: （数値・該当件数）
- **所見**: （何が問題か、なぜ問題か）
- **推奨アクション**: （修正SQL or 調査依頼）

---
```

### ルール

1. SQLの実行結果は**必ず数値を記録**する（「多かった」などの曖昧表現禁止）
2. WARN/FAIL の場合、**該当データのサンプル**を最大10件記載する
3. 修正が必要な場合、**UPDATE/DELETE SQL を下書き**する（実行はしない）
4. 判断に迷う場合は「要確認」として監督者に差し戻す

---

## 4. 判定基準

### PASS（合格）

- 異常値が 0 件、または全体の **0.5% 未満**
- 既知の仕様として説明がつく
- ユーザー体験に影響しない

### WARN（警告）

- 異常値が全体の **0.5% 以上 5% 未満**
- データ品質に懸念があるが、サービス運用に致命的ではない
- 中期的に修正すべき

### FAIL（不合格）

- 異常値が全体の **5% 以上**
- ユーザーに誤った情報を表示する可能性がある
- 法的リスク（虚偽の給与情報、存在しない施設など）
- 即時修正が必要

### 特別ルール

- **salary_min > salary_max**: 1件でも FAIL
- **派遣求人の混入**: 1件でも FAIL（事業方針として派遣は対象外）
- **非看護師求人の混入**: 5件以上で FAIL
- **緯度経度が日本外**: 1件でも FAIL

---

## 5. 監査手順

### Phase 1: 個別精査（専門家 2-7 が並列実行）

1. 各専門家が自分のチェック項目を全て実行
2. 結果を所定のログファイルに記録
3. FAIL が出た場合、即座に監督者に報告

### Phase 2: クロスレビュー（監督者）

1. 全ログファイルを読み込み
2. FAIL 項目の再現確認（同じ SQL を再実行）
3. 専門家間で矛盾する指摘がないか確認
4. FAIL 項目に対する修正 SQL を検証（DRY RUN）

### Phase 3: 修正実行

1. 修正 SQL を `/db_audit/reports/fix_queries.sql` に集約
2. 監督者が優先度順にソート（FAIL > WARN）
3. バックアップ確認後、修正実行
4. 修正後に影響を受けたチェック項目を再実行して PASS 確認

### Phase 4: 最終レポート

1. 全チェック項目の PASS/WARN/FAIL サマリ表を作成
2. 残存 WARN の理由と対応計画を記載
3. データ品質スコア（PASS率）を算出
4. `/db_audit/reports/final_report.md` に出力

---

## 6. 完了条件

### 必須条件（全て満たすこと）

- [ ] 全 7 専門家のログファイルが `/db_audit/logs/` に存在する
- [ ] 全チェック項目（A1-A17, M1-M10, G1-G10, S1-S10, C1-C10, F1-F10, I1-I8）が実行済み
- [ ] **FAIL 判定が 0 件**（全て修正済み、または WARN に格下げの根拠あり）
- [ ] 修正した SQL の実行後、対象チェックが PASS に変わっている
- [ ] 最終レポートが作成されている

### 品質目標

- **全体 PASS 率**: 90% 以上
- **FAIL**: 0 件（修正 or 根拠付き格下げ）
- **WARN**: 10 件以下

### 最終レポートの承認

監督者が最終レポートを作成し、以下を宣言した時点で精査完了:

```
## 精査完了宣言

全 65 チェック項目の精査を完了しました。
- PASS: XX 件
- WARN: XX 件（対応計画あり）
- FAIL: 0 件
データ品質スコア: XX%

精査完了日: YYYY-MM-DD
```

---

## 付録: チェック項目数サマリ

| 専門家 | 項目数 | 対象テーブル |
|--------|--------|-------------|
| データアナリスト | 17 | facilities + jobs |
| ミサキ | 10 | facilities + jobs |
| 地理エキスパート | 10 | facilities + jobs |
| 給与・労働条件 | 10 | jobs |
| 施設分類 | 10 | facilities |
| 求人フィルタ | 10 | jobs |
| 整合性チェッカー | 8 | facilities + jobs |
| **合計** | **65** | |
