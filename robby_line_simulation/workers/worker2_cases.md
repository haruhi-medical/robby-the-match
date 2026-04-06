# Worker 2 - LINE Bot Simulation Test Cases (関東 Focus)

> Generated: 2026-04-06
> Worker: 2 of N
> Assignment: 関東 (50 cases)
> Distribution: 茨城(5), 栃木(5), 群馬(5), 東京(5), 神奈川(5), 千葉(5), 埼玉(5), spare(5), cross(10)
> Mix: 30 standard, 12 boundary, 8 adversarial

---

## SUPPORTED PREFECTURES (東京/神奈川/千葉/埼玉)

---

### Case W2-001
- **Prefecture:** 東京都
- **Region Block:** 関東
- **Case Type:** standard
- **User Profile:** 30歳、急性期病院勤務、日勤希望、品川区在住
- **Entry Route:** LINE友だち追加
- **Difficulty:** Easy

**Scenario:** 東京23区で日勤のみの急性期病院を探す標準フロー。全ステップがボタン操作。

**Conversation Flow:**
1. [Bot] Welcome → 「求人を見る」ボタン表示
2. [User] 「求人を見る」タップ
3. [Bot] 「24,488件の医療機関の中から...まず、どのエリアで働きたいですか？」→ 5択QR
4. [User] 「東京都」タップ (il_pref=tokyo)
5. [Bot] 「東京都ですね！📊 候補: 12,748件 東京のどのあたりが希望ですか？」→ 23区/多摩/どこでもOK
6. [User] 「23区」タップ (il_area=tokyo_23ku)
7. [Bot] 「23区ですね！📊 候補: X件 どんな職場が気になりますか？」→ 7択
8. [User] 「急性期病院」タップ (il_ft=hospital_acute)
9. [Bot] 「希望の診療科はありますか？」→ 10択
10. [User] 「こだわりなし」タップ (il_dept=any)
11. [Bot] 「希望の働き方は？」→ 4択
12. [User] 「日勤のみ」タップ (il_ws=day)
13. [Bot] 「今の転職への気持ちは？」→ 3択
14. [User] 「すぐにでも転職したい」タップ (il_urg=urgent)
15. [Bot] matching_preview → Flexカルーセル5件表示

**System Behavior Evaluation:**
- il_pref=tokyo → prefecture=tokyo → il_subarea表示（正常）
- il_area=tokyo_23ku → area=tokyo_23ku_il → AREA_CITY_MAP参照で23区全区検索
- D1クエリ: prefecture='東京都' + AREA_CITY_MAP 23区名リスト → 大量ヒット期待
- 急性期 + 日勤のみ → 候補が絞られるがDB 12,748件なので十分な結果が出るはず

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: no
- National Expansion Risk: N/A (supported)

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** N/A
**Retry Needed:** no
**Auditor Comment:** 最も基本的なハッピーパス。東京23区はDB最大ボリュームゾーンで問題なし。

---

### Case W2-002
- **Prefecture:** 東京都
- **Region Block:** 関東
- **Case Type:** standard
- **User Profile:** 26歳、新卒3年目、多摩地域在住、訪問看護に興味
- **Entry Route:** LINE友だち追加
- **Difficulty:** Easy

**Scenario:** 東京多摩地域で訪問看護を探す。クリニック以外なので働き方選択あり。

**Conversation Flow:**
1. [Bot] Welcome → 「求人を見る」
2. [User] タップ
3. [Bot] il_area → 5択
4. [User] 「東京都」タップ
5. [Bot] il_subarea → 「東京のどのあたりが希望ですか？」
6. [User] 「多摩地域」タップ (il_area=tokyo_tama)
7. [Bot] il_facility_type → 候補数表示 + 7択
8. [User] 「訪問看護」タップ (il_ft=visiting)
9. [Bot] il_workstyle → 4択（il_departmentスキップ: 病院以外）
10. [User] 「パート・非常勤」タップ (il_ws=part)
11. [Bot] il_urgency → 3択
12. [User] 「いい求人があれば」タップ (il_urg=good)
13. [Bot] matching_preview → Flexカルーセル表示

**System Behavior Evaluation:**
- 多摩地域: tokyo_tama → AREA_CITY_MAP['tokyo_tama'] = 八王子市/立川市/武蔵野市等9市
- 訪問看護はil_departmentスキップ（正常）
- パート希望 → workStyle=part
- 多摩の訪問看護ステーションはDB件数次第。D1に訪問看護STデータがあれば表示

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: no
- National Expansion Risk: N/A

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** N/A
**Retry Needed:** no
**Auditor Comment:** 多摩×訪問看護×パートの組み合わせは候補が少ない可能性あるが、0件でもnurture導線あり。

---

### Case W2-003
- **Prefecture:** 東京都
- **Region Block:** 関東
- **Case Type:** boundary
- **User Profile:** 35歳、ベテラン看護師、東京と神奈川の境目（町田市）
- **Entry Route:** LINE友だち追加
- **Difficulty:** Medium

**Scenario:** 「どこでもOK」を選んだ場合、東京都と神奈川県の境界エリアの結果が出るか。tokyo_includedは新宿/渋谷/品川/世田谷/大田+横浜/川崎を含む。

**Conversation Flow:**
1. [Bot] Welcome → 「求人を見る」
2. [User] タップ
3. [Bot] il_area → 5択
4. [User] 「東京都」タップ
5. [Bot] il_subarea → 23区/多摩/どこでもOK
6. [User] 「どこでもOK」タップ (il_area=tokyo_included)
7. [Bot] il_facility_type → 候補数表示 + 7択
8. [User] 「こだわりなし」タップ (il_ft=any)
9. [Bot] il_workstyle → 4択
10. [User] 「夜勤ありOK」タップ
11. [Bot] il_urgency → 3択
12. [User] 「すぐにでも転職したい」
13. [Bot] matching_preview → 結果表示

**System Behavior Evaluation:**
- tokyo_included の AREA_CITY_MAP = 新宿区/渋谷区/品川区/世田谷区/大田区 + 横浜市/川崎市
- 東京の「どこでもOK」なのに横浜・川崎が含まれる。ユーザーは東京全域を期待するが、実際は23区一部+神奈川一部
- 町田市は多摩にも tokyo_included にも入っていない
- countCandidatesD1: AREA_PREF_MAP[tokyo_included] = null → フィルタなし → 全DB検索になる

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: yes
- National Expansion Risk: AREA_CITY_MAPのtokyo_includedは限定的だが、D1クエリではフィルタなし（全県表示）になる矛盾

**Failure Category:** JOB_MATCH_FAIL
**Severity:** Medium
**Fix Proposal:** tokyo_included のD1クエリは prefecture='東京都' にすべき。現状はフィルタなしで全DB24,488件が対象になり、神奈川/千葉/埼玉の結果も混ざる。AREA_CITY_MAPとcountCandidatesD1のロジックが不整合。
**Retry Needed:** yes
**Auditor Comment:** 候補数カウントと実際のマッチングで異なるフィルタが適用される可能性。ユーザー体験は「東京」選択なのに神奈川の施設が出る矛盾。

---

### Case W2-004
- **Prefecture:** 東京都
- **Region Block:** 関東
- **Case Type:** adversarial
- **User Profile:** 40歳、看護師、LINEに不慣れ
- **Entry Route:** LINE友だち追加
- **Difficulty:** Hard

**Scenario:** il_area表示中にボタンを使わず「新宿で働きたい」とフリーテキスト入力。

**Conversation Flow:**
1. [Bot] Welcome → 「求人を見る」
2. [User] タップ
3. [Bot] il_area → 5択QR表示
4. [User] 「新宿で働きたい」（フリーテキスト）
5. [Bot] unexpectedTextCount++ → Quick Reply再表示（同じ5択）
6. [User] 「東京の病院ありますか？」（フリーテキスト再度）
7. [Bot] unexpectedTextCount++ → Quick Reply再表示
8. [User] 「東京都」タップ（ようやくボタン利用）
9. [Bot] il_subarea → 正常続行

**System Behavior Evaluation:**
- phase=il_area中のフリーテキスト → handleLineText内で unexpectedTextCount++ → return null
- return null → buildPhaseMessage再送（同じQuick Reply表示）
- TEXT_TO_POSTBACK辞書にはphaseToExpectedPrefixが空オブジェクト → テキスト→postback変換は機能しない
- ユーザーが「新宿」と言っても「東京都」ボタンに誘導されるだけ

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes（ボタン利用後）
- Reached Next Action: yes
- Region Bias Signs: no
- National Expansion Risk: N/A

**Failure Category:** INPUT_LOCK
**Severity:** High
**Fix Proposal:** il_area phase中のフリーテキストで地名（新宿/渋谷/横浜等）を検知し、該当の都道府県+サブエリアに自動マッピングする機能追加。または「下のボタンからお選びください」と明示的にガイドするメッセージ。
**Retry Needed:** no
**Auditor Comment:** 高齢者やスマホ不慣れなユーザーはQRボタンに気づかず離脱する。看護師の年齢層は幅広いため深刻。

---

### Case W2-005
- **Prefecture:** 東京都
- **Region Block:** 関東
- **Case Type:** boundary
- **User Profile:** 32歳、夜勤専従希望、クリニック選択
- **Entry Route:** LINE友だち追加
- **Difficulty:** Medium

**Scenario:** クリニックを選択すると workStyle が自動で 'day' に設定され il_workstyle がスキップされる。夜勤専従希望者がクリニックを選んだ場合の矛盾。

**Conversation Flow:**
1. [Bot] Welcome → 「求人を見る」
2. [User] タップ
3. [Bot] il_area → 5択
4. [User] 「東京都」→「23区」タップ
5. [Bot] il_facility_type → 7択
6. [User] 「クリニック」タップ (il_ft=clinic)
7. [Bot] il_urgency → 直接表示（il_workstyle スキップ、workStyle='day' 自動設定）
8. [User] 「すぐにでも転職したい」タップ
9. [Bot] matching_preview → 日勤クリニックのみ表示

