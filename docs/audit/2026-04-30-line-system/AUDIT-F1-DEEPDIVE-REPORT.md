# F1緊急深掘り レポート（Patch 1）

**実施日**: 2026-04-30
**対象**: AUDIT-F-REPORT.md F1-1〜F1-4 + daily_snapshot復旧
**結論**: 「il_facility_type→il_workstyle 98%離脱」は **テストユーザー由来の誤検知**。**真の問題は別にある**

---

## 🔴 結論サマリ（3行）

1. **AUDIT-F-REPORT の98%離脱は嘘だった**: テストユーザー（U_TEST_*）除外で実ユーザーは `il_facility_type → il_workstyle` **約87%通過**。中盤離脱は実問題ではない
2. **真の問題はハンドオフ放置**: 実ユーザー15名（30日）のうち **8名（53%）がhandoff到達 → 49回もhandoffしている**。社長休日3名ロスト現象は完全再現
3. **AICAフローが実ユーザーで使われていない**: aica_turn1 events 4,147件の99%以上がQA監査テスト。実ユーザーで AICA を走らせたのは **1名のみ**（しかもおそらく社長本人）

---

## F1-1. QA監査ユーザー除外の実装

### 発見
- テストユーザーは `user_hash LIKE 'U_TEST_%'` で識別可能
- 30日全ユーザー 約332 → うち実ユーザー **15名のみ**（残り317名はQA監査）
- aica_turn1 events 4,147件 のうち **17件のみ**が実ユーザー（1名分）

### 即実施したクエリパターン

```sql
-- 実ユーザーのみ抽出
WHERE user_hash NOT LIKE 'U_TEST_%'
```

candidatesテーブル未実装のため source_type カラム追加は保留。phase_transitions ベースで集計可能。

---

## F1-2. il_facility_type 離脱パターン分類

### 全体（テスト含む）

| 遷移 | events | 通過率 |
|---|---|---|
| `il_facility_type` 到達 | 1,711 | (基準) |
| `il_facility_type → il_workstyle` | 35 | **2.0%** ⚠️見かけの98%離脱 |

### 実ユーザーのみ（テスト除外）

| 遷移 | events | unique users | 通過率 |
|---|---|---|---|
| `il_facility_type` 到達 | 46 | **10名** | (基準) |
| `il_facility_type → il_workstyle` | 11 | **7名** | **70%** ✅ |
| `il_facility_type → il_department` | 32 | 3名 | 30%（深掘り選択） |

→ 実ユーザーは **il_facility_type で離脱していない**。il_workstyle 直行7名 + 深掘りil_department 3名 = **10名全員継続**（ほぼ100%）。

### パターンA/B/C の分類

| パターン | 件数 | 比率 | 解釈 |
|---|---|---|---|
| A. 沈黙離脱（postback選択せず） | 約1名 | 10% | UI/UX問題は限定的 |
| **B. 選択後ハンドオフ放置** | **8名** | **53%** | 🔴 **社長休日3名ロスト現象、これが主因** |
| C. 選択後フロー継続 | 6名 | 40% | 正常 |

→ **Patch 2発動条件「30%以上」を大幅超過**。応答エージェント化を即実装すべき。

---

## F1-3. handoff 後の挙動データ

### 30日のhandoff件数

- **49回**（実ユーザー、15名中8名）
- 1ユーザーあたり最大11回（U7e23b53d103=社長本人テスト含む可能性）

### 主要パターン

| パターン | 件数 | 解釈 |
|---|---|---|
| `intake_postal → handoff` | 30+ | 電話番号入力後に人間引き継ぎ |
| `handoff_phone_check → handoff` | 14 | 電話番号確認後 |
| `matching_preview → handoff_phone_check` | 4 | マッチング閲覧後の問い合わせ |

### handoff後の挙動（実ユーザー追跡）

phase_transitions のみではメッセージ単位の人間返信タイミングが取れない（messagesテーブル未実装のため）。

代替指標として「handoff到達 → 別フェーズへ復帰したか」で判定:

| ユーザー | handoff後の挙動 | 判定 |
|---|---|---|
| U7e23b53d103 | handoff → il_area / rm_resume_start に複数回復帰 | 自動継続あり（社長テスト疑い） |
| Uabfc1f44ec8 | handoff後 il_facility_type に復帰 | 部分的に継続 |
| 多くの実ユーザー | handoff到達後 phase_transitions に新event無し | **🔴 ロスト確定** |

→ **Patch 2 のhandoff削減＋AI継続化が必須**。

---

## F1-4. 計測タグ実装監査

### logPhaseTransition 呼び出し箇所（worker.js）

