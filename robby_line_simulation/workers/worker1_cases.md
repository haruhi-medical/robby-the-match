# Worker 1: LINE Bot Simulation — 北海道・東北 Region
**Generated:** 2026-04-06
**Worker:** 1 of 5
**Region:** 北海道・東北 (primary) + cross-region
**Total Cases:** 50

---

## Cases W1-001 ~ W1-006: 北海道

### Case W1-001
- **Prefecture:** 北海道
- **Region Block:** 北海道
- **Case Type:** standard
- **User Profile:** 32歳、札幌市の急性期病院で内科勤務、日勤希望
- **Entry Route:** LINE友だち追加（Instagram広告経由）
- **Difficulty:** 低

**Scenario:** 札幌在住の看護師が日勤の急性期病院を探して友だち追加。素直にフローに従う。

**Conversation Flow:**
1. [Bot] Welcome: "24,488件の医療機関の中からあなたにぴったりの職場を見つけます！"
2. [Bot] il_area: エリア選択表示（東京都/神奈川県/千葉県/埼玉県/その他の地域）
3. [User] 「その他の地域」をタップ
4. [Bot] "その他の地域ですね！候補: 24,488件" → il_facility_type表示
5. [User] 「急性期病院」をタップ
6. [Bot] il_department表示
7. [User] 「内科系」をタップ
8. [Bot] il_workstyle表示
9. [User] 「日勤のみ」をタップ
10. [Bot] il_urgency表示
11. [User] 「良い所あれば」をタップ
12. [Bot] matching_preview: 関東の施設5件をカード表示（横浜・川崎・東京等）

**System Behavior Evaluation:**
- 「その他の地域」選択後に北海道の求人がないことが一切説明されない
- 24,488件と表示されるが全て関東の施設
- マッチング結果に札幌の施設は1件も含まれない
- ユーザーが結果を見て「なぜ関東？」と混乱する可能性が極めて高い

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: yes — マッチング結果が全て関東圏（横浜・川崎・23区等）
- National Expansion Risk: ユーザーが「北海道の求人がない」と気づき、サービスへの信頼を失う

**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** il_area選択時に「現在は関東エリア（東京・神奈川・千葉・埼玉）の求人のみ対応中」と明示。その他地域選択時に「お住まいのエリアは準備中です。関東の求人をお探しですか？」と確認ステップを追加。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-002
- **Prefecture:** 北海道
- **Region Block:** 北海道
- **Case Type:** adversarial
- **User Profile:** 26歳、旭川の回復期病院でリハビリ勤務、夜勤あり
- **Entry Route:** LINE友だち追加（TikTok経由）
- **Difficulty:** 高

**Scenario:** 旭川の看護師がエリア選択画面で「北海道」と自由テキスト入力する。

**Conversation Flow:**
1. [Bot] Welcome: "24,488件の医療機関の中からあなたにぴったりの職場を見つけます！"
2. [Bot] il_area: エリア選択表示
3. [User] 「北海道」とテキスト入力
4. [Bot] "もう一度お選びください👇" + il_area再表示
5. [User] 「旭川市で探したいんですけど」とテキスト入力
6. [Bot] "もう一度お選びください👇" + il_area再表示
7. [User] 離脱

**System Behavior Evaluation:**
- 自由テキスト入力を一切パースしない
- 「北海道」という明確な地域名を無視してボタン再表示するのみ
- ユーザーの意図（北海道で探したい）を汲み取る機能がない
- 2回拒否されたユーザーは高確率で離脱

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: no
- Reached Next Action: no
- Region Bias Signs: yes — 北海道がそもそも選択肢にない
- National Expansion Risk: 自由テキストで地域名を入力するユーザーへの対応が皆無

**Failure Category:** INPUT_LOCK
**Severity:** Critical
**Fix Proposal:** 自由テキスト入力時にNLPで地域名を抽出し、対応エリア外なら「現在北海道は準備中です。関東エリアへの転職にご興味はありますか？」と案内。または「直接相談する」への導線を提示。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-003
- **Prefecture:** 北海道
- **Region Block:** 北海道
- **Case Type:** boundary
- **User Profile:** 40歳、函館の訪問看護師、パート希望、東京への転居も検討中
- **Entry Route:** LINE友だち追加（ブログ記事経由）
- **Difficulty:** 中

**Scenario:** 函館在住だが東京への引っ越しも視野に入れている看護師。「東京都」を選択してフローを進める。

**Conversation Flow:**
1. [Bot] Welcome: "24,488件の医療機関の中からあなたにぴったりの職場を見つけます！"
2. [Bot] il_area: エリア選択表示
3. [User] 「東京都」をタップ
4. [Bot] il_subarea: 東京のサブエリア表示（23区/多摩 等）
5. [User] 「23区」をタップ
6. [Bot] il_facility_type表示
7. [User] 「訪問看護」をタップ
8. [Bot] il_workstyle表示（訪問看護なので科目スキップ）
9. [User] 「パート・非常勤」をタップ
10. [Bot] il_urgency表示
11. [User] 「良い所あれば」をタップ
12. [Bot] matching_preview: 23区の訪問看護5件表示

**System Behavior Evaluation:**
- 関東への転居意向があるユーザーにとってはフローが正常に機能
- 「現住所と希望勤務地が異なる」ケースへの配慮はないが、致命的ではない
- 結果は東京の施設なので期待通り

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: no — ユーザーが意図的に東京を選択
- National Expansion Risk: 転居前提の人は救えるが、地元で探したい人は救えない

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** 「現在お住まいのエリア」と「希望勤務地」を分けて聞く設問があるとより親切。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-004
- **Prefecture:** 北海道
- **Region Block:** 北海道
- **Case Type:** standard
- **User Profile:** 29歳、帯広の慢性期病院で精神科勤務、すぐ転職したい
- **Entry Route:** LINE友だち追加（Google検索経由）
- **Difficulty:** 低

**Scenario:** 帯広の看護師がすぐ転職したくて登録。「その他の地域」を選択してフローを完走するが、結果に困惑。

**Conversation Flow:**
1. [Bot] Welcome: "24,488件の医療機関の中からあなたにぴったりの職場を見つけます！"
2. [Bot] il_area: エリア選択表示
3. [User] 「その他の地域」をタップ
4. [Bot] "その他の地域ですね！候補: 24,488件" → il_facility_type表示
5. [User] 「慢性期病院」をタップ
6. [Bot] il_department表示
7. [User] 「精神科」をタップ
8. [Bot] il_workstyle表示
9. [User] 「夜勤ありOK」をタップ
10. [Bot] il_urgency表示
11. [User] 「すぐ転職したい」をタップ
12. [Bot] matching_preview: 関東の慢性期精神科病院5件表示
13. [User] 「これ全部関東じゃないですか？帯広の求人はないんですか？」とテキスト入力
14. [Bot] ポストマッチングメニュー表示（テキスト入力は無視される可能性）

**System Behavior Evaluation:**
- フロー自体は完走するが結果が全て関東
- 「すぐ転職したい」という緊急度の高いユーザーの期待を裏切る
- マッチング後のテキスト質問への応答がAIチャット経由で行われるかはフェーズ次第

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: yes — 帯広の求人ゼロ、関東のみ表示
- National Expansion Risk: 緊急度の高いユーザーほど裏切られた感が強い

**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** マッチング結果表示時に「現在は関東エリアの求人のみご案内可能です」と明記。その他地域ユーザーには事前に告知。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-005
- **Prefecture:** 北海道
- **Region Block:** 北海道
- **Case Type:** adversarial
- **User Profile:** 35歳、釧路の介護施設勤務、転職意欲低
- **Entry Route:** LINE友だち追加（友人紹介）
- **Difficulty:** 高

**Scenario:** 釧路の看護師がエリア選択で「その他の地域」を選択後、施設タイプ選択で「釧路の介護施設」とテキスト入力。

**Conversation Flow:**
1. [Bot] Welcome: "24,488件の医療機関の中からあなたにぴったりの職場を見つけます！"
2. [Bot] il_area: エリア選択表示
3. [User] 「その他の地域」をタップ
4. [Bot] "その他の地域ですね！候補: 24,488件" → il_facility_type表示
5. [User] 「釧路の介護施設を探しています」とテキスト入力
6. [Bot] "もう一度お選びください👇" + il_facility_type再表示
7. [User] 「介護施設」をタップ
8. [Bot] il_workstyle表示（介護施設なので科目スキップ）
9. [User] 「パート・非常勤」をタップ
10. [Bot] il_urgency表示
11. [User] 「まだ情報収集」をタップ
12. [Bot] matching_preview: 関東の介護施設5件表示
13. [User] 離脱

**System Behavior Evaluation:**
- テキスト入力で「釧路」と明記しても無視される
- ボタンを押し直させるUXがフラストレーションを生む
- 結果が全て関東で、情報収集段階のユーザーは即離脱

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes
- Reached Next Action: no
- Region Bias Signs: yes — 釧路の施設ゼロ
- National Expansion Risk: テキスト入力のコンテキストが完全に捨てられる

**Failure Category:** INPUT_LOCK
**Severity:** High
**Fix Proposal:** テキスト入力時に地域名キーワードを検出し、対応外エリアなら「釧路エリアは現在準備中です」と明示的に回答。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-006
- **Prefecture:** 北海道
- **Region Block:** 北海道
- **Case Type:** boundary
- **User Profile:** 24歳、新卒で札幌配属、神奈川の実家近くに戻りたい
- **Entry Route:** LINE友だち追加（SEO記事「神奈川 看護師 転職」経由）
- **Difficulty:** 低