**System Behavior Evaluation:**
- clinic選択 → entry.workStyle = 'day' + _clinicSkip = true → il_urgency直行
- 夜勤専従希望の看護師がクリニック選んだ場合、本当は美容クリニック等の夜間帯勤務もあり得る
- しかしBot側は「クリニック=日勤」と決め打ち → ユーザーの本来の希望を聞かない

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: no
- National Expansion Risk: N/A

**Failure Category:** JOB_MATCH_FAIL
**Severity:** Medium
**Fix Proposal:** クリニック選択時も workStyle を聞くか、「クリニックは基本的に日勤です。日勤でよろしいですか？」の確認を入れる。美容クリニック等は夜間営業もある。
**Retry Needed:** no
**Auditor Comment:** 設計判断としてはクリニック=日勤は合理的だが、ユーザーの期待との不一致リスクあり。

---

### Case W2-006
- **Prefecture:** 神奈川県
- **Region Block:** 関東
- **Case Type:** standard
- **User Profile:** 28歳（ペルソナ・ミサキ相当）、横浜市在住、回復期希望、夜勤あり
- **Entry Route:** LINE友だち追加
- **Difficulty:** Easy

**Scenario:** ペルソナに最も近い標準ユーザー。横浜・川崎エリアで回復期病院を探す。

**Conversation Flow:**
1. [Bot] Welcome → 「求人を見る」
2. [User] タップ
3. [Bot] il_area → 5択
4. [User] 「神奈川県」タップ (il_pref=kanagawa)
5. [Bot] il_subarea → 「神奈川県ですね！📊 候補: 5,165件 神奈川のどのあたりが希望ですか？」→ 6択
6. [User] 「横浜・川崎」タップ (il_area=yokohama_kawasaki)
7. [Bot] il_facility_type → 候補数表示 + 7択
8. [User] 「回復期病院」タップ (il_ft=hospital_recovery)
9. [Bot] il_department → 10択
10. [User] 「リハビリ」タップ (il_dept=リハビリテーション科)
11. [Bot] il_workstyle → 4択
12. [User] 「夜勤ありOK」タップ (il_ws=twoshift)
13. [Bot] il_urgency → 3択
14. [User] 「いい求人があれば」タップ (il_urg=good)
15. [Bot] matching_preview → Flexカルーセル5件表示

**System Behavior Evaluation:**
- 神奈川 → 横浜・川崎: AREA_CITY_MAP['yokohama_kawasaki'] = ['横浜市', '川崎市']
- 回復期 + リハビリ科: D1クエリで category LIKE '%回復期%' AND department検索
- 横浜市は神奈川最大のDB件数。回復期病院も多数存在
- ペルソナ・ミサキのプロファイルに最も近いパス

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: no
- National Expansion Risk: N/A

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** N/A
**Retry Needed:** no
**Auditor Comment:** 事業のコアターゲット。このフローが完璧に動くことが最重要。

---

### Case W2-007
- **Prefecture:** 神奈川県
- **Region Block:** 関東
- **Case Type:** standard
- **User Profile:** 45歳、ベテラン看護師、小田原市在住、慢性期希望
- **Entry Route:** LINE友だち追加
- **Difficulty:** Easy

**Scenario:** 県西・小田原エリアで慢性期病院を探す。DB件数が少ないエリア。

**Conversation Flow:**
1. [Bot] Welcome → 「求人を見る」
2. [User] タップ
3. [Bot] il_area → 5択
4. [User] 「神奈川県」タップ
5. [Bot] il_subarea → 6択
6. [User] 「小田原・県西」タップ (il_area=odawara_kensei)
7. [Bot] il_facility_type → 候補数表示（少なめ予想）+ 7択
8. [User] 「慢性期病院」タップ
9. [Bot] il_department → 10択
10. [User] 「内科系」タップ (il_dept=内科)
11. [Bot] il_workstyle → 4択
12. [User] 「日勤のみ」タップ
13. [Bot] il_urgency → 3択
14. [User] 「まずは情報収集」タップ
15. [Bot] matching_preview → 結果表示（0〜3件の可能性）

**System Behavior Evaluation:**
- odawara_kensei: 小田原市/南足柄市/箱根町等15市町 → DB件数は限定的
- 慢性期 + 内科 + 日勤のみ → かなり絞り込まれる
- 0件の場合: 「条件に合う新着が出たらLINEでお知らせ」+ nurture導線
- suggestRelaxation: matchCount < 3 の場合エリア拡大提案

**Results:**
- Drop-off risk: yes（0件の場合）
- Reached Job Proposal: yes（1件以上の場合）/ no（0件の場合）
- Reached Next Action: yes（nurture導線あり）
- Region Bias Signs: no
- National Expansion Risk: N/A

**Failure Category:** JOB_MATCH_FAIL
**Severity:** Medium
**Fix Proposal:** 県西エリアは件数が少ないため、0件時に「湘南・鎌倉エリアまで広げると○件見つかります」等の具体的な緩和提案が有効。
**Retry Needed:** yes
**Auditor Comment:** 県西は事業発祥地（小田原）。ここで0件は致命的。最低3件は表示できる緩和ロジックが必要。

---

### Case W2-008
- **Prefecture:** 神奈川県
- **Region Block:** 関東
- **Case Type:** boundary
- **User Profile:** 33歳、横須賀市在住、介護施設希望
- **Entry Route:** LINE友だち追加
- **Difficulty:** Medium

**Scenario:** 横須賀・三浦エリアは最も狭い（横須賀市+三浦市の2市のみ）。介護施設の絞り込みで0件リスク。

**Conversation Flow:**
1. [Bot] Welcome → 「求人を見る」
2. [User] タップ → 「神奈川県」→「横須賀・三浦」タップ
3. [Bot] il_facility_type → 候補数表示
4. [User] 「介護施設」タップ
5. [Bot] il_workstyle → 4択
6. [User] 「パート・非常勤」タップ
7. [Bot] il_urgency → 3択
8. [User] 「いい求人があれば」タップ
9. [Bot] matching_preview → 0〜2件？

**System Behavior Evaluation:**
- yokosuka_miura: ['横須賀市', '三浦市'] のみ
- 介護施設 + パート → DB内に介護施設カテゴリがあるか次第
- CATEGORY_MAP['care'] = '介護施設' → D1検索対応
- 2市のみの狭域 → 件数リスク高

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes（件数次第）
- Reached Next Action: yes（nurture導線）
- Region Bias Signs: no
- National Expansion Risk: N/A

**Failure Category:** JOB_MATCH_FAIL
**Severity:** Medium
**Fix Proposal:** 狭域エリア（横須賀三浦/県西）で件数が少ない場合、自動的に隣接エリアを含める「エリア拡大提案」をmatching_preview内に組み込む。
**Retry Needed:** yes
**Auditor Comment:** 横須賀・三浦は17施設（MEMORY.md記載）。介護施設に絞ると数件になる可能性大。

---

### Case W2-009
- **Prefecture:** 神奈川県
- **Region Block:** 関東
- **Case Type:** standard
- **User Profile:** 29歳、湘南エリア希望、急性期外科
- **Entry Route:** LINE友だち追加
- **Difficulty:** Easy

**Scenario:** 湘南・鎌倉エリアで急性期病院の外科系を探す。

**Conversation Flow:**
1. [Bot] Welcome → 「求人を見る」
2. [User] タップ → 「神奈川県」→「湘南・鎌倉」タップ (il_area=shonan_kamakura)
3. [Bot] il_facility_type → 候補数表示 + 7択
4. [User] 「急性期病院」タップ
5. [Bot] il_department → 10択
6. [User] 「外科系」タップ (il_dept=外科)
7. [Bot] il_workstyle → 4択
8. [User] 「夜勤ありOK」タップ
9. [Bot] il_urgency → 3択
10. [User] 「すぐにでも転職したい」タップ
11. [Bot] matching_preview → 結果表示

**System Behavior Evaluation:**
- shonan_kamakura: 藤沢市/茅ヶ崎市/鎌倉市/逗子市/葉山町/寒川町
- 急性期 + 外科 → 湘南エリアの総合病院（藤沢市民病院、茅ヶ崎市立病院等）
- 6市町で範囲はそこそこ。急性期外科は需要あり

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: no
- National Expansion Risk: N/A

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** N/A
**Retry Needed:** no
**Auditor Comment:** 湘南エリアは中間的なDB件数。急性期外科なら結果は出る。

---

### Case W2-010
- **Prefecture:** 神奈川県
- **Region Block:** 関東
- **Case Type:** adversarial
- **User Profile:** 31歳、相模原市在住、条件変更を繰り返すユーザー
- **Entry Route:** LINE友だち追加
- **Difficulty:** Hard

**Scenario:** matching_previewまで到達後、「条件を変えて探す」で最初からやり直しを3回繰り返す。

**Conversation Flow:**
1. [User] 全ステップ完了 → matching_preview表示（1回目: 相模原・県央 × 急性期）
2. [User] 「条件を変えて探す」タップ (matching_preview=deep)
3. [Bot] il_area に戻る（全フィールドリセット？）
4. [User] 「神奈川県」→「横浜・川崎」→ クリニック → il_urgency → matching_preview（2回目）
5. [User] 「条件を変えて探す」タップ（2回目）
6. [Bot] il_area に戻る
7. [User] 「東京都」→「23区」→ 訪問看護 → パート → matching_preview（3回目）
8. [User] 「もっと求人を見る」タップ (matching_preview=more)
9. [Bot] matching_browse → 次の3件表示

**System Behavior Evaluation:**
- matching_preview=deep → nextPhase = "il_area" → intake_lightやり直し
- 問題: il_area に戻った時、前回の entry フィールド（area, prefecture等）がリセットされるか？
- il_pref 選択時に delete entry.area / entry.workStyle 等のリセット処理あり → OK
- 3回やり直しても技術的にはセッションは継続

**Results:**
- Drop-off risk: yes（繰り返しで疲弊）
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: no
- National Expansion Risk: N/A

**Failure Category:** UX_DROP
**Severity:** Medium
**Fix Proposal:** 2回以上条件変更した場合、「直接ご相談いただければ、もっと細かい条件でお探しします」とhandoff導線を提案。無限ループ防止。
**Retry Needed:** no
**Auditor Comment:** フィールドリセットは正しく動作するが、UX的にループは離脱リスク。

