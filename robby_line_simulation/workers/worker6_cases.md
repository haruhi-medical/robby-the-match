# Worker 6 - LINE Bot Simulation Test Cases: 中国地方

> **Region:** 中国 (Chugoku)
> **Prefectures:** 鳥取, 島根, 岡山, 広島, 山口
> **Total Cases:** 50 (Main 40 + Cross 10)
> **DB Reality:** 0 facilities in all 5 prefectures. "その他の地域" routes to Kanto results only.
> **Critical Context:** 広島 is a mid-size metro (~1.2M city pop). 山口 borders 福岡. 鳥取/島根 are Japan's least populated prefectures. Users here will be confused/frustrated when offered only Kanto options.

---

## Main Cases: 鳥取県 (7 cases)

---

### Case W6-001
- **Prefecture:** 鳥取県 / **Region Block:** 中国 / **Case Type:** Standard / **User Profile:** 30歳、鳥取大学医学部附属病院の外科病棟看護師 / **Entry Route:** LINE友だち追加 → 自動Welcome / **Difficulty:** Medium

**Scenario:**
鳥取市在住の外科看護師。夜勤回数が多く、日勤のみのクリニックへ転職希望。鳥取県内での転職を前提にBotに相談開始。

**Conversation Flow:**
1. Bot: Welcome メッセージ → エリア選択ボタン表示
2. User: 「鳥取県で探したいです」
3. Bot: il_area選択肢に鳥取県なし → 「その他の地域」を案内
4. User: 「その他の地域」をタップ
5. Bot: 施設タイプ選択 → クリニック選択
6. User: 「クリニック」をタップ
7. Bot: 診療科選択
8. User: 「外科」
9. Bot: 勤務形態選択
10. User: 「日勤のみ」→ マッチング結果表示（関東の施設のみ）

**System Behavior Evaluation:**
- 鳥取県の選択肢がないことへの説明が不足
- 「その他の地域」選択後のフロー内で一切「関東の結果です」という注記なし
- ユーザーは鳥取の結果が出ると思い込んだまま関東施設を提示される

**Results:**
- Drop-off: HIGH（関東施設提示時に離脱確実）
- Job Proposal: 関東の外科クリニック（ユーザー意図と地域不一致）
- Next Action: 鳥取県内は対応不可の旨を明示し、LINE相談へ誘導すべき
- Region Bias: 関東偏重（鳥取DB=0件）
- National Expansion Risk: HIGH — 鳥取ユーザーへの信頼喪失

**Failure Category:** Region Mismatch / Silent Redirect
**Severity:** Critical
**Fix Proposal:** 「その他の地域」選択時に「現在、関東エリア（東京・神奈川・千葉・埼玉）の求人のみご紹介可能です。鳥取県の求人は担当者が個別にお探しします」と明示
**Retry Needed:** Yes
**Auditor Comment:** 鳥取県は人口最少県。地元志向が極めて強く、関東提示は完全なミスマッチ。

---

### Case W6-002
- **Prefecture:** 鳥取県 / **Region Block:** 中国 / **Case Type:** Boundary / **User Profile:** 25歳、米子市の回復期リハビリ病棟看護師 / **Entry Route:** Instagram広告 → LINE / **Difficulty:** Hard

**Scenario:**
米子市は島根県境に近い。松江市（島根）も通勤圏内。県境をまたぐ転職希望だが、Bot選択肢にどちらの県もない。

**Conversation Flow:**
1. Bot: Welcome メッセージ
2. User: 「米子か松江あたりで転職したいんですが」
3. Bot: エリア選択ボタン表示（東京都/神奈川県/千葉県/埼玉県/その他の地域）
4. User: 「...その他の地域ですかね」
5. Bot: 施設タイプ選択
6. User: 「病院」
7. Bot: 診療科選択
8. User: 「リハビリ科」
9. Bot: 勤務形態 → 日勤のみ → マッチング
10. User: 関東の結果を見て「え？米子の求人は？」

**System Behavior Evaluation:**
- 米子・松江という具体的な地名に一切反応できない
- 県境通勤という現実的なニーズに対応する仕組みなし
- フリーテキストの地名入力を活用できていない

**Results:**
- Drop-off: VERY HIGH
- Job Proposal: 関東のリハビリ病院（完全不一致）
- Next Action: 「鳥取・島根エリアは個別対応」と早期に案内
- Region Bias: 致命的
- National Expansion Risk: HIGH

**Failure Category:** Geography Parsing Failure / Cross-Prefecture Blindspot
**Severity:** Critical
**Fix Proposal:** フリーテキストで地名入力された場合、対応エリア外なら即座に人間オペレーター接続を案内
**Retry Needed:** Yes
**Auditor Comment:** 米子-松江は山陰の主要都市圏。この通勤圏を無視するのは致命的。

---

### Case W6-003
- **Prefecture:** 鳥取県 / **Region Block:** 中国 / **Case Type:** Standard / **User Profile:** 40歳、鳥取赤十字病院のベテラン看護師 / **Entry Route:** Google検索 → LINE / **Difficulty:** Easy

**Scenario:**
管理職候補として条件の良い病院を探している。鳥取県内の大規模病院は限られているため、広域での検索を希望。

**Conversation Flow:**
1. Bot: Welcome → エリア選択
2. User: 「その他の地域」をタップ
3. Bot: 施設タイプ選択
4. User: 「病院」
5. Bot: 診療科 → 「内科」
6. Bot: 勤務形態 → 「常勤（夜勤あり）」
7. Bot: 緊急度 → 「3ヶ月以内」
8. Bot: マッチング結果 → 関東の病院リスト表示

**System Behavior Evaluation:**
- フロー自体はスムーズに完走
- しかし40歳管理職候補に関東の一般求人を出す意味がない
- 「鳥取で管理職」という高単価案件の可能性を逃している

**Results:**
- Drop-off: HIGH（結果画面で離脱）
- Job Proposal: 関東の一般病院（ミスマッチ）
- Next Action: 管理職案件は個別対応として担当者接続
- Region Bias: 関東限定
- National Expansion Risk: MEDIUM

**Failure Category:** Region Mismatch / Value Loss
**Severity:** High
**Fix Proposal:** 管理職・高条件案件は自動マッチング不適。早期にハンドオフ
**Retry Needed:** No
**Auditor Comment:** 紹介手数料10%でも管理職年収600万なら60万。逃すべきでない。

---

### Case W6-004
- **Prefecture:** 鳥取県 / **Region Block:** 中国 / **Case Type:** Adversarial / **User Profile:** 22歳、新卒看護師（鳥取看護大学卒） / **Entry Route:** TikTok → LINE / **Difficulty:** Hard

**Scenario:**
新卒で就職先を探しているが、Botは転職前提の設計。「就職」と「転職」の違いに対応できるか。さらに鳥取県という対象外エリア。

**Conversation Flow:**
1. Bot: Welcome
2. User: 「来年4月から働ける病院を探してます！新卒です」
3. Bot: エリア選択表示（新卒への分岐なし）
4. User: 「鳥取か岡山がいいです」
5. Bot: 選択肢に該当なし → 「その他の地域」へ
6. User: 「その他の地域」
7. Bot: 施設タイプ選択（通常フロー続行）
8. User: 「病院」→ 診療科 → 勤務形態
9. Bot: マッチング結果（関東・中途向け求人）
10. User: 「新卒OKのところありますか？」→ Bot応答不可

**System Behavior Evaluation:**
- 新卒/中途の区別なし
- 新卒特有のニーズ（教育体制、プリセプター制度等）に対応不可
- 二重の問題：エリア外 + 対象者外

**Results:**
- Drop-off: VERY HIGH
- Job Proposal: 中途向け関東求人（完全不適切）
- Next Action: 新卒は別フロー or 人間対応必須
- Region Bias: 関東偏重
- National Expansion Risk: HIGH

**Failure Category:** User Segment Mismatch + Region Mismatch
**Severity:** Critical
**Fix Proposal:** Q1で新卒/中途分岐を追加。新卒は即ハンドオフ
**Retry Needed:** Yes
**Auditor Comment:** TikTok経由の若年層に新卒が混ざるのは想定すべき。

---

### Case W6-005
- **Prefecture:** 鳥取県 / **Region Block:** 中国 / **Case Type:** Standard / **User Profile:** 35歳、倉吉市の訪問看護師 / **Entry Route:** LINE友だち追加 / **Difficulty:** Medium

**Scenario:**
訪問看護ステーションから病院への転職希望。倉吉市は鳥取県中部の小都市。

**Conversation Flow:**
1. Bot: Welcome → エリア選択
2. User: 「その他の地域」
3. Bot: 施設タイプ → 「病院」
4. User: 「病院」
5. Bot: 診療科 → 「内科」
6. Bot: 勤務形態 → 「日勤のみ」
7. Bot: 緊急度 → 「半年以内」
8. Bot: マッチング → 関東施設表示

**System Behavior Evaluation:**
- 訪問看護→病院という転職パターンは一般的だが、Botがキャリアチェンジの文脈を理解していない
- 倉吉市という地名への対応なし
- 「半年以内」という余裕ある時間軸なのに、担当者紹介の余地を活かしていない

**Results:**
- Drop-off: HIGH
- Job Proposal: 関東病院（地域不一致）
- Next Action: 担当者による個別対応案内
- Region Bias: 関東限定
- National Expansion Risk: MEDIUM

**Failure Category:** Region Mismatch
**Severity:** High
**Fix Proposal:** 緊急度「半年以内」以上は自動マッチングより担当者紹介を優先
**Retry Needed:** No
**Auditor Comment:** 時間的余裕がある案件こそ丁寧な個別対応で成約率が上がる。

---

### Case W6-006
- **Prefecture:** 鳥取県 / **Region Block:** 中国 / **Case Type:** Boundary / **User Profile:** 28歳、鳥取県立中央病院のICU看護師 / **Entry Route:** 友人紹介 → LINE / **Difficulty:** Medium

**Scenario:**
ICU経験5年。スキルアップのため都市部への転居も視野に入れている。鳥取→関東の転居転職は現実的だが、Botがその文脈を拾えるか。

