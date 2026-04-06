# Worker 4: Tokai Region Test Cases (W4-001 ~ W4-050)

> **Scope:** 岐阜(8), 静岡(8), 愛知(10), 三重(8), spare(6) + Cross-region(10)
> **DB Reality:** D1 has 0 facilities in 岐阜/静岡/愛知/三重. "その他の地域" → `undecided` → Kanto facilities only.
> **Key Risk:** 愛知(名古屋) is Japan's 4th largest metro. Users will expect local results and will be confused/angry when shown Tokyo/Yokohama facilities.

---

## Aichi Prefecture (愛知) — 10 cases

### Case W4-001
- **Prefecture:** 愛知県 / **Region Block:** 東海 / **Case Type:** Standard / **User Profile:** 名古屋市内の急性期病院勤務、3年目看護師 / **Entry Route:** LINE友達追加(QR) / **Difficulty:** Medium

**Scenario:** 名古屋在住の看護師が地元で転職先を探す。最も一般的な東海ユーザーパターン。

**Conversation Flow:**
1. User follows LINE → Bot: Welcome + "○○件の医療機関の中から..."
2. Bot shows area selection: 東京都/神奈川県/千葉県/埼玉県/その他の地域
3. User taps "その他の地域"
4. Bot: "その他の地域ですね！ 候補: XX件" → skips subarea → il_facility_type
5. User taps "急性期病院"
6. Bot → il_department → User taps "内科系"
7. Bot → il_workstyle → User taps "二交代"
8. Bot → il_urgency → User taps "すぐ転職したい"
9. Bot → matching_preview: shows 5 facilities — ALL from Kanto (横浜/川崎/東京等)
10. User sees zero 名古屋/愛知 facilities → confusion/drop-off

**System Behavior Evaluation:**
- il_pref=other → entry.area = "undecided_il" → AREA_ZONE_MAP q3_undecided_il = ["横浜","川崎","23区","多摩","さいたま","千葉"]
- Matching results will be 100% Kanto. Zero explanation that 愛知 is not covered.
- Candidate count displayed ("候補: XX件") is misleading — implies 愛知 facilities exist.

**Results:** Drop-off: HIGH (90%+) / Job Proposal: Kanto-only (irrelevant) / Next Action: None / Region Bias: CRITICAL — 愛知 user shown only Kanto results / National Expansion Risk: HIGH — 愛知 is 4th largest prefecture, losing all users here
**Failure Category:** Regional Coverage Gap / **Severity:** P0-Critical / **Fix Proposal:** (1) Add 愛知 facilities to D1, (2) At minimum, display honest message "現在、愛知県の求人は準備中です" before showing Kanto alternatives / **Retry Needed:** Yes — after fix / **Auditor Comment:** The single most damaging gap in the entire bot. 名古屋 metro area has ~7.5M population. Every 愛知 user who taps "その他の地域" gets bait-and-switched.

---

### Case W4-002
- **Prefecture:** 愛知県 / **Region Block:** 東海 / **Case Type:** Adversarial / **User Profile:** 名古屋の大学病院勤務、10年目ベテラン / **Entry Route:** LINE友達追加 / **Difficulty:** Hard

**Scenario:** User types free text "名古屋の求人は？" at il_area phase instead of tapping Quick Reply.

**Conversation Flow:**
1. User follows LINE → Bot: Welcome
2. Bot shows il_area Quick Reply buttons
3. User ignores buttons, types "名古屋の求人は？"
4. Bot: unexpectedTextCount++ → re-displays Quick Reply (no text parsing for area names)
5. User types again "愛知県で探してます"
6. Bot: unexpectedTextCount++ → re-displays Quick Reply again
7. User frustrated, taps "その他の地域" reluctantly
8. Bot proceeds with undecided → Kanto matching
9. User sees Kanto results → immediate block
10. (No recovery path offered)

**System Behavior Evaluation:**
- Free text at il_area phase returns null → Quick Reply re-display. No NLP/keyword extraction.
- TEXT_TO_POSTBACK has no mapping for "名古屋" or "愛知" → always falls through.
- User's intent is crystal clear but bot cannot parse it.

**Results:** Drop-off: VERY HIGH / Job Proposal: None relevant / Next Action: None / Region Bias: CRITICAL / National Expansion Risk: HIGH
**Failure Category:** Free Text Handling + Regional Gap / **Severity:** P0-Critical / **Fix Proposal:** (1) Add keyword→postback mapping for major cities (名古屋→other, 大阪→other etc.), (2) When "other" selected, detect prefecture from free text and display honest coverage message / **Retry Needed:** Yes / **Auditor Comment:** "名古屋の求人は？" is the most natural possible query. Bot's inability to parse it AND lack of 愛知 coverage creates double frustration.

---

### Case W4-003
- **Prefecture:** 愛知県 / **Region Block:** 東海 / **Case Type:** Boundary / **User Profile:** 豊橋市勤務、静岡との県境通勤者 / **Entry Route:** LINE友達追加 / **Difficulty:** Medium

**Scenario:** 豊橋市（愛知東部）在住で、浜松市（静岡西部）も通勤圏内。どちらも DB に存在しない。

**Conversation Flow:**
1. User follows LINE → Welcome
2. Bot shows area selection
3. User taps "その他の地域"
4. Bot: "その他の地域ですね！ 候補: XX件" → il_facility_type
5. User taps "クリニック" → il_urgency (clinic skips workstyle)
6. User taps "良い求人があれば"
7. Bot → matching_preview: 5 Kanto facilities
8. User: "豊橋や浜松のクリニックはないですか？" (free text at matching_preview)
9. Bot: unexpectedTextCount++ → re-displays matching Quick Reply
10. User drops off

**System Behavior Evaluation:**
- Both 豊橋(愛知) and 浜松(静岡) have 0 facilities in DB.
- Cross-border commuting pattern completely unsupported.
- No mechanism to collect user's actual desired area for future expansion.

**Results:** Drop-off: HIGH / Job Proposal: Irrelevant / Next Action: None / Region Bias: CRITICAL / National Expansion Risk: HIGH
**Failure Category:** Regional Gap + Cross-Border / **Severity:** P1-High / **Fix Proposal:** Add "ご希望エリアを教えてください" free text field for "other" users, store for demand analysis / **Retry Needed:** Yes / **Auditor Comment:** Losing dual-market potential. 豊橋-浜松 corridor is a real commuting zone.

---

### Case W4-004
- **Prefecture:** 愛知県 / **Region Block:** 東海 / **Case Type:** Standard / **User Profile:** 愛知県一宮市、訪問看護希望 / **Entry Route:** Instagram広告 → LINE / **Difficulty:** Medium

**Scenario:** Instagram広告を見てLINE登録。訪問看護で自宅近くを希望。

**Conversation Flow:**
1. User follows LINE from IG ad → Welcome
2. Bot shows area selection
3. User taps "その他の地域"
4. Bot → il_facility_type
5. User taps "訪問看護" → il_workstyle
6. User taps "日勤のみ"
7. Bot → il_urgency → User taps "すぐ転職したい"
8. Bot → matching_preview: 5 Kanto visiting nurse stations
9. User: sees facilities in 横浜/川崎 — completely irrelevant for 一宮市
10. User blocks LINE account

**System Behavior Evaluation:**
- Ad spend wasted: CPC ~53 + LINE registration cost, zero conversion potential.
- Visiting nurse positions are hyper-local (commuting distance matters enormously).
- Showing 横浜 visiting nurse jobs to 一宮 user is borderline deceptive.

**Results:** Drop-off: VERY HIGH / Job Proposal: 100% irrelevant / Next Action: Block / Region Bias: CRITICAL / National Expansion Risk: HIGH — ad spend waste
**Failure Category:** Regional Gap + Ad Funnel Leak / **Severity:** P0-Critical / **Fix Proposal:** (1) Meta ad targeting should exclude 東海 region until coverage exists, (2) Add geographic disclaimer at "その他の地域" / **Retry Needed:** Yes / **Auditor Comment:** Ad money burned on users the bot cannot serve. Meta targeting geo-exclusion is immediate low-cost fix.

---

### Case W4-005
- **Prefecture:** 愛知県 / **Region Block:** 東海 / **Case Type:** Adversarial / **User Profile:** 名古屋市中区、転職エージェント経験者 / **Entry Route:** TikTok → LINE / **Difficulty:** Hard

**Scenario:** 他社エージェントも利用中の看護師。「その他の地域」ラベルに不信感を持ち、ボタンを押さない。

**Conversation Flow:**
1. User follows LINE → Welcome
2. Bot shows: 東京都/神奈川県/千葉県/埼玉県/その他の地域
3. User types "愛知県はないんですか？"
4. Bot: unexpectedTextCount=1 → Quick Reply re-display
5. User types "名古屋で働きたいです。その他の地域って何ですか？"
6. Bot: unexpectedTextCount=2 → Quick Reply re-display (same buttons)
7. User types "対応エリア教えてください"
8. Bot: unexpectedTextCount=3 → Quick Reply re-display (no escalation logic)
9. User gives up, blocks account
10. (Lost a high-value candidate — experienced nurse actively looking)

**System Behavior Evaluation:**
- unexpectedTextCount increments but never triggers escalation or human handoff.
- No threshold-based Slack alert for repeated unexpected text.
- User's explicit question about coverage area goes completely unanswered.