---

### Case W2-011
- **Prefecture:** 千葉県
- **Region Block:** 関東
- **Case Type:** standard
- **User Profile:** 27歳、船橋市在住、クリニック希望
- **Entry Route:** LINE友だち追加
- **Difficulty:** Easy

**Scenario:** 千葉県を選択。サブエリア選択なし（chiba/saitama/otherはil_subarea表示で直接il_facility_typeへ）。

**Conversation Flow:**
1. [Bot] Welcome → 「求人を見る」
2. [User] タップ
3. [Bot] il_area → 5択
4. [User] 「千葉県」タップ (il_pref=chiba)
5. [Bot] il_subarea → 「千葉県ですね！📊 候補: 2,902件 どんな職場が気になりますか？」→ 施設タイプ7択（サブエリアスキップ）
6. [User] 「クリニック」タップ (il_ft=clinic)
7. [Bot] il_urgency → 直行（clinic → workStyle='day' 自動設定、il_workstyleスキップ）
8. [User] 「いい求人があれば」タップ
9. [Bot] matching_preview → 千葉県全域のクリニック結果

**System Behavior Evaluation:**
- il_pref=chiba → PREF_AREA_MAP['chiba'] = 'chiba_all' → area='chiba_all_il'
- il_subarea phase: prefecture === 'chiba' → 東京/神奈川以外 → サブエリアなしで直接facility_type表示
- chiba_all: AREA_CITY_MAP参照で千葉市/船橋市/市川市等13市
- クリニック → workStyle='day' 自動

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: no
- National Expansion Risk: N/A

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** N/A
**Retry Needed:** no
**Auditor Comment:** 千葉県は2,902件でボリューム十分。サブエリアスキップは体験をスムーズにする。

---

### Case W2-012
- **Prefecture:** 千葉県
- **Region Block:** 関東
- **Case Type:** standard
- **User Profile:** 38歳、柏市在住、慢性期内科希望、夜勤専従
- **Entry Route:** LINE友だち追加
- **Difficulty:** Easy

**Scenario:** 千葉県で慢性期病院の内科系、夜勤専従を探す。ニッチな条件。

**Conversation Flow:**
1. [User] 「千葉県」→ 施設タイプ「慢性期病院」→ 診療科「内科系」→ 「夜勤専従」→ 「すぐにでも転職したい」
2. [Bot] matching_preview → 結果表示

**System Behavior Evaluation:**
- 千葉全域(chiba_all) × 慢性期 × 内科 × 夜勤専従 → かなり絞り込まれる
- 夜勤専従は需要はあるが検索条件としてニッチ
- 0件になるリスクあり → nurture導線へ

**Results:**
- Drop-off risk: yes（0件の場合）
- Reached Job Proposal: yes（件数次第）
- Reached Next Action: yes
- Region Bias Signs: no
- National Expansion Risk: N/A

**Failure Category:** JOB_MATCH_FAIL
**Severity:** Low
**Fix Proposal:** 夜勤専従の場合、「夜勤ありOK」の結果も含めて表示する緩和ロジックがあると良い。
**Retry Needed:** no
**Auditor Comment:** ニッチ条件だが千葉2,902件あればある程度ヒットするはず。

---

### Case W2-013
- **Prefecture:** 千葉県
- **Region Block:** 関東
- **Case Type:** boundary
- **User Profile:** 25歳、浦安市在住、東京のディズニーエリアと千葉の境目
- **Entry Route:** LINE友だち追加
- **Difficulty:** Medium

**Scenario:** 浦安在住で「東京と千葉どちらでもいい」と思っているが、1つしか選べない。千葉を選んだが東京の結果も見たくなる。

**Conversation Flow:**
1. [User] 「千葉県」→ クリニック → 「すぐにでも転職したい」
2. [Bot] matching_preview → 千葉のクリニック表示
3. [User] 「条件を変えて探す」タップ
4. [Bot] il_area → 5択
5. [User] 「東京都」→「23区」→ クリニック → matching_preview → 東京のクリニック表示
6. [User] 満足

**System Behavior Evaluation:**
- 複数都道府県を跨いで探したいユーザーには「条件変更」が唯一の手段
- 2回フロー回す必要あり → UX負荷
- 「千葉と東京の両方で探す」という選択肢がない

**Results:**
- Drop-off risk: yes（2回目で離脱リスク）
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: no
- National Expansion Risk: 複数都道府県横断検索の未対応

**Failure Category:** UX_DROP
**Severity:** Medium
**Fix Proposal:** 千葉/埼玉選択時に「東京都も含めて探す」オプション追加。浦安/市川等の千葉西部は東京通勤圏。
**Retry Needed:** no
**Auditor Comment:** 都県境のユーザーは多い。浦安→東京、川口→東京、町田→神奈川等。複数エリア選択機能は優先度高。

---

### Case W2-014
- **Prefecture:** 千葉県
- **Region Block:** 関東
- **Case Type:** adversarial
- **User Profile:** 34歳、成田空港近辺在住
- **Entry Route:** LINE友だち追加
- **Difficulty:** Medium

**Scenario:** 千葉県を選ぶが、成田エリアの施設がDB内にあるか不明。chiba_allのAREA_CITY_MAPには成田市が含まれているが実際のD1データ次第。

**Conversation Flow:**
1. [User] 「千葉県」→ 急性期病院 → 救急 → 夜勤ありOK → 「すぐにでも転職したい」
2. [Bot] matching_preview → 結果表示
3. [User] 結果が千葉市/船橋市ばかりで成田が出ない → 不満

**System Behavior Evaluation:**
- chiba_all は千葉県全域扱いだが AREA_CITY_MAP は13市限定
- 成田市はリストに入っている → D1クエリで address LIKE '%成田市%' は検索される
- ただし実際のDB登録施設が千葉市/船橋市に偏っている可能性
- 急性期×救急は大規模病院限定→成田赤十字等は存在するはず

**Results:**
- Drop-off risk: yes（地元の施設が出ない場合）
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: yes（都市部偏重の可能性）
- National Expansion Risk: DB収録バイアス

**Failure Category:** JOB_MATCH_FAIL
**Severity:** Low
**Fix Proposal:** 千葉県のサブエリア選択を追加（東葛/千葉/房総/北総等）するとミスマッチ減少。
**Retry Needed:** no
**Auditor Comment:** 千葉のサブエリアなしは簡便だが、成田/木更津/館山等の遠方ユーザーには都市部偏重の結果になりがち。

---

### Case W2-015
- **Prefecture:** 千葉県
- **Region Block:** 関東
- **Case Type:** standard
- **User Profile:** 31歳、松戸市在住、訪問看護パート
- **Entry Route:** LINE友だち追加
- **Difficulty:** Easy

**Scenario:** 千葉で訪問看護のパートを探す標準フロー。

**Conversation Flow:**
1. [User] 「千葉県」→ 訪問看護 → パート・非常勤 → 「まずは情報収集」
2. [Bot] matching_preview → 結果表示
3. [User] 「まだ早いかも」相当のボタン選択
4. [Bot] nurture_warm → 通知受け取り or 条件変更の選択肢

**System Behavior Evaluation:**
- 訪問看護 + パート + 情報収集 → urgency=info
- 松戸市は chiba_all のAREA_CITY_MAP内
- nurture導線: 温度感が低い(info)ユーザー向けの適切なフォローアップ

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: no
- National Expansion Risk: N/A

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** N/A
**Retry Needed:** no
**Auditor Comment:** 情報収集段階のユーザーにnurture導線があるのは良い設計。

---

### Case W2-016
- **Prefecture:** 埼玉県
- **Region Block:** 関東
- **Case Type:** standard
- **User Profile:** 29歳、さいたま市在住、回復期リハビリ希望
- **Entry Route:** LINE友だち追加
- **Difficulty:** Easy

**Scenario:** 埼玉県で回復期病院のリハビリ科を探す。

**Conversation Flow:**
1. [User] 「埼玉県」タップ (il_pref=saitama)
2. [Bot] il_subarea → 「埼玉県ですね！📊 候補: 3,673件 どんな職場が気になりますか？」→ 施設タイプ直表示
3. [User] 「回復期病院」→ 「リハビリ」→ 「夜勤ありOK」→ 「いい求人があれば」
4. [Bot] matching_preview → 結果表示

**System Behavior Evaluation:**
- saitama → PREF_AREA_MAP['saitama'] = 'saitama_all' → area='saitama_all_il'
- サブエリアスキップ（千葉同様）
- 回復期 × リハビリは需要高い → 結果期待

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: no
- National Expansion Risk: N/A

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** N/A
**Retry Needed:** no
**Auditor Comment:** 埼玉3,673件で十分。回復期リハビリは看護師需要の定番。

---

### Case W2-017
- **Prefecture:** 埼玉県
- **Region Block:** 関東
- **Case Type:** standard
- **User Profile:** 42歳、川越市在住、介護施設日勤
- **Entry Route:** LINE友だち追加
- **Difficulty:** Easy

**Scenario:** 埼玉で介護施設の日勤を探す。

**Conversation Flow:**
1. [User] 「埼玉県」→ 介護施設 → 日勤のみ → 「まずは情報収集」
2. [Bot] matching_preview → 結果表示

**System Behavior Evaluation:**
- 介護施設 → il_departmentスキップ（病院以外）
- saitama_all: さいたま市/川口市等13市 → 川越市は含まれている
- 介護施設×日勤は一般的な組み合わせ

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: no
- National Expansion Risk: N/A

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** N/A
**Retry Needed:** no
**Auditor Comment:** 問題なし。

---

### Case W2-018
- **Prefecture:** 埼玉県
- **Region Block:** 関東
- **Case Type:** boundary
- **User Profile:** 36歳、越谷市在住、東京と埼玉両方で探したい
- **Entry Route:** LINE友だち追加
- **Difficulty:** Medium

**Scenario:** 越谷在住で東京の北区・足立区にも通勤可能。埼玉を選んだ後に「東京も見たい」と思う。W2-013と同パターンだが埼玉側。