**Scenario:** 現在札幌だが神奈川に戻りたい。「神奈川県」を選択して正常フロー。

**Conversation Flow:**
1. [Bot] Welcome: "24,488件の医療機関の中からあなたにぴったりの職場を見つけます！"
2. [Bot] il_area: エリア選択表示
3. [User] 「神奈川県」をタップ
4. [Bot] il_subarea: 神奈川のサブエリア表示（横浜/川崎/相模原/横須賀三浦/県央/湘南/県西）
5. [User] 「横浜」をタップ
6. [Bot] il_facility_type表示
7. [User] 「急性期病院」をタップ
8. [Bot] il_department表示
9. [User] 「こだわりなし」をタップ
10. [Bot] il_workstyle表示
11. [User] 「日勤のみ」をタップ
12. [Bot] il_urgency表示
13. [User] 「すぐ転職したい」をタップ
14. [Bot] matching_preview: 横浜の急性期病院5件表示
15. [User] 「この施設について聞く」をタップ

**System Behavior Evaluation:**
- 希望勤務地が関東圏なのでフロー正常
- 現住所が北海道でも問題なく利用可能
- マッチング結果も適切

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: no — ユーザーが神奈川を選択
- National Expansion Risk: Uターン希望者は正常に利用可能

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** なし（正常動作）
**Retry Needed:** no
**Auditor Comment:**

---

## Cases W1-007 ~ W1-011: 青森

### Case W1-007
- **Prefecture:** 青森県
- **Region Block:** 東北
- **Case Type:** standard
- **User Profile:** 31歳、青森市の急性期病院で外科勤務、夜勤あり
- **Entry Route:** LINE友だち追加（Instagram広告経由）
- **Difficulty:** 低

**Scenario:** 青森市の看護師が転職を検討。素直にフローに従い「その他の地域」を選択。

**Conversation Flow:**
1. [Bot] Welcome: "24,488件の医療機関の中からあなたにぴったりの職場を見つけます！"
2. [Bot] il_area: エリア選択表示
3. [User] 「その他の地域」をタップ
4. [Bot] "その他の地域ですね！候補: 24,488件" → il_facility_type表示
5. [User] 「急性期病院」をタップ
6. [Bot] il_department表示
7. [User] 「外科系」をタップ
8. [Bot] il_workstyle表示
9. [User] 「夜勤ありOK」をタップ
10. [Bot] il_urgency表示
11. [User] 「良い所あれば」をタップ
12. [Bot] matching_preview: 関東の急性期外科病院5件表示

**System Behavior Evaluation:**
- 全て関東の施設が表示され、青森の求人はゼロ
- 「24,488件」という数字が期待を持たせるが実態は関東のみ

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: yes — 青森の求人ゼロ、全て関東
- National Expansion Risk: 東北ユーザーが全員同じ問題に直面

**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** 「その他の地域」選択後に「現在の対応エリア：東京・神奈川・千葉・埼玉」と明示。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-008
- **Prefecture:** 青森県
- **Region Block:** 東北
- **Case Type:** adversarial
- **User Profile:** 28歳、八戸のクリニック勤務、パート希望
- **Entry Route:** LINE友だち追加（TikTok経由）
- **Difficulty:** 高

**Scenario:** 八戸の看護師がエリア選択画面を見て「青森県がないんですけど」とテキスト入力。

**Conversation Flow:**
1. [Bot] Welcome: "24,488件の医療機関の中からあなたにぴったりの職場を見つけます！"
2. [Bot] il_area: エリア選択表示
3. [User] 「青森県がないんですけど」とテキスト入力
4. [Bot] "もう一度お選びください👇" + il_area再表示
5. [User] 「青森」とテキスト入力
6. [Bot] "もう一度お選びください👇" + il_area再表示
7. [User] 「対応してないってこと？」とテキスト入力
8. [Bot] "もう一度お選びください👇" + il_area再表示
9. [User] 離脱（ブロック）

**System Behavior Evaluation:**
- 3回連続で同じ再プロンプトを返す機械的な応答
- ユーザーの質問（「対応してないってこと？」）に一切答えない
- LINEブロックにつながる最悪のUX

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: no
- Reached Next Action: no
- Region Bias Signs: yes — 青森が選択肢に存在しない
- National Expansion Risk: テキスト質問への応答不能がブランド毀損

**Failure Category:** INPUT_LOCK
**Severity:** Critical
**Fix Proposal:** intakeフェーズでもテキスト入力をAIで処理し、「現在は関東4県のみ対応しています。エリア拡大時にお知らせしましょうか？」と回答。LINE通知許可でリード保持。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-009
- **Prefecture:** 青森県
- **Region Block:** 東北
- **Case Type:** standard
- **User Profile:** 45歳、弘前の回復期病院で師長、日勤希望
- **Entry Route:** LINE友だち追加（Google検索経由）
- **Difficulty:** 低

**Scenario:** ベテラン看護師が情報収集目的で登録。「その他の地域」から完走。

**Conversation Flow:**
1. [Bot] Welcome: "24,488件の医療機関の中からあなたにぴったりの職場を見つけます！"
2. [Bot] il_area: エリア選択表示
3. [User] 「その他の地域」をタップ
4. [Bot] "その他の地域ですね！候補: 24,488件" → il_facility_type表示
5. [User] 「回復期病院」をタップ
6. [Bot] il_department表示
7. [User] 「リハビリ」をタップ
8. [Bot] il_workstyle表示
9. [User] 「日勤のみ」をタップ
10. [Bot] il_urgency表示
11. [User] 「まだ情報収集」をタップ
12. [Bot] matching_preview: 関東の回復期リハビリ病院5件表示
13. [User] 「条件を変えて探す」をタップ（地元の求人が出ることを期待）
14. [Bot] il_area再表示 → 同じ選択肢のループ

**System Behavior Evaluation:**
- 「条件を変えて探す」でもエリア選択が同じなので結果は変わらない
- ベテラン看護師は「このサービスは使えない」と判断して終了

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: yes — 弘前の求人ゼロ
- National Expansion Risk: リトライしても同じ結果でユーザー体験が悪化

**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** 「条件を変えて探す」選択時に「現在対応外のエリアの方は直接ご相談ください」と案内を追加。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-010
- **Prefecture:** 青森県
- **Region Block:** 東北
- **Case Type:** boundary
- **User Profile:** 33歳、むつ市の訪問看護師、東京で働くことも検討中
- **Entry Route:** LINE友だち追加（知人紹介）
- **Difficulty:** 中

**Scenario:** 地元と東京の両方で検討中。まず東京で検索、次に地元で検索しようとする。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「東京都」をタップ
3. [Bot] il_subarea表示
4. [User] 「23区」をタップ
5. [Bot] il_facility_type表示
6. [User] 「訪問看護」をタップ
7. [Bot] il_workstyle表示
8. [User] 「日勤のみ」をタップ
9. [Bot] il_urgency表示
10. [User] 「良い所あれば」をタップ
11. [Bot] matching_preview: 23区の訪問看護5件表示
12. [User] 「条件を変えて探す」をタップ
13. [Bot] il_area再表示
14. [User] 「その他の地域」をタップ（青森で探したい）
15. [Bot] 関東の施設が表示される → ユーザー困惑

**System Behavior Evaluation:**
- 1回目（東京）は正常
- 2回目で「青森」を探そうとしても「その他の地域」=関東全域なので同じ関東が出る
- 2エリアを比較検討したいユーザーのニーズに応えられない

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: yes — 2回目の「その他の地域」で関東が出る
- National Expansion Risk: 複数エリア比較ができない構造的問題

**Failure Category:** GEO_LOCK
**Severity:** High
**Fix Proposal:** 「その他の地域」選択時に都道府県プルダウンを表示。対応外なら明示。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-011
- **Prefecture:** 青森県
- **Region Block:** 東北
- **Case Type:** adversarial
- **User Profile:** 22歳、新卒看護師、スマホ操作に慣れている
- **Entry Route:** LINE友だち追加（TikTok経由）
- **Difficulty:** 高

**Scenario:** 新卒看護師がエリア選択で「🍎青森」と絵文字入りテキストを送信。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「🍎青森」とテキスト入力
3. [Bot] "もう一度お選びください👇" + il_area再表示
4. [User] 「なんで青森ないの？w」とテキスト入力
5. [Bot] "もう一度お選びください👇" + il_area再表示
6. [User] LINEで友人に「このサービス使えないわ」と共有
7. [User] 離脱

**System Behavior Evaluation:**
- 絵文字入りテキストも通常テキストも同様に拒否
- 若年層のカジュアルなコミュニケーションに対応できない
- 口コミで悪評が広がるリスク

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: no
- Reached Next Action: no
- Region Bias Signs: yes — 青森が選択肢にない
- National Expansion Risk: 若年層SNSでの負の口コミリスク

**Failure Category:** INPUT_LOCK
**Severity:** High
**Fix Proposal:** テキスト入力のNLP処理を実装。絵文字除去後に地域名を抽出。
**Retry Needed:** no
**Auditor Comment:**

---

## Cases W1-012 ~ W1-016: 岩手

### Case W1-012
- **Prefecture:** 岩手県
- **Region Block:** 東北
- **Case Type:** standard
- **User Profile:** 30歳、盛岡の急性期病院で循環器勤務
- **Entry Route:** LINE友だち追加（Instagram経由）
- **Difficulty:** 低

