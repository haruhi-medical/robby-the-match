# Worker 1: 東京都 LINE Bot Simulation Cases (KW1-001 ~ KW1-050)

> **Scope:** 東京都全域（23区20件 / 多摩15件 / どこでもOK 5件 / 越境10件）
> **Case Mix:** Standard 30 / Boundary 12 / Adversarial 8
> **DB:** 東京12,748施設 / 病院1,498件（全体24,488件）
> **Known Bugs:** tokyo_tama 9都市のみ（20+都市欠落）/ tokyo_included に横浜市・川崎市混入 / tokyo_included候補数が全24,488件カウント

---

## 23区 Cases (KW1-001 ~ KW1-020)

---

### Case KW1-001
- **Prefecture:** 東京都
- **Sub-area:** 23区
- **Specific Location:** 世田谷区
- **Case Type:** standard
- **User Profile:** 32歳、急性期病院の外科病棟3年目。通勤30分圏内で日勤のみ希望。
- **Entry Route:** LP→LINE
- **Difficulty:** Easy

**Scenario:** 世田谷区在住の看護師が、近場の回復期病院で日勤のみの求人を探す標準的なフロー。

**Conversation Flow:**
1. [Bot] Welcome: "○○件の医療機関の中からあなたにぴったりの職場を見つけます"
2. [User] 東京都 を選択
3. [Bot] il_subarea表示: 23区 / 多摩地域 / どこでもOK
4. [User] 23区 を選択
5. [Bot] il_facility_type表示
6. [User] 回復期病院 を選択
7. [Bot] il_department表示
8. [User] リハビリ を選択
9. [Bot] il_workstyle表示
10. [User] 日勤のみ を選択
11. [Bot] il_urgency表示
12. [User] 良い所あれば を選択
13. [Bot] matching_preview: 5施設表示（世田谷区含む23区内の回復期リハビリ病院）

**System Behavior Evaluation:**
- 23区全域が検索対象に含まれるため、回復期リハビリ病院の候補は十分ある
- 世田谷区固有の絞り込みはないが、23区内なので通勤圏内の結果が出る

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Handoff: no
- Matching Quality: good
- Sub-area Coverage Issue: no

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** N/A
**Retry Needed:** no
**Auditor Comment:**

---

### Case KW1-002
- **Prefecture:** 東京都
- **Sub-area:** 23区
- **Specific Location:** 足立区
- **Case Type:** standard
- **User Profile:** 25歳、新卒2年目。急性期病院で夜勤ありOK。救急志望。
- **Entry Route:** 広告→LINE（source=meta_ad）
- **Difficulty:** Easy

**Scenario:** Meta広告経由でLINE登録した若手看護師。足立区周辺で救急のある急性期病院を探す。

**Conversation Flow:**
1. [Bot] "広告から来てくれたんですね！○○件の医療機関の中から..."
2. [User] 東京都 を選択
3. [Bot] il_subarea表示
4. [User] 23区 を選択
5. [Bot] il_facility_type表示
6. [User] 急性期病院 を選択
7. [Bot] il_department表示
8. [User] 救急 を選択
9. [Bot] il_workstyle表示
10. [User] 夜勤ありOK を選択
11. [Bot] il_urgency表示
12. [User] すぐ転職したい を選択
13. [Bot] matching_preview: 5施設表示

**System Behavior Evaluation:**
- Meta広告ウェルカムメッセージが正しく表示される
- 23区内の救急対応急性期病院は多数あるはず（足立区周辺含む）
- 「すぐ転職したい」の場合、handoff提案が強めに出るか要確認

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Handoff: no
- Matching Quality: good
- Sub-area Coverage Issue: no

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** N/A
**Retry Needed:** no
**Auditor Comment:**

---

### Case KW1-003
- **Prefecture:** 東京都
- **Sub-area:** 23区
- **Specific Location:** 江戸川区
- **Case Type:** standard
- **User Profile:** 40歳、ブランク5年のママナース。パート希望。クリニック志望。
- **Entry Route:** blog記事→LINE
- **Difficulty:** Easy

**Scenario:** ブログ記事「ブランクナースの復職ガイド」から来た復職希望者。江戸川区でパートのクリニック。

**Conversation Flow:**
1. [Bot] blog経由ウェルカム: 専用メッセージ
2. [User] 東京都 を選択
3. [Bot] il_subarea表示
4. [User] 23区 を選択
5. [Bot] il_facility_type表示
6. [User] クリニック を選択
7. [Bot] il_workstyle表示（**il_departmentスキップ** — クリニックは診療科質問なし）
8. [User] パート・非常勤 を選択
9. [Bot] il_urgency表示
10. [User] 良い所あれば を選択
11. [Bot] matching_preview: 5施設表示

**System Behavior Evaluation:**
- クリニック選択時にil_departmentがスキップされることを確認
- クリニック選択時にil_workstyleで「日勤のみ」に自動設定されるか？ → コード上はスキップではなく自動設定
- 待って、コード分析によるとクリニックは workstyle が 'day' に自動設定される → il_workstyleもスキップされるはず
- パート希望だがクリニック=日勤自動なので、パート選択肢が出ない可能性あり

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Handoff: no
- Matching Quality: acceptable
- Sub-area Coverage Issue: no

**Failure Category:** UX_DROP
**Severity:** Medium
**Fix Proposal:** クリニック選択時もパート・非常勤の選択は必要。日勤のみ自動設定はworkstyle全体ではなくシフト形態のみに適用すべき。
**Retry Needed:** no
**Auditor Comment:**

---

### Case KW1-004
- **Prefecture:** 東京都
- **Sub-area:** 23区
- **Specific Location:** 千代田区
- **Case Type:** boundary
- **User Profile:** 35歳、美容クリニック希望。高収入志向。
- **Entry Route:** 直接follow
- **Difficulty:** Medium

**Scenario:** 美容クリニック特化の求人を探しているが、facility_typeに「美容クリニック」の選択肢がない。「クリニック」を選ぶしかない。

**Conversation Flow:**
1. [Bot] Welcome
2. [User] 東京都 → 23区 を選択
3. [Bot] il_facility_type表示: 急性期/回復期/慢性期/クリニック/訪問看護/介護施設/こだわりなし
4. [User] クリニック を選択
5. [Bot] il_workstyle（スキップ、日勤自動設定）→ il_urgency表示
6. [User] すぐ転職したい を選択
7. [Bot] matching_preview: 5施設表示 → 一般クリニック（内科・皮膚科等）が混在
8. [User] "美容クリニックはありますか？" とフリーテキスト入力
9. [Bot] AI consultation: GPT-4o-miniが美容クリニックについて回答

**System Behavior Evaluation:**
- 「美容クリニック」というカテゴリが存在しないため、一般クリニックと混在した結果になる
- マッチング後のAI相談で「美容クリニック」について聞けるが、DB検索の再実行はされない
- ユーザーの本来のニーズ（美容特化）が満たされない

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes
- Reached Handoff: no
- Matching Quality: poor
- Sub-area Coverage Issue: no

**Failure Category:** JOB_MATCH_FAIL
**Severity:** Medium
**Fix Proposal:** facility_typeに「美容クリニック」を追加するか、クリニック選択後に診療科サブカテゴリを表示する。
**Retry Needed:** yes
**Auditor Comment:**

---

### Case KW1-005
- **Prefecture:** 東京都
- **Sub-area:** 23区
- **Specific Location:** 葛飾区
- **Case Type:** standard
- **User Profile:** 28歳、訪問看護に興味。現在は急性期病棟。
- **Entry Route:** area_page→LINE
- **Difficulty:** Easy

**Scenario:** 葛飾区の地域ページから来た看護師。訪問看護ステーションを探す標準フロー。

**Conversation Flow:**
1. [Bot] area_page経由ウェルカム
2. [User] 東京都 → 23区 を選択
3. [Bot] il_facility_type表示
4. [User] 訪問看護 を選択
5. [Bot] il_workstyle表示（訪問看護は病院ではないのでil_departmentスキップ）
6. [User] 日勤のみ を選択
7. [Bot] il_urgency表示
8. [User] 良い所あれば を選択
9. [Bot] matching_preview: 5施設表示

**System Behavior Evaluation:**
- 訪問看護は診療科質問スキップが正しく動作するはず
- 23区内の訪問看護ステーション数は十分あるはず
- 葛飾区固有の絞り込みはないが、結果は23区全域から

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Handoff: no
- Matching Quality: good
- Sub-area Coverage Issue: no

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** N/A
**Retry Needed:** no
**Auditor Comment:**

---

### Case KW1-006
- **Prefecture:** 東京都
- **Sub-area:** 23区
- **Specific Location:** 港区
- **Case Type:** standard
- **User Profile:** 30歳、循環器専門。キャリアアップ志望。
- **Entry Route:** 直接follow
- **Difficulty:** Easy

**Scenario:** 循環器内科でキャリアアップしたい中堅ナース。港区周辺の急性期病院希望。

**Conversation Flow:**
1. [Bot] Welcome
2. [User] 東京都 → 23区 → 急性期病院 → 循環器 → 夜勤ありOK → すぐ転職したい
3. [Bot] matching_preview: 5施設表示
4. [User] "この施設について聞く" を選択
5. [Bot] AI consultation開始、施設の循環器科の詳細を説明
6. [User] "看護師の教育体制はどうですか？"
7. [Bot] AIが教育体制について回答（DB情報 + 一般知識）
8. [User] "直接相談する" を選択
9. [Bot] handoff_phone_check: "お電話は控えた方が良いですか？"
10. [User] "電話OK"
11. [Bot] handoff_phone_time: 時間帯選択
12. [User] 時間帯選択
13. [Bot] handoff完了、Slack転送