**Conversation Flow:**
1. [User] 「埼玉県」→ 急性期病院 → こだわりなし → 夜勤あり → 「すぐにでも転職したい」
2. [Bot] matching_preview → 埼玉の結果表示
3. [User] 「もっと求人を見る」タップ → matching_browse
4. [Bot] 次の3件 → 埼玉の追加結果
5. [User] 「条件を変えて探す」タップ
6. [Bot] il_area → 今度は「東京都」選択

**System Behavior Evaluation:**
- matching_browse=change → il_area に戻る
- 埼玉→東京の切り替えは可能だが2回フロー必要
- W2-013と同じ構造的問題

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: no
- National Expansion Risk: 複数都県横断

**Failure Category:** UX_DROP
**Severity:** Medium
**Fix Proposal:** 「近隣エリアも含めて探す」オプション。越谷→足立区/葛飾区は通勤圏。
**Retry Needed:** no
**Auditor Comment:** 埼玉南部↔東京北部は実質同じ生活圏。

---

### Case W2-019
- **Prefecture:** 埼玉県
- **Region Block:** 関東
- **Case Type:** adversarial
- **User Profile:** 24歳、新卒2年目、秩父市在住
- **Entry Route:** LINE友だち追加
- **Difficulty:** Hard

**Scenario:** 秩父市はsaitama_allのAREA_CITY_MAPに含まれていない。D1検索で秩父の施設が出ない可能性。

**Conversation Flow:**
1. [User] 「埼玉県」→ 急性期病院 → こだわりなし → 日勤のみ → 「すぐにでも転職したい」
2. [Bot] matching_preview → さいたま市/川口市/所沢市等の結果ばかり
3. [User] 秩父市近辺の施設が出ない → 不満

**System Behavior Evaluation:**
- saitama_all のAREA_CITY_MAP: さいたま市/川口市/所沢市/川越市/越谷市等13市 → 秩父市なし
- D1クエリ: AREA_PREF_MAP['saitama_all'] が未定義 → AREA_CITY_MAP参照 → 13市のみ検索
- 秩父市はDB内に施設があっても検索されない
- countCandidatesD1で AREA_PREF_MAP にsaitama_allがない → AREA_CITY_MAPフォールバック

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes（ただし秩父の施設ではない）
- Reached Next Action: yes
- Region Bias Signs: yes（都市部偏重）
- National Expansion Risk: 郊外/地方エリアのDB漏れ

**Failure Category:** GEO_LOCK
**Severity:** High
**Fix Proposal:** saitama_all は AREA_PREF_MAP に 'saitama_all': '埼玉県' を追加して県全体を検索対象にすべき。現状のAREA_CITY_MAP方式では秩父/熊谷/深谷等が漏れる。千葉も同様（銚子/館山等が漏れる）。
**Retry Needed:** yes
**Auditor Comment:** 重要なバグ。saitama_all/chiba_allはAREA_PREF_MAPにprefecture指定がなく、AREA_CITY_MAPの限定リストしか検索されない。県全体をカバーしていない。

---

### Case W2-020
- **Prefecture:** 埼玉県
- **Region Block:** 関東
- **Case Type:** standard
- **User Profile:** 30歳、草加市在住、精神科希望
- **Entry Route:** LINE友だち追加
- **Difficulty:** Easy

**Scenario:** 埼玉で精神科の急性期病院を探す。

**Conversation Flow:**
1. [User] 「埼玉県」→ 急性期病院 → 精神科 → 夜勤ありOK → 「いい求人があれば」
2. [Bot] matching_preview → 結果表示

**System Behavior Evaluation:**
- 精神科×急性期は特殊だが精神科救急病院は存在
- 草加市はsaitama_all内
- D1でdepartment='精神科'検索

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: no
- National Expansion Risk: N/A

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** N/A
**Retry Needed:** no
**Auditor Comment:** 精神科は専門性高いが需要もある。

---

## UNSUPPORTED PREFECTURES (茨城/栃木/群馬)

---

### Case W2-021
- **Prefecture:** 茨城県
- **Region Block:** 関東（非対応）
- **Case Type:** standard
- **User Profile:** 30歳、つくば市在住、急性期希望
- **Entry Route:** LINE友だち追加
- **Difficulty:** Medium

**Scenario:** 茨城県の看護師がBot利用。「その他の地域」を選択するしかない。

**Conversation Flow:**
1. [Bot] Welcome → 「求人を見る」
2. [User] タップ
3. [Bot] il_area → 「東京都/神奈川県/千葉県/埼玉県/その他の地域」
4. [User] 「その他の地域」タップ (il_pref=other)
5. [Bot] il_subarea → 「その他の地域ですね！📊 候補: X件 どんな職場が気になりますか？」→ 施設タイプ直表示
6. [User] 「急性期病院」→ 「こだわりなし」→ 「夜勤ありOK」→ 「すぐにでも転職したい」
7. [Bot] matching_preview → 横浜/川崎/23区/多摩/さいたま/千葉の結果が表示される

**System Behavior Evaluation:**
- il_pref=other → PREF_AREA_MAP['other'] = 'undecided' → area='undecided_il'
- AREA_ZONE_MAP['q3_undecided_il'] = ["横浜", "川崎", "23区", "多摩", "さいたま", "千葉"]
- countCandidatesD1: areaKey='undecided' → フィルタなし → 全24,488件表示
- しかしマッチング結果は関東4県の施設のみ。茨城の施設は0件
- ユーザーは茨城の求人を期待しているが、東京/神奈川/千葉/埼玉の結果しか出ない

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes（ただし茨城の施設ではない）
- Reached Next Action: yes
- Region Bias Signs: yes（茨城の施設が0）
- National Expansion Risk: 非対応県ユーザーへの説明なし

**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** 「その他の地域」選択時に「現在、東京/神奈川/千葉/埼玉の求人のみご案内しています。お近くのエリアの求人をお見せしますか？」と明示する。茨城ユーザーに東京/千葉を提案するのは合理的だが、説明なしは不信感。
**Retry Needed:** yes
**Auditor Comment:** つくば→千葉/埼玉は通勤可能だが、ユーザーは「茨城で探している」つもり。期待と結果の不一致が深刻。

---

### Case W2-022
- **Prefecture:** 茨城県
- **Region Block:** 関東（非対応）
- **Case Type:** adversarial
- **User Profile:** 35歳、水戸市在住、「茨城で探してるんですけど」とフリーテキスト
- **Entry Route:** LINE友だち追加
- **Difficulty:** Hard

**Scenario:** il_area表示時に「茨城で探してるんですけど」とテキスト入力。

**Conversation Flow:**
1. [Bot] il_area → 5択QR
2. [User] 「茨城で探してるんですけど」（フリーテキスト）
3. [Bot] unexpectedTextCount++ → 同じ5択再表示
4. [User] 「茨城ないんですか？」（フリーテキスト）
5. [Bot] unexpectedTextCount++ → 同じ5択再表示（説明なし）
6. [User] 離脱

**System Behavior Evaluation:**
- il_area phaseでフリーテキスト → return null → Quick Reply再表示
- 「茨城」というテキストへの対応なし
- ユーザーは2回聞いても答えをもらえず離脱
- TEXT_TO_POSTBACKにも茨城のマッピングなし

**Results:**
- Drop-off risk: yes（高確率で離脱）
- Reached Job Proposal: no
- Reached Next Action: no
- Region Bias Signs: yes
- National Expansion Risk: 非対応県の明示的な案内欠如

**Failure Category:** GEO_LOCK + INPUT_LOCK
**Severity:** Critical
**Fix Proposal:** (1) フリーテキストで県名を検知し、非対応県の場合「申し訳ございません、現在茨城県の求人は準備中です。近隣の千葉/埼玉の求人をご案内できますが、いかがですか？」と応答。(2) 「その他の地域」ボタン自体の説明テキスト改善。
**Retry Needed:** yes
**Auditor Comment:** 非対応エリアのユーザーがフリーテキストで地名を入力する場面は頻出。放置は致命的。

---

### Case W2-023
- **Prefecture:** 茨城県
- **Region Block:** 関東（非対応）
- **Case Type:** boundary
- **User Profile:** 28歳、守谷市在住（つくばエクスプレス沿線、東京通勤圏）
- **Entry Route:** LINE友だち追加
- **Difficulty:** Medium

**Scenario:** 守谷市から秋葉原まで約35分。東京で働けるので「東京都」を選択する合理的ケース。

**Conversation Flow:**
1. [User] 「東京都」タップ → 「23区」→ クリニック → 「いい求人があれば」
2. [Bot] matching_preview → 東京23区のクリニック表示
3. [User] 満足 → 「この施設について聞く」

**System Behavior Evaluation:**
- 茨城県民だが東京で就業希望 → 問題なく動作
- 通勤時間の概念がBotにはないため、守谷→秋葉原35分を知らない
- 結果的に満足できるパス

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: no
- National Expansion Risk: N/A

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** 通勤時間ベースの検索機能は将来的に有用だが現時点では不要。
**Retry Needed:** no
**Auditor Comment:** 県境在住者が対応県を選ぶケースは正常に動作する。問題は「茨城」にこだわるユーザー。

---

### Case W2-024
- **Prefecture:** 茨城県
- **Region Block:** 関東（非対応）
- **Case Type:** adversarial
- **User Profile:** 50歳、日立市在住、地元志向
- **Entry Route:** LINE友だち追加→即ブロック候補
- **Difficulty:** Hard

**Scenario:** 日立市は東京から遠く、通勤不可。「その他の地域」を選んでも関東4県の結果しか出ず、完全にミスマッチ。

**Conversation Flow:**
1. [User] 「その他の地域」タップ
2. [Bot] 候補数表示（全DB24,488件 → 期待を上げてしまう）
3. [User] 急性期病院 → 内科 → 日勤 → 「すぐにでも転職したい」
4. [Bot] matching_preview → 横浜/千葉/東京の施設ばかり
5. [User] 「日立の病院ないの？」（フリーテキスト）
6. [Bot] unexpectedTextCount++ → Quick Reply再表示
7. [User] LINEブロック

**System Behavior Evaluation:**
- undecided → 全DB検索 → 24,488件表示 → 「こんなにあるのか」と期待
- しかし茨城の施設は0件 → 落差が大きい
- 候補数の「24,488件」はミスリーディング

