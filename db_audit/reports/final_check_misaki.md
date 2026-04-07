# LINE Bot 全フローシミュレーション（ミサキ視点）

> 実施日: 2026-04-06
> 対象ファイル: `api/worker.js`
> ペルソナ: ミサキ（28歳・二交代制看護師・急性期病棟勤務）

---

## ケース1: 標準フロー（東京23区・急性期・内科・日勤・すぐ転職）

### ステップ1: 友だち追加（followイベント）

**Bot応答:**
```
はじめまして！
ナースロビーのロビーです🤖

{N}件の医療機関の中から
あなたにぴったりの職場を見つけます。

完全無料・電話なし・LINE完結。

まずは求人を探してみませんか？
```
**Quick Reply:** `[求人を探す] [年収を知りたい] [まず相談したい] [まだ見てるだけ]`

> ミサキは「求人を探す」をタップ → postback: `welcome=see_jobs`

### ステップ2: il_area（都道府県選択）

**Bot応答:**
```
{N}件の医療機関の中から
あなたにぴったりの職場を見つけます。

まず、どのエリアで働きたいですか？
```
**Quick Reply:** `[東京都] [神奈川県] [千葉県] [埼玉県] [その他の地域]`

> ミサキは「東京都」をタップ → postback: `il_pref=tokyo`
> entry.prefecture = 'tokyo' → nextPhase = "il_subarea"

### ステップ3: il_subarea（東京サブエリア選択）

**Bot応答:**
```
東京都ですね！

━━━━━━━━━━━━━━━
📊 候補: {N}件
━━━━━━━━━━━━━━━

東京のどのあたりが希望ですか？
```
**Quick Reply:** `[23区] [多摩地域] [どこでもOK]`

> ミサキは「23区」をタップ → postback: `il_area=tokyo_23ku`
> entry.area = 'tokyo_23ku_il', entry.areaLabel = '東京23区' → nextPhase = "il_facility_type"

### ステップ4: il_facility_type（施設タイプ選択）

**Bot応答:**
```
東京23区ですね！

━━━━━━━━━━━━━━━
📊 候補: {N}件
━━━━━━━━━━━━━━━

どんな職場が気になりますか？
```
**Quick Reply:** `[急性期病院] [回復期病院] [慢性期病院] [クリニック] [訪問看護] [介護施設] [こだわりなし]`

> ミサキは「急性期病院」をタップ → postback: `il_ft=hospital_acute`
> entry.facilityType = 'hospital', entry.hospitalSubType = '急性期' → nextPhase = "il_department"

### ステップ5: il_department（診療科選択）

**Bot応答:**
```
急性期ですね！
希望の診療科はありますか？
```
**Quick Reply:** `[内科系] [外科系] [整形外科] [循環器] [小児科] [産婦人科] [精神科] [リハビリ] [救急] [こだわりなし]`

> ミサキは「内科系」をタップ → postback: `il_dept=内科`
> entry.department = '内科' → nextPhase = "il_workstyle"

### ステップ6: il_workstyle（働き方選択）

**Bot応答:**
```
病院ですね！

━━━━━━━━━━━━━━━
📊 候補: {N}件
━━━━━━━━━━━━━━━

希望の働き方は？
```
**Quick Reply:** `[日勤のみ] [夜勤ありOK] [パート・非常勤] [夜勤専従]`

> ※ `_isClinic`はfalseなので4択が表示される（正常）
> ミサキは「日勤のみ」をタップ → postback: `il_ws=day`
> entry.workStyle = 'day' → nextPhase = "il_urgency"

### ステップ7: il_urgency（転職意欲）

**Bot応答:**
```
今の転職への気持ちは？
```
**Quick Reply:** `[すぐにでも転職したい] [いい求人があれば] [まずは情報収集]`

> ミサキは「すぐにでも転職したい」をタップ → postback: `il_urg=urgent`
> entry.urgency = 'urgent' → nextPhase = "matching_preview"

### ステップ8: matching_preview（求人カード表示）

**処理:** `generateLineMatching()` が実行される
- D1 jobsテーブル検索: area=tokyo_23ku_il → tokyo_23ku → 23区内の市区町村でフィルタ
- SQL: `WHERE work_location LIKE '%千代田区%' OR ... AND prefecture = '東京都' AND title NOT LIKE '%夜勤%' AND (title LIKE '%内科%' OR description LIKE '%内科%') ORDER BY score DESC LIMIT 5`
- D1結果0件 → EXTERNAL_JOBSフォールバック → さらに0件 → D1施設フォールバック