**Results:** Drop-off: CERTAIN / Job Proposal: None / Next Action: Block / Region Bias: CRITICAL / National Expansion Risk: HIGH
**Failure Category:** Free Text Dead End + No Escalation / **Severity:** P0-Critical / **Fix Proposal:** (1) At unexpectedTextCount>=3, offer human handoff or explain coverage, (2) Log these messages for demand analysis, (3) Send Slack alert when user appears stuck / **Retry Needed:** Yes / **Auditor Comment:** Three explicit attempts to communicate, all ignored. This is the worst possible UX for a service that claims "24時間AIサポート".

---

### Case W4-006
- **Prefecture:** 愛知県 / **Region Block:** 東海 / **Case Type:** Standard / **User Profile:** 春日井市、回復期リハビリ志望 / **Entry Route:** SEO検索 → LP → LINE / **Difficulty:** Medium

**Scenario:** "看護師 転職 愛知" でGoogle検索、SEOページからLP経由でLINE登録。

**Conversation Flow:**
1. User searches Google → lands on quads-nurse.com (神奈川ナース転職)
2. Site name says "神奈川" but user registers anyway (hoping for 愛知 coverage)
3. User follows LINE → Welcome
4. Bot: "○○件の医療機関の中から..."
5. User taps "その他の地域"
6. Bot proceeds → il_facility_type → "回復期病院"
7. → il_department → "リハビリ"
8. → il_workstyle → "日勤のみ"
9. → il_urgency → "すぐ転職したい"
10. matching_preview: 5 Kanto回復期hospitals → total mismatch

**System Behavior Evaluation:**
- Site branding "神奈川ナース転職" should deter non-Kanagawa users, but "その他の地域" button implies wider coverage.
- Brand confusion: site says 神奈川, bot says 24,488件 (implying national).

**Results:** Drop-off: HIGH / Job Proposal: Irrelevant / Next Action: None / Region Bias: CRITICAL / National Expansion Risk: MEDIUM
**Failure Category:** Brand Mismatch + Regional Gap / **Severity:** P1-High / **Fix Proposal:** Either rename bot to reflect national ambition or explicitly state "神奈川・東京・千葉・埼玉限定" / **Retry Needed:** Yes / **Auditor Comment:** The total facility count (24,488) displayed at il_area implies national coverage. This is misleading.

---

### Case W4-007
- **Prefecture:** 愛知県 / **Region Block:** 東海 / **Case Type:** Boundary / **User Profile:** 愛知県豊田市、自動車工場健康管理室勤務 / **Entry Route:** LINE友達追加 / **Difficulty:** Medium

**Scenario:** 企業内看護師から病院転職希望。施設タイプ「こだわりなし」で進む。

**Conversation Flow:**
1. User follows LINE → Welcome
2. User taps "その他の地域"
3. Bot → il_facility_type → User taps "こだわりなし"
4. Bot → il_workstyle → User taps "日勤のみ"
5. Bot → il_urgency → User taps "良い求人があれば"
6. matching_preview: 5 mixed Kanto facilities
7. User taps "他の求人も見たい" (matching_browse)
8. Bot shows 3 more Kanto facilities
9. User taps "条件を変える" → loops back to il_area
10. Same options, same dead end

**System Behavior Evaluation:**
- "条件を変える" loops back to il_area but same 5 options appear.
- No way to break out of Kanto-only results regardless of how many times user retries.
- Loop detection: none. User could cycle indefinitely.

**Results:** Drop-off: HIGH / Job Proposal: All irrelevant / Next Action: Frustration loop / Region Bias: CRITICAL / National Expansion Risk: HIGH
**Failure Category:** Infinite Loop + Regional Gap / **Severity:** P1-High / **Fix Proposal:** After 1 retry from matching_browse→il_area, offer human handoff instead / **Retry Needed:** Yes / **Auditor Comment:** The "条件を変える" escape hatch leads right back to the same wall.

---

### Case W4-008
- **Prefecture:** 愛知県 / **Region Block:** 東海 / **Case Type:** Adversarial / **User Profile:** 名古屋市港区、新卒看護師 / **Entry Route:** LINE友達追加 / **Difficulty:** Hard

**Scenario:** 新卒で初めての就職活動。LINE Botに質問形式で話しかける。

**Conversation Flow:**
1. User follows LINE → Welcome
2. Bot shows il_area Quick Reply
3. User types "はじめまして！名古屋で新卒の求人探してます"
4. Bot: unexpectedTextCount++ → Quick Reply re-display
5. User types "新卒でも大丈夫ですか？"
6. Bot: unexpectedTextCount++ → Quick Reply re-display
7. User taps "その他の地域" (gives up on conversation)
8. Bot proceeds through intake → matching_preview with Kanto results
9. User types "関東じゃなくて名古屋がいいんですけど..."
10. Bot: re-displays matching Quick Reply

**System Behavior Evaluation:**
- Bot cannot engage in any conversational exchange during intake_light.
- New grad specific needs (教育体制, プリセプター) cannot be captured.
- "はじめまして" greeting completely ignored.

**Results:** Drop-off: VERY HIGH / Job Proposal: Irrelevant / Next Action: None / Region Bias: CRITICAL / National Expansion Risk: HIGH
**Failure Category:** Conversational Dead End + Regional Gap / **Severity:** P1-High / **Fix Proposal:** (1) Detect greeting patterns and respond warmly before Quick Reply, (2) Parse city/prefecture names from free text / **Retry Needed:** Yes / **Auditor Comment:** New grad nurse's first impression of the service is being repeatedly ignored. Brand damage.

---

### Case W4-009
- **Prefecture:** 愛知県 / **Region Block:** 東海 / **Case Type:** Standard / **User Profile:** 岡崎市、夜勤専従希望 / **Entry Route:** LINE友達追加 / **Difficulty:** Medium

**Scenario:** 夜勤専従で高収入を狙う看護師。

**Conversation Flow:**
1. User follows LINE → Welcome
2. User taps "その他の地域"
3. Bot → il_facility_type → "急性期病院"
4. → il_department → "救急"
5. → il_workstyle → "夜勤あり"
6. → il_urgency → "すぐ転職したい"
7. matching_preview: 5 Kanto acute hospitals with ER
8. User sees "横浜市立大学附属病院" etc. — meaningless for岡崎市
9. User taps "今はやめておく" → nurture_warm
10. Bot enters nurture but user will never reactivate (wrong region)

**System Behavior Evaluation:**
- Nurture flow wastes resources on a user who will never convert (wrong geography).
- 夜勤専従 is a specific, high-value search — lost entirely.

**Results:** Drop-off: Deferred (nurture) but CERTAIN eventual / Job Proposal: Irrelevant / Next Action: Nurture (wasted) / Region Bias: CRITICAL / National Expansion Risk: HIGH
**Failure Category:** Regional Gap + Nurture Waste / **Severity:** P1-High / **Fix Proposal:** Tag nurture entries with requested_region for future expansion targeting / **Retry Needed:** Yes / **Auditor Comment:** Every nurture push notification to this user is spam since we have no 愛知 facilities.

---

### Case W4-010
- **Prefecture:** 愛知県 / **Region Block:** 東海 / **Case Type:** Adversarial / **User Profile:** 名古屋市千種区、精神科10年経験 / **Entry Route:** Web診断LP → LINE引き継ぎ / **Difficulty:** Hard

**Scenario:** LP上のWeb診断で3問回答済み、引き継ぎコードでLINEに入る。しかし Web診断にも地域制限の表示がなかった。

**Conversation Flow:**
1. User completes LP mini-diagnosis (area: undecided, workstyle: 二交代, urgency: すぐ)
2. LP generates handoff code → User enters code in LINE
3. Bot: intake_light skip → immediate matching_preview
4. matching_preview: 5 Kanto facilities (user selected "undecided" on LP)
5. User: "名古屋の精神科病院を探しているんですが"
6. Bot: unexpectedTextCount++ → matching Quick Reply re-display
7. User taps "条件を変える"
8. Bot → il_area → same 5 options
9. User taps "その他の地域" → same Kanto results
10. User drops off, negative impression of both LP and LINE Bot

**System Behavior Evaluation:**
- Web→LINE handoff preserves "undecided" area → Kanto matching.
- Double deception: LP didn't warn about region limits, bot doesn't explain either.
- Web diagnosis completion was tracked as intake_complete event → inflated funnel metrics.

**Results:** Drop-off: CERTAIN / Job Proposal: Irrelevant / Next Action: None / Region Bias: CRITICAL / National Expansion Risk: HIGH
**Failure Category:** Web-LINE Handoff + Regional Gap / **Severity:** P0-Critical / **Fix Proposal:** LP must display "現在の対応エリア: 東京・神奈川・千葉・埼玉" before diagnosis starts / **Retry Needed:** Yes / **Auditor Comment:** The handoff path is the premium flow. Failing here means the most engaged users are getting the worst experience.

---

## Gifu Prefecture (岐阜) — 8 cases

### Case W4-011
- **Prefecture:** 岐阜県 / **Region Block:** 東海 / **Case Type:** Standard / **User Profile:** 岐阜市内の総合病院、5年目 / **Entry Route:** LINE友達追加 / **Difficulty:** Medium

**Scenario:** 岐阜市在住看護師が転職活動。地元希望。

**Conversation Flow:**
1. User follows LINE → Welcome
2. Bot shows il_area buttons
3. User taps "その他の地域"
4. Bot: "その他の地域ですね！ 候補: XX件" → il_facility_type
5. User taps "急性期病院" → il_department
6. User taps "外科系" → il_workstyle
7. User taps "二交代" → il_urgency
8. User taps "すぐ転職したい"
9. matching_preview: 5 Kanto hospitals
10. User: 岐阜の病院がゼロ → drop-off