**Results:**
- Drop-off risk: yes（ブロック確実）
- Reached Job Proposal: yes（ただし無関係の施設）
- Reached Next Action: no
- Region Bias Signs: yes
- National Expansion Risk: 期待値操作の問題

**Failure Category:** GEO_LOCK + UX_DROP
**Severity:** Critical
**Fix Proposal:** (1) 「その他の地域」選択時の候補数表示を「関東4県の求人からご案内します」に変更。(2) 対応エリア外の旨を事前に伝える。(3) 将来的なDB拡大計画の告知。
**Retry Needed:** yes
**Auditor Comment:** 期待値のミスマッチが最も深刻なケース。24,488件と表示して自県0件は信頼崩壊。

---

### Case W2-025
- **Prefecture:** 茨城県
- **Region Block:** 関東（非対応）
- **Case Type:** boundary
- **User Profile:** 32歳、取手市在住（千葉県柏市の隣）
- **Entry Route:** LINE友だち追加
- **Difficulty:** Medium

**Scenario:** 取手市は千葉県柏市の隣。「千葉県」を選べば実用的な結果が得られる。

**Conversation Flow:**
1. [User] 「千葉県」タップ → 急性期病院 → 循環器 → 夜勤あり → 「すぐにでも転職したい」
2. [Bot] matching_preview → 柏/松戸/我孫子等の結果 → 通勤圏内

**System Behavior Evaluation:**
- 取手→柏は電車10分。千葉県選択は合理的
- chiba_allに柏市/松戸市含む → 通勤圏内の結果表示
- ユーザーが自発的に隣県を選べるケース

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: no
- National Expansion Risk: N/A

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** N/A
**Retry Needed:** no
**Auditor Comment:** 県境ユーザーが賢く隣県を選ぶパス。Botの誘導がなくてもワークする。

---

### Case W2-026
- **Prefecture:** 栃木県
- **Region Block:** 関東（非対応）
- **Case Type:** standard
- **User Profile:** 29歳、宇都宮市在住、回復期希望
- **Entry Route:** LINE友だち追加
- **Difficulty:** Medium

**Scenario:** 栃木県宇都宮の看護師。「その他の地域」を選択。

**Conversation Flow:**
1. [Bot] il_area → 5択
2. [User] （栃木県がないのでためらう → 3秒考える）
3. [User] 「その他の地域」タップ
4. [Bot] 候補数表示 + 施設タイプ選択
5. [User] 回復期病院 → リハビリ → 夜勤あり → 「いい求人があれば」
6. [Bot] matching_preview → 東京/神奈川/千葉/埼玉の結果

**System Behavior Evaluation:**
- 宇都宮→東京は新幹線で50分だが日常通勤には遠い
- 「その他の地域」→ undecided → 全DB結果
- 栃木の施設は表示されない
- W2-021と同様のGEO_LOCK問題

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes（ただし栃木の施設ではない）
- Reached Next Action: yes
- Region Bias Signs: yes
- National Expansion Risk: 北関東3県の完全非対応

**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** W2-021と同じ。「その他の地域」選択時に対応エリアの限定を明示。
**Retry Needed:** yes
**Auditor Comment:** 宇都宮から東京通勤は現実的でないユーザーにとって完全な空振り。

---

### Case W2-027
- **Prefecture:** 栃木県
- **Region Block:** 関東（非対応）
- **Case Type:** adversarial
- **User Profile:** 45歳、那須塩原市在住、訪問看護希望
- **Entry Route:** LINE友だち追加
- **Difficulty:** Hard

**Scenario:** 那須塩原は東京から200km以上。「その他の地域」を選んでも関東4県は全て通勤不可能。

**Conversation Flow:**
1. [User] 「その他の地域」→ 訪問看護 → パート → 「まずは情報収集」
2. [Bot] matching_preview → 東京/神奈川の訪問看護ST表示
3. [User] 全て通勤不可 → 「直接相談する」タップ
4. [Bot] handoff → Slack転送
5. [Human agent] 「申し訳ございません、現在栃木県の求人は...」

**System Behavior Evaluation:**
- 最終的にhandoff → 人間対応 → 正直に非対応を伝えるしかない
- Bot段階で非対応を伝えないため、ユーザーの時間を浪費
- handoff後の対応品質は人間エージェント次第

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes（無関係）
- Reached Next Action: yes（handoff）
- Region Bias Signs: yes
- National Expansion Risk: 遠方ユーザーのhandoff負荷

**Failure Category:** GEO_LOCK + HUMAN_HANDOFF_FAIL
**Severity:** Critical
**Fix Proposal:** 「その他の地域」選択後に「現在、東京・神奈川・千葉・埼玉エリアの求人をご案内しています。通勤可能な場合はお進みください。それ以外の地域の方は直接ご相談ください」と分岐を設ける。
**Retry Needed:** yes
**Auditor Comment:** 那須塩原→東京通勤は物理的に不可能。Botが時間を浪費させている。

---

### Case W2-028
- **Prefecture:** 栃木県
- **Region Block:** 関東（非対応）
- **Case Type:** boundary
- **User Profile:** 26歳、小山市在住（埼玉県との県境）
- **Entry Route:** LINE友だち追加
- **Difficulty:** Medium

**Scenario:** 小山市はJR宇都宮線で大宮まで40分。埼玉県を選ぶのが合理的。

**Conversation Flow:**
1. [User] 「埼玉県」タップ → 急性期 → こだわりなし → 夜勤あり → 「すぐにでも転職したい」
2. [Bot] matching_preview → さいたま/川口/春日部等の結果

**System Behavior Evaluation:**
- 小山→大宮は通勤圏。埼玉県選択は合理的
- saitama_allで大宮/春日部エリアの施設が表示される
- 県境ユーザーの自主的な隣県選択パス

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: no
- National Expansion Risk: N/A

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** N/A
**Retry Needed:** no
**Auditor Comment:** 小山→埼玉は現実的な通勤パス。

---

### Case W2-029
- **Prefecture:** 栃木県
- **Region Block:** 関東（非対応）
- **Case Type:** adversarial
- **User Profile:** 38歳、足利市在住、「群馬と栃木の境目」
- **Entry Route:** LINE友だち追加
- **Difficulty:** Hard

**Scenario:** 足利市は群馬県太田市の隣。どちらも非対応県。「その他の地域」しか選べない。

**Conversation Flow:**
1. [User] 「その他の地域」→ クリニック → 「いい求人があれば」
2. [Bot] matching_preview → 関東4県のクリニック
3. [User] 「足利か太田のクリニックないですか？」（フリーテキスト）
4. [Bot] unexpectedTextCount++ → Quick Reply再表示
5. [User] 離脱

**System Behavior Evaluation:**
- 足利/太田は東京から80km以上 → 通勤不可
- 非対応県×非対応県の境目 → Bot提案は全て的外れ
- フリーテキストへの対応なし

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes（無関係）
- Reached Next Action: no
- Region Bias Signs: yes
- National Expansion Risk: 北関東全体が空白地帯

**Failure Category:** GEO_LOCK + INPUT_LOCK
**Severity:** Critical
**Fix Proposal:** 非対応エリアユーザーのearly exit導線。「現在ご案内できるエリア外ですが、お近くで求人情報が出たらお知らせすることも可能です」→ 将来の拡大用リスト登録。
**Retry Needed:** yes
**Auditor Comment:** 最も不幸なユーザーパス。2県とも非対応で逃げ場なし。

---

### Case W2-030
- **Prefecture:** 栃木県
- **Region Block:** 関東（非対応）
- **Case Type:** standard
- **User Profile:** 33歳、栃木市在住、介護施設希望
- **Entry Route:** SNS（TikTok）経由
- **Difficulty:** Medium

**Scenario:** TikTokの動画を見てLINE登録。「神奈川ナース転職」のブランド名から地域限定だと理解せず。

**Conversation Flow:**
1. [Bot] Welcome → 「求人を見る」
2. [User] タップ
3. [Bot] il_area → 5択（東京/神奈川/千葉/埼玉/その他の地域）
4. [User] （「栃木がない...」と気づく。SNSでは全国対応の印象だった）
5. [User] 「その他の地域」→ 介護施設 → 日勤 → 情報収集
6. [Bot] matching_preview → 関東4県の結果
7. [User] がっかり → LINEブロック

**System Behavior Evaluation:**
- SNS流入ユーザーはブランド名「神奈川ナース転職」から地域限定を推測しにくい
  （TikTokでは @nurse_robby / Instagram @robby.for.nurse で「神奈川」不明瞭）
- il_area表示時点で「あ、関東限定か」と気づくが、選択肢に自県がない失望感
- 「その他の地域」は期待を持たせるが結果は関東4県のみ

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes（無関係）
- Reached Next Action: no（ブロック）
- Region Bias Signs: yes
- National Expansion Risk: SNS→LINE流入の期待値ミスマッチ

**Failure Category:** REGION_EXPANSION_FAIL
**Severity:** High
**Fix Proposal:** (1) SNSプロフィールに「関東エリア対応」を明記。(2) LINE登録直後のWelcomeメッセージに「現在、東京/神奈川/千葉/埼玉の求人をご案内中」と記載。(3) 「その他の地域」選択時に対応エリア外である旨を事前告知。
**Retry Needed:** yes
**Auditor Comment:** SNS経由の非対応県ユーザーは最も期待値が高い→落差が大きい→LINEブロック率直結。

---

### Case W2-031
- **Prefecture:** 群馬県
- **Region Block:** 関東（非対応）
- **Case Type:** standard
- **User Profile:** 31歳、前橋市在住、急性期希望
- **Entry Route:** LINE友だち追加
- **Difficulty:** Medium

**Scenario:** 群馬県前橋の看護師。「その他の地域」を選択。

**Conversation Flow:**
1. [User] 「その他の地域」→ 急性期 → 外科系 → 夜勤あり → 「すぐにでも転職したい」
2. [Bot] matching_preview → 関東4県の結果

**System Behavior Evaluation:**
- 前橋→東京は新幹線で1時間。通勤は厳しい
- undecided → 全DB検索 → 関東4県の施設表示
- W2-021/W2-026と同パターン

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes（無関係）
- Reached Next Action: yes
- Region Bias Signs: yes
- National Expansion Risk: 北関東の空白