**System Behavior Evaluation:**
- 循環器 + 急性期 + 23区の組み合わせは結果豊富なはず
- AI consultation → handoff の完全フローテスト
- handoff後のbot沈黙確認が必要

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Handoff: yes
- Matching Quality: good
- Sub-area Coverage Issue: no

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** N/A
**Retry Needed:** no
**Auditor Comment:**

---

### Case KW1-007
- **Prefecture:** 東京都
- **Sub-area:** 23区
- **Specific Location:** 墨田区
- **Case Type:** boundary
- **User Profile:** 45歳、慢性期病院の主任。精神科への転科希望。
- **Entry Route:** 直接follow
- **Difficulty:** Medium

**Scenario:** 精神科 + 慢性期病院の組み合わせ。23区内では精神科の慢性期病院は限定的か。

**Conversation Flow:**
1. [Bot] Welcome
2. [User] 東京都 → 23区 → 慢性期病院 → 精神科 → 日勤のみ → 良い所あれば
3. [Bot] matching_preview: 施設表示

**System Behavior Evaluation:**
- 慢性期 + 精神科 + 23区: ニッチだが精神科病院は多摩に集中している傾向あり
- 23区内の精神科慢性期は少数の可能性 → 結果が0-2件になる可能性
- 0件の場合のハンドリングを確認

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes（少数の可能性）
- Reached Handoff: no
- Matching Quality: acceptable
- Sub-area Coverage Issue: no

**Failure Category:** JOB_MATCH_FAIL
**Severity:** Low
**Fix Proposal:** 結果が少ない場合「条件を広げますか？」の提案を強化。多摩地域の精神科も提案すべき。
**Retry Needed:** no
**Auditor Comment:**

---

### Case KW1-008
- **Prefecture:** 東京都
- **Sub-area:** 23区
- **Specific Location:** 新宿区
- **Case Type:** adversarial
- **User Profile:** 不明（テスト目的の入力）
- **Entry Route:** 直接follow
- **Difficulty:** Hard

**Scenario:** intake中にフリーテキストを連続入力。ボタンを押さず「新宿で働きたい」「ICUがいい」等を打ち込む。

**Conversation Flow:**
1. [Bot] Welcome + il_area クイックリプライ表示
2. [User] "東京の新宿で働きたいです"（フリーテキスト）
3. [Bot] unexpectedTextCount++、"もう一度お選びください" + クイックリプライ再表示
4. [User] "ICUのある病院を教えてください"（フリーテキスト）
5. [Bot] unexpectedTextCount++、"もう一度お選びください" + クイックリプライ再表示
6. [User] "なんで選べないの？"（フリーテキスト）
7. [Bot] unexpectedTextCount++、同じ応答
8. [User] 東京都 をようやくボタンで選択
9. [Bot] il_subarea表示 → 以降正常フロー

**System Behavior Evaluation:**
- フリーテキストの意図（新宿、ICU）が完全に無視される
- unexpectedTextCountにエスカレーション閾値がない → 何度でも同じ応答
- ユーザーが「なぜボタンしか使えないのか」を理解するまでの案内がない
- 3回連続の無視はUX的に脱落リスクが高い

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes（最終的にボタン選択した場合）
- Reached Handoff: no
- Matching Quality: N/A
- Sub-area Coverage Issue: no

**Failure Category:** INPUT_LOCK
**Severity:** High
**Fix Proposal:** (1) unexpectedTextCount 3回でhandoff提案 (2) フリーテキストからキーワード抽出してボタン選択を提案 (3) 「ボタンからお選びください」の説明を初回から明示
**Retry Needed:** yes
**Auditor Comment:**

---

### Case KW1-009
- **Prefecture:** 東京都
- **Sub-area:** 23区
- **Specific Location:** 大田区
- **Case Type:** standard
- **User Profile:** 29歳、介護施設で看護師として勤務希望。夜勤専従。
- **Entry Route:** LP→LINE
- **Difficulty:** Easy

**Scenario:** 介護施設 + 夜勤専従という組み合わせ。大田区在住。

**Conversation Flow:**
1. [Bot] LP経由ウェルカム
2. [User] 東京都 → 23区 → 介護施設 → 夜勤専従 → すぐ転職したい
3. [Bot] matching_preview: 5施設表示
4. [User] "もっと求人を見る" を選択
5. [Bot] 追加施設表示

**System Behavior Evaluation:**
- 介護施設は診療科質問スキップ
- 夜勤専従 + 介護施設は需要が高い組み合わせ、23区内に多数あるはず
- 「もっと求人を見る」の追加表示機能テスト

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Handoff: no
- Matching Quality: good
- Sub-area Coverage Issue: no

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** N/A
**Retry Needed:** no
**Auditor Comment:**

---

### Case KW1-010
- **Prefecture:** 東京都
- **Sub-area:** 23区
- **Specific Location:** 渋谷区
- **Case Type:** boundary
- **User Profile:** 26歳、小児科希望。夜勤専従。
- **Entry Route:** 直接follow
- **Difficulty:** Medium

**Scenario:** 小児科 + 夜勤専従 + 23区 → 非常にニッチな条件。0件になる可能性をテスト。

**Conversation Flow:**
1. [Bot] Welcome
2. [User] 東京都 → 23区 → 急性期病院 → 小児科 → 夜勤専従 → すぐ転職したい
3. [Bot] matching_preview: 0件 or 極少数

**System Behavior Evaluation:**
- 小児科 + 夜勤専従は極めてニッチ。23区内で該当する病院は0-1件の可能性
- 0件時のUXハンドリングを確認: 「条件を変えて探す」が提案されるか
- 0件で脱落するユーザーが多いはず

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: no（0件の可能性大）
- Reached Handoff: no
- Matching Quality: poor
- Sub-area Coverage Issue: no

**Failure Category:** JOB_MATCH_FAIL
**Severity:** High
**Fix Proposal:** 0件時に(1)条件緩和提案（「夜勤ありOK」に変更を提案）(2)「直接相談する」を強く提案 (3)近隣県の候補を提示
**Retry Needed:** yes
**Auditor Comment:**

---

### Case KW1-011
- **Prefecture:** 東京都
- **Sub-area:** 23区
- **Specific Location:** 練馬区
- **Case Type:** standard
- **User Profile:** 33歳、回復期病院で整形外科リハビリ。日勤のみ。
- **Entry Route:** 広告→LINE（source=meta_ad）
- **Difficulty:** Easy

**Scenario:** 練馬区在住。回復期 + 整形外科 + 日勤のみの標準フロー。

**Conversation Flow:**
1. [Bot] Meta広告ウェルカム
2. [User] 東京都 → 23区 → 回復期病院 → 整形外科 → 日勤のみ → 良い所あれば
3. [Bot] matching_preview: 5施設表示
4. [User] "条件を変えて探す" を選択
5. [Bot] intake最初からやり直し（il_area?）or 途中から変更可能?

**System Behavior Evaluation:**
- 「条件を変えて探す」のフロー: 完全リセットか部分変更か確認
- 回復期 + 整形外科は十分な候補があるはず
- 条件変更フローの使いやすさをテスト

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Handoff: no
- Matching Quality: good
- Sub-area Coverage Issue: no

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** 「条件を変えて探す」は全リセットではなく、変更したい項目だけ選べるUIが望ましい。
**Retry Needed:** no
**Auditor Comment:**

---

### Case KW1-012
- **Prefecture:** 東京都
- **Sub-area:** 23区
- **Specific Location:** 板橋区
- **Case Type:** adversarial
- **User Profile:** 不明
- **Entry Route:** 直接follow
- **Difficulty:** Hard

**Scenario:** intake中に同じボタンを高速連打。il_areaで「東京都」を3回連続タップ。

**Conversation Flow:**
1. [Bot] Welcome + il_area
2. [User] 東京都 をタップ（1回目）
3. [User] 東京都 をタップ（2回目、レスポンス前に再タップ）
4. [User] 東京都 をタップ（3回目）
5. [Bot] il_subarea表示（1回目の処理）
6. [Bot] 2回目・3回目の処理結果 → 状態の不整合が起きるか?

**System Behavior Evaluation:**
- Webhookの重複処理対策を確認
- 同一postbackの連続送信がセッション状態を破壊しないか
- LINE Messaging APIのレート制限は通常問題ない

**Results:**
- Drop-off risk: yes（状態不整合の場合）
- Reached Job Proposal: no（状態破壊の場合）
- Reached Handoff: no
- Matching Quality: N/A
- Sub-area Coverage Issue: no

**Failure Category:** REENTRY_FAIL
**Severity:** Medium
**Fix Proposal:** Webhook受信時にセッション状態とphaseを確認し、同一phaseの重複postbackを無視する。
**Retry Needed:** yes
**Auditor Comment:**

---

### Case KW1-013
- **Prefecture:** 東京都
- **Sub-area:** 23区
- **Specific Location:** 中野区
- **Case Type:** standard
- **User Profile:** 38歳、産婦人科専門。パート希望。
- **Entry Route:** 紹介（友人のLINE共有）
- **Difficulty:** Easy

**Scenario:** 友人経由でLINE登録。産婦人科のある病院をパートで。

**Conversation Flow:**
1. [Bot] Welcome（標準、紹介元の追跡なし）
2. [User] 東京都 → 23区 → 急性期病院 → 産婦人科 → パート・非常勤 → 良い所あれば
3. [Bot] matching_preview: 5施設表示

