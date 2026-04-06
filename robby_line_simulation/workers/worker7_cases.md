# Worker 7: 四国（徳島・香川・愛媛・高知）+ クロスリージョン

> 50 cases total: Main 40 (徳島9, 香川9, 愛媛9, 高知9, spare4) + Cross 10 (東京2, 大阪2, 広島2, 福岡2, 神奈川2)
> Mix: 30 standard, 12 boundary, 8 adversarial
> Key insight: 四国は対応エリア外。施設DB=0件。「その他の地域」選択→関東施設が表示される。

---

## 徳島県（9件）

### Case W7-001
- **Prefecture:** 徳島県 / **Region Block:** 四国 / **Case Type:** Standard / **User Profile:** 32歳、徳島赤十字病院勤務、急性期3年 / **Entry Route:** LP検索流入 / **Difficulty:** Normal
**Scenario:** 徳島市在住の看護師が地元の転職先を探してLINE登録。急性期経験を活かした転職希望。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択（東京都/神奈川県/千葉県/埼玉県/その他の地域）
3. User: 「その他の地域」を選択
4. Bot: 施設タイプ選択へ進む
5. User: 「病院」を選択
6. Bot: 診療科選択
7. User: 「救急」を選択
8. Bot: 勤務形態選択
9. User: 「常勤（日勤のみ）」
10. Bot: マッチング結果→関東の施設を提示
**System Behavior Evaluation:** ユーザーは徳島の求人を期待しているが、関東の施設が提示される。「その他の地域」選択時に対応エリア外である旨の事前説明がないため、マッチング結果で初めて期待とのギャップが発生する。
**Results:** Drop-off: 高（90%） / Job Proposal: 関東施設のみ / Next Action: 人間引き継ぎ推奨 / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK / **Severity:** Critical / **Fix Proposal:** 「その他の地域」選択時に「現在は関東エリアの求人のみご紹介可能です。それでもよろしいですか？」の確認ステップを追加 / **Retry Needed:** Yes / **Auditor Comment:** 四国の看護師が最も遭遇する典型パターン。事前説明なしは致命的UX欠陥。

---

### Case W7-002
- **Prefecture:** 徳島県 / **Region Block:** 四国 / **Case Type:** Standard / **User Profile:** 45歳、准看護師、診療所勤務20年 / **Entry Route:** Instagram広告 / **Difficulty:** Normal
**Scenario:** 阿南市の准看護師がSNS広告から流入。年齢を考慮した安定職場を希望。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「その他の地域」を選択
4. Bot: 施設タイプ選択
5. User: 「クリニック」を選択
6. Bot: 診療科選択
7. User: 「内科」
8. Bot: 勤務形態
9. User: 「パート」
10. Bot: マッチング結果→関東のクリニックを提示
**System Behavior Evaluation:** 准看護師の場合、地方では就業先が限られる一方、関東への転居は非現実的。ユーザーのライフステージ（45歳・地方在住）と提案内容の乖離が大きい。
**Results:** Drop-off: 極高 / Job Proposal: 関東クリニック / Next Action: 地元求人リソース案内 / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK / **Severity:** High / **Fix Proposal:** 対応エリア外ユーザーにはハローワーク求人情報やナースセンターへのリンク提供を検討 / **Retry Needed:** No / **Auditor Comment:** 高齢准看護師の地方求人ニーズは完全に対応不可。代替リソース案内がないのは不親切。

---

### Case W7-003
- **Prefecture:** 徳島県 / **Region Block:** 四国 / **Case Type:** Boundary / **User Profile:** 26歳、新卒2年目、大学病院勤務 / **Entry Route:** TikTok経由 / **Difficulty:** Hard
**Scenario:** 徳島大学病院勤務の看護師が「関東に出たい」と漠然と考えている。エリア選択で迷う。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「東京に行きたいけど、神奈川もいいかな...どっちがいいですか？」（自由テキスト入力）
4. Bot: エリア選択ボタンを再表示（テキスト入力に非対応の場合）
5. User: 「東京都」を選択
6. Bot: 施設タイプ選択
7. User: 「大学病院」（選択肢にない場合は「病院」）
8. Bot: 診療科→勤務形態→緊急度と進む
9. User: 各ステップで回答
10. Bot: 東京の病院を提示
**System Behavior Evaluation:** 自由テキストでの相談に対するBot応答が鍵。選択肢の再表示のみでは相談に答えていない。ただしエリア選択自体は正常に処理される。
**Results:** Drop-off: 中 / Job Proposal: 東京の病院 / Next Action: 東京vs神奈川の比較情報を人間が補足 / Region Bias: なし（東京選択） / National Expansion Risk: 低
**Failure Category:** AMBIG_FAIL / **Severity:** Medium / **Fix Proposal:** 自由テキスト入力時に「東京と神奈川、どちらもご紹介できますよ！まずはどちらかお選びください」等のガイドメッセージ / **Retry Needed:** No / **Auditor Comment:** 地方→関東希望者の「相談型」流入は四国で多い。テキスト応答力が問われる。

---

### Case W7-004
- **Prefecture:** 徳島県 / **Region Block:** 四国 / **Case Type:** Standard / **User Profile:** 35歳、訪問看護師、子供2人 / **Entry Route:** Google検索 / **Difficulty:** Normal
**Scenario:** 鳴門市の訪問看護師が夫の転勤（埼玉）に伴い転職先を探している。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「埼玉県」を選択
4. Bot: 施設タイプ選択
5. User: 「訪問看護」を選択
6. Bot: 診療科選択
7. User: 該当を選択
8. Bot: 勤務形態
9. User: 「常勤（日勤のみ）」
10. Bot: マッチング結果→埼玉の訪問看護ステーションを提示
**System Behavior Evaluation:** 転勤伴い転居のケースは正常フロー。埼玉はD1 DB対応エリアのため問題なくマッチング。
**Results:** Drop-off: 低 / Job Proposal: 埼玉の訪問看護 / Next Action: 詳細ヒアリング / Region Bias: なし / National Expansion Risk: なし
**Failure Category:** なし / **Severity:** None / **Fix Proposal:** なし / **Retry Needed:** No / **Auditor Comment:** 四国→関東転居の成功パターン。このケースでBotは正常機能する。

---

### Case W7-005
- **Prefecture:** 徳島県 / **Region Block:** 四国 / **Case Type:** Adversarial / **User Profile:** 不明（スパム疑い） / **Entry Route:** 不明 / **Difficulty:** Hard
**Scenario:** 「徳島の求人全部見せて」と繰り返し要求。選択肢を無視してテキスト連打。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「徳島の求人見せて」
4. Bot: エリア選択ボタン再表示
5. User: 「だから徳島って言ってるんだけど」
6. Bot: エリア選択ボタン再表示（同じ応答）
7. User: 「使えないBot」
8. Bot: 応答なし or エリア選択繰り返し
**System Behavior Evaluation:** 選択肢にない地域をテキストで要求するユーザーへの対応がループに陥る。「徳島」というキーワード認識ができず、永久にエリア選択を繰り返す。
**Results:** Drop-off: 確実 / Job Proposal: なし / Next Action: 人間引き継ぎ / Region Bias: 対応不可 / National Expansion Risk: 高
**Failure Category:** AMBIG_FAIL + GEO_LOCK / **Severity:** Critical / **Fix Proposal:** 3回テキスト入力が続いた場合は人間オペレーターに引き継ぎ。「徳島」等の非対応地域名検知時に対応エリア外メッセージを表示 / **Retry Needed:** Yes / **Auditor Comment:** 最も攻撃的だが最も現実的なケース。地元の求人を探す人が最初にやること。

---

### Case W7-006
- **Prefecture:** 徳島県 / **Region Block:** 四国 / **Case Type:** Standard / **User Profile:** 29歳、ICU看護師、夜勤多め / **Entry Route:** 友人紹介 / **Difficulty:** Normal
**Scenario:** 美馬市在住。夜勤の負担軽減のため転職検討中。神奈川に姉が住んでおり、引っ越しも視野。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「神奈川県」を選択
4. Bot: 施設タイプ選択
5. User: 「病院」
6. Bot: 診療科
7. User: 「ICU・集中治療」
8. Bot: 勤務形態
9. User: 「常勤（日勤のみ）」
10. Bot: マッチング結果→神奈川のICU/集中治療のある病院を提示
**System Behavior Evaluation:** 正常フロー。四国在住だが希望エリアが神奈川のため問題なくマッチング。夜勤→日勤希望の条件変更も正しく処理。
**Results:** Drop-off: 低 / Job Proposal: 神奈川の病院 / Next Action: 面談設定 / Region Bias: なし / National Expansion Risk: なし
**Failure Category:** なし / **Severity:** None / **Fix Proposal:** なし / **Retry Needed:** No / **Auditor Comment:** 四国→神奈川の親族頼りUターンは現実的パターン。正常動作。

