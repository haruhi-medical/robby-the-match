# Worker 8: 九州・沖縄 — LINE Bot Simulation Test Cases

> 50 cases total: Main 40 (福岡6, 佐賀5, 長崎5, 熊本5, 大分5, 宮崎5, 鹿児島5, 沖縄4) + Cross 10 (東京2, 大阪2, 愛知2, 北海道2, 神奈川2)
> Mix: 30 standard / 12 boundary / 8 adversarial
> KEY INSIGHT: 0 facilities in DB for all 九州・沖縄 prefectures. "その他の地域" routes to Kanto facilities only.

---

## 福岡県 (6 cases)

### Case W8-001
- **Prefecture:** 福岡県 / **Region Block:** 九州 / **Case Type:** Standard / **User Profile:** 30歳、福岡市内の急性期病院勤務5年目、常勤 / **Entry Route:** Instagram広告→LINE / **Difficulty:** Easy
**Scenario:** 福岡市在住の看護師が地元での転職を希望。エリア選択で「その他の地域」を選ぶ必要がある違和感を検証。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ表示
3. User: 「転職相談したいです」
4. Bot: エリア選択表示（東京都/神奈川県/千葉県/埼玉県/その他の地域）
5. User: 「その他の地域」を選択（福岡がないため）
6. Bot: 施設タイプ選択表示
7. User: 「急性期病院」選択
8. Bot: 診療科選択
9. User: 「外科」選択
10. Bot: マッチング結果 → 関東の施設を提示
**System Behavior Evaluation:** 福岡在住ユーザーに関東施設を提示する致命的ミスマッチ。「その他の地域」選択後に地域確認の分岐がない。日本5位の都市圏をカバーしていない事実がUXに露呈する。
**Results:** Drop-off: 高（80%推定）/ Job Proposal: 関東施設のみ / Next Action: 福岡エリア対応追加が急務 / Region Bias: 極めて強い / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + REGION_EXPANSION_FAIL / **Severity:** Critical / **Fix Proposal:** 「その他の地域」選択後に都道府県テキスト入力→エリア外なら「現在準備中。LINE登録で通知」の導線を追加 / **Retry Needed:** Yes / **Auditor Comment:** 福岡は人口500万都市圏。ここが完全に空白なのは事業リスク。

### Case W8-002
- **Prefecture:** 福岡県 / **Region Block:** 九州 / **Case Type:** Boundary / **User Profile:** 25歳、北九州市の回復期リハ病院、夜勤あり、東京への転職検討中 / **Entry Route:** TikTok→LP→LINE / **Difficulty:** Medium
**Scenario:** 北九州から東京へのUターンではなくIターン転職を検討。関東エリアが希望なのでDB的には問題ないが、遠距離転職特有の質問（引越し、寮、面接交通費）が発生。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「東京で働きたい」
4. Bot: エリア選択表示
5. User: 「東京都」選択
6. Bot: 施設タイプ選択
7. User: 「回復期リハビリテーション病院」
8. Bot: 診療科→勤務形態→緊急度と進む
9. User: 各質問に回答
10. Bot: 東京の施設を提示
**System Behavior Evaluation:** エリア選択が東京なのでDB的には正常動作。ただし遠距離転職に必要な寮・引越支援・Web面接対応の情報が一切ない。Botが九州在住を認識していないため適切なフォローができない。
**Results:** Drop-off: 中 / Job Proposal: 東京の施設（適切）/ Next Action: 遠距離転職者向けヒアリング項目追加 / Region Bias: なし（東京選択のため）/ National Expansion Risk: 中
**Failure Category:** JOB_MATCH_FAIL / **Severity:** Medium / **Fix Proposal:** 現住所ヒアリングを追加し、希望勤務地と異なる場合は寮・引越支援の有無を提示 / **Retry Needed:** No / **Auditor Comment:** Iターン需要は実在する。現住所と希望地の乖離検知は重要。

### Case W8-003
- **Prefecture:** 福岡県 / **Region Block:** 九州 / **Case Type:** Standard / **User Profile:** 40歳、久留米市の大学病院、師長補佐、管理職希望 / **Entry Route:** Google検索→LP→LINE / **Difficulty:** Easy
**Scenario:** 管理職ポジションを希望する中堅看護師。福岡県内での転職を希望するが「その他の地域」しか選べない。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「管理職の求人を探しています」
4. Bot: エリア選択表示
5. User: 「その他の地域」選択
6. Bot: 施設タイプ選択
7. User: 「総合病院」
8. Bot: 診療科→勤務形態→緊急度
9. User: 順に回答
10. Bot: 関東施設を提示
**System Behavior Evaluation:** 管理職希望という高度な条件を持つユーザーに対し、地域すら合わない提案を行う。この層は転職エージェント経験者が多く、サービス品質への期待が高い。即離脱のリスク極大。
**Results:** Drop-off: 極高 / Job Proposal: 関東施設（完全ミスマッチ）/ Next Action: 管理職枠は人力マッチング導線を優先 / Region Bias: 極めて強い / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + JOB_MATCH_FAIL / **Severity:** Critical / **Fix Proposal:** 管理職・専門職は自動マッチング不可→即人力ハンドオフの分岐を追加 / **Retry Needed:** Yes / **Auditor Comment:** 管理職求人はエリア×ポジションの絞り込みが命。DB空では話にならない。

### Case W8-004
- **Prefecture:** 福岡県 / **Region Block:** 九州 / **Case Type:** Adversarial / **User Profile:** 33歳、福岡市の訪問看護ステーション、フリーテキストで大量条件を一気投下 / **Entry Route:** LINE直接追加 / **Difficulty:** Hard
**Scenario:** ユーザーが選択肢を無視して自由記述で「福岡市中央区で訪問看護、日勤のみ、年収450万以上、託児所付き、土日休み、車通勤可」と一気に入力。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「福岡市中央区で訪問看護、日勤のみ、年収450万以上、託児所付き、土日休み、車通勤可で探して」
4. Bot: エリア選択ボタンを表示（テキスト入力を無視する可能性）
5. User: 「だから福岡って言ってるじゃん」
6. Bot: エリア選択ボタンを再表示
7. User: 諦めて「その他の地域」を選択
8. Bot: 施設タイプ選択（条件の大半が無視されている）
9. User: 離脱
**System Behavior Evaluation:** 自由記述の条件をパースする能力がない。ユーザーの詳細条件を全て無視し、定型フローを強制する。3ターン目で不信感→離脱は確実。
**Results:** Drop-off: 確実（3-4ターン目）/ Job Proposal: なし / Next Action: NLP条件抽出の実装検討 / Region Bias: 強い / National Expansion Risk: 高
**Failure Category:** AMBIG_FAIL + INPUT_LOCK / **Severity:** High / **Fix Proposal:** フリーテキスト入力時にAIが条件を抽出→確認→フロー途中に合流させる仕組み / **Retry Needed:** Yes / **Auditor Comment:** 看護師は忙しい。条件を一気に伝えたいのは当然。これを拾えないのは致命的。

### Case W8-005
- **Prefecture:** 福岡県 / **Region Block:** 九州 / **Case Type:** Standard / **User Profile:** 22歳、新卒、福岡の看護学校卒業予定、初めての就職 / **Entry Route:** 友人紹介→LINE / **Difficulty:** Easy
**Scenario:** 新卒看護師が初めての就職先を探している。転職ではなく就職。Botが「転職」前提で設計されている場合の対応を検証。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ（「転職」という文言が含まれる可能性）
3. User: 「来年4月から働ける病院を探しています。新卒です」
4. Bot: エリア選択表示
5. User: 「その他の地域」選択
6. Bot: 施設タイプ→診療科→勤務形態→緊急度
7. User: 順に回答（緊急度は「半年以内」）
8. Bot: 関東施設を提示
**System Behavior Evaluation:** 新卒＝転職ではないが、Botはその区別をしない。また福岡の新卒に関東施設を紹介するのは完全に的外れ。新卒特有のニーズ（教育体制、プリセプター制度、研修充実度）への対応もない。
**Results:** Drop-off: 高 / Job Proposal: 関東施設（完全ミスマッチ）/ Next Action: 新卒/既卒の分岐追加 / Region Bias: 強い / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + JOB_MATCH_FAIL / **Severity:** High / **Fix Proposal:** 初回ヒアリングで「転職/新卒就職」を分岐。新卒は教育体制重視のマッチング / **Retry Needed:** Yes / **Auditor Comment:** 紹介事業なので新卒は対象外の可能性もあるが、その場合は明確に案内すべき。