**System Behavior Evaluation:**
- Identical to 愛知 pattern. "その他の地域" → undecided → Kanto only.
- 岐阜 is smaller than 愛知 but still 2M population.

**Results:** Drop-off: HIGH / Job Proposal: Irrelevant / Next Action: None / Region Bias: CRITICAL / National Expansion Risk: MEDIUM
**Failure Category:** Regional Coverage Gap / **Severity:** P1-High / **Fix Proposal:** Same as W4-001 / **Retry Needed:** Yes / **Auditor Comment:** 岐阜 users get zero indication before completing full intake that no local results exist.

---

### Case W4-012
- **Prefecture:** 岐阜県 / **Region Block:** 東海 / **Case Type:** Boundary / **User Profile:** 大垣市、名古屋通勤可能 / **Entry Route:** LINE友達追加 / **Difficulty:** Medium

**Scenario:** 大垣市在住だが名古屋駅まで JR で30分。名古屋勤務も視野に入れている。しかし DB にはどちらも存在しない。

**Conversation Flow:**
1. User follows LINE → Welcome
2. User taps "その他の地域"
3. Bot → il_facility_type → "クリニック" → il_urgency (clinic skips)
4. User taps "良い求人があれば"
5. matching_preview: 5 Kanto clinics
6. User types "大垣か名古屋のクリニック希望です"
7. Bot: re-displays Quick Reply
8. User taps "今はやめておく"
9. Bot → nurture_warm
10. User eventually blocks

**System Behavior Evaluation:**
- Cross-prefecture commuting (岐阜→愛知) is extremely common in 東海 region.
- Neither prefecture has DB coverage, making cross-border logic irrelevant.

**Results:** Drop-off: HIGH / Job Proposal: Irrelevant / Next Action: Nurture (wasted) / Region Bias: CRITICAL / National Expansion Risk: HIGH
**Failure Category:** Regional Gap + Cross-Border / **Severity:** P1-High / **Fix Proposal:** Priority: add 愛知 first, then cross-border 岐阜→愛知 / **Retry Needed:** Yes / **Auditor Comment:** 大垣→名古屋 is a daily commute corridor. Losing both ends.

---

### Case W4-013
- **Prefecture:** 岐阜県 / **Region Block:** 東海 / **Case Type:** Standard / **User Profile:** 高山市、地方在住看護師 / **Entry Route:** LINE友達追加 / **Difficulty:** Easy

**Scenario:** 飛騨地方の山間部在住。地元の病院は少なく選択肢が限られる。

**Conversation Flow:**
1. User follows LINE → Welcome
2. User taps "その他の地域"
3. Bot → il_facility_type → "こだわりなし"
4. → il_workstyle → "日勤のみ"
5. → il_urgency → "情報収集中"
6. matching_preview: 5 Kanto facilities
7. User sees results all in 関東 → "高山からは通えません"
8. Bot: re-displays Quick Reply
9. User taps "今はやめておく"
10. User blocks

**System Behavior Evaluation:**
- Rural users have the most to gain from job matching services.
- 高山市 is 4+ hours from any DB facility.

**Results:** Drop-off: HIGH / Job Proposal: Geographically impossible / Next Action: None / Region Bias: CRITICAL / National Expansion Risk: MEDIUM
**Failure Category:** Regional Gap (Rural) / **Severity:** P1-High / **Fix Proposal:** For rural "other" users, offer "引越し前提の転職も検討されますか？" before showing Kanto results / **Retry Needed:** Yes / **Auditor Comment:** At least ask if relocation is an option before showing distant results.

---

### Case W4-014
- **Prefecture:** 岐阜県 / **Region Block:** 東海 / **Case Type:** Adversarial / **User Profile:** 各務原市、航空自衛隊基地近くの看護師 / **Entry Route:** LINE友達追加 / **Difficulty:** Hard

**Scenario:** 自衛隊病院から民間転職希望。Free text で具体的に "各務原市か岐阜市" と入力。

**Conversation Flow:**
1. User follows LINE → Welcome
2. Bot shows il_area buttons
3. User types "各務原市か岐阜市で探しています"
4. Bot: unexpectedTextCount=1 → re-displays Quick Reply
5. User types "岐阜県"
6. Bot: unexpectedTextCount=2 → re-displays Quick Reply
7. User types "岐阜！"
8. Bot: unexpectedTextCount=3 → re-displays Quick Reply (no escalation)
9. User gives up, does not tap any button
10. Session abandoned

**System Behavior Evaluation:**
- "岐阜県" as free text is not parsed. TEXT_TO_POSTBACK has no 岐阜 mapping.
- 3 attempts, zero acknowledgment of user's prefecture.

**Results:** Drop-off: CERTAIN / Job Proposal: None / Next Action: None / Region Bias: CRITICAL / National Expansion Risk: HIGH
**Failure Category:** Free Text Dead End / **Severity:** P0-Critical / **Fix Proposal:** Add prefecture keyword detection → map to "other" postback + display honest coverage message / **Retry Needed:** Yes / **Auditor Comment:** Bot feels broken when it ignores explicit prefecture names 3 times in a row.

---

### Case W4-015
- **Prefecture:** 岐阜県 / **Region Block:** 東海 / **Case Type:** Standard / **User Profile:** 関市、介護施設勤務 / **Entry Route:** LINE友達追加 / **Difficulty:** Easy

**Scenario:** 介護施設から病院への転職希望。

**Conversation Flow:**
1. User follows LINE → Welcome
2. User taps "その他の地域"
3. Bot → il_facility_type → "急性期病院"
4. → il_department → "整形外科"
5. → il_workstyle → "二交代"
6. → il_urgency → "すぐ転職したい"
7. matching_preview: Kanto acute hospitals
8. User confused, taps "もっと詳しく聞きたい"
9. Bot → matching/consultation flow begins
10. User discovers during consultation that service is Kanto-only → frustrated drop-off

**System Behavior Evaluation:**
- User progressed deep into funnel before discovering regional mismatch.
- Consultation start tracked as event → inflates funnel metrics.

**Results:** Drop-off: Late-stage (post-consultation start) / Job Proposal: Irrelevant / Next Action: None / Region Bias: CRITICAL / National Expansion Risk: MEDIUM
**Failure Category:** Late Discovery of Regional Gap / **Severity:** P1-High / **Fix Proposal:** Display coverage disclaimer at "その他の地域" selection, not after full intake / **Retry Needed:** Yes / **Auditor Comment:** Late-stage drop-offs are the most expensive in terms of bot compute and user trust.

---

### Case W4-016
- **Prefecture:** 岐阜県 / **Region Block:** 東海 / **Case Type:** Boundary / **User Profile:** 多治見市、名古屋通勤圏 / **Entry Route:** LINE友達追加 / **Difficulty:** Medium

**Scenario:** 多治見市在住、名古屋まで JR 中央線で40分。実質名古屋通勤圏。

**Conversation Flow:**
1. User follows LINE → Welcome
2. User taps "その他の地域"
3. Bot → il_facility_type → "回復期病院"
4. → il_department → "リハビリ"
5. → il_workstyle → "日勤のみ"
6. → il_urgency → "良い求人があれば"
7. matching_preview: 5 Kanto回復期
8. User taps "条件を変える" → il_area
9. Same 5 options → taps "その他の地域" again
10. Same Kanto results → drop-off

**System Behavior Evaluation:**
- Condition change loop provides no new results for non-Kanto users.

**Results:** Drop-off: HIGH / Job Proposal: Irrelevant / Next Action: Loop → drop / Region Bias: CRITICAL / National Expansion Risk: MEDIUM
**Failure Category:** Regional Gap + Retry Loop / **Severity:** P1-High / **Fix Proposal:** Same as W4-007 / **Retry Needed:** Yes / **Auditor Comment:** 多治見→名古屋 is a standard commuting pattern. Both are missing from DB.

---

### Case W4-017
- **Prefecture:** 岐阜県 / **Region Block:** 東海 / **Case Type:** Adversarial / **User Profile:** 中津川市、Uターン希望 / **Entry Route:** LINE友達追加 / **Difficulty:** Hard

**Scenario:** 現在東京勤務、地元岐阜にUターン転職希望。東京の結果が出ても意味がない。

**Conversation Flow:**
1. User follows LINE → Welcome
2. User taps "その他の地域" (東京に今いるが岐阜に帰りたい)
3. Bot → intake完了 → matching_preview: Kanto results
4. User: "東京じゃなくて岐阜に戻りたいんです"
5. Bot: re-displays Quick Reply
6. User taps "条件を変える" → il_area
7. User sees "東京都" button → does NOT tap it (東京は今の居場所であって希望地ではない)
8. User taps "その他の地域" again → same loop
9. User types "Uターンで岐阜希望"
10. Bot: re-displays Quick Reply

**System Behavior Evaluation:**
- Uターン/Iターン use case completely unsupported.
- User's current location ≠ desired location, bot cannot distinguish.

**Results:** Drop-off: CERTAIN / Job Proposal: Actively wrong (shows current area, not desired) / Next Action: None / Region Bias: CRITICAL / National Expansion Risk: HIGH
**Failure Category:** Use Case Gap (U-turn migration) / **Severity:** P1-High / **Fix Proposal:** (1) Explicitly ask "働きたいエリア" vs "現在のエリア", (2) Support relocation use case / **Retry Needed:** Yes / **Auditor Comment:** U-turn migration is a major nursing trend in Japan. Not supporting it is a strategic gap.

