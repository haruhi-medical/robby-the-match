# ゲートキーパー #5: prefecture空欄の復元（877件 / 29.6%）

作業日: 2026-04-17
担当: Claude Code エージェント
対象ファイル: `/Users/robby2/robby-the-match/scripts/hellowork_to_d1.py`

## 1. 修正したロジック

### 変更前
`build_sql()` 内にインラインで都道府県抽出を実装。
1. `work_location/work_address/employer_address` から "東京都|神奈川県|千葉県|埼玉県" を substring 一致で抽出
2. 抽出できなければ、ハローワーク `area` 値から `AREA_PREF_REVERSE` で逆引き（16エリア）
3. それでも解決できなければ空欄

### 変更後
抽出ロジックをモジュール関数 `resolve_prefecture(loc, area)` として切り出し、3段階フォールバックを実装。

1. **住所文字列に都道府県名が直接含まれる** → そのまま抽出
2. **住所文字列に市区町村名 or 東京23区名が含まれる** → `CITY_PREF_MAP` / `TOKYO_23_WARDS` で逆引き
   - 神奈川33市町村 / 東京25市+23区 / 千葉33市 / 埼玉37市町 を網羅（関東4都県のみ）
   - 他県と重複する名称（例: 府中市は広島にもあるが東京優先）は明示コメント
3. **ハローワーク `area` 値から逆引き** → 既存 `AREA_PREF_REVERSE`（16エリア）を流用

派遣除外は上流（`hellowork_rank.py`）で処理済みのため影響なし。SQL文は既存の
`escape_sql()` でエスケープされており、バインドパラメータ相当の安全性を維持。

## 2. 想定復活件数（実測）

`python3 scripts/hellowork_to_d1.py --stats-only` を新規追加し、DB更新なしで
現JSONに対する解決率を試算できるようにした。

現スナップショット（`data/hellowork_ranked.json` 3374件）での結果:

| 指標 | 値 |
|------|----|
| 旧DB（現SQLite） total | 2963件 |
| 旧DB prefecture 空欄 | **877件（29.6%）** |
| 旧DB 神奈川県=? | 469件 |
| 新ロジック total（再生成後） | 3373件 |
| 新ロジック 空欄 | **0件（0.0%）** |
| 新ロジック 神奈川県=? | **814件（+345件, +73.6%）** |
| 新ロジック 東京都 | 1203件 |
| 新ロジック 千葉県 | 668件 |
| 新ロジック 埼玉県 | 688件 |

神奈川検索の脱落率: 32.6% → 0%（推定228件の神奈川求人がヒット可能に）。

## 3. 変更行数

- 追加: +144行（`resolve_prefecture` 関数 + `CITY_PREF_MAP` + `TOKYO_23_WARDS` + `print_prefecture_stats` + `--stats-only`）
- 削除: −22行（`build_sql()` 内インラインロジック）
- 実質 +122行 / ファイル総行数: 300 → 422

## 4. 翌朝 cron 反映までのラグ

- crontab: `30 6 * * * /bin/bash ~/robby-the-match/scripts/pdca_hellowork.sh`
- 処理チェーン: fetch → rank → `hellowork_to_d1.py`（自動D1投入）
- **反映タイミング: 2026-04-18 06:30〜06:40**（約23時間後）
- 本作業中は **DB直接更新していない**（指示遵守）。バックアップ
  `/tmp/hellowork_jobs_backup_20260417.sqlite` 経由で --local テスト後、元状態に復元済み。

## 5. 懸念点

1. **府中市の曖昧性**: 東京都府中市と広島県府中市が同名。東京優先としたが、
   ハローワークが広島求人を返すことは稀のため実害なし（関東4都県スコープでは無害）。
2. **町名のみの住所（"○○町"）**: 全国に同名の町が多数あるため含めていない。
   影響範囲は極めて限定的（該当なしを確認）。
3. **localSQLite テスト結果**: 3374件→3373件（1件減）はスクリプト変更ではなく、
   `INSERT OR IGNORE` + `kjno UNIQUE` 制約による重複除去（既存挙動。無害）。
4. **STATE.md の「prefecture空欄修正済」記述が虚偽だった件**: 翌朝cron実行後に
   `prefecture=''` が0件であることを確認次第、STATE.mdを正しい状態に更新する必要あり。
5. **D1側は cron 内で `DROP TABLE IF EXISTS jobs;` + `CREATE TABLE` + 再INSERT**
   しているため、インデックスも再作成される。ダウンタイムは数秒（許容範囲）。

## 検証コマンド

翌朝の cron 実行後、以下で反映を確認:

```bash
# ローカルSQLite（本番D1と同じSQLから再生成されている場合）
sqlite3 ~/robby-the-match/data/hellowork_jobs.sqlite \
  "SELECT COUNT(*), SUM(CASE WHEN prefecture='' THEN 1 ELSE 0 END) FROM jobs;"
# 期待: 空欄=0

# 事前確認（現時点でも可能）
cd ~/robby-the-match && python3 scripts/hellowork_to_d1.py --stats-only
```