**System Behavior Evaluation:**
- 紹介経由の特別なウェルカムメッセージはなし（entry routeに「紹介」なし）
- 産婦人科 + 急性期 + パートの組み合わせ: 23区内に存在するはず
- 紹介追跡の仕組みがないことの確認

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Handoff: no
- Matching Quality: acceptable
- Sub-area Coverage Issue: no

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** 紹介経由の追跡（UTMパラメータ等）があると分析に有用。
**Retry Needed:** no
**Auditor Comment:**

---

### Case KW1-014
- **Prefecture:** 東京都
- **Sub-area:** 23区
- **Specific Location:** 荒川区
- **Case Type:** standard
- **User Profile:** 27歳、急性期の内科系。夜勤ありOK。情報収集段階。
- **Entry Route:** 直接follow
- **Difficulty:** Easy

**Scenario:** 「まだ情報収集」を選択した場合のnurture_warmフローをテスト。

**Conversation Flow:**
1. [Bot] Welcome
2. [User] 東京都 → 23区 → 急性期病院 → 内科系 → 夜勤ありOK → まだ情報収集
3. [Bot] matching_preview: 5施設表示（情報収集でもマッチングは実行される）
4. [User] "まだ早いかも" を選択
5. [Bot] nurture_warm: 「わかりました！良い求人が出たらお知らせしますね」等

**System Behavior Evaluation:**
- 「まだ情報収集」→ マッチング表示 → 「まだ早いかも」のnurtureフロー
- nurture_warmメッセージの温度感: 押し付けがましくないか
- 後日のフォローアップ設計があるか確認

**Results:**
- Drop-off risk: no（意図的な離脱）
- Reached Job Proposal: yes
- Reached Handoff: no
- Matching Quality: good
- Sub-area Coverage Issue: no

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** nurture_warm後に1週間後の再アプローチメッセージがあると良い。
**Retry Needed:** no
**Auditor Comment:**

---

### Case KW1-015
- **Prefecture:** 東京都
- **Sub-area:** 23区
- **Specific Location:** 豊島区
- **Case Type:** boundary
- **User Profile:** 50歳、管理職経験あり。クリニックの管理者ポジション希望。
- **Entry Route:** 直接follow
- **Difficulty:** Medium

**Scenario:** 「管理者」「師長」等のポジション指定ができない。facility_typeとworkstyleにポジション概念がない。

**Conversation Flow:**
1. [Bot] Welcome
2. [User] 東京都 → 23区 → クリニック → 良い所あれば
3. [Bot] matching_preview: 一般の看護師求人が表示される
4. [User] "管理職のポジションはありますか？" とフリーテキスト
5. [Bot] AI consultation: 管理職についてAIが回答するが、検索条件の変更はできない

**System Behavior Evaluation:**
- ポジション（スタッフ/主任/師長/管理者）の選択肢がintakeにない
- AI相談で対応可能だが、DB検索の再実行ができないため実質的に非対応
- 管理職希望者は早期handoffが適切

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes（ただし管理職ではない）
- Reached Handoff: no
- Matching Quality: poor
- Sub-area Coverage Issue: no

**Failure Category:** JOB_MATCH_FAIL
**Severity:** Medium
**Fix Proposal:** ポジション/役職のintake質問を追加するか、AI相談から直接handoff提案する流れを強化。
**Retry Needed:** no
**Auditor Comment:**

---

### Case KW1-016
- **Prefecture:** 東京都
- **Sub-area:** 23区
- **Specific Location:** 北区
- **Case Type:** standard
- **User Profile:** 31歳、慢性期病院の内科。日勤のみ希望。
- **Entry Route:** LP hero CTA→LINE
- **Difficulty:** Easy

**Scenario:** LP上部のCTAボタンから来た看護師。慢性期 + 内科 + 日勤の標準フロー。

**Conversation Flow:**
1. [Bot] LP hero経由ウェルカム
2. [User] 東京都 → 23区 → 慢性期病院 → 内科系 → 日勤のみ → すぐ転職したい
3. [Bot] matching_preview: 5施設表示
4. [User] "直接相談する" を選択
5. [Bot] handoff_phone_check
6. [User] "LINEでお願いします"
7. [Bot] handoff（LINE only）、Slack転送

**System Behavior Evaluation:**
- LP hero CTA → LINE登録 → intake → matching → handoff（LINE only）の完全フロー
- handoff時にphonePreference: line_onlyで適切なメッセージが出るか
- handoff後のbot沈黙テスト

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Handoff: yes
- Matching Quality: good
- Sub-area Coverage Issue: no

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** N/A
**Retry Needed:** no
**Auditor Comment:**

---

### Case KW1-017
- **Prefecture:** 東京都
- **Sub-area:** 23区
- **Specific Location:** 台東区
- **Case Type:** adversarial
- **User Profile:** 不明
- **Entry Route:** 直接follow
- **Difficulty:** Hard

**Scenario:** AI consultation中に5ターン上限に達する。その後さらに質問を続ける。

**Conversation Flow:**
1. [Bot] Welcome → intake完了 → matching_preview表示
2. [User] "この施設について聞く"
3. [Bot] AI consultation開始
4. [User] 質問1 → [Bot] 回答1
5. [User] 質問2 → [Bot] 回答2
6. [User] 質問3 → [Bot] 回答3
7. [User] 質問4 → [Bot] 回答4
8. [User] 質問5 → [Bot] 回答5 + "もっと詳しく知りたい場合は直接相談がおすすめです"
9. [User] 質問6 → [Bot] handoff提案?

**System Behavior Evaluation:**
- 5ターン上限後の挙動を確認
- handoff提案が出るか、それとも単にブロックされるか
- ユーザーの質問がさらに続いた場合の対応

**Results:**
- Drop-off risk: yes（上限到達で不満）
- Reached Job Proposal: yes
- Reached Handoff: no（提案はされるが実行はユーザー次第）
- Matching Quality: good
- Sub-area Coverage Issue: no

**Failure Category:** UX_DROP
**Severity:** Medium
**Fix Proposal:** 5ターン上限到達時に「直接相談する」ボタンを表示し、遷移しやすくする。
**Retry Needed:** no
**Auditor Comment:**

---

### Case KW1-018
- **Prefecture:** 東京都
- **Sub-area:** 23区
- **Specific Location:** 杉並区
- **Case Type:** standard
- **User Profile:** 24歳、新卒。急性期の外科系。夜勤ありOK。
- **Entry Route:** salary_check→LINE
- **Difficulty:** Easy

**Scenario:** 給与診断ページから来た新人ナース。外科系急性期で夜勤ありの標準フロー。

**Conversation Flow:**
1. [Bot] salary_check経由ウェルカム
2. [User] 東京都 → 23区 → 急性期病院 → 外科系 → 夜勤ありOK → すぐ転職したい
3. [Bot] matching_preview: 5施設表示

**System Behavior Evaluation:**
- salary_check経由の専用ウェルカムメッセージ確認
- 外科系 + 急性期 + 23区は候補豊富
- 給与情報がマッチング結果に含まれるか

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Handoff: no
- Matching Quality: good
- Sub-area Coverage Issue: no

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** salary_check経由ユーザーには給与レンジをマッチング結果に含めると効果的。
**Retry Needed:** no
**Auditor Comment:**

---

### Case KW1-019
- **Prefecture:** 東京都
- **Sub-area:** 23区
- **Specific Location:** 品川区
- **Case Type:** adversarial
- **User Profile:** 不明
- **Entry Route:** 直接follow
- **Difficulty:** Hard

**Scenario:** AI consultation中に3回連続AIが失敗（OpenAI/Claude/Gemini全てタイムアウト）→ 自動handoff発動テスト。

**Conversation Flow:**
1. [Bot] Welcome → intake完了 → matching_preview表示
2. [User] "この施設について聞く"
3. [Bot] AI consultation開始
4. [User] 質問入力
5. [System] OpenAI GPT-4o-mini → timeout
6. [System] Claude Haiku → timeout
7. [System] Gemini Flash → timeout
8. [System] Workers AI → failure
9. [Bot] 1回目失敗メッセージ
10. [User] 再度質問
11. [System] 全AI再びfailure（×2回目）
12. [User] 再度質問
13. [System] 全AI failure（×3回目） → 自動handoff発動
14. [Bot] "申し訳ありません、直接スタッフがお答えします" → handoff

**System Behavior Evaluation:**
- 3回連続AI失敗で自動handoffが発動するか確認
- 各AIのフォールバックチェーン（OpenAI → Claude → Gemini → Workers AI）が正しく動くか
- 自動handoff後のSlack転送が正しく行われるか

**Results:**
- Drop-off risk: yes（AI失敗中の待ち時間）
- Reached Job Proposal: yes
- Reached Handoff: yes（自動）
- Matching Quality: good
- Sub-area Coverage Issue: no

**Failure Category:** OTHER
**Severity:** High
**Fix Proposal:** AI失敗時のフォールバックメッセージを改善。1回目の失敗時点で「直接相談する」ボタンを表示。
**Retry Needed:** no
**Auditor Comment:**

---

### Case KW1-020
- **Prefecture:** 東京都
- **Sub-area:** 23区
- **Specific Location:** 文京区
- **Case Type:** boundary
- **User Profile:** 36歳、急性期のICU経験。こだわりなし（facility_type）で検索。
- **Entry Route:** 直接follow
- **Difficulty:** Medium

**Scenario:** facility_typeで「こだわりなし」を選択した場合、il_departmentは表示されるのか。