**Bot応答（求人あり時）:**
```
あなたの条件に近い求人が
見つかりました！

東京23区 × 日勤のみ で {N}件マッチ 🎯
おすすめ順にご紹介します。
```
**+ Flexカルーセル:** 最大5枚の求人カード（月給/賞与/勤務時間/最寄駅/年間休日）
**+ 末尾ナビカード:** `[他の求人を探す] [条件を変えて探す] [直接相談する]`
**+ フォローテキスト:**
```
ナースロビーは病院側の負担が少ないシステムですので、内定に繋がりやすいです。
気軽にお尋ねください！
```
**Quick Reply:** `[他の求人も見る] [条件を変える] [直接相談する] [あとで見る]`

### ステップ9: 「他の求人も見る」1回目

> ミサキは「他の求人も見る」をタップ → postback: `matching_preview=more`
> nextPhase = "matching_browse" → offset 0 → newOffset = 5
> `generateLineMatching(entry, env, 5)` 実行 → 次の5件をカルーセル表示

### ステップ10: 「他の求人も見る」2回目 → 10件上限

> ミサキは再度「他の求人を探す」をタップ → postback: `matching_preview=more`
> nextPhase = "matching_browse" → currentOffset = 5 → newOffset = 10
> **10 >= 10 → 上限メッセージ表示:**

```
ここまで10件の求人をご紹介しました。

この中にピンとくるものがなければ、担当者があなたの条件に合う求人を直接お探しします。

非公開求人や、気になる医療機関があれば逆指名で問い合わせることも可能です。
```
**Quick Reply:** `[担当者に探してもらう] [条件を変えて探す] [今日はここまで]`

### 判定: **PASS**

- 全7ステップ（都道府県→サブエリア→施設→診療科→働き方→意欲→マッチング）が正常に遷移
- 急性期病院選択時にil_department（診療科）が挿入される
- 求人カードはFlexカルーセルで月給・賞与・勤務時間・最寄駅・年間休日を表示
- 「もっと見る」2回目で10件上限メッセージが正しく表示される

---

## ケース2: 千葉・船橋・クリニック・パート

### ステップ1: 友だち追加 → 「求人を探す」

（ケース1と同じウェルカムメッセージ）

### ステップ2: il_area → 「千葉県」

> postback: `il_pref=chiba` → entry.prefecture = 'chiba' → nextPhase = "il_subarea"

### ステップ3: il_subarea（千葉サブエリア選択）

**Bot応答:**
```
千葉県ですね！

━━━━━━━━━━━━━━━
📊 候補: {N}件
━━━━━━━━━━━━━━━

千葉のどのあたりが希望ですか？
```
**Quick Reply:** `[船橋・松戸・柏] [千葉市・内房] [成田・印旛] [外房・房総] [どこでもOK]`

> ミサキは「船橋・松戸・柏」をタップ → postback: `il_area=chiba_tokatsu`
> entry.area = 'chiba_tokatsu_il', entry.areaLabel = '船橋・松戸・柏'
> AREA_CITY_MAP[chiba_tokatsu] = ['船橋市', '市川市', '松戸市', '柏市', ...] ← 正常にマッピング

### ステップ4: il_facility_type → 「クリニック」

> postback: `il_ft=clinic`
> entry.facilityType = 'clinic', entry._isClinic = true → nextPhase = "il_workstyle"
> ※ クリニック選択時は il_department（診療科）をスキップ → 直接 il_workstyle へ

### ステップ5: il_workstyle（クリニック用2択）

**Bot応答:**
```
クリニックですね！

━━━━━━━━━━━━━━━
📊 候補: {N}件
━━━━━━━━━━━━━━━

希望の働き方は？
```
**Quick Reply:** `[常勤（日勤）] [パート・非常勤]`

> **`_isClinic = true` → 2択（常勤/パート）が表示される** ← 正常動作
> ミサキは「パート・非常勤」をタップ → postback: `il_ws=part`
> entry.workStyle = 'part'

### ステップ6-7: il_urgency → matching_preview

（ケース1と同様の流れ）

**マッチング処理:**
- D1 jobs: `WHERE work_location LIKE '%船橋市%' OR '%市川市%' OR '%松戸市%' OR ... AND emp_type LIKE '%パート%'`
- EXTERNAL_JOBS: areaKeys = `q3_chiba_tokatsu_il` → `["船橋・市川", "柏・松戸"]`
- 施設タイプフィルタ: `matchesFacilityType()` で `['クリニック', '診療所', '医院']` を含むもののみ

### 判定: **PASS**