**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** W2-021と同じ。
**Retry Needed:** yes
**Auditor Comment:** 群馬も茨城・栃木と同じ構造的問題。

---

### Case W2-032
- **Prefecture:** 群馬県
- **Region Block:** 関東（非対応）
- **Case Type:** boundary
- **User Profile:** 27歳、高崎市在住（東京通勤ギリギリ）
- **Entry Route:** LINE友だち追加
- **Difficulty:** Medium

**Scenario:** 高崎は新幹線で東京50分。「東京都」を選択して通勤可能な求人を探す。

**Conversation Flow:**
1. [User] 「東京都」→ 「23区」→ クリニック → 「いい求人があれば」
2. [Bot] matching_preview → 23区のクリニック表示

**System Behavior Evaluation:**
- 高崎→東京は新幹線通勤者あり（定期代が高額）
- 23区のクリニック結果は正しく表示される
- ただしBot側に通勤手段/時間の概念なし → 新幹線通勤の現実性を判断できない

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: no
- National Expansion Risk: N/A

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** N/A
**Retry Needed:** no
**Auditor Comment:** 新幹線通勤を前提にすれば動作する。通勤手段はユーザー判断。

---

### Case W2-033
- **Prefecture:** 群馬県
- **Region Block:** 関東（非対応）
- **Case Type:** adversarial
- **User Profile:** 55歳、沼田市在住、地元のみ希望
- **Entry Route:** 検索エンジン経由
- **Difficulty:** Hard

**Scenario:** 沼田市は東京から150km。「その他の地域」選択後、結果が全て遠方で即ブロック。

**Conversation Flow:**
1. [User] 「その他の地域」→ 慢性期 → 内科 → 日勤 → 「すぐにでも」
2. [Bot] matching_preview → 東京/神奈川の慢性期病院
3. [User] 「沼田の病院を紹介してほしい」（フリーテキスト）
4. [Bot] Quick Reply再表示
5. [User] LINEブロック

**System Behavior Evaluation:**
- 沼田→東京は物理的に通勤不可
- W2-024/W2-027と同パターン
- 地元のみ希望のユーザーには完全に無力

**Results:**
- Drop-off risk: yes（ブロック確実）
- Reached Job Proposal: yes（無関係）
- Reached Next Action: no
- Region Bias Signs: yes
- National Expansion Risk: 地方ユーザーの完全排除

**Failure Category:** GEO_LOCK + INPUT_LOCK
**Severity:** Critical
**Fix Proposal:** 非対応エリアの早期通知 + 将来拡大時の通知登録機能。
**Retry Needed:** yes
**Auditor Comment:** W2-024と同構造。地方ほど深刻。

---

### Case W2-034
- **Prefecture:** 群馬県
- **Region Block:** 関東（非対応）
- **Case Type:** boundary
- **User Profile:** 24歳、太田市在住（埼玉県熊谷市の近く）
- **Entry Route:** LINE友だち追加
- **Difficulty:** Medium

**Scenario:** 太田市は熊谷まで30分程度。「埼玉県」を選択するが、熊谷市はsaitama_allに含まれていない（W2-019の問題）。

**Conversation Flow:**
1. [User] 「埼玉県」→ 急性期 → こだわりなし → 夜勤あり → 「すぐにでも」
2. [Bot] matching_preview → さいたま/川口/所沢等の結果（熊谷周辺なし）
3. [User] 通勤可能な結果が少ない → 不満

**System Behavior Evaluation:**
- saitama_allのAREA_CITY_MAPに熊谷市なし → 熊谷の施設は検索されない
- W2-019と同じ問題: saitama_allが県全体をカバーしていない
- 群馬南部→埼玉北部の通勤圏がDBの穴

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes（遠方の施設のみ）
- Reached Next Action: yes
- Region Bias Signs: yes
- National Expansion Risk: 埼玉北部の空白

**Failure Category:** GEO_LOCK + JOB_MATCH_FAIL
**Severity:** High
**Fix Proposal:** W2-019の修正（saitama_allをprefecture='埼玉県'に変更）で解決。熊谷/深谷/本庄等の北部もカバーされる。
**Retry Needed:** yes
**Auditor Comment:** W2-019の問題が群馬ユーザーにも波及。AREA_PREF_MAPの修正は必須。

---

### Case W2-035
- **Prefecture:** 群馬県
- **Region Block:** 関東（非対応）
- **Case Type:** adversarial
- **User Profile:** 40歳、伊勢崎市在住、「ナースロビーって全国対応じゃないの？」
- **Entry Route:** Instagram経由
- **Difficulty:** Hard

**Scenario:** Instagramの投稿を見てLINE登録。il_area表示を見て「全国対応じゃないのか」と失望し、テキストで問い合わせ。

**Conversation Flow:**
1. [Bot] il_area → 5択
2. [User] 「群馬は対応していますか？」（フリーテキスト）
3. [Bot] unexpectedTextCount++ → Quick Reply再表示
4. [User] 「全国対応ですか？」（フリーテキスト）
5. [Bot] unexpectedTextCount++ → Quick Reply再表示
6. [User] 離脱

**System Behavior Evaluation:**
- 質問型のフリーテキストに一切応答できない
- 「対応していますか」「全国ですか」等の質問は想定されるが処理なし
- il_area中はAI応答もなし（ai_consultation phaseではない）

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: no
- Reached Next Action: no
- Region Bias Signs: yes
- National Expansion Risk: 対応エリア問い合わせへの無応答

**Failure Category:** INPUT_LOCK + GEO_LOCK
**Severity:** Critical
**Fix Proposal:** intake phase中のフリーテキストに対し、(1) エリア関連キーワード検出 → 対応エリア案内、(2) 質問検出 → 簡易FAQ応答、(3) それ以外 → 「下のボタンからお選びください」のガイダンス。
**Retry Needed:** yes
**Auditor Comment:** intake中のフリーテキスト完全無視は全ケースで問題だが、非対応エリアのユーザーが質問する場面で最も致命的。

---

## SPARE CASES (関東追加)

---

### Case W2-036
- **Prefecture:** 神奈川県
- **Region Block:** 関東
- **Case Type:** standard
- **User Profile:** 34歳、相模原市在住、こだわりなし全部
- **Entry Route:** LINE友だち追加
- **Difficulty:** Easy

**Scenario:** 全ての選択肢で「こだわりなし」「どこでもOK」を選ぶ。最大候補数を維持したまま結果表示。

**Conversation Flow:**
1. [User] 「神奈川県」→「どこでもOK」(kanagawa_all) → 「こだわりなし」(il_ft=any) → 「日勤のみ」→ 「まずは情報収集」
2. [Bot] matching_preview → 神奈川全域の幅広い結果

**System Behavior Evaluation:**
- kanagawa_all → AREA_CITY_MAP: 13市 → 広範囲
- facilityType=any → カテゴリフィルタなし
- 候補が多すぎて優先順位付けが曖昧になる可能性

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: no
- National Expansion Risk: N/A

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** 「こだわりなし」が多い場合、上位5件の選定基準（距離? 人気? ランダム?）を明示すると信頼感向上。
**Retry Needed:** no
**Auditor Comment:** 条件を絞らないユーザーへの結果品質はD1のランキングロジック次第。

---

### Case W2-037
- **Prefecture:** 東京都
- **Region Block:** 関東
- **Case Type:** adversarial
- **User Profile:** 22歳、看護学生（まだ免許なし）
- **Entry Route:** TikTok経由
- **Difficulty:** Hard

**Scenario:** 看護学生がTikTok経由で興味本位でLINE登録。intakeフロー途中で「まだ学生なんですけど」とテキスト入力。

**Conversation Flow:**
1. [User] 「東京都」→ 「23区」→ 急性期病院 → 小児科
2. [Bot] il_workstyle → 4択
3. [User] 「まだ学生なんですけど登録できますか？」（フリーテキスト）
4. [Bot] unexpectedTextCount++ → Quick Reply再表示
5. [User] 「日勤のみ」タップ → 「まずは情報収集」
6. [Bot] matching_preview → 結果表示

**System Behavior Evaluation:**
- 看護学生は紹介対象外（免許なし）
- しかしBotには学生判別機能なし → 通常フローで進行
- handoffまで行った場合、人間エージェントが対応

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: no
- National Expansion Risk: N/A

**Failure Category:** OTHER
**Severity:** Low
**Fix Proposal:** 「学生」「国試」「実習」等のキーワード検出で「卒業見込みの方は、国試合格後にぜひご相談ください」と案内。将来のリード育成にも有用。
**Retry Needed:** no
**Auditor Comment:** 学生ユーザーはTikTok経由で一定数見込まれる。拒否ではなく将来顧客として育成する導線が理想。

---

### Case W2-038
- **Prefecture:** 神奈川県
- **Region Block:** 関東
- **Case Type:** boundary
- **User Profile:** 36歳、川崎市在住、産婦人科希望
- **Entry Route:** LINE友だち追加
- **Difficulty:** Medium

**Scenario:** 産婦人科は急性期・クリニック両方にある。急性期を選んで産婦人科を指定するケースと、クリニックを選ぶケースで結果が変わる。

**Conversation Flow (パターンA):**
1. [User] 「神奈川県」→「横浜・川崎」→「急性期病院」→「産婦人科」→「日勤のみ」→「いい求人があれば」
2. [Bot] matching_preview → 急性期の産婦人科病棟

**Conversation Flow (パターンB):**
1. [User] 「神奈川県」→「横浜・川崎」→「クリニック」→ il_urgency直行（workStyle=day自動）
2. [Bot] matching_preview → 全クリニック（産婦人科に絞れない）

**System Behavior Evaluation:**
- パターンA: hospital + 産婦人科 → 正確な結果
- パターンB: clinic → department選択なし → 産婦人科クリニックに絞れない
- クリニック選択時にdepartmentを聞かない設計 → 産婦人科/皮膚科/眼科等の専門クリニックユーザーにはミスマッチ

**Results:**
- Drop-off risk: no（パターンA）/ yes（パターンB、ミスマッチ）
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: no
- National Expansion Risk: N/A