### Case W8-006
- **Prefecture:** 福岡県 / **Region Block:** 九州 / **Case Type:** Boundary / **User Profile:** 35歳、福岡県飯塚市、療養型病院、夜勤専従 / **Entry Route:** SEO記事→LINE / **Difficulty:** Medium
**Scenario:** 夜勤専従で高収入だが体力的に限界を感じている。日勤のみの職場を希望するが年収ダウンを受け入れられるか迷っている。相談ベースでBotに話しかける。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「夜勤専従から日勤に変えたいんですが、年収どのくらい下がりますか？」
4. Bot: エリア選択を表示（相談内容に応答できない）
5. User: 「まず相談だけしたいんですけど」
6. Bot: エリア選択を再表示
7. User: 「その他の地域」を選択
8. Bot: 施設タイプ選択に進む
**System Behavior Evaluation:** 相談ベースの入り口に対応できない。ユーザーは具体的な求人検索ではなくキャリア相談を求めているが、Botは定型フローしか持たない。この層は人力ハンドオフが最適。
**Results:** Drop-off: 高 / Job Proposal: 関東施設（ミスマッチ）/ Next Action: 相談モード→人力ハンドオフの分岐 / Region Bias: 強い / National Expansion Risk: 中
**Failure Category:** AMBIG_FAIL + HUMAN_HANDOFF_FAIL / **Severity:** Medium / **Fix Proposal:** 「相談」「迷っている」等のキーワード検知→即座にスタッフ対応導線 / **Retry Needed:** No / **Auditor Comment:** 相談→信頼構築→紹介が本来の導線。Botで全て完結させる必要はない。

---

## 佐賀県 (5 cases)

### Case W8-007
- **Prefecture:** 佐賀県 / **Region Block:** 九州 / **Case Type:** Standard / **User Profile:** 29歳、佐賀市の中規模病院、内科病棟、常勤 / **Entry Route:** Instagram投稿→LINE / **Difficulty:** Easy
**Scenario:** 佐賀県内での転職を希望。選択肢に佐賀県がなく「その他の地域」を選ぶ。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「転職考えてます」
4. Bot: エリア選択表示
5. User: 「佐賀県」とテキスト入力を試みる
6. Bot: エリア選択ボタンを再表示
7. User: 「その他の地域」選択
8. Bot: 施設タイプ→診療科→勤務形態→緊急度
9. User: 「総合病院」「内科」「日勤・夜勤両方」「3ヶ月以内」
10. Bot: 関東施設を提示
**System Behavior Evaluation:** 佐賀→「その他」→関東施設提示の流れ。テキスト入力の「佐賀県」が無視される。地方ユーザーにとって「あなたの県は対象外」と暗に伝わるUX。
**Results:** Drop-off: 高 / Job Proposal: 関東施設（完全ミスマッチ）/ Next Action: エリア外対応フロー整備 / Region Bias: 極めて強い / National Expansion Risk: 高
**Failure Category:** GEO_LOCK / **Severity:** Critical / **Fix Proposal:** 「その他の地域」選択後にフリーテキストで県名入力→DB外なら「準備中」メッセージ+人力導線 / **Retry Needed:** Yes / **Auditor Comment:** 佐賀は福岡通勤圏。福岡DBがあれば佐賀ユーザーも救える可能性あり。

### Case W8-008
- **Prefecture:** 佐賀県 / **Region Block:** 九州 / **Case Type:** Standard / **User Profile:** 45歳、鳥栖市のクリニック、外来看護師、パート希望 / **Entry Route:** Google検索→LINE / **Difficulty:** Easy
**Scenario:** 鳥栖市は福岡県境。福岡市内への通勤も視野に入れているが、Botにそれを伝える手段がない。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「鳥栖から福岡市内に通える範囲で探してます」
4. Bot: エリア選択表示（福岡も選択肢にない）
5. User: 「その他の地域」選択
6. Bot: 施設タイプ選択
7. User: 「クリニック」
8. Bot: 診療科→勤務形態→緊急度
9. User: 回答
10. Bot: 関東施設を提示
**System Behavior Evaluation:** 県境通勤という現実的な条件を処理できない。佐賀↔福岡のクロスエリア検索は不可。そもそも両県ともDB外。
**Results:** Drop-off: 高 / Job Proposal: 関東施設（完全ミスマッチ）/ Next Action: 通勤圏ベースの検索機能 / Region Bias: 極めて強い / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + AMBIG_FAIL / **Severity:** Critical / **Fix Proposal:** 通勤圏（距離/時間ベース）での検索を将来実装。当面は人力対応 / **Retry Needed:** Yes / **Auditor Comment:** 県境ユーザーは全国に多数。都道府県単位の検索では拾えない層。

### Case W8-009
- **Prefecture:** 佐賀県 / **Region Block:** 九州 / **Case Type:** Boundary / **User Profile:** 32歳、唐津市の訪問看護、結婚を機に神奈川へ引越予定 / **Entry Route:** LP→LINE / **Difficulty:** Medium
**Scenario:** 引越先が神奈川県なのでDB的にはマッチ可能。しかしBotフローでは引越予定の情報を聞くタイミングがない。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「来月神奈川に引っ越すので転職先を探してます」
4. Bot: エリア選択表示
5. User: 「神奈川県」選択
6. Bot: 施設タイプ→診療科→勤務形態→緊急度
7. User: 「訪問看護」「在宅」「日勤のみ」「1ヶ月以内」
8. Bot: 神奈川の施設を提示
**System Behavior Evaluation:** 神奈川を選択したので正常動作。ただし引越前のWeb面接対応、入職日調整などの遠距離特有ニーズへの対応なし。引越時期と入職時期の調整が必要だがBotは把握しない。
**Results:** Drop-off: 低 / Job Proposal: 神奈川施設（適切）/ Next Action: 引越予定者向けフロー追加 / Region Bias: なし / National Expansion Risk: 低
**Failure Category:** JOB_MATCH_FAIL / **Severity:** Low / **Fix Proposal:** 引越予定の有無をヒアリングに追加。Web面接対応施設のフラグ化 / **Retry Needed:** No / **Auditor Comment:** 正常系に近いが、引越タイミングの考慮が欲しい。

### Case W8-010
- **Prefecture:** 佐賀県 / **Region Block:** 九州 / **Case Type:** Adversarial / **User Profile:** 28歳、武雄市の温泉病院、方言が強い / **Entry Route:** TikTok→LINE / **Difficulty:** Hard
**Scenario:** 佐賀弁で「こっちんほうでよかとこなかですか」と入力。方言対応を検証。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「こっちんほうでよかとこなかですか」
4. Bot: エリア選択表示（方言を理解できない）
5. User: 「佐賀でよかとばい」
6. Bot: エリア選択表示を再度
7. User: 「その他の地域」を渋々選択
8. Bot: 施設タイプ選択
9. User: 「もうよかです」→離脱
**System Behavior Evaluation:** 方言テキストへの対応力ゼロ。AI応答部分でも方言解析ができない場合、ユーザーの意図を汲めない。九州は方言使用率が高く、この問題は地域特有。
**Results:** Drop-off: 確実 / Job Proposal: なし / Next Action: 方言対応のNLP強化 / Region Bias: 間接的（地方軽視）/ National Expansion Risk: 中
**Failure Category:** TYPO_FAIL + UX_DROP / **Severity:** Medium / **Fix Proposal:** OpenAI/Claude APIで方言→標準語変換を前処理に挟む / **Retry Needed:** Yes / **Auditor Comment:** 方言は誤字ではなく正当な日本語。対応できないのはサービスの限界。

### Case W8-011
- **Prefecture:** 佐賀県 / **Region Block:** 九州 / **Case Type:** Standard / **User Profile:** 38歳、佐賀大学医学部附属病院、ICU、キャリアアップ志向 / **Entry Route:** SEOブログ→LINE / **Difficulty:** Easy
**Scenario:** ICU経験を活かしてスキルアップしたい。専門性の高い求人を希望。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「ICU経験8年です。もっとスキルアップできる環境を探しています」
4. Bot: エリア選択表示
5. User: 「その他の地域」
6. Bot: 施設タイプ選択
7. User: 「急性期病院」
8. Bot: 診療科→勤務形態→緊急度
9. User: 「ICU/救急」「常勤」「半年以内」
10. Bot: 関東施設を提示
**System Behavior Evaluation:** ICU経験8年のベテランに対し、専門性を考慮しないマッチング。提示された関東施設がICU強化を謳っているかは不明。スキルベースのマッチングがない。
**Results:** Drop-off: 高 / Job Proposal: 関東施設（地域ミスマッチ）/ Next Action: 専門スキルベースのマッチング / Region Bias: 強い / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + JOB_MATCH_FAIL / **Severity:** High / **Fix Proposal:** スキル・経験年数をマッチングスコアに反映 / **Retry Needed:** Yes / **Auditor Comment:** 専門職は条件が明確。それを活かせないマッチングは信頼を失う。

---

## 長崎県 (5 cases)

### Case W8-012
- **Prefecture:** 長崎県 / **Region Block:** 九州 / **Case Type:** Standard / **User Profile:** 27歳、長崎市の総合病院、小児科、常勤 / **Entry Route:** Instagram→LINE / **Difficulty:** Easy
**Scenario:** 長崎市内の小児科看護師。同市内での転職を希望。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「小児科で別の病院探してます」
4. Bot: エリア選択表示
5. User: 「その他の地域」
6. Bot: 施設タイプ→「総合病院」→診療科→「小児科」→勤務形態→「常勤」→緊急度→「3ヶ月以内」
7. Bot: 関東施設を提示
**System Behavior Evaluation:** 長崎市内の小児科求人を探しているのに関東施設を提示。小児科は専門性が高く、提案施設の小児科の規模感も不明。
**Results:** Drop-off: 高 / Job Proposal: 関東施設（ミスマッチ）/ Next Action: エリア拡大 / Region Bias: 強い / National Expansion Risk: 高
**Failure Category:** GEO_LOCK / **Severity:** Critical / **Fix Proposal:** エリア外告知+LINE登録維持で将来対応を約束 / **Retry Needed:** Yes / **Auditor Comment:** 長崎は離島も多く医療需要は高い。対応優先度を検討すべき。