---

### Case W7-007
- **Prefecture:** 徳島県 / **Region Block:** 四国 / **Case Type:** Boundary / **User Profile:** 38歳、透析看護師、シングルマザー / **Entry Route:** LP直接 / **Difficulty:** Hard
**Scenario:** 徳島市在住。子供の学校があるため引っ越し不可。地元での転職を強く希望。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「その他の地域」を選択
4. Bot: 施設タイプ選択
5. User: 「クリニック」
6. Bot: 診療科
7. User: 「透析」（選択肢にない場合は近い科を選択）
8. Bot: 勤務形態
9. User: 「パート（時短）」
10. Bot: マッチング結果→関東の施設を提示
**System Behavior Evaluation:** 引っ越し不可のユーザーに関東求人を提示するのは完全なミスマッチ。「その他の地域」の選択肢設計が、転居不可ユーザーを想定していない。
**Results:** Drop-off: 確実 / Job Proposal: 不適切（関東） / Next Action: 離脱→ネガティブ口コミリスク / Region Bias: 致命的 / National Expansion Risk: 最高
**Failure Category:** GEO_LOCK + JOB_MATCH_FAIL / **Severity:** Critical / **Fix Proposal:** 「その他の地域」選択後に「お住まいの地域での転職ですか？関東への転居もご検討中ですか？」の分岐質問を追加。転居不可→「現在、関東エリアのみのご紹介となります。お力になれず申し訳ございません」+代替リソース案内 / **Retry Needed:** Yes / **Auditor Comment:** シングルマザー×地方×転居不可は最も救えないパターン。離脱だけでなく悪評リスクあり。

---

### Case W7-008
- **Prefecture:** 徳島県 / **Region Block:** 四国 / **Case Type:** Boundary / **User Profile:** 24歳、新人看護師、精神科 / **Entry Route:** TikTok / **Difficulty:** Medium
**Scenario:** 徳島市の精神科病院に勤務する新人。パワハラで退職したく、すぐにでも辞めたい。場所はどこでもいい。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「どこでもいいから早く転職したい」（テキスト入力）
4. Bot: エリア選択ボタン再表示
5. User: 「東京都」を選択（消去法で）
6. Bot: 施設タイプ→診療科→勤務形態と進む
7. User: 「精神科」「常勤」
8. Bot: 緊急度質問
9. User: 「今すぐ」
10. Bot: マッチング結果→東京の精神科病院を提示
**System Behavior Evaluation:** 緊急性の高いケースだが、Bot は通常フローで処理。「どこでもいい」の自由テキストは無視される。緊急度を拾えている点は評価できるが、パワハラ相談には応答できない。
**Results:** Drop-off: 中 / Job Proposal: 東京の精神科 / Next Action: 緊急引き継ぎ / Region Bias: なし（東京選択） / National Expansion Risk: 低
**Failure Category:** HUMAN_HANDOFF_FAIL / **Severity:** High / **Fix Proposal:** 「今すぐ辞めたい」「パワハラ」等のキーワード検知時は即座に人間オペレーターへ引き継ぎ / **Retry Needed:** Yes / **Auditor Comment:** 緊急離職相談はBotでは限界。人間対応フラグが必要。

---

### Case W7-009
- **Prefecture:** 徳島県 / **Region Block:** 四国 / **Case Type:** Standard / **User Profile:** 50歳、看護部長経験、管理職希望 / **Entry Route:** Google検索 / **Difficulty:** Normal
**Scenario:** 徳島市の総合病院で看護部長を務めた後、定年前に新天地を求めて千葉へ転居予定。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「千葉県」を選択
4. Bot: 施設タイプ選択
5. User: 「病院」
6. Bot: 診療科
7. User: 「管理職」（選択肢にない場合は「その他」）
8. Bot: 勤務形態
9. User: 「常勤」
10. Bot: マッチング結果→千葉の病院を提示
**System Behavior Evaluation:** 管理職ポジションが選択肢にない場合のフォールバック処理が鍵。千葉はD1対応エリアのため地理的な問題はない。
**Results:** Drop-off: 低 / Job Proposal: 千葉の病院（管理職マッチ精度は不明） / Next Action: 管理職ポジション確認→人間引き継ぎ / Region Bias: なし / National Expansion Risk: なし
**Failure Category:** JOB_MATCH_FAIL / **Severity:** Low / **Fix Proposal:** 管理職・師長等の役職選択肢追加 / **Retry Needed:** No / **Auditor Comment:** 管理職マッチングはBot単体では限界。人間引き継ぎで対応可能。

---

## 香川県（9件）

### Case W7-010
- **Prefecture:** 香川県 / **Region Block:** 四国 / **Case Type:** Standard / **User Profile:** 30歳、総合病院の外科病棟、常勤 / **Entry Route:** Instagram / **Difficulty:** Normal
**Scenario:** 高松市在住。地元での転職を希望するが、Bot上に香川の選択肢がない。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「その他の地域」を選択
4. Bot: 施設タイプ選択
5. User: 「病院」
6. Bot: 診療科
7. User: 「外科」
8. Bot: 勤務形態
9. User: 「常勤（二交代）」
10. Bot: マッチング結果→関東の外科病院を提示
**System Behavior Evaluation:** 徳島同様、香川のユーザーも「その他の地域」経由で関東施設が提示される。高松は四国最大都市であり看護師需要も高いが、DBに施設がない。
**Results:** Drop-off: 高 / Job Proposal: 関東の外科病院 / Next Action: 離脱 / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK / **Severity:** Critical / **Fix Proposal:** W7-001と同一。エリア外事前告知必須 / **Retry Needed:** Yes / **Auditor Comment:** 高松は四国の中核都市。対応不可による機会損失が大きい。

---

### Case W7-011
- **Prefecture:** 香川県 / **Region Block:** 四国 / **Case Type:** Standard / **User Profile:** 27歳、NICU看護師、独身 / **Entry Route:** TikTok / **Difficulty:** Normal
**Scenario:** 丸亀市在住。東京の大きな病院で働いてみたい。関東への転居意欲高い。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「東京都」を選択
4. Bot: 施設タイプ
5. User: 「病院」
6. Bot: 診療科
7. User: 「NICU・小児」
8. Bot: 勤務形態
9. User: 「常勤（三交代）」
10. Bot: マッチング結果→東京のNICUのある病院を提示
**System Behavior Evaluation:** 関東志向の強いユーザーは正常フローで問題なし。NICUという専門性の高い希望にどこまでマッチできるかが鍵。
**Results:** Drop-off: 低 / Job Proposal: 東京の病院 / Next Action: 詳細ヒアリング / Region Bias: なし / National Expansion Risk: なし
**Failure Category:** なし / **Severity:** None / **Fix Proposal:** なし / **Retry Needed:** No / **Auditor Comment:** 四国→東京のキャリアアップ組。正常ケース。

---

### Case W7-012
- **Prefecture:** 香川県 / **Region Block:** 四国 / **Case Type:** Boundary / **User Profile:** 40歳、介護施設看護師、ブランク5年 / **Entry Route:** LP / **Difficulty:** Hard
**Scenario:** 坂出市在住。育児で5年ブランクあり。復職したいが自信がない。場所は問わないが現実的には四国圏内。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「その他の地域」を選択
4. Bot: 施設タイプ
5. User: 「介護施設」
6. Bot: 診療科
7. User: 該当を選択
8. Bot: 勤務形態
9. User: 「パート」
10. Bot: マッチング結果→関東の介護施設を提示
**System Behavior Evaluation:** ブランク復帰×地方×パートの複合条件。関東の施設を提示されても転居意欲がないため離脱する。ブランクに対するケアメッセージもない。
**Results:** Drop-off: 極高 / Job Proposal: 不適切 / Next Action: 離脱 / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + UX_DROP / **Severity:** High / **Fix Proposal:** ブランク復帰者向けの安心メッセージ追加。転居不可者への対応フロー整備 / **Retry Needed:** Yes / **Auditor Comment:** ブランク復帰者は不安が強く、ミスマッチ提案で二度と戻らない。