**Scenario:** 盛岡の看護師が転職を検討。「その他の地域」を選択してフロー完走。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「その他の地域」をタップ
3. [Bot] "その他の地域ですね！候補: 24,488件" → il_facility_type表示
4. [User] 「急性期病院」をタップ
5. [Bot] il_department表示
6. [User] 「循環器」をタップ
7. [Bot] il_workstyle表示
8. [User] 「夜勤ありOK」をタップ
9. [Bot] il_urgency表示
10. [User] 「すぐ転職したい」をタップ
11. [Bot] matching_preview: 関東の循環器病院5件表示

**System Behavior Evaluation:**
- 盛岡の循環器病院は1件も表示されない
- 「すぐ転職したい」緊急ユーザーにとって致命的

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: yes — 盛岡の求人ゼロ
- National Expansion Risk: 緊急転職者の期待を完全に裏切る

**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** 対応外エリアの緊急転職者には「直接相談する」への即時導線を設置。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-013
- **Prefecture:** 岩手県
- **Region Block:** 東北
- **Case Type:** boundary
- **User Profile:** 38歳、釜石の慢性期病院勤務、埼玉に親族あり
- **Entry Route:** LINE友だち追加（ブログ経由）
- **Difficulty:** 中

**Scenario:** 親族のいる埼玉への転職も検討中。「埼玉県」を選択。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「埼玉県」をタップ
3. [Bot] il_subarea表示（さいたま/川口・戸田/川越/所沢 等）
4. [User] 「さいたま」をタップ
5. [Bot] il_facility_type表示
6. [User] 「慢性期病院」をタップ
7. [Bot] il_department表示
8. [User] 「内科系」をタップ
9. [Bot] il_workstyle表示
10. [User] 「日勤のみ」をタップ
11. [Bot] il_urgency表示
12. [User] 「良い所あれば」をタップ
13. [Bot] matching_preview: さいたまの慢性期内科病院5件表示
14. [User] 「この施設について聞く」をタップ

**System Behavior Evaluation:**
- 埼玉を選択したので正常にマッチング
- 岩手在住でも関東への転居意向があれば問題なく利用可能

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: no — ユーザーが意図的に埼玉を選択
- National Expansion Risk: 転居前提なら機能するが、地元での利用は不可

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** なし
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-014
- **Prefecture:** 岩手県
- **Region Block:** 東北
- **Case Type:** adversarial
- **User Profile:** 27歳、一関のクリニック勤務
- **Entry Route:** LINE友だち追加（友人紹介）
- **Difficulty:** 高

**Scenario:** エリア選択を無視して「岩手県一関市のクリニックで時給2000円以上のパートを探しています」と詳細なテキストを送信。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「岩手県一関市のクリニックで時給2000円以上のパートを探しています」とテキスト入力
3. [Bot] "もう一度お選びください👇" + il_area再表示
4. [User] 「ボタンじゃなくてテキストで答えたいんですけど」とテキスト入力
5. [Bot] "もう一度お選びください👇" + il_area再表示
6. [User] 離脱

**System Behavior Evaluation:**
- 非常に具体的な検索条件（地域・施設タイプ・時給・雇用形態）が全て無視される
- ユーザーが努力して詳細を入力しても一切活用されない

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: no
- Reached Next Action: no
- Region Bias Signs: yes — 岩手県が選択不可
- National Expansion Risk: 詳細な検索意図を持つユーザーのデータが完全にロスト

**Failure Category:** INPUT_LOCK
**Severity:** Critical
**Fix Proposal:** テキスト入力から条件を抽出してフロー変数にプリセット。対応外エリアなら「ご希望の条件を承りました。現在岩手県は準備中ですが、スタッフが個別にお探しします」→ 人間引き継ぎ。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-015
- **Prefecture:** 岩手県
- **Region Block:** 東北
- **Case Type:** standard
- **User Profile:** 34歳、花巻の介護施設勤務、夜勤専従
- **Entry Route:** LINE友だち追加（Instagram広告経由）
- **Difficulty:** 低

**Scenario:** 介護施設の夜勤専従看護師が転職を検討。「その他の地域」で完走。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「その他の地域」をタップ
3. [Bot] "その他の地域ですね！候補: 24,488件" → il_facility_type表示
4. [User] 「介護施設」をタップ
5. [Bot] il_workstyle表示（介護施設なので科目スキップ）
6. [User] 「夜勤専従」をタップ
7. [Bot] il_urgency表示
8. [User] 「良い所あれば」をタップ
9. [Bot] matching_preview: 関東の介護施設5件表示
10. [User] 「直接相談する」をタップ
11. [Bot] 電話番号確認 → handoff処理

**System Behavior Evaluation:**
- 結果は関東だが「直接相談する」を選択してhandoffに到達
- handoff後に人間スタッフが「岩手は対応外」と伝えることになる
- 人間スタッフの負荷増加

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: yes — 花巻の求人ゼロ
- National Expansion Risk: handoff先の人間スタッフが対応外を説明する必要

**Failure Category:** HUMAN_HANDOFF_FAIL
**Severity:** High
**Fix Proposal:** handoff前に「現在対応エリア：関東4県。岩手県は準備中です。それでもスタッフに相談しますか？」と確認。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-016
- **Prefecture:** 岩手県
- **Region Block:** 東北
- **Case Type:** boundary
- **User Profile:** 25歳、盛岡出身で現在千葉在住、地元に戻るか迷い中
- **Entry Route:** LINE友だち追加（SEO記事経由）
- **Difficulty:** 中

**Scenario:** 千葉在住で千葉の求人を見つつ、地元岩手も検討したい。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「千葉県」をタップ
3. [Bot] il_subarea表示
4. [User] 「千葉市」をタップ
5. [Bot] il_facility_type表示
6. [User] 「クリニック」をタップ
7. [Bot] il_workstyle表示（クリニックなので勤務形態スキップ? → コードではクリニックはworkstyleスキップ）
8. [Bot] il_urgency表示
9. [User] 「まだ情報収集」をタップ
10. [Bot] matching_preview: 千葉のクリニック5件表示
11. [User] 「条件を変えて探す」→ 「その他の地域」選択 → 関東が出る
12. [User] 「盛岡の求人も見たかったのに…」と思い離脱

**System Behavior Evaluation:**
- 千葉の検索は正常
- 地元（岩手）の検索はGEO_LOCKで不可

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: yes — 2回目の検索で岩手が出ない
- National Expansion Risk: Uターン検討者の比較ニーズに非対応

**Failure Category:** GEO_LOCK
**Severity:** High
**Fix Proposal:** 「その他の地域」選択時に都道府県入力欄を設け、未対応なら明示。
**Retry Needed:** no
**Auditor Comment:**

---

## Cases W1-017 ~ W1-022: 宮城

### Case W1-017
- **Prefecture:** 宮城県
- **Region Block:** 東北
- **Case Type:** standard
- **User Profile:** 29歳、仙台の急性期病院で救急勤務
- **Entry Route:** LINE友だち追加（Google検索「仙台 看護師 転職」経由）
- **Difficulty:** 低

**Scenario:** 仙台の救急看護師が転職サイトを探してLINE登録。「その他の地域」で完走。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「その他の地域」をタップ
3. [Bot] "その他の地域ですね！候補: 24,488件" → il_facility_type表示
4. [User] 「急性期病院」をタップ
5. [Bot] il_department表示
6. [User] 「救急」をタップ
7. [Bot] il_workstyle表示
8. [User] 「夜勤ありOK」をタップ
9. [Bot] il_urgency表示
10. [User] 「すぐ転職したい」をタップ
11. [Bot] matching_preview: 関東の救急病院5件表示

**System Behavior Evaluation:**
- 仙台は東北最大の都市だが求人ゼロ
- 「仙台 看護師 転職」で検索して来たユーザーの期待と結果が完全に乖離

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: yes — 仙台の求人ゼロ
- National Expansion Risk: SEO流入のユーザーが地元求人を期待して裏切られる

**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** 「仙台 看護師 転職」等のSEO記事がある場合、LP上で「現在関東エリアのみ対応」と明記してからLINE誘導。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-018
- **Prefecture:** 宮城県
- **Region Block:** 東北
- **Case Type:** adversarial
- **User Profile:** 36歳、石巻の訪問看護師
- **Entry Route:** LINE友だち追加（友人紹介）
- **Difficulty:** 高

**Scenario:** 石巻の看護師がWelcomeメッセージの前に「仙台か石巻で訪問看護の求人ありますか？」と先にテキスト送信。

**Conversation Flow:**
1. [User] 「仙台か石巻で訪問看護の求人ありますか？」とテキスト入力（友だち追加直後）
2. [Bot] Welcome: "24,488件の医療機関の中からあなたにぴったりの職場を見つけます！" + il_area表示
3. [User] テキストが無視されたことに気づく
4. [User] 「その他の地域」をタップ（仕方なく）
5. [Bot] "その他の地域ですね！候補: 24,488件" → il_facility_type表示
6. [User] 「訪問看護」をタップ
7. [Bot] il_workstyle表示
8. [User] 「日勤のみ」をタップ
9. [Bot] il_urgency表示
10. [User] 「良い所あれば」をタップ
11. [Bot] matching_preview: 関東の訪問看護5件表示
12. [User] 「さっき聞いたんですけど、宮城の求人はないんですか？」とテキスト入力
13. [Bot] ポストマッチングメニュー表示 or AIチャット応答