**Conversation Flow:**
1. Bot: Welcome → エリア選択
2. User: 「東京か神奈川で考えてます。今は鳥取にいるんですが引っ越すつもりです」
3. Bot: エリア選択肢表示
4. User: 「東京都」をタップ
5. Bot: 施設タイプ → 「病院」
6. Bot: 診療科 → 「救急科」
7. Bot: 勤務形態 → 「常勤（夜勤あり）」
8. Bot: 緊急度 → 「3ヶ月以内」
9. Bot: マッチング → 東京の救急病院表示
10. User: 「引っ越し支援とかありますか？」→ Bot応答なし

**System Behavior Evaluation:**
- 東京選択でフローは正常動作
- ただし転居前提の追加情報（住居支援、赴任手当等）に一切触れない
- ICU5年は高スキル人材だが、スキルレベルに応じた施設推薦ができない

**Results:**
- Drop-off: LOW（フロー完走するが追加質問で詰まる）
- Job Proposal: 東京の救急病院（方向性は合致）
- Next Action: 転居支援の有無を担当者から説明
- Region Bias: なし（ユーザー自身が関東を選択）
- National Expansion Risk: LOW

**Failure Category:** Context Insensitivity / Missing Follow-up
**Severity:** Medium
**Fix Proposal:** 現住所と希望エリアが異なる場合、転居支援情報を自動付与
**Retry Needed:** No
**Auditor Comment:** 鳥取→東京は成功パターン。転居支援の案内があれば成約率向上。

---

### Case W6-007
- **Prefecture:** 鳥取県 / **Region Block:** 中国 / **Case Type:** Adversarial / **User Profile:** 45歳、境港市の介護施設勤務（准看護師） / **Entry Route:** Google広告 → LINE / **Difficulty:** Hard

**Scenario:**
准看護師が正看護師取得後の転職先を探している。Botは准看/正看の区別なし。さらに境港市は島根県境。

**Conversation Flow:**
1. Bot: Welcome
2. User: 「准看なんですが、来年正看取れるので転職考えてます」
3. Bot: エリア選択（准看/正看の分岐なし）
4. User: 「その他の地域」
5. Bot: 施設タイプ選択
6. User: 「介護施設」
7. Bot: 選択肢に「介護施設」がない場合 → ユーザー混乱
8. User: 「クリニックでいいです...」
9. Bot: 診療科 → 勤務形態 → マッチング（関東）
10. User: 「境港で働きたいんですが...」→ 対応不可

**System Behavior Evaluation:**
- 准看護師の資格状況に対応不可
- 介護施設が施設タイプ選択肢にない可能性
- 「来年正看取得」という将来の条件変化に対応不可

**Results:**
- Drop-off: VERY HIGH
- Job Proposal: 関東クリニック（完全不一致）
- Next Action: 資格取得予定者は担当者による個別対応
- Region Bias: 関東限定
- National Expansion Risk: HIGH

**Failure Category:** Qualification Blindspot + Region Mismatch + Facility Type Gap
**Severity:** Critical
**Fix Proposal:** 准看/正看の分岐追加。介護施設を施設タイプに追加。資格取得予定者フラグ
**Retry Needed:** Yes
**Auditor Comment:** 三重の問題が重なる最悪ケース。一つでも拾えれば離脱を防げた。

---

## Main Cases: 島根県 (7 cases)

---

### Case W6-008
- **Prefecture:** 島根県 / **Region Block:** 中国 / **Case Type:** Standard / **User Profile:** 32歳、松江市の総合病院勤務（内科病棟） / **Entry Route:** LINE検索 → 友だち追加 / **Difficulty:** Medium

**Scenario:**
松江市内の別の病院へ転職希望。島根県の看護師は県内転職が基本だが、DBに島根の施設は0件。

**Conversation Flow:**
1. Bot: Welcome → エリア選択
2. User: 「島根県松江市です」
3. Bot: 選択肢に島根なし → 「その他の地域」を案内
4. User: 「その他の地域」
5. Bot: 施設タイプ → 「病院」
6. Bot: 診療科 → 「内科」
7. Bot: 勤務形態 → 「常勤（夜勤あり）」
8. Bot: 緊急度 → 「すぐにでも」
9. Bot: マッチング → 関東の内科病院表示
10. User: 「松江市の病院じゃないんですか？」

**System Behavior Evaluation:**
- 「すぐにでも」という緊急度の高いユーザーに対して、地域外の結果しか出せない
- 松江市は島根県最大都市で病院数もあるのに、DB未収録で機会損失

**Results:**
- Drop-off: VERY HIGH
- Job Proposal: 関東内科病院（地域完全不一致）
- Next Action: 緊急度高→即座に担当者ホットライン案内
- Region Bias: 致命的
- National Expansion Risk: HIGH

**Failure Category:** Region Mismatch / Urgency-Response Gap
**Severity:** Critical
**Fix Proposal:** 緊急度「すぐにでも」×対象外エリア → 即座に電話/LINE相談へエスカレーション
**Retry Needed:** Yes
**Auditor Comment:** 転職意欲最大のユーザーを逃す最悪パターン。

---

### Case W6-009
- **Prefecture:** 島根県 / **Region Block:** 中国 / **Case Type:** Standard / **User Profile:** 27歳、出雲市の産婦人科クリニック看護師 / **Entry Route:** Instagram → LINE / **Difficulty:** Easy

**Scenario:**
出雲大社のある出雲市で、産婦人科から小児科への転科を希望。

**Conversation Flow:**
1. Bot: Welcome → エリア選択
2. User: 「その他の地域」
3. Bot: 施設タイプ → 「クリニック」
4. Bot: 診療科 → 「小児科」
5. Bot: 勤務形態 → 「日勤のみ」
6. Bot: 緊急度 → 「半年以内」
7. Bot: マッチング → 関東の小児科クリニック

**System Behavior Evaluation:**
- フロー自体はスムーズに完走
- 転科希望（産婦人科→小児科）の文脈を拾えない
- 出雲市の求人は0件

**Results:**
- Drop-off: HIGH
- Job Proposal: 関東小児科クリニック（地域不一致）
- Next Action: 島根県内の小児科求人を担当者が探す旨を案内
- Region Bias: 関東限定
- National Expansion Risk: MEDIUM

**Failure Category:** Region Mismatch
**Severity:** High
**Fix Proposal:** 「その他の地域」完走後に「ご希望の地域の求人は担当者が個別にお探しします」を表示
**Retry Needed:** No
**Auditor Comment:** 転科希望は丁寧な対応で成約しやすい案件。自動マッチングだけでは不十分。

---

### Case W6-010
- **Prefecture:** 島根県 / **Region Block:** 中国 / **Case Type:** Adversarial / **User Profile:** 50歳、隠岐の島の診療所看護師 / **Entry Route:** LINE友だち追加 / **Difficulty:** Hard

**Scenario:**
離島（隠岐諸島）勤務。本土への転職希望だが、離島という特殊環境への理解がBotにあるか。

**Conversation Flow:**
1. Bot: Welcome
2. User: 「隠岐の島から本土に戻りたいんですが」
3. Bot: エリア選択表示（「隠岐」を理解できない）
4. User: 「島根県の松江あたりで」
5. Bot: 「その他の地域」を案内
6. User: 「その他の地域」→ フロー進行
7. Bot: 施設タイプ → 「病院」
8. Bot: 診療科 → 「総合内科」（選択肢になければ「内科」）
9. Bot: マッチング → 関東病院表示
10. User: 「松江の病院が見たかったんですが...もういいです」

**System Behavior Evaluation:**
- 離島→本土という転職パターンに対応不可
- 隠岐の島という地名を解釈できない
- 50歳のベテランが持つ離島医療経験は非常に貴重だが、その価値を活かせない

**Results:**
- Drop-off: VERY HIGH（「もういいです」で完全離脱）
- Job Proposal: 関東病院（完全不一致）
- Next Action: 離島医療経験者は高価値人材。即ハンドオフ
- Region Bias: 致命的
- National Expansion Risk: HIGH

**Failure Category:** Special Context Blindspot / Region Mismatch / Value Loss
**Severity:** Critical
**Fix Proposal:** 離島・僻地キーワード検出時、特別対応フラグを立てて即ハンドオフ
**Retry Needed:** Yes
**Auditor Comment:** 離島医療経験20年超は破格の人材。手数料10%でも高額案件になり得る。

---

### Case W6-011
- **Prefecture:** 島根県 / **Region Block:** 中国 / **Case Type:** Boundary / **User Profile:** 29歳、浜田市の精神科病院看護師 / **Entry Route:** ブログ記事 → LINE / **Difficulty:** Medium

**Scenario:**
浜田市は島根県西部で広島県に近い。広島市への通勤は片道2時間以上だが転居も考慮中。

**Conversation Flow:**
1. Bot: Welcome → エリア選択
2. User: 「広島か島根で精神科の求人ありますか？」
3. Bot: エリア選択肢表示（どちらもない）
4. User: 「その他の地域」
5. Bot: 施設タイプ → 「病院」
6. Bot: 診療科 → 「精神科」
7. Bot: 勤務形態 → 「常勤（夜勤あり）」
8. Bot: マッチング → 関東の精神科病院

**System Behavior Evaluation:**
- 広島・島根の二県にまたがる希望に対応不可
- 精神科は専門性が高く、マッチング精度が重要
- 二県とも0件

**Results:**
- Drop-off: HIGH
- Job Proposal: 関東精神科病院（地域不一致）
- Next Action: 精神科専門の個別対応
- Region Bias: 関東限定
- National Expansion Risk: MEDIUM

**Failure Category:** Multi-Prefecture Request + Region Mismatch
**Severity:** High
**Fix Proposal:** 複数県の希望をフリーテキストから検出し、対応可否を明示
**Retry Needed:** No
**Auditor Comment:** 精神科看護師は需要が高い。島根・広島エリアでも紹介可能な案件はあるはず。

---

### Case W6-012
- **Prefecture:** 島根県 / **Region Block:** 中国 / **Case Type:** Standard / **User Profile:** 38歳、益田市の訪問看護ステーション管理者 / **Entry Route:** LINE / **Difficulty:** Medium

**Scenario:**
訪問看護ステーションの管理者だが、病院への復帰を検討。益田市は島根県最西端で山口県に近い。

**Conversation Flow:**
1. Bot: Welcome → エリア選択
2. User: 「その他の地域」
3. Bot: 施設タイプ → 「病院」
4. Bot: 診療科 → 「内科」
5. Bot: 勤務形態 → 「日勤のみ」
6. Bot: 緊急度 → 「情報収集中」
7. Bot: マッチング → 関東病院