---

### Case W4-018
- **Prefecture:** 岐阜県 / **Region Block:** 東海 / **Case Type:** Standard / **User Profile:** 岐阜市、産婦人科5年 / **Entry Route:** LINE友達追加 / **Difficulty:** Easy

**Scenario:** 産婦人科経験者、地元で同じ診療科を希望。

**Conversation Flow:**
1. User follows LINE → Welcome
2. User taps "その他の地域"
3. Bot → il_facility_type → "急性期病院"
4. → il_department → "産婦人科"
5. → il_workstyle → "夜勤あり"
6. → il_urgency → "すぐ転職したい"
7. matching_preview: Kanto産婦人科のある病院
8. User: 岐阜のではない → drops off
9. (Session data lost, no demand signal captured)
10. No follow-up possible

**System Behavior Evaluation:**
- Specialty-specific search (産婦人科) with zero local results.
- No demand logging for future 岐阜 expansion planning.

**Results:** Drop-off: HIGH / Job Proposal: Irrelevant / Next Action: None / Region Bias: CRITICAL / National Expansion Risk: MEDIUM
**Failure Category:** Regional Gap / **Severity:** P1-High / **Fix Proposal:** Log {prefecture: "岐阜", specialty: "産婦人科"} demand data / **Retry Needed:** Yes / **Auditor Comment:** Demand data from failed sessions is gold for expansion planning but currently discarded.

---

## Shizuoka Prefecture (静岡) — 8 cases

### Case W4-019
- **Prefecture:** 静岡県 / **Region Block:** 東海 / **Case Type:** Boundary / **User Profile:** 熱海市、神奈川通勤可能 / **Entry Route:** LINE友達追加 / **Difficulty:** Medium

**Scenario:** 熱海市在住、小田原まで新幹線/JRで20分。実質神奈川県西通勤圏。

**Conversation Flow:**
1. User follows LINE → Welcome
2. User taps "神奈川県" (通勤可能なので)
3. Bot → il_subarea → User taps "小田原・県西"
4. Bot → il_facility_type → "急性期病院"
5. → il_department → "内科系"
6. → il_workstyle → "二交代"
7. → il_urgency → "すぐ転職したい"
8. matching_preview: 5 県西エリア hospitals (小田原, 秦野, 平塚等)
9. User finds relevant results! Some within commuting distance.
10. User taps "もっと詳しく聞きたい" → consultation flow

**System Behavior Evaluation:**
- This is a SUCCESS case. 熱海→小田原 cross-border commuting works because user chose 神奈川県.
- Bot has 県西 facilities that are genuinely reachable from 熱海.
- However, user needed to know to select 神奈川県 instead of "その他の地域".

**Results:** Drop-off: LOW / Job Proposal: Relevant (県西) / Next Action: Consultation / Region Bias: None (user self-corrected) / National Expansion Risk: LOW
**Failure Category:** None (success) / **Severity:** N/A / **Fix Proposal:** Add hint text: "通勤圏で選んでください" at il_area phase / **Retry Needed:** No / **Auditor Comment:** Rare success for 東海 user, but only because 熱海 is on the Kanagawa border and user was savvy enough to select 神奈川.

---

### Case W4-020
- **Prefecture:** 静岡県 / **Region Block:** 東海 / **Case Type:** Boundary / **User Profile:** 三島市、神奈川と静岡の中間 / **Entry Route:** LINE友達追加 / **Difficulty:** Medium

**Scenario:** 三島市在住。小田原まで新幹線こだまで15分だが、沼津・静岡方面も視野。

**Conversation Flow:**
1. User follows LINE → Welcome
2. User hesitates between "神奈川県" and "その他の地域"
3. User taps "その他の地域" (静岡県民としてのアイデンティティ)
4. Bot: "その他の地域ですね！ 候補: XX件" → il_facility_type
5. → "回復期病院" → "リハビリ" → "日勤のみ" → "良い求人があれば"
6. matching_preview: Kanto facilities (not 県西 specific — undecided shows all Kanto)
7. User sees 横浜/東京の病院 → "小田原近辺はないですか？"
8. Bot: re-displays Quick Reply
9. User taps "条件を変える" → il_area → taps "神奈川県" → "小田原・県西"
10. Now gets relevant 県西 results → success on 2nd attempt

**System Behavior Evaluation:**
- User had to go through full intake TWICE to get relevant results.
- The 1st attempt wasted time but user was persistent enough to retry.
- "その他の地域" did not surface 県西 options even though they would have been relevant.

**Results:** Drop-off: MEDIUM (recovered on retry) / Job Proposal: Eventually relevant / Next Action: Consultation possible / Region Bias: 1st attempt CRITICAL, 2nd OK / National Expansion Risk: MEDIUM
**Failure Category:** Suboptimal Routing / **Severity:** P2-Medium / **Fix Proposal:** For "other" users near Kanagawa border, suggest "神奈川県西エリアも通勤圏ですか？" / **Retry Needed:** No (self-recovered) / **Auditor Comment:** User wasted 5+ minutes on 1st attempt. Many users would not retry.

---

### Case W4-021
- **Prefecture:** 静岡県 / **Region Block:** 東海 / **Case Type:** Standard / **User Profile:** 静岡市駿河区、7年目 / **Entry Route:** LINE友達追加 / **Difficulty:** Medium

**Scenario:** 静岡市中心部在住。県庁所在地で病院数は多いが DB にゼロ。

**Conversation Flow:**
1. User follows LINE → Welcome
2. User taps "その他の地域"
3. Bot → intake完了 → matching_preview: Kanto facilities
4. User: 静岡市の病院がない → drop-off
5-10. (Standard drop-off pattern, same as W4-011)

**System Behavior Evaluation:**
- 静岡市 (人口69万) is a significant city with no DB coverage.

**Results:** Drop-off: HIGH / Job Proposal: Irrelevant / Next Action: None / Region Bias: CRITICAL / National Expansion Risk: HIGH
**Failure Category:** Regional Gap / **Severity:** P1-High / **Fix Proposal:** Same as W4-001 / **Retry Needed:** Yes / **Auditor Comment:** 静岡市 is larger than many covered Kanagawa cities.

---

### Case W4-022
- **Prefecture:** 静岡県 / **Region Block:** 東海 / **Case Type:** Standard / **User Profile:** 浜松市、3年目 / **Entry Route:** LINE友達追加 / **Difficulty:** Medium

**Scenario:** 浜松市(人口79万)在住看護師。静岡県最大の都市。

**Conversation Flow:**
1. User follows LINE → Welcome
2. User taps "その他の地域"
3. Bot → "急性期病院" → "循環器" → "二交代" → "すぐ転職したい"
4. matching_preview: Kanto循環器系hospitals
5. User: "浜松医科大学病院の近くで探しています"
6. Bot: re-displays Quick Reply
7. User drops off
8-10. (No recovery)

**System Behavior Evaluation:**
- 浜松市 is a 政令指定都市 (designated city) — same status as 横浜/川崎/さいたま.
- All three of those are in the DB, but 浜松 has zero.

**Results:** Drop-off: HIGH / Job Proposal: Irrelevant / Next Action: None / Region Bias: CRITICAL / National Expansion Risk: HIGH
**Failure Category:** Regional Gap / **Severity:** P1-High / **Fix Proposal:** Add 政令指定都市 as priority expansion targets / **Retry Needed:** Yes / **Auditor Comment:** 浜松 is a designated city like 横浜. Coverage disparity is glaring.

---

### Case W4-023
- **Prefecture:** 静岡県 / **Region Block:** 東海 / **Case Type:** Boundary / **User Profile:** 御殿場市、神奈川も通勤圏 / **Entry Route:** LINE友達追加 / **Difficulty:** Medium

**Scenario:** 御殿場市在住、小田原まで車で1時間。県西エリアも通勤可能だが微妙。

**Conversation Flow:**
1. User follows LINE → Welcome
2. User taps "その他の地域" (静岡県だから)
3. Bot → intake完了 → Kanto results
4. User sees 小田原の病院があるが「その他の地域」なので横浜/東京が主
5. User types "小田原近辺なら通えます"
6. Bot: re-displays Quick Reply
7. User taps "条件を変える" → il_area
8. User taps "神奈川県" → "小田原・県西"
9. 県西の結果が出る → relevant
10. User proceeds to consultation

**System Behavior Evaluation:**
- Similar to W4-020. Recovery possible but requires user initiative.
- "その他の地域" → undecided shows all Kanto randomly, not nearest facilities.

**Results:** Drop-off: MEDIUM / Job Proposal: Eventually relevant / Next Action: Consultation / Region Bias: 1st attempt bad / National Expansion Risk: LOW
**Failure Category:** Suboptimal Routing / **Severity:** P2-Medium / **Fix Proposal:** Geo-proximity sorting for "undecided" users / **Retry Needed:** No / **Auditor Comment:** 御殿場→小田原 is viable but bot makes user discover it themselves.

---

### Case W4-024
- **Prefecture:** 静岡県 / **Region Block:** 東海 / **Case Type:** Adversarial / **User Profile:** 富士市、看護師長経験 / **Entry Route:** LINE友達追加 / **Difficulty:** Hard

**Scenario:** 管理職経験者。「その他の地域」というラベルに管理職としての不信感。