**Conversation Flow:**
1. [Bot] Welcome
2. [User] 東京都 → 23区 → こだわりなし
3. [Bot] il_departmentは表示される?（「こだわりなし」は病院ではないのでスキップ?）
4. → il_workstyle表示
5. [User] 夜勤ありOK → すぐ転職したい
6. [Bot] matching_preview: 全カテゴリから5施設表示

**System Behavior Evaluation:**
- 「こだわりなし」選択時のil_department表示/スキップのロジック確認
- コード上「hospitals only」で診療科表示なので、「こだわりなし」ではスキップされるはず
- 全カテゴリから表示されるため、結果の多様性は高いが関連性は下がる

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Handoff: no
- Matching Quality: acceptable
- Sub-area Coverage Issue: no

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** 「こだわりなし」選択時は結果の多様性を担保しつつ、ユーザーの経験（ICU）を活かせる提案があると良い。
**Retry Needed:** no
**Auditor Comment:**

---

## 多摩 Cases (KW1-021 ~ KW1-035)

---

### Case KW1-021
- **Prefecture:** 東京都
- **Sub-area:** 多摩
- **Specific Location:** 八王子市
- **Case Type:** standard
- **User Profile:** 34歳、急性期の内科系。日勤のみ希望。
- **Entry Route:** 直接follow
- **Difficulty:** Easy

**Scenario:** 八王子市は AREA_CITY_MAP の9都市に含まれている。正常にマッチングされるか。

**Conversation Flow:**
1. [Bot] Welcome
2. [User] 東京都 → 多摩地域 → 急性期病院 → 内科系 → 日勤のみ → 良い所あれば
3. [Bot] matching_preview: 5施設表示（八王子市の施設が含まれるはず）

**System Behavior Evaluation:**
- 八王子市はAREA_CITY_MAPに含まれるため正常動作
- 八王子は多摩最大の都市で医療機関も多い
- SQL: `address LIKE '%八王子市%'` が正しくヒットする

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Handoff: no
- Matching Quality: good
- Sub-area Coverage Issue: no

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** N/A
**Retry Needed:** no
**Auditor Comment:**

---

### Case KW1-022
- **Prefecture:** 東京都
- **Sub-area:** 多摩
- **Specific Location:** 青梅市
- **Case Type:** boundary
- **User Profile:** 42歳、慢性期病院で長年勤務。通勤は青梅線沿線希望。
- **Entry Route:** 直接follow
- **Difficulty:** Hard

**Scenario:** 青梅市はAREA_CITY_MAPに含まれていない。「多摩地域」を選んでも青梅市の施設がヒットしない。

**Conversation Flow:**
1. [Bot] Welcome
2. [User] 東京都 → 多摩地域 → 慢性期病院 → 内科系 → 日勤のみ → 良い所あれば
3. [Bot] matching_preview: 5施設表示 → **青梅市の施設は含まれない**
4. [User] 「青梅市の病院はありませんか？」
5. [Bot] AI consultation: AIは回答するが検索条件にAREA_CITY_MAPの制約があることは知らない

**System Behavior Evaluation:**
- **BUG確認**: AREA_CITY_MAP tokyo_tama に青梅市がない
- 青梅市には青梅市立総合病院等の医療機関がDBに存在するはず
- SQL `address LIKE '%青梅市%'` が生成されないため、結果から除外される
- ユーザーは「多摩地域」を正しく選択したのに青梅の施設が出ない → GEO_LOCK

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes（ただし青梅市の施設なし）
- Reached Handoff: no
- Matching Quality: poor
- Sub-area Coverage Issue: yes — 青梅市がAREA_CITY_MAP tokyo_tamaに未登録

**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** AREA_CITY_MAP tokyo_tama に青梅市を追加。多摩地域の全26市3町1村をカバーすべき。
**Retry Needed:** yes
**Auditor Comment:**

---

### Case KW1-023
- **Prefecture:** 東京都
- **Sub-area:** 多摩
- **Specific Location:** 国分寺市
- **Case Type:** boundary
- **User Profile:** 29歳、訪問看護。日勤のみ。国分寺駅周辺希望。
- **Entry Route:** area_page→LINE
- **Difficulty:** Hard

**Scenario:** 国分寺市もAREA_CITY_MAPに未登録。中央線沿線で利便性の高い地域だが結果に含まれない。

**Conversation Flow:**
1. [Bot] area_page経由ウェルカム
2. [User] 東京都 → 多摩地域 → 訪問看護 → 日勤のみ → 良い所あれば
3. [Bot] matching_preview: 5施設表示 → **国分寺市の施設は含まれない**

**System Behavior Evaluation:**
- **BUG確認**: 国分寺市がAREA_CITY_MAP tokyo_tamaに未登録
- 国分寺市の訪問看護ステーションはDBに存在するはず
- ユーザーには「なぜ国分寺が出ないのか」分からない

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes（ただし国分寺市なし）
- Reached Handoff: no
- Matching Quality: poor
- Sub-area Coverage Issue: yes — 国分寺市がAREA_CITY_MAP tokyo_tamaに未登録

**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** AREA_CITY_MAP tokyo_tama に国分寺市を追加。
**Retry Needed:** yes
**Auditor Comment:**

---

### Case KW1-024
- **Prefecture:** 東京都
- **Sub-area:** 多摩
- **Specific Location:** 西東京市
- **Case Type:** boundary
- **User Profile:** 31歳、クリニック勤務。パート希望。西東京市在住。
- **Entry Route:** 直接follow
- **Difficulty:** Hard

**Scenario:** 西東京市もAREA_CITY_MAP未登録。2001年に保谷市・田無市合併で誕生した比較的新しい市。

**Conversation Flow:**
1. [Bot] Welcome
2. [User] 東京都 → 多摩地域 → クリニック → 良い所あれば
3. [Bot] matching_preview: 5施設表示 → **西東京市の施設は含まれない**
4. [User] "西東京市のクリニックを探しています"
5. [Bot] AI consultation回答 → 検索は変わらない

**System Behavior Evaluation:**
- **BUG確認**: 西東京市がAREA_CITY_MAP tokyo_tamaに未登録
- 西東京市は人口20万超の中規模都市でクリニック多数
- 練馬区に隣接しており、23区選択なら近隣施設がヒットするが、多摩選択ではゼロ

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes（ただし西東京市なし）
- Reached Handoff: no
- Matching Quality: poor
- Sub-area Coverage Issue: yes — 西東京市がAREA_CITY_MAP tokyo_tamaに未登録

**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** AREA_CITY_MAP tokyo_tama に西東京市を追加。
**Retry Needed:** yes
**Auditor Comment:**

---

### Case KW1-025
- **Prefecture:** 東京都
- **Sub-area:** 多摩
- **Specific Location:** 小平市
- **Case Type:** boundary
- **User Profile:** 37歳、精神科専門。小平市の精神科病院希望。
- **Entry Route:** 直接follow
- **Difficulty:** Hard

**Scenario:** 小平市もAREA_CITY_MAP未登録。多摩地域には精神科病院が集中しており、小平市にも存在するはず。

**Conversation Flow:**
1. [Bot] Welcome
2. [User] 東京都 → 多摩地域 → 慢性期病院 → 精神科 → 日勤のみ → すぐ転職したい
3. [Bot] matching_preview: 5施設表示 → **小平市の施設は含まれない**

**System Behavior Evaluation:**
- **BUG確認**: 小平市がAREA_CITY_MAP tokyo_tamaに未登録
- 小平市には国立精神・神経医療研究センター等の有名施設がある
- 精神科 + 多摩は本来マッチしやすいが、9都市限定で大幅に候補が削られる

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes（ただし小平市なし）
- Reached Handoff: no
- Matching Quality: poor
- Sub-area Coverage Issue: yes — 小平市がAREA_CITY_MAP tokyo_tamaに未登録

**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** AREA_CITY_MAP tokyo_tama に小平市を追加。
**Retry Needed:** yes
**Auditor Comment:**

---

### Case KW1-026
- **Prefecture:** 東京都
- **Sub-area:** 多摩
- **Specific Location:** 東村山市
- **Case Type:** boundary
- **User Profile:** 44歳、回復期リハビリ経験。東村山市在住。
- **Entry Route:** 直接follow
- **Difficulty:** Hard

**Scenario:** 東村山市もAREA_CITY_MAP未登録。

**Conversation Flow:**
1. [Bot] Welcome
2. [User] 東京都 → 多摩地域 → 回復期病院 → リハビリ → 日勤のみ → 良い所あれば
3. [Bot] matching_preview: **東村山市の施設は含まれない**

**System Behavior Evaluation:**
- **BUG確認**: 東村山市がAREA_CITY_MAP tokyo_tamaに未登録
- 東村山市の回復期病院がDBにあっても検索対象外
- 近隣の府中市・日野市（登録済み）の施設は出る可能性あり

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes（ただし東村山市なし）
- Reached Handoff: no
- Matching Quality: poor
- Sub-area Coverage Issue: yes — 東村山市がAREA_CITY_MAP tokyo_tamaに未登録

**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** AREA_CITY_MAP tokyo_tama に東村山市を追加。
**Retry Needed:** yes
**Auditor Comment:**

---

### Case KW1-027
- **Prefecture:** 東京都
- **Sub-area:** 多摩
- **Specific Location:** 清瀬市
- **Case Type:** boundary
- **User Profile:** 26歳、急性期外科。清瀬市在住。
- **Entry Route:** 広告→LINE
- **Difficulty:** Hard