**System Behavior Evaluation:**
- 管理者→スタッフへのキャリアダウンに言及なし
- 「情報収集中」なのに即マッチング結果を出す必要があるか
- 益田市→山口県萩市も通勤圏だが考慮されない

**Results:**
- Drop-off: MEDIUM（情報収集段階なので怒りは少ないが再利用なし）
- Job Proposal: 関東病院
- Next Action: 情報収集段階 → メルマガ的な定期情報提供が適切
- Region Bias: 関東限定
- National Expansion Risk: LOW

**Failure Category:** Region Mismatch / Urgency Mishandling
**Severity:** Medium
**Fix Proposal:** 「情報収集中」選択時は即マッチングではなく定期的な求人配信を案内
**Retry Needed:** No
**Auditor Comment:** 情報収集段階のユーザーにはナーチャリングが有効。

---

### Case W6-013
- **Prefecture:** 島根県 / **Region Block:** 中国 / **Case Type:** Adversarial / **User Profile:** 24歳、島根県立大学看護学部卒・津和野町の診療所勤務 / **Entry Route:** TikTok → LINE / **Difficulty:** Hard

**Scenario:**
津和野町は人口7,000人の過疎地。「こんな田舎じゃ転職先ない」とBot利用。自虐的・ネガティブな入力をする。

**Conversation Flow:**
1. Bot: Welcome
2. User: 「田舎すぎて転職先ないんですけどw」
3. Bot: エリア選択表示（感情に対応できず）
4. User: 「まあ島根なんで無理ですよね」
5. Bot: エリア選択を再表示
6. User: 「その他の地域」
7. Bot: 通常フロー進行
8. User: 「どうせ関東の求人でしょ」
9. Bot: マッチング → 関東求人表示
10. User: 「やっぱりね」→ 離脱

**System Behavior Evaluation:**
- ネガティブ感情に対する共感応答なし
- 「田舎」「無理」といったキーワードへの対応なし
- ユーザーの予想通りの結果を出してしまい、不信感を確認させてしまう

**Results:**
- Drop-off: CERTAIN
- Job Proposal: 関東求人（予想通りの失望）
- Next Action: 共感→「地方でも求人はあります。担当者が一緒に探します」
- Region Bias: 致命的
- National Expansion Risk: HIGH（SNSで拡散されるリスク）

**Failure Category:** Emotional Intelligence Gap / Region Mismatch
**Severity:** Critical
**Fix Proposal:** ネガティブ入力検出 → 共感メッセージ + 即ハンドオフ。「地方=無理」の印象を与えない
**Retry Needed:** Yes
**Auditor Comment:** TikTok世代はネガティブ体験をSNSで共有する。ブランドリスク大。

---

### Case W6-014
- **Prefecture:** 島根県 / **Region Block:** 中国 / **Case Type:** Standard / **User Profile:** 33歳、松江市の透析クリニック看護師 / **Entry Route:** LINE / **Difficulty:** Easy

**Scenario:**
透析看護の専門性を活かした転職希望。松江市内で。

**Conversation Flow:**
1. Bot: Welcome → エリア選択
2. User: 「その他の地域」
3. Bot: 施設タイプ → 「クリニック」
4. Bot: 診療科 → 「腎臓内科」（なければ「内科」）
5. Bot: 勤務形態 → 「日勤のみ」
6. Bot: マッチング → 関東クリニック

**System Behavior Evaluation:**
- 透析看護という専門スキルに対応する診療科選択肢がない可能性
- 専門性の高い看護師ほど、的外れな結果に失望が大きい

**Results:**
- Drop-off: HIGH
- Job Proposal: 関東内科クリニック（専門性不一致の可能性）
- Next Action: 透析専門の求人を個別に探す案内
- Region Bias: 関東限定
- National Expansion Risk: MEDIUM

**Failure Category:** Specialty Matching Gap + Region Mismatch
**Severity:** High
**Fix Proposal:** 専門分野（透析・オペ室・ICU等）の選択肢を追加
**Retry Needed:** No
**Auditor Comment:** 透析看護師は需要が高い。専門性を活かしたマッチングが必要。

---

## Main Cases: 岡山県 (7 cases)

---

### Case W6-015
- **Prefecture:** 岡山県 / **Region Block:** 中国 / **Case Type:** Standard / **User Profile:** 31歳、岡山大学病院の循環器内科看護師 / **Entry Route:** LINE友だち追加 / **Difficulty:** Medium

**Scenario:**
岡山市は「中国・四国の医療拠点」。大学病院から民間病院への転職希望。岡山の医療は充実しているが、DB=0件。

**Conversation Flow:**
1. Bot: Welcome → エリア選択
2. User: 「岡山県内で探しています」
3. Bot: 選択肢に岡山なし → 「その他の地域」へ
4. User: 「その他の地域」
5. Bot: 施設タイプ → 「病院」
6. Bot: 診療科 → 「循環器内科」（なければ「内科」）
7. Bot: 勤務形態 → 「常勤（夜勤あり）」
8. Bot: 緊急度 → 「3ヶ月以内」
9. Bot: マッチング → 関東の病院表示
10. User: 「岡山の病院が見たいんですが...」

**System Behavior Evaluation:**
- 岡山は医療都市として有名（岡山大学病院、倉敷中央病院等）
- 大学病院経験者は高スキル人材
- 岡山県内で十分な選択肢があるはずなのにDB未登録

**Results:**
- Drop-off: VERY HIGH
- Job Proposal: 関東病院（岡山の医療水準を知るユーザーにとってミスマッチ）
- Next Action: 岡山県の求人を個別に探す案内
- Region Bias: 致命的
- National Expansion Risk: HIGH

**Failure Category:** Region Mismatch / Market Awareness Gap
**Severity:** Critical
**Fix Proposal:** 岡山は医療集積地。DB拡充の優先度が高い
**Retry Needed:** Yes
**Auditor Comment:** 岡山は「医療のメッカ」。ここの看護師を取りこぼすのは事業上の大損失。

---

### Case W6-016
- **Prefecture:** 岡山県 / **Region Block:** 中国 / **Case Type:** Boundary / **User Profile:** 26歳、倉敷市の急性期病院看護師 / **Entry Route:** Instagram広告 → LINE / **Difficulty:** Medium

**Scenario:**
倉敷市から岡山市内への転職を希望。倉敷中央病院（全国トップクラス）の近くで働きたい。

**Conversation Flow:**
1. Bot: Welcome → エリア選択
2. User: 「岡山市内の大きい病院で働きたいです」
3. Bot: 選択肢表示
4. User: 「その他の地域」
5. Bot: 施設タイプ → 「病院」
6. Bot: 診療科 → 「救急科」
7. Bot: 勤務形態 → 「常勤（夜勤あり）」
8. Bot: マッチング → 関東の急性期病院

**System Behavior Evaluation:**
- 「大きい病院」という希望に対する規模フィルターなし
- 倉敷→岡山という近距離転職のニーズに対応不可

**Results:**
- Drop-off: HIGH
- Job Proposal: 関東急性期病院
- Next Action: 岡山市内の大規模病院リストを担当者から提供
- Region Bias: 関東限定
- National Expansion Risk: MEDIUM

**Failure Category:** Region Mismatch / Scale Filter Missing
**Severity:** High
**Fix Proposal:** 病院規模（大規模/中規模/小規模）のフィルター追加
**Retry Needed:** No
**Auditor Comment:** 倉敷中央病院は全国的に有名。この知名度を活用すべき。

---

### Case W6-017
- **Prefecture:** 岡山県 / **Region Block:** 中国 / **Case Type:** Standard / **User Profile:** 42歳、津山市の療養型病院看護師長 / **Entry Route:** Google → LINE / **Difficulty:** Medium

**Scenario:**
看護師長だが施設の経営不安から転職検討。津山市は岡山県北部の山間部。

**Conversation Flow:**
1. Bot: Welcome → エリア選択
2. User: 「その他の地域」
3. Bot: 施設タイプ → 「病院」
4. Bot: 診療科 → 「内科」
5. Bot: 勤務形態 → 「日勤のみ」
6. Bot: 緊急度 → 「1ヶ月以内」
7. Bot: マッチング → 関東病院

**System Behavior Evaluation:**
- 看護師長という役職情報を取得する項目がない
- 施設の経営不安という転職理由に対応するカウンセリング機能なし
- 緊急度高なのに地域外の結果のみ

**Results:**
- Drop-off: VERY HIGH
- Job Proposal: 関東病院（役職・地域不一致）
- Next Action: 管理職案件は個別対応必須
- Region Bias: 関東限定
- National Expansion Risk: HIGH

**Failure Category:** Region Mismatch / Role-Level Blindspot
**Severity:** Critical
**Fix Proposal:** 役職（師長/主任/スタッフ）の質問を追加。管理職は即ハンドオフ
**Retry Needed:** Yes
**Auditor Comment:** 看護師長の転職は紹介手数料が高額。確実に拾うべき。

---

### Case W6-018
- **Prefecture:** 岡山県 / **Region Block:** 中国 / **Case Type:** Adversarial / **User Profile:** 23歳、岡山市の美容クリニック看護師 / **Entry Route:** TikTok → LINE / **Difficulty:** Hard

**Scenario:**
美容クリニックから一般病院への転職を検討。「美容から一般に戻れるか不安」という相談をBotにしてくる。

**Conversation Flow:**
1. Bot: Welcome
2. User: 「美容クリニックで働いてるんですけど、一般病院に戻れますかね？」
3. Bot: エリア選択表示（相談には答えず）
4. User: 「あ、まず質問に答えないとダメですか」
5. Bot: エリア選択を再表示
6. User: 「その他の地域」
7. Bot: 施設タイプ → 「病院」
8. Bot: 通常フロー → マッチング → 関東病院
9. User: 「で、美容から戻れるかの質問は...」
10. Bot: 応答なし or 定型文

**System Behavior Evaluation:**
- キャリア相談に一切対応できない
- フロー強制が強すぎてユーザー体験が悪い
- 美容→一般という転職パターンへの助言機能なし

**Results:**
- Drop-off: HIGH
- Job Proposal: 関東病院（相談したかったのに結果だけ）
- Next Action: キャリア相談は人間カウンセラーへ接続
- Region Bias: 関東限定
- National Expansion Risk: MEDIUM