---

### Case W7-013
- **Prefecture:** 香川県 / **Region Block:** 四国 / **Case Type:** Standard / **User Profile:** 33歳、助産師、産婦人科勤務 / **Entry Route:** 紹介 / **Difficulty:** Normal
**Scenario:** 高松市在住の助産師が、神奈川で産婦人科の求人を探している。夫の転勤が決定。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「神奈川県」を選択
4. Bot: 施設タイプ
5. User: 「病院」
6. Bot: 診療科
7. User: 「産婦人科」
8. Bot: 勤務形態
9. User: 「常勤」
10. Bot: マッチング結果→神奈川の産婦人科を提示
**System Behavior Evaluation:** 正常フロー。助産師資格の考慮がマッチング精度に影響するが、基本的な診療科マッチは動作する。
**Results:** Drop-off: 低 / Job Proposal: 神奈川の産婦人科 / Next Action: 助産師資格を活かせるポジション確認 / Region Bias: なし / National Expansion Risk: なし
**Failure Category:** なし / **Severity:** None / **Fix Proposal:** 資格（助産師/保健師等）入力欄の追加検討 / **Retry Needed:** No / **Auditor Comment:** 正常ケース。助産師は看護師資格の上位互換のため問題なし。

---

### Case W7-014
- **Prefecture:** 香川県 / **Region Block:** 四国 / **Case Type:** Adversarial / **User Profile:** 不明 / **Entry Route:** 不明 / **Difficulty:** Hard
**Scenario:** 「香川うどん県の看護師です。うどん屋の近くの病院ありますか？」と冗談めいた入力。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「うどん県の病院教えて」（テキスト入力）
4. Bot: エリア選択ボタン再表示
5. User: 「香川の求人は？」
6. Bot: エリア選択ボタン再表示
7. User: 「その他の地域」を選択（諦めて）
8. Bot: 施設タイプ選択へ
**System Behavior Evaluation:** 冗談・方言・俗称への対応力テスト。「うどん県」=香川という解釈は不可。テキスト入力が続くとループするが、最終的に選択肢を使えば進行可能。
**Results:** Drop-off: 中 / Job Proposal: 関東施設 / Next Action: なし / Region Bias: 対応不可 / National Expansion Risk: 中
**Failure Category:** AMBIG_FAIL + TYPO_FAIL / **Severity:** Medium / **Fix Proposal:** 都道府県名のテキスト認識を追加（俗称含む） / **Retry Needed:** No / **Auditor Comment:** 冗談入力だがユーザー心理としては「香川の求人」を探している。テキスト認識がないと無駄なやり取りが発生。

---

### Case W7-015
- **Prefecture:** 香川県 / **Region Block:** 四国 / **Case Type:** Boundary / **User Profile:** 55歳、訪問看護管理者、定年前転職 / **Entry Route:** Google検索 / **Difficulty:** Medium
**Scenario:** 高松市在住。岡山（中国地方）への通勤も視野に入れている。瀬戸大橋で通えるエリア。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「岡山か高松で探してるんですけど」（テキスト入力）
4. Bot: エリア選択ボタン再表示
5. User: 「その他の地域」を選択
6. Bot: 施設タイプ→訪問看護→常勤と進む
7. Bot: マッチング結果→関東の訪問看護を提示
**System Behavior Evaluation:** 香川↔岡山の近県通勤は現実的だが、どちらもD1対応エリア外。テキストでの相談は無視される。複数県横断の希望を処理できない。
**Results:** Drop-off: 高 / Job Proposal: 不適切 / Next Action: 離脱 / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + AMBIG_FAIL / **Severity:** High / **Fix Proposal:** 複数エリア希望の処理フロー。テキスト内の都道府県名認識 / **Retry Needed:** Yes / **Auditor Comment:** 瀬戸大橋通勤圏は香川看護師の現実。「その他」1択は粗すぎる。

---

### Case W7-016
- **Prefecture:** 香川県 / **Region Block:** 四国 / **Case Type:** Standard / **User Profile:** 31歳、手術室看護師、キャリアアップ志向 / **Entry Route:** LP / **Difficulty:** Normal
**Scenario:** 善通寺市在住。手術室の経験を積むため、東京の大病院への転職を計画中。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「東京都」を選択
4. Bot: 施設タイプ
5. User: 「病院」
6. Bot: 診療科
7. User: 「手術室・オペ室」（選択肢にない場合は「外科」）
8. Bot: 勤務形態
9. User: 「常勤（二交代）」
10. Bot: マッチング結果→東京の病院を提示
**System Behavior Evaluation:** 正常フロー。オペ室という専門希望が選択肢にあるかが精度に影響。東京選択で地理的問題なし。
**Results:** Drop-off: 低 / Job Proposal: 東京の病院 / Next Action: 手術室配属確認 / Region Bias: なし / National Expansion Risk: なし
**Failure Category:** なし / **Severity:** None / **Fix Proposal:** 手術室/オペ室の選択肢追加が望ましい / **Retry Needed:** No / **Auditor Comment:** キャリアアップ目的の四国→東京は多い。正常動作。

---

### Case W7-017
- **Prefecture:** 香川県 / **Region Block:** 四国 / **Case Type:** Adversarial / **User Profile:** 不明（看護学生の可能性） / **Entry Route:** TikTok / **Difficulty:** Hard
**Scenario:** 「まだ学生なんですけど来年の就職先を探してます」。新卒対応の可否テスト。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「まだ看護学生です。来年香川で就職したいです」（テキスト入力）
4. Bot: エリア選択ボタン再表示
5. User: 「その他の地域」を選択
6. Bot: 施設タイプ→通常フロー継続
7. User: 各質問に回答
8. Bot: マッチング結果→関東施設を提示
**System Behavior Evaluation:** 学生（未資格者）がフローに入れてしまう点が問題。紹介事業は有資格者対象のため、学生には就職支援ナビ等を案内すべき。
**Results:** Drop-off: 高 / Job Proposal: 不適切（新卒対応外＋エリア外） / Next Action: 学生向けリソース案内 / Region Bias: 関東偏重 / National Expansion Risk: 中
**Failure Category:** INPUT_LOCK + GEO_LOCK / **Severity:** High / **Fix Proposal:** 最初のステップに「現在の状況」（現役看護師/ブランク中/学生）の選択を追加。学生→新卒ナビ案内へ分岐 / **Retry Needed:** Yes / **Auditor Comment:** TikTok経由で学生流入は十分あり得る。対象外ユーザーの適切な振り分けが必要。

---

### Case W7-018
- **Prefecture:** 香川県 / **Region Block:** 四国 / **Case Type:** Standard / **User Profile:** 36歳、救急看護認定看護師 / **Entry Route:** 友人紹介 / **Difficulty:** Normal
**Scenario:** 三豊市在住。認定看護師資格を活かして埼玉の救命救急センターへ転職希望。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「埼玉県」を選択
4. Bot: 施設タイプ
5. User: 「病院」
6. Bot: 診療科
7. User: 「救急」
8. Bot: 勤務形態
9. User: 「常勤（三交代）」
10. Bot: マッチング結果→埼玉の救急対応病院を提示
**System Behavior Evaluation:** 正常フロー。認定看護師という高スキル人材の情報を取得する欄がないが、マッチング自体は問題なし。
**Results:** Drop-off: 低 / Job Proposal: 埼玉の救急病院 / Next Action: 認定看護師資格の活用相談 / Region Bias: なし / National Expansion Risk: なし
**Failure Category:** なし / **Severity:** None / **Fix Proposal:** 認定看護師/専門看護師等の資格入力欄追加 / **Retry Needed:** No / **Auditor Comment:** 高スキル人材は手数料収益も高い。資格情報の取得は改善ポイント。

---

## 愛媛県（9件）