### Case W8-013
- **Prefecture:** 長崎県 / **Region Block:** 九州 / **Case Type:** Boundary / **User Profile:** 31歳、五島列島の診療所、離島看護師 / **Entry Route:** Google検索→LINE / **Difficulty:** Hard
**Scenario:** 離島の診療所で働く看護師。本土への転職を希望するが、離島勤務経験という特殊スキルの扱いを検証。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「五島列島で3年働いてます。本土に戻りたいです」
4. Bot: エリア選択表示
5. User: 「その他の地域」（長崎本土を想定）
6. Bot: 施設タイプ選択
7. User: 「総合病院」
8. Bot: 診療科→勤務形態→緊急度
9. User: 「総合内科」「常勤」「半年以内」
10. Bot: 関東施設を提示
**System Behavior Evaluation:** 離島勤務経験は高く評価されるべきスキル（多科対応、救急対応、少人数運営）だがBotはそれを認識しない。「本土」が長崎本土なのか関東なのかの確認もない。
**Results:** Drop-off: 高 / Job Proposal: 関東施設（意図不明）/ Next Action: 離島看護師の特殊スキル評価導線 / Region Bias: 強い / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + AMBIG_FAIL / **Severity:** High / **Fix Proposal:** 「本土」の定義を確認する質問を追加。離島経験をスキルとして評価 / **Retry Needed:** Yes / **Auditor Comment:** 離島医療人材は希少。丁寧に対応すべき層。

### Case W8-014
- **Prefecture:** 長崎県 / **Region Block:** 九州 / **Case Type:** Standard / **User Profile:** 42歳、佐世保市の精神科病院、准看護師 / **Entry Route:** LINE直接追加 / **Difficulty:** Easy
**Scenario:** 准看護師で正看護師資格なし。Botが資格種別を確認するかどうかを検証。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「准看なんですけど大丈夫ですか？」
4. Bot: エリア選択表示（質問に回答しない）
5. User: 「その他の地域」
6. Bot: 施設タイプ→診療科→勤務形態→緊急度
7. User: 回答
8. Bot: 施設提示（准看/正看の区別なし）
**System Behavior Evaluation:** 准看護師という重要な資格情報に対して応答がない。マッチングでも准看と正看を区別していない可能性。求人には資格要件があるため、ここを無視するとミスマッチ。
**Results:** Drop-off: 中 / Job Proposal: 資格要件不明の施設 / Next Action: 資格種別ヒアリングの追加 / Region Bias: 強い / National Expansion Risk: 中
**Failure Category:** JOB_MATCH_FAIL + INPUT_LOCK / **Severity:** Medium / **Fix Proposal:** 資格種別（正看/准看/保健師/助産師）をフロー初期に確認 / **Retry Needed:** No / **Auditor Comment:** 准看護師の求人条件は異なる。区別必須。

### Case W8-015
- **Prefecture:** 長崎県 / **Region Block:** 九州 / **Case Type:** Adversarial / **User Profile:** 26歳、諫早市、ユーザーがBotのエリア制限を指摘して怒る / **Entry Route:** 広告→LINE / **Difficulty:** Hard
**Scenario:** ユーザーが「神奈川だけじゃん」と気づいてクレーム。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「長崎で探してます」
4. Bot: エリア選択表示
5. User: 「え、東京と神奈川と千葉と埼玉しかないの？九州は？」
6. Bot: エリア選択表示を再度（苦情に対応できない）
7. User: 「広告で見て来たのに対象外とか詐欺じゃないですか」
8. Bot: エリア選択表示
9. User: ブロック
**System Behavior Evaluation:** クレームに対する応答能力がゼロ。広告（TikTok/Instagram）は全国配信されているため、対象外地域からの流入は必然。クレーム対応フローの欠如は信頼破壊。
**Results:** Drop-off: 確実+ブロック / Job Proposal: なし / Next Action: クレーム対応フロー構築 / Region Bias: 致命的 / National Expansion Risk: 極高
**Failure Category:** GEO_LOCK + UX_DROP + REGION_EXPANSION_FAIL / **Severity:** Critical / **Fix Proposal:** 1)広告のターゲティング地域を限定 2)エリア外ユーザーへの丁寧な説明文+将来通知オプション 3)クレーム検知→即人力ハンドオフ / **Retry Needed:** Yes / **Auditor Comment:** 広告の全国配信×エリア限定サービスは矛盾。最優先で対処すべき。

### Case W8-016
- **Prefecture:** 長崎県 / **Region Block:** 九州 / **Case Type:** Standard / **User Profile:** 36歳、長崎市の訪問看護ステーション、ケアマネ資格あり / **Entry Route:** ブログ記事→LINE / **Difficulty:** Easy
**Scenario:** ケアマネ資格を持つ看護師。介護施設や在宅系での転職を希望。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「ケアマネの資格もあるんですが、活かせる職場ありますか？」
4. Bot: エリア選択表示
5. User: 「その他の地域」
6. Bot: 施設タイプ選択
7. User: 「介護施設」（選択肢にあるか不明）
8. Bot: 診療科→勤務形態→緊急度
9. User: 回答
10. Bot: 施設提示
**System Behavior Evaluation:** ケアマネ資格というダブルライセンスの価値を認識できない。施設タイプの選択肢に介護施設が含まれるかも不明。看護師紹介に特化しすぎて介護領域をカバーできない可能性。
**Results:** Drop-off: 中 / Job Proposal: 関東施設（ミスマッチ）/ Next Action: ダブルライセンス対応 / Region Bias: 強い / National Expansion Risk: 中
**Failure Category:** GEO_LOCK + JOB_MATCH_FAIL / **Severity:** Medium / **Fix Proposal:** 追加資格ヒアリングとそれを活かせる施設タイプの提案 / **Retry Needed:** No / **Auditor Comment:** ケアマネ+看護師は市場価値が高い。この層を逃すのはもったいない。

---

## 熊本県 (5 cases)

### Case W8-017
- **Prefecture:** 熊本県 / **Region Block:** 九州 / **Case Type:** Standard / **User Profile:** 30歳、熊本市の急性期病院、外科病棟、常勤 / **Entry Route:** TikTok→LINE / **Difficulty:** Easy
**Scenario:** 熊本市内での転職希望。標準的なフロー検証。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「熊本で転職したいです」
4. Bot: エリア選択表示
5. User: 「その他の地域」
6. Bot: 施設タイプ→「急性期病院」→診療科→「外科」→勤務形態→「常勤夜勤あり」→緊急度→「3ヶ月以内」
7. Bot: 関東施設を提示
**System Behavior Evaluation:** 熊本市は政令指定都市。人口73万。DB空で関東施設を提示するのは明らかにミスマッチ。
**Results:** Drop-off: 高 / Job Proposal: 関東施設（ミスマッチ）/ Next Action: エリア拡大 / Region Bias: 強い / National Expansion Risk: 高
**Failure Category:** GEO_LOCK / **Severity:** Critical / **Fix Proposal:** 政令指定都市は優先的にDB拡充 / **Retry Needed:** Yes / **Auditor Comment:** 熊本は地震復興で医療需要も高い。

### Case W8-018
- **Prefecture:** 熊本県 / **Region Block:** 九州 / **Case Type:** Boundary / **User Profile:** 48歳、天草市の市立病院、定年まで働ける職場希望 / **Entry Route:** Google→LINE / **Difficulty:** Medium
**Scenario:** 離島・僻地に近い天草からの転職希望。年齢的に50代目前で安定志向。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「50近いんですけど、まだ転職できますか？」
4. Bot: エリア選択表示（年齢に関する質問を無視）
5. User: 「その他の地域」
6. Bot: 施設タイプ→診療科→勤務形態→緊急度
7. User: 「療養型」「内科」「日勤のみ」「急いでない」
8. Bot: 関東施設を提示
**System Behavior Evaluation:** 年齢に関する不安への応答がない。50代看護師の転職市場は実際には好況だが、その情報提供もない。加えて地域ミスマッチ。
**Results:** Drop-off: 高 / Job Proposal: 関東施設（ミスマッチ）/ Next Action: 年齢不安への応答テンプレ / Region Bias: 強い / National Expansion Risk: 中
**Failure Category:** GEO_LOCK + AMBIG_FAIL / **Severity:** Medium / **Fix Proposal:** FAQ的な応答（年齢制限なし等）をAI応答に組み込む / **Retry Needed:** No / **Auditor Comment:** 看護師不足で50代は歓迎される。不安を解消するだけで離脱防止。