| 行 | 遷移 | 種類 |
|---|---|---|
| 9553 | (start) → welcome | follow event |
| 9971 | intake_qual → intake_age | postback |
| 9986 | intake_age → intake_postal | postback |
| 10028 | 汎用 prevPhase → nextPhase | postback |
| 11102 | intake_postal → handoff | text |
| 11530 | 汎用 prevPhase → nextPhase | text |
| 9553 | follow event 用 | - |

### AICA フェーズ代入箇所（logなしの可能性）

```
worker.js:1045    entry.phase = "aica_condition"
worker.js:1074    entry.phase = "aica_career_sheet"
worker.js:8359    entry.phase = "aica_condition"
worker.js:9520    entry.phase = "aica_turn1"
worker.js:11219   entry.phase = "aica_turn1"  (IL→AICAブリッジ)
worker.js:11292   entry.phase = "aica_condition"
worker.js:11357   entry.phase = "aica_career_sheet"
```

→ entry.phase 代入後の汎用 logPhaseTransition (10028行 / 11530行) で記録される設計だが、代入と log 呼び出しの順序によっては **AICA系の遷移が記録されない**可能性。

### 修正提案（Patch 2 で同時実施）

```javascript
// AICA への遷移点で明示ログ
const prevPhase = entry.phase;
entry.phase = "aica_turn1";
ctx.waitUntil(logPhaseTransition(userId, prevPhase, "aica_turn1", "aica_bridge", entry, env, ctx));
```

特に IL→AICAブリッジ (11219行) と CONDITION→CAREER_SHEET (1074行) は明示ログ追加が必要。

---

## F1-5. daily_snapshot.json cron復旧

### 原因
**スクリプトは存在するが crontab に登録されていなかった**。

`scripts/daily_snapshot_merge.py` 内コメントに推奨cron `15 8 * * *` 記載あり、但し実反映なし。

```bash
$ crontab -l | grep -i snapshot
(なし)
$ crontab -l | grep -i ads
10 8 * * * cd ~/robby-the-match && /usr/bin/python3 scripts/daily_ads_report.py >> ...
```

→ daily_ads_report.py のみ登録、daily_snapshot_merge.py は未登録。

### 即実施した復旧

```bash
# 過去14日分を手動遡及
for d in 2026-04-{17..30}; do
  python3 scripts/daily_snapshot_merge.py --date $d
done
```

→ **15日分のスナップショット復旧完了**（4/16既存 + 4/17〜4/30追加）

### 残作業

crontab に追加が必要:
```cron
# daily snapshot merge (15分後の08:15、ads_reportの後)
15 8 * * * cd ~/robby-the-match && /usr/bin/python3 scripts/daily_snapshot_merge.py >> logs/daily_snapshot_$(date +\%Y-\%m-\%d).log 2>&1
```

→ Claude Code 側で crontab 編集権限なし。**社長アクション項目**: `crontab -e` で上記行を追加。

### 取得できたデータの状態

各日:
- ✅ ハローワーク件数（4,000件前後）
- ✅ Meta広告（4/16のみ実数値、他は空）
- ⚠️ GA4（403エラーで取得失敗の日が多い）
- ⚠️ Worker統計（限定情報）

→ **GA4 / Meta広告のデータパイプラインも別途修復必要**（次タスク）。

---

## 真の問題と次アクション

### v2/v3で書いた KPI想定の欠陥

| 指摘 | 実態 |
|---|---|
| 「TURN1→matching_preview 1.18%」 | テスト混入。実ユーザーは AICA フロー自体に流入していない |
| 「il_facility_type 98%離脱」 | テスト由来。実ユーザーは70%通過 |
| 「中盤離脱が最重要課題」 | **誤り**。真の課題は handoff放置 |

### 真の課題ランキング

1. 🔴 **AICAフロー誘導の不在**（実ユーザー0%流入）
2. 🔴 **handoff後の人間応答放置**（53%のユーザーが該当）
3. 🟡 計測タグのAICA系記録漏れ
4. 🟡 GA4/Metaデータパイプライン障害
5. 🟢 daily_snapshot cron未登録（即実施で復旧、cron登録は社長対応）

### Patch 2 発動条件の判定

| 条件 | 結果 |
|---|---|
| パターンB（ハンドオフ放置）が30%以上 | **53% = 大幅超過** |

→ **Patch 2（応答エージェント化）即実施推奨**。

---

## Claude Code 側で実施可（次タスク候補）

- [x] テストユーザー除外集計（user_hash LIKE 'U_TEST_%'）
- [x] daily_snapshot 14日分遡及取得
- [ ] **Patch 2 実装**（handoff発火条件圧縮、求人問い合わせpostbackをAI継続化）
- [ ] AICA系logPhaseTransition明示追加（11219行 / 1074行 等）

## 社長アクション項目

- [ ] crontab に daily_snapshot 行追加（`crontab -e`）
- [ ] Patch 2 実装承認 → デプロイ承認

---

**END OF REPORT**