### Case W7-019
- **Prefecture:** 愛媛県 / **Region Block:** 四国 / **Case Type:** Standard / **User Profile:** 28歳、急性期病棟、常勤 / **Entry Route:** Instagram広告 / **Difficulty:** Normal
**Scenario:** 松山市在住。地元愛媛での転職を希望。SNS広告の「シン・AI転職」に興味を持った。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「その他の地域」を選択
4. Bot: 施設タイプ
5. User: 「病院」
6. Bot: 診療科
7. User: 「循環器」
8. Bot: 勤務形態
9. User: 「常勤（日勤のみ）」
10. Bot: マッチング結果→関東施設を提示
**System Behavior Evaluation:** ペルソナ「ミサキ」に最も近いプロフィール。愛媛で転職したいのに関東を提示される。広告から期待を持って流入したのにギャップが大きい。
**Results:** Drop-off: 極高 / Job Proposal: 不適切 / Next Action: 離脱+LINEブロック / Region Bias: 関東偏重 / National Expansion Risk: 最高
**Failure Category:** GEO_LOCK / **Severity:** Critical / **Fix Proposal:** 広告配信エリアを関東に限定するか、エリア外対応フローを整備 / **Retry Needed:** Yes / **Auditor Comment:** 広告でリーチした愛媛ユーザーがBot で裏切られるパターン。広告費の無駄+ブランド毀損。

---

### Case W7-020
- **Prefecture:** 愛媛県 / **Region Block:** 四国 / **Case Type:** Standard / **User Profile:** 34歳、回復期リハ病棟、既婚 / **Entry Route:** SEOブログ / **Difficulty:** Normal
**Scenario:** 今治市在住。ブログ記事「看護師の転職時期」を読んでLINE登録。夫と大阪への転居を検討中。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「その他の地域」を選択（大阪がリストにないため）
4. Bot: 施設タイプ
5. User: 「病院」
6. Bot: 診療科→勤務形態→緊急度
7. User: 各ステップ回答
8. Bot: マッチング結果→関東施設を提示
**System Behavior Evaluation:** 大阪希望なのに選択肢にないため「その他」を選ぶしかなく、関東が出る。愛媛→大阪は地理的に自然な転居先だが、対応できない。
**Results:** Drop-off: 高 / Job Proposal: 不適切（関東） / Next Action: 離脱 / Region Bias: 関東偏重。大阪非対応が致命的 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK / **Severity:** High / **Fix Proposal:** 大阪をエリア選択肢に追加。または「その他」選択時に希望エリアをテキスト入力可能にし、非対応なら明示 / **Retry Needed:** Yes / **Auditor Comment:** 四国→大阪の人口移動は多い。大阪非対応は機会損失大。

---

### Case W7-021
- **Prefecture:** 愛媛県 / **Region Block:** 四国 / **Case Type:** Boundary / **User Profile:** 22歳、新卒1年目、精神的に疲弊 / **Entry Route:** TikTok / **Difficulty:** Hard
**Scenario:** 松山市の急性期病院で新卒配属。プリセプターとの関係が悪く、毎日泣いている。「もう辞めたい」。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「もう無理です。辞めたいです。助けてください」（テキスト入力）
4. Bot: エリア選択ボタン再表示
5. User: 「話聞いてほしいだけなのに...」
6. Bot: エリア選択ボタン再表示
7. User: ブロック
**System Behavior Evaluation:** 精神的に追い詰められたユーザーに対し、機械的にエリア選択を繰り返すのは最悪のUX。「辞めたい」「助けて」等のSOSワードへの対応がゼロ。
**Results:** Drop-off: 確実（ブロック） / Job Proposal: なし / Next Action: なし / Region Bias: N/A / National Expansion Risk: 中
**Failure Category:** HUMAN_HANDOFF_FAIL + UX_DROP / **Severity:** Critical / **Fix Proposal:** SOSキーワード（辞めたい/助けて/つらい/無理）検知で即人間引き継ぎ+「お気持ちお聞かせいただきありがとうございます」等の共感メッセージ。必要に応じて相談窓口案内 / **Retry Needed:** Yes / **Auditor Comment:** 最も深刻なケース。若手看護師のメンタルヘルスは社会問題。冷淡な応答はブランド致命傷。

---

### Case W7-022
- **Prefecture:** 愛媛県 / **Region Block:** 四国 / **Case Type:** Standard / **User Profile:** 42歳、訪問看護、ケアマネ資格あり / **Entry Route:** LP / **Difficulty:** Normal
**Scenario:** 宇和島市在住。子供の大学進学に合わせて東京へ引っ越し予定。訪問看護の仕事を探したい。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「東京都」を選択
4. Bot: 施設タイプ
5. User: 「訪問看護」
6. Bot: 診療科→勤務形態→緊急度
7. User: 各ステップ回答
8. Bot: マッチング結果→東京の訪問看護を提示
**System Behavior Evaluation:** 正常フロー。東京選択で地理的問題なし。ケアマネ資格は取得できないが人間引き継ぎで対応可能。
**Results:** Drop-off: 低 / Job Proposal: 東京の訪問看護 / Next Action: ケアマネ資格活用の詳細相談 / Region Bias: なし / National Expansion Risk: なし
**Failure Category:** なし / **Severity:** None / **Fix Proposal:** なし / **Retry Needed:** No / **Auditor Comment:** 子供の進学に合わせた転居は現実的パターン。正常動作。

---

### Case W7-023
- **Prefecture:** 愛媛県 / **Region Block:** 四国 / **Case Type:** Boundary / **User Profile:** 48歳、療養型病院、腰痛あり / **Entry Route:** Google検索 / **Difficulty:** Medium
**Scenario:** 新居浜市在住。腰痛が悪化して病棟業務が厳しい。身体負担の少ない職場を探したいが、愛媛県内限定。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「その他の地域」を選択
4. Bot: 施設タイプ
5. User: 「クリニック」
6. Bot: 診療科
7. User: 「皮膚科」（身体負担少ない科を希望）
8. Bot: 勤務形態
9. User: 「パート」
10. Bot: マッチング結果→関東のクリニックを提示
**System Behavior Evaluation:** 身体的制約のあるユーザーに転居を伴う求人を提示するのは非現実的。「腰痛で身体負担の少ない仕事」という条件をBotは取得できない。
**Results:** Drop-off: 確実 / Job Proposal: 不適切 / Next Action: 離脱 / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + JOB_MATCH_FAIL / **Severity:** High / **Fix Proposal:** 身体的制約・健康上の条件入力ステップ追加。転居不可者への早期告知 / **Retry Needed:** Yes / **Auditor Comment:** 身体的制約×地方×転居不可のトリプルミスマッチ。

---

### Case W7-024
- **Prefecture:** 愛媛県 / **Region Block:** 四国 / **Case Type:** Adversarial / **User Profile:** 不明（医師の可能性） / **Entry Route:** 誤登録 / **Difficulty:** Hard
**Scenario:** 「医師ですが看護師の求人サイトですか？」と質問。誤登録対応テスト。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「医師なんですが、ここは看護師専門ですか？」
4. Bot: エリア選択ボタン再表示
5. User: 「質問に答えてくれないの？」
6. Bot: エリア選択ボタン再表示
7. User: ブロック
**System Behavior Evaluation:** 対象外職種からの問い合わせに対し全く応答できない。テキスト入力への対応がないため、質問がループする。
**Results:** Drop-off: 確実 / Job Proposal: なし / Next Action: なし / Region Bias: N/A / National Expansion Risk: 低
**Failure Category:** AMBIG_FAIL / **Severity:** Medium / **Fix Proposal:** 「看護師専門の転職サービスです」という自己紹介メッセージを自由テキスト入力時に返す / **Retry Needed:** No / **Auditor Comment:** 誤登録は少数だが、応答なしはサービス品質の問題。

---

### Case W7-025
- **Prefecture:** 愛媛県 / **Region Block:** 四国 / **Case Type:** Standard / **User Profile:** 25歳、美容クリニック勤務 / **Entry Route:** Instagram / **Difficulty:** Normal
**Scenario:** 松山市在住。美容クリニックの経験を活かして東京の美容クリニックへ転職したい。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「東京都」を選択
4. Bot: 施設タイプ
5. User: 「クリニック」
6. Bot: 診療科
7. User: 「美容」（選択肢にない場合は「皮膚科」等）
8. Bot: 勤務形態
9. User: 「常勤（日勤のみ）」
10. Bot: マッチング結果→東京のクリニックを提示
**System Behavior Evaluation:** 正常フロー。美容クリニックが診療科選択肢にあるかが精度に影響。東京の美容クリニック求人は豊富なためマッチは比較的容易。
**Results:** Drop-off: 低 / Job Proposal: 東京のクリニック / Next Action: 美容分野の詳細確認 / Region Bias: なし / National Expansion Risk: なし
**Failure Category:** なし / **Severity:** None / **Fix Proposal:** 美容外科/美容皮膚科の選択肢追加 / **Retry Needed:** No / **Auditor Comment:** 美容クリニック看護師は若い女性に多い。正常ケース。