- 千葉県 → サブエリア選択（5択: 船橋・松戸・柏 / 千葉市・内房 / 成田・印旛 / 外房・房総 / どこでもOK）が正常表示
- クリニック選択 → `_isClinic = true` → 働き方が**2択**（常勤/パート）に正しく切り替わる
- パート選択 → `il_ws=part` が正常記録
- AREA_CITY_MAP[chiba_tokatsu] に船橋市が含まれており、D1/EXTERNAL_JOBSの検索対象に正しくマッピング

---

## ケース3: 「その他の地域」選択（エリア外対応）

### ステップ1-2: 友だち追加 → 「求人を探す」→ il_area

### ステップ3: 「その他の地域」選択

> postback: `il_pref=other`
> entry.prefecture = 'other', entry.area = 'undecided_il', entry.areaLabel = '全エリア'
> nextPhase = "il_subarea"

### ステップ4: il_subarea（エリア外メッセージ表示）

**Bot応答（正直メッセージ）:**
```
現在ナースロビーでは、東京・神奈川・千葉・埼玉の求人をご紹介しています。

お住まいの地域は準備中です。
以下からお選びください👇
```
**Quick Reply（3選択肢）:**
- `[関東の求人を見る]` → postback: `il_other=see_kanto` → il_facility_typeへ
- `[エリア拡大時に通知]` → postback: `il_other=notify_optin` → area_notify_optinへ
- `[スタッフに相談]` → postback: `il_other=consult_staff` → handoff_phone_checkへ

### 各選択肢の遷移確認:

**A. 「関東の求人を見る」:**
> nextPhase = "il_facility_type" → area=undecided_il のまま通常フローに合流

**B. 「エリア拡大時に通知」:**
> entry.areaNotifyOptIn = true → nextPhase = "area_notify_optin"
> Bot応答:
```
ありがとうございます！
対応エリアが拡大したらこのLINEでお知らせしますね。

それまでの間、転職に役立つ情報をお届けします。
```
> → phase = "nurture_warm" に自動遷移

**C. 「スタッフに相談」:**
> nextPhase = "handoff_phone_check" → 担当者引き継ぎフローへ

### 判定: **PASS**

- 「その他の地域」選択時に正直メッセージ（対応エリア外を正直に伝える）が表示される
- 3選択肢（関東求人を見る / エリア拡大通知 / スタッフに相談）が正しく表示される
- 各選択肢の遷移先が正常

---

## ケース4: handoff完全フロー（電話OK → 番号 → 完了）

> 前提: ケース1のmatching_preview表示後、求人カードの「この施設について聞く」をタップ

### ステップ1: 求人カード「この施設について聞く」

> postback: `match=detail&idx=0`
> entry.interestedFacility = matchingResults[0].n
> nextPhase = "handoff_phone_check"

### ステップ2: handoff_phone_check（電話確認）

**Bot応答:**
```
担当者に引き継ぎますね。

お電話は控えた方が良いですか？
```
**Quick Reply:** `[はい（LINEでお願いします）] [いいえ（電話OK）]`

> ミサキは「いいえ（電話OK）」をタップ → postback: `phone_check=phone_ok`
> entry.phonePreference = 'phone_ok' → nextPhase = "handoff_phone_time"

### ステップ3: handoff_phone_time（時間帯確認）

**Bot応答:**
```
ありがとうございます！
ご都合の良い時間帯はありますか？
```
**Quick Reply:** `[午前中] [午後] [夕方以降] [いつでもOK]`

> ミサキは「夕方以降」をタップ → postback: `phone_time=evening`
> entry.preferredCallTime = 'evening' → nextPhase = "handoff_phone_number"

### ステップ4: handoff_phone_number（電話番号入力）

**Bot応答:**
```
夕方以降ですね！

📞 お電話番号を教えてください。
（例: 090-1234-5678）

※担当者からのご連絡にのみ使用します。
```

> ミサキは「090-1234-5678」と入力（テキストメッセージ）
> handleFreeTextInput: phase === "handoff_phone_number"
> digits = '09012345678' → /^0[0-9]{9,10}$/ にマッチ → entry.phoneNumber = '09012345678'
> return "handoff"

### ステップ5: handoff（完了メッセージ）

**Bot応答:**
```
担当者に引き継ぎました。
24時間以内にご希望の時間帯（evening）にお電話またはLINEでご連絡いたしますので、少しお待ちください。

気になることがあればいつでもメッセージしてくださいね。
```

> ※ processLineEvents内の直接テキスト生成（L6221-6223）では `entry.preferredCallTime` をそのまま埋め込んでいる
> 表示: `ご希望の時間帯（evening）に` ← **英語のまま表示されている**