**Scenario:** 清瀬市もAREA_CITY_MAP未登録。結核療養所の歴史があり医療機関が集中する地域。

**Conversation Flow:**
1. [Bot] Meta広告ウェルカム
2. [User] 東京都 → 多摩地域 → 急性期病院 → 外科系 → 夜勤ありOK → すぐ転職したい
3. [Bot] matching_preview: **清瀬市の施設は含まれない**

**System Behavior Evaluation:**
- **BUG確認**: 清瀬市がAREA_CITY_MAP tokyo_tamaに未登録
- 清瀬市は医療施設密度が高い地域だが全て検索対象外
- Meta広告から来たユーザーの期待値が高い中で結果が不十分

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes（ただし清瀬市なし）
- Reached Handoff: no
- Matching Quality: poor
- Sub-area Coverage Issue: yes — 清瀬市がAREA_CITY_MAP tokyo_tamaに未登録

**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** AREA_CITY_MAP tokyo_tama に清瀬市を追加。
**Retry Needed:** yes
**Auditor Comment:**

---

### Case KW1-028
- **Prefecture:** 東京都
- **Sub-area:** 多摩
- **Specific Location:** 立川市
- **Case Type:** standard
- **User Profile:** 30歳、急性期循環器。立川駅通勤圏。
- **Entry Route:** LP→LINE
- **Difficulty:** Easy

**Scenario:** 立川市はAREA_CITY_MAPに含まれている。正常フローの確認。

**Conversation Flow:**
1. [Bot] LP経由ウェルカム
2. [User] 東京都 → 多摩地域 → 急性期病院 → 循環器 → 夜勤ありOK → すぐ転職したい
3. [Bot] matching_preview: 5施設表示（立川市を含む）
4. [User] "直接相談する"
5. [Bot] handoff_phone_check → phone OK → time → handoff

**System Behavior Evaluation:**
- 立川市は登録済みで正常動作
- 循環器 + 急性期 + 多摩の組み合わせ: 立川の大病院がヒットするはず
- handoffまでの完全フロー確認

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Handoff: yes
- Matching Quality: good
- Sub-area Coverage Issue: no

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** N/A
**Retry Needed:** no
**Auditor Comment:**

---

### Case KW1-029
- **Prefecture:** 東京都
- **Sub-area:** 多摩
- **Specific Location:** 武蔵野市（三鷹市隣接）
- **Case Type:** standard
- **User Profile:** 28歳、訪問看護志望。武蔵野市/三鷹市エリア。
- **Entry Route:** 直接follow
- **Difficulty:** Easy

**Scenario:** 武蔵野市・三鷹市は両方ともAREA_CITY_MAPに登録済み。

**Conversation Flow:**
1. [Bot] Welcome
2. [User] 東京都 → 多摩地域 → 訪問看護 → 日勤のみ → 良い所あれば
3. [Bot] matching_preview: 武蔵野市/三鷹市の訪問看護が含まれる

**System Behavior Evaluation:**
- 武蔵野市・三鷹市は登録済み、正常動作
- 訪問看護ステーションは住宅地に多く、この地域にも複数あるはず

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Handoff: no
- Matching Quality: good
- Sub-area Coverage Issue: no

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** N/A
**Retry Needed:** no
**Auditor Comment:**

---

### Case KW1-030
- **Prefecture:** 東京都
- **Sub-area:** 多摩
- **Specific Location:** 東久留米市
- **Case Type:** boundary
- **User Profile:** 39歳、介護施設勤務。東久留米市在住。
- **Entry Route:** 直接follow
- **Difficulty:** Hard

**Scenario:** 東久留米市はAREA_CITY_MAP未登録。

**Conversation Flow:**
1. [Bot] Welcome
2. [User] 東京都 → 多摩地域 → 介護施設 → 日勤のみ → 良い所あれば
3. [Bot] matching_preview: **東久留米市の施設は含まれない**

**System Behavior Evaluation:**
- **BUG確認**: 東久留米市がAREA_CITY_MAP tokyo_tamaに未登録
- 介護施設は住宅地に多く東久留米市にも存在するはず

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes（ただし東久留米市なし）
- Reached Handoff: no
- Matching Quality: poor
- Sub-area Coverage Issue: yes — 東久留米市がAREA_CITY_MAP tokyo_tamaに未登録

**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** AREA_CITY_MAP tokyo_tama に東久留米市を追加。
**Retry Needed:** yes
**Auditor Comment:**

---

### Case KW1-031
- **Prefecture:** 東京都
- **Sub-area:** 多摩
- **Specific Location:** 稲城市
- **Case Type:** boundary
- **User Profile:** 33歳、クリニック希望。稲城市在住。
- **Entry Route:** 直接follow
- **Difficulty:** Hard

**Scenario:** 稲城市はAREA_CITY_MAP未登録。川崎市麻生区に隣接し、通勤圏が重なる。

**Conversation Flow:**
1. [Bot] Welcome
2. [User] 東京都 → 多摩地域 → クリニック → まだ情報収集
3. [Bot] matching_preview: **稲城市のクリニックは含まれない**

**System Behavior Evaluation:**
- **BUG確認**: 稲城市がAREA_CITY_MAP tokyo_tamaに未登録
- 稲城市は多摩ニュータウンの一部であり、医療施設は存在する

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes（ただし稲城市なし）
- Reached Handoff: no
- Matching Quality: poor
- Sub-area Coverage Issue: yes — 稲城市がAREA_CITY_MAP tokyo_tamaに未登録

**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** AREA_CITY_MAP tokyo_tama に稲城市を追加。
**Retry Needed:** yes
**Auditor Comment:**

---

### Case KW1-032
- **Prefecture:** 東京都
- **Sub-area:** 多摩
- **Specific Location:** 町田市
- **Case Type:** standard
- **User Profile:** 35歳、回復期リハビリ。町田市在住。
- **Entry Route:** LP→LINE
- **Difficulty:** Easy

**Scenario:** 町田市はAREA_CITY_MAPに登録済み。正常動作確認。

**Conversation Flow:**
1. [Bot] LP経由ウェルカム
2. [User] 東京都 → 多摩地域 → 回復期病院 → リハビリ → 日勤のみ → すぐ転職したい
3. [Bot] matching_preview: 町田市を含む5施設
4. [User] "もっと求人を見る"
5. [Bot] 追加施設表示

**System Behavior Evaluation:**
- 町田市は登録済み、正常動作
- 町田市は神奈川県との境界で、相模原市の施設も近いが多摩限定なので出ない

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Handoff: no
- Matching Quality: good
- Sub-area Coverage Issue: no

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** 町田市選択時に近隣の相模原市の施設も提案できると良い。
**Retry Needed:** no
**Auditor Comment:**

---

### Case KW1-033
- **Prefecture:** 東京都
- **Sub-area:** 多摩
- **Specific Location:** あきる野市
- **Case Type:** boundary
- **User Profile:** 48歳、慢性期内科。あきる野市在住。
- **Entry Route:** 直接follow
- **Difficulty:** Hard

**Scenario:** あきる野市はAREA_CITY_MAP未登録。西多摩地域の医療過疎エリア。

**Conversation Flow:**
1. [Bot] Welcome
2. [User] 東京都 → 多摩地域 → 慢性期病院 → 内科系 → 日勤のみ → 良い所あれば
3. [Bot] matching_preview: **あきる野市の施設は含まれない**
4. [User] "あきる野市周辺の病院はありますか？"
5. [Bot] AI consultation回答 → DB検索は変わらない

**System Behavior Evaluation:**
- **BUG確認**: あきる野市がAREA_CITY_MAP tokyo_tamaに未登録
- 西多摩地域（あきる野/福生/羽村/瑞穂/日の出/檜原/奥多摩）は全て未登録
- この地域の住民は全員、多摩地域選択で結果が出ない

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes（ただしあきる野市なし）
- Reached Handoff: no
- Matching Quality: poor
- Sub-area Coverage Issue: yes — あきる野市がAREA_CITY_MAP tokyo_tamaに未登録

**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** AREA_CITY_MAP tokyo_tama に西多摩地域全体を追加。
**Retry Needed:** yes
**Auditor Comment:**

---

### Case KW1-034
- **Prefecture:** 東京都
- **Sub-area:** 多摩
- **Specific Location:** 多摩市
- **Case Type:** standard
- **User Profile:** 27歳、急性期小児科。多摩市在住。
- **Entry Route:** 広告→LINE
- **Difficulty:** Easy

**Scenario:** 多摩市はAREA_CITY_MAPに登録済み。小児科 + 急性期の標準フロー。

**Conversation Flow:**
1. [Bot] Meta広告ウェルカム
2. [User] 東京都 → 多摩地域 → 急性期病院 → 小児科 → 夜勤ありOK → すぐ転職したい
3. [Bot] matching_preview: 多摩市含む結果

**System Behavior Evaluation:**
- 多摩市は登録済み、正常動作
- 小児科 + 急性期 + 多摩: 候補は限定的だが存在するはず

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Handoff: no
- Matching Quality: acceptable
- Sub-area Coverage Issue: no

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** N/A
**Retry Needed:** no
**Auditor Comment:**

---

### Case KW1-035
- **Prefecture:** 東京都
- **Sub-area:** 多摩
- **Specific Location:** 福生市
- **Case Type:** adversarial
- **User Profile:** 55歳、准看護師。福生市在住。
- **Entry Route:** 直接follow
- **Difficulty:** Hard

**Scenario:** 福生市はAREA_CITY_MAP未登録。さらに「准看護師」という条件がintakeで指定できない。