---

### Case W7-026
- **Prefecture:** 愛媛県 / **Region Block:** 四国 / **Case Type:** Boundary / **User Profile:** 37歳、病棟主任、年収500万以上希望 / **Entry Route:** Google検索 / **Difficulty:** Medium
**Scenario:** 西条市在住。現職年収450万。年収アップが最優先条件。エリアは問わないが具体的にいくら上がるか知りたい。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「年収500万以上の求人ありますか？」（テキスト入力）
4. Bot: エリア選択ボタン再表示
5. User: 「神奈川県」を選択（年収が高そうだから）
6. Bot: 施設タイプ→診療科→勤務形態と進む
7. User: 各ステップ回答
8. Bot: マッチング結果→神奈川の施設を提示（年収情報なし）
**System Behavior Evaluation:** 年収条件をBotは取得できない。マッチング結果にも年収情報が含まれていない可能性。ユーザーの最重要条件が無視される。
**Results:** Drop-off: 中 / Job Proposal: 神奈川の施設（年収不明） / Next Action: 年収情報は人間が補足 / Region Bias: なし / National Expansion Risk: なし
**Failure Category:** JOB_MATCH_FAIL / **Severity:** Medium / **Fix Proposal:** 希望年収入力ステップの追加。マッチング結果に年収レンジ表示 / **Retry Needed:** No / **Auditor Comment:** 年収は転職動機の最上位。Bot で取れないのは設計上の穴。

---

### Case W7-027
- **Prefecture:** 愛媛県 / **Region Block:** 四国 / **Case Type:** Standard / **User Profile:** 30歳、ER看護師 / **Entry Route:** TikTok / **Difficulty:** Normal
**Scenario:** 八幡浜市在住。離島医療に興味があり、沖縄や離島の求人を探している。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「その他の地域」を選択
4. Bot: 施設タイプ
5. User: 「病院」
6. Bot: 診療科
7. User: 「救急」
8. Bot: 勤務形態
9. User: 「常勤」
10. Bot: マッチング結果→関東施設を提示
**System Behavior Evaluation:** 離島医療希望者に関東の救急病院を提示。ユーザーの志向と全く合わない。「その他の地域」の期待値と実際の結果のギャップが最大。
**Results:** Drop-off: 確実 / Job Proposal: 完全不適切 / Next Action: 離脱 / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + JOB_MATCH_FAIL / **Severity:** High / **Fix Proposal:** 「その他の地域」選択時にフリーテキストで希望地域を入力させ、非対応なら明確に伝える / **Retry Needed:** Yes / **Auditor Comment:** 離島医療志望者は少数だが志が高い。ミスマッチ提案は失礼。

---

## 高知県（9件）

### Case W7-028
- **Prefecture:** 高知県 / **Region Block:** 四国 / **Case Type:** Standard / **User Profile:** 29歳、急性期病棟、独身 / **Entry Route:** LP / **Difficulty:** Normal
**Scenario:** 高知市在住。高知での転職を希望。地元を離れたくない。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「その他の地域」を選択
4. Bot: 施設タイプ
5. User: 「病院」
6. Bot: 診療科
7. User: 「消化器」
8. Bot: 勤務形態
9. User: 「常勤」
10. Bot: マッチング結果→関東施設を提示
**System Behavior Evaluation:** 高知は四国で最も人口が少なく、看護師の転職市場も小さい。しかし地元志向が強い県民性があり、関東提示は完全にミスマッチ。
**Results:** Drop-off: 極高 / Job Proposal: 不適切 / Next Action: 離脱+ネガティブ口コミ / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK / **Severity:** Critical / **Fix Proposal:** エリア外事前告知。高知県のナースセンター・ハローワーク情報の代替案内 / **Retry Needed:** Yes / **Auditor Comment:** 高知県民は地元愛が強い。関東を出すのは逆効果。

---

### Case W7-029
- **Prefecture:** 高知県 / **Region Block:** 四国 / **Case Type:** Standard / **User Profile:** 33歳、透析室看護師、夫婦共働き / **Entry Route:** SEOブログ / **Difficulty:** Normal
**Scenario:** 四万十市在住。夫の仕事の都合で神奈川に引っ越し予定。透析経験を活かしたい。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「神奈川県」を選択
4. Bot: 施設タイプ
5. User: 「クリニック」
6. Bot: 診療科
7. User: 「透析」（選択肢にない場合は「腎臓内科」等）
8. Bot: 勤務形態
9. User: 「常勤（日勤のみ）」
10. Bot: マッチング結果→神奈川の透析クリニックを提示
**System Behavior Evaluation:** 正常フロー。神奈川選択で問題なし。透析が診療科選択肢にあるかが精度に影響。
**Results:** Drop-off: 低 / Job Proposal: 神奈川の透析施設 / Next Action: 詳細ヒアリング / Region Bias: なし / National Expansion Risk: なし
**Failure Category:** なし / **Severity:** None / **Fix Proposal:** なし / **Retry Needed:** No / **Auditor Comment:** 高知→神奈川の転居ケース。正常。

---

### Case W7-030
- **Prefecture:** 高知県 / **Region Block:** 四国 / **Case Type:** Boundary / **User Profile:** 52歳、看護教員、大学勤務 / **Entry Route:** Google検索 / **Difficulty:** Hard
**Scenario:** 高知市の看護大学教員。臨床に戻りたいが、20年のブランクがある。場所は問わない。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「場所は問いませんが、ブランク20年でも受け入れてくれる病院はありますか？」（テキスト入力）
4. Bot: エリア選択ボタン再表示
5. User: 「東京都」を選択
6. Bot: 施設タイプ→診療科→勤務形態
7. User: 「病院」「内科」「常勤」
8. Bot: マッチング結果→東京の病院を提示
**System Behavior Evaluation:** 20年ブランクという極端な条件に対するフィルタリングがない。テキストでの相談は無視。マッチング自体は動くが、ブランク20年を受け入れる病院かどうかは不明。
**Results:** Drop-off: 中 / Job Proposal: 東京の病院（ブランク考慮なし） / Next Action: 人間がブランク対応可の施設を選定 / Region Bias: なし / National Expansion Risk: なし
**Failure Category:** JOB_MATCH_FAIL + AMBIG_FAIL / **Severity:** Medium / **Fix Proposal:** ブランク年数入力ステップ追加。長期ブランクは人間引き継ぎフラグ / **Retry Needed:** No / **Auditor Comment:** 看護教員→臨床復帰は特殊ケース。人間対応必須。

---

### Case W7-031
- **Prefecture:** 高知県 / **Region Block:** 四国 / **Case Type:** Adversarial / **User Profile:** 不明（競合調査の可能性） / **Entry Route:** 直接LINE追加 / **Difficulty:** Hard
**Scenario:** 全フローを高速で進み、複数パターンで繰り返しテスト。競合他社による偵察行動。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「東京都」→病院→外科→常勤→マッチング結果確認
4. User: 再度最初から「神奈川県」→クリニック→内科→パート→マッチング結果確認
5. User: 再度「埼玉県」→介護施設→リハビリ→常勤→マッチング結果確認
6. User: 短時間で3回全フロー実行
**System Behavior Evaluation:** 短時間での複数フロー実行に対するレート制限がない。競合による情報収集を防ぐ仕組みがない。ただし施設DBの情報は公開情報ベースのためリスクは低い。
**Results:** Drop-off: N/A（意図的離脱） / Job Proposal: 複数回提示 / Next Action: なし / Region Bias: なし / National Expansion Risk: 低
**Failure Category:** OTHER / **Severity:** Low / **Fix Proposal:** 短時間での複数フロー実行検知。24時間以内に3回以上全フロー完了したらフラグ+Slack通知 / **Retry Needed:** No / **Auditor Comment:** 競合偵察は起こりうる。対策は低優先だが認識は必要。