**Failure Category:** Career Counseling Gap / Flow Rigidity
**Severity:** High
**Fix Proposal:** 質問形式の入力を検出 → 「キャリア相談は担当者にお繋ぎします」と案内
**Retry Needed:** Yes
**Auditor Comment:** 相談型ユーザーは成約率が高い。Botで切り捨てるのは損失。

---

### Case W6-019
- **Prefecture:** 岡山県 / **Region Block:** 中国 / **Case Type:** Standard / **User Profile:** 36歳、玉野市の小規模病院看護師 / **Entry Route:** LINE / **Difficulty:** Easy

**Scenario:**
玉野市は岡山市南部の港町。高松市（香川県）へのフェリー通勤も可能な特殊な立地。

**Conversation Flow:**
1. Bot: Welcome → エリア選択
2. User: 「その他の地域」
3. Bot: 施設タイプ → 「病院」
4. Bot: 診療科 → 「整形外科」
5. Bot: 勤務形態 → 「日勤のみ」
6. Bot: 緊急度 → 「3ヶ月以内」
7. Bot: マッチング → 関東整形外科病院

**System Behavior Evaluation:**
- 玉野市→高松市という県境・海峡越えの通勤可能性に対応不可
- 標準的なフロー完走だが結果は無意味

**Results:**
- Drop-off: HIGH
- Job Proposal: 関東整形外科（地域不一致）
- Next Action: 岡山・香川の求人を個別案内
- Region Bias: 関東限定
- National Expansion Risk: MEDIUM

**Failure Category:** Region Mismatch
**Severity:** High
**Fix Proposal:** 中国・四国エリアのDB構築を検討
**Retry Needed:** No
**Auditor Comment:** 瀬戸内海エリアは県境を越えた通勤が一般的。エリアの考え方を再設計すべき。

---

### Case W6-020
- **Prefecture:** 岡山県 / **Region Block:** 中国 / **Case Type:** Boundary / **User Profile:** 30歳、笠岡市の介護老人保健施設看護師 / **Entry Route:** 友人紹介 → LINE / **Difficulty:** Medium

**Scenario:**
笠岡市は広島県福山市と隣接。福山市内の病院も通勤圏。

**Conversation Flow:**
1. Bot: Welcome → エリア選択
2. User: 「笠岡か福山あたりで病院の求人ありますか？」
3. Bot: エリア選択肢表示（どちらの地名も認識できず）
4. User: 「その他の地域」
5. Bot: 通常フロー → マッチング → 関東病院
6. User: 「福山の求人が見たかったんですけど...」

**System Behavior Evaluation:**
- 笠岡-福山の生活圏を理解できない
- フリーテキストの地名を無視してフロー強制

**Results:**
- Drop-off: HIGH
- Job Proposal: 関東病院
- Next Action: 岡山県西部・広島県東部の求人を個別案内
- Region Bias: 関東限定
- National Expansion Risk: MEDIUM

**Failure Category:** Cross-Prefecture Blindspot / Region Mismatch
**Severity:** High
**Fix Proposal:** 隣接県をまたぐ生活圏の概念をマッチングに導入
**Retry Needed:** No
**Auditor Comment:** 笠岡-福山は完全な一体生活圏。県境で分けるのは非現実的。

---

### Case W6-021
- **Prefecture:** 岡山県 / **Region Block:** 中国 / **Case Type:** Adversarial / **User Profile:** 28歳、総社市の看護師（育休中） / **Entry Route:** LINE / **Difficulty:** Hard

**Scenario:**
育休中で復帰先を変えたい。時短勤務が条件だが、Botに時短の選択肢がない。

**Conversation Flow:**
1. Bot: Welcome
2. User: 「育休中なんですが、復帰先を変えたくて。時短で働ける病院探してます」
3. Bot: エリア選択表示
4. User: 「その他の地域」
5. Bot: 施設タイプ → 「病院」
6. Bot: 診療科 → 「小児科」（子育て経験から）
7. Bot: 勤務形態 → 「日勤のみ」（時短の選択肢なし）
8. Bot: マッチング → 関東病院（フルタイム前提）
9. User: 「時短勤務できるところはないですか？」
10. Bot: 対応不可

**System Behavior Evaluation:**
- 育休中・時短勤務という重要な条件に対応不可
- 勤務形態の選択肢が不十分（時短/パート/週3等がない）
- 育休→転職は法的にもデリケートだが配慮なし

**Results:**
- Drop-off: HIGH
- Job Proposal: 関東フルタイム求人（条件不一致）
- Next Action: 時短勤務対応可能な施設を個別に探す
- Region Bias: 関東限定
- National Expansion Risk: MEDIUM

**Failure Category:** Working Condition Gap / Region Mismatch
**Severity:** High
**Fix Proposal:** 勤務形態に「時短勤務」「パート」を追加。育休中フラグで法的注意喚起
**Retry Needed:** Yes
**Auditor Comment:** 育休中の転職相談は増加傾向。対応できないのは機会損失。

---

## Main Cases: 広島県 (8 cases)

---

### Case W6-022
- **Prefecture:** 広島県 / **Region Block:** 中国 / **Case Type:** Standard / **User Profile:** 29歳、広島市立広島市民病院のER看護師 / **Entry Route:** LINE友だち追加 / **Difficulty:** Medium

**Scenario:**
広島市は政令指定都市で人口119万人。ER経験を活かして別の急性期病院へ。広島は大都市なのにDB=0件。

**Conversation Flow:**
1. Bot: Welcome → エリア選択
2. User: 「広島市内で急性期の病院探してます」
3. Bot: 選択肢に広島なし
4. User: 「え、広島ないんですか？」
5. Bot: 「その他の地域」を案内（説明不足）
6. User: 「その他の地域」
7. Bot: 施設タイプ → 「病院」→ 診療科 → 「救急科」
8. Bot: 勤務形態 → 「常勤（夜勤あり）」
9. Bot: マッチング → 関東の急性期病院
10. User: 「広島の病院が一つも出てこないんですが...」

**System Behavior Evaluation:**
- 政令指定都市である広島市がエリア選択肢にないのは深刻
- ER看護師は高スキル人材で引く手あまた
- 「え、広島ないんですか？」というユーザーの驚きに対する説明がない

**Results:**
- Drop-off: VERY HIGH
- Job Proposal: 関東急性期病院（ユーザーは広島希望）
- Next Action: 広島市内の急性期病院を個別に紹介
- Region Bias: 致命的
- National Expansion Risk: VERY HIGH（広島は主要都市）

**Failure Category:** Major City Coverage Gap / Region Mismatch
**Severity:** Critical
**Fix Proposal:** 広島は中国地方最大都市。エリア選択肢への追加 or DB拡充を最優先
**Retry Needed:** Yes
**Auditor Comment:** 政令指定都市をカバーしていないのは事業としての信頼性に関わる。

---

### Case W6-023
- **Prefecture:** 広島県 / **Region Block:** 中国 / **Case Type:** Standard / **User Profile:** 34歳、福山市の回復期リハビリ病院看護師 / **Entry Route:** Google → LINE / **Difficulty:** Easy

**Scenario:**
福山市は広島県東部で人口46万人。岡山との県境に位置する。

**Conversation Flow:**
1. Bot: Welcome → エリア選択
2. User: 「その他の地域」
3. Bot: 施設タイプ → 「病院」
4. Bot: 診療科 → 「リハビリ科」
5. Bot: 勤務形態 → 「日勤のみ」
6. Bot: 緊急度 → 「半年以内」
7. Bot: マッチング → 関東のリハビリ病院

**System Behavior Evaluation:**
- フロー完走するが結果が地域外
- 福山市は中核市で病院数も多い

**Results:**
- Drop-off: HIGH
- Job Proposal: 関東リハビリ病院
- Next Action: 福山・岡山エリアの求人を個別案内
- Region Bias: 関東限定
- National Expansion Risk: MEDIUM

**Failure Category:** Region Mismatch
**Severity:** High
**Fix Proposal:** 「その他の地域」フロー完走後に地域別の個別対応を案内
**Retry Needed:** No
**Auditor Comment:** 福山-岡山の生活圏をカバーすれば中国地方東部を効率的に取れる。

---

### Case W6-024
- **Prefecture:** 広島県 / **Region Block:** 中国 / **Case Type:** Boundary / **User Profile:** 27歳、呉市の海上自衛隊病院退職の看護師 / **Entry Route:** 友人紹介 → LINE / **Difficulty:** Hard

**Scenario:**
自衛隊病院を退職して民間へ。呉市は海軍の街で自衛隊関連施設が多い。特殊な経歴。

**Conversation Flow:**
1. Bot: Welcome
2. User: 「自衛隊病院を辞めて民間の病院に行きたいんですが」
3. Bot: エリア選択表示（特殊経歴に反応できず）
4. User: 「広島県の呉で」
5. Bot: 「その他の地域」を案内
6. User: 「その他の地域」→ 通常フロー
7. Bot: マッチング → 関東病院
8. User: 「呉市内の病院が良いんですが」

**System Behavior Evaluation:**
- 自衛隊病院という特殊経歴に対応不可
- 呉市の地域特性を理解できない
- 自衛隊→民間の転職は経歴の活かし方にコツがある

**Results:**
- Drop-off: HIGH
- Job Proposal: 関東病院（地域・文脈不一致）
- Next Action: 特殊経歴者は担当者が直接カウンセリング
- Region Bias: 関東限定
- National Expansion Risk: MEDIUM

**Failure Category:** Special Background Blindspot / Region Mismatch
**Severity:** High
**Fix Proposal:** 自衛隊・国公立等の特殊経歴キーワード検出→ハンドオフ
**Retry Needed:** No
**Auditor Comment:** 自衛隊病院経験は高い基礎能力の証。民間でも需要大。

---

### Case W6-025
- **Prefecture:** 広島県 / **Region Block:** 中国 / **Case Type:** Standard / **User Profile:** 40歳、東広島市の大学病院看護師 / **Entry Route:** LINE / **Difficulty:** Medium

**Scenario:**
広島大学病院（東広島）から広島市内の病院への転職希望。通勤時間短縮が目的。