> 一方、buildPhaseMessage("handoff") では日本語ラベル変換あり:
> `timeLabels = { morning: '午前中', afternoon: '午後', evening: '夕方以降', anytime: 'いつでもOK' }`
> → 実際にはprocessLineEvents内のL6221-6223の方が実行される（nextPhase === "handoff"のとき）

**Slack通知:** `sendHandoffNotification()` が実行され、全情報がSlackに送信される

### 判定: **FAIL**

- 電話確認→時間帯→番号入力→完了の全フローは正常に遷移する
- 「24時間以内にご連絡」メッセージは表示される
- **問題点:** processLineEvents L6222で `entry.preferredCallTime` が日本語変換されず `evening` のまま表示される。`buildPhaseMessage("handoff")` にはtimeLabels変換があるが、processLineEventsの直接生成コード（L6218-6224）が優先されるため、`ご希望の時間帯（evening）に` と英語が混入する

**修正提案:** L6222の文字列内で `entry.preferredCallTime` を日本語ラベルに変換する:
```javascript
const timeLabels = { morning: '午前中', afternoon: '午後', evening: '夕方以降', anytime: 'いつでもOK' };
const timeText = timeLabels[entry.preferredCallTime] || '';
```

---

## ケース5: 条件変更（部分変更UIの確認）

> 前提: ケース1のmatching_preview表示後

### ステップ1: 「条件を変えて探す」をタップ

> postback: `matching_preview=deep` → nextPhase = "condition_change"

### ステップ2: condition_change（現在の条件表示 + 部分変更選択肢）

**Bot応答:**
```
現在の条件:
📍 エリア: 東京23区
🏥 施設: 病院
⏰ 働き方: 日勤のみ

どの条件を変更しますか？
```
**Quick Reply:** `[エリアを変える] [施設タイプを変える] [働き方を変える] [全部やり直す]`

### 各選択肢の遷移確認:

**A. 「エリアを変える」** → postback: `cond_change=area`
- entry.area, areaLabel, prefecture を削除
- matchingResults, browsedJobIds を削除、matchingOffset = 0
- → nextPhase = "il_area"（都道府県選択からやり直し）

**B. 「施設タイプを変える」** → postback: `cond_change=facility`
- entry.facilityType, hospitalSubType, department を削除
- → nextPhase = "il_facility_type"（施設選択からやり直し。エリアは保持）

**C. 「働き方を変える」** → postback: `cond_change=workstyle`
- entry.workStyle, _isClinic を削除
- → nextPhase = "il_workstyle"（働き方選択からやり直し。エリア・施設は保持）

**D. 「全部やり直す」** → postback: `cond_change=all`
- area, areaLabel, prefecture, facilityType, hospitalSubType, department, workStyle, urgency, _isClinic を全削除
- → nextPhase = "il_area"（最初からやり直し）

### 判定: **PASS**

- 現在の条件（エリア/施設/働き方）が正しく表示される
- 4つの部分変更選択肢が表示される
- 各選択肢で該当フィールドのみリセットされ、他の条件は保持される
- matchingResults/browsedJobIds/matchingOffsetが全パターンでリセットされる

---

## 総合結果

| ケース | シナリオ | 判定 |
|--------|----------|------|
| 1 | 標準フロー（東京23区・急性期・内科・日勤・すぐ転職） | **PASS** |
| 2 | 千葉・船橋・クリニック・パート | **PASS** |
| 3 | 「その他の地域」選択（エリア外対応） | **PASS** |
| 4 | handoff完全フロー（電話OK→番号→完了） | **FAIL** |
| 5 | 条件変更（部分変更UI） | **PASS** |

## 検出された問題

### BUG: handoff完了メッセージで時間帯が英語表示（ケース4）

- **場所:** `processLineEvents` L6221-6223
- **症状:** `entry.preferredCallTime` が `evening` のまま表示される（日本語ラベル変換なし）
- **影響:** ユーザーに `ご希望の時間帯（evening）に` と表示される
- **修正案:** `buildPhaseMessage("handoff")` と同じ `timeLabels` 辞書を使って日本語変換する
- **該当コード:**
  ```javascript
  // L6222（現在）
  `24時間以内に${entry.preferredCallTime ? `ご希望の時間帯（${entry.preferredCallTime}）に` : ""}お電話または...`
  // 修正後
  const _tl = { morning: '午前中', afternoon: '午後', evening: '夕方以降', anytime: 'いつでもOK' };
  const _tt = entry.preferredCallTime ? _tl[entry.preferredCallTime] || entry.preferredCallTime : '';
  `24時間以内に${_tt ? `${_tt}に` : ""}お電話または...`
  ```