**Failure Category:** JOB_MATCH_FAIL（パターンBのみ）
**Severity:** Medium
**Fix Proposal:** クリニック選択時にも「何科のクリニックですか？」の追加質問があると精度向上。特に産婦人科/小児科/精神科クリニックは専門性が高い。
**Retry Needed:** no
**Auditor Comment:** クリニックの診療科スキップは簡便だが、専門クリニック希望者には不十分。

---

### Case W2-039
- **Prefecture:** 埼玉県
- **Region Block:** 関東
- **Case Type:** adversarial
- **User Profile:** 28歳、さいたま市在住、LINEで長文を送るタイプ
- **Entry Route:** LINE友だち追加
- **Difficulty:** Hard

**Scenario:** il_area表示中に「さいたま市大宮区で、できれば駅から徒歩10分以内の、残業が少ない回復期の病院を探しています。夜勤は月4回まで希望で、年収450万以上だと嬉しいです。」と長文送信。

**Conversation Flow:**
1. [Bot] il_area → 5択
2. [User] 上記長文（フリーテキスト）
3. [Bot] unexpectedTextCount++ → Quick Reply再表示
4. [User] （詳細を伝えたのに無視された感覚 → 不信）
5. [User] しぶしぶ「埼玉県」タップ
6. [Bot] 通常フロー続行

**System Behavior Evaluation:**
- 長文に含まれる有用情報: 大宮区/回復期/駅近/残業少/夜勤月4回/年収450万
- これらは全てintakeで聞く（または聞けない）項目
- Botは全て無視してQuick Reply再送 → ユーザーの詳細情報が無駄に

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: no
- National Expansion Risk: N/A

**Failure Category:** INPUT_LOCK
**Severity:** High
**Fix Proposal:** intake phase中の長文テキストをパースし、(1) 都道府県/エリア検出 → 自動設定、(2) 施設タイプ/診療科検出 → 自動設定、(3) 残りの条件はメモとして保存 → handoff時にエージェントに引き渡し。
**Retry Needed:** no
**Auditor Comment:** 長文で条件を伝えるユーザーは本気度が高い。無視は最悪のUX。NLP解析でentry自動設定が理想。

---

### Case W2-040
- **Prefecture:** 東京都
- **Region Block:** 関東
- **Case Type:** boundary
- **User Profile:** 29歳、セッション中断後の再開
- **Entry Route:** LINE友だち追加（前日）
- **Difficulty:** Medium

**Scenario:** 前日にil_facility_typeまで進めて中断。翌日LINEを開いて再開しようとする。

**Conversation Flow:**
1. [前日] 「東京都」→「23区」→ il_facility_type表示 → LINEアプリ閉じる
2. [翌日] LINEを開く → 前日のQuick Reply表示が残っている
3. [User] 「急性期病院」タップ（前日のQuick Reply）
4. [Bot] postback処理 → entry.phase=il_facility_type → il_ft=hospital_acute処理
5. [Bot] il_department → 正常続行

**System Behavior Evaluation:**
- LINE Quick Replyのpostbackは期限なし → 翌日でも有効
- entry KVのTTL次第。LINE_SESSIONSのKVは期限設定がある
- KV TTLが24時間以上なら正常動作。24時間未満だとentry消失 → 新規フロー

**Results:**
- Drop-off risk: no（KV残存時）/ yes（KV消失時）
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: no
- National Expansion Risk: N/A

**Failure Category:** REENTRY_FAIL（KV消失の場合）
**Severity:** Medium
**Fix Proposal:** セッションTTLを72時間以上に設定。中断再開時に「前回の続きから始めますか？」の確認メッセージ。
**Retry Needed:** yes（KV TTL確認が必要）
**Auditor Comment:** セッション中断→再開は頻出パターン。看護師は忙しい→翌日再開は普通。

---

## CROSS-REGION CASES (北海道/大阪/福岡/静岡/広島)

---

### Case W2-041
- **Prefecture:** 北海道
- **Region Block:** 北海道（非対応）
- **Case Type:** standard
- **User Profile:** 30歳、札幌市在住、急性期希望
- **Entry Route:** Google検索「看護師 転職 LINE」→ LP経由
- **Difficulty:** Medium

**Scenario:** 北海道の看護師がGoogle検索でLINE登録。「その他の地域」しか選べない。

**Conversation Flow:**
1. [Bot] il_area → 5択
2. [User] 「その他の地域」タップ
3. [Bot] 候補数表示 + 施設タイプ
4. [User] 急性期 → 内科 → 夜勤あり → 「すぐにでも」
5. [Bot] matching_preview → 関東4県の結果
6. [User] 「札幌の病院はないんですか？」→ Quick Reply再表示 → 離脱

**System Behavior Evaluation:**
- 北海道→関東は引っ越し前提でない限り完全にミスマッチ
- LP経由の場合、LP上に「関東エリア」の記載があるかが問題
- Welcomeメッセージに対応エリア未記載

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes（無関係）
- Reached Next Action: no
- Region Bias Signs: yes
- National Expansion Risk: 全国からの流入に未対応

**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** (1) LP/SNSに「関東エリア限定」を明記。(2) Welcomeメッセージに対応エリア記載。(3) 「その他の地域」で非関東を検出した場合のearly exit。
**Retry Needed:** yes
**Auditor Comment:** Google検索は全国から来る。LP段階でフィルタリングすべき。

---

### Case W2-042
- **Prefecture:** 北海道
- **Region Block:** 北海道（非対応）
- **Case Type:** adversarial
- **User Profile:** 35歳、旭川市在住、「関東に引っ越し予定」
- **Entry Route:** LINE友だち追加
- **Difficulty:** Medium

**Scenario:** 関東への引っ越し予定がある北海道ユーザー。「東京都」を選んで情報収集。

**Conversation Flow:**
1. [User] 「東京都」→「23区」→ 急性期 → こだわりなし → 夜勤あり → 「いい求人があれば」
2. [Bot] matching_preview → 23区の結果表示
3. [User] 「もっと求人を見る」→ matching_browse → 追加3件
4. [User] 「直接相談する」→ handoff

**System Behavior Evaluation:**
- 引っ越し前提ユーザーは対応エリア選択で正常動作
- handoff後に「いつ頃引っ越し予定ですか？」等の人間対応
- Botレベルでは問題なし

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Next Action: yes（handoff）
- Region Bias Signs: no
- National Expansion Risk: N/A

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** N/A
**Retry Needed:** no
**Auditor Comment:** 引っ越し予定ユーザーは正常パス。稀だが存在する。

---

### Case W2-043
- **Prefecture:** 大阪府
- **Region Block:** 近畿（非対応）
- **Case Type:** standard
- **User Profile:** 28歳、大阪市在住、クリニック希望
- **Entry Route:** Instagram経由
- **Difficulty:** Medium

**Scenario:** 大阪の看護師がInstagram経由でLINE登録。

**Conversation Flow:**
1. [Bot] il_area → 5択
2. [User] 「その他の地域」タップ
3. [Bot] 候補数24,488件表示 + 施設タイプ
4. [User] クリニック → 「まずは情報収集」
5. [Bot] matching_preview → 関東4県のクリニック
6. [User] 全て大阪から遠い → 離脱

**System Behavior Evaluation:**
- 大阪→関東は完全にミスマッチ
- 候補数24,488件の表示がミスリーディング
- W2-021系列と同じGEO_LOCK

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes（無関係）
- Reached Next Action: no
- Region Bias Signs: yes
- National Expansion Risk: 大阪は看護師需要トップクラスの市場

**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** 同上。加えて大阪は将来の拡大候補として優先度高い。非対応エリア登録者リストを蓄積し、拡大時の初期ユーザーにする。
**Retry Needed:** yes
**Auditor Comment:** 大阪ユーザーの蓄積は事業拡大の布石になる。切り捨てではなくウェイトリスト化。

---

### Case W2-044
- **Prefecture:** 大阪府
- **Region Block:** 近畿（非対応）
- **Case Type:** adversarial
- **User Profile:** 32歳、堺市在住、「大阪で探してるんですけど」
- **Entry Route:** LINE友だち追加
- **Difficulty:** Hard

**Scenario:** フリーテキストで「大阪」と入力し続けるユーザー。

**Conversation Flow:**
1. [Bot] il_area → 5択
2. [User] 「大阪で探したい」（フリーテキスト）
3. [Bot] Quick Reply再表示
4. [User] 「大阪府」（フリーテキスト）
5. [Bot] Quick Reply再表示
6. [User] 「大阪」（フリーテキスト）
7. [Bot] Quick Reply再表示
8. [User] 離脱（3回無視された）

**System Behavior Evaluation:**
- 3回連続でフリーテキスト無視
- unexpectedTextCountは増加するが、閾値超過時の特別処理なし
- 3回目で「ボタンからお選びください」等のガイダンスもなし

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: no
- Reached Next Action: no
- Region Bias Signs: yes
- National Expansion Risk: フリーテキスト無視の構造問題

**Failure Category:** INPUT_LOCK + GEO_LOCK
**Severity:** Critical
**Fix Proposal:** unexpectedTextCount >= 2 の場合、「ボタンが表示されない場合は、LINEアプリを最新版にアップデートしてみてください。現在は東京/神奈川/千葉/埼玉エリアの求人をご案内しています」等のテキスト応答。
**Retry Needed:** yes
**Auditor Comment:** 3回無視は確実に離脱。unexpectedTextCountの閾値処理を追加すべき。

---

### Case W2-045
- **Prefecture:** 福岡県
- **Region Block:** 九州（非対応）
- **Case Type:** standard
- **User Profile:** 26歳、福岡市在住、訪問看護希望
- **Entry Route:** TikTok経由
- **Difficulty:** Medium

**Scenario:** 福岡の看護師がTikTok動画に興味を持ちLINE登録。

**Conversation Flow:**
1. [Bot] il_area → 5択
2. [User] 「その他の地域」→ 訪問看護 → パート → 「まずは情報収集」
3. [Bot] matching_preview → 関東の訪問看護ST
4. [User] 福岡の施設なし → 離脱