**Conversation Flow:**
1. User follows LINE → Welcome
2. Bot shows: 東京都/神奈川県/千葉県/埼玉県/その他の地域
3. User types "静岡県の管理職求人を探しています"
4. Bot: unexpectedTextCount++ → Quick Reply re-display
5. User types "対応エリアを教えてください。静岡は対象ですか？"
6. Bot: unexpectedTextCount++ → Quick Reply re-display
7. User: "このサービスは関東限定ですか？直接聞いてるんですが"
8. Bot: unexpectedTextCount++ → Quick Reply re-display
9. User: increasingly frustrated, three explicit questions unanswered
10. User blocks, leaves negative review/口コミ

**System Behavior Evaluation:**
- Senior/management-level nurses are the highest-value candidates.
- Three direct questions about coverage completely ignored.
- Risk of negative word-of-mouth in nursing community.

**Results:** Drop-off: CERTAIN / Job Proposal: None / Next Action: Block + negative WOM / Region Bias: CRITICAL / National Expansion Risk: VERY HIGH
**Failure Category:** Free Text Dead End + High-Value Candidate Loss / **Severity:** P0-Critical / **Fix Proposal:** (1) Implement unexpectedTextCount>=3 escalation, (2) Parse "対応エリア" "対象" keywords → respond with coverage info / **Retry Needed:** Yes / **Auditor Comment:** Losing a nurse manager to bot silence is catastrophic. One negative 口コミ from a senior nurse can deter dozens of potential users.

---

### Case W4-025
- **Prefecture:** 静岡県 / **Region Block:** 東海 / **Case Type:** Standard / **User Profile:** 沼津市、訪問看護希望 / **Entry Route:** LINE友達追加 / **Difficulty:** Easy

**Scenario:** 沼津市で訪問看護ステーション希望。

**Conversation Flow:**
1. User follows LINE → Welcome
2. User taps "その他の地域"
3. Bot → "訪問看護" → "日勤のみ" (auto) → il_urgency
4. User taps "良い求人があれば"
5. matching_preview: Kanto visiting nurse stations
6. User: 沼津は通えない → drop-off

**System Behavior Evaluation:**
- Visiting nurse: commuting distance is critical (home visits within service area).
- Showing Kanto VNS to 沼津 user is completely unusable.

**Results:** Drop-off: HIGH / Job Proposal: Geographically impossible / Next Action: None / Region Bias: CRITICAL / National Expansion Risk: MEDIUM
**Failure Category:** Regional Gap / **Severity:** P1-High / **Fix Proposal:** Same as W4-001 / **Retry Needed:** Yes / **Auditor Comment:** Visiting nurse positions MUST be local. This is the worst match type for out-of-area users.

---

### Case W4-026
- **Prefecture:** 静岡県 / **Region Block:** 東海 / **Case Type:** Boundary / **User Profile:** 伊豆市、観光地の病院勤務 / **Entry Route:** LINE友達追加 / **Difficulty:** Medium

**Scenario:** 伊豆半島在住。最寄りの都市圏は小田原か三島。どちらに行くべきか迷っている。

**Conversation Flow:**
1. User follows LINE → Welcome
2. User taps "その他の地域"
3. Bot → intake → matching_preview: random Kanto
4. User types "伊豆から通える範囲で探したい"
5. Bot: re-displays Quick Reply
6. User taps "条件を変える"
7. User realizes "神奈川県" → "小田原・県西" might work
8. Taps 神奈川県 → 小田原・県西 → gets 県西 results
9. Some are viable (小田原、平塚)
10. User proceeds cautiously

**System Behavior Evaluation:**
- Similar to W4-019/W4-023 border cases.
- Partial success depends entirely on user's geographic knowledge.

**Results:** Drop-off: MEDIUM / Job Proposal: Partially relevant / Next Action: Maybe consultation / Region Bias: 1st attempt bad / National Expansion Risk: LOW
**Failure Category:** Suboptimal Routing / **Severity:** P2-Medium / **Fix Proposal:** Add "伊豆/熱海/三島の方は神奈川県西もご検討ください" hint / **Retry Needed:** No / **Auditor Comment:** Border area users CAN find results but the bot doesn't help them do so.

---

## Mie Prefecture (三重) — 8 cases

### Case W4-027
- **Prefecture:** 三重県 / **Region Block:** 東海 / **Case Type:** Standard / **User Profile:** 津市、県立病院勤務、5年目 / **Entry Route:** LINE友達追加 / **Difficulty:** Medium

**Scenario:** 三重県庁所在地の看護師。地元で転職希望。

**Conversation Flow:**
1. User follows LINE → Welcome
2. User taps "その他の地域"
3. Bot → "急性期病院" → "内科系" → "二交代" → "すぐ転職したい"
4. matching_preview: Kanto hospitals
5. User: 三重の病院がない → drop-off

**System Behavior Evaluation:**
- Standard regional gap pattern.

**Results:** Drop-off: HIGH / Job Proposal: Irrelevant / Next Action: None / Region Bias: CRITICAL / National Expansion Risk: MEDIUM
**Failure Category:** Regional Gap / **Severity:** P1-High / **Fix Proposal:** Same as W4-001 / **Retry Needed:** Yes / **Auditor Comment:** 三重 is the most isolated 東海 prefecture from Kanto — zero viable commuting options.

---

### Case W4-028
- **Prefecture:** 三重県 / **Region Block:** 東海 / **Case Type:** Standard / **User Profile:** 四日市市、石油化学工場の産業看護師 / **Entry Route:** LINE友達追加 / **Difficulty:** Medium

**Scenario:** 産業看護師から病院へのキャリアチェンジ希望。名古屋も通勤圏。

**Conversation Flow:**
1. User follows LINE → Welcome
2. User taps "その他の地域"
3. Bot → intake → matching_preview: Kanto
4. User: "四日市か名古屋で探してます"
5. Bot: re-displays Quick Reply
6. User drops off

**System Behavior Evaluation:**
- 四日市→名古屋 は近鉄で30分（実質通勤圏）。両方ともDB外。

**Results:** Drop-off: HIGH / Job Proposal: Irrelevant / Next Action: None / Region Bias: CRITICAL / National Expansion Risk: HIGH
**Failure Category:** Regional Gap / **Severity:** P1-High / **Fix Proposal:** Same as W4-001 / **Retry Needed:** Yes / **Auditor Comment:** 四日市-名古屋 corridor lost entirely.

---

### Case W4-029
- **Prefecture:** 三重県 / **Region Block:** 東海 / **Case Type:** Adversarial / **User Profile:** 伊勢市、看護教員 / **Entry Route:** LINE友達追加 / **Difficulty:** Hard

**Scenario:** 看護学校教員から臨床復帰希望。"その他の地域" に対して詳細質問。

**Conversation Flow:**
1. User follows LINE → Welcome
2. User types "三重県伊勢市で臨床に復帰したいのですが、対応していただけますか？"
3. Bot: unexpectedTextCount=1 → Quick Reply re-display
4. User types "お返事いただけますか？"
5. Bot: unexpectedTextCount=2 → Quick Reply re-display
6. User types "ボタンは見えていますが、質問に答えてほしいです"
7. Bot: unexpectedTextCount=3 → Quick Reply re-display
8. User: gives up entirely
9-10. (Session abandoned, no recovery)

**System Behavior Evaluation:**
- Polite, clear communication from a professional educator — completely unacknowledged.
- Bot's behavior (silent re-display of same buttons) feels dismissive.

**Results:** Drop-off: CERTAIN / Job Proposal: None / Next Action: None / Region Bias: CRITICAL / National Expansion Risk: MEDIUM
**Failure Category:** Free Text Dead End / **Severity:** P0-Critical / **Fix Proposal:** At minimum, acknowledge free text with "申し訳ございません、ボタンからお選びください" + coverage explanation / **Retry Needed:** Yes / **Auditor Comment:** The bot's silence to polite questions is the single worst UX pattern identified. Must fix.

---

### Case W4-030
- **Prefecture:** 三重県 / **Region Block:** 東海 / **Case Type:** Boundary / **User Profile:** 桑名市、名古屋通勤圏 / **Entry Route:** LINE友達追加 / **Difficulty:** Medium

**Scenario:** 桑名→名古屋 近鉄で20分。実質名古屋都市圏だが DB にない。

**Conversation Flow:**
1. User follows LINE → Welcome
2. User taps "その他の地域"
3. Bot → intake → matching_preview: Kanto
4. User drops off (名古屋の結果すら出ない)

**System Behavior Evaluation:**
- 桑名は名古屋通勤圏のベッドタウン。名古屋DB があれば救える。

**Results:** Drop-off: HIGH / Job Proposal: Irrelevant / Next Action: None / Region Bias: CRITICAL / National Expansion Risk: HIGH
**Failure Category:** Regional Gap / **Severity:** P1-High / **Fix Proposal:** Priority: add 愛知(名古屋) → automatically captures 桑名・四日市通勤圏 / **Retry Needed:** Yes / **Auditor Comment:** Adding 名古屋 DB would save multiple 三重 border users too.

---

### Case W4-031
- **Prefecture:** 三重県 / **Region Block:** 東海 / **Case Type:** Standard / **User Profile:** 鈴鹿市、2年目 / **Entry Route:** Instagram広告 → LINE / **Difficulty:** Easy

**Scenario:** Instagram広告から流入。広告に地域制限の記載なし。