**System Behavior Evaluation:**
- 最初のテキストがWelcomeフローに上書きされて無視
- マッチング後のテキスト質問はAIチャットが応答する可能性あるが、求人データベース自体に宮城がないので有益な回答不可

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: yes — 宮城の求人データなし
- National Expansion Risk: 初回テキストの意図が完全にロスト

**Failure Category:** INPUT_LOCK
**Severity:** High
**Fix Proposal:** 友だち追加時の初回テキストをコンテキストとして保存し、intakeフローに反映。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-019
- **Prefecture:** 宮城県
- **Region Block:** 東北
- **Case Type:** standard
- **User Profile:** 42歳、仙台の回復期病院でリハビリ科師長
- **Entry Route:** LINE友だち追加（Google検索経由）
- **Difficulty:** 低

**Scenario:** 管理職経験者が新天地を探す。「その他の地域」で完走し「直接相談する」を選択。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「その他の地域」をタップ
3. [Bot] "その他の地域ですね！候補: 24,488件" → il_facility_type表示
4. [User] 「回復期病院」をタップ
5. [Bot] il_department表示
6. [User] 「リハビリ」をタップ
7. [Bot] il_workstyle表示
8. [User] 「日勤のみ」をタップ
9. [Bot] il_urgency表示
10. [User] 「良い所あれば」をタップ
11. [Bot] matching_preview: 関東の回復期リハビリ病院5件表示
12. [User] 「直接相談する」をタップ
13. [Bot] 電話番号確認フロー
14. [User] 電話番号入力
15. [Bot] handoff完了、Slack転送

**System Behavior Evaluation:**
- handoffまで到達するが、人間スタッフが宮城の求人を紹介できるかは別問題
- 管理職の転職相談は高価値だが地域制限で逃す可能性

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: yes — 表示は関東のみ
- National Expansion Risk: 高価値リードを地域制限で失うリスク

**Failure Category:** GEO_LOCK
**Severity:** High
**Fix Proposal:** 対応外エリアのhandoffリードは「エリア拡大候補リスト」として管理。需要データとして活用。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-020
- **Prefecture:** 宮城県
- **Region Block:** 東北
- **Case Type:** boundary
- **User Profile:** 26歳、気仙沼の急性期病院勤務、東京に興味あり
- **Entry Route:** LINE友だち追加（Instagram経由）
- **Difficulty:** 中

**Scenario:** 気仙沼から東京への転職に興味。「東京都」を選択し正常フロー。途中で「やっぱり地元がいい」と思い直す。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「東京都」をタップ
3. [Bot] il_subarea表示
4. [User] 「23区」をタップ
5. [Bot] il_facility_type表示
6. [User] 「急性期病院」をタップ
7. [Bot] il_department表示
8. [User] 「こだわりなし」をタップ
9. [Bot] il_workstyle表示
10. [User] 「夜勤ありOK」をタップ
11. [Bot] il_urgency表示
12. [User] 「まだ情報収集」をタップ
13. [Bot] matching_preview: 23区の急性期病院5件表示
14. [User] 「条件を変えて探す」をタップ
15. [Bot] il_area再表示
16. [User] 「その他の地域」をタップ → 関東が出る → 宮城は無い → 諦め

**System Behavior Evaluation:**
- 東京の検索は正常だが、地元に戻りたくなった時に選択肢がない
- 心変わりに対応できないフロー設計

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: yes — 宮城の選択肢なし
- National Expansion Risk: 「やっぱり地元」という心変わりをフォローできない

**Failure Category:** GEO_LOCK
**Severity:** Medium
**Fix Proposal:** 「条件を変えて探す」時に自由テキストでエリア入力可能にする。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-021
- **Prefecture:** 宮城県
- **Region Block:** 東北
- **Case Type:** standard
- **User Profile:** 31歳、名取市のクリニック勤務、パート希望
- **Entry Route:** LINE友だち追加（TikTok経由）
- **Difficulty:** 低

**Scenario:** クリニック勤務のパート看護師が「その他の地域」で完走。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「その他の地域」をタップ
3. [Bot] "その他の地域ですね！候補: 24,488件" → il_facility_type表示
4. [User] 「クリニック」をタップ
5. [Bot] il_urgency表示（クリニックはworkstyleスキップ）
6. [User] 「良い所あれば」をタップ
7. [Bot] matching_preview: 関東のクリニック5件表示
8. [User] 「まだ早いかも」をタップ
9. [Bot] 終了メッセージ

**System Behavior Evaluation:**
- クリニックの場合workstyleがスキップされるフロー短縮は機能
- しかし結果が関東なので「まだ早いかも」で離脱

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: yes — 名取市のクリニックゼロ
- National Expansion Risk: 短いフローでも結果が合わなければ離脱

**Failure Category:** GEO_LOCK
**Severity:** High
**Fix Proposal:** 「まだ早いかも」選択者にもエリア拡大通知のオプトインを提示。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-022
- **Prefecture:** 宮城県
- **Region Block:** 東北
- **Case Type:** adversarial
- **User Profile:** 23歳、仙台の大学病院勤務、2年目
- **Entry Route:** LINE友だち追加（TikTok経由）
- **Difficulty:** 高

**Scenario:** 若手看護師がWelcomeメッセージに対して「仙台」とだけ返信し続ける。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「仙台」とテキスト入力
3. [Bot] "もう一度お選びください👇" + il_area再表示
4. [User] 「仙台市」とテキスト入力
5. [Bot] "もう一度お選びください👇" + il_area再表示
6. [User] 「宮城」とテキスト入力
7. [Bot] "もう一度お選びください👇" + il_area再表示
8. [User] 「東北」とテキスト入力
9. [Bot] "もう一度お選びください👇" + il_area再表示
10. [User] 離脱（ブロック）

**System Behavior Evaluation:**
- 4回連続でテキスト入力を拒否
- 地域の粒度を変えても（仙台→仙台市→宮城→東北）全て同じ応答
- ユーザーの忍耐の限界を超える

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: no
- Reached Next Action: no
- Region Bias Signs: yes — 東北エリア全体が選択不可
- National Expansion Risk: テキスト入力の繰り返し拒否がUXの最大の弱点

**Failure Category:** INPUT_LOCK
**Severity:** Critical
**Fix Proposal:** 2回以上テキスト入力された場合はAIチャットモードに切り替え、意図を汲み取る。
**Retry Needed:** no
**Auditor Comment:**

---

## Cases W1-023 ~ W1-027: 秋田

### Case W1-023
- **Prefecture:** 秋田県
- **Region Block:** 東北
- **Case Type:** standard
- **User Profile:** 33歳、秋田市の急性期病院で産婦人科勤務
- **Entry Route:** LINE友だち追加（Instagram広告経由）
- **Difficulty:** 低

**Scenario:** 産婦人科の看護師が「その他の地域」で完走。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「その他の地域」をタップ
3. [Bot] "その他の地域ですね！候補: 24,488件" → il_facility_type表示
4. [User] 「急性期病院」をタップ
5. [Bot] il_department表示
6. [User] 「産婦人科」をタップ
7. [Bot] il_workstyle表示
8. [User] 「日勤のみ」をタップ
9. [Bot] il_urgency表示
10. [User] 「良い所あれば」をタップ
11. [Bot] matching_preview: 関東の産婦人科病院5件表示

**System Behavior Evaluation:**
- 秋田の産婦人科求人ゼロ
- 専門性の高い検索条件でもエリアが関東に固定

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: yes — 秋田の求人ゼロ
- National Expansion Risk: 専門科の検索でもGEO_LOCK

**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** 対応エリア外ユーザーには「ご希望の条件をメモしました。エリア拡大時に優先通知」機能。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-024
- **Prefecture:** 秋田県
- **Region Block:** 東北
- **Case Type:** adversarial
- **User Profile:** 44歳、横手の慢性期病院勤務、IT苦手
- **Entry Route:** LINE友だち追加（知人紹介）
- **Difficulty:** 高

**Scenario:** IT苦手な看護師がボタンの意味がわからず「秋田県横手市」とテキスト入力。その後も質問テキストを送り続ける。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「秋田県横手市」とテキスト入力
3. [Bot] "もう一度お選びください👇" + il_area再表示
4. [User] 「ボタンの押し方がわかりません」とテキスト入力
5. [Bot] "もう一度お選びください👇" + il_area再表示
6. [User] 「助けてください」とテキスト入力
7. [Bot] "もう一度お選びください👇" + il_area再表示
8. [User] 知人に電話して聞く → 諦めて離脱

**System Behavior Evaluation:**
- IT苦手なユーザーへのサポートがゼロ
- 「助けてください」というSOSにも定型文で応答
- 年配層のデジタルディバイド問題に非対応

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: no
- Reached Next Action: no
- Region Bias Signs: yes — 秋田が選択肢にない
- National Expansion Risk: デジタルリテラシーの低いユーザー全体が離脱するリスク

**Failure Category:** INPUT_LOCK
**Severity:** Critical
**Fix Proposal:** 「助けて」「わからない」等のヘルプワードを検知したら、操作ガイドを送信 or 人間スタッフに即時転送。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-025
- **Prefecture:** 秋田県
- **Region Block:** 東北
- **Case Type:** standard
- **User Profile:** 27歳、大仙市の介護施設勤務
- **Entry Route:** LINE友だち追加（Instagram経由）
- **Difficulty:** 低