**System Behavior Evaluation:**
- 福岡→関東は完全ミスマッチ
- TikTok経由ユーザーは地域制限を意識していない

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes（無関係）
- Reached Next Action: no
- Region Bias Signs: yes
- National Expansion Risk: 九州市場の未開拓

**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** SNSの投稿/プロフィールに「関東エリア」を追記。TikTokビオに「東京/神奈川/千葉/埼玉の看護師さん向け」と明記。
**Retry Needed:** yes
**Auditor Comment:** TikTokは全国に拡散する。SNS側でのフィルタリングが最も効率的。

---

### Case W2-046
- **Prefecture:** 福岡県
- **Region Block:** 九州（非対応）
- **Case Type:** boundary
- **User Profile:** 29歳、北九州市在住、「東京で働いてみたい」
- **Entry Route:** LINE友だち追加
- **Difficulty:** Medium

**Scenario:** 東京への転職（引っ越し込み）を考えている福岡ユーザー。

**Conversation Flow:**
1. [User] 「東京都」→「どこでもOK」→ 急性期 → こだわりなし → 夜勤あり → 「いい求人があれば」
2. [Bot] matching_preview → 東京+αの結果
3. [User] 「直接相談する」→ handoff
4. [Human] 「東京への転職ですね。住居等もサポートできる施設をご案内しますね」

**System Behavior Evaluation:**
- 引っ越し前提の遠方ユーザー → 正常動作
- tokyo_included → AREA_PREF_MAP null → フィルタなし → 全DB検索
- handoff後の人間対応で引っ越しサポート

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Next Action: yes（handoff）
- Region Bias Signs: no
- National Expansion Risk: N/A

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** N/A
**Retry Needed:** no
**Auditor Comment:** 地方→東京の転職希望は一定数あり。Botは正常に動作する。

---

### Case W2-047
- **Prefecture:** 静岡県
- **Region Block:** 中部（非対応）
- **Case Type:** standard
- **User Profile:** 33歳、静岡市在住、回復期希望
- **Entry Route:** Google検索「看護師 転職 手数料 安い」→ LP経由
- **Difficulty:** Medium

**Scenario:** 手数料10%に魅力を感じてLINE登録した静岡ユーザー。

**Conversation Flow:**
1. [Bot] il_area → 5択
2. [User] 「その他の地域」→ 回復期 → リハビリ → 日勤 → 「いい求人があれば」
3. [Bot] matching_preview → 関東4県の結果
4. [User] 「静岡の病院はないですよね...」（フリーテキスト）
5. [Bot] Quick Reply再表示

**System Behavior Evaluation:**
- 静岡→関東は新幹線で1時間だが日常通勤は困難
- 手数料10%のUSPに惹かれたユーザーにとって「エリア外」は大きな失望
- 中部地方は将来の拡大候補

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes（無関係）
- Reached Next Action: no
- Region Bias Signs: yes
- National Expansion Risk: USPに惹かれた非対応エリアユーザーの取りこぼし

**Failure Category:** GEO_LOCK
**Severity:** High
**Fix Proposal:** 手数料10%で差別化しているなら、ウェイトリスト機能で「お住まいのエリアが対応エリアになったらお知らせします」が有効。USPに惹かれたユーザーは将来の強力なリードになる。
**Retry Needed:** yes
**Auditor Comment:** 静岡は神奈川の隣。エリア拡大の第一候補として蓄積すべき。

---

### Case W2-048
- **Prefecture:** 静岡県
- **Region Block:** 中部（非対応）
- **Case Type:** boundary
- **User Profile:** 27歳、熱海市在住（神奈川県との県境）
- **Entry Route:** LINE友だち追加
- **Difficulty:** Medium

**Scenario:** 熱海は小田原まで電車20分。神奈川県を選択すれば県西エリアの結果が得られる。

**Conversation Flow:**
1. [User] 「神奈川県」→「小田原・県西」→ クリニック → 「すぐにでも転職したい」
2. [Bot] matching_preview → 小田原/湯河原/真鶴等のクリニック

**System Behavior Evaluation:**
- 熱海→小田原/湯河原は日常通勤圏
- odawara_kensei のAREA_CITY_MAPに湯河原町含む
- 県境ユーザーの最適パス

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: no
- National Expansion Risk: N/A

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** N/A
**Retry Needed:** no
**Auditor Comment:** 熱海→神奈川県西は完全な通勤圏。Botが正常動作する好例。

---

### Case W2-049
- **Prefecture:** 広島県
- **Region Block:** 中国（非対応）
- **Case Type:** adversarial
- **User Profile:** 40歳、広島市在住、絵文字多用タイプ
- **Entry Route:** Instagram経由
- **Difficulty:** Hard

**Scenario:** 絵文字だけ送信「😊🏥💪」→ Botの反応確認。

**Conversation Flow:**
1. [Bot] il_area → 5択
2. [User] 「😊🏥💪」（絵文字のみ）
3. [Bot] unexpectedTextCount++ → Quick Reply再表示
4. [User] 「広島で看護師の仕事探してます😊」
5. [Bot] unexpectedTextCount++ → Quick Reply再表示
6. [User] 「その他の地域」タップ
7. [Bot] 通常フロー → 関東4県の結果
8. [User] 離脱

**System Behavior Evaluation:**
- 絵文字のみ入力 → フリーテキスト扱い → Quick Reply再表示
- 絵文字 + テキスト混在 → 同じくフリーテキスト扱い
- 広島ユーザーにとって関東の結果は完全にミスマッチ

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes（無関係）
- Reached Next Action: no
- Region Bias Signs: yes
- National Expansion Risk: 西日本全域が空白

**Failure Category:** GEO_LOCK + INPUT_LOCK
**Severity:** High
**Fix Proposal:** 絵文字のみ入力時は「メッセージありがとうございます。下のボタンからお選びください」と親切なガイダンス。テキスト内の県名検出で非対応エリア案内。
**Retry Needed:** yes
**Auditor Comment:** 絵文字文化のユーザーは一定数いる。完全無視は不親切。

---

### Case W2-050
- **Prefecture:** 広島県
- **Region Block:** 中国（非対応）
- **Case Type:** adversarial
- **User Profile:** 38歳、福山市在住、スタンプのみ送信
- **Entry Route:** LINE友だち追加
- **Difficulty:** Hard

**Scenario:** LINEスタンプを送信。Botの反応確認。

**Conversation Flow:**
1. [Bot] il_area → 5択
2. [User] LINEスタンプ送信
3. [Bot] スタンプはmessage typeが'sticker' → テキストではないためhandleLineTextに到達しない可能性
4. [User] 反応なし or エラー
5. [User] 「求人見たいです」（テキスト）
6. [Bot] unexpectedTextCount++ → Quick Reply再表示
7. [User] 「その他の地域」タップ → 以降通常フロー

**System Behavior Evaluation:**
- LINEスタンプのevent type = message, message type = sticker
- worker.jsがsticker typeをどう処理するか → おそらくtext以外は無視
- ユーザーに反応がないと「壊れてる？」と思う

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes（ステップ7以降）
- Reached Next Action: yes
- Region Bias Signs: yes（結局GEO_LOCK）
- National Expansion Risk: N/A

**Failure Category:** INPUT_LOCK
**Severity:** Medium
**Fix Proposal:** sticker/image/video等の非テキストメッセージに対し、「メッセージありがとうございます！下のボタンから選んでくださいね」と応答。完全無視は不信感につながる。
**Retry Needed:** no
**Auditor Comment:** LINEはスタンプ文化。スタンプ送信への無応答はLINE Botの基本的な問題。

---

## Summary Statistics

| Category | Count | Percentage |
|----------|-------|------------|
| Standard | 30 | 60% |
| Boundary | 12 | 24% |
| Adversarial | 8 | 16% |

| Failure Category | Count | Cases |
|-----------------|-------|-------|
| NONE | 16 | W2-001,002,006,009,011,012,015,016,017,020,023,025,028(partial),032,042,046,048 |
| GEO_LOCK | 17 | W2-019,021,022,024,026,027,029,030,031,033,034,035,041,043,044,045,047 |
| INPUT_LOCK | 8 | W2-004,022,029,035,039,044,049,050 |
| JOB_MATCH_FAIL | 6 | W2-003,005,007,008,014,038 |
| UX_DROP | 4 | W2-010,013,018,024 |
| REGION_EXPANSION_FAIL | 1 | W2-030 |
| REENTRY_FAIL | 1 | W2-040 |
| HUMAN_HANDOFF_FAIL | 1 | W2-027 |
| OTHER | 1 | W2-037 |

*Note: Some cases have multiple failure categories.*

| Severity | Count |
|----------|-------|
| Critical | 14 |
| High | 6 |
| Medium | 16 |
| Low | 14 |

## Top Findings

### 1. GEO_LOCK is the dominant failure (Critical)
- **17 of 50 cases** involve users from unsupported prefectures receiving no explanation
- The "その他の地域" option displays 24,488 candidates but delivers 0 local results
- No early exit or explanation for non-Kanto users

### 2. AREA_PREF_MAP bug for saitama_all and chiba_all (High)
- **Case W2-019/W2-034**: saitama_all and chiba_all are not in AREA_PREF_MAP
- Falls back to AREA_CITY_MAP which only covers 13 cities each
- Entire prefectures (秩父/熊谷/銚子/館山 etc.) are excluded from search results
- **Fix**: Add `saitama_all: '埼玉県'` and `chiba_all: '千葉県'` to AREA_PREF_MAP in countCandidatesD1

### 3. INPUT_LOCK during intake phases (High)
- **8 cases**: Free text during intake is completely ignored with no guidance
- unexpectedTextCount increments but triggers no helpful response at any threshold
- Users asking questions, naming prefectures, or sending long conditions get silent re-prompts

### 4. tokyo_included filter mismatch (Medium)
- **Case W2-003**: AREA_PREF_MAP[tokyo_included] = null means NO filter applied
- Entire 24,488 DB searched for "東京どこでもOK" users
- Results may include Kanagawa/Chiba/Saitama facilities under a "Tokyo" selection

### 5. Clinic department skip (Medium)
- **Case W2-038**: Clinic selection skips department → specialty clinic seekers get broad results
- Obstetrics/dermatology/psychiatry clinic users cannot filter