### Case W8-019
- **Prefecture:** 熊本県 / **Region Block:** 九州 / **Case Type:** Standard / **User Profile:** 26歳、阿蘇市の公立病院、救急外来、Uターン検討中 / **Entry Route:** LP→LINE / **Difficulty:** Easy
**Scenario:** 熊本出身だが東京の大学を出て地元に戻った。再び東京に行くか迷っている。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「東京に戻ろうか迷ってます」
4. Bot: エリア選択表示
5. User: 「東京都」選択
6. Bot: 施設タイプ→診療科→勤務形態→緊急度
7. User: 「救急病院」「救急外来」「常勤」「半年以内」
8. Bot: 東京の施設を提示
**System Behavior Evaluation:** 東京を選択したので正常動作。しかし「迷っている」段階のユーザーに即座にマッチング結果を出すのは早すぎる。キャリアカウンセリング的な対応が先。
**Results:** Drop-off: 中 / Job Proposal: 東京施設（一応適切）/ Next Action: 迷い中ユーザーへの段階的アプローチ / Region Bias: なし / National Expansion Risk: 低
**Failure Category:** UX_DROP / **Severity:** Low / **Fix Proposal:** 「迷っている」検知→情報提供モード（給与比較、生活費比較等）を先に提示 / **Retry Needed:** No / **Auditor Comment:** Uターン/Iターン層は決断前の情報提供が効く。

### Case W8-020
- **Prefecture:** 熊本県 / **Region Block:** 九州 / **Case Type:** Adversarial / **User Profile:** 34歳、熊本市、ユーザーがBotの挙動をテストする / **Entry Route:** LINE直接追加 / **Difficulty:** Hard
**Scenario:** IT系の夫を持つ看護師がBotの性能を試すために矛盾する条件を入力。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「年収800万、週3日、夜勤なし、熊本市中心部、徒歩5分」
4. Bot: エリア選択表示
5. User: 「その他の地域」
6. Bot: 施設タイプ選択
7. User: 「美容クリニック」
8. Bot: 診療科→勤務形態→緊急度
9. User: 「美容外科」「パート」「今すぐ」
10. Bot: 関東施設を提示（年収800万パートは現実的でない）
**System Behavior Evaluation:** 非現実的な条件（年収800万+週3+パート）を検証せずにマッチングを進める。条件の妥当性チェックがない。さらに地域ミスマッチも重なる。
**Results:** Drop-off: 高 / Job Proposal: 関東施設（条件+地域ミスマッチ）/ Next Action: 条件妥当性チェック / Region Bias: 強い / National Expansion Risk: 中
**Failure Category:** AMBIG_FAIL + JOB_MATCH_FAIL / **Severity:** Medium / **Fix Proposal:** 年収+勤務形態の組合せで非現実的な場合は「この条件での求人は限られます」と通知 / **Retry Needed:** No / **Auditor Comment:** 矛盾条件の検出は品質指標。なくても致命的ではないが信頼性向上に寄与。

### Case W8-021
- **Prefecture:** 熊本県 / **Region Block:** 九州 / **Case Type:** Standard / **User Profile:** 24歳、熊本市のクリニック、皮膚科、美容看護に興味 / **Entry Route:** Instagram→LINE / **Difficulty:** Easy
**Scenario:** 美容クリニックへの転職を希望する若手看護師。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「美容クリニックで働きたいです」
4. Bot: エリア選択表示
5. User: 「その他の地域」
6. Bot: 施設タイプ選択
7. User: 「クリニック」
8. Bot: 診療科→「美容」or「皮膚科」→勤務形態→緊急度
9. User: 回答
10. Bot: 関東施設を提示
**System Behavior Evaluation:** 美容クリニックはInstagram経由の問い合わせが多い業態。この層は比較的若く、SNS活用に長けている。しかし提案は地域ミスマッチ。
**Results:** Drop-off: 高 / Job Proposal: 関東施設（ミスマッチ）/ Next Action: 美容系特化の導線検討 / Region Bias: 強い / National Expansion Risk: 中
**Failure Category:** GEO_LOCK / **Severity:** High / **Fix Proposal:** 美容系は全国需要あり。地域DB拡充の優先候補 / **Retry Needed:** Yes / **Auditor Comment:** 美容クリニック転職はSNS親和性が高く、広告からの流入が多い。対応できないと機会損失大。

---

## 大分県 (5 cases)

### Case W8-022
- **Prefecture:** 大分県 / **Region Block:** 九州 / **Case Type:** Standard / **User Profile:** 29歳、大分市の総合病院、整形外科、常勤 / **Entry Route:** TikTok→LINE / **Difficulty:** Easy
**Scenario:** 大分市内での転職希望。スタンダードフロー検証。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「大分で整形外科の求人ありますか？」
4. Bot: エリア選択表示
5. User: 「その他の地域」
6. Bot: 施設タイプ→診療科→勤務形態→緊急度
7. User: 「総合病院」「整形外科」「常勤」「3ヶ月以内」
8. Bot: 関東施設を提示
**System Behavior Evaluation:** 大分→「その他」→関東施設の定番パターン。整形外科という明確な希望も地域ミスマッチで無意味に。
**Results:** Drop-off: 高 / Job Proposal: 関東施設（ミスマッチ）/ Next Action: エリア拡大 / Region Bias: 強い / National Expansion Risk: 高
**Failure Category:** GEO_LOCK / **Severity:** Critical / **Fix Proposal:** エリア外メッセージの改善 / **Retry Needed:** Yes / **Auditor Comment:** 九州全県で同じ問題が反復している。

### Case W8-023
- **Prefecture:** 大分県 / **Region Block:** 九州 / **Case Type:** Boundary / **User Profile:** 37歳、別府市の温泉病院リハビリ科、独自性のある職場環境 / **Entry Route:** ブログ→LINE / **Difficulty:** Medium
**Scenario:** 別府の温泉病院はユニークな環境。こうした特殊環境からの転職は条件の言語化が難しい。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「温泉リハビリやってたんですけど、普通の回復期に行きたいです」
4. Bot: エリア選択表示
5. User: 「その他の地域」
6. Bot: 施設タイプ選択
7. User: 「回復期リハビリテーション病院」
8. Bot: 診療科→勤務形態→緊急度
9. User: 「リハビリ科」「常勤」「半年以内」
10. Bot: 関東施設を提示
**System Behavior Evaluation:** 温泉リハビリという特殊経験を持つユーザーのスキルセットを把握できない。回復期病院の提案自体は悪くないが地域が合わない。
**Results:** Drop-off: 高 / Job Proposal: 関東施設（ミスマッチ）/ Next Action: 特殊経験の記録と活用 / Region Bias: 強い / National Expansion Risk: 中
**Failure Category:** GEO_LOCK / **Severity:** High / **Fix Proposal:** フリーテキストで前職環境を記録→人力マッチング時の参考情報に / **Retry Needed:** Yes / **Auditor Comment:** 特殊経験者は人力対応の方がマッチ精度が上がる。

### Case W8-024
- **Prefecture:** 大分県 / **Region Block:** 九州 / **Case Type:** Standard / **User Profile:** 33歳、中津市の病院、産婦人科、子育て中 / **Entry Route:** Instagram→LINE / **Difficulty:** Easy
**Scenario:** 子育て中で時短勤務を希望。保育園のお迎えに間に合う職場が条件。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「子供のお迎えがあるので17時までに帰れる病院を探してます」
4. Bot: エリア選択表示
5. User: 「その他の地域」
6. Bot: 施設タイプ→診療科→勤務形態→緊急度
7. User: 「総合病院」「産婦人科」「時短/パート」「3ヶ月以内」
8. Bot: 関東施設を提示
**System Behavior Evaluation:** 「17時まで」という具体的時間条件をフローで拾えない。勤務形態で「時短」を選べるかも不明。子育て看護師は最大のターゲット層の一つだが、きめ細かい条件対応ができていない。
**Results:** Drop-off: 高 / Job Proposal: 関東施設（ミスマッチ）/ Next Action: 時短条件の詳細化 / Region Bias: 強い / National Expansion Risk: 中
**Failure Category:** GEO_LOCK + INPUT_LOCK / **Severity:** High / **Fix Proposal:** 時短希望者向けに「希望退勤時間」をヒアリング項目に追加 / **Retry Needed:** Yes / **Auditor Comment:** ペルソナ「ミサキ」にも通じる層。最重要ターゲットの条件を拾えないのは問題。

### Case W8-025
- **Prefecture:** 大分県 / **Region Block:** 九州 / **Case Type:** Adversarial / **User Profile:** 28歳、大分市、途中で条件を二転三転させる / **Entry Route:** LINE直接 / **Difficulty:** Hard
**Scenario:** ユーザーが途中で希望条件を変え続ける。Botの会話管理能力を検証。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「急性期に行きたい」
4. Bot: エリア選択→「その他の地域」→施設タイプ選択
5. User: 「やっぱりクリニックがいい」
6. Bot: 選択肢を再表示？or前の回答が上書きされる？
7. User: 「いや、訪問看護にしようかな」
8. Bot: 対応不明
9. User: 「もういいです」→離脱
**System Behavior Evaluation:** 条件変更に対するフロー巻き戻しの柔軟性が不明。定型フローの場合、一度選択した項目を変更する手段がないケースが多い。「やっぱり〜」という日常的な表現に対応できるか。
**Results:** Drop-off: 確実 / Job Proposal: なし / Next Action: フロー巻き戻し機能 / Region Bias: N/A / National Expansion Risk: 低
**Failure Category:** UX_DROP + AMBIG_FAIL / **Severity:** Medium / **Fix Proposal:** 「戻る」ボタンまたは「最初からやり直す」オプションを常時表示 / **Retry Needed:** Yes / **Auditor Comment:** 迷いながら選ぶのは当然。巻き戻しなしはUX的に厳しい。