---

### Case W7-032
- **Prefecture:** 高知県 / **Region Block:** 四国 / **Case Type:** Boundary / **User Profile:** 26歳、離島診療所勤務 / **Entry Route:** TikTok / **Difficulty:** Medium
**Scenario:** 高知県の離島（沖の島）勤務。都会に出たいが、どの都市がいいかわからない。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「都会で働きたいです。おすすめはどこですか？」（テキスト入力）
4. Bot: エリア選択ボタン再表示
5. User: 「東京都」を選択（とりあえず）
6. Bot: 施設タイプ→診療科→勤務形態
7. User: 「病院」「総合」「常勤」
8. Bot: マッチング結果→東京の病院を提示
**System Behavior Evaluation:** 「おすすめ」を聞くユーザーに対しBotは選択肢を再提示するのみ。相談型の対話には対応不可。ただし最終的にフローは完了。
**Results:** Drop-off: 低〜中 / Job Proposal: 東京の病院 / Next Action: 詳細ヒアリングで希望をすり合わせ / Region Bias: なし / National Expansion Risk: なし
**Failure Category:** AMBIG_FAIL / **Severity:** Low / **Fix Proposal:** 「おすすめ」等の相談型入力時に各エリアの特徴を簡単に紹介するメッセージ / **Retry Needed:** No / **Auditor Comment:** 離島→都会は勇気のいる決断。Botの対応が冷たいと離脱する。

---

### Case W7-033
- **Prefecture:** 高知県 / **Region Block:** 四国 / **Case Type:** Standard / **User Profile:** 31歳、精神科看護師 / **Entry Route:** Instagram / **Difficulty:** Normal
**Scenario:** 南国市在住。精神科経験を活かして千葉の精神科病院へ転職希望。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「千葉県」を選択
4. Bot: 施設タイプ
5. User: 「病院」
6. Bot: 診療科
7. User: 「精神科」
8. Bot: 勤務形態
9. User: 「常勤（二交代）」
10. Bot: マッチング結果→千葉の精神科病院を提示
**System Behavior Evaluation:** 正常フロー。千葉は対応エリア。精神科は診療科選択肢にあるため問題なし。
**Results:** Drop-off: 低 / Job Proposal: 千葉の精神科病院 / Next Action: 詳細ヒアリング / Region Bias: なし / National Expansion Risk: なし
**Failure Category:** なし / **Severity:** None / **Fix Proposal:** なし / **Retry Needed:** No / **Auditor Comment:** 正常ケース。高知→千葉は距離があるが本人の意思。

---

### Case W7-034
- **Prefecture:** 高知県 / **Region Block:** 四国 / **Case Type:** Adversarial / **User Profile:** 不明 / **Entry Route:** 不明 / **Difficulty:** Hard
**Scenario:** 英語でメッセージを送信。外国人看護師の可能性。「I'm a nurse in Kochi. Are there any jobs?」
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ（日本語）+エリア選択
3. User: "I'm looking for nursing jobs in Japan"
4. Bot: エリア選択ボタン再表示（日本語のみ）
5. User: "Do you speak English?"
6. Bot: エリア選択ボタン再表示
7. User: 離脱
**System Behavior Evaluation:** 多言語対応が一切ない。外国人看護師（EPA等）の存在を考慮していない。高知には外国人技能実習生・EPA看護師がいる。
**Results:** Drop-off: 確実 / Job Proposal: なし / Next Action: なし / Region Bias: N/A / National Expansion Risk: 中
**Failure Category:** AMBIG_FAIL + UX_DROP / **Severity:** Medium / **Fix Proposal:** 英語テキスト検知時に「申し訳ございません。日本語のみ対応しています / Sorry, Japanese only.」のバイリンガルメッセージ返信 / **Retry Needed:** No / **Auditor Comment:** EPA看護師の増加を考えると最低限の英語対応は将来必要。

---

### Case W7-035
- **Prefecture:** 高知県 / **Region Block:** 四国 / **Case Type:** Boundary / **User Profile:** 44歳、老健看護師、親の介護中 / **Entry Route:** LP / **Difficulty:** Medium
**Scenario:** 高知市在住。実家の親の介護をしながら夜勤なしの仕事を探している。高知県内のみ。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「その他の地域」を選択
4. Bot: 施設タイプ
5. User: 「介護施設」
6. Bot: 診療科→勤務形態
7. User: 「パート（日勤のみ）」
8. Bot: マッチング結果→関東の介護施設を提示
**System Behavior Evaluation:** 親の介護中で転居不可のユーザーに関東施設を提示。最も乖離が大きいケース。高知の介護施設は人手不足で需要はあるが対応不可。
**Results:** Drop-off: 確実 / Job Proposal: 不適切 / Next Action: 離脱 / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK / **Severity:** Critical / **Fix Proposal:** 転居可否の確認ステップ。転居不可→エリア外告知+地元リソース案内 / **Retry Needed:** Yes / **Auditor Comment:** 介護離職と転職のダブル苦。最も支援が必要な層にリーチできない。

---

### Case W7-036
- **Prefecture:** 高知県 / **Region Block:** 四国 / **Case Type:** Standard / **User Profile:** 27歳、産婦人科、結婚予定 / **Entry Route:** 紹介 / **Difficulty:** Normal
**Scenario:** 室戸市在住。婚約者が埼玉在住のため結婚を機に転居予定。産婦人科の経験を活かしたい。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「埼玉県」を選択
4. Bot: 施設タイプ
5. User: 「病院」
6. Bot: 診療科
7. User: 「産婦人科」
8. Bot: 勤務形態
9. User: 「常勤」
10. Bot: マッチング結果→埼玉の産婦人科を提示
**System Behavior Evaluation:** 正常フロー。埼玉は対応エリアのため問題なし。
**Results:** Drop-off: 低 / Job Proposal: 埼玉の産婦人科 / Next Action: 詳細ヒアリング / Region Bias: なし / National Expansion Risk: なし
**Failure Category:** なし / **Severity:** None / **Fix Proposal:** なし / **Retry Needed:** No / **Auditor Comment:** 結婚を機に転居は多いパターン。正常動作。

---

## 予備枠（4件）

### Case W7-037
- **Prefecture:** 徳島県 / **Region Block:** 四国 / **Case Type:** Adversarial / **User Profile:** 不明 / **Entry Route:** 不明 / **Difficulty:** Hard
**Scenario:** 同一アカウントで1回目は「その他の地域」、2回目は「東京都」を選択。途中で条件を全部変える。
**Conversation Flow:**
1. User: LINE友だち追加→「その他の地域」→病院→外科→常勤
2. Bot: マッチング結果→関東施設提示
3. User: 「やっぱり最初からやり直したい」
4. Bot: 応答不明（リセット機能の有無）
5. User: 「東京都」と入力
6. Bot: エリア選択ボタン再表示 or フロー継続不能
7. User: 離脱
**System Behavior Evaluation:** フロー再開・リセット機能の有無がテストポイント。マッチング後のやり直しに対応できるか。
**Results:** Drop-off: 高 / Job Proposal: 1回目のみ / Next Action: なし / Region Bias: N/A / National Expansion Risk: 中
**Failure Category:** REENTRY_FAIL / **Severity:** High / **Fix Proposal:** 「最初からやり直す」ボタンまたはキーワード対応。24時間以内のリセット機能 / **Retry Needed:** Yes / **Auditor Comment:** やり直し要求は頻出。リセット機能は必須UX。

---

### Case W7-038
- **Prefecture:** 香川県 / **Region Block:** 四国 / **Case Type:** Boundary / **User Profile:** 39歳、デイサービス看護師 / **Entry Route:** LP / **Difficulty:** Medium
**Scenario:** 高松市在住。深夜2時にLINE登録。「今すぐ転職相談したい」。深夜対応テスト。
**Conversation Flow:**
1. User: 深夜2:00にLINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択（即時応答）
3. User: 「今すぐ相談できますか？」（テキスト入力）
4. Bot: エリア選択ボタン再表示
5. User: 「その他の地域」→介護施設→パート
6. Bot: マッチング結果→関東の介護施設を提示
7. User: 「これじゃなくて高松の求人が欲しいんです」
8. Bot: 応答なし or 同じ結果を再表示
**System Behavior Evaluation:** 深夜でもBotは即応答できる点は評価。しかしエリア外+相談型ニーズの両方に対応不可。深夜は人間引き継ぎもできない。
**Results:** Drop-off: 高 / Job Proposal: 不適切 / Next Action: 翌朝人間対応 / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + HUMAN_HANDOFF_FAIL / **Severity:** High / **Fix Proposal:** 深夜帯は「翌朝○時にオペレーターからご連絡します」のメッセージ。エリア外は即告知 / **Retry Needed:** Yes / **Auditor Comment:** 夜勤明け看護師の深夜アクセスは多い。24時間Bot対応の強みを活かすべき。