**Conversation Flow:**
1. Bot: Welcome → エリア選択
2. User: 「その他の地域」
3. Bot: 施設タイプ → 「病院」
4. Bot: 診療科 → 「外科」
5. Bot: 勤務形態 → 「常勤（夜勤あり）」
6. Bot: 緊急度 → 「3ヶ月以内」
7. Bot: マッチング → 関東病院

**System Behavior Evaluation:**
- 東広島→広島市という「同一都市圏内の近距離転職」に対応不可
- 通勤時間という転職動機を把握する仕組みなし

**Results:**
- Drop-off: HIGH
- Job Proposal: 関東病院
- Next Action: 広島市内の外科病院を個別に案内
- Region Bias: 関東限定
- National Expansion Risk: MEDIUM

**Failure Category:** Region Mismatch
**Severity:** High
**Fix Proposal:** 転職理由のヒアリング項目を追加（通勤/給与/人間関係等）
**Retry Needed:** No
**Auditor Comment:** 通勤時間短縮は最も成約しやすい転職動機。逃すべきでない。

---

### Case W6-026
- **Prefecture:** 広島県 / **Region Block:** 中国 / **Case Type:** Adversarial / **User Profile:** 22歳、広島市のクリニック看護師（経験1年未満） / **Entry Route:** TikTok → LINE / **Difficulty:** Hard

**Scenario:**
入職1年未満での転職検討。「もう辞めたい」という感情的なメッセージ。早期離職への対応が問われる。

**Conversation Flow:**
1. Bot: Welcome
2. User: 「もう無理。先輩怖いし毎日泣いてる。辞めたい」
3. Bot: エリア選択表示（感情に全く対応せず）
4. User: 「...」（沈黙）
5. Bot: 再度エリア選択を促す
6. User: 「その他の地域」（諦めて選択）
7. Bot: 通常フロー進行
8. User: フロー途中で「やっぱりいいです」→ 離脱

**System Behavior Evaluation:**
- メンタルヘルスに関わる深刻な訴えに機械的に対応
- 「もう無理」「泣いてる」「辞めたい」というSOSキーワードを検出できない
- 早期離職者へのケアフロー皆無

**Results:**
- Drop-off: CERTAIN（途中離脱）
- Job Proposal: なし（フロー未完了）
- Next Action: メンタルケア→相談窓口案内→状況落ち着いたら転職相談
- Region Bias: N/A
- National Expansion Risk: HIGH（SNS拡散リスク大）

**Failure Category:** Mental Health / Emotional Crisis Response Gap
**Severity:** Critical
**Fix Proposal:** SOSキーワード検出→共感メッセージ+相談窓口案内+担当者即接続。「まずはお気持ちお聞かせください」
**Retry Needed:** Yes
**Auditor Comment:** 22歳のSOSを無視するBotは炎上リスク。最優先で対応すべき。

---

### Case W6-027
- **Prefecture:** 広島県 / **Region Block:** 中国 / **Case Type:** Standard / **User Profile:** 37歳、尾道市の療養型病院看護師 / **Entry Route:** LINE / **Difficulty:** Easy

**Scenario:**
尾道市は「しまなみ海道」の起点。愛媛県今治市とも繋がる。急性期への復帰希望。

**Conversation Flow:**
1. Bot: Welcome → エリア選択
2. User: 「その他の地域」
3. Bot: 施設タイプ → 「病院」
4. Bot: 診療科 → 「内科」
5. Bot: 勤務形態 → 「常勤（夜勤あり）」
6. Bot: マッチング → 関東病院

**System Behavior Evaluation:**
- 尾道→今治のしまなみ海道通勤圏を考慮できない
- 療養型→急性期という復帰パターンへの助言なし

**Results:**
- Drop-off: HIGH
- Job Proposal: 関東病院
- Next Action: 広島県東部・愛媛県の求人を個別案内
- Region Bias: 関東限定
- National Expansion Risk: LOW

**Failure Category:** Region Mismatch
**Severity:** High
**Fix Proposal:** 瀬戸内海エリアの生活圏マッピングを導入
**Retry Needed:** No
**Auditor Comment:** しまなみ海道は観光だけでなく生活道路。県境を越えた求人提案が有効。

---

### Case W6-028
- **Prefecture:** 広島県 / **Region Block:** 中国 / **Case Type:** Adversarial / **User Profile:** 45歳、広島市の大手病院看護部長 / **Entry Route:** LINE / **Difficulty:** Hard

**Scenario:**
看護部長クラスの超ハイレベル人材がBotに来た。「ちょっと見てみるか」程度の軽い気持ち。

**Conversation Flow:**
1. Bot: Welcome
2. User: 「今の病院から転職も考えてて、ちょっと情報見たいだけなんですが」
3. Bot: エリア選択
4. User: 「その他の地域」
5. Bot: 施設タイプ → 「病院」
6. Bot: 通常フロー → マッチング → 関東のスタッフ向け求人
7. User: 「看護部長の求人ってないんですか？」
8. Bot: 対応不可

**System Behavior Evaluation:**
- 部長職の人材に一般スタッフ求人を表示
- 「情報見たいだけ」というカジュアルな利用者への対応なし
- 超高単価人材を逃す

**Results:**
- Drop-off: CERTAIN
- Job Proposal: 関東スタッフ求人（完全不適切）
- Next Action: 即座にVIP対応→代表直接面談
- Region Bias: 関東限定
- National Expansion Risk: LOW

**Failure Category:** VIP Detection Failure / Role-Level Blindspot
**Severity:** Critical
**Fix Proposal:** 役職キーワード（部長/副部長/師長）検出→VIPフラグ→最優先ハンドオフ
**Retry Needed:** Yes
**Auditor Comment:** 看護部長の年収は800万超。手数料10%=80万。一人で月間目標達成可能な超大型案件。

---

### Case W6-029
- **Prefecture:** 広島県 / **Region Block:** 中国 / **Case Type:** Boundary / **User Profile:** 31歳、三次市の小規模病院看護師 / **Entry Route:** LINE / **Difficulty:** Medium

**Scenario:**
三次市は広島県北部の中山間地。広島市まで車で1.5時間。過疎地域からの脱出希望。

**Conversation Flow:**
1. Bot: Welcome → エリア選択
2. User: 「広島市内に引っ越して転職したい」
3. Bot: エリア選択肢表示
4. User: 「その他の地域」
5. Bot: 施設タイプ → 「病院」
6. Bot: 診療科 → 「内科」
7. Bot: 勤務形態 → 「常勤（夜勤あり）」
8. Bot: マッチング → 関東病院
9. User: 「広島市の病院を探してるんですが...」

**System Behavior Evaluation:**
- 「広島市内に引っ越して」という明確な希望を無視
- 中山間地→都市部の転居転職パターンに対応不可

**Results:**
- Drop-off: HIGH
- Job Proposal: 関東病院（広島市ではない）
- Next Action: 広島市内の病院を個別案内
- Region Bias: 関東限定
- National Expansion Risk: MEDIUM

**Failure Category:** Region Mismatch / Relocation Context Missing
**Severity:** High
**Fix Proposal:** 転居先の具体的な地名が入力された場合、対応可否を即座に返答
**Retry Needed:** No
**Auditor Comment:** 「広島市内に引っ越して」は明確な意思。これを拾えないBotは改善必須。

---

## Main Cases: 山口県 (7 cases)

---

### Case W6-030
- **Prefecture:** 山口県 / **Region Block:** 中国 / **Case Type:** Standard / **User Profile:** 30歳、下関市の総合病院看護師 / **Entry Route:** LINE友だち追加 / **Difficulty:** Medium

**Scenario:**
下関市は関門海峡を挟んで北九州市と隣接。福岡県への越境通勤が一般的。山口なのか福岡なのか、生活圏が曖昧。

**Conversation Flow:**
1. Bot: Welcome → エリア選択
2. User: 「下関か北九州で探してます」
3. Bot: 選択肢にどちらもなし
4. User: 「その他の地域」
5. Bot: 施設タイプ → 「病院」
6. Bot: 診療科 → 「内科」
7. Bot: 勤務形態 → 「常勤（夜勤あり）」
8. Bot: マッチング → 関東病院
9. User: 「北九州の病院は？」

**System Behavior Evaluation:**
- 関門海峡圏（下関-北九州）は日本有数の県境一体生活圏
- 両市合わせて人口130万人超の大都市圏を完全に無視
- 「下関か北九州」のフリーテキストを処理できない

**Results:**
- Drop-off: VERY HIGH
- Job Proposal: 関東病院（完全不一致）
- Next Action: 関門エリアの求人を個別案内
- Region Bias: 致命的
- National Expansion Risk: VERY HIGH

**Failure Category:** Cross-Prefecture Major Metro Blindspot / Region Mismatch
**Severity:** Critical
**Fix Proposal:** 関門エリア（下関+北九州）を一つの生活圏として認識。DB拡充優先
**Retry Needed:** Yes
**Auditor Comment:** 下関-北九州は通勤20分。県境を理由に分断するのは非現実的。

---

### Case W6-031
- **Prefecture:** 山口県 / **Region Block:** 中国 / **Case Type:** Standard / **User Profile:** 35歳、山口市の県立総合医療センター看護師 / **Entry Route:** Google → LINE / **Difficulty:** Easy

**Scenario:**
山口市は県庁所在地だが人口19万人。市内での転職先は限られる。

**Conversation Flow:**
1. Bot: Welcome → エリア選択
2. User: 「その他の地域」
3. Bot: 施設タイプ → 「病院」
4. Bot: 診療科 → 「外科」
5. Bot: 勤務形態 → 「日勤のみ」
6. Bot: 緊急度 → 「3ヶ月以内」
7. Bot: マッチング → 関東病院

**System Behavior Evaluation:**
- 山口市内の転職先が限られることへの配慮なし
- 広島や福岡への転居提案もなし

**Results:**
- Drop-off: HIGH
- Job Proposal: 関東病院
- Next Action: 山口市内+広島・福岡への広域提案
- Region Bias: 関東限定
- National Expansion Risk: MEDIUM

**Failure Category:** Region Mismatch
**Severity:** High
**Fix Proposal:** 人口少都市の場合、隣接大都市圏も提案する機能
**Retry Needed:** No
**Auditor Comment:** 山口市は広島・福岡の中間。どちらへも新幹線30分。広域提案が有効。

---