**Conversation Flow:**
1. User taps IG ad → LINE follow → Welcome
2. User taps "その他の地域"
3. Bot → intake → Kanto results
4. User: "鈴鹿の求人は？"
5. Bot: re-displays Quick Reply
6. User blocks

**System Behavior Evaluation:**
- Ad CPC wasted (~53). No geo-targeting exclusion for 三重.

**Results:** Drop-off: HIGH / Job Proposal: Irrelevant / Next Action: Block / Region Bias: CRITICAL / National Expansion Risk: MEDIUM
**Failure Category:** Ad Funnel Leak / **Severity:** P1-High / **Fix Proposal:** Meta ad geo-targeting: exclude 東海 / **Retry Needed:** Yes / **Auditor Comment:** Each 三重 user from ads is pure waste. IG ad targeting fix is immediate and free.

---

### Case W4-032
- **Prefecture:** 三重県 / **Region Block:** 東海 / **Case Type:** Standard / **User Profile:** 松阪市、精神科勤務 / **Entry Route:** LINE友達追加 / **Difficulty:** Easy

**Scenario:** 松阪市の精神科病院から転職希望。

**Conversation Flow:**
1. User follows LINE → Welcome
2. User taps "その他の地域"
3. Bot → "急性期病院" → "精神科" → "日勤のみ" → "良い求人があれば"
4. matching_preview: Kanto精神科
5. User: 三重ではない → drops off

**Results:** Drop-off: HIGH / Job Proposal: Irrelevant / Next Action: None / Region Bias: CRITICAL / National Expansion Risk: MEDIUM
**Failure Category:** Regional Gap / **Severity:** P1-High / **Fix Proposal:** Same as W4-001 / **Retry Needed:** Yes / **Auditor Comment:** Standard pattern. 三重 users have zero chance of relevant results.

---

### Case W4-033
- **Prefecture:** 三重県 / **Region Block:** 東海 / **Case Type:** Adversarial / **User Profile:** 志摩市、リゾート地看護師 / **Entry Route:** LINE友達追加 / **Difficulty:** Hard

**Scenario:** 志摩市（伊勢志摩）在住。超地方で選択肢が限られる中、AI転職に期待して登録。

**Conversation Flow:**
1. User follows LINE → Welcome
2. Bot: "24,488件の医療機関の中から..."
3. User: 24,488件もあるなら志摩にもあるはず → "その他の地域" タップ
4. Bot → intake → Kanto results
5. User: "志摩市近辺の求人はありますか？24,488件って言ってたのに..."
6. Bot: re-displays Quick Reply
7. User: trust completely broken
8-10. Drop-off + potential negative WOM

**System Behavior Evaluation:**
- "24,488件" count is technically correct (D1 total) but implies national coverage.
- User took the number at face value → felt deceived when results are all Kanto.
- This is the most trust-damaging scenario: explicit number promise → zero delivery.

**Results:** Drop-off: CERTAIN / Job Proposal: None / Next Action: Negative WOM / Region Bias: CRITICAL / National Expansion Risk: VERY HIGH
**Failure Category:** Misleading Count + Regional Gap / **Severity:** P0-Critical / **Fix Proposal:** (1) Show count per region, not total, (2) Or display "関東エリア: XX件" at il_area / **Retry Needed:** Yes / **Auditor Comment:** "24,488件" is the most dangerous number in the bot. It promises something the service cannot deliver to non-Kanto users.

---

### Case W4-034
- **Prefecture:** 三重県 / **Region Block:** 東海 / **Case Type:** Boundary / **User Profile:** 名張市、大阪通勤圏 / **Entry Route:** LINE友達追加 / **Difficulty:** Medium

**Scenario:** 名張市在住、近鉄で大阪まで通勤可能だが大阪もDB外。

**Conversation Flow:**
1. User follows LINE → Welcome
2. User taps "その他の地域"
3. Bot → intake → Kanto results
4. User: "大阪か名古屋方面で探しています"
5. Bot: re-displays Quick Reply
6. User drops off

**System Behavior Evaluation:**
- 名張→大阪 は近鉄で1時間。通勤可能だがDB外。
- 名張→名古屋 も近鉄で1.5時間。これもDB外。
- 三重県のどの方角に行っても DB 施設がない。

**Results:** Drop-off: HIGH / Job Proposal: Irrelevant / Next Action: None / Region Bias: CRITICAL / National Expansion Risk: HIGH
**Failure Category:** Regional Gap (all directions) / **Severity:** P1-High / **Fix Proposal:** 大阪・名古屋の DB 追加が先決 / **Retry Needed:** Yes / **Auditor Comment:** 名張 is trapped between two major metros, neither covered. Worst-case geographic isolation in the bot.

---

## Spare Cases (東海 Mixed) — 6 cases

### Case W4-035
- **Prefecture:** 愛知県 / **Region Block:** 東海 / **Case Type:** Standard / **User Profile:** 豊橋市、介護施設勤務 / **Entry Route:** LINE友達追加 / **Difficulty:** Easy

**Scenario:** 介護施設から介護施設への転職希望。

**Conversation Flow:**
1. User follows LINE → Welcome
2. User taps "その他の地域"
3. Bot → "介護施設" → "日勤のみ" → "良い求人があれば"
4. matching_preview: Kanto介護施設
5. User drops off

**Results:** Drop-off: HIGH / Job Proposal: Irrelevant / Next Action: None / Region Bias: CRITICAL / National Expansion Risk: MEDIUM
**Failure Category:** Regional Gap / **Severity:** P1-High / **Fix Proposal:** Same as W4-001 / **Retry Needed:** Yes / **Auditor Comment:**介護施設 is hyper-local. Kanto results are useless for 豊橋 user.

---

### Case W4-036
- **Prefecture:** 静岡県 / **Region Block:** 東海 / **Case Type:** Adversarial / **User Profile:** 浜松市、2回目の利用 / **Entry Route:** LINE再アクティベーション / **Difficulty:** Hard

**Scenario:** 以前登録して drop-off した浜松市ユーザーが、ナーチャリングメッセージで再来。

**Conversation Flow:**
1. Bot sends nurture message: "お仕事探しの状況はいかがですか？"
2. User taps "まだ探している"
3. Bot: nurture_reactivate → entry.phase = "il_area"
4. Same 5 options appear
5. User: "前も静岡の求人なかったですよね"
6. Bot: unexpectedTextCount++ → Quick Reply re-display
7. User: "まだ静岡はないんですか？"
8. Bot: unexpectedTextCount++ → Quick Reply re-display
9. User blocks permanently
10. (Nurture reactivation cost wasted)

**System Behavior Evaluation:**
- Nurture message sent to user who cannot be served → spam.
- Reactivation leads to identical dead end as first visit.
- nurture_reactivate event tracked → inflates metrics.

**Results:** Drop-off: CERTAIN (2nd time) / Job Proposal: Same irrelevant results / Next Action: Permanent block / Region Bias: CRITICAL / National Expansion Risk: HIGH
**Failure Category:** Nurture Waste + Regional Gap / **Severity:** P0-Critical / **Fix Proposal:** Tag users by requested_region, do NOT nurture users outside coverage area / **Retry Needed:** Yes / **Auditor Comment:** Sending nurture messages to users you cannot serve is worse than silence. It's active annoyance.

---

### Case W4-037
- **Prefecture:** 岐阜県 / **Region Block:** 東海 / **Case Type:** Boundary / **User Profile:** 中津川市、長野県境 / **Entry Route:** LINE友達追加 / **Difficulty:** Medium

**Scenario:** 中津川市在住。長野県(松本・飯田方面)も通勤圏だが両方DB外。

**Conversation Flow:**
1. User follows LINE → Welcome
2. User taps "その他の地域"
3. Bot → intake → Kanto results
4. User: "中津川か飯田の病院は？"
5. Bot: re-display
6. User drops off

**Results:** Drop-off: HIGH / Job Proposal: Irrelevant / Next Action: None / Region Bias: CRITICAL / National Expansion Risk: MEDIUM
**Failure Category:** Regional Gap / **Severity:** P1-High / **Fix Proposal:** Same as W4-001 / **Retry Needed:** Yes / **Auditor Comment:** Central Japan mountain corridor completely uncovered.

---

### Case W4-038
- **Prefecture:** 静岡県 / **Region Block:** 東海 / **Case Type:** Adversarial / **User Profile:** 磐田市、サッカー好き看護師 / **Entry Route:** TikTok → LINE / **Difficulty:** Hard

**Scenario:** TikTokでナースロビーのコンテンツを見て興味を持ちLINE登録。TikTokには地域制限の記載なし。

**Conversation Flow:**
1. User follows LINE from TikTok bio link → Welcome
2. Bot: "24,488件の医療機関から..."
3. User excited, taps "その他の地域"
4. Bot → intake → Kanto results
5. User: "あれ？磐田の求人は？TikTokで見て登録したのに"
6. Bot: re-displays Quick Reply
7. User: "TikTokの動画と違うじゃん"
8. Bot: re-displays Quick Reply
9. User screenshots and posts negative comment on TikTok
10. Potential viral negative PR

**System Behavior Evaluation:**
- TikTok/SNS content makes no geographic disclaimer.
- Bot's "24,488件" reinforces national coverage impression.
- Risk of negative TikTok comments visible to all followers.