### Case W8-026
- **Prefecture:** 大分県 / **Region Block:** 九州 / **Case Type:** Standard / **User Profile:** 41歳、杵築市の介護老人保健施設、看護主任 / **Entry Route:** SEO→LINE / **Difficulty:** Easy
**Scenario:** 介護施設から病院への復帰を希望。ブランク的な扱いになるかを検証。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「老健で5年働いたんですが、病院に戻りたいです」
4. Bot: エリア選択→「その他の地域」
5. Bot: 施設タイプ→診療科→勤務形態→緊急度
6. User: 「総合病院」「一般内科」「常勤」「半年以内」
7. Bot: 関東施設を提示
**System Behavior Evaluation:** 介護施設→病院復帰は「ブランク」ではないが、急性期スキルの鈍りはある。この情報をマッチングに反映できない。加えて地域ミスマッチ。
**Results:** Drop-off: 高 / Job Proposal: 関東施設（ミスマッチ）/ Next Action: 前職種別の適性評価 / Region Bias: 強い / National Expansion Risk: 中
**Failure Category:** GEO_LOCK + JOB_MATCH_FAIL / **Severity:** High / **Fix Proposal:** 前職の施設種別をマッチングスコアに反映 / **Retry Needed:** Yes / **Auditor Comment:** 介護→病院復帰はニーズが多い。教育体制の充実した施設を優先的に提案すべき。

---

## 宮崎県 (5 cases)

### Case W8-027
- **Prefecture:** 宮崎県 / **Region Block:** 九州 / **Case Type:** Standard / **User Profile:** 27歳、宮崎市の市民病院、循環器内科、常勤 / **Entry Route:** Instagram→LINE / **Difficulty:** Easy
**Scenario:** 宮崎市内での転職。循環器内科の経験を活かしたい。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「循環器で4年やってます。宮崎市内で探してます」
4. Bot: エリア選択表示
5. User: 「その他の地域」
6. Bot: 施設タイプ→診療科→勤務形態→緊急度
7. User: 「急性期病院」「循環器内科」「常勤」「3ヶ月以内」
8. Bot: 関東施設を提示
**System Behavior Evaluation:** 循環器内科4年の具体的経験をマッチングに活かせない。宮崎→関東の地域ミスマッチ。
**Results:** Drop-off: 高 / Job Proposal: 関東施設（ミスマッチ）/ Next Action: エリア拡大+専門科マッチング強化 / Region Bias: 強い / National Expansion Risk: 高
**Failure Category:** GEO_LOCK / **Severity:** Critical / **Fix Proposal:** 経験年数+診療科の組合せで施設推薦精度を上げる / **Retry Needed:** Yes / **Auditor Comment:** 同じパターンの繰り返しだが、各県で検証は必要。

### Case W8-028
- **Prefecture:** 宮崎県 / **Region Block:** 九州 / **Case Type:** Boundary / **User Profile:** 55歳、延岡市の市立病院、定年後再雇用を見据えた転職 / **Entry Route:** Google→LINE / **Difficulty:** Medium
**Scenario:** 定年を5年後に控え、再雇用条件の良い職場を探している。年齢制限への不安。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「55歳です。定年後も働ける病院を探しています」
4. Bot: エリア選択表示
5. User: 「その他の地域」
6. Bot: 施設タイプ→診療科→勤務形態→緊急度
7. User: 「療養型病院」「内科」「常勤」「急いでない」
8. Bot: 関東施設を提示
**System Behavior Evaluation:** 55歳のシニア看護師のキャリア相談に対する配慮がない。定年後再雇用という長期的なキャリアプランへの対応もゼロ。地域ミスマッチも当然発生。
**Results:** Drop-off: 高 / Job Proposal: 関東施設（ミスマッチ）/ Next Action: シニア層対応フロー / Region Bias: 強い / National Expansion Risk: 中
**Failure Category:** GEO_LOCK + AMBIG_FAIL / **Severity:** Medium / **Fix Proposal:** シニア看護師向け再雇用制度の有無を施設情報に追加 / **Retry Needed:** No / **Auditor Comment:** 看護師不足でシニア層の価値は上昇中。定年後対応は差別化になる。

### Case W8-029
- **Prefecture:** 宮崎県 / **Region Block:** 九州 / **Case Type:** Standard / **User Profile:** 31歳、都城市の精神科病院、うつ病からの復職 / **Entry Route:** LP→LINE / **Difficulty:** Medium
**Scenario:** メンタルヘルスの問題で休職後、復職先を探している。デリケートな状況。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「休職してたんですけど、そろそろ復帰したいです」
4. Bot: エリア選択表示
5. User: 「その他の地域」
6. Bot: 施設タイプ→診療科→勤務形態→緊急度
7. User: 「クリニック」「心療内科」「パート」「急いでない」
8. Bot: 関東施設を提示
**System Behavior Evaluation:** 休職理由への配慮がない。メンタルヘルス復帰者にはストレス少ない環境、段階的な勤務復帰、理解のある職場の提案が必要だがBotは対応不可。非常にデリケートな層をBotだけで扱うリスク。
**Results:** Drop-off: 中 / Job Proposal: 関東施設（ミスマッチ）/ Next Action: 復職支援導線→人力ハンドオフ / Region Bias: 強い / National Expansion Risk: 中
**Failure Category:** GEO_LOCK + HUMAN_HANDOFF_FAIL / **Severity:** High / **Fix Proposal:** 「休職」「復帰」キーワード検知→即座に人力カウンセラー導線 / **Retry Needed:** Yes / **Auditor Comment:** メンタルヘルス復帰者は丁寧なケアが必要。Bot完結は不適切。

### Case W8-030
- **Prefecture:** 宮崎県 / **Region Block:** 九州 / **Case Type:** Adversarial / **User Profile:** 23歳、日南市、Botに個人情報を聞かれたくない / **Entry Route:** LINE直接 / **Difficulty:** Hard
**Scenario:** プライバシーを気にするユーザーが情報提供を最小限にしたい。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「求人だけ見せて」
4. Bot: エリア選択表示
5. User: 「その他の地域」
6. Bot: 施設タイプ選択
7. User: 「なんでもいい。早く見せて」
8. Bot: 診療科選択
9. User: 「個人情報とかいらないでしょ。求人見せてよ」
10. Bot: 診療科選択を再表示→離脱
**System Behavior Evaluation:** 段階的な情報収集フローが「壁」になっている。求人一覧をまず見せる→興味のある求人に応募→そこで情報取得、という逆順フローに対応できない。
**Results:** Drop-off: 確実 / Job Proposal: なし / Next Action: 求人一覧閲覧モード / Region Bias: N/A / National Expansion Risk: 低
**Failure Category:** INPUT_LOCK + UX_DROP / **Severity:** Medium / **Fix Proposal:** 条件未指定でも閲覧可能な求人一覧ページへのリンクを提供 / **Retry Needed:** Yes / **Auditor Comment:** まず見せてから聞く。情報収集が先のフローは現代UXと合わない。

### Case W8-031
- **Prefecture:** 宮崎県 / **Region Block:** 九州 / **Case Type:** Standard / **User Profile:** 35歳、西都市の回復期病院、夫の転勤で千葉へ / **Entry Route:** LP→LINE / **Difficulty:** Easy
**Scenario:** 夫の転勤で千葉県に引っ越すことが決定。千葉でのDB対応あり。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「夫の転勤で千葉に行きます。千葉で看護師の仕事探してます」
4. Bot: エリア選択表示
5. User: 「千葉県」選択
6. Bot: 施設タイプ→診療科→勤務形態→緊急度
7. User: 「回復期病院」「リハビリ科」「常勤」「1ヶ月以内」
8. Bot: 千葉の施設を提示
**System Behavior Evaluation:** 千葉選択なので正常動作。転勤族の妻という背景は把握されないが、マッチング自体は機能する。入職日の急ぎ具合に対応できるか。
**Results:** Drop-off: 低 / Job Proposal: 千葉施設（適切）/ Next Action: 引越タイミング考慮 / Region Bias: なし / National Expansion Risk: 低
**Failure Category:** なし（軽微なJOB_MATCH_FAIL）/ **Severity:** Low / **Fix Proposal:** 引越日程をヒアリングし入職日と調整 / **Retry Needed:** No / **Auditor Comment:** 正常系。細かい改善余地はあるが致命的ではない。

---

## 鹿児島県 (5 cases)

### Case W8-032
- **Prefecture:** 鹿児島県 / **Region Block:** 九州 / **Case Type:** Standard / **User Profile:** 28歳、鹿児島市の急性期病院、消化器外科、常勤 / **Entry Route:** TikTok→LINE / **Difficulty:** Easy
**Scenario:** 鹿児島市内での転職希望。標準フロー。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「鹿児島で消化器外科の病院探してます」
4. Bot: エリア選択表示
5. User: 「その他の地域」
6. Bot: 施設タイプ→診療科→勤務形態→緊急度
7. User: 「急性期病院」「消化器外科」「常勤」「3ヶ月以内」
8. Bot: 関東施設を提示
**System Behavior Evaluation:** 鹿児島市は人口60万。DB空で関東施設提示。九州全県共通の問題。
**Results:** Drop-off: 高 / Job Proposal: 関東施設（ミスマッチ）/ Next Action: エリア拡大 / Region Bias: 強い / National Expansion Risk: 高
**Failure Category:** GEO_LOCK / **Severity:** Critical / **Fix Proposal:** 九州エリアのDB構築を検討 / **Retry Needed:** Yes / **Auditor Comment:** 鹿児島はドクターヘリ拠点もあり医療需要は高い。