---

### Case W7-039
- **Prefecture:** 愛媛県 / **Region Block:** 四国 / **Case Type:** Adversarial / **User Profile:** 不明 / **Entry Route:** 不明 / **Difficulty:** Hard
**Scenario:** 「個人情報を入力したくない。求人だけ見せて。」と要求。情報提供拒否テスト。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「個人情報は教えたくないです。求人一覧だけ見れますか？」
4. Bot: エリア選択ボタン再表示
5. User: 「名前とか電話番号は聞かれますか？」
6. Bot: エリア選択ボタン再表示
7. User: 「その他の地域」を選択（渋々）
8. Bot: フロー進行（個人情報は聞かない）
9. User: マッチング結果まで到達
10. Bot: マッチング結果→関東施設を提示+LINE相談誘導
**System Behavior Evaluation:** 実際にはBotフローで氏名・電話番号は聞かれないが、ユーザーの不安に対する説明がない。プライバシーポリシー案内もない。
**Results:** Drop-off: 中 / Job Proposal: 関東施設 / Next Action: なし / Region Bias: 関東偏重 / National Expansion Risk: 中
**Failure Category:** INPUT_LOCK + AMBIG_FAIL / **Severity:** Medium / **Fix Proposal:** 「お名前や電話番号はお聞きしません。条件に合う求人をお探しします」の安心メッセージ。プライバシーポリシーへのリンク / **Retry Needed:** No / **Auditor Comment:** プライバシー懸念は増加傾向。安心感の提供はCVR向上に直結。

---

### Case W7-040
- **Prefecture:** 高知県 / **Region Block:** 四国 / **Case Type:** Boundary / **User Profile:** 35歳、保健師資格あり、行政勤務 / **Entry Route:** Google検索 / **Difficulty:** Medium
**Scenario:** 高知市在住の保健師。臨床看護に転向したい。看護師としてのブランクが長い。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「保健師から看護師に転職したいんですが」（テキスト入力）
4. Bot: エリア選択ボタン再表示
5. User: 「その他の地域」を選択
6. Bot: 施設タイプ→診療科→勤務形態
7. User: 「クリニック」「内科」「常勤」
8. Bot: マッチング結果→関東のクリニック提示
**System Behavior Evaluation:** 保健師→看護師という特殊な転向相談をBotは処理できない。テキスト入力は無視。加えてエリア外問題も重なる。
**Results:** Drop-off: 高 / Job Proposal: 不適切 / Next Action: 離脱 / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + AMBIG_FAIL / **Severity:** High / **Fix Proposal:** 職種転向相談は人間引き継ぎフラグ。現在の資格・職種入力ステップ追加 / **Retry Needed:** Yes / **Auditor Comment:** 保健師→看護師転向は専門的相談。Bot単体では無理。

---

## クロスリージョン（10件）

### Case W7-041
- **Prefecture:** 東京都 / **Region Block:** 関東 / **Case Type:** Standard / **User Profile:** 28歳、愛媛出身、東京在住、急性期 / **Entry Route:** Instagram / **Difficulty:** Normal
**Scenario:** 愛媛出身で東京の病院に勤務中。都内で転職希望。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「東京都」を選択
4. Bot: 施設タイプ→病院→内科→常勤→マッチング結果
5. Bot: 東京の病院を提示
**System Behavior Evaluation:** 完全正常フロー。東京在住の東京希望。
**Results:** Drop-off: 低 / Job Proposal: 東京の病院 / Next Action: 詳細ヒアリング / Region Bias: なし / National Expansion Risk: なし
**Failure Category:** なし / **Severity:** None / **Fix Proposal:** なし / **Retry Needed:** No / **Auditor Comment:** 基準ケース。問題なし。

---

### Case W7-042
- **Prefecture:** 東京都 / **Region Block:** 関東 / **Case Type:** Standard / **User Profile:** 35歳、高知出身、東京在住、Uターン検討中 / **Entry Route:** TikTok / **Difficulty:** Normal
**Scenario:** 高知出身で東京勤務。親の高齢化でUターンも考えているが、まずは東京で探す。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「東京都」を選択
4. Bot: 施設タイプ
5. User: 「訪問看護」
6. Bot: 診療科→勤務形態
7. User: 「常勤（日勤のみ）」
8. Bot: マッチング結果→東京の訪問看護を提示
**System Behavior Evaluation:** 正常フロー。Uターン検討は現時点ではBot対応外だが、今は東京を選択しているため問題なし。
**Results:** Drop-off: 低 / Job Proposal: 東京の訪問看護 / Next Action: Uターンの可能性は人間ヒアリングで確認 / Region Bias: なし / National Expansion Risk: なし
**Failure Category:** なし / **Severity:** None / **Fix Proposal:** なし / **Retry Needed:** No / **Auditor Comment:** 将来的にUターン希望が出た時の対応は課題だが、現時点は正常。

---

### Case W7-043
- **Prefecture:** 大阪府 / **Region Block:** 関西 / **Case Type:** Boundary / **User Profile:** 30歳、香川出身、大阪在住 / **Entry Route:** LP / **Difficulty:** Medium
**Scenario:** 香川出身で大阪の病院に勤務。大阪での転職を希望するが、大阪はエリア選択肢にない。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「大阪」とテキスト入力
4. Bot: エリア選択ボタン再表示
5. User: 「その他の地域」を選択
6. Bot: 施設タイプ→病院→循環器→常勤
7. Bot: マッチング結果→関東の病院を提示
8. User: 「大阪の求人が欲しいんですけど」
9. Bot: 応答なし
**System Behavior Evaluation:** 大阪は人口第3位の都市だが選択肢にない。「その他の地域」経由で関東施設が出るのはミスマッチ。大阪ユーザーの取りこぼしは大きい。
**Results:** Drop-off: 確実 / Job Proposal: 不適切 / Next Action: 離脱 / Region Bias: 関東偏重 / National Expansion Risk: 最高
**Failure Category:** GEO_LOCK + REGION_EXPANSION_FAIL / **Severity:** Critical / **Fix Proposal:** 大阪をD1 DB対応エリアに追加。少なくともエリア選択肢に追加して人間引き継ぎ / **Retry Needed:** Yes / **Auditor Comment:** 大阪非対応は国内第2の看護師市場を捨てている。事業拡大時の最優先。

---

### Case W7-044
- **Prefecture:** 大阪府 / **Region Block:** 関西 / **Case Type:** Standard / **User Profile:** 26歳、徳島出身、大阪在住、ER / **Entry Route:** TikTok / **Difficulty:** Normal
**Scenario:** 徳島出身で大阪のER勤務。東京のERに興味があり、エリア選択で「東京都」を選択。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「東京都」を選択
4. Bot: 施設タイプ→病院→救急→常勤（三交代）
5. Bot: マッチング結果→東京の救急病院を提示
**System Behavior Evaluation:** 正常フロー。大阪在住だが東京希望のため問題なし。
**Results:** Drop-off: 低 / Job Proposal: 東京の救急病院 / Next Action: 詳細ヒアリング / Region Bias: なし / National Expansion Risk: なし
**Failure Category:** なし / **Severity:** None / **Fix Proposal:** なし / **Retry Needed:** No / **Auditor Comment:** 正常ケース。

---