**Conversation Flow:**
1. [Bot] Welcome
2. [User] 東京都 → 多摩地域 → クリニック → まだ情報収集
3. [Bot] matching_preview: **福生市の施設なし** + 正看護師前提の結果
4. [User] "准看護師でも大丈夫ですか？"
5. [Bot] AI consultation: 准看護師について一般的な回答

**System Behavior Evaluation:**
- **BUG二重**: (1) 福生市がAREA_CITY_MAP未登録 (2) 准看護師/正看護師の区別がintakeにない
- 准看護師の求人条件が異なる（給与・対応施設）が、botはこの違いを反映できない

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes（ただし福生市なし・准看護師非対応）
- Reached Handoff: no
- Matching Quality: poor
- Sub-area Coverage Issue: yes — 福生市がAREA_CITY_MAP tokyo_tamaに未登録

**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** (1) AREA_CITY_MAP tokyo_tamaに福生市追加 (2) 資格種別（正看/准看）のintake質問追加を検討
**Retry Needed:** yes
**Auditor Comment:**

---

## どこでもOK Cases (KW1-036 ~ KW1-040)

---

### Case KW1-036
- **Prefecture:** 東京都
- **Sub-area:** どこでもOK
- **Specific Location:** N/A（東京全域のはず）
- **Case Type:** boundary
- **User Profile:** 30歳、急性期外科系。勤務地にこだわりなし。
- **Entry Route:** 直接follow
- **Difficulty:** Hard

**Scenario:** 「どこでもOK」を選択するとtokyo_included発動。結果に横浜市・川崎市が混入するバグの確認。

**Conversation Flow:**
1. [Bot] Welcome
2. [User] 東京都 → どこでもOK → 急性期病院 → 外科系 → 夜勤ありOK → すぐ転職したい
3. [Bot] matching_preview: 5施設表示 → **横浜市/川崎市の施設が混入する可能性**

**System Behavior Evaluation:**
- **BUG確認**: tokyo_included の AREA_CITY_MAP に横浜市・川崎市が含まれている
- ユーザーは「東京都」→「どこでもOK」を選んだのに神奈川の施設が出る
- さらに、新宿区/渋谷区/品川区/世田谷区/大田区の5区+横浜市/川崎市の7地域しかない
- 足立区、練馬区、板橋区等の大半の区が検索対象外

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes（ただし結果が不正確）
- Reached Handoff: no
- Matching Quality: poor
- Sub-area Coverage Issue: yes — tokyo_includedに横浜市/川崎市混入 + 23区の大半が未カバー

**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** tokyo_included のAREA_CITY_MAPを修正: (1)横浜市/川崎市を削除 (2)23区全て+多摩全市を含める。またはフィルタなし（東京都全体）にする。
**Retry Needed:** yes
**Auditor Comment:**

---

### Case KW1-037
- **Prefecture:** 東京都
- **Sub-area:** どこでもOK
- **Specific Location:** N/A
- **Case Type:** boundary
- **User Profile:** 25歳、クリニック希望。東京ならどこでも。
- **Entry Route:** 広告→LINE
- **Difficulty:** Hard

**Scenario:** 「どこでもOK」+クリニックで候補数表示を確認。AREA_PREF_MAPがnull → 全24,488件がカウントされるバグ。

**Conversation Flow:**
1. [Bot] Meta広告ウェルカム: "**24,488件**の医療機関の中から..."（全件カウントされる可能性）
2. [User] 東京都 → どこでもOK → クリニック → まだ情報収集
3. [Bot] matching_preview: 7地域（新宿/渋谷/品川/世田谷/大田/横浜/川崎）からのみ5件

**System Behavior Evaluation:**
- **BUG確認**: countCandidatesD1でtokyo_includedのAREA_PREF_MAPがnull
- nullの場合フィルタなし → 全24,488件がカウントされてウェルカムメッセージに表示
- 実際の検索結果は7地域限定 → カウントと実結果の乖離が激しい
- 「24,488件からぴったりの職場を」と言いつつ7地域しか出ないのは詐欺的

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes（ただし7地域限定）
- Reached Handoff: no
- Matching Quality: poor
- Sub-area Coverage Issue: yes — 候補数と検索範囲の不一致

**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** (1) AREA_PREF_MAPにtokyo_includedの正しいprefを設定 (2) tokyo_includedのAREA_CITY_MAPを修正 (3) countとsearch対象を一致させる
**Retry Needed:** yes
**Auditor Comment:**

---

### Case KW1-038
- **Prefecture:** 東京都
- **Sub-area:** どこでもOK
- **Specific Location:** N/A
- **Case Type:** adversarial
- **User Profile:** 28歳、訪問看護。「どこでもOK」選択後に結果を見て困惑。
- **Entry Route:** 直接follow
- **Difficulty:** Hard

**Scenario:** 「どこでもOK」で横浜の施設が出て、「東京を選んだのに？」と問い合わせ。

**Conversation Flow:**
1. [Bot] Welcome
2. [User] 東京都 → どこでもOK → 訪問看護 → 日勤のみ → 良い所あれば
3. [Bot] matching_preview: 5施設中に「横浜市○○区」の施設が含まれる
4. [User] "東京を選んだのに横浜の施設が出ているんですが？"
5. [Bot] AI consultation: AIが混乱の原因を説明できない（バグを知らない）
6. [User] 不信感 → 離脱

**System Behavior Evaluation:**
- **BUG確認**: ユーザーが実際にバグに気づくケース
- AIは「横浜が出ている理由」を説明できない（バグの存在を知らない）
- ユーザーの信頼を大きく損なう
- この時点でhandoff提案すべきだが、AIが問題を認識できない

**Results:**
- Drop-off risk: yes（信頼喪失）
- Reached Job Proposal: yes（ただし不正確）
- Reached Handoff: no
- Matching Quality: poor
- Sub-area Coverage Issue: yes — 横浜市の施設が東京検索に混入

**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** tokyo_includedから横浜市/川崎市を削除。AI相談で「結果がおかしい」系の指摘があった場合はhandoff提案を優先。
**Retry Needed:** yes
**Auditor Comment:**

---

### Case KW1-039
- **Prefecture:** 東京都
- **Sub-area:** どこでもOK
- **Specific Location:** N/A
- **Case Type:** boundary
- **User Profile:** 40歳、介護施設希望。多摩在住だが23区も可。
- **Entry Route:** 直接follow
- **Difficulty:** Medium

**Scenario:** 多摩在住で23区も含めて広く探したい人が「どこでもOK」を選ぶが、実際には5区+横浜/川崎しか検索されない。

**Conversation Flow:**
1. [Bot] Welcome
2. [User] 東京都 → どこでもOK → 介護施設 → パート・非常勤 → 良い所あれば
3. [Bot] matching_preview: 新宿/渋谷/品川/世田谷/大田/横浜/川崎の施設のみ
4. [User] "練馬区や板橋区の施設も見たいです"
5. [Bot] AI consultation回答 → 検索範囲は変わらない

**System Behavior Evaluation:**
- 「どこでもOK」は本来「東京全域」の意味だが、実際は7地域限定
- 多摩の施設が一切出ない + 23区も5区のみ
- ユーザーの「どこでもOK」の期待と実結果の落差が大きい

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes（ただし限定地域のみ）
- Reached Handoff: no
- Matching Quality: poor
- Sub-area Coverage Issue: yes — 「どこでもOK」なのに7地域限定

**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** tokyo_includedは東京都全域（全23区+全多摩市）をカバーすべき。AREA_PREF_MAP='東京都'での全検索が最もシンプル。
**Retry Needed:** yes
**Auditor Comment:**

---

### Case KW1-040
- **Prefecture:** 東京都
- **Sub-area:** どこでもOK
- **Specific Location:** N/A
- **Case Type:** adversarial
- **User Profile:** 不明
- **Entry Route:** 直接follow
- **Difficulty:** Hard

**Scenario:** 「どこでもOK」→ マッチング → 「条件を変えて探す」→ 23区に変更 → 再マッチング。結果の変化を検証。

**Conversation Flow:**
1. [Bot] Welcome
2. [User] 東京都 → どこでもOK → 急性期病院 → 内科系 → 夜勤ありOK → すぐ転職したい
3. [Bot] matching_preview: 7地域限定の結果（横浜/川崎混入）
4. [User] "条件を変えて探す"
5. [Bot] intake再開?
6. [User] 東京都 → 23区 → 急性期病院 → 内科系 → 夜勤ありOK → すぐ転職したい
7. [Bot] matching_preview: 23区全域からの結果

**System Behavior Evaluation:**
- 「どこでもOK」→ 23区への変更で結果が大幅に改善する
- 23区は全23区がカバーされるため、「どこでもOK」より良い結果になる矛盾
- セッション状態のリセットが正しく行われるか

**Results:**
- Drop-off risk: no（条件変更で改善）
- Reached Job Proposal: yes
- Reached Handoff: no
- Matching Quality: good（2回目）
- Sub-area Coverage Issue: yes — 1回目の「どこでもOK」が23区より狭い

**Failure Category:** GEO_LOCK
**Severity:** High
**Fix Proposal:** tokyo_includedの検索範囲を東京都全域に修正。
**Retry Needed:** no
**Auditor Comment:**

---

## 越境 Cases (KW1-041 ~ KW1-050)

---

### Case KW1-041
- **Prefecture:** 東京都 → 神奈川県
- **Sub-area:** 23区（大田区）→ 横浜市
- **Specific Location:** 大田区在住、横浜市も通勤圏
- **Case Type:** standard
- **User Profile:** 29歳、急性期外科。大田区在住で横浜も通勤可能。
- **Entry Route:** LP→LINE
- **Difficulty:** Medium