**Scenario:** 介護施設の看護師が「その他の地域」→「介護施設」で完走。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「その他の地域」をタップ
3. [Bot] "その他の地域ですね！候補: 24,488件" → il_facility_type表示
4. [User] 「介護施設」をタップ
5. [Bot] il_workstyle表示
6. [User] 「日勤のみ」をタップ
7. [Bot] il_urgency表示
8. [User] 「すぐ転職したい」をタップ
9. [Bot] matching_preview: 関東の介護施設5件表示
10. [User] 「もっと求人を見る」をタップ
11. [Bot] 次の5件表示（全て関東）
12. [User] 離脱

**System Behavior Evaluation:**
- 「もっと求人を見る」でも全て関東
- ページネーションしても地元の求人は永遠に出ない

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: yes — 秋田の介護施設ゼロ
- National Expansion Risk: 「もっと見る」の期待を裏切り続ける

**Failure Category:** GEO_LOCK
**Severity:** High
**Fix Proposal:** 「もっと求人を見る」で結果が全て同一エリアの場合「他エリアの求人もご覧になりますか？」と案内。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-026
- **Prefecture:** 秋田県
- **Region Block:** 東北
- **Case Type:** boundary
- **User Profile:** 30歳、秋田市在住、神奈川出身で戻りたい
- **Entry Route:** LINE友だち追加（SEO記事経由）
- **Difficulty:** 中

**Scenario:** 神奈川出身で「神奈川県」を選択。正常にマッチング。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「神奈川県」をタップ
3. [Bot] il_subarea表示
4. [User] 「川崎」をタップ
5. [Bot] il_facility_type表示
6. [User] 「急性期病院」をタップ
7. [Bot] il_department表示
8. [User] 「小児科」をタップ
9. [Bot] il_workstyle表示
10. [User] 「日勤のみ」をタップ
11. [Bot] il_urgency表示
12. [User] 「良い所あれば」をタップ
13. [Bot] matching_preview: 川崎の小児科急性期病院5件表示

**System Behavior Evaluation:**
- 関東への転居希望なので正常動作
- 神奈川出身者の帰省ニーズにはマッチ

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: no — ユーザーが神奈川を選択
- National Expansion Risk: なし（関東帰省ケース）

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** なし
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-027
- **Prefecture:** 秋田県
- **Region Block:** 東北
- **Case Type:** adversarial
- **User Profile:** 50歳、能代の病院勤務、転職は初めて
- **Entry Route:** LINE友だち追加（チラシQR経由）
- **Difficulty:** 高

**Scenario:** 転職初めての看護師が「その他の地域」の意味がわからず、全ボタンを順にタップ → 毎回結果を見て混乱。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「東京都」をタップ（なんとなく）
3. [Bot] il_subarea表示 → ユーザー「秋田は？」と混乱
4. [User] 前の画面に戻りたいがLINEには戻るボタンがない
5. [User] 「戻る」とテキスト入力
6. [Bot] "もう一度お選びください👇"（サブエリア再表示）
7. [User] 離脱

**System Behavior Evaluation:**
- 「戻る」機能がない
- 一度エリアを選択すると前のステップに戻れない
- 誤操作への対応がない

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: no
- Reached Next Action: no
- Region Bias Signs: yes — 秋田が選択肢にない上、戻る手段もない
- National Expansion Risk: フロー途中の「戻る」操作が不可能

**Failure Category:** UX_DROP
**Severity:** High
**Fix Proposal:** 各ステップに「戻る」ボタンを追加。「最初からやり直す」オプションも設置。
**Retry Needed:** no
**Auditor Comment:**

---

## Cases W1-028 ~ W1-032: 山形

### Case W1-028
- **Prefecture:** 山形県
- **Region Block:** 東北
- **Case Type:** standard
- **User Profile:** 28歳、山形市の急性期病院で整形外科勤務
- **Entry Route:** LINE友だち追加（Instagram広告経由）
- **Difficulty:** 低

**Scenario:** 山形の整形外科看護師が「その他の地域」で完走。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「その他の地域」をタップ
3. [Bot] "その他の地域ですね！候補: 24,488件" → il_facility_type表示
4. [User] 「急性期病院」をタップ
5. [Bot] il_department表示
6. [User] 「整形外科」をタップ
7. [Bot] il_workstyle表示
8. [User] 「夜勤ありOK」をタップ
9. [Bot] il_urgency表示
10. [User] 「良い所あれば」をタップ
11. [Bot] matching_preview: 関東の整形外科病院5件表示

**System Behavior Evaluation:**
- 山形の整形外科求人ゼロ
- 標準フローの典型的なGEO_LOCKパターン

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: yes — 山形の求人ゼロ
- National Expansion Risk: 東北全県で同じパターンが反復

**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** 「その他の地域」を廃止し、47都道府県から選択可能にする。対応外は「準備中」表記。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-029
- **Prefecture:** 山形県
- **Region Block:** 東北
- **Case Type:** adversarial
- **User Profile:** 39歳、鶴岡市の回復期病院勤務
- **Entry Route:** LINE友だち追加（知人紹介）
- **Difficulty:** 高

**Scenario:** 看護師がエリア選択で「その他の地域って何？関東以外は対応してないの？」と質問テキストを送信。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「その他の地域って何？関東以外は対応してないの？」とテキスト入力
3. [Bot] "もう一度お選びください👇" + il_area再表示
4. [User] 「質問に答えてよ」とテキスト入力
5. [Bot] "もう一度お選びください👇" + il_area再表示
6. [User] 離脱

**System Behavior Evaluation:**
- サービスの対応範囲に関する正当な質問が無視される
- 「その他の地域」のラベルが曖昧で質問を誘発しているのにそれに答えない

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: no
- Reached Next Action: no
- Region Bias Signs: yes — 質問自体が無視される
- National Expansion Risk: 「その他の地域」のラベルが誤解を招く設計

**Failure Category:** INPUT_LOCK
**Severity:** Critical
**Fix Proposal:** 「その他の地域」のラベルを「関東エリア全域で探す」に変更。テキスト質問にはAIが応答。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-030
- **Prefecture:** 山形県
- **Region Block:** 東北
- **Case Type:** standard
- **User Profile:** 35歳、米沢のクリニック勤務、パート希望
- **Entry Route:** LINE友だち追加（TikTok経由）
- **Difficulty:** 低

**Scenario:** クリニック勤務看護師が「その他の地域」→「クリニック」で完走。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「その他の地域」をタップ
3. [Bot] "その他の地域ですね！候補: 24,488件" → il_facility_type表示
4. [User] 「クリニック」をタップ
5. [Bot] il_urgency表示（クリニックはworkstyleスキップ）
6. [User] 「まだ情報収集」をタップ
7. [Bot] matching_preview: 関東のクリニック5件表示
8. [User] 「まだ早いかも」をタップ

**System Behavior Evaluation:**
- 短いフローで完走するが結果が合わない
- 「まだ早いかも」で完全離脱

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: yes — 米沢のクリニックゼロ
- National Expansion Risk: 情報収集段階のユーザーは結果不一致で即離脱

**Failure Category:** GEO_LOCK
**Severity:** High
**Fix Proposal:** 「まだ早いかも」選択時に「エリア拡大時にお知らせ」のオプション提示。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-031
- **Prefecture:** 山形県
- **Region Block:** 東北
- **Case Type:** boundary
- **User Profile:** 26歳、酒田市在住、東京の大学病院への転職を希望
- **Entry Route:** LINE友だち追加（Google検索「東京 大学病院 看護師」経由）
- **Difficulty:** 中

**Scenario:** 東京の大学病院を志望して「東京都」を選択。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「東京都」をタップ
3. [Bot] il_subarea表示
4. [User] 「23区」をタップ
5. [Bot] il_facility_type表示
6. [User] 「急性期病院」をタップ
7. [Bot] il_department表示
8. [User] 「こだわりなし」をタップ
9. [Bot] il_workstyle表示
10. [User] 「夜勤ありOK」をタップ
11. [Bot] il_urgency表示
12. [User] 「すぐ転職したい」をタップ
13. [Bot] matching_preview: 23区の急性期病院5件表示
14. [User] 「この施設について聞く」をタップ

**System Behavior Evaluation:**
- 東京への転職志望なので正常動作
- 「大学病院」という施設種別はないが「急性期病院」でカバー

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: no — ユーザーが東京を選択
- National Expansion Risk: 関東志望者は正常に利用可能

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** 「大学病院」「公立病院」等の施設種別の細分化があるとよい。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-032
- **Prefecture:** 山形県
- **Region Block:** 東北
- **Case Type:** adversarial
- **User Profile:** 48歳、山形市の訪問看護師、方言で入力
- **Entry Route:** LINE友だち追加（チラシ経由）
- **Difficulty:** 高

**Scenario:** 山形弁で「山形で探してけろ」とテキスト入力。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「山形で探してけろ」とテキスト入力
3. [Bot] "もう一度お選びください👇" + il_area再表示
4. [User] 「なんだず、ボタン押さねばだめだのが」とテキスト入力
5. [Bot] "もう一度お選びください👇" + il_area再表示
6. [User] 「その他の地域」をタップ（仕方なく）
7. [Bot] "その他の地域ですね！候補: 24,488件" → il_facility_type表示
8. [User] 「訪問看護」をタップ
9. [Bot] il_workstyle表示
10. [User] 「日勤のみ」をタップ
11. [Bot] il_urgency表示
12. [User] 「良い所あれば」をタップ
13. [Bot] matching_preview: 関東の訪問看護5件表示
14. [User] 「なんだこれ、関東ばっかりだず」→ 離脱