### Case W7-045
- **Prefecture:** 広島県 / **Region Block:** 中国 / **Case Type:** Boundary / **User Profile:** 32歳、愛媛出身、広島在住 / **Entry Route:** Instagram / **Difficulty:** Medium
**Scenario:** 愛媛出身で広島勤務。広島での転職希望だが選択肢にない。「しまなみ海道で愛媛にも通えるけど...」
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「広島か愛媛で探してます」（テキスト入力）
4. Bot: エリア選択ボタン再表示
5. User: 「その他の地域」を選択
6. Bot: フロー進行→マッチング→関東施設提示
7. User: 離脱
**System Behavior Evaluation:** 広島・愛媛の両方が非対応。しまなみ海道通勤圏の概念はBotには存在しない。
**Results:** Drop-off: 確実 / Job Proposal: 不適切 / Next Action: 離脱 / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK / **Severity:** High / **Fix Proposal:** エリア外告知の早期化 / **Retry Needed:** Yes / **Auditor Comment:** 中国・四国間の通勤は現実にある。対応エリア拡大の参考情報。

---

### Case W7-046
- **Prefecture:** 広島県 / **Region Block:** 中国 / **Case Type:** Standard / **User Profile:** 40歳、高知出身、広島在住、管理職 / **Entry Route:** Google検索 / **Difficulty:** Normal
**Scenario:** 広島の病院で師長をしている。夫の東京転勤に伴い、神奈川の管理職ポジションを希望。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「神奈川県」を選択
4. Bot: 施設タイプ→病院→内科→常勤
5. Bot: マッチング結果→神奈川の病院を提示
**System Behavior Evaluation:** 正常フロー。管理職希望の情報は取得できないが、フロー自体は問題なし。
**Results:** Drop-off: 低 / Job Proposal: 神奈川の病院 / Next Action: 管理職ポジション確認→人間引き継ぎ / Region Bias: なし / National Expansion Risk: なし
**Failure Category:** JOB_MATCH_FAIL / **Severity:** Low / **Fix Proposal:** 役職・ポジション選択肢の追加 / **Retry Needed:** No / **Auditor Comment:** 管理職マッチングは人間対応で補完可能。

---

### Case W7-047
- **Prefecture:** 福岡県 / **Region Block:** 九州 / **Case Type:** Standard / **User Profile:** 27歳、高知出身、福岡在住 / **Entry Route:** TikTok / **Difficulty:** Normal
**Scenario:** 高知出身で福岡のクリニック勤務。福岡での転職を希望。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「その他の地域」を選択（福岡がリストにない）
4. Bot: 施設タイプ→クリニック→皮膚科→常勤
5. Bot: マッチング結果→関東のクリニック提示
6. User: 「福岡の求人が見たいです」
7. Bot: 応答なし
**System Behavior Evaluation:** 福岡は政令指定都市で看護師需要が高いが非対応。W7-043の大阪と同様の問題。
**Results:** Drop-off: 高 / Job Proposal: 不適切 / Next Action: 離脱 / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK / **Severity:** High / **Fix Proposal:** 福岡対応またはエリア外事前告知 / **Retry Needed:** Yes / **Auditor Comment:** 九州最大都市の非対応。

---

### Case W7-048
- **Prefecture:** 福岡県 / **Region Block:** 九州 / **Case Type:** Boundary / **User Profile:** 34歳、愛媛出身、福岡在住、子育て中 / **Entry Route:** LP / **Difficulty:** Medium
**Scenario:** 愛媛出身で福岡在住。子供の保育園があるため転居不可。パートで働きたい。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「その他の地域」を選択
4. Bot: 施設タイプ→クリニック→小児科→パート
5. Bot: マッチング結果→関東のクリニック提示
6. User: 「福岡で探してるんですけど...」
7. Bot: 応答なし
**System Behavior Evaluation:** 転居不可+非対応エリア。W7-007と同様のパターン。
**Results:** Drop-off: 確実 / Job Proposal: 不適切 / Next Action: 離脱 / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK / **Severity:** High / **Fix Proposal:** 転居不可+非対応エリアの早期検知と丁寧な離脱フロー / **Retry Needed:** Yes / **Auditor Comment:** 子育て中のパート看護師は全国にいる。対応エリアの限界を丁寧に伝えることが重要。

---

### Case W7-049
- **Prefecture:** 神奈川県 / **Region Block:** 関東 / **Case Type:** Standard / **User Profile:** 29歳、徳島出身、神奈川在住 / **Entry Route:** LP / **Difficulty:** Normal
**Scenario:** 徳島出身で横浜在住。神奈川での転職希望。Bot の本領発揮エリア。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「神奈川県」を選択
4. Bot: 施設タイプ→病院→整形外科→常勤（日勤のみ）
5. Bot: マッチング結果→神奈川の整形外科病院を提示（施設DB充実）
**System Behavior Evaluation:** 最も得意なエリア。施設DB212件のうち神奈川が豊富。マッチング精度が高い。
**Results:** Drop-off: 低 / Job Proposal: 神奈川の整形外科 / Next Action: 面談設定 / Region Bias: なし（ホームエリア） / National Expansion Risk: なし
**Failure Category:** なし / **Severity:** None / **Fix Proposal:** なし / **Retry Needed:** No / **Auditor Comment:** 最適ケース。四国出身者が神奈川に定住しているパターン。

---

### Case W7-050
- **Prefecture:** 神奈川県 / **Region Block:** 関東 / **Case Type:** Boundary / **User Profile:** 38歳、香川出身、神奈川在住、夜勤専従 / **Entry Route:** 友人紹介 / **Difficulty:** Medium
**Scenario:** 香川出身で川崎在住。夜勤専従で働いているが日勤に変えたい。条件変更の相談をしたい。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: ウェルカムメッセージ+エリア選択
3. User: 「神奈川県」を選択
4. Bot: 施設タイプ
5. User: 「病院」
6. Bot: 診療科
7. User: 「内科」
8. Bot: 勤務形態
9. User: 「常勤（日勤のみ）」
10. Bot: マッチング結果→神奈川の日勤内科病院を提示
**System Behavior Evaluation:** 正常フロー。夜勤専従→日勤のみという条件変更の背景はBotでは取得できないが、勤務形態選択で「日勤のみ」を選べば対応可能。
**Results:** Drop-off: 低 / Job Proposal: 神奈川の日勤内科 / Next Action: 夜勤専従からの転向理由ヒアリング / Region Bias: なし / National Expansion Risk: なし
**Failure Category:** なし / **Severity:** None / **Fix Proposal:** 転職理由入力ステップの追加が望ましい / **Retry Needed:** No / **Auditor Comment:** 条件変更（夜勤→日勤）は最も多い転職動機。正常動作。

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| Total Cases | 50 |
| Standard | 30 |
| Boundary | 12 |
| Adversarial | 8 |
| Severity: Critical | 8 |
| Severity: High | 14 |
| Severity: Medium | 10 |
| Severity: Low | 4 |
| Severity: None | 14 |
| GEO_LOCK | 22 |
| AMBIG_FAIL | 10 |
| JOB_MATCH_FAIL | 7 |
| HUMAN_HANDOFF_FAIL | 4 |
| UX_DROP | 3 |
| INPUT_LOCK | 3 |
| REENTRY_FAIL | 1 |
| REGION_EXPANSION_FAIL | 1 |
| OTHER | 1 |
| No Failure | 14 |
| Retry Needed: Yes | 18 |
| Retry Needed: No | 32 |

### Prefecture Distribution
| Prefecture | Cases |
|-----------|-------|
| 徳島県 | 9 |
| 香川県 | 9 |
| 愛媛県 | 9 |
| 高知県 | 9 |
| Spare (徳島/香川/愛媛/高知) | 4 |
| 東京都 | 2 |
| 大阪府 | 2 |
| 広島県 | 2 |
| 福岡県 | 2 |
| 神奈川県 | 2 |

### Key Findings for 四国 Region
1. **GEO_LOCK dominates**: 22/50 cases hit the geographic limitation. 四国 has 0 facilities in DB, making every local-seeking user a guaranteed failure.
2. **"その他の地域" is a trap**: Users expecting local results get Kanto facilities with no warning. This is the single biggest UX failure.
3. **大阪 non-support is critical for 四国**: Many Shikoku nurses consider 大阪 their nearest major city. Not having 大阪 in the selection list forces them into "その他" → Kanto mismatch.
4. **SOS/emotional messages get ignored**: The bot's rigid selection-based flow cannot handle distressed users (W7-021, W7-008).
5. **Text input is a dead end**: Every free-text message results in button re-display, regardless of content or urgency.
6. **Successful cases require Kanto intent**: Only users who already plan to relocate to 東京/神奈川/千葉/埼玉 have a positive experience.