### Case W6-032
- **Prefecture:** 山口県 / **Region Block:** 中国 / **Case Type:** Boundary / **User Profile:** 26歳、岩国市の総合病院看護師 / **Entry Route:** Instagram → LINE / **Difficulty:** Medium

**Scenario:**
岩国市は広島県との県境で、広島市への通勤者も多い。米軍岩国基地もある特殊な地域。

**Conversation Flow:**
1. Bot: Welcome → エリア選択
2. User: 「岩国から広島に通える病院探してます」
3. Bot: 選択肢表示（広島も山口もなし）
4. User: 「その他の地域」
5. Bot: 通常フロー → マッチング → 関東病院
6. User: 「広島の病院が見たいんですけど...」

**System Behavior Evaluation:**
- 岩国→広島の通勤転職は一般的なのに対応不可
- 「通える」というキーワードから通勤圏を推定できない

**Results:**
- Drop-off: HIGH
- Job Proposal: 関東病院
- Next Action: 広島西部の通勤可能な病院を個別案内
- Region Bias: 関東限定
- National Expansion Risk: MEDIUM

**Failure Category:** Commute Range Blindspot / Region Mismatch
**Severity:** High
**Fix Proposal:** 通勤圏キーワード（「通える」「通勤」等）検出→居住地と希望地の距離を考慮
**Retry Needed:** No
**Auditor Comment:** 岩国-広島は在来線で1時間半。十分な通勤圏。

---

### Case W6-033
- **Prefecture:** 山口県 / **Region Block:** 中国 / **Case Type:** Adversarial / **User Profile:** 48歳、周南市の病院看護師（パワハラ被害） / **Entry Route:** LINE / **Difficulty:** Hard

**Scenario:**
パワハラで精神的に追い詰められている。「早く辞めたい」が先行し、冷静な判断ができない状態。

**Conversation Flow:**
1. Bot: Welcome
2. User: 「パワハラがひどくて限界です。すぐ辞めたいです」
3. Bot: エリア選択表示（緊急性を認識できず）
4. User: 「山口県で」→ 選択肢なし
5. Bot: 「その他の地域」を案内
6. User: 「もうどこでもいいです」
7. Bot: 通常フロー → マッチング → 関東病院
8. User: 「やっぱり山口がいいんですけど...でももう疲れた」

**System Behavior Evaluation:**
- パワハラという深刻な労働問題への対応なし
- 「限界」「すぐ辞めたい」という緊急性を無視
- 「どこでもいい」は本心ではなく追い詰められた結果

**Results:**
- Drop-off: HIGH
- Job Proposal: 関東病院（「どこでもいい」に応じたが本意でない）
- Next Action: 労働問題→専門家（労基署等）案内 + 担当者による緊急対応
- Region Bias: 関東限定
- National Expansion Risk: HIGH

**Failure Category:** Crisis Response Gap / Region Mismatch
**Severity:** Critical
**Fix Proposal:** ハラスメントキーワード検出→共感+労働相談窓口案内+担当者即接続
**Retry Needed:** Yes
**Auditor Comment:** パワハラ被害者への不適切対応は訴訟リスクもある。最優先で改善すべき。

---

### Case W6-034
- **Prefecture:** 山口県 / **Region Block:** 中国 / **Case Type:** Standard / **User Profile:** 33歳、宇部市の精神科病院看護師 / **Entry Route:** LINE / **Difficulty:** Easy

**Scenario:**
精神科から一般内科への転科希望。宇部市は山口大学医学部がある医療都市。

**Conversation Flow:**
1. Bot: Welcome → エリア選択
2. User: 「その他の地域」
3. Bot: 施設タイプ → 「病院」
4. Bot: 診療科 → 「内科」
5. Bot: 勤務形態 → 「日勤のみ」
6. Bot: マッチング → 関東病院

**System Behavior Evaluation:**
- 精神科→内科の転科を把握する仕組みなし
- 宇部市の医療環境（山口大学医学部）を活かせない

**Results:**
- Drop-off: HIGH
- Job Proposal: 関東内科病院
- Next Action: 山口県内の内科求人を個別案内
- Region Bias: 関東限定
- National Expansion Risk: LOW

**Failure Category:** Region Mismatch
**Severity:** High
**Fix Proposal:** 現在の診療科と希望診療科の両方をヒアリング
**Retry Needed:** No
**Auditor Comment:** 転科は担当者のアドバイスが成約率を大きく左右する。

---

### Case W6-035
- **Prefecture:** 山口県 / **Region Block:** 中国 / **Case Type:** Boundary / **User Profile:** 28歳、萩市の地域医療支援病院看護師 / **Entry Route:** LINE / **Difficulty:** Medium

**Scenario:**
萩市は山口県北部の観光都市（人口4.5万人）。地域医療に携わってきたが、スキルアップのため都市部を志望。

**Conversation Flow:**
1. Bot: Welcome → エリア選択
2. User: 「萩から出たいんですが、広島か福岡で考えてます」
3. Bot: 選択肢にどちらもなし
4. User: 「その他の地域」
5. Bot: 通常フロー → マッチング → 関東
6. User: 「広島か福岡って言ったんですが...」

**System Behavior Evaluation:**
- 明確に「広島か福岡」と言っているのに無視
- 地方→都市部のキャリアアップ転職パターンへの理解なし

**Results:**
- Drop-off: VERY HIGH
- Job Proposal: 関東病院
- Next Action: 広島・福岡の求人を個別案内
- Region Bias: 致命的
- National Expansion Risk: HIGH

**Failure Category:** User Intent Ignored / Region Mismatch
**Severity:** Critical
**Fix Proposal:** フリーテキストで地名が複数指定された場合、それを条件として保持
**Retry Needed:** Yes
**Auditor Comment:** ユーザーが明示した希望地を無視するのは最もタチが悪いUXバグ。

---

### Case W6-036
- **Prefecture:** 山口県 / **Region Block:** 中国 / **Case Type:** Adversarial / **User Profile:** 55歳、光市の病院看護師（定年を見据えた転職） / **Entry Route:** LINE / **Difficulty:** Hard

**Scenario:**
定年（60歳）を見据えて最後の職場を探している。年齢に関する不安が大きい。

**Conversation Flow:**
1. Bot: Welcome
2. User: 「55歳なんですが、まだ転職できますかね？」
3. Bot: エリア選択表示（年齢の質問に答えず）
4. User: 「質問に答えてくれないんですね...」
5. Bot: 再度エリア選択
6. User: 「その他の地域」（渋々）
7. Bot: 通常フロー → マッチング → 関東病院
8. User: 「55歳でも大丈夫なところありますか？」
9. Bot: 対応不可

**System Behavior Evaluation:**
- 年齢に関する不安への回答機能なし
- 55歳の転職に対する助言やサポート情報なし
- 質問を無視してフロー強制する姿勢

**Results:**
- Drop-off: HIGH
- Job Proposal: 関東病院（年齢条件不明）
- Next Action: 年齢不問の求人を個別に探す+担当者カウンセリング
- Region Bias: 関東限定
- National Expansion Risk: MEDIUM

**Failure Category:** Age-Related Counseling Gap / Flow Rigidity / Region Mismatch
**Severity:** High
**Fix Proposal:** 年齢キーワード検出→「経験豊富な方の転職もサポートしています」+担当者接続
**Retry Needed:** Yes
**Auditor Comment:** 高齢看護師は夜勤なし・日勤のみ求人で需要あり。年齢を理由に離脱させるのは損失。

---

## Main Cases: Spare (4 cases)

---

### Case W6-037
- **Prefecture:** 広島県 / **Region Block:** 中国 / **Case Type:** Standard / **User Profile:** 32歳、広島市のがん専門病院看護師 / **Entry Route:** LINE / **Difficulty:** Medium

**Scenario:**
がん看護専門看護師（CNS）の資格を持つスペシャリスト。専門性を活かせる施設を探している。

**Conversation Flow:**
1. Bot: Welcome → エリア選択
2. User: 「がん看護の専門看護師なんですが、専門性を活かせる病院を探してます」
3. Bot: エリア選択表示（専門資格に反応できず）
4. User: 「その他の地域」
5. Bot: 施設タイプ → 「病院」
6. Bot: 診療科 → 「腫瘍科」（なければ「内科」）
7. Bot: マッチング → 関東病院（専門看護師の条件なし）

**System Behavior Evaluation:**
- CNS（専門看護師）、CN（認定看護師）等の専門資格を把握する仕組みなし
- 専門性の高い人材ほど汎用的なマッチングでは満足しない

**Results:**
- Drop-off: HIGH
- Job Proposal: 関東の一般病院（専門性無視）
- Next Action: がん拠点病院の求人を個別に紹介
- Region Bias: 関東限定
- National Expansion Risk: MEDIUM

**Failure Category:** Specialty Credential Blindspot / Region Mismatch
**Severity:** High
**Fix Proposal:** 専門資格（CNS/CN/特定行為等）のヒアリング項目追加
**Retry Needed:** No
**Auditor Comment:** CNSは全国で2,000人程度の希少人材。確実に成約すべき。

---

### Case W6-038
- **Prefecture:** 岡山県 / **Region Block:** 中国 / **Case Type:** Adversarial / **User Profile:** 26歳、岡山市のクリニック看護師（外国籍・EPA看護師） / **Entry Route:** LINE / **Difficulty:** Hard

**Scenario:**
フィリピン出身のEPA看護師。日本語でのBot操作に困難あり。在留資格に関する質問もある。

**Conversation Flow:**
1. Bot: Welcome（日本語のみ）
2. User: 「I want to find hospital in Okayama. Can I use this in English?」
3. Bot: エリア選択表示（英語に対応できず）
4. User: 「岡山で病院探したい」（日本語に切り替え）
5. Bot: 「その他の地域」
6. Bot: 通常フロー → マッチング → 関東
7. User: 「visa support ありますか？」
8. Bot: 対応不可

**System Behavior Evaluation:**
- 多言語対応なし
- EPA看護師という在留資格の特殊性に対応不可
- ビザサポートの質問に回答できない

**Results:**
- Drop-off: VERY HIGH
- Job Proposal: 関東病院（ビザ条件不明）
- Next Action: EPA看護師専門の担当者に接続
- Region Bias: 関東限定
- National Expansion Risk: HIGH