**Results:** Drop-off: CERTAIN / Job Proposal: None / Next Action: Negative SNS / Region Bias: CRITICAL / National Expansion Risk: VERY HIGH
**Failure Category:** SNS Funnel + Regional Gap / **Severity:** P0-Critical / **Fix Proposal:** (1) Add "関東エリア対応" to TikTok bio, (2) SNS content should mention coverage area / **Retry Needed:** Yes / **Auditor Comment:** Negative TikTok comment has amplification risk. SNS bio must state coverage area.

---

### Case W4-039
- **Prefecture:** 愛知県 / **Region Block:** 東海 / **Case Type:** Standard / **User Profile:** 名古屋市緑区、ママナース / **Entry Route:** LINE友達追加 / **Difficulty:** Easy

**Scenario:** 育休明けのママナース、自宅近くのクリニック希望。通勤時間が最重要。

**Conversation Flow:**
1. User follows LINE → Welcome
2. User taps "その他の地域"
3. Bot → "クリニック" → il_urgency (skips workstyle)
4. User taps "すぐ転職したい"
5. matching_preview: Kanto clinics
6. User: "名古屋市内のクリニックは？子供がいるので近くがいい"
7. Bot: re-displays Quick Reply
8. User: motherhood urgency ignored → blocks

**Results:** Drop-off: CERTAIN / Job Proposal: Irrelevant (通勤不可能) / Next Action: Block / Region Bias: CRITICAL / National Expansion Risk: HIGH
**Failure Category:** Regional Gap + Life-Stage Mismatch / **Severity:** P1-High / **Fix Proposal:** Same as W4-001 / **Retry Needed:** Yes / **Auditor Comment:** ママナース segment is a core target persona. Losing them in 名古屋 is losing a key demographic.

---

### Case W4-040
- **Prefecture:** 三重県 / **Region Block:** 東海 / **Case Type:** Adversarial / **User Profile:** 尾鷲市、過疎地看護師 / **Entry Route:** LINE友達追加 / **Difficulty:** Hard

**Scenario:** 過疎地域の看護師。人手不足で疲弊。AI転職サービスに最後の希望を託す。

**Conversation Flow:**
1. User follows LINE → Welcome
2. Bot: "24,488件の医療機関から..."
3. User: hopeful → taps "その他の地域"
4. Bot → intake → Kanto results
5. User types "尾鷲市か新宮市で探しています。本当に困っています"
6. Bot: re-displays Quick Reply
7. User types "誰か助けてください"
8. Bot: re-displays Quick Reply
9. User: desperation unacknowledged → drops off
10. (Most vulnerable user population, zero support)

**System Behavior Evaluation:**
- Rural/過疎地 nurses are the most underserved and most in need.
- Bot cannot even acknowledge emotional distress signals.
- "誰か助けてください" gets same robotic Quick Reply re-display.

**Results:** Drop-off: CERTAIN / Job Proposal: None / Next Action: None / Region Bias: CRITICAL / National Expansion Risk: HIGH
**Failure Category:** Emotional Handling + Regional Gap / **Severity:** P0-Critical / **Fix Proposal:** (1) Detect distress keywords (困っています, 助けて) → immediate human handoff, (2) Even without local coverage, connect to human agent / **Retry Needed:** Yes / **Auditor Comment:** This is the ethical floor. A user saying "助けてください" must get human connection, not button re-display. Fix immediately.

---

## Cross-Region Cases — 10 cases

### Case W4-041
- **Prefecture:** 東京都 / **Region Block:** 関東 / **Case Type:** Standard / **User Profile:** 新宿区、急性期病院5年目 / **Entry Route:** LINE友達追加 / **Difficulty:** Easy

**Scenario:** 東京都内で転職希望。最も標準的な成功パターン。

**Conversation Flow:**
1. User follows LINE → Welcome
2. User taps "東京都"
3. Bot → il_subarea: "23区" / "多摩地域" / "どこでもOK"
4. User taps "23区"
5. Bot → il_facility_type → "急性期病院"
6. → il_department → "外科系"
7. → il_workstyle → "二交代"
8. → il_urgency → "すぐ転職したい"
9. matching_preview: 5 東京23区 acute hospitals — RELEVANT
10. User taps "もっと詳しく聞きたい" → consultation

**System Behavior Evaluation:**
- Full success path. 東京23区 has rich DB coverage.
- Subarea selection (23区/多摩) narrows well.

**Results:** Drop-off: LOW / Job Proposal: Highly relevant / Next Action: Consultation → potential conversion / Region Bias: None / National Expansion Risk: N/A
**Failure Category:** None (success) / **Severity:** N/A / **Fix Proposal:** N/A / **Retry Needed:** No / **Auditor Comment:** Baseline success case. This is what every user should experience.

---

### Case W4-042
- **Prefecture:** 東京都 / **Region Block:** 関東 / **Case Type:** Boundary / **User Profile:** 町田市、神奈川との県境 / **Entry Route:** LINE友達追加 / **Difficulty:** Medium

**Scenario:** 町田市在住。東京都だが実質神奈川(相模原)との生活圏。

**Conversation Flow:**
1. User follows LINE → Welcome
2. User taps "東京都"
3. Bot → il_subarea → User taps "多摩地域"
4. Bot → il_facility_type → "クリニック" → il_urgency
5. User taps "良い求人があれば"
6. matching_preview: 多摩地域 clinics (八王子、立川、町田等)
7. User: 結果に満足。相模原のも見たいが十分。
8. User taps "もっと詳しく聞きたい"
9. Consultation starts
10. Success

**System Behavior Evaluation:**
- 町田 is in 多摩 area list → results are relevant.
- User might miss 相模原 options but 多摩 results are acceptable.

**Results:** Drop-off: LOW / Job Proposal: Relevant / Next Action: Consultation / Region Bias: Slight (misses 相模原) / National Expansion Risk: N/A
**Failure Category:** None (success with minor gap) / **Severity:** N/A / **Fix Proposal:** Could suggest "相模原エリアも検討されますか？" for 町田 users / **Retry Needed:** No / **Auditor Comment:** Good outcome. Cross-border hint would make it perfect.

---

### Case W4-043
- **Prefecture:** 北海道 / **Region Block:** 北海道 / **Case Type:** Standard / **User Profile:** 札幌市、大学病院勤務 / **Entry Route:** LINE友達追加 / **Difficulty:** Medium

**Scenario:** 札幌の看護師がSNS経由で登録。北海道は完全にDB外。

**Conversation Flow:**
1. User follows LINE → Welcome
2. Bot: "24,488件の医療機関から..."
3. User taps "その他の地域"
4. Bot → intake → Kanto results
5. User: "札幌の求人はありますか？"
6. Bot: re-displays Quick Reply
7. User drops off

**System Behavior Evaluation:**
- 札幌(196万人)は日本5番目の都市。DB外。
- "24,488件" が全国対応を想起させる。

**Results:** Drop-off: HIGH / Job Proposal: Irrelevant / Next Action: None / Region Bias: CRITICAL / National Expansion Risk: HIGH
**Failure Category:** Regional Gap (major metro) / **Severity:** P1-High / **Fix Proposal:** Same as all non-Kanto cases / **Retry Needed:** Yes / **Auditor Comment:** 札幌 is a huge market. Same pattern as 名古屋.

---

### Case W4-044
- **Prefecture:** 北海道 / **Region Block:** 北海道 / **Case Type:** Adversarial / **User Profile:** 旭川市、地方病院勤務 / **Entry Route:** TikTok → LINE / **Difficulty:** Hard

**Scenario:** 旭川市の看護師。TikTok動画を見て期待して登録するが北海道は対象外。

**Conversation Flow:**
1. User follows LINE → Welcome
2. User types "旭川で転職したいです"
3. Bot: unexpectedTextCount++ → Quick Reply re-display
4. User taps "その他の地域"
5. Bot → intake → Kanto results
6. User: "北海道は対象外ですか？"
7. Bot: re-display
8. User blocks

**Results:** Drop-off: CERTAIN / Job Proposal: None / Next Action: Block / Region Bias: CRITICAL / National Expansion Risk: HIGH
**Failure Category:** Regional Gap + Free Text / **Severity:** P1-High / **Fix Proposal:** Prefecture keyword detection + coverage disclosure / **Retry Needed:** Yes / **Auditor Comment:** 旭川 is 4th largest city in Hokkaido. Completely unreachable from Kanto.

---

### Case W4-045
- **Prefecture:** 大阪府 / **Region Block:** 近畿 / **Case Type:** Standard / **User Profile:** 大阪市北区、急性期3年目 / **Entry Route:** LINE友達追加 / **Difficulty:** Medium

**Scenario:** 大阪(日本2番目の都市圏)の看護師。DB外。

**Conversation Flow:**
1. User follows LINE → Welcome
2. User taps "その他の地域"
3. Bot → intake → Kanto results
4. User: "大阪市内の求人は？"
5. Bot: re-display
6. User drops off immediately

**System Behavior Evaluation:**
- 大阪(880万都市圏)が「その他の地域」扱い。
- 日本2位の都市圏がDBゼロは最大級のギャップ。

**Results:** Drop-off: CERTAIN / Job Proposal: None / Next Action: None / Region Bias: CRITICAL / National Expansion Risk: VERY HIGH
**Failure Category:** Regional Gap (2nd largest metro) / **Severity:** P0-Critical / **Fix Proposal:** 大阪 DB 追加は 愛知 と同等優先度 / **Retry Needed:** Yes / **Auditor Comment:** 大阪 is arguably the biggest single expansion opportunity after the current 4 prefectures.

---