**System Behavior Evaluation:**
- 方言テキストを処理できない
- ボタン操作に切り替えて完走するが結果に不満
- 方言圏のユーザーへの配慮がない

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes
- Reached Next Action: no
- Region Bias Signs: yes — 山形の求人ゼロ
- National Expansion Risk: 方言テキストのNLP処理が必要

**Failure Category:** INPUT_LOCK
**Severity:** High
**Fix Proposal:** テキスト入力のNLPに方言対応を追加。「探してけろ」→「探してほしい」等の方言変換。
**Retry Needed:** no
**Auditor Comment:**

---

## Cases W1-033 ~ W1-037: 福島

### Case W1-033
- **Prefecture:** 福島県
- **Region Block:** 東北
- **Case Type:** standard
- **User Profile:** 30歳、郡山の急性期病院で内科勤務
- **Entry Route:** LINE友だち追加（Instagram広告経由）
- **Difficulty:** 低

**Scenario:** 郡山の内科看護師が「その他の地域」で完走。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「その他の地域」をタップ
3. [Bot] "その他の地域ですね！候補: 24,488件" → il_facility_type表示
4. [User] 「急性期病院」をタップ
5. [Bot] il_department表示
6. [User] 「内科系」をタップ
7. [Bot] il_workstyle表示
8. [User] 「日勤のみ」をタップ
9. [Bot] il_urgency表示
10. [User] 「すぐ転職したい」をタップ
11. [Bot] matching_preview: 関東の内科病院5件表示

**System Behavior Evaluation:**
- 福島の求人ゼロ
- 郡山は福島第2の都市だが対応外

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: yes — 福島の求人ゼロ
- National Expansion Risk: 標準的なGEO_LOCKパターン

**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** 同上（エリア選択UIの根本改修）
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-034
- **Prefecture:** 福島県
- **Region Block:** 東北
- **Case Type:** boundary
- **User Profile:** 32歳、いわき市在住、埼玉の親戚宅に居候しながら転職活動予定
- **Entry Route:** LINE友だち追加（Google検索経由）
- **Difficulty:** 中

**Scenario:** いわき市から埼玉へ転居予定。「埼玉県」を選択して正常フロー。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「埼玉県」をタップ
3. [Bot] il_subarea表示
4. [User] 「川口・戸田」をタップ
5. [Bot] il_facility_type表示
6. [User] 「急性期病院」をタップ
7. [Bot] il_department表示
8. [User] 「外科系」をタップ
9. [Bot] il_workstyle表示
10. [User] 「夜勤ありOK」をタップ
11. [Bot] il_urgency表示
12. [User] 「すぐ転職したい」をタップ
13. [Bot] matching_preview: 川口・戸田の急性期外科病院5件表示
14. [User] 「この施設について聞く」をタップ

**System Behavior Evaluation:**
- 転居先の関東で検索するので正常
- いわき→埼玉の転居ケースは実際に多いパターン

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: no — ユーザーが埼玉を選択
- National Expansion Risk: なし

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** なし
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-035
- **Prefecture:** 福島県
- **Region Block:** 東北
- **Case Type:** adversarial
- **User Profile:** 37歳、福島市の慢性期病院勤務
- **Entry Route:** LINE友だち追加（友人紹介）
- **Difficulty:** 高

**Scenario:** 看護師が「その他の地域」を選択後、施設タイプ選択でスタンプ（画像）を送信。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「その他の地域」をタップ
3. [Bot] "その他の地域ですね！候補: 24,488件" → il_facility_type表示
4. [User] LINEスタンプ（泣き顔）を送信
5. [Bot] "もう一度お選びください👇" + il_facility_type再表示
6. [User] 「慢性期病院」をタップ
7. [Bot] il_department表示
8. [User] LINEスタンプ（考え中）を送信
9. [Bot] "もう一度お選びください👇" + il_department再表示
10. [User] 「こだわりなし」をタップ
11. [Bot] il_workstyle → il_urgency → matching_preview表示

**System Behavior Evaluation:**
- スタンプ送信は再プロンプトで処理される（致命的ではない）
- ユーザーがスタンプと選択を交互に使うパターンに対応はしている

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: yes — 福島の求人ゼロ
- National Expansion Risk: スタンプ処理は問題ないがGEO_LOCKは残る

**Failure Category:** GEO_LOCK
**Severity:** High
**Fix Proposal:** スタンプ送信時の再プロンプトメッセージを「ボタンからお選びください😊」等、より親切に。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-036
- **Prefecture:** 福島県
- **Region Block:** 東北
- **Case Type:** standard
- **User Profile:** 25歳、会津若松のクリニック勤務
- **Entry Route:** LINE友だち追加（TikTok経由）
- **Difficulty:** 低

**Scenario:** 会津若松のクリニック看護師が「その他の地域」→「クリニック」で完走。結果を見て「直接相談する」。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「その他の地域」をタップ
3. [Bot] "その他の地域ですね！候補: 24,488件" → il_facility_type表示
4. [User] 「クリニック」をタップ
5. [Bot] il_urgency表示
6. [User] 「良い所あれば」をタップ
7. [Bot] matching_preview: 関東のクリニック5件表示
8. [User] 「直接相談する」をタップ
9. [Bot] 電話番号確認フロー
10. [User] 電話番号入力
11. [Bot] handoff完了

**System Behavior Evaluation:**
- handoff到達はするが、人間スタッフが会津若松の求人を持っていない可能性が高い
- 人間コスト発生

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: yes — 会津若松の求人ゼロ
- National Expansion Risk: 対応外エリアからのhandoffが人間スタッフの負荷に

**Failure Category:** HUMAN_HANDOFF_FAIL
**Severity:** High
**Fix Proposal:** handoff前に対応エリアを明示。対応外なら「エリア拡大リクエスト」として記録。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-037
- **Prefecture:** 福島県
- **Region Block:** 東北
- **Case Type:** boundary
- **User Profile:** 41歳、白河市在住（栃木県境）、栃木での勤務も検討
- **Entry Route:** LINE友だち追加（Google検索経由）
- **Difficulty:** 中

**Scenario:** 県境在住で栃木も視野に入れているが、栃木もD1データベースにない。「その他の地域」を選択。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「その他の地域」をタップ（栃木を期待）
3. [Bot] "その他の地域ですね！候補: 24,488件" → il_facility_type表示
4. [User] 「急性期病院」をタップ
5. [Bot] il_department → il_workstyle → il_urgency
6. [User] 各ステップで選択
7. [Bot] matching_preview: 関東の施設5件表示（栃木はなし）
8. [User] 「栃木の求人もないんですか？」とテキスト入力
9. [Bot] ポストマッチングメニュー表示

**System Behavior Evaluation:**
- 栃木県もD1データベースにないため表示されない
- 「関東」と言っても東京・神奈川・千葉・埼玉のみで北関東は非対応
- 県境ユーザーの「隣県も可」ニーズに応えられない

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: yes — 栃木（北関東）も非対応
- National Expansion Risk: 「関東」の定義が南関東4県に限定されている事実が明示されていない

**Failure Category:** GEO_LOCK
**Severity:** High
**Fix Proposal:** 「その他の地域」のラベルを「東京・神奈川・千葉・埼玉 全域」に変更し、対応範囲を明確化。
**Retry Needed:** no
**Auditor Comment:**

---

## Cases W1-038 ~ W1-040: Spare（東北分散）

### Case W1-038
- **Prefecture:** 北海道
- **Region Block:** 北海道
- **Case Type:** boundary
- **User Profile:** 36歳、苫小牧の急性期病院で救急勤務、単身赴任で千葉勤務を検討
- **Entry Route:** LINE友だち追加（Instagram経由）
- **Difficulty:** 中

**Scenario:** 単身赴任で千葉を検討。「千葉県」選択で正常フローだが、フロー途中で「やっぱり家族の近くがいい」と方針転換。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「千葉県」をタップ
3. [Bot] il_subarea表示
4. [User] 「千葉市」をタップ
5. [Bot] il_facility_type表示
6. [User] 「やっぱり北海道で探したい」とテキスト入力
7. [Bot] "もう一度お選びください👇" + il_facility_type再表示
8. [User] 諦めて「急性期病院」をタップ → フロー完走
9. [Bot] matching_preview: 千葉の救急病院5件表示
10. [User] 「まだ早いかも」をタップ

**System Behavior Evaluation:**
- フロー途中の方針転換に対応できない
- テキストで「北海道で探したい」と入力しても無視
- 一度開始したフローは最後までやるか離脱するかの二択

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: yes — フロー途中での地域変更不可
- National Expansion Risk: ユーザーの心変わりをフロー内で処理できない

**Failure Category:** UX_DROP
**Severity:** Medium
**Fix Proposal:** 各ステップでテキスト入力を受け付け、「最初からやり直す」コマンドを実装。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-039
- **Prefecture:** 宮城県
- **Region Block:** 東北
- **Case Type:** adversarial
- **User Profile:** 29歳、仙台の訪問看護師、複数の転職サイトを比較中
- **Entry Route:** LINE友だち追加（Google検索経由）
- **Difficulty:** 高