### Case W8-033
- **Prefecture:** 鹿児島県 / **Region Block:** 九州 / **Case Type:** Boundary / **User Profile:** 30歳、奄美大島の県立病院、離島から本土へ / **Entry Route:** Google→LINE / **Difficulty:** Hard
**Scenario:** 奄美大島（鹿児島県）の離島勤務から本土転職。沖縄に近い地理的位置。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「奄美大島からです。本土で働きたいです」
4. Bot: エリア選択表示
5. User: 「その他の地域」
6. Bot: 施設タイプ→診療科→勤務形態→緊急度
7. User: 「総合病院」「救急」「常勤」「半年以内」
8. Bot: 関東施設を提示
**System Behavior Evaluation:** 離島→本土の「本土」が鹿児島本土なのか関東なのか確認なし。離島勤務経験の価値評価もなし。奄美大島は鹿児島県だが沖縄にも近く、文化的にもユニーク。
**Results:** Drop-off: 高 / Job Proposal: 関東施設（意図不明）/ Next Action: 離島医療人材の専門対応 / Region Bias: 強い / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + AMBIG_FAIL / **Severity:** High / **Fix Proposal:** 「本土」の意味を確認する質問+離島経験のスキル評価 / **Retry Needed:** Yes / **Auditor Comment:** 離島看護師は多科経験が豊富。高く評価される人材。

### Case W8-034
- **Prefecture:** 鹿児島県 / **Region Block:** 九州 / **Case Type:** Standard / **User Profile:** 39歳、霧島市の介護施設、施設看護師からの復帰 / **Entry Route:** ブログ→LINE / **Difficulty:** Easy
**Scenario:** 介護施設での勤務歴が長く、病院に戻りたいが技術面での不安あり。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「介護施設にいたので、点滴とか久しぶりで不安です」
4. Bot: エリア選択表示
5. User: 「その他の地域」
6. Bot: フロー進行
7. User: 「療養型」「内科」「常勤」「半年以内」
8. Bot: 関東施設を提示
**System Behavior Evaluation:** ブランク・技術不安への対応なし。復帰支援プログラムのある施設の提案ができない。地域ミスマッチも重なる。
**Results:** Drop-off: 高 / Job Proposal: 関東施設（ミスマッチ）/ Next Action: ブランク看護師向け復帰支援情報の追加 / Region Bias: 強い / National Expansion Risk: 中
**Failure Category:** GEO_LOCK + JOB_MATCH_FAIL / **Severity:** High / **Fix Proposal:** ブランク年数ヒアリング→復帰研修ありの施設を優先提案 / **Retry Needed:** Yes / **Auditor Comment:** 技術不安への寄り添いが離脱防止に直結する。

### Case W8-035
- **Prefecture:** 鹿児島県 / **Region Block:** 九州 / **Case Type:** Adversarial / **User Profile:** 25歳、鹿児島市、深夜3時にLINEメッセージ / **Entry Route:** LINE直接 / **Difficulty:** Medium
**Scenario:** 夜勤明けの深夜3時にLINEでメッセージ。Bot応答の24時間対応を検証。
**Conversation Flow:**
1. User: 深夜3:00に友だち追加
2. Bot: ウェルカムメッセージ（即時？遅延？）
3. User: 「夜勤終わった。もう辞めたい。今すぐ転職したい」
4. Bot: エリア選択表示
5. User: 「その他の地域」
6. Bot: 施設タイプ選択
7. User: 「なんでもいいから夜勤のないとこ」
8. Bot: 施設タイプの選択を強制
9. User: 眠くて離脱
**System Behavior Evaluation:** Botは24時間応答可能（メリット）だが、感情的なユーザーへの寄り添いがない。「辞めたい」「もう無理」は看護師からよくあるSOSだが、Botは機械的にフロー進行。深夜ユーザーの集中力も低い。
**Results:** Drop-off: 高（深夜特有）/ Job Proposal: なし / Next Action: 感情対応モード / Region Bias: 間接的 / National Expansion Risk: 低
**Failure Category:** UX_DROP + AMBIG_FAIL / **Severity:** Medium / **Fix Proposal:** 感情ワード検知→共感メッセージ→翌日リマインドの導線 / **Retry Needed:** No / **Auditor Comment:** 看護師の転職検討は夜勤後に多い。この瞬間を逃さない仕組みが重要。

### Case W8-036
- **Prefecture:** 鹿児島県 / **Region Block:** 九州 / **Case Type:** Standard / **User Profile:** 44歳、指宿市の温泉病院、リハビリ看護 / **Entry Route:** Instagram→LINE / **Difficulty:** Easy
**Scenario:** 指宿の温泉リハビリ病院から一般病院への転職を検討。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「指宿で温泉リハビリやってます。一般病院に移りたいです」
4. Bot: エリア選択→「その他の地域」
5. Bot: 施設タイプ→「一般病院」→診療科→「内科」→勤務形態→「常勤」→緊急度→「3ヶ月以内」
6. Bot: 関東施設を提示
**System Behavior Evaluation:** 温泉リハビリ→一般病院という転職動機は明確だが、DBに地域データがなく対応不可。
**Results:** Drop-off: 高 / Job Proposal: 関東施設（ミスマッチ）/ Next Action: エリア拡大 / Region Bias: 強い / National Expansion Risk: 高
**Failure Category:** GEO_LOCK / **Severity:** High / **Fix Proposal:** エリア外対応の改善 / **Retry Needed:** Yes / **Auditor Comment:** 鹿児島南部は特に医療過疎。対応できれば社会的意義も大きい。

---

## 沖縄県 (4 cases)

### Case W8-037
- **Prefecture:** 沖縄県 / **Region Block:** 沖縄 / **Case Type:** Standard / **User Profile:** 26歳、那覇市の総合病院、外科、常勤 / **Entry Route:** TikTok→LINE / **Difficulty:** Easy
**Scenario:** 沖縄県内での転職希望。沖縄は独自の医療事情（離島多数、米軍基地病院等）。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「那覇で転職考えてます」
4. Bot: エリア選択表示
5. User: 「その他の地域」
6. Bot: 施設タイプ→診療科→勤務形態→緊急度
7. User: 「総合病院」「外科」「常勤」「3ヶ月以内」
8. Bot: 関東施設を提示
**System Behavior Evaluation:** 沖縄→関東は地理的に最も遠い組合せ。沖縄独自の医療環境（離島医療、軍関連病院、観光地の医療需要）に対応する情報が皆無。
**Results:** Drop-off: 極高 / Job Proposal: 関東施設（極端なミスマッチ）/ Next Action: 沖縄エリア対応検討 / Region Bias: 極めて強い / National Expansion Risk: 極高
**Failure Category:** GEO_LOCK + REGION_EXPANSION_FAIL / **Severity:** Critical / **Fix Proposal:** 沖縄の医療事情を踏まえた対応。最低でもエリア外メッセージの改善 / **Retry Needed:** Yes / **Auditor Comment:** 沖縄→関東の提案は最もUXダメージが大きい組合せ。

### Case W8-038
- **Prefecture:** 沖縄県 / **Region Block:** 沖縄 / **Case Type:** Boundary / **User Profile:** 34歳、宮古島の診療所、離島看護師5年目 / **Entry Route:** Google→LINE / **Difficulty:** Hard
**Scenario:** 宮古島の離島医療に従事。離島手当は高いが生活環境に限界を感じている。那覇か本土への転職を検討。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「宮古島で5年やりました。そろそろ都会に出たいです」
4. Bot: エリア選択表示
5. User: 「東京都」選択（都会を目指す）
6. Bot: 施設タイプ→診療科→勤務形態→緊急度
7. User: 「急性期病院」「総合内科」「常勤」「半年以内」
8. Bot: 東京の施設を提示
**System Behavior Evaluation:** 東京選択なので動作自体は正常。しかし離島→都会の大幅な環境変化に対するサポート情報（住居、通勤、生活コスト差）がない。離島5年の経験は高く評価されるべき。
**Results:** Drop-off: 低 / Job Proposal: 東京施設（一応適切）/ Next Action: 離島→都市部転職のサポート情報 / Region Bias: なし / National Expansion Risk: 低
**Failure Category:** JOB_MATCH_FAIL / **Severity:** Low / **Fix Proposal:** 環境変化大の転職者向け情報（寮、生活費比較）を提供 / **Retry Needed:** No / **Auditor Comment:** 離島看護師の都市部転職は増加傾向。サポート情報で差別化可能。