### Case W4-046
- **Prefecture:** 大阪府 / **Region Block:** 近畿 / **Case Type:** Adversarial / **User Profile:** 堺市、ベテラン15年 / **Entry Route:** SEO → LINE / **Difficulty:** Hard

**Scenario:** "看護師 転職 大阪" 検索でサイトにたどり着く。サイト名は「神奈川ナース転職」なのに登録してしまう。

**Conversation Flow:**
1. User somehow lands on quads-nurse.com
2. Follows LINE → Welcome
3. Bot: "24,488件..." → User taps "その他の地域"
4. Intake → Kanto results
5. User types "大阪の求人がひとつもないんですが...サイト名に神奈川って書いてありましたね"
6. Bot: re-display
7. User: realizes mistake and blocks
8-10. (Self-blame but still negative experience)

**Results:** Drop-off: CERTAIN / Job Proposal: None / Next Action: Block / Region Bias: CRITICAL / National Expansion Risk: HIGH
**Failure Category:** Brand Confusion + Regional Gap / **Severity:** P1-High / **Fix Proposal:** Bot welcome message should state coverage area explicitly / **Retry Needed:** Yes / **Auditor Comment:** Even when user self-identifies the brand mismatch, the experience is negative.

---

### Case W4-047
- **Prefecture:** 沖縄県 / **Region Block:** 沖縄 / **Case Type:** Standard / **User Profile:** 那覇市、中部病院5年目 / **Entry Route:** Instagram → LINE / **Difficulty:** Medium

**Scenario:** 沖縄の看護師がInstagram広告から登録。沖縄はDB外。

**Conversation Flow:**
1. User follows LINE from IG → Welcome
2. User taps "その他の地域"
3. Bot → intake → Kanto results
4. User: "沖縄から関東の求人紹介されても..."
5. Bot: re-display
6. User blocks

**System Behavior Evaluation:**
- 沖縄→関東は飛行機3時間。通勤は不可能。
- Uターン/移住希望者以外に価値なし。

**Results:** Drop-off: CERTAIN / Job Proposal: Geographically impossible / Next Action: Block / Region Bias: CRITICAL / National Expansion Risk: MEDIUM
**Failure Category:** Regional Gap + Ad Waste / **Severity:** P1-High / **Fix Proposal:** Meta ad geo-exclude 沖縄 / **Retry Needed:** Yes / **Auditor Comment:** IG ad spend on 沖縄 users is pure waste unless relocation is explicitly offered.

---

### Case W4-048
- **Prefecture:** 沖縄県 / **Region Block:** 沖縄 / **Case Type:** Boundary / **User Profile:** 沖縄在住、関東移住希望 / **Entry Route:** LINE友達追加 / **Difficulty:** Medium

**Scenario:** 沖縄から関東への移住を前提に転職活動中。唯一 "その他の地域" で成功しうるパターン。

**Conversation Flow:**
1. User follows LINE → Welcome
2. User taps "東京都" (移住先として)
3. Bot → "23区" → intake → matching_preview: 東京23区 hospitals
4. User: 結果は relevant (移住前提なので東京の求人が正しい)
5. User taps "もっと詳しく聞きたい"
6. Bot → consultation: "いつ頃の転職をお考えですか？"
7. User: "3ヶ月後に引っ越し予定です"
8. Consultation proceeds normally
9. Handoff to human agent
10. Success (移住前提なら全く問題なし)

**System Behavior Evaluation:**
- Relocation user who correctly selects destination prefecture → success.
- Bot has no way to know user is relocating, but it works by accident.

**Results:** Drop-off: LOW / Job Proposal: Relevant (移住先) / Next Action: Handoff → conversion possible / Region Bias: None / National Expansion Risk: N/A
**Failure Category:** None (success) / **Severity:** N/A / **Fix Proposal:** N/A / **Retry Needed:** No / **Auditor Comment:** This works but only because user made the right choice. Bot should ask "現在のお住まいと希望勤務地は同じですか？" to support this pattern explicitly.

---

### Case W4-049
- **Prefecture:** 宮城県 / **Region Block:** 東北 / **Case Type:** Standard / **User Profile:** 仙台市、3年目 / **Entry Route:** LINE友達追加 / **Difficulty:** Medium

**Scenario:** 仙台市(109万人)の看護師。東北最大都市だがDB外。

**Conversation Flow:**
1. User follows LINE → Welcome
2. User taps "その他の地域"
3. Bot → intake → Kanto results
4. User: "仙台市内で探しているんですが"
5. Bot: re-display
6. User drops off

**System Behavior Evaluation:**
- 仙台(109万)は 政令指定都市。DB外。
- 東北地方全体がDB外。

**Results:** Drop-off: HIGH / Job Proposal: Irrelevant / Next Action: None / Region Bias: CRITICAL / National Expansion Risk: HIGH
**Failure Category:** Regional Gap / **Severity:** P1-High / **Fix Proposal:** 仙台 is a future expansion candidate / **Retry Needed:** Yes / **Auditor Comment:** 仙台 is another designated city without coverage.

---

### Case W4-050
- **Prefecture:** 宮城県 / **Region Block:** 東北 / **Case Type:** Adversarial / **User Profile:** 石巻市、被災地病院勤務 / **Entry Route:** LINE友達追加 / **Difficulty:** Hard

**Scenario:** 震災復興地域の過酷な環境から転職希望。感情的なメッセージを送る。

**Conversation Flow:**
1. User follows LINE → Welcome
2. User types "石巻の病院で10年働いています。人手が足りなくてもう限界です。仙台に転職したい"
3. Bot: unexpectedTextCount=1 → Quick Reply re-display
4. User types "誰か相談に乗ってもらえませんか"
5. Bot: unexpectedTextCount=2 → Quick Reply re-display
6. User taps "その他の地域" → intake → Kanto results
7. User: "仙台の求人を探してるんです..."
8. Bot: re-display
9. User: hope extinguished → blocks
10. (Emotional impact: extreme)

**System Behavior Evaluation:**
- Distress signals ("限界", "相談") completely unrecognized.
- Same as W4-040: most vulnerable users get worst experience.
- No human handoff triggered.

**Results:** Drop-off: CERTAIN / Job Proposal: None / Next Action: Block / Region Bias: CRITICAL / National Expansion Risk: HIGH
**Failure Category:** Emotional Handling + Regional Gap / **Severity:** P0-Critical / **Fix Proposal:** (1) Distress keyword detection → immediate human handoff, (2) Even "申し訳ございません、現在仙台エリアは準備中です" would be vastly better than silence / **Retry Needed:** Yes / **Auditor Comment:** Combined with W4-040, these distress cases represent the ethical minimum the bot must handle. Two users saying they're at their limit, both ignored. This is a mandatory fix.

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| Total Cases | 50 |
| Standard | 30 |
| Boundary | 12 |
| Adversarial | 8 |
| P0-Critical | 12 |
| P1-High | 28 |
| P2-Medium | 4 |
| Success (N/A) | 6 |
| Expected Drop-off Rate (東海) | ~95% |
| Expected Drop-off Rate (Cross-region covered) | ~10% |

## Top Failure Patterns (Ranked by Impact)

1. **"24,488件" Misleading Count** (W4-033, W4-038, W4-043): Total DB count displayed implies national coverage. Non-Kanto users feel deceived. Fix: Show regional count or add "関東エリア" qualifier.

2. **Free Text Dead End** (W4-002, W4-005, W4-014, W4-024, W4-029): Users type prefecture/city names, bot ignores completely. Fix: Keyword→postback mapping for major cities/prefectures.

3. **No Escalation at unexpectedTextCount>=3** (W4-005, W4-024, W4-050): Users ask direct questions 3+ times, bot just re-displays buttons. Fix: Threshold-based human handoff or coverage explanation.

4. **Distress Signals Ignored** (W4-040, W4-050): "助けてください" "限界です" get robotic Quick Reply. Fix: Keyword detection → immediate human handoff.

5. **Nurture Waste** (W4-009, W4-036): Nurture messages sent to users outside coverage area. Fix: Tag requested_region, exclude from nurture if uncovered.

6. **Ad Spend Leak** (W4-004, W4-031, W4-038, W4-047): Meta/IG/TikTok ads reaching non-Kanto users with zero conversion potential. Fix: Geo-targeting exclusion for uncovered regions.

7. **愛知(名古屋) Zero Coverage** (W4-001 through W4-010): Japan's 4th largest prefecture, 7.5M metro population, zero facilities in DB. This is the single biggest expansion priority after current 4 prefectures.

## Recommended Priority Fixes

| Priority | Fix | Effort | Impact |
|----------|-----|--------|--------|
| 1 | Display "関東エリア: XX件" instead of total at il_area | Low | HIGH — stops misleading all non-Kanto users |
| 2 | Add coverage disclaimer at "その他の地域" selection | Low | HIGH — honest expectation setting |
| 3 | Distress keyword detection → human handoff | Medium | CRITICAL — ethical minimum |
| 4 | unexpectedTextCount>=3 → explain coverage or handoff | Medium | HIGH — reduces dead-end frustration |
| 5 | Meta/IG ad geo-exclusion for non-Kanto | Low | MEDIUM — stops ad waste |
| 6 | Prefecture keyword mapping in TEXT_TO_POSTBACK | Medium | HIGH — handles "名古屋" "大阪" etc. |
| 7 | Log requested_region for uncovered users | Low | MEDIUM — demand data for expansion |
| 8 | Add 愛知(名古屋) to D1 DB | High | VERY HIGH — unlocks 4th largest market |