**Scenario:** 他の転職サイトとの比較のため、わざと全フローを完走して対応エリアを確認する。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「その他の地域」をタップ
3. [Bot] "その他の地域ですね！候補: 24,488件" → il_facility_type表示
4. [User] 「訪問看護」をタップ
5. [Bot] il_workstyle表示
6. [User] 「日勤のみ」をタップ
7. [Bot] il_urgency表示
8. [User] 「すぐ転職したい」をタップ
9. [Bot] matching_preview: 関東の訪問看護5件表示
10. [User] 「対応エリアは関東だけですか？仙台の求人は扱っていますか？」とテキスト入力
11. [Bot] AIチャット応答（もしポストマッチングでAI応答が有効なら）or メニュー表示
12. [User] 回答が曖昧なら他サービスへ移行

**System Behavior Evaluation:**
- 比較検討ユーザーは冷静に対応エリアの制限を発見する
- 競合サービスへの流出が最も起きやすいパターン
- AIチャットが「現在は関東エリアを中心にご案内」と正直に答えれば信頼は保てる

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: yes — 仙台の求人なし
- National Expansion Risk: 比較検討ユーザーは正確にGEO_LOCKを検出し、競合へ流出

**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** エリア制限を正直に開示しつつ「仙台エリアは準備中。拡大時に優先通知」でリード保持。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-040
- **Prefecture:** 福島県
- **Region Block:** 東北
- **Case Type:** standard
- **User Profile:** 43歳、相馬市の回復期病院勤務、パート希望
- **Entry Route:** LINE友だち追加（ブログ記事経由）
- **Difficulty:** 低

**Scenario:** 相馬市の看護師が「その他の地域」で完走。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「その他の地域」をタップ
3. [Bot] "その他の地域ですね！候補: 24,488件" → il_facility_type表示
4. [User] 「回復期病院」をタップ
5. [Bot] il_department表示
6. [User] 「こだわりなし」をタップ
7. [Bot] il_workstyle表示
8. [User] 「パート・非常勤」をタップ
9. [Bot] il_urgency表示
10. [User] 「まだ情報収集」をタップ
11. [Bot] matching_preview: 関東の回復期病院5件表示
12. [User] 離脱

**System Behavior Evaluation:**
- 相馬市の求人ゼロ
- 情報収集目的のユーザーは結果不一致で静かに離脱

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes
- Reached Next Action: no
- Region Bias Signs: yes — 相馬市の求人ゼロ
- National Expansion Risk: サイレント離脱が最も計測しにくい失敗パターン

**Failure Category:** GEO_LOCK
**Severity:** High
**Fix Proposal:** マッチング結果と「その他の地域」選択の組み合わせ時にエリアミスマッチ警告を表示。
**Retry Needed:** no
**Auditor Comment:**

---

## Cases W1-041 ~ W1-050: Cross-Region

### Case W1-041
- **Prefecture:** 東京都
- **Region Block:** 関東
- **Case Type:** standard
- **User Profile:** 27歳、新宿区の急性期病院で内科勤務
- **Entry Route:** LINE友だち追加（Instagram広告経由）
- **Difficulty:** 低

**Scenario:** 東京在住の看護師が正常フローで完走。対応エリア内なので問題なし。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「東京都」をタップ
3. [Bot] il_subarea表示
4. [User] 「23区」をタップ
5. [Bot] il_facility_type表示
6. [User] 「急性期病院」をタップ
7. [Bot] il_department表示
8. [User] 「内科系」をタップ
9. [Bot] il_workstyle表示
10. [User] 「日勤のみ」をタップ
11. [Bot] il_urgency表示
12. [User] 「すぐ転職したい」をタップ
13. [Bot] matching_preview: 23区の内科急性期病院5件表示
14. [User] 「この施設について聞く」をタップ

**System Behavior Evaluation:**
- 対応エリア内なので全て正常動作
- マッチング結果も適切

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: no
- National Expansion Risk: なし（正常ケース）

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** なし
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-042
- **Prefecture:** 東京都
- **Region Block:** 関東
- **Case Type:** boundary
- **User Profile:** 34歳、多摩地域の慢性期病院で精神科勤務
- **Entry Route:** LINE友だち追加（SEO記事経由）
- **Difficulty:** 中

**Scenario:** 多摩地域の看護師がサブエリア選択で迷う。多摩から23区への通勤も検討。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「東京都」をタップ
3. [Bot] il_subarea表示（23区/多摩）
4. [User] 「多摩」をタップ
5. [Bot] il_facility_type表示
6. [User] 「慢性期病院」をタップ
7. [Bot] il_department表示
8. [User] 「精神科」をタップ
9. [Bot] il_workstyle表示
10. [User] 「日勤のみ」をタップ
11. [Bot] il_urgency表示
12. [User] 「良い所あれば」をタップ
13. [Bot] matching_preview: 多摩の慢性期精神科病院5件表示
14. [User] 「条件を変えて探す」→ 「東京都」→ 「23区」で再検索

**System Behavior Evaluation:**
- 多摩地域のマッチングは正常
- 複数サブエリアの比較ができるフロー
- 2回目の検索も正常に動作

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: no
- National Expansion Risk: なし

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** 「複数エリアを同時に検索」機能があると便利。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-043
- **Prefecture:** 大阪府
- **Region Block:** 近畿
- **Case Type:** standard
- **User Profile:** 31歳、大阪市の急性期病院で循環器勤務
- **Entry Route:** LINE友だち追加（Instagram広告経由）
- **Difficulty:** 低

**Scenario:** 大阪の看護師がLINE登録。「その他の地域」を選択してフロー完走。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「その他の地域」をタップ（大阪がない）
3. [Bot] "その他の地域ですね！候補: 24,488件" → il_facility_type表示
4. [User] 「急性期病院」をタップ
5. [Bot] il_department表示
6. [User] 「循環器」をタップ
7. [Bot] il_workstyle表示
8. [User] 「夜勤ありOK」をタップ
9. [Bot] il_urgency表示
10. [User] 「良い所あれば」をタップ
11. [Bot] matching_preview: 関東の循環器病院5件表示

**System Behavior Evaluation:**
- 大阪という大都市圏のユーザーに関東の求人を見せる
- 「24,488件」の表示が大阪の求人を含むと誤解させる

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: yes — 大阪の求人ゼロ、全て関東
- National Expansion Risk: 大阪は全国2位の看護師需要エリア。対応しないのは大きな機会損失

**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** 大阪府を5番目の対応エリアとして追加を検討。少なくとも「関東のみ対応」を明示。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-044
- **Prefecture:** 大阪府
- **Region Block:** 近畿
- **Case Type:** adversarial
- **User Profile:** 28歳、堺市のクリニック勤務
- **Entry Route:** LINE友だち追加（TikTok経由）
- **Difficulty:** 高

**Scenario:** 大阪の看護師が「大阪」とテキスト入力後、「なんで大阪ないねん」と関西弁で苦情。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「大阪」とテキスト入力
3. [Bot] "もう一度お選びください👇" + il_area再表示
4. [User] 「なんで大阪ないねん」とテキスト入力
5. [Bot] "もう一度お選びください👇" + il_area再表示
6. [User] 「使えんわこれ」とテキスト入力
7. [Bot] "もう一度お選びください👇" + il_area再表示
8. [User] ブロック

**System Behavior Evaluation:**
- 関西弁の苦情にも定型文で応答
- 「なんで大阪ないねん」という正当なフィードバックが完全にロスト
- ネガティブ体験によるブランド毀損

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: no
- Reached Next Action: no
- Region Bias Signs: yes — 大阪が選択肢にない
- National Expansion Risk: 大阪ユーザーからのフィードバックが記録されない

**Failure Category:** INPUT_LOCK
**Severity:** Critical
**Fix Proposal:** テキスト入力をログに記録し、対応外エリアの需要データとして分析。苦情テキストには「ご不便おかけします。大阪エリアは準備中です」と回答。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-045
- **Prefecture:** 愛知県
- **Region Block:** 中部
- **Case Type:** standard
- **User Profile:** 33歳、名古屋の急性期病院で外科勤務
- **Entry Route:** LINE友だち追加（Google検索経由）
- **Difficulty:** 低

**Scenario:** 名古屋の看護師が「その他の地域」で完走。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「その他の地域」をタップ
3. [Bot] "その他の地域ですね！候補: 24,488件" → il_facility_type表示
4. [User] 「急性期病院」をタップ
5. [Bot] il_department表示
6. [User] 「外科系」をタップ
7. [Bot] il_workstyle表示
8. [User] 「夜勤ありOK」をタップ
9. [Bot] il_urgency表示
10. [User] 「すぐ転職したい」をタップ
11. [Bot] matching_preview: 関東の外科病院5件表示

**System Behavior Evaluation:**
- 名古屋は全国3位の看護師需要エリアだが対応外
- 「すぐ転職したい」緊急ユーザーに関東の求人を見せる

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: yes — 名古屋の求人ゼロ
- National Expansion Risk: 三大都市圏の一角が非対応

**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** 愛知県をD1データベースに追加。最低限「対応エリア：関東4県」の明示。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-046
- **Prefecture:** 愛知県
- **Region Block:** 中部
- **Case Type:** boundary
- **User Profile:** 29歳、豊橋市在住、静岡・神奈川への通勤も可能
- **Entry Route:** LINE友だち追加（SEO記事経由）
- **Difficulty:** 中

**Scenario:** 豊橋在住で神奈川西部（小田原等）への通勤も検討。「神奈川県」を選択。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「神奈川県」をタップ
3. [Bot] il_subarea表示
4. [User] 「県西」をタップ
5. [Bot] il_facility_type表示
6. [User] 「回復期病院」をタップ
7. [Bot] il_department表示
8. [User] 「リハビリ」をタップ
9. [Bot] il_workstyle表示
10. [User] 「日勤のみ」をタップ
11. [Bot] il_urgency表示
12. [User] 「良い所あれば」をタップ
13. [Bot] matching_preview: 県西の回復期リハビリ病院5件表示