### Case W8-039
- **Prefecture:** 沖縄県 / **Region Block:** 沖縄 / **Case Type:** Adversarial / **User Profile:** 29歳、沖縄市の米軍基地内クリニック（軍雇用員）、日英バイリンガル / **Entry Route:** LINE直接 / **Difficulty:** Hard
**Scenario:** 米軍基地のクリニックから日本の民間病院への転職。特殊な経歴。英語混じりのメッセージ。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「I'm currently working at a military clinic in Okinawa. 日本の病院に転職したいです」
4. Bot: エリア選択表示（英語部分を処理できるか）
5. User: 「Okinawa prefectureで探してます」
6. Bot: エリア選択表示を再度
7. User: 「その他の地域」
8. Bot: フロー進行
9. User: 「bilingual nursing positionってありますか？」
10. Bot: 対応不明→離脱
**System Behavior Evaluation:** 英語混じりの入力に対する対応力がない。バイリンガル看護師は希少人材で高く評価されるが、Botの言語処理は日本語のみの想定。沖縄特有の米軍関連医療人材への対応もゼロ。
**Results:** Drop-off: 高 / Job Proposal: なし / Next Action: 多言語対応の検討 / Region Bias: 間接的 / National Expansion Risk: 中
**Failure Category:** TYPO_FAIL + AMBIG_FAIL + GEO_LOCK / **Severity:** Medium / **Fix Proposal:** 英語テキスト検知→日本語での案内を丁寧に返す。バイリンガル求人のタグ化 / **Retry Needed:** Yes / **Auditor Comment:** 沖縄の米軍医療従事者は転職市場でユニークな存在。ニッチだが対応できれば強み。

### Case W8-040
- **Prefecture:** 沖縄県 / **Region Block:** 沖縄 / **Case Type:** Boundary / **User Profile:** 50歳、石垣島の市立病院、定年間近で那覇へ / **Entry Route:** 紹介→LINE / **Difficulty:** Medium
**Scenario:** 石垣島から那覇への転居を考えている50歳の看護師。沖縄県内の移動だがDB空。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「石垣から那覇に引っ越す予定です。那覇の病院を探してます」
4. Bot: エリア選択表示
5. User: 「その他の地域」
6. Bot: 施設タイプ→診療科→勤務形態→緊急度
7. User: 「総合病院」「内科」「常勤」「3ヶ月以内」
8. Bot: 関東施設を提示
**System Behavior Evaluation:** 沖縄県内（石垣→那覇）の転居にもかかわらず関東施設を提示。ユーザーにとって最も不自然な結果。那覇は沖縄最大都市で病院も多数あるのにカバーできていない。
**Results:** Drop-off: 極高 / Job Proposal: 関東施設（極端なミスマッチ）/ Next Action: 沖縄DB構築 / Region Bias: 極めて強い / National Expansion Risk: 極高
**Failure Category:** GEO_LOCK + REGION_EXPANSION_FAIL / **Severity:** Critical / **Fix Proposal:** 沖縄県内の施設DBを優先構築。離島医療の拠点として需要あり / **Retry Needed:** Yes / **Auditor Comment:** 沖縄県内転居でも関東を提案するのは最もひどいUX。

---

## クロスリージョン: 東京 (2 cases)

### Case W8-041
- **Prefecture:** 東京都 / **Region Block:** 関東 / **Case Type:** Standard / **User Profile:** 32歳、福岡出身、東京の大学病院勤務3年目、地元に戻るか東京残留か / **Entry Route:** LP→LINE / **Difficulty:** Easy
**Scenario:** 福岡出身で東京勤務中。東京で転職するか福岡に戻るか迷っている。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「東京か福岡で迷ってます」
4. Bot: エリア選択表示
5. User: 「東京都」選択
6. Bot: 施設タイプ→診療科→勤務形態→緊急度
7. User: 「大学病院」「消化器内科」「常勤」「半年以内」
8. Bot: 東京の施設を提示
**System Behavior Evaluation:** 東京選択なので正常動作。しかし「東京か福岡で迷っている」という情報は失われ、福岡の選択肢を提示できない。比較検討型ユーザーへの対応不足。
**Results:** Drop-off: 低 / Job Proposal: 東京施設（半分適切）/ Next Action: 複数エリア比較機能 / Region Bias: 中（福岡オプション消失）/ National Expansion Risk: 中
**Failure Category:** AMBIG_FAIL / **Severity:** Low / **Fix Proposal:** 複数エリアの同時検索・比較機能 / **Retry Needed:** No / **Auditor Comment:** 比較検討層は情報提供で囲い込める。

### Case W8-042
- **Prefecture:** 東京都 / **Region Block:** 関東 / **Case Type:** Standard / **User Profile:** 27歳、鹿児島から上京して1年目、東京の急性期で働きたい / **Entry Route:** Instagram→LINE / **Difficulty:** Easy
**Scenario:** Iターン1年目。東京の病院での転職。DB対応エリア。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「東京の急性期で探してます」
4. Bot: エリア選択表示
5. User: 「東京都」選択
6. Bot: 施設タイプ→診療科→勤務形態→緊急度
7. User: 「急性期病院」「救急」「常勤」「3ヶ月以内」
8. Bot: 東京の施設を提示
**System Behavior Evaluation:** 正常動作。東京のDB対応施設から提案。ただし東京は施設数が多いため、絞り込みの精度が問われる。
**Results:** Drop-off: 低 / Job Proposal: 東京施設（適切）/ Next Action: 東京内のエリア絞り込み / Region Bias: なし / National Expansion Risk: 低
**Failure Category:** なし / **Severity:** None / **Fix Proposal:** 東京23区/多摩のサブエリア選択を追加 / **Retry Needed:** No / **Auditor Comment:** 正常系。東京は施設数が多いため細分化が有効。

---

## クロスリージョン: 大阪 (2 cases)

### Case W8-043
- **Prefecture:** 大阪府 / **Region Block:** 関西 / **Case Type:** Boundary / **User Profile:** 33歳、熊本から大阪に引越予定、夫の転職に合わせて / **Entry Route:** LP→LINE / **Difficulty:** Medium
**Scenario:** 熊本から大阪への引越予定だが、大阪はDB対象外。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「来月大阪に引っ越します。大阪で看護師の仕事探してます」
4. Bot: エリア選択表示
5. User: 「その他の地域」
6. Bot: 施設タイプ→診療科→勤務形態→緊急度
7. User: 回答
8. Bot: 関東施設を提示
**System Behavior Evaluation:** 大阪もDB対象外。日本第2の都市をカバーしていないのは関東集中の限界が如実に出る。「その他の地域」選択後に関東施設を提示するのは大阪ユーザーにも違和感大。
**Results:** Drop-off: 高 / Job Proposal: 関東施設（ミスマッチ）/ Next Action: 大阪エリアDB構築 / Region Bias: 極めて強い / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + REGION_EXPANSION_FAIL / **Severity:** Critical / **Fix Proposal:** 大阪は関東に次ぐ優先度でDB構築すべき / **Retry Needed:** Yes / **Auditor Comment:** 大阪非対応は九州ユーザーの大阪転職検討にも影響。

### Case W8-044
- **Prefecture:** 大阪府 / **Region Block:** 関西 / **Case Type:** Adversarial / **User Profile:** 28歳、宮崎出身→大阪在住、Bot言語を関西弁でテスト / **Entry Route:** LINE直接 / **Difficulty:** Hard
**Scenario:** 関西弁でBotに話しかける。方言対応力の検証。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「なんか大阪でええとこないん？」
4. Bot: エリア選択表示
5. User: 「大阪ないやん。なんでなん？」
6. Bot: エリア選択を再表示
7. User: 「ほんま使えんな」→離脱
**System Behavior Evaluation:** 関西弁への対応もゼロ。加えて「なんでないの？」という正当な疑問にも応答できない。ユーザーの不満を放置したまま定型フローを繰り返す。
**Results:** Drop-off: 確実 / Job Proposal: なし / Next Action: 方言対応+エリア外説明 / Region Bias: 強い / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + TYPO_FAIL + UX_DROP / **Severity:** High / **Fix Proposal:** 方言のNLP対応+エリア外説明の自然言語応答 / **Retry Needed:** Yes / **Auditor Comment:** 関西弁ユーザーは多い。最低限の理解は必要。

---

## クロスリージョン: 愛知 (2 cases)

### Case W8-045
- **Prefecture:** 愛知県 / **Region Block:** 東海 / **Case Type:** Standard / **User Profile:** 31歳、大分出身→名古屋在住、名古屋で転職 / **Entry Route:** Google→LINE / **Difficulty:** Easy
**Scenario:** 名古屋での転職希望。愛知はDB対象外。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「名古屋市内で転職したいです」
4. Bot: エリア選択表示
5. User: 「その他の地域」
6. Bot: 施設タイプ→診療科→勤務形態→緊急度
7. User: 回答
8. Bot: 関東施設を提示
**System Behavior Evaluation:** 名古屋は日本第3の都市圏。ここもDB空。三大都市圏のうち東京圏しかカバーしていない事実が顕在化。
**Results:** Drop-off: 高 / Job Proposal: 関東施設（ミスマッチ）/ Next Action: 名古屋エリアDB / Region Bias: 強い / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + REGION_EXPANSION_FAIL / **Severity:** Critical / **Fix Proposal:** 三大都市圏（東京・大阪・名古屋）の優先カバー / **Retry Needed:** Yes / **Auditor Comment:** 名古屋は看護師需要も高い。