**Failure Category:** Language Barrier / Visa Blindspot / Region Mismatch
**Severity:** Critical
**Fix Proposal:** 英語入力検出→多言語対応案内 or バイリンガル担当者接続
**Retry Needed:** Yes
**Auditor Comment:** EPA看護師は増加傾向。多言語対応は今後の差別化要因。

---

### Case W6-039
- **Prefecture:** 島根県 / **Region Block:** 中国 / **Case Type:** Boundary / **User Profile:** 29歳、安来市の病院看護師 / **Entry Route:** LINE / **Difficulty:** Medium

**Scenario:**
安来市は鳥取県米子市と隣接。鳥取大学医学部附属病院（米子市）への転職も視野。

**Conversation Flow:**
1. Bot: Welcome → エリア選択
2. User: 「安来か米子の病院探してます」
3. Bot: 選択肢になし → 「その他の地域」
4. User: 「その他の地域」
5. Bot: 通常フロー → マッチング → 関東
6. User: 「米子の大学病院とかないんですか？」

**System Behavior Evaluation:**
- 安来-米子の生活圏を認識できない
- 大学病院という具体的な施設カテゴリの希望に対応不可

**Results:**
- Drop-off: HIGH
- Job Proposal: 関東病院
- Next Action: 鳥取大学病院等の求人を個別案内
- Region Bias: 関東限定
- National Expansion Risk: MEDIUM

**Failure Category:** Cross-Prefecture Living Area / Region Mismatch
**Severity:** High
**Fix Proposal:** 「大学病院」キーワードで施設カテゴリフィルターを追加
**Retry Needed:** No
**Auditor Comment:** 山陰の県境（安来-米子）は完全に一体の生活圏。

---

### Case W6-040
- **Prefecture:** 山口県 / **Region Block:** 中国 / **Case Type:** Standard / **User Profile:** 39歳、防府市の病院看護師 / **Entry Route:** LINE / **Difficulty:** Easy

**Scenario:**
防府市は山口市の隣。病院の統合で人員整理されそうなため転職を検討。

**Conversation Flow:**
1. Bot: Welcome → エリア選択
2. User: 「その他の地域」
3. Bot: 施設タイプ → 「病院」
4. Bot: 診療科 → 「内科」
5. Bot: 勤務形態 → 「常勤（夜勤あり）」
6. Bot: 緊急度 → 「1ヶ月以内」
7. Bot: マッチング → 関東病院

**System Behavior Evaluation:**
- 病院統合による人員整理という切迫した事情に対応不可
- 緊急度高だが地域外結果のみ

**Results:**
- Drop-off: HIGH
- Job Proposal: 関東病院
- Next Action: 山口県内の急募案件を担当者が緊急対応
- Region Bias: 関東限定
- National Expansion Risk: MEDIUM

**Failure Category:** Region Mismatch / Urgency Mishandling
**Severity:** High
**Fix Proposal:** 緊急度「1ヶ月以内」×エリア外 → 担当者ホットライン即接続
**Retry Needed:** No
**Auditor Comment:** 病院統合で失職する看護師は複数名。一度に複数成約の可能性。

---

## Cross Cases: 東京都 (2 cases)

---

### Case W6-041
- **Prefecture:** 東京都 / **Region Block:** 関東（Cross from 中国） / **Case Type:** Standard / **User Profile:** 28歳、広島市出身で東京の大学病院勤務（3年目） / **Entry Route:** LINE / **Difficulty:** Easy

**Scenario:**
広島出身で東京の大学病院に勤務中。東京での転職を検討。対応エリア内なので正常動作するはず。

**Conversation Flow:**
1. Bot: Welcome → エリア選択
2. User: 「東京都」をタップ
3. Bot: 施設タイプ → 「病院」
4. Bot: 診療科 → 「循環器内科」
5. Bot: 勤務形態 → 「常勤（夜勤あり）」
6. Bot: 緊急度 → 「3ヶ月以内」
7. Bot: マッチング → 東京の循環器病院表示

**System Behavior Evaluation:**
- 東京在住なのでフロー正常動作
- 広島出身の文脈は拾えないが、東京の求人表示は適切

**Results:**
- Drop-off: LOW
- Job Proposal: 東京の循環器病院（適切）
- Next Action: 気になる求人に応募→担当者フォロー
- Region Bias: なし
- National Expansion Risk: LOW

**Failure Category:** None（正常動作）
**Severity:** Low
**Fix Proposal:** 出身地情報の取得で「将来Uターンしたくなったら」の案内も可能に
**Retry Needed:** No
**Auditor Comment:** 対応エリア内では問題なし。Uターン転職の伏線を張る余地あり。

---

### Case W6-042
- **Prefecture:** 東京都 / **Region Block:** 関東（Cross from 中国） / **Case Type:** Boundary / **User Profile:** 35歳、岡山から東京へ転居予定の看護師 / **Entry Route:** LINE / **Difficulty:** Medium

**Scenario:**
夫の転勤で岡山→東京へ転居予定。東京の求人を探しつつ、岡山での退職もまだ。

**Conversation Flow:**
1. Bot: Welcome → エリア選択
2. User: 「来月東京に引っ越すので東京の求人探してます」
3. Bot: 「東京都」をタップ可能
4. User: 「東京都」
5. Bot: 施設タイプ → 「クリニック」
6. Bot: 診療科 → 「小児科」
7. Bot: 勤務形態 → 「パート」（選択肢にない場合「日勤のみ」）
8. Bot: マッチング → 東京の小児科クリニック

**System Behavior Evaluation:**
- 東京選択で正常動作
- 「来月引っ越す」という時間軸を考慮した提案はできない
- パート希望への対応が不十分な可能性

**Results:**
- Drop-off: LOW
- Job Proposal: 東京小児科クリニック（方向性は合致）
- Next Action: 転居時期に合わせた入職日調整を担当者がフォロー
- Region Bias: なし
- National Expansion Risk: LOW

**Failure Category:** Minor（転居タイミング考慮なし）
**Severity:** Low
**Fix Proposal:** 「いつから働けますか？」の質問を追加
**Retry Needed:** No
**Auditor Comment:** 転居転職は確実に成約する案件。タイミング調整さえすれば問題なし。

---

## Cross Cases: 大阪 (2 cases)

---

### Case W6-043
- **Prefecture:** 大阪府 / **Region Block:** 関西（Cross from 中国） / **Case Type:** Standard / **User Profile:** 30歳、広島から大阪への転居転職希望 / **Entry Route:** LINE / **Difficulty:** Medium

**Scenario:**
広島の看護師が大阪の大病院への転職を希望。Botは大阪に対応していない。

**Conversation Flow:**
1. Bot: Welcome → エリア選択
2. User: 「大阪で探してます」
3. Bot: 選択肢に大阪なし
4. User: 「大阪ないんですか...」
5. Bot: 「その他の地域」を案内
6. User: 「その他の地域」
7. Bot: 通常フロー → マッチング → 関東病院
8. User: 「東京の求人出されても困るんですが。大阪が希望です」

**System Behavior Evaluation:**
- 大阪は日本第2の都市圏。対応していないのは大きな穴
- 関東の結果を出されてユーザーの不信感MAX

**Results:**
- Drop-off: VERY HIGH
- Job Proposal: 関東病院（完全不一致）
- Next Action: 大阪の求人は個別対応で案内
- Region Bias: 関東限定
- National Expansion Risk: VERY HIGH

**Failure Category:** Major City Coverage Gap / Region Mismatch
**Severity:** Critical
**Fix Proposal:** 大阪は優先的にDB追加すべき都市圏
**Retry Needed:** Yes
**Auditor Comment:** 日本第二の都市を未対応は事業としてありえない。

---

### Case W6-044
- **Prefecture:** 大阪府 / **Region Block:** 関西（Cross from 中国） / **Case Type:** Adversarial / **User Profile:** 27歳、岡山出身で大阪在住の看護師 / **Entry Route:** TikTok → LINE / **Difficulty:** Hard

**Scenario:**
「関西の看護師転職サイトかと思って登録したのに関東しかないの？」というクレーム型ユーザー。

**Conversation Flow:**
1. Bot: Welcome
2. User: 「大阪の求人見たいんですけど」
3. Bot: エリア選択表示
4. User: 「大阪ないじゃないですか。なんで？」
5. Bot: 同じ選択肢を再表示
6. User: 「ちゃんと答えてください」
7. Bot: 定型応答 or 無応答
8. User: 「使えない。ブロックします」→ 離脱

**System Behavior Evaluation:**
- クレームに対する応対機能なし
- 「なんで？」という質問に理由を説明できない
- ユーザーの怒りをエスカレートさせてしまう

**Results:**
- Drop-off: CERTAIN（ブロック）
- Job Proposal: なし
- Next Action: クレーム対応→人間オペレーター即接続
- Region Bias: 致命的
- National Expansion Risk: VERY HIGH（SNS炎上リスク）

**Failure Category:** Complaint Handling Failure / Coverage Gap
**Severity:** Critical
**Fix Proposal:** クレームキーワード検出→謝罪+理由説明+人間オペレーター接続。「現在は関東エリアを中心にサービス提供中です。ご不便をおかけし申し訳ございません」
**Retry Needed:** Yes
**Auditor Comment:** ブロック=永久的な顧客喪失。初回で適切に対応すれば防げた。

---

## Cross Cases: 愛知 (2 cases)

---

### Case W6-045
- **Prefecture:** 愛知県 / **Region Block:** 中部（Cross from 中国） / **Case Type:** Standard / **User Profile:** 31歳、山口出身で名古屋勤務の看護師 / **Entry Route:** LINE / **Difficulty:** Medium

**Scenario:**
名古屋市内での転職希望だが、Botは愛知県に対応していない。

**Conversation Flow:**
1. Bot: Welcome → エリア選択
2. User: 「名古屋で探してます」
3. Bot: 選択肢に愛知なし → 「その他の地域」
4. User: 「その他の地域」
5. Bot: 通常フロー → マッチング → 関東病院
6. User: 「名古屋の病院ないんですか...」

**System Behavior Evaluation:**
- 名古屋は日本第3の都市圏。未対応は致命的
- 関東の結果に失望

**Results:**
- Drop-off: VERY HIGH
- Job Proposal: 関東病院（不一致）
- Next Action: 名古屋の求人を個別案内
- Region Bias: 関東限定
- National Expansion Risk: VERY HIGH