**Scenario:** 最初に東京23区で検索 → 結果確認後「条件を変えて探す」→ 神奈川県に変更。

**Conversation Flow:**
1. [Bot] LP経由ウェルカム
2. [User] 東京都 → 23区 → 急性期病院 → 外科系 → 夜勤ありOK → すぐ転職したい
3. [Bot] matching_preview: 23区の結果表示
4. [User] "条件を変えて探す"
5. [Bot] intake再開
6. [User] 神奈川県 → 横浜市 → 急性期病院 → 外科系 → 夜勤ありOK → すぐ転職したい
7. [Bot] matching_preview: 横浜市の結果表示

**System Behavior Evaluation:**
- 東京→神奈川への県変更フローが正しく動くか
- セッション状態のリセットが正しく行われるか
- 2回目の検索で前回の条件が残っていないか確認

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Handoff: no
- Matching Quality: good
- Sub-area Coverage Issue: no

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** 「東京都と神奈川県の両方で探す」オプションがあると便利。
**Retry Needed:** no
**Auditor Comment:**

---

### Case KW1-042
- **Prefecture:** 東京都 → 千葉県
- **Sub-area:** 23区（江戸川区）→ 千葉県
- **Specific Location:** 江戸川区在住、市川市/船橋市が通勤圏
- **Case Type:** standard
- **User Profile:** 33歳、回復期リハビリ。江戸川区在住で千葉方面も可。
- **Entry Route:** 直接follow
- **Difficulty:** Medium

**Scenario:** 23区で検索後に千葉県に切り替える典型的な越境パターン。

**Conversation Flow:**
1. [Bot] Welcome
2. [User] 東京都 → 23区 → 回復期病院 → リハビリ → 日勤のみ → 良い所あれば
3. [Bot] matching_preview表示
4. [User] "千葉県の求人も見たいです"（フリーテキスト）
5. [Bot] AI consultation: 千葉の情報を回答するが検索変更はできない
6. [User] "条件を変えて探す"
7. [Bot] intake再開
8. [User] 千葉県 → ... → matching_preview

**System Behavior Evaluation:**
- フリーテキストでの県変更要望にAI consultationが対応するが、検索変更不可
- 「条件を変えて探す」経由で千葉に切り替え可能
- 東京+千葉の同時検索はできない

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Handoff: no
- Matching Quality: acceptable
- Sub-area Coverage Issue: no

**Failure Category:** REGION_EXPANSION_FAIL
**Severity:** Medium
**Fix Proposal:** 越境ニーズが高い組み合わせ（江戸川↔市川、大田↔川崎等）を自動提案する機能追加。
**Retry Needed:** no
**Auditor Comment:**

---

### Case KW1-043
- **Prefecture:** 東京都 → 埼玉県
- **Sub-area:** 23区（練馬区）→ 埼玉県
- **Specific Location:** 練馬区在住、和光市/朝霞市が通勤圏
- **Case Type:** standard
- **User Profile:** 36歳、急性期内科。練馬区在住で埼玉南部も可。
- **Entry Route:** 広告→LINE
- **Difficulty:** Medium

**Scenario:** 東京23区 → 埼玉県への越境。練馬区から東武東上線・有楽町線で和光/朝霞方面。

**Conversation Flow:**
1. [Bot] Meta広告ウェルカム
2. [User] 東京都 → 23区 → 急性期病院 → 内科系 → 日勤のみ → 良い所あれば
3. [Bot] matching_preview表示
4. [User] "条件を変えて探す"
5. [User] 埼玉県 → sub-area選択 → 急性期病院 → 内科系 → 日勤のみ → 良い所あれば
6. [Bot] matching_preview: 埼玉の結果

**System Behavior Evaluation:**
- 東京→埼玉の切り替えフロー確認
- 埼玉のsub-area構造がどうなっているか（さいたま市/川口市等）

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Handoff: no
- Matching Quality: good
- Sub-area Coverage Issue: no

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** 練馬区選択時に「埼玉南部も含めて探しますか？」の提案があると良い。
**Retry Needed:** no
**Auditor Comment:**

---

### Case KW1-044
- **Prefecture:** 東京都（多摩）→ 神奈川県
- **Sub-area:** 多摩（町田市）→ 相模原市
- **Specific Location:** 町田市在住、相模原市が生活圏
- **Case Type:** boundary
- **User Profile:** 31歳、訪問看護。町田市在住。相模原市橋本にも通勤可能。
- **Entry Route:** 直接follow
- **Difficulty:** Medium

**Scenario:** 町田市と相模原市は隣接し生活圏が重なるが、都県をまたぐため同時検索不可。

**Conversation Flow:**
1. [Bot] Welcome
2. [User] 東京都 → 多摩地域 → 訪問看護 → 日勤のみ → 良い所あれば
3. [Bot] matching_preview: 多摩9市からの結果（町田含む）
4. [User] "相模原市も見たいです"
5. [Bot] AI consultation: 相模原について回答するが検索変更不可
6. [User] "条件を変えて探す"
7. [User] 神奈川県 → 相模原市 → 訪問看護 → 日勤のみ → 良い所あれば
8. [Bot] matching_preview: 相模原市の結果

**System Behavior Evaluation:**
- 町田↔相模原は典型的な越境パターン
- 2回の検索が必要で手間がかかる
- 町田市の結果に相模原市が含まれないのは正しいが、ユーザーのニーズには合わない

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Handoff: no
- Matching Quality: acceptable
- Sub-area Coverage Issue: no（仕様通りだが不便）

**Failure Category:** REGION_EXPANSION_FAIL
**Severity:** Medium
**Fix Proposal:** 隣接自治体の自動提案機能。町田市選択時に「相模原市も含めますか？」
**Retry Needed:** no
**Auditor Comment:**

---

### Case KW1-045
- **Prefecture:** 東京都 → その他の地域
- **Sub-area:** N/A
- **Specific Location:** 東京在住、地方への転居検討
- **Case Type:** boundary
- **User Profile:** 28歳、急性期。東京から地方移住を検討。
- **Entry Route:** 直接follow
- **Difficulty:** Medium

**Scenario:** il_areaで「その他の地域」を選択した場合の挙動確認。

**Conversation Flow:**
1. [Bot] Welcome
2. [User] その他の地域 を選択
3. [Bot] → 対応していない旨のメッセージ? or handoff提案?

**System Behavior Evaluation:**
- 「その他の地域」の選択肢が存在するが、DBには関東4県のデータしかない
- 選択後のフロー: エラーメッセージか、handoff提案か
- ユーザーの期待（全国対応）と実態（関東のみ）のギャップ

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: no
- Reached Handoff: no（提案があれば可能）
- Matching Quality: N/A
- Sub-area Coverage Issue: no（仕様の範囲外）

**Failure Category:** UX_DROP
**Severity:** Medium
**Fix Proposal:** 「その他の地域」選択時に「現在は東京・神奈川・千葉・埼玉に対応しています。直接ご相談いただければ全国の求人もお探しします」とhandoff提案。
**Retry Needed:** no
**Auditor Comment:**

---

### Case KW1-046
- **Prefecture:** 東京都
- **Sub-area:** 23区（足立区）→ 埼玉県
- **Specific Location:** 足立区在住、草加市/川口市が隣接
- **Case Type:** standard
- **User Profile:** 34歳、クリニック。足立区在住で埼玉南部も可。
- **Entry Route:** blog→LINE
- **Difficulty:** Medium

**Scenario:** 足立区→埼玉南部の越境。23区で結果確認後に埼玉へ。

**Conversation Flow:**
1. [Bot] blog経由ウェルカム
2. [User] 東京都 → 23区 → クリニック → 良い所あれば
3. [Bot] matching_preview: 23区のクリニック
4. [User] "条件を変えて探す"
5. [User] 埼玉県 → 川口市方面 → クリニック → 良い所あれば
6. [Bot] matching_preview: 埼玉の結果

**System Behavior Evaluation:**
- 足立区↔川口市/草加市は電車1本の距離
- 2回検索が必要だが、フロー自体は正常動作するはず

**Results:**
- Drop-off risk: no
- Reached Job Proposal: yes
- Reached Handoff: no
- Matching Quality: good
- Sub-area Coverage Issue: no

**Failure Category:** NONE
**Severity:** Low
**Fix Proposal:** 足立区・葛飾区選択時に埼玉南部の提案があると良い。
**Retry Needed:** no
**Auditor Comment:**

---

### Case KW1-047
- **Prefecture:** 東京都
- **Sub-area:** 23区 → 多摩
- **Specific Location:** 中野区在住、多摩方面も検討
- **Case Type:** adversarial
- **User Profile:** 35歳、急性期。中野区在住だが多摩の自然環境にも興味。
- **Entry Route:** 直接follow
- **Difficulty:** Medium

**Scenario:** 23区で検索 → 多摩に変更 → 多摩の9都市限定バグに遭遇。

**Conversation Flow:**
1. [Bot] Welcome
2. [User] 東京都 → 23区 → 急性期病院 → 内科系 → 夜勤ありOK → 良い所あれば
3. [Bot] matching_preview: 23区の結果（良好）
4. [User] "条件を変えて探す"
5. [User] 東京都 → 多摩地域 → 急性期病院 → 内科系 → 夜勤ありOK → 良い所あれば
6. [Bot] matching_preview: **9都市限定の結果** → 23区より候補が少ない?