### Case W8-046
- **Prefecture:** 愛知県 / **Region Block:** 東海 / **Case Type:** Boundary / **User Profile:** 36歳、福岡出身→名古屋→東京を検討、三拠点で比較 / **Entry Route:** LP→LINE / **Difficulty:** Hard
**Scenario:** 福岡・名古屋・東京の三拠点で比較検討したいが、Botは1エリアしか選べない。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「福岡と名古屋と東京で給料比較したいんですけど」
4. Bot: エリア選択表示（1つのみ）
5. User: 「3つ同時に見れないんですか？」
6. Bot: エリア選択を再表示
7. User: 「東京都」選択（仕方なく1つ選ぶ）
8. Bot: フロー進行
**System Behavior Evaluation:** 複数エリアの同時比較は不可。転職検討者の多くは複数地域を比較するが、この基本ニーズに対応できない。UIの制約がUXを大きく損ねている。
**Results:** Drop-off: 中 / Job Proposal: 東京施設のみ / Next Action: 複数エリア比較機能 / Region Bias: 構造的（1エリア強制）/ National Expansion Risk: 高
**Failure Category:** INPUT_LOCK + UX_DROP / **Severity:** Medium / **Fix Proposal:** 複数エリアの並行検索→比較表示。または地域別の相場情報ページへのリンク / **Retry Needed:** No / **Auditor Comment:** 比較はユーザーの基本行動。対応すべき。

---

## クロスリージョン: 北海道 (2 cases)

### Case W8-047
- **Prefecture:** 北海道 / **Region Block:** 北海道 / **Case Type:** Standard / **User Profile:** 29歳、沖縄出身→札幌に移住予定、寒冷地での生活に不安 / **Entry Route:** Instagram→LINE / **Difficulty:** Medium
**Scenario:** 沖縄から北海道への大移動。北海道もDB対象外。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「札幌で看護師の仕事ありますか？」
4. Bot: エリア選択表示
5. User: 「その他の地域」
6. Bot: 施設タイプ→診療科→勤務形態→緊急度
7. User: 回答
8. Bot: 関東施設を提示
**System Behavior Evaluation:** 沖縄→北海道という日本の端から端への転職でも関東施設を提示。地理的感覚の欠如が最も顕著に現れるケース。
**Results:** Drop-off: 極高 / Job Proposal: 関東施設（極端なミスマッチ）/ Next Action: 北海道DB / Region Bias: 極めて強い / National Expansion Risk: 極高
**Failure Category:** GEO_LOCK + REGION_EXPANSION_FAIL / **Severity:** Critical / **Fix Proposal:** 主要都市（札幌・福岡・大阪・名古屋）のDB優先構築 / **Retry Needed:** Yes / **Auditor Comment:** 沖縄→北海道に関東を勧めるのは笑えないレベル。

### Case W8-048
- **Prefecture:** 北海道 / **Region Block:** 北海道 / **Case Type:** Adversarial / **User Profile:** 40歳、長崎出身→旭川在住、Botに怒りをぶつける / **Entry Route:** LINE直接 / **Difficulty:** Hard
**Scenario:** 北海道在住の元長崎県民。エリア制限に怒りを感じている。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「旭川で探してるんだけど」
4. Bot: エリア選択表示
5. User: 「北海道ないの？ふざけてるの？」
6. Bot: エリア選択を再表示
7. User: 「全国対応って書いてたよね？嘘じゃん」
8. Bot: エリア選択を再表示
9. User: 「消費者センターに通報するわ」→ブロック
**System Behavior Evaluation:** エスカレーションに全く対応できない。「全国対応」の表記がLP/広告にあった場合は景品表示法の問題にもなりうる。怒りのユーザーへの対応は人力ハンドオフが必須。
**Results:** Drop-off: 確実+ブロック+風評リスク / Job Proposal: なし / Next Action: クレーム対応フロー+広告表記確認 / Region Bias: 致命的 / National Expansion Risk: 極高
**Failure Category:** GEO_LOCK + UX_DROP + REGION_EXPANSION_FAIL / **Severity:** Critical / **Fix Proposal:** 1)広告・LPで対応エリアを明記 2)エリア外ユーザーへの丁寧な説明+謝罪 3)クレーム検知→即人力 / **Retry Needed:** Yes / **Auditor Comment:** 法的リスクも含む深刻なケース。広告表記の確認が急務。

---

## クロスリージョン: 神奈川 (2 cases)

### Case W8-049
- **Prefecture:** 神奈川県 / **Region Block:** 関東 / **Case Type:** Standard / **User Profile:** 30歳、福岡から横浜へ転居済み、地元の知人ゼロ / **Entry Route:** LP→LINE / **Difficulty:** Easy
**Scenario:** 福岡から神奈川に引っ越した看護師。神奈川はDB対応エリアで最もデータが充実。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「横浜で働ける病院を探してます」
4. Bot: エリア選択表示
5. User: 「神奈川県」選択
6. Bot: 施設タイプ→診療科→勤務形態→緊急度
7. User: 「総合病院」「循環器内科」「常勤」「1ヶ月以内」
8. Bot: 神奈川の施設を提示（充実した結果）
**System Behavior Evaluation:** 神奈川は本サービスのメインエリア。DB充実。212施設からのマッチングが機能する。横浜エリアの施設が適切に提案されるか。
**Results:** Drop-off: 低 / Job Proposal: 神奈川施設（適切・充実）/ Next Action: マッチング精度の向上 / Region Bias: なし（本拠地）/ National Expansion Risk: なし
**Failure Category:** なし / **Severity:** None / **Fix Proposal:** 横浜市内のサブエリア（18区）選択で絞り込み強化 / **Retry Needed:** No / **Auditor Comment:** 正常系のベストケース。神奈川は問題なし。

### Case W8-050
- **Prefecture:** 神奈川県 / **Region Block:** 関東 / **Case Type:** Boundary / **User Profile:** 28歳、鹿児島出身、川崎在住、実家に帰るか川崎で続けるか / **Entry Route:** TikTok→LINE / **Difficulty:** Medium
**Scenario:** 鹿児島に帰るか神奈川に残るか迷っている。一旦神奈川で検索。
**Conversation Flow:**
1. User: 友だち追加
2. Bot: ウェルカムメッセージ
3. User: 「川崎か鹿児島で迷ってるんですけど、とりあえず川崎で」
4. Bot: エリア選択表示
5. User: 「神奈川県」選択
6. Bot: 施設タイプ→診療科→勤務形態→緊急度
7. User: 「急性期病院」「脳外科」「常勤」「半年以内」
8. Bot: 神奈川の施設を提示
9. User: 「鹿児島の方も見たいんですけど」
10. Bot: エリア選択に戻れるか？
**System Behavior Evaluation:** 神奈川の結果は正常。しかし「鹿児島も見たい」に対し、フローの巻き戻しが可能かが問われる。セッション内で2回目のエリア選択ができるか。鹿児島はDB外なのでそもそも提示不可。
**Results:** Drop-off: 中 / Job Proposal: 神奈川施設（適切）/ Next Action: エリア再選択の導線+エリア外メッセージ / Region Bias: 中（鹿児島非対応）/ National Expansion Risk: 中
**Failure Category:** REENTRY_FAIL + GEO_LOCK / **Severity:** Medium / **Fix Proposal:** セッション内でのエリア再選択を可能に。エリア外の場合は明確に案内 / **Retry Needed:** No / **Auditor Comment:** 迷いユーザーのフロー巻き戻しは必須機能。

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| Total Cases | 50 |
| Standard | 30 |
| Boundary | 12 |
| Adversarial | 8 |
| Severity: Critical | 16 |
| Severity: High | 12 |
| Severity: Medium | 14 |
| Severity: Low | 5 |
| Severity: None | 3 |
| GEO_LOCK | 35 |
| REGION_EXPANSION_FAIL | 11 |
| JOB_MATCH_FAIL | 13 |
| AMBIG_FAIL | 12 |
| UX_DROP | 9 |
| INPUT_LOCK | 5 |
| HUMAN_HANDOFF_FAIL | 3 |
| TYPO_FAIL | 3 |
| REENTRY_FAIL | 1 |

## Key Findings (九州・沖縄 Region)

1. **GEO_LOCK is dominant**: 35/50 cases hit GEO_LOCK. All 8 prefectures in this region have 0 DB facilities. This is the single biggest issue.
2. **福岡 gap is critical**: Japan's 5th largest metro (population 5M+) is completely uncovered. This is a business risk, not just a UX issue.
3. **離島問題**: 長崎(五島列島)、鹿児島(奄美大島)、沖縄(宮古島/石垣島) have unique island healthcare needs that the bot cannot address at all.
4. **方言バリア**: 九州弁・関西弁への対応がゼロ。テキスト入力ユーザーの離脱要因。
5. **「その他の地域」→関東施設** is the worst UX pattern: Users in Okinawa/Kagoshima being shown Tokyo/Kanagawa facilities is absurd and damages brand trust.
6. **広告×エリア制限の矛盾**: SNS広告は全国配信されるため、九州ユーザーの流入は避けられない。エリア外の丁寧な説明が最低限必要。
7. **Cross-region cases (DB対応エリア)**: 10 cross-region cases show the bot works correctly when users select covered areas, but lacks support for remote relocation needs (housing, moving, web interviews).