**System Behavior Evaluation:**
- 神奈川県西部は対応エリア内なので正常動作
- 豊橋→小田原は新幹線通勤圏として現実的
- ただし愛知県の求人は見られない

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: no — ユーザーが神奈川を選択
- National Expansion Risk: 県境ユーザーは対応エリアを選べるので部分的に機能

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** なし（正常動作）
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-047
- **Prefecture:** 福岡県
- **Region Block:** 九州
- **Case Type:** standard
- **User Profile:** 30歳、福岡市の急性期病院で小児科勤務
- **Entry Route:** LINE友だち追加（Instagram広告経由）
- **Difficulty:** 低

**Scenario:** 福岡の看護師が「その他の地域」で完走。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「その他の地域」をタップ
3. [Bot] "その他の地域ですね！候補: 24,488件" → il_facility_type表示
4. [User] 「急性期病院」をタップ
5. [Bot] il_department表示
6. [User] 「小児科」をタップ
7. [Bot] il_workstyle表示
8. [User] 「日勤のみ」をタップ
9. [Bot] il_urgency表示
10. [User] 「良い所あれば」をタップ
11. [Bot] matching_preview: 関東の小児科病院5件表示
12. [User] 「福岡の求人が見たいんですが」とテキスト入力
13. [Bot] ポストマッチングメニュー表示 or AIチャット

**System Behavior Evaluation:**
- 福岡は九州最大の都市だが求人ゼロ
- ポストマッチングのテキスト入力でAIが「福岡は準備中」と答えるかは不明

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes
- Reached Next Action: yes
- Region Bias Signs: yes — 福岡の求人ゼロ
- National Expansion Risk: 九州全域が非対応

**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** 全国展開計画のロードマップを策定。当面は対応エリアを正直に明示。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-048
- **Prefecture:** 福岡県
- **Region Block:** 九州
- **Case Type:** adversarial
- **User Profile:** 35歳、北九州市の訪問看護師
- **Entry Route:** LINE友だち追加（友人紹介）
- **Difficulty:** 高

**Scenario:** 北九州の看護師がWelcomeメッセージの「24,488件」を見て「福岡も入ってますか？」と質問。

**Conversation Flow:**
1. [Bot] Welcome: "24,488件の医療機関の中からあなたにぴったりの職場を見つけます！" + il_area表示
2. [User] 「福岡も入ってますか？」とテキスト入力
3. [Bot] "もう一度お選びください👇" + il_area再表示
4. [User] 「24,488件って書いてるけど、どの地域の話？」とテキスト入力
5. [Bot] "もう一度お選びください👇" + il_area再表示
6. [User] 離脱

**System Behavior Evaluation:**
- 「24,488件」の内訳を聞いても回答なし
- ユーザーの正当な質問が完全に無視される
- 数字の信頼性が問われる

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: no
- Reached Next Action: no
- Region Bias Signs: yes — 件数の内訳が非開示
- National Expansion Risk: 「24,488件」という数字が全国と誤認される

**Failure Category:** AMBIG_FAIL
**Severity:** Critical
**Fix Proposal:** Welcomeメッセージを「関東エリア24,488件の医療機関の中から...」に変更。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-049
- **Prefecture:** 沖縄県
- **Region Block:** 沖縄
- **Case Type:** standard
- **User Profile:** 26歳、那覇の急性期病院で救急勤務
- **Entry Route:** LINE友だち追加（TikTok経由）
- **Difficulty:** 低

**Scenario:** 沖縄の看護師が「その他の地域」で完走。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「その他の地域」をタップ
3. [Bot] "その他の地域ですね！候補: 24,488件" → il_facility_type表示
4. [User] 「急性期病院」をタップ
5. [Bot] il_department表示
6. [User] 「救急」をタップ
7. [Bot] il_workstyle表示
8. [User] 「夜勤ありOK」をタップ
9. [Bot] il_urgency表示
10. [User] 「すぐ転職したい」をタップ
11. [Bot] matching_preview: 関東の救急病院5件表示
12. [User] 「沖縄の求人はないの？」→ 離脱

**System Behavior Evaluation:**
- 沖縄から関東は地理的に最も遠い
- 転居の現実性が極めて低い結果を表示
- 沖縄ユーザーにとって完全に無意味

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes
- Reached Next Action: no
- Region Bias Signs: yes — 沖縄の求人ゼロ、表示は全て関東
- National Expansion Risk: 地理的距離が最大のケースでGEO_LOCKの問題が顕著

**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** 「その他の地域」選択時に「現在は関東（東京・神奈川・千葉・埼玉）の求人のみです。沖縄エリアは準備中です」と明示。
**Retry Needed:** no
**Auditor Comment:**

---

### Case W1-050
- **Prefecture:** 沖縄県
- **Region Block:** 沖縄
- **Case Type:** adversarial
- **User Profile:** 38歳、宮古島の診療所勤務、離島勤務の特殊性
- **Entry Route:** LINE友だち追加（Google検索「離島 看護師 転職」経由）
- **Difficulty:** 高

**Scenario:** 宮古島の看護師が「離島で働ける求人ありますか？」と初手でテキスト入力。

**Conversation Flow:**
1. [Bot] Welcome + il_area表示
2. [User] 「離島で働ける求人ありますか？」とテキスト入力
3. [Bot] "もう一度お選びください👇" + il_area再表示
4. [User] 「沖縄」とテキスト入力
5. [Bot] "もう一度お選びください👇" + il_area再表示
6. [User] 「宮古島」とテキスト入力
7. [Bot] "もう一度お選びください👇" + il_area再表示
8. [User] 「対応してない地域はどこ？」とテキスト入力
9. [Bot] "もう一度お選びください👇" + il_area再表示
10. [User] ブロック

**System Behavior Evaluation:**
- 離島勤務という特殊なニーズに一切対応できない
- 4回連続のテキスト入力を全て無視
- 「対応してない地域はどこ？」という基本的な質問にも答えない
- GEO_LOCKとINPUT_LOCKの複合問題

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: no
- Reached Next Action: no
- Region Bias Signs: yes — 沖縄・離島が完全に非対応
- National Expansion Risk: 離島看護師という高ニーズ層を完全に逃している

**Failure Category:** INPUT_LOCK
**Severity:** Critical
**Fix Proposal:** intakeフェーズのテキスト入力に対してAI応答を実装。「離島」等のキーワードには「現在離島エリアは準備中です。関東エリアの求人にご興味はありますか？」と案内。テキスト入力のログを需要データとして保存。
**Retry Needed:** no
**Auditor Comment:**

---

## Summary Statistics

| Metric | Count | Rate |
|--------|-------|------|
| Total Cases | 50 | 100% |
| Drop-off Risk | 40 | 80% |
| Reached Job Proposal | 43 | 86% |
| Reached Next Action | 38 | 76% |
| Region Bias Signs | 42 | 84% |

### Failure Category Breakdown

| Category | Count | % |
|----------|-------|---|
| GEO_LOCK | 25 | 50% |
| INPUT_LOCK | 14 | 28% |
| NONE | 7 | 14% |
| HUMAN_HANDOFF_FAIL | 2 | 4% |
| UX_DROP | 2 | 4% |
| AMBIG_FAIL | 1 | 2% |

### Severity Breakdown

| Severity | Count | % |
|----------|-------|---|
| Critical | 24 | 48% |
| High | 14 | 28% |
| Medium | 3 | 6% |
| Low | 9 | 18% |

### Case Type Breakdown

| Type | Count |
|------|-------|
| Standard | 30 |
| Boundary | 12 |
| Adversarial | 8 |

### Key Findings

1. **GEO_LOCK is the dominant failure**: 50% of all cases hit the geographic lock issue. Every 北海道・東北 user who selects "その他の地域" receives only Kanto results with no warning.

2. **INPUT_LOCK compounds GEO_LOCK**: 28% of cases show that free text input during intake is completely ignored. Users who type their prefecture name, ask questions, or express confusion all receive the same "もう一度お選びください" response.

3. **"24,488件" is misleading**: The welcome message implies nationwide coverage. Users from non-Kanto areas believe this number includes their region.

4. **"その他の地域" label is deceptive**: The label suggests the service covers areas beyond the four listed prefectures, but it actually just searches across all Kanto sub-areas.

5. **No escape hatch**: There is no way for a non-Kanto user to discover that the service doesn't cover their area without completing the entire intake flow and seeing irrelevant results.

6. **Handoff burden**: Users who reach "直接相談する" from non-Kanto areas create work for human staff who cannot help them.

7. **Silent data loss**: User intent expressed via text (prefecture names, specific conditions, complaints) is never logged or analyzed as demand data.

### Priority Fixes (Worker 1 Recommendation)

1. **P0**: Change Welcome message to "関東エリア（東京・神奈川・千葉・埼玉）24,488件の医療機関の中から..."
2. **P0**: Replace "その他の地域" with explicit "関東エリア全域" or add a confirmation step for non-Kanto users
3. **P1**: Implement text input NLP during intake to detect prefecture names and respond appropriately
4. **P1**: Add "戻る" button to each intake step
5. **P2**: Log all text inputs during intake as demand data for expansion planning
6. **P2**: Add "エリア拡大通知" opt-in for non-Kanto users to retain leads