**System Behavior Evaluation:**
- 23区→多摩への切り替えで、多摩の9都市限定バグが発露
- 23区は全23区カバーだが、多摩は9/26市のみ
- 同じ東京都内なのに検索品質に大きな格差がある

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes
- Reached Handoff: no
- Matching Quality: poor（多摩）
- Sub-area Coverage Issue: yes — 多摩9都市限定

**Failure Category:** GEO_LOCK
**Severity:** High
**Fix Proposal:** 多摩のAREA_CITY_MAPを全26市3町1村に拡張。
**Retry Needed:** yes
**Auditor Comment:**

---

### Case KW1-048
- **Prefecture:** 東京都（多摩）→ 千葉県
- **Sub-area:** 多摩 → 千葉
- **Specific Location:** 調布市在住、千葉にも検討拡大
- **Case Type:** adversarial
- **User Profile:** 27歳、回復期。調布市在住だが実家が千葉。
- **Entry Route:** LIFF session（LP診断からのキャリーオーバー）
- **Difficulty:** Hard

**Scenario:** LIFF sessionでarea=東京/workStyle=日勤/urgency=すぐがキャリーオーバーされた状態で入力。facility_typeから開始。

**Conversation Flow:**
1. [Bot] Welcome（LIFF session: area/workStyle/urgency がプリセット）
2. [Bot] il_facility_type表示（area/workStyle/urgencyスキップ）
3. [User] 回復期病院 → リハビリ
4. [Bot] matching_preview: 多摩? 23区? LIFF sessionのarea='東京'がどのsub-areaにマッピングされるか不明
5. [User] "千葉の実家近くも見たいです"
6. [Bot] AI consultation → 検索変更不可

**System Behavior Evaluation:**
- LIFF sessionからのキャリーオーバー: area='東京'がどのsub-areaに変換されるか
- sub-area未指定の場合のデフォルト挙動が不明
- キャリーオーバー後の条件変更（千葉追加）ができない

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes（ただしsub-area不明）
- Reached Handoff: no
- Matching Quality: acceptable
- Sub-area Coverage Issue: yes — LIFFからのarea変換ロジック不明

**Failure Category:** AMBIG_FAIL
**Severity:** High
**Fix Proposal:** LIFF sessionからのarea変換ロジックを明確化。sub-area未指定時はtokyo_includedにフォールバック? → バグの上塗り。tokyo_includedのバグ修正が先決。
**Retry Needed:** yes
**Auditor Comment:**

---

### Case KW1-049
- **Prefecture:** 東京都 → 神奈川県 → 東京都
- **Sub-area:** 23区 → 横浜市 → 多摩
- **Specific Location:** 品川区在住
- **Case Type:** adversarial
- **User Profile:** 30歳、急性期。迷って3回条件変更。
- **Entry Route:** 直接follow
- **Difficulty:** Hard

**Scenario:** 3回の条件変更でセッション状態の整合性をテスト。東京→神奈川→東京（多摩）。

**Conversation Flow:**
1. [Bot] Welcome
2. [User] 東京都 → 23区 → 急性期病院 → 循環器 → 夜勤ありOK → すぐ転職したい
3. [Bot] matching_preview: 23区の結果
4. [User] "条件を変えて探す"
5. [User] 神奈川県 → 横浜市 → 急性期病院 → 循環器 → 夜勤ありOK → すぐ転職したい
6. [Bot] matching_preview: 横浜の結果
7. [User] "条件を変えて探す"
8. [User] 東京都 → 多摩地域 → 急性期病院 → 循環器 → 夜勤ありOK → すぐ転職したい
9. [Bot] matching_preview: 多摩9都市の結果

**System Behavior Evaluation:**
- 3回の条件変更でセッション状態が正しくリセットされるか
- 前回のprefecture/sub-areaの値が残っていないか
- 3回目でtokyo_tamaの9都市限定バグに遭遇
- ユーザーの辛抱強さに依存する設計

**Results:**
- Drop-off risk: yes（3回の条件変更は離脱リスク大）
- Reached Job Proposal: yes
- Reached Handoff: no
- Matching Quality: poor（3回目、多摩限定）
- Sub-area Coverage Issue: yes — 多摩9都市限定

**Failure Category:** REENTRY_FAIL
**Severity:** High
**Fix Proposal:** (1) 多摩のAREA_CITY_MAP修正 (2) 条件変更UIを改善（変更したい項目だけ選べるように） (3) 2回目の条件変更時にhandoff提案
**Retry Needed:** yes
**Auditor Comment:**

---

### Case KW1-050
- **Prefecture:** 東京都
- **Sub-area:** 23区（葛飾区）
- **Specific Location:** 葛飾区在住、松戸市/三郷市も生活圏
- **Case Type:** adversarial
- **User Profile:** 不明
- **Entry Route:** 直接follow
- **Difficulty:** Hard

**Scenario:** 葛飾区在住ユーザーが意図的に矛盾した条件を入力。「クリニックなのに夜勤専従」を選ぼうとする。

**Conversation Flow:**
1. [Bot] Welcome
2. [User] 東京都 → 23区 → クリニック
3. [Bot] il_workstyleスキップ（クリニック='day'自動設定） → il_urgency表示
4. [User] 「夜勤専従で働きたいのですが」（フリーテキスト）
5. [Bot] unexpectedTextCount++、"もう一度お選びください" + il_urgencyクイックリプライ再表示
6. [User] 「クリニックで夜勤はないんですか？」（フリーテキスト）
7. [Bot] unexpectedTextCount++、同じ応答
8. [User] すぐ転職したい を選択（諦めてボタン押下）
9. [Bot] matching_preview: 日勤クリニックの結果

**System Behavior Evaluation:**
- クリニック選択時にworkstyleが自動的に'day'になるため、夜勤専従の要望が反映されない
- フリーテキストでの要望は完全に無視される（intake中なのでAI consultationに入らない）
- 実際には夜間診療のクリニックや美容クリニック（夜間営業）も存在するが、この分類では対応不可
- ユーザーの「クリニック+夜勤」ニーズは「条件矛盾」ではなく合理的なケースもある

**Results:**
- Drop-off risk: yes
- Reached Job Proposal: yes（ただし夜勤希望は無視）
- Reached Handoff: no
- Matching Quality: poor
- Sub-area Coverage Issue: no

**Failure Category:** INPUT_LOCK
**Severity:** High
**Fix Proposal:** (1) クリニック選択時もworkstyle質問を表示する（夜間クリニックの需要あり） (2) intake中のフリーテキストでキーワード検出してhandoff提案
**Retry Needed:** yes
**Auditor Comment:**

---

## Summary

### Bug Coverage

| Bug | Cases Testing It | Confirmed |
|-----|-----------------|-----------|
| tokyo_tama 9都市限定 | KW1-022~027, 030, 031, 033, 035, 047, 049 | Yes (12 cases) |
| tokyo_included 横浜/川崎混入 | KW1-036~040 | Yes (5 cases) |
| tokyo_included 候補数全件カウント | KW1-037 | Yes (1 case) |
| クリニック workstyle自動設定 | KW1-003, 050 | Yes (2 cases) |
| フリーテキスト無視 (intake中) | KW1-008, 050 | Yes (2 cases) |
| AI consultation 5ターン上限 | KW1-017 | Yes (1 case) |
| AI 3連続失敗 → 自動handoff | KW1-019 | Yes (1 case) |
| LIFF session area変換 | KW1-048 | Yes (1 case) |

### Failure Category Distribution

| Category | Count | Severity |
|----------|-------|----------|
| GEO_LOCK | 16 | Critical (14), High (2) |
| INPUT_LOCK | 2 | High |
| JOB_MATCH_FAIL | 3 | High (1), Medium (2) |
| UX_DROP | 2 | Medium |
| REGION_EXPANSION_FAIL | 2 | Medium |
| REENTRY_FAIL | 2 | High (1), Medium (1) |
| AMBIG_FAIL | 1 | High |
| HUMAN_HANDOFF_FAIL | 0 | - |
| OTHER | 1 | High |
| NONE | 19 | Low |

### Critical Fix Priorities

1. **AREA_CITY_MAP tokyo_tama 拡張** — 9都市 → 26市3町1村。青梅/国分寺/西東京/小平/東村山/清瀬/東久留米/稲城/あきる野/福生+町村 を追加
2. **tokyo_included のAREA_CITY_MAP修正** — 横浜市/川崎市を削除、23区全て+多摩全市を追加（or AREA_PREF_MAP='東京都'で全検索）
3. **tokyo_included の候補数カウント修正** — AREA_PREF_MAPがnullで全24,488件カウントされるバグ
4. **クリニック workstyle自動設定の見直し** — 夜間クリニック等の需要に対応
5. **intake中フリーテキストのキーワード検出** — unexpectedTextCount閾値でhandoff提案

### 多摩 AREA_CITY_MAP 欠落都市一覧（テスト対象）

| 欠落都市 | Case | 人口(万) | 医療施設集中度 |
|----------|------|---------|--------------|
| 青梅市 | KW1-022 | 13 | 中 |
| 国分寺市 | KW1-023 | 13 | 中 |
| 西東京市 | KW1-024 | 21 | 高 |
| 小平市 | KW1-025 | 20 | 高 |
| 東村山市 | KW1-026 | 15 | 中 |
| 清瀬市 | KW1-027 | 7 | 高（医療集中） |
| 東久留米市 | KW1-030 | 12 | 中 |
| 稲城市 | KW1-031 | 9 | 低 |
| あきる野市 | KW1-033 | 8 | 低 |
| 福生市 | KW1-035 | 6 | 低 |