**Failure Category:** Major City Coverage Gap
**Severity:** Critical
**Fix Proposal:** 名古屋圏のDB構築を検討
**Retry Needed:** Yes
**Auditor Comment:** 東京・大阪・名古屋の三大都市圏が揃わないのは致命的。

---

### Case W6-046
- **Prefecture:** 愛知県 / **Region Block:** 中部（Cross from 中国） / **Case Type:** Boundary / **User Profile:** 29歳、広島→名古屋→東京と検討中の看護師 / **Entry Route:** LINE / **Difficulty:** Hard

**Scenario:**
転居先を迷っている。複数都市で比較検討したい。

**Conversation Flow:**
1. Bot: Welcome
2. User: 「東京か名古屋か迷ってるんですけど、両方の求人見れますか？」
3. Bot: エリア選択（1つしか選べない）
4. User: 「東京都」（まず1つ選択）
5. Bot: フロー完走 → 東京の結果
6. User: 「名古屋の分もお願いします」→ フロー再実行できるか不明

**System Behavior Evaluation:**
- 複数エリアの比較検討に対応不可
- フローの再実行方法が不明確
- 「迷っている」ユーザーへのカウンセリング機能なし

**Results:**
- Drop-off: MEDIUM（東京は見れるが名古屋で詰まる）
- Job Proposal: 東京病院のみ（片方のみ）
- Next Action: 複数エリア比較は担当者が対応
- Region Bias: 関東のみ対応可
- National Expansion Risk: HIGH

**Failure Category:** Multi-Area Comparison Gap / Flow Limitation
**Severity:** High
**Fix Proposal:** フロー完走後に「他のエリアも見る」ボタンを追加
**Retry Needed:** No
**Auditor Comment:** 比較検討ユーザーは本気度が高い。手厚い対応で成約に繋がる。

---

## Cross Cases: 福岡 (2 cases)

---

### Case W6-047
- **Prefecture:** 福岡県 / **Region Block:** 九州（Cross from 中国） / **Case Type:** Standard / **User Profile:** 30歳、下関市から北九州市への越境転職希望 / **Entry Route:** LINE / **Difficulty:** Medium

**Scenario:**
下関（山口県）在住で北九州（福岡県）の病院へ転職希望。関門海峡エリアの典型的な越境転職。

**Conversation Flow:**
1. Bot: Welcome → エリア選択
2. User: 「北九州市の病院探してます。下関に住んでます」
3. Bot: 選択肢に福岡なし
4. User: 「その他の地域」
5. Bot: 通常フロー → マッチング → 関東病院
6. User: 「北九州のはないですか？関門トンネルで20分なんですけど...」

**System Behavior Evaluation:**
- 関門海峡エリアの越境通勤を理解できない
- 北九州市（人口93万人）の求人がゼロ

**Results:**
- Drop-off: VERY HIGH
- Job Proposal: 関東病院（完全不一致）
- Next Action: 北九州の求人を個別案内
- Region Bias: 致命的
- National Expansion Risk: HIGH

**Failure Category:** Cross-Prefecture Commute / Major City Coverage Gap
**Severity:** Critical
**Fix Proposal:** 北九州市は政令指定都市。DB拡充すべき
**Retry Needed:** Yes
**Auditor Comment:** 関門海峡通勤は毎日1万人以上。完全な日常。

---

### Case W6-048
- **Prefecture:** 福岡県 / **Region Block:** 九州（Cross from 中国） / **Case Type:** Adversarial / **User Profile:** 25歳、山口出身で福岡市勤務・博多の繁華街が好き / **Entry Route:** TikTok → LINE / **Difficulty:** Medium

**Scenario:**
カジュアルなノリで「福岡最高！転職するなら福岡っしょ」とBot利用。若者のライトな利用。

**Conversation Flow:**
1. Bot: Welcome
2. User: 「福岡で看護師の求人ある？めっちゃ探してるんだけど！」
3. Bot: エリア選択表示
4. User: 「福岡ないやん笑 マジ？」
5. Bot: 「その他の地域」を案内
6. User: 「その他の地域でやってみるか」
7. Bot: 通常フロー → 関東結果
8. User: 「東京か〜...まあいいけど福岡がよかった笑」

**System Behavior Evaluation:**
- カジュアルな入力に対する柔軟な応答がない
- 福岡未対応で軽い失望
- ただしライトユーザーなので深刻なクレームにはならない

**Results:**
- Drop-off: MEDIUM
- Job Proposal: 関東病院（第2希望としてはあり得る）
- Next Action: 福岡の求人を後日LINEで案内
- Region Bias: 関東限定
- National Expansion Risk: MEDIUM

**Failure Category:** Coverage Gap（軽度）
**Severity:** Medium
**Fix Proposal:** カジュアルトーンへの対応+「福岡の求人は担当者が探します！」の案内
**Retry Needed:** No
**Auditor Comment:** TikTok世代のカジュアルユーザーは将来の顧客。ブランド印象が重要。

---

## Cross Cases: 沖縄 (2 cases)

---

### Case W6-049
- **Prefecture:** 沖縄県 / **Region Block:** 沖縄（Cross from 中国） / **Case Type:** Standard / **User Profile:** 27歳、広島出身で沖縄移住検討中の看護師 / **Entry Route:** LINE / **Difficulty:** Medium

**Scenario:**
「沖縄で看護師やりたい！」という移住転職希望。Botは沖縄に対応していない。

**Conversation Flow:**
1. Bot: Welcome → エリア選択
2. User: 「沖縄で看護師の仕事探してます！」
3. Bot: 選択肢に沖縄なし
4. User: 「その他の地域」
5. Bot: 通常フロー → マッチング → 関東病院
6. User: 「沖縄の求人はないんですか？」

**System Behavior Evaluation:**
- 沖縄移住希望者は一定数いるが対応不可
- 関東の結果はユーザーの期待と完全に乖離

**Results:**
- Drop-off: VERY HIGH
- Job Proposal: 関東病院（完全不一致）
- Next Action: 沖縄の求人は個別対応で案内
- Region Bias: 関東限定
- National Expansion Risk: HIGH

**Failure Category:** Region Mismatch / Coverage Gap
**Severity:** High
**Fix Proposal:** 移住転職は「その他の地域」選択時に「移住先の地域名を教えてください」と個別対応へ
**Retry Needed:** Yes
**Auditor Comment:** 沖縄移住看護師は需要が高い。離島・僻地手当も含め高条件が多い。

---

### Case W6-050
- **Prefecture:** 沖縄県 / **Region Block:** 沖縄（Cross from 中国） / **Case Type:** Adversarial / **User Profile:** 33歳、島根出身で沖縄在住の看護師（Uターン検討中） / **Entry Route:** LINE / **Difficulty:** Hard

**Scenario:**
沖縄在住だが島根へのUターンと沖縄残留で迷っている。Botはどちらにも対応していない。

**Conversation Flow:**
1. Bot: Welcome
2. User: 「沖縄にいるんですけど、島根に帰るか迷ってて。どっちの求人も見たいです」
3. Bot: エリア選択表示（沖縄も島根もなし）
4. User: 「どっちもないですね...」
5. Bot: 「その他の地域」を案内
6. User: 「その他の地域」→ 関東結果
7. User: 「沖縄も島根もないのに関東出されても...」→ 離脱

**System Behavior Evaluation:**
- 二拠点の比較検討に完全に対応不可
- 沖縄・島根のどちらもDB=0件
- Uターン転職という重要なパターンへの理解なし

**Results:**
- Drop-off: CERTAIN
- Job Proposal: 関東病院（完全不一致×2）
- Next Action: Uターン相談として担当者が個別対応
- Region Bias: 致命的
- National Expansion Risk: VERY HIGH

**Failure Category:** Dual Region Request / Total Coverage Failure
**Severity:** Critical
**Fix Proposal:** 「その他の地域」選択時に希望地を自由入力させ、担当者に引き継ぐ
**Retry Needed:** Yes
**Auditor Comment:** Uターン転職は地方自治体も支援しており、連携のチャンス。ここで切り捨てるのは大損失。

---

## Summary Statistics

| Category | Count |
|----------|-------|
| **Total Cases** | 50 |
| Standard | 30 |
| Boundary | 12 |
| Adversarial | 8 |

| Severity | Count |
|----------|-------|
| Critical | 22 |
| High | 21 |
| Medium | 5 |
| Low | 2 |

| Failure Category | Frequency |
|-------------------|-----------|
| Region Mismatch / Silent Redirect | 42/50 |
| Major City Coverage Gap | 8/50 |
| Cross-Prefecture Blindspot | 7/50 |
| Emotional/Crisis Response Gap | 4/50 |
| Flow Rigidity | 5/50 |
| Specialty/Role Blindspot | 6/50 |
| User Segment Mismatch | 3/50 |

## Key Findings for 中国 Region

1. **広島市（政令指定都市119万人）が対応エリアに含まれていない** — 中国地方最大の人口を持つ都市圏を完全に無視。事業としての信頼性に直結する問題。

2. **関門海峡圏（下関-北九州）の越境通勤が考慮されていない** — 毎日1万人以上が越境する主要生活圏をDB未収録。山口県西部と福岡県北部は一体で扱うべき。

3. **岡山は「医療のメッカ」** — 岡山大学病院、倉敷中央病院等の全国レベルの医療機関が集積。ここの看護師を取りこぼすのは大きな事業損失。

4. **鳥取・島根は人口最少県** — 地元志向が極めて強く、関東提示は完全なミスマッチ。少数でも個別対応で成約すれば地域での口コミ効果大。

5. **「その他の地域」→関東結果の暗黙リダイレクトが最大の問題** — 中国地方の全50ケース中42件で発生。ユーザーは自分の地域の結果が出ると期待しており、説明なく関東結果を出すのは信頼破壊。

## Priority Fix Recommendations

1. **即時対応**: 「その他の地域」選択時に「現在は関東エリアの求人のみ表示されます。お住まいの地域の求人は担当者が個別にお探しします」と明示
2. **短期対応**: SOSキーワード（パワハラ/辞めたい/限界/泣いてる）検出→即ハンドオフ
3. **中期対応**: 広島・岡山のDB構築（中国地方の医療中心地）
4. **中期対応**: 役職・専門資格のヒアリング項目追加（VIP検出）
5. **長期対応**: 全国主要都市圏のDB構築（大阪・名古屋・福岡・広島）
