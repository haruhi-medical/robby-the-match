# worker.js 整合性検証レポート

実施日: 2026-04-06

---

## 1. 構文チェック

```
node --check api/worker.js → OK（エラーなし）
```

**結果: PASS**

---

## 2. フェーズ整合性（entry.phase 代入 vs switch case）

### entry.phase に直接代入される16フェーズ

ai_consultation, apply_confirm, apply_consent, apply_info, career_sheet,
condition_change, handoff, handoff_phone_check, handoff_phone_number,
handoff_phone_time, il_area, il_subarea, interview_prep, matching,
nurture_warm, welcome

### buildPhaseMessage switch に存在する32 case

welcome, il_area, il_subarea, il_department, il_workstyle, il_urgency,
il_facility_type, matching_preview, matching_browse, nurture_warm,
nurture_subscribed, nurture_stay, condition_change, area_notify_optin,
faq_free, faq_salary, faq_no_phone, faq_nightshift, faq_timing,
faq_stealth, faq_holiday, matching, ai_consultation, apply_info,
apply_consent, career_sheet, apply_confirm, interview_prep,
handoff_phone_check, handoff_phone_time, handoff_phone_number, handoff

### switchにあるがentry.phaseに直接代入されない16フェーズ

area_notify_optin, faq_free, faq_holiday, faq_nightshift, faq_no_phone,
faq_salary, faq_stealth, faq_timing, il_department, il_facility_type,
il_urgency, il_workstyle, matching_browse, matching_preview,
nurture_stay, nurture_subscribed

→ 全て `nextPhase` 変数経由（L5917: `entry.phase = nextPhase`）で設定される。問題なし。

### 特殊フェーズ

- `matching_more`: switchにないが L6112 で専用分岐あり（10件超で matching に遷移）
- `handoff_silent`: switchにないが L5901/L6551 で専用分岐あり（Slack転送のみ）

**結果: PASS（全フェーズに到達パスあり）**

---

## 3. postbackデータ整合性

### Flex Message等で定義されるpostback data キー

handoff, matching_preview, nurture, phone_check, welcome, match

### params.has() で処理される25キー

il_pref, il_other, il_area, il_ft, il_dept, il_ws, il_urg,
matching_preview, matching_browse, cond_change, nurture, faq, match,
phone_check, phone_time, handoff, welcome, consent, consult,
area_welcome, fallback, apply, resume, sheet, prep

### 分析

- postback data側の全キー（handoff, matching_preview, nurture, phone_check, welcome, match）は params.has() に存在する
- params.has()にしか存在しないキー（il_pref, il_other等）はテンプレートリテラルやLINE Flex内で動的生成される

**結果: PASS（未処理のpostbackなし）**

---

## 4. D1 jobs検索 SQL構文

```sql
SELECT id, facility_name, work_location, employment_type, salary_text,
       description, welfare FROM jobs WHERE 1=1
  AND (work_location LIKE ? OR work_location LIKE ? ...)  -- 動的バインド
```

- `WHERE 1=1` + 動的 `AND` 追加パターン: 正常
- パラメータバインド（`?`）使用: SQLインジェクション対策OK
- `cities.map(() => 'work_location LIKE ?').join(' OR ')` で動的OR構築: 構文正常

**結果: PASS**

---

## 5. AREA_CITY_MAP 整合性

### 定義済みエリア（21エリア）

| カテゴリ | エリアキー |
|---------|-----------|
| 神奈川 | yokohama_kawasaki, shonan_kamakura, sagamihara_kenoh, yokosuka_miura, odawara_kensei, kanagawa_all |
| 東京 | tokyo_included, tokyo_23ku, tokyo_tama |
| 千葉 | chiba_tokatsu, chiba_uchibo, chiba_inba, chiba_sotobo, chiba_all |
| 埼玉 | saitama_south, saitama_east, saitama_west, saitama_north, saitama_all |
| その他 | undecided |

- 千葉4サブエリア + 埼玉4サブエリア: 全て定義済み（計40箇所参照あり）
- `_all` エリアは空配列 → prefectureフィルタで検索（正常動作）
- `undecided` は空配列 → 全エリア検索（正常動作）

**結果: PASS**

---

## 6. Worker シークレット

```
CHAT_SECRET_KEY          ✅
LINE_CHANNEL_ACCESS_TOKEN ✅
LINE_CHANNEL_SECRET       ✅
LINE_PUSH_SECRET          ✅
OPENAI_API_KEY            ✅
SLACK_BOT_TOKEN           ✅
SLACK_CHANNEL_ID          ✅
```

7/7 シークレット設定済み。

**結果: PASS**

---

## 総合結果

| チェック項目 | 結果 |
|-------------|------|
| 1. 構文チェック | PASS |
| 2. フェーズ整合性 | PASS |
| 3. postbackデータ整合性 | PASS |
| 4. SQL構文 | PASS |
| 5. AREA_CITY_MAP | PASS |
| 6. シークレット | PASS |

**全6項目 PASS。worker.js に構文エラー・整合性問題なし。**
