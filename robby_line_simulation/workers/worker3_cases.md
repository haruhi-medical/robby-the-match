# Worker 3: 甲信越・北陸 テストケース（50件）

> 担当地域: 新潟(6), 富山(6), 石川(6), 福井(6), 山梨(6), 長野(6), 予備(4)
> クロステスト: 東京(2), 神奈川(2), 愛知(2), 大阪(2), 福岡(2)
> 内訳: 標準30件 / 境界12件 / 攻撃的8件
> 重要: 主担当6県は全てDB未登録（施設0件）。全ケースで「その他の地域」→関東施設表示の問題が発生する。

---

## 新潟県（6件）

### Case W3-001
- **Prefecture:** 新潟県 / **Region Block:** 甲信越 / **Case Type:** 標準 / **User Profile:** 32歳、急性期病棟5年目、常勤 / **Entry Route:** Google検索→LP→LINE / **Difficulty:** 標準
**Scenario:**
新潟市内の総合病院で働く看護師。夜勤がきつくなり日勤のみの職場を探している。LPから友だち追加。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: 「○○件の医療機関の中から...」Welcome表示
3. Bot: il_area表示（東京都/神奈川県/千葉県/埼玉県/その他の地域）
4. User: 「その他の地域」を選択（新潟がないため）
5. Bot: il_facility_type表示（エリア未確定のまま進行）
6. User: 「急性期」を選択
7. Bot: il_department表示
8. User: 「内科」を選択
9. Bot: il_workstyle表示
10. User: 「日勤のみ」を選択
11. Bot: il_urgency表示
12. User: 「良い所あれば」を選択
13. Bot: matching_preview → 関東の施設5件を表示
14. User: 「新潟の求人はないんですか？」（困惑）
**System Behavior Evaluation:**
- 「その他の地域」選択後、エリアが「undecided」になるが、ユーザーに新潟が対象外であることの明示がない
- matching_previewで関東施設が表示されるのは新潟在住者にとって完全にミスマッチ
- ユーザーの「新潟の求人はないんですか？」に対するBot応答が未定義（フリーテキスト未解析）
**Results:** Drop-off: 高確率で離脱 / Job Proposal: 地域ミスマッチ / Next Action: 人間引き継ぎ必要だが自動では発火しない / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK / **Severity:** Critical / **Fix Proposal:** 「その他の地域」選択時に「現在、神奈川県を中心に関東エリアの求人をご紹介しています。対象エリア拡大時にお知らせしますか？」と明示 / **Retry Needed:** Yes / **Auditor Comment:** 最も基本的なGEO_LOCKパターン。新潟在住者が関東施設を見せられる体験は致命的。

---

### Case W3-002
- **Prefecture:** 新潟県 / **Region Block:** 甲信越 / **Case Type:** 標準 / **User Profile:** 45歳、訪問看護10年、パート希望 / **Entry Route:** Instagram広告→LINE / **Difficulty:** 標準
**Scenario:**
長岡市で訪問看護をしている。子どもが高校受験で時間の融通が利くパート勤務に変えたい。地元で探したい。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「その他の地域」を選択
5. Bot: il_facility_type表示
6. User: 「訪問看護」を選択
7. Bot: il_workstyle表示（訪問看護は病院ではないのでdepartmentスキップ）
8. User: 「パート・非常勤」を選択
9. Bot: il_urgency表示
10. User: 「良い所あれば」を選択
11. Bot: matching_preview → 関東の訪問看護ステーション5件表示
12. User: 無反応のまま離脱
**System Behavior Evaluation:**
- 訪問看護→パートという具体的な希望があるのに地域がマッチしない
- 訪問看護は地域密着型サービスなので、関東の提案は特に不適切
- 離脱後のフォローメッセージの有無が不明
**Results:** Drop-off: サイレント離脱 / Job Proposal: 地域ミスマッチ / Next Action: フォローなし / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK / **Severity:** High / **Fix Proposal:** 訪問看護は通勤圏が狭いため、エリア外の場合は「お住まいの地域では現在求人をお取り扱いしていません」と即時通知すべき / **Retry Needed:** Yes / **Auditor Comment:** 訪問看護のGEO_LOCKは通勤不可能という物理的制約があり、他業態より深刻。

---

### Case W3-003
- **Prefecture:** 新潟県 / **Region Block:** 甲信越 / **Case Type:** 境界 / **User Profile:** 24歳、新卒2年目、東京への転居検討中 / **Entry Route:** TikTok→プロフィールリンク→LINE / **Difficulty:** 中
**Scenario:**
新潟の地方病院勤務。東京に出たいと思っているが迷い中。TikTokで「シン・AI転職」を見て興味を持った。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「東京都」を選択（転居希望あり）
5. Bot: il_subarea表示（東京のサブエリア）
6. User: サブエリアを選択
7. Bot: il_facility_type表示
8. User: 「急性期」を選択
9. Bot: il_department表示
10. User: 「外科」を選択
11. Bot: il_workstyle表示
12. User: 「夜勤ありOK」を選択
13. Bot: il_urgency表示
14. User: 「良い所あれば」を選択
15. Bot: matching_preview → 東京の急性期病院5件表示
**System Behavior Evaluation:**
- 転居前提であれば正常フロー。東京の施設が表示され問題なし
- ただし「新潟から東京」という転居サポートの情報提供がない
- 引越し費用・寮の有無などの追加情報が欲しい場面
**Results:** Drop-off: 低 / Job Proposal: マッチ / Next Action: 転居サポート情報の追加提供が望ましい / Region Bias: なし（東京選択のため） / National Expansion Risk: なし
**Failure Category:** なし（正常フロー） / **Severity:** Low / **Fix Proposal:** 転居を伴う転職の場合、寮・引越し支援の有無をマッチング条件に追加 / **Retry Needed:** No / **Auditor Comment:** GEO_LOCK回避パターン。地方→東京の転居希望者はBotが正常に機能する唯一のケース。

---

### Case W3-004
- **Prefecture:** 新潟県 / **Region Block:** 甲信越 / **Case Type:** 攻撃的 / **User Profile:** 38歳、ICU7年、条件厳しい / **Entry Route:** LP→LINE / **Difficulty:** 高
**Scenario:**
新潟市のICU看護師。給与500万以上、日勤のみ、新潟市内、ICU経験活かせる職場。条件が非常に具体的だが全てエリア外。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「その他の地域」を選択
5. Bot: il_facility_type表示
6. User: 「急性期」を選択
7. Bot: il_department表示
8. User: 「ICU」と自由入力（選択肢にない場合）
9. Bot: 自由入力を解析できず無応答 or デフォルト処理
10. User: 「ICUで働きたいです」再度入力
11. Bot: 同上
12. User: 怒りの離脱
**System Behavior Evaluation:**
- il_departmentの選択肢にICUがあるか不明。なければフリーテキスト入力を解析できない
- 「その他の地域」+「ICU」という二重の未対応パターン
- ユーザーの専門性が高いほど、BOTの対応力不足が際立つ
**Results:** Drop-off: 高確率で怒りの離脱 / Job Proposal: 不可 / Next Action: 人間引き継ぎすべきだが発動しない / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + INPUT_LOCK / **Severity:** Critical / **Fix Proposal:** (1) ICUを診療科選択肢に追加 (2) エリア外+専門職種の組み合わせは即時人間引き継ぎ / **Retry Needed:** Yes / **Auditor Comment:** 高スキル人材ほど失望が大きい。ICU経験者は紹介手数料も高くなるため、機会損失も大きい。

---

### Case W3-005
- **Prefecture:** 新潟県 / **Region Block:** 甲信越 / **Case Type:** 境界 / **User Profile:** 50歳、准看護師、ブランク3年 / **Entry Route:** 知人紹介→LINE / **Difficulty:** 中
**Scenario:**
新潟県上越市在住。介護施設で准看護師として働いていたが腰を痛めて3年ブランク。復帰したいが不安。知人から紹介されてLINE追加。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「その他の地域」を選択
5. Bot: il_facility_type表示
6. User: 「介護施設」を選択
7. Bot: il_workstyle表示
8. User: 「パート・非常勤」を選択
9. Bot: il_urgency表示
10. User: 「まだ情報収集」を選択
11. Bot: matching_preview → 関東の介護施設5件表示
12. User: 「上越市で探してるんですけど...准看でブランクありでも大丈夫ですか？」
13. Bot: フリーテキスト未解析、定型応答
**System Behavior Evaluation:**
- 准看護師・ブランクありという重要属性をヒアリングする工程がない
- 知人紹介からの流入は信頼度が高いのに、BOTの対応で信頼を損なう
- 「まだ情報収集」を選んだ温度感の低いユーザーに関東施設を見せるのは逆効果
**Results:** Drop-off: 高 / Job Proposal: 地域ミスマッチ / Next Action: 准看・ブランクの相談対応が必要 / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + AMBIG_FAIL / **Severity:** High / **Fix Proposal:** (1) 准看護師/ブランクのヒアリング項目追加 (2) 「まだ情報収集」+エリア外は求人表示せず情報提供モードに切替 / **Retry Needed:** Yes / **Auditor Comment:** 復帰不安を抱えるユーザーにミスマッチ求人を出すのは精神的にも悪影響。

---

### Case W3-006
- **Prefecture:** 新潟県 / **Region Block:** 甲信越 / **Case Type:** 標準 / **User Profile:** 29歳、オペ室3年、常勤 / **Entry Route:** Google検索「新潟 看護師 転職」→LP→LINE / **Difficulty:** 標準
**Scenario:**
新潟市の大学病院オペ室勤務。人間関係のストレスで転職を考えている。Google検索で「神奈川ナース転職」のLPにたどり着いたが、神奈川と気づかずLINE追加。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 選択肢を見て「新潟がない...」と気づく
5. User: 「新潟県の求人はありますか？」とフリーテキスト入力
6. Bot: フリーテキスト未解析、il_area選択を再促進
7. User: 仕方なく「その他の地域」を選択
8. Bot: il_facility_type表示
9. User: ここで離脱（神奈川のサービスだと理解して去る）
**System Behavior Evaluation:**
- SEO流入で地域ミスマッチが発生する典型パターン
- 「新潟県の求人はありますか？」にBotが答えられない
- LP時点で「神奈川県を中心とした関東エリア限定」と明示すべき
**Results:** Drop-off: il_area段階で離脱 / Job Proposal: なし / Next Action: なし / Region Bias: LP/SEOで全国からの流入を誘引している / National Expansion Risk: Critical
**Failure Category:** GEO_LOCK + REGION_EXPANSION_FAIL / **Severity:** Critical / **Fix Proposal:** (1) LP/SEOで対象エリアを明示 (2) il_area段階でフリーテキスト「新潟」→「現在新潟県は対象外です」と即応答 (3) メタディスクリプションに「神奈川・関東」を明記 / **Retry Needed:** Yes / **Auditor Comment:** SEO流入からの期待外れは最も印象が悪い。LPでの地域明示が根本解決。

---

## 富山県（6件）

### Case W3-007
- **Prefecture:** 富山県 / **Region Block:** 北陸 / **Case Type:** 標準 / **User Profile:** 35歳、回復期リハ病棟4年、常勤 / **Entry Route:** Instagram広告→LINE / **Difficulty:** 標準
**Scenario:**
富山市の回復期リハビリテーション病棟勤務。リハビリ看護が好きだが給与に不満。Instagram広告の「手数料10%」に惹かれてLINE追加。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「その他の地域」を選択
5. Bot: il_facility_type表示
6. User: 「回復期」を選択
7. Bot: il_workstyle表示
8. User: 「日勤のみ」を選択
9. Bot: il_urgency表示
10. User: 「すぐ転職したい」を選択
11. Bot: matching_preview → 関東の回復期病院5件表示
12. User: 「富山県内で探しています」とテキスト入力
13. Bot: フリーテキスト未解析
14. User: 離脱
**System Behavior Evaluation:**
- 「すぐ転職したい」という高温度ユーザーに地域ミスマッチが発生
- 緊急度が高いほど離脱後に競合サービスへ流れる可能性大
- Instagram広告で全国配信している場合、この問題は大量発生する
**Results:** Drop-off: 高温度ユーザーの離脱（最悪パターン） / Job Proposal: 地域ミスマッチ / Next Action: なし / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK / **Severity:** Critical / **Fix Proposal:** (1) 広告配信を関東エリアに限定 (2) 「すぐ転職したい」+エリア外は即時人間引き継ぎ / **Retry Needed:** Yes / **Auditor Comment:** 広告費を使って非対象エリアのユーザーを集めるのはCPA悪化の直接原因。

---

### Case W3-008
- **Prefecture:** 富山県 / **Region Block:** 北陸 / **Case Type:** 標準 / **User Profile:** 27歳、クリニック外来2年、常勤 / **Entry Route:** TikTok→LINE / **Difficulty:** 標準
**Scenario:**
高岡市の内科クリニック勤務。院長のパワハラに悩み、別のクリニックに移りたい。TikTokの「看護師あるある」動画からLINE追加。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「その他の地域」を選択
5. Bot: il_facility_type表示
6. User: 「クリニック」を選択
7. Bot: il_workstyle表示
8. User: 「日勤のみ」を選択
9. Bot: il_urgency表示
10. User: 「すぐ転職したい」を選択
11. Bot: matching_preview → 関東のクリニック5件表示
12. User: 「富山なんですけど...」
13. Bot: 応答なし or 定型文
14. User: LINEブロック
**System Behavior Evaluation:**
- クリニック勤務者は地元密着型転職が多い
- パワハラ相談要素があるが、BOTにはハラスメント対応フローがない
- ブロックされると再接触不可
**Results:** Drop-off: ブロック離脱 / Job Proposal: 地域ミスマッチ / Next Action: 不可（ブロック済み） / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK / **Severity:** High / **Fix Proposal:** ブロック前にエリア外通知+「対象エリア拡大時の通知希望」を聞く / **Retry Needed:** Yes / **Auditor Comment:** ブロックは不可逆。エリア外と分かった時点で誠実に伝える方がブランド毀損を防げる。

---

### Case W3-009
- **Prefecture:** 富山県 / **Region Block:** 北陸 / **Case Type:** 境界 / **User Profile:** 40歳、夜勤専従、単身赴任OK / **Entry Route:** LP→LINE / **Difficulty:** 中
**Scenario:**
富山在住だが単身赴任で関東勤務も検討中。夜勤専従で高収入を狙いたい。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「神奈川県」を選択（関東勤務検討中のため）
5. Bot: il_subarea表示
6. User: サブエリアを選択
7. Bot: il_facility_type表示
8. User: 「急性期」を選択
9. Bot: il_department表示
10. User: 「内科」を選択
11. Bot: il_workstyle表示
12. User: 「夜勤専従」を選択
13. Bot: il_urgency表示
14. User: 「良い所あれば」を選択
15. Bot: matching_preview → 神奈川の急性期病院5件表示
**System Behavior Evaluation:**
- 正常フロー。神奈川を選択したので施設表示は適切
- ただし「富山から単身赴任」という背景情報のヒアリングがない
- 寮・社宅の有無がマッチング条件に含まれていない
**Results:** Drop-off: 低 / Job Proposal: マッチ / Next Action: 寮・引越し支援の情報提供 / Region Bias: なし / National Expansion Risk: なし
**Failure Category:** なし（正常フロー） / **Severity:** Low / **Fix Proposal:** 遠方からの転居を伴う場合の追加ヒアリング項目（寮・引越し・赴任手当） / **Retry Needed:** No / **Auditor Comment:** 単身赴任希望者はBotで正常処理可能だが、転居サポート情報の付加価値がない。

---

### Case W3-010
- **Prefecture:** 富山県 / **Region Block:** 北陸 / **Case Type:** 攻撃的 / **User Profile:** 31歳、産科3年 / **Entry Route:** LINE / **Difficulty:** 高
**Scenario:**
「富山県射水市」と最初から地名をフリーテキストで送信。選択式UIを無視して自然言語で会話しようとする。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「富山県射水市で産科の求人ありますか？」（フリーテキスト）
5. Bot: il_area選択を再表示 or 無応答
6. User: 「選択肢に富山がないんですけど」
7. Bot: 同上
8. User: 「使えないな...」離脱
**System Behavior Evaluation:**
- intake中のフリーテキストを完全に無視する設計
- ユーザーの自然な会話行動に全く対応できない
- 「選択肢に富山がない」という明確なフィードバックにも応答不能
**Results:** Drop-off: 即時離脱 / Job Proposal: なし / Next Action: なし / Region Bias: N/A / National Expansion Risk: 高
**Failure Category:** INPUT_LOCK + GEO_LOCK / **Severity:** Critical / **Fix Proposal:** (1) intake中のフリーテキストからキーワード抽出（都道府県名・施設種別） (2) 対象外エリアのキーワード検出時は即「現在○○県は対象外です」と応答 / **Retry Needed:** Yes / **Auditor Comment:** LINEはチャットUIなので、ユーザーがフリーテキストを打つのは自然な行動。これを無視するのはUXとして致命的。

---

### Case W3-011
- **Prefecture:** 富山県 / **Region Block:** 北陸 / **Case Type:** 境界 / **User Profile:** 22歳、新卒、内定辞退後 / **Entry Route:** 友人のLINE転送→LINE / **Difficulty:** 中
**Scenario:**
富山の看護学校を卒業したばかり。内定を辞退して行き先がない。友人が「このLINE使ってみて」と転送してきた。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. User: 「内定辞退してしまって、すぐ働けるところを探しています。富山です。」（Welcome直後にフリーテキスト）
4. Bot: il_area表示（フリーテキスト無視）
5. User: 「その他の地域」を選択
6. Bot: il_facility_type表示
7. User: 「こだわりなし」を選択
8. Bot: il_workstyle表示
9. User: 「日勤のみ」を選択
10. Bot: il_urgency表示
11. User: 「すぐ転職したい」を選択
12. Bot: matching_preview → 関東施設5件表示
13. User: 「富山で...」離脱
**System Behavior Evaluation:**
- 緊急性の高いケースだがエリア外で救済不可
- 新卒・内定辞退という特殊事情に対応するフローがない
- 最初のフリーテキストで「富山」「すぐ」というキーワードが取れているのに活用されない
**Results:** Drop-off: matching_preview段階で離脱 / Job Proposal: 地域ミスマッチ / Next Action: 緊急案件として人間引き継ぎすべき / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + HUMAN_HANDOFF_FAIL / **Severity:** Critical / **Fix Proposal:** (1) 「すぐ転職したい」+エリア外は即時Slack通知で人間引き継ぎ (2) フリーテキストの地域名検出 / **Retry Needed:** Yes / **Auditor Comment:** 新卒で内定辞退は深刻な状況。機械的な対応は信頼を完全に失う。

---

### Case W3-012
- **Prefecture:** 富山県 / **Region Block:** 北陸 / **Case Type:** 標準 / **User Profile:** 55歳、慢性期15年、定年前 / **Entry Route:** LP→LINE / **Difficulty:** 標準
**Scenario:**
富山県魚津市の療養型病院で15年勤務。定年後も働けるパート勤務を探している。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「その他の地域」を選択
5. Bot: il_facility_type表示
6. User: 「慢性期」を選択
7. Bot: il_workstyle表示
8. User: 「パート・非常勤」を選択
9. Bot: il_urgency表示
10. User: 「まだ情報収集」を選択
11. Bot: matching_preview → 関東の慢性期病院5件表示
12. User: 静かに離脱
**System Behavior Evaluation:**
- 定年前のベテランは地元での転職希望が強い
- 「まだ情報収集」段階で関東施設を出すのは完全にミスマッチ
- 55歳のユーザーはLINE操作自体に不慣れな可能性もある
**Results:** Drop-off: サイレント離脱 / Job Proposal: 地域ミスマッチ / Next Action: なし / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK / **Severity:** High / **Fix Proposal:** 「まだ情報収集」+エリア外の場合は求人表示せず転職コラム等の情報提供に切替 / **Retry Needed:** Yes / **Auditor Comment:** シニア層のサイレント離脱は計測しづらいが、口コミでの悪影響が大きい。

---

## 石川県（6件）

### Case W3-013
- **Prefecture:** 石川県 / **Region Block:** 北陸 / **Case Type:** 標準 / **User Profile:** 30歳、救急外来4年、常勤 / **Entry Route:** Google検索→LP→LINE / **Difficulty:** 標準
**Scenario:**
金沢市の救急病院勤務。燃え尽き気味で環境を変えたい。「看護師 転職 AI」で検索してLPにたどり着いた。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「その他の地域」を選択
5. Bot: il_facility_type表示
6. User: 「急性期」を選択
7. Bot: il_department表示
8. User: 「救急」を選択
9. Bot: il_workstyle表示
10. User: 「日勤のみ」を選択（夜勤から逃げたい）
11. Bot: il_urgency表示
12. User: 「良い所あれば」を選択
13. Bot: matching_preview → 関東の急性期病院5件表示
14. User: 「金沢の求人は...」離脱
**System Behavior Evaluation:**
- 救急→日勤のみという条件変更を伴う転職希望
- 「AI転職」キーワードで流入しているのでAI対応への期待値が高い
- 期待値が高い分、エリア外だったときの失望も大きい
**Results:** Drop-off: matching_preview段階で離脱 / Job Proposal: 地域ミスマッチ / Next Action: なし / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK / **Severity:** High / **Fix Proposal:** 「AI転職」を謳うならエリア制限を事前に明示すべき。AIへの期待値との乖離が大きい / **Retry Needed:** Yes / **Auditor Comment:** ブランドメッセージ「シン・AI転職」が全国対応を連想させるのが問題の根本。

---

### Case W3-014
- **Prefecture:** 石川県 / **Region Block:** 北陸 / **Case Type:** 境界 / **User Profile:** 33歳、NICUナース、夫の転勤で神奈川へ / **Entry Route:** LP→LINE / **Difficulty:** 中
**Scenario:**
金沢市でNICU勤務中。夫が横浜に転勤が決まり、3ヶ月後に引っ越し予定。神奈川で同じNICUの仕事を探したい。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「神奈川県」を選択
5. Bot: il_subarea表示
6. User: 「横浜」を選択
7. Bot: il_facility_type表示
8. User: 「急性期」を選択
9. Bot: il_department表示
10. User: 「小児科」を選択（NICUに最も近い）
11. Bot: il_workstyle表示
12. User: 「夜勤ありOK」を選択
13. Bot: il_urgency表示
14. User: 「良い所あれば」を選択
15. Bot: matching_preview → 横浜の急性期病院5件表示
**System Behavior Evaluation:**
- 正常フロー。転勤帯同で神奈川に来るケースはターゲットど真ん中
- NICUという専門分野が選択肢にないため「小児科」で代替
- 3ヶ月後という時間軸の情報をヒアリングできていない
**Results:** Drop-off: 低 / Job Proposal: マッチ（NICUの精度は不十分） / Next Action: NICU経験の詳細ヒアリングを人間が実施 / Region Bias: なし / National Expansion Risk: なし
**Failure Category:** JOB_MATCH_FAIL（軽微） / **Severity:** Low / **Fix Proposal:** NICUを診療科選択肢に追加 or 専門分野のフリーテキスト入力欄を設ける / **Retry Needed:** No / **Auditor Comment:** 転勤帯同者はBotの正常フロー。NICU→小児科の代替は許容範囲だが精度向上の余地あり。

---

### Case W3-015
- **Prefecture:** 石川県 / **Region Block:** 北陸 / **Case Type:** 攻撃的 / **User Profile:** 28歳、精神科3年 / **Entry Route:** LINE / **Difficulty:** 高
**Scenario:**
能登半島の精神科病院勤務。2024年の能登半島地震の影響でメンタルが厳しい。「どこでもいいから逃げたい」という切迫した状態。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. User: 「能登で被災してもう限界です。どこでもいいので紹介してください」（フリーテキスト）
4. Bot: il_area表示（フリーテキスト無視）
5. User: 「その他の地域」を選択
6. Bot: il_facility_type表示
7. User: 「こだわりなし」を選択
8. Bot: il_workstyle表示
9. User: 「こだわりなし」と入力（選択肢をタップしない）
10. Bot: il_workstyle再表示
11. User: 「日勤のみ」を選択
12. Bot: il_urgency表示
13. User: 「すぐ転職したい」を選択
14. Bot: matching_preview → 関東の施設5件表示
15. User: 「...関東ですか。行きます。」
**System Behavior Evaluation:**
- メンタル危機のユーザーに対する配慮がゼロ
- 「限界」「逃げたい」というキーワードを検出して人間に引き継ぐべき
- 被災者支援の観点からも、機械的な対応は不適切
- ただし「どこでもいいから」は関東でもマッチする可能性あり
**Results:** Drop-off: 意外と低い（切迫しているので関東でもOKの可能性） / Job Proposal: 条件は曖昧だがマッチ可能 / Next Action: 即時人間引き継ぎ必須 / Region Bias: 結果的に関東で進む可能性 / National Expansion Risk: N/A
**Failure Category:** HUMAN_HANDOFF_FAIL / **Severity:** Critical / **Fix Proposal:** (1) 「限界」「逃げたい」「被災」等のキーワード検出で即人間引き継ぎ (2) メンタルヘルス相談窓口の案内を自動表示 / **Retry Needed:** Yes / **Auditor Comment:** 人命に関わる可能性。BOTで対応してはいけないケース。

---

### Case W3-016
- **Prefecture:** 石川県 / **Region Block:** 北陸 / **Case Type:** 標準 / **User Profile:** 42歳、管理職（師長）、キャリアダウン希望 / **Entry Route:** LP→LINE / **Difficulty:** 標準
**Scenario:**
金沢市の中規模病院の看護師長。管理業務に疲れ、現場に戻りたい。管理職経験を活かせるがプレッシャーのない職場を希望。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「その他の地域」を選択
5. Bot: il_facility_type表示
6. User: 「回復期」を選択
7. Bot: il_workstyle表示
8. User: 「日勤のみ」を選択
9. Bot: il_urgency表示
10. User: 「良い所あれば」を選択
11. Bot: matching_preview → 関東の回復期病院5件表示
12. User: 離脱
**System Behavior Evaluation:**
- 管理職→現場復帰という特殊なキャリアチェンジ希望を拾えない
- 役職・経験年数のヒアリングがない
- 師長経験者は求人側にとっても価値が高い
**Results:** Drop-off: 高 / Job Proposal: 地域ミスマッチ / Next Action: なし / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK / **Severity:** High / **Fix Proposal:** 管理職経験のヒアリング項目追加。高価値人材の取りこぼし防止 / **Retry Needed:** Yes / **Auditor Comment:** 師長経験者の紹介手数料は高額。機会損失が大きい。

---

### Case W3-017
- **Prefecture:** 石川県 / **Region Block:** 北陸 / **Case Type:** 境界 / **User Profile:** 26歳、一般病棟2年目 / **Entry Route:** LINE / **Difficulty:** 中
**Scenario:**
加賀市在住。LINEで友だち追加後、数日放置してから操作を始める。途中で止まり、翌日また続きから再開しようとする。
**Conversation Flow:**
1. User: LINE友だち追加（Day 1）
2. Bot: Welcome表示
3. （3日間放置）
4. User: トーク画面を開く（Day 4）
5. Bot: il_area表示（前回の続き？リセット？）
6. User: 「その他の地域」を選択
7. Bot: il_facility_type表示
8. User: 「急性期」を選択
9. （翌日）
10. User: トーク画面を再度開く（Day 5）
11. Bot: il_department表示が出る？ or リセット？
12. User: 混乱して離脱
**System Behavior Evaluation:**
- セッション管理のタイムアウト挙動が不明
- 数日空いた場合に途中から再開できるのか、リセットされるのか
- リセットされる場合、ユーザーに説明があるか
**Results:** Drop-off: セッション不整合で離脱の可能性 / Job Proposal: N/A / Next Action: N/A / Region Bias: N/A / National Expansion Risk: N/A
**Failure Category:** REENTRY_FAIL / **Severity:** Medium / **Fix Proposal:** (1) 24時間以上放置されたセッションは「前回の続きから再開しますか？」と確認 (2) localStorage 24h有効の仕様をLINE Bot側にも適用 / **Retry Needed:** Yes / **Auditor Comment:** GEO_LOCK以前にセッション管理の問題。北陸に限らず全国で発生しうる。

---

### Case W3-018
- **Prefecture:** 石川県 / **Region Block:** 北陸 / **Case Type:** 攻撃的 / **User Profile:** 34歳 / **Entry Route:** LINE / **Difficulty:** 高
**Scenario:**
LINEスタンプだけを連続で送信する。テキストも選択もせず、スタンプのみ。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: スタンプ送信（にっこり）
5. Bot: il_area再表示？ or 無応答？
6. User: スタンプ送信（OK）
7. Bot: 同上
8. User: スタンプ送信（ハート）
9. Bot: 同上
10. User: 飽きて離脱
**System Behavior Evaluation:**
- スタンプ入力に対するハンドリングが未定義
- 「スタンプではお答えできません。下のボタンからお選びください」等の案内がない
- LINEではスタンプコミュニケーションが一般的なので、この入力は想定すべき
**Results:** Drop-off: 即時 / Job Proposal: なし / Next Action: なし / Region Bias: N/A / National Expansion Risk: N/A
**Failure Category:** INPUT_LOCK / **Severity:** Medium / **Fix Proposal:** スタンプ受信時に「ありがとうございます！下のボタンからお住まいの地域をお選びください」と案内 / **Retry Needed:** Yes / **Auditor Comment:** 石川県固有の問題ではないが、LINEの基本的なUXとして対応必須。

---

## 福井県（6件）

### Case W3-019
- **Prefecture:** 福井県 / **Region Block:** 北陸 / **Case Type:** 標準 / **User Profile:** 36歳、透析クリニック5年、常勤 / **Entry Route:** Google検索→LP→LINE / **Difficulty:** 標準
**Scenario:**
福井市の透析クリニック勤務。透析看護の専門性を活かして別の透析施設に移りたい。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「その他の地域」を選択
5. Bot: il_facility_type表示
6. User: 「クリニック」を選択
7. Bot: il_workstyle表示
8. User: 「日勤のみ」を選択
9. Bot: il_urgency表示
10. User: 「良い所あれば」を選択
11. Bot: matching_preview → 関東のクリニック5件表示
12. User: 「透析のクリニックはありますか？」
13. Bot: フリーテキスト未解析
14. User: 離脱
**System Behavior Evaluation:**
- 透析という専門分野を選択肢で表現できない
- クリニック内の専門分化（透析/美容/皮膚科等）を区別するフローがない
- エリア外+専門分野ミスマッチの二重問題
**Results:** Drop-off: 高 / Job Proposal: 地域ミスマッチ+専門ミスマッチ / Next Action: なし / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + JOB_MATCH_FAIL / **Severity:** High / **Fix Proposal:** クリニックの専門分野（透析/美容/在宅等）をサブ選択肢として追加 / **Retry Needed:** Yes / **Auditor Comment:** 透析看護師は専門性が高く転職市場での価値も高い。拾えないのは損失。

---

### Case W3-020
- **Prefecture:** 福井県 / **Region Block:** 北陸 / **Case Type:** 標準 / **User Profile:** 48歳、介護施設8年、パート / **Entry Route:** Instagram→LINE / **Difficulty:** 標準
**Scenario:**
敦賀市の特養で働くパート看護師。同市内で別の介護施設に移りたい。通勤30分以内が絶対条件。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「その他の地域」を選択
5. Bot: il_facility_type表示
6. User: 「介護施設」を選択
7. Bot: il_workstyle表示
8. User: 「パート・非常勤」を選択
9. Bot: il_urgency表示
10. User: 「良い所あれば」を選択
11. Bot: matching_preview → 関東の介護施設5件表示
12. User: 離脱（敦賀から関東は通えない）
**System Behavior Evaluation:**
- 「通勤30分以内」という条件をヒアリングするフローがない
- 介護施設+パートは地域密着度が最も高いカテゴリ
- 敦賀市のような小都市では選択肢が限られるため、エリア外はより致命的
**Results:** Drop-off: 即時離脱 / Job Proposal: 地域ミスマッチ / Next Action: なし / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK / **Severity:** High / **Fix Proposal:** 通勤時間/距離の条件ヒアリングを追加 / **Retry Needed:** Yes / **Auditor Comment:** 介護施設パートは最も地域密着。関東提案は完全にナンセンス。

---

### Case W3-021
- **Prefecture:** 福井県 / **Region Block:** 北陸 / **Case Type:** 境界 / **User Profile:** 25歳、病棟1年目、第二新卒 / **Entry Route:** TikTok→LINE / **Difficulty:** 中
**Scenario:**
福井市の急性期病棟に配属されたが、想像と違い3ヶ月で辞めたい。「第二新卒 看護師」で情報を探していてTikTokからLINE追加。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. User: 「3ヶ月で辞めたいんですけど大丈夫ですか？」（フリーテキスト）
4. Bot: il_area表示（フリーテキスト無視）
5. User: 「その他の地域」を選択
6. Bot: il_facility_type表示
7. User: 「こだわりなし」を選択
8. Bot: il_workstyle表示
9. User: 「日勤のみ」を選択
10. Bot: il_urgency表示
11. User: 「すぐ転職したい」を選択
12. Bot: matching_preview → 関東施設5件表示
13. User: 「福井で探してます...」離脱
**System Behavior Evaluation:**
- 「3ヶ月で辞めたい」という不安・相談をBotが拾えない
- 第二新卒特有の不安に対するケアがない
- 経験1年未満は紹介先が限られるため、早期に人間が対応すべき
**Results:** Drop-off: 高 / Job Proposal: 地域ミスマッチ / Next Action: 第二新卒相談として人間引き継ぎ / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + HUMAN_HANDOFF_FAIL / **Severity:** High / **Fix Proposal:** (1) 「辞めたい」「不安」等のキーワードで相談モード切替 (2) 経験1年未満は早期人間引き継ぎ / **Retry Needed:** Yes / **Auditor Comment:** 第二新卒は離職理由のケアが最重要。Botの機械的対応は不適切。

---

### Case W3-022
- **Prefecture:** 福井県 / **Region Block:** 北陸 / **Case Type:** 攻撃的 / **User Profile:** 39歳 / **Entry Route:** LINE / **Difficulty:** 高
**Scenario:**
同じ質問を繰り返し送信するユーザー。「福井の求人ある？」を5回連続で送る。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「福井の求人ある？」
5. Bot: il_area再表示
6. User: 「福井の求人ある？」
7. Bot: il_area再表示
8. User: 「福井の求人ある？」
9. Bot: il_area再表示
10. User: 「福井の求人ある？」
11. Bot: il_area再表示
12. User: 「福井の求人ある？」→ 離脱 or 暴言
**System Behavior Evaluation:**
- 同一フリーテキストの繰り返しに対する処理がない
- 3回以上同じ内容が来た場合のエスカレーション機能がない
- ユーザーのフラストレーションが蓄積していく一方
**Results:** Drop-off: 確実に離脱 / Job Proposal: なし / Next Action: なし / Region Bias: N/A / National Expansion Risk: 高
**Failure Category:** INPUT_LOCK + GEO_LOCK / **Severity:** High / **Fix Proposal:** (1) 同一テキスト3回以上で「申し訳ございません。現在福井県は対象エリア外です。スタッフにお繋ぎしますか？」と人間引き継ぎ提案 (2) フリーテキスト中の都道府県名検出 / **Retry Needed:** Yes / **Auditor Comment:** ループ検出→エスカレーションは基本的なBOT設計。未実装は問題。

---

### Case W3-023
- **Prefecture:** 福井県 / **Region Block:** 北陸 / **Case Type:** 境界 / **User Profile:** 44歳、訪問看護管理者、起業検討中 / **Entry Route:** LP→LINE / **Difficulty:** 中
**Scenario:**
福井県越前市で訪問看護ステーション管理者。自分で訪問看護ステーションを開業するか、別の職場に転職するか迷っている。情報収集目的。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「その他の地域」を選択
5. Bot: il_facility_type表示
6. User: 「訪問看護」を選択
7. Bot: il_workstyle表示
8. User: 「日勤のみ」を選択
9. Bot: il_urgency表示
10. User: 「まだ情報収集」を選択
11. Bot: matching_preview → 関東の訪問看護5件表示
12. User: 「開業相談とかはできますか？」
13. Bot: フリーテキスト未解析
14. User: 離脱
**System Behavior Evaluation:**
- 転職以外のニーズ（開業相談）に対応できない
- 管理者クラスの人材は紹介価値が非常に高い
- 「まだ情報収集」は開業検討中の可能性を考慮すべき
**Results:** Drop-off: 高 / Job Proposal: 地域ミスマッチ+ニーズミスマッチ / Next Action: 開業相談は対象外だが人材としては価値大 / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + AMBIG_FAIL / **Severity:** Medium / **Fix Proposal:** 転職以外のニーズ（開業・キャリア相談）検出時は人間引き継ぎ / **Retry Needed:** Yes / **Auditor Comment:** 開業相談は業務範囲外だが、「この人材を逃すな」という判断を人間に委ねるべき。

---

### Case W3-024
- **Prefecture:** 福井県 / **Region Block:** 北陸 / **Case Type:** 標準 / **User Profile:** 29歳、外来2年、常勤 / **Entry Route:** LINE検索→友だち追加 / **Difficulty:** 標準
**Scenario:**
小浜市の病院外来勤務。LINE検索で「看護師 転職」と検索してBotアカウントを見つけた。地域を確認せず追加。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「その他の地域」を選択
5. Bot: il_facility_type表示
6. User: 「急性期」を選択
7. Bot: il_department表示
8. User: 「外科」を選択
9. Bot: il_workstyle表示
10. User: 「日勤のみ」を選択
11. Bot: il_urgency表示
12. User: 「良い所あれば」を選択
13. Bot: matching_preview → 関東施設5件表示
14. User: 離脱
**System Behavior Evaluation:**
- LINE検索からの流入はエリア認識なしで来るケースが多い
- 全フローを完走してから地域ミスマッチが判明するのは時間の無駄
- il_areaで「その他の地域」を選んだ時点でエリア外告知すべき
**Results:** Drop-off: matching_preview段階で離脱 / Job Proposal: 地域ミスマッチ / Next Action: なし / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + UX_DROP / **Severity:** High / **Fix Proposal:** 「その他の地域」選択直後に対象エリア告知。全フロー完走後に不適合を知らせるのはUXが悪すぎる / **Retry Needed:** Yes / **Auditor Comment:** 7ステップ費やしてから「実はエリア外でした」は最悪のUX。

---

## 山梨県（6件）

### Case W3-025
- **Prefecture:** 山梨県 / **Region Block:** 甲信越 / **Case Type:** 標準 / **User Profile:** 31歳、産婦人科4年、常勤 / **Entry Route:** Instagram→LINE / **Difficulty:** 標準
**Scenario:**
甲府市の産婦人科病院勤務。分娩件数が減少して将来が不安。近隣の山梨県内で探したい。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「その他の地域」を選択
5. Bot: il_facility_type表示
6. User: 「急性期」を選択
7. Bot: il_department表示
8. User: 「産婦人科」を選択
9. Bot: il_workstyle表示
10. User: 「夜勤ありOK」を選択
11. Bot: il_urgency表示
12. User: 「良い所あれば」を選択
13. Bot: matching_preview → 関東の急性期病院5件表示
14. User: 離脱
**System Behavior Evaluation:**
- 山梨は東京に隣接しており、通勤圏内の場合もある
- しかし「その他の地域」→undecidedでは八王子・相模原方面の近隣施設も提案できない
- 山梨→東京西部/神奈川西部の通勤可能性を活かせていない
**Results:** Drop-off: 高（ただし関東西部なら通勤可能性あり） / Job Proposal: 地域ミスマッチだが近隣あり / Next Action: 「東京都・神奈川県にも通勤可能ですか？」と聞くべき / Region Bias: 近隣関東を提案する機会を逃している / National Expansion Risk: 中
**Failure Category:** GEO_LOCK + AMBIG_FAIL / **Severity:** High / **Fix Proposal:** 「その他の地域」+隣接県（山梨・静岡等）の場合は「東京/神奈川への通勤は検討されますか？」と確認 / **Retry Needed:** Yes / **Auditor Comment:** 山梨は関東隣接県。他の北陸県と違い、通勤圏で救済可能なケースがある。

---

### Case W3-026
- **Prefecture:** 山梨県 / **Region Block:** 甲信越 / **Case Type:** 境界 / **User Profile:** 28歳、一般病棟3年、東京通勤中 / **Entry Route:** LP→LINE / **Difficulty:** 中
**Scenario:**
大月市在住で東京の病院に電車通勤している。通勤が片道1.5時間で辛く、東京か神奈川の職場に近い場所で探したい。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「東京都」を選択（勤務地で探す）
5. Bot: il_subarea表示
6. User: 東京西部のサブエリアを選択
7. Bot: il_facility_type表示
8. User: 「急性期」を選択
9. Bot: il_department表示
10. User: 「内科」を選択
11. Bot: il_workstyle表示
12. User: 「日勤のみ」を選択
13. Bot: il_urgency表示
14. User: 「すぐ転職したい」を選択
15. Bot: matching_preview → 東京西部の急性期病院5件表示
**System Behavior Evaluation:**
- 正常フロー。山梨在住でも勤務地として東京を選べば問題なし
- ただし通勤時間短縮が転職動機なのに、提案施設への通勤時間情報がない
- 大月からのアクセス情報があれば提案の精度が上がる
**Results:** Drop-off: 低 / Job Proposal: マッチ / Next Action: 通勤時間を考慮した施設絞り込み / Region Bias: なし / National Expansion Risk: なし
**Failure Category:** なし（正常フロー） / **Severity:** Low / **Fix Proposal:** 通勤時間/最寄り駅の情報をマッチング条件に追加 / **Retry Needed:** No / **Auditor Comment:** 山梨→東京通勤者はBotの正常フロー。通勤時間考慮で付加価値を出せる。

---

### Case W3-027
- **Prefecture:** 山梨県 / **Region Block:** 甲信越 / **Case Type:** 攻撃的 / **User Profile:** 33歳、美容クリニック志望 / **Entry Route:** LINE / **Difficulty:** 高
**Scenario:**
甲府在住。美容クリニックで働きたい。「美容」は選択肢にないのでフリーテキストで要望を送信。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「その他の地域」を選択
5. Bot: il_facility_type表示
6. User: 「美容クリニックで働きたい」（フリーテキスト）
7. Bot: il_facility_type再表示（フリーテキスト無視）
8. User: 「クリニック」を選択（仕方なく）
9. Bot: il_workstyle表示
10. User: 「日勤のみ」を選択
11. Bot: il_urgency表示
12. User: 「すぐ転職したい」を選択
13. Bot: matching_preview → 関東の一般クリニック5件表示
14. User: 「美容クリニックがないんですけど...」離脱
**System Behavior Evaluation:**
- 美容クリニックは人気分野だがil_facility_typeに専用選択肢がない
- 「クリニック」で代替すると一般クリニックが混在
- エリア外+分野ミスマッチの二重不適合
**Results:** Drop-off: 高 / Job Proposal: 分野ミスマッチ / Next Action: なし / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + JOB_MATCH_FAIL / **Severity:** High / **Fix Proposal:** (1) クリニックのサブカテゴリに「美容」を追加 (2) 美容クリニックは全国的にニーズが高いので選択肢として優先度高 / **Retry Needed:** Yes / **Auditor Comment:** 美容クリニック志望者は若年層に多く、SNS流入も多い。対応必須。

---

### Case W3-028
- **Prefecture:** 山梨県 / **Region Block:** 甲信越 / **Case Type:** 標準 / **User Profile:** 52歳、療養型10年 / **Entry Route:** LP→LINE / **Difficulty:** 標準
**Scenario:**
富士吉田市の療養型病院勤務。体力的にきつくなり、負担の少ない職場を探している。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「その他の地域」を選択
5. Bot: il_facility_type表示
6. User: 「慢性期」を選択
7. Bot: il_workstyle表示
8. User: 「パート・非常勤」を選択
9. Bot: il_urgency表示
10. User: 「まだ情報収集」を選択
11. Bot: matching_preview → 関東の慢性期病院5件表示
12. User: 離脱
**System Behavior Evaluation:**
- 富士吉田は静岡県にも近く、複数県での検索ニーズがある
- 「まだ情報収集」+エリア外は最も離脱率が高い組み合わせ
- 体力面の不安をヒアリングする項目がない
**Results:** Drop-off: サイレント離脱 / Job Proposal: 地域ミスマッチ / Next Action: なし / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK / **Severity:** High / **Fix Proposal:** 複数県またぎの検索に対応（山梨+東京+神奈川+静岡） / **Retry Needed:** Yes / **Auditor Comment:** 県境在住者の複数エリア検索ニーズは現行のil_area設計では対応不可。

---

### Case W3-029
- **Prefecture:** 山梨県 / **Region Block:** 甲信越 / **Case Type:** 境界 / **User Profile:** 23歳、新卒、内定前 / **Entry Route:** TikTok→LINE / **Difficulty:** 中
**Scenario:**
山梨県内の看護学生。まだ国試にも受かっていないが、就職先の情報収集をしたい。TikTokで見かけて軽い気持ちでLINE追加。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. User: 「まだ学生なんですけど、登録できますか？」（フリーテキスト）
4. Bot: il_area表示（フリーテキスト無視）
5. User: 「その他の地域」を選択
6. Bot: il_facility_type表示
7. User: 「こだわりなし」を選択
8. Bot: il_workstyle表示
9. User: 「日勤のみ」を選択
10. Bot: il_urgency表示
11. User: 「まだ情報収集」を選択
12. Bot: matching_preview → 関東施設5件表示
13. User: 「学生でも大丈夫なのかな...」（モヤモヤしながら離脱）
**System Behavior Evaluation:**
- 学生/未資格者の判別フローがない
- 紹介事業としては免許取得前の登録は法的にグレー
- 「まだ学生」という重要情報をBotが拾えない
**Results:** Drop-off: 高 / Job Proposal: 学生には不適切 / Next Action: 学生向け案内（免許取得後の再訪促し）が必要 / Region Bias: 関東偏重 / National Expansion Risk: N/A
**Failure Category:** AMBIG_FAIL + GEO_LOCK / **Severity:** Medium / **Fix Proposal:** 「学生」キーワード検出時に「免許取得後にご利用ください。取得後にまたお声がけくださいね！」と案内 / **Retry Needed:** Yes / **Auditor Comment:** 学生の早期囲い込みは将来の顧客獲得につながるが、法的リスクも考慮必要。

---

### Case W3-030
- **Prefecture:** 山梨県 / **Region Block:** 甲信越 / **Case Type:** 攻撃的 / **User Profile:** 37歳 / **Entry Route:** LINE / **Difficulty:** 高
**Scenario:**
英語で話しかけてくる外国人看護師。日本の看護師免許は持っている。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示（日本語）
3. User: "Hello, I'm a nurse looking for a job in Yamanashi. Do you have any openings?"
4. Bot: il_area表示（日本語）
5. User: "I don't understand Japanese well. Can you help in English?"
6. Bot: il_area再表示（日本語のまま）
7. User: Taps 「その他の地域」（選択肢は読めるがBotの説明は理解できない）
8. Bot: il_facility_type表示（日本語）
9. User: 混乱して離脱
**System Behavior Evaluation:**
- 多言語対応が一切ない
- 外国人看護師は増加傾向にあり、将来的なニーズは確実
- 選択式UIなら最低限操作可能だが、説明文が読めない
**Results:** Drop-off: 高 / Job Proposal: なし / Next Action: なし / Region Bias: N/A / National Expansion Risk: N/A
**Failure Category:** INPUT_LOCK / **Severity:** Medium / **Fix Proposal:** (1) 英語検出時に「Currently Japanese only. Please contact us via: [email/phone]」と案内 (2) 将来的に英語対応フロー追加 / **Retry Needed:** No / **Auditor Comment:** 外国人看護師対応は事業拡大の観点で将来課題。現時点ではScope外だが案内は必要。

---

## 長野県（6件）

### Case W3-031
- **Prefecture:** 長野県 / **Region Block:** 甲信越 / **Case Type:** 標準 / **User Profile:** 34歳、地域包括ケア病棟3年、常勤 / **Entry Route:** Google検索→LP→LINE / **Difficulty:** 標準
**Scenario:**
松本市の地域包括ケア病棟勤務。地域医療に関心があるが、松本市内で選択肢を広げたい。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「その他の地域」を選択
5. Bot: il_facility_type表示
6. User: 「回復期」を選択（地域包括ケアに最も近い）
7. Bot: il_workstyle表示
8. User: 「日勤のみ」を選択
9. Bot: il_urgency表示
10. User: 「良い所あれば」を選択
11. Bot: matching_preview → 関東の回復期病院5件表示
12. User: 離脱
**System Behavior Evaluation:**
- 地域包括ケア病棟という分類がil_facility_typeにない
- 「回復期」で代替するしかないが、地域包括ケアとは異なる
- 長野県は医療資源が分散しており、地域医療のニーズが高い
**Results:** Drop-off: 高 / Job Proposal: 地域ミスマッチ / Next Action: なし / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK / **Severity:** High / **Fix Proposal:** 地域包括ケア病棟をil_facility_typeの選択肢に追加 / **Retry Needed:** Yes / **Auditor Comment:** 地域包括ケア病棟は2025年以降増加傾向。カテゴリとして対応すべき。

---

### Case W3-032
- **Prefecture:** 長野県 / **Region Block:** 甲信越 / **Case Type:** 標準 / **User Profile:** 26歳、急性期2年、Uターン希望 / **Entry Route:** LP→LINE / **Difficulty:** 標準
**Scenario:**
東京の大学病院で2年勤務。長野県上田市の実家に戻りたい。Uターン転職希望。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「その他の地域」を選択（長野に帰りたいので）
5. Bot: il_facility_type表示
6. User: 「急性期」を選択
7. Bot: il_department表示
8. User: 「内科」を選択
9. Bot: il_workstyle表示
10. User: 「夜勤ありOK」を選択
11. Bot: il_urgency表示
12. User: 「良い所あれば」を選択
13. Bot: matching_preview → 関東の急性期病院5件表示
14. User: 「長野に戻りたいのに東京の病院が出てきた...」離脱
**System Behavior Evaluation:**
- Uターン転職は地方出身者にとって重要なニーズ
- 現在東京にいるのに「その他の地域」を選ぶ行動が示す「帰りたい」意図を汲めない
- 「東京都」を選べば正常フローだが、それは本人の希望と逆
**Results:** Drop-off: 高 / Job Proposal: 地域ミスマッチ（現住所ではなく希望勤務地がエリア外） / Next Action: なし / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK / **Severity:** High / **Fix Proposal:** il_areaの質問を「お住まいの地域」ではなく「働きたい地域」と明確化 / **Retry Needed:** Yes / **Auditor Comment:** Uターン希望者は地方創生の文脈でも重要。il_areaの質問文があいまいだと正しい選択ができない。

---

### Case W3-033
- **Prefecture:** 長野県 / **Region Block:** 甲信越 / **Case Type:** 境界 / **User Profile:** 41歳、訪問看護6年、ケアマネ資格あり / **Entry Route:** LP→LINE / **Difficulty:** 中
**Scenario:**
長野市の訪問看護ステーション勤務。ケアマネージャー資格を取得したので、ケアマネとして転職したい。しかしBotは看護師紹介専門。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. User: 「ケアマネの求人はありますか？」（フリーテキスト）
4. Bot: il_area表示（フリーテキスト無視）
5. User: 「その他の地域」を選択
6. Bot: il_facility_type表示
7. User: 「介護施設」を選択（ケアマネに最も近い）
8. Bot: il_workstyle表示
9. User: 「日勤のみ」を選択
10. Bot: il_urgency表示
11. User: 「良い所あれば」を選択
12. Bot: matching_preview → 関東の介護施設5件表示（看護師求人として）
13. User: 「ケアマネの求人じゃないんですけど...」離脱
**System Behavior Evaluation:**
- 看護師紹介事業なのでケアマネ求人は対象外
- しかし「ケアマネ」と言われたときに「看護師求人のみ取り扱い」と明示すべき
- ケアマネ資格を持つ看護師は介護施設での看護師求人で付加価値が高い
**Results:** Drop-off: 高 / Job Proposal: 職種ミスマッチ / Next Action: 「看護師としてケアマネ資格を活かせる求人」の提案が可能 / Region Bias: 関東偏重 / National Expansion Risk: N/A
**Failure Category:** AMBIG_FAIL + GEO_LOCK / **Severity:** Medium / **Fix Proposal:** (1) 「ケアマネ」検出時に「看護師求人のみですが、ケアマネ資格を活かせる看護師求人もあります」と案内 (2) 保有資格のヒアリング追加 / **Retry Needed:** Yes / **Auditor Comment:** 隣接職種のニーズを看護師求人に変換する提案力がBotに必要。

---

### Case W3-034
- **Prefecture:** 長野県 / **Region Block:** 甲信越 / **Case Type:** 攻撃的 / **User Profile:** 30歳 / **Entry Route:** LINE / **Difficulty:** 高
**Scenario:**
個人情報を一切出したくないユーザー。全ての質問に対して最小限の回答しかしない。名前も聞かれたら拒否する。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「その他の地域」を選択
5. Bot: il_facility_type表示
6. User: 「こだわりなし」を選択
7. Bot: il_workstyle表示
8. User: 「こだわりなし」と入力（選択肢にない場合）
9. Bot: il_workstyle再表示
10. User: 「日勤のみ」を選択（仕方なく）
11. Bot: il_urgency表示
12. User: 「まだ情報収集」を選択
13. Bot: matching_preview → 関東施設5件表示
14. Bot: 「お名前を教えてください」（想定）
15. User: 「教えたくありません」
16. Bot: 対応不明
**System Behavior Evaluation:**
- 個人情報拒否に対するフォールバックがない
- 「こだわりなし」が全項目で選べるわけではない
- 匿名での情報収集ニーズは正当だが、紹介事業としては個人情報が必要
**Results:** Drop-off: 個人情報要求時に離脱 / Job Proposal: 匿名では紹介不可 / Next Action: 情報提供のみモードに切替 / Region Bias: N/A / National Expansion Risk: N/A
**Failure Category:** INPUT_LOCK / **Severity:** Medium / **Fix Proposal:** (1) 匿名での情報閲覧モードを用意 (2) 「個人情報は紹介確定時まで不要です」と安心感を与える設計 / **Retry Needed:** Yes / **Auditor Comment:** プライバシー懸念は正当。段階的な情報開示設計が必要。

---

### Case W3-035
- **Prefecture:** 長野県 / **Region Block:** 甲信越 / **Case Type:** 境界 / **User Profile:** 38歳、病棟→保健師転職希望 / **Entry Route:** LP→LINE / **Difficulty:** 中
**Scenario:**
長野県飯田市の病棟看護師。保健師資格を持っており、産業保健師や行政保健師に転向したい。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. User: 「保健師の求人はありますか？」（フリーテキスト）
4. Bot: il_area表示（フリーテキスト無視）
5. User: 「その他の地域」を選択
6. Bot: il_facility_type表示
7. User: どれも合わないので「こだわりなし」を選択
8. Bot: il_workstyle表示
9. User: 「日勤のみ」を選択
10. Bot: il_urgency表示
11. User: 「良い所あれば」を選択
12. Bot: matching_preview → 関東の看護師求人5件表示
13. User: 「保健師の求人じゃないですね...」離脱
**System Behavior Evaluation:**
- 保健師は看護師の隣接職種だが、BOTの対象外
- 「保健師」キーワードに対する明示的な回答がない
- 保健師資格を持つ看護師は看護師求人でも価値が高い
**Results:** Drop-off: 高 / Job Proposal: 職種ミスマッチ / Next Action: なし / Region Bias: 関東偏重 / National Expansion Risk: N/A
**Failure Category:** AMBIG_FAIL + GEO_LOCK / **Severity:** Medium / **Fix Proposal:** 「保健師」「助産師」等の隣接職種キーワード検出時に対象外であることを明示しつつ、看護師求人への誘導を試みる / **Retry Needed:** Yes / **Auditor Comment:** W3-033（ケアマネ）と同様、隣接職種のニーズへの対応が必要。

---

### Case W3-036
- **Prefecture:** 長野県 / **Region Block:** 甲信越 / **Case Type:** 標準 / **User Profile:** 27歳、小児科3年 / **Entry Route:** TikTok→LINE / **Difficulty:** 標準
**Scenario:**
軽井沢在住。小児科で働いているが、軽井沢周辺（長野県東部・群馬県西部）で転職先を探したい。県境エリア。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「その他の地域」を選択（長野なので）
5. Bot: il_facility_type表示
6. User: 「急性期」を選択
7. Bot: il_department表示
8. User: 「小児科」を選択
9. Bot: il_workstyle表示
10. User: 「日勤のみ」を選択
11. Bot: il_urgency表示
12. User: 「良い所あれば」を選択
13. Bot: matching_preview → 関東施設5件表示
14. User: 「群馬の高崎とか前橋とかの求人はないですか？」
15. Bot: フリーテキスト未解析
**System Behavior Evaluation:**
- 軽井沢→群馬西部は現実的な通勤圏
- 「その他の地域」を選んだが、実は埼玉・群馬にもアクセス可能
- DBに群馬の施設があるかは不明（埼玉はDBあり）
- 県境在住者の複数エリア検索ニーズに対応できない
**Results:** Drop-off: 高 / Job Proposal: 関東施設が出るが、軽井沢から通える施設かは不明 / Next Action: 埼玉の施設なら通勤可能性あり / Region Bias: 提案が的外れ / National Expansion Risk: 中
**Failure Category:** GEO_LOCK + AMBIG_FAIL / **Severity:** High / **Fix Proposal:** (1) 「その他の地域」選択時に隣接県への通勤可否を確認 (2) 複数エリアの同時検索機能 / **Retry Needed:** Yes / **Auditor Comment:** 軽井沢は新幹線で東京1時間。関東DBの施設が通勤圏にある可能性があるのに活かせていない。

---

## 予備（4件）

### Case W3-037
- **Prefecture:** 新潟県（佐渡島） / **Region Block:** 甲信越 / **Case Type:** 境界 / **User Profile:** 45歳、離島医療15年 / **Entry Route:** LP→LINE / **Difficulty:** 高
**Scenario:**
佐渡島の診療所で15年勤務。本土に戻りたいが、離島医療の経験しかなく不安。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「その他の地域」を選択
5. Bot: il_facility_type表示
6. User: 「クリニック」を選択
7. Bot: il_workstyle表示
8. User: 「日勤のみ」を選択
9. Bot: il_urgency表示
10. User: 「良い所あれば」を選択
11. Bot: matching_preview → 関東のクリニック5件表示
12. User: 「離島から本土に戻りたいんですけど、どこがいいですか？」
13. Bot: フリーテキスト未解析
14. User: 離脱
**System Behavior Evaluation:**
- 離島医療経験者は希少価値が高い人材
- 「本土に戻りたい」は関東も含むが、BOTがこの文脈を理解できない
- 離島→本土の転職は引越し・生活再建を伴う大きな判断
**Results:** Drop-off: 高 / Job Proposal: 地域不明だが関東でも可能性あり / Next Action: 人間引き継ぎで丁寧な相談対応が必要 / Region Bias: N/A / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + HUMAN_HANDOFF_FAIL / **Severity:** High / **Fix Proposal:** 離島・へき地からの転職は特殊ケースとして即人間引き継ぎ / **Retry Needed:** Yes / **Auditor Comment:** 離島医療経験者は自治体の奨学金返済等の事情もあり、BOT対応は不適切。

---

### Case W3-038
- **Prefecture:** 富山県 / **Region Block:** 北陸 / **Case Type:** 攻撃的 / **User Profile:** 不明（Bot業者の可能性） / **Entry Route:** LINE / **Difficulty:** 高
**Scenario:**
短時間に大量のメッセージを送信するアカウント。求人情報を自動収集しようとしている疑い。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. User: 「東京都」を選択
4. Bot: il_subarea表示
5. User: 即座にサブエリア選択
6. Bot: il_facility_type表示
7. User: 即座に「急性期」選択
8. Bot: il_department表示
9. User: 即座に「内科」選択（全て1秒以内）
10. Bot: il_workstyle表示
11. User: 即座に選択
12. Bot: matching_preview → 5件表示
13. User: 即座にLINEブロック→別アカウントで再追加→同じフローを繰り返し
**System Behavior Evaluation:**
- Bot/スクレイパー対策がない
- 応答速度の異常検知がない
- 求人情報の大量取得を防ぐ仕組みがない
- レート制限がない
**Results:** Drop-off: N/A（悪意ある利用） / Job Proposal: N/A / Next Action: アカウントBAN / Region Bias: N/A / National Expansion Risk: N/A
**Failure Category:** OTHER（セキュリティ） / **Severity:** High / **Fix Proposal:** (1) 応答間隔の異常検知（全選択が1秒以内→Bot判定） (2) 同一IPからの複数アカウント検出 (3) matching_previewの表示回数制限 / **Retry Needed:** No / **Auditor Comment:** 競合他社による情報スクレイピングのリスク。求人データは資産。

---

### Case W3-039
- **Prefecture:** 石川県 / **Region Block:** 北陸 / **Case Type:** 境界 / **User Profile:** 36歳、病棟5年+育休2年、復帰先探し / **Entry Route:** ママ友紹介→LINE / **Difficulty:** 中
**Scenario:**
金沢市在住。育休から復帰するが元の職場に戻りたくない。時短勤務可能な職場を探している。ママ友から紹介された。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. User: 「育休明けで時短で働ける病院を探しています」（フリーテキスト）
4. Bot: il_area表示（フリーテキスト無視）
5. User: 「その他の地域」を選択
6. Bot: il_facility_type表示
7. User: 「急性期」を選択
8. Bot: il_department表示
9. User: 「こだわりなし」（選択肢にあれば）or 適当に選択
10. Bot: il_workstyle表示
11. User: 「パート・非常勤」を選択（時短に最も近い）
12. Bot: il_urgency表示
13. User: 「すぐ転職したい」を選択
14. Bot: matching_preview → 関東施設5件表示
15. User: 「金沢で...」離脱
**System Behavior Evaluation:**
- 「時短勤務」という選択肢がil_workstyleにない
- パート・非常勤≠時短勤務（常勤の時短制度とは異なる）
- 育休明けの復帰サポートはニーズが高いが、BOTで拾えない
- ママ友紹介の信頼度をBotが活かせない
**Results:** Drop-off: 高 / Job Proposal: 地域ミスマッチ+勤務形態ミスマッチ / Next Action: 育休復帰相談として人間引き継ぎ / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + AMBIG_FAIL / **Severity:** High / **Fix Proposal:** (1) il_workstyleに「時短勤務」を追加 (2) 「育休」「時短」キーワードで相談モード切替 / **Retry Needed:** Yes / **Auditor Comment:** ペルソナ「ミサキ」に近い属性。このケースを落とすのは戦略的に最も痛い。

---

### Case W3-040
- **Prefecture:** 長野県 / **Region Block:** 甲信越 / **Case Type:** 攻撃的 / **User Profile:** 不明 / **Entry Route:** LINE / **Difficulty:** 高
**Scenario:**
看護師ではない一般人が興味本位でBotを操作。途中で「看護師じゃないけど大丈夫？」と聞く。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「東京都」を選択
5. Bot: il_subarea表示
6. User: サブエリア選択
7. Bot: il_facility_type表示
8. User: 「クリニック」を選択
9. Bot: il_workstyle表示
10. User: 「看護師じゃないんですけど、医療事務の求人ありますか？」（フリーテキスト）
11. Bot: il_workstyle再表示（フリーテキスト無視）
12. User: 「日勤のみ」を選択
13. Bot: il_urgency表示
14. User: 「まだ情報収集」を選択
15. Bot: matching_preview → 東京のクリニック5件表示（看護師求人として）
**System Behavior Evaluation:**
- 非看護師の利用を判別できない
- 「看護師じゃない」というキーワードを拾えない
- 医療事務など他職種求人は対象外
- 非対象者に看護師求人を表示しても無駄
**Results:** Drop-off: matching_preview後に離脱 / Job Proposal: 職種ミスマッチ / Next Action: なし / Region Bias: なし / National Expansion Risk: N/A
**Failure Category:** AMBIG_FAIL / **Severity:** Low / **Fix Proposal:** 「看護師免許をお持ちですか？」の確認ステップ追加 or 「看護師じゃない」検出時に「看護師専門のサービスです」と案内 / **Retry Needed:** No / **Auditor Comment:** 発生頻度は低いが、SNS流入が増えると非看護師の利用も増える。

---

## クロステスト: 東京都（2件）

### Case W3-041
- **Prefecture:** 東京都 / **Region Block:** 関東 / **Case Type:** 標準 / **User Profile:** 29歳、ICU3年、常勤 / **Entry Route:** LP→LINE / **Difficulty:** 標準
**Scenario:**
新潟出身で東京都内のICU勤務。ICU経験を活かして都内で転職したい。正常フローの確認。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「東京都」を選択
5. Bot: il_subarea表示
6. User: 「23区」を選択
7. Bot: il_facility_type表示
8. User: 「急性期」を選択
9. Bot: il_department表示
10. User: 「内科」を選択（ICUがないため）
11. Bot: il_workstyle表示
12. User: 「夜勤ありOK」を選択
13. Bot: il_urgency表示
14. User: 「すぐ転職したい」を選択
15. Bot: matching_preview → 東京23区の急性期病院5件表示
**System Behavior Evaluation:**
- 正常フロー。東京のDBがあるので施設表示は適切
- ICUがdepartment選択肢にないのは主担当ケースと同じ問題
- 「すぐ転職したい」の高温度ユーザーに対する迅速な人間引き継ぎの有無
**Results:** Drop-off: 低 / Job Proposal: マッチ / Next Action: 人間引き継ぎで詳細条件ヒアリング / Region Bias: なし / National Expansion Risk: なし
**Failure Category:** JOB_MATCH_FAIL（軽微） / **Severity:** Low / **Fix Proposal:** ICUを診療科選択肢に追加 / **Retry Needed:** No / **Auditor Comment:** 正常フローの確認OK。ICU問題はW3-004と共通。

---

### Case W3-042
- **Prefecture:** 東京都 / **Region Block:** 関東 / **Case Type:** 境界 / **User Profile:** 35歳、ER→日勤クリニック転換希望 / **Entry Route:** TikTok→LINE / **Difficulty:** 中
**Scenario:**
東京都多摩地域のER勤務。燃え尽きて日勤のみのクリニックに転職したい。TikTokの看護師あるある動画からLINE追加。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「東京都」を選択
5. Bot: il_subarea表示
6. User: 「多摩」を選択（サブエリアの表現次第）
7. Bot: il_facility_type表示
8. User: 「クリニック」を選択
9. Bot: il_workstyle表示
10. User: 「日勤のみ」を選択
11. Bot: il_urgency表示
12. User: 「良い所あれば」を選択
13. Bot: matching_preview → 多摩エリアのクリニック5件表示
**System Behavior Evaluation:**
- 正常フロー。ER→クリニックのキャリアチェンジはよくあるパターン
- 多摩地域のサブエリア表示が適切か（23区/多摩/島しょ等の分類）
- ER経験者のスキルを活かせるクリニック提案ができるか
**Results:** Drop-off: 低 / Job Proposal: マッチ / Next Action: ER経験を活かせるクリニック提案 / Region Bias: なし / National Expansion Risk: なし
**Failure Category:** なし（正常フロー） / **Severity:** Low / **Fix Proposal:** キャリアチェンジ（病棟→クリニック等）のパターンに応じた提案ロジック / **Retry Needed:** No / **Auditor Comment:** 正常フローの確認OK。

---

## クロステスト: 神奈川県（2件）

### Case W3-043
- **Prefecture:** 神奈川県 / **Region Block:** 関東 / **Case Type:** 標準 / **User Profile:** 32歳、回復期リハ4年、常勤 / **Entry Route:** Google検索→LP→LINE / **Difficulty:** 標準
**Scenario:**
横浜市の回復期リハビリテーション病院勤務。同市内で給与の高い急性期病院に戻りたい。サービスのメインターゲット。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「神奈川県」を選択
5. Bot: il_subarea表示
6. User: 「横浜」を選択
7. Bot: il_facility_type表示
8. User: 「急性期」を選択
9. Bot: il_department表示
10. User: 「整形外科」を選択（リハビリ経験を活かす）
11. Bot: il_workstyle表示
12. User: 「夜勤ありOK」を選択
13. Bot: il_urgency表示
14. User: 「すぐ転職したい」を選択
15. Bot: matching_preview → 横浜の急性期病院5件表示
**System Behavior Evaluation:**
- 完全な正常フロー。メインターゲットエリア+施設種別+診療科の全マッチ
- DB212施設中横浜79施設からの選択なので精度が最も高い
- 「すぐ転職したい」に対する迅速な人間引き継ぎが重要
**Results:** Drop-off: 低 / Job Proposal: 高精度マッチ / Next Action: 即時人間引き継ぎで面談設定 / Region Bias: なし / National Expansion Risk: なし
**Failure Category:** なし（理想的フロー） / **Severity:** N/A / **Fix Proposal:** N/A / **Retry Needed:** No / **Auditor Comment:** これがBotのゴールデンパス。全ケースがこうなるべき。

---

### Case W3-044
- **Prefecture:** 神奈川県 / **Region Block:** 関東 / **Case Type:** 境界 / **User Profile:** 28歳、小田原の病棟3年 / **Entry Route:** LP→LINE / **Difficulty:** 中
**Scenario:**
小田原市の中規模病院勤務。県西エリアは施設数が少ないが、自宅から通える範囲で探したい。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「神奈川県」を選択
5. Bot: il_subarea表示
6. User: 「県西」を選択（小田原・足柄など）
7. Bot: il_facility_type表示
8. User: 「急性期」を選択
9. Bot: il_department表示
10. User: 「内科」を選択
11. Bot: il_workstyle表示
12. User: 「日勤のみ」を選択
13. Bot: il_urgency表示
14. User: 「良い所あれば」を選択
15. Bot: matching_preview → 県西の施設表示（DB17施設から5件）
**System Behavior Evaluation:**
- 正常フロー。県西はDB17施設あるので提案可能
- ただし急性期+内科+日勤のみで絞ると5件未満の可能性
- 条件緩和の提案（「県央エリアも含めますか？」等）があると良い
**Results:** Drop-off: 低〜中（施設数不足の場合） / Job Proposal: マッチだが選択肢が少ない可能性 / Next Action: 条件緩和または隣接エリア提案 / Region Bias: なし / National Expansion Risk: なし
**Failure Category:** JOB_MATCH_FAIL（軽微） / **Severity:** Low / **Fix Proposal:** 検索結果が5件未満の場合、隣接エリアの施設も表示するオプション / **Retry Needed:** No / **Auditor Comment:** 県西は施設数が限られるが、これは地理的現実。隣接エリア提案で補える。

---

## クロステスト: 愛知県（2件）

### Case W3-045
- **Prefecture:** 愛知県 / **Region Block:** 東海 / **Case Type:** 標準 / **User Profile:** 30歳、急性期4年、常勤 / **Entry Route:** Instagram広告→LINE / **Difficulty:** 標準
**Scenario:**
名古屋市の総合病院勤務。Instagram広告で「手数料10%」に惹かれたがエリア外。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 選択肢に愛知がないことに気づく
5. User: 「名古屋の求人はないですか？」（フリーテキスト）
6. Bot: il_area再表示
7. User: 「その他の地域」を選択
8. Bot: il_facility_type表示
9. User: 途中で「これ関東のサービスか」と気づいて離脱
**System Behavior Evaluation:**
- 愛知県はDBに0施設。完全にエリア外
- Instagram広告が全国配信されている場合、名古屋からの流入が多い
- il_area段階で離脱するのでフローの浅い段階で離脱（被害は少ない）
**Results:** Drop-off: il_area段階で離脱 / Job Proposal: なし / Next Action: なし / Region Bias: 広告配信エリアの問題 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK / **Severity:** High / **Fix Proposal:** (1) 広告配信を関東に限定 (2) LP/Welcome文に「関東エリア限定」と明記 / **Retry Needed:** Yes / **Auditor Comment:** 広告費の無駄。愛知は人口が多いので広告配信エリア制限が効果的。

---

### Case W3-046
- **Prefecture:** 愛知県 / **Region Block:** 東海 / **Case Type:** 攻撃的 / **User Profile:** 33歳、怒り / **Entry Route:** LINE / **Difficulty:** 高
**Scenario:**
名古屋のER看護師。友人に紹介されてLINE追加したが、愛知が選択肢にないことに激怒。クレームメッセージを送信。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「なんで愛知県がないんですか？全国対応じゃないの？」
5. Bot: il_area再表示（フリーテキスト無視）
6. User: 「返事しろよ！使えないBotだな」
7. Bot: il_area再表示
8. User: 「もういい。二度と使わない」→ LINEブロック+SNSで悪評投稿
**System Behavior Evaluation:**
- 怒りのメッセージに対するエスカレーション機能がない
- 「使えない」「クソ」等のネガティブキーワード検出がない
- SNSでの悪評拡散リスクが高い
- 紹介元の友人関係にも悪影響
**Results:** Drop-off: ブロック+悪評拡散 / Job Proposal: なし / Next Action: 事後対応不可（ブロック済み） / Region Bias: N/A / National Expansion Risk: Critical（風評被害）
**Failure Category:** GEO_LOCK + HUMAN_HANDOFF_FAIL / **Severity:** Critical / **Fix Proposal:** (1) ネガティブキーワード検出で即人間引き継ぎ (2) フリーテキスト質問への最低限の応答（「申し訳ございません。現在関東エリアのみ...」） (3) 怒りの感情検出アラート / **Retry Needed:** Yes / **Auditor Comment:** 1人の悪評は10人の潜在顧客を失う。怒りへの対応は最優先。

---

## クロステスト: 大阪府（2件）

### Case W3-047
- **Prefecture:** 大阪府 / **Region Block:** 関西 / **Case Type:** 標準 / **User Profile:** 27歳、病棟2年、常勤 / **Entry Route:** TikTok→LINE / **Difficulty:** 標準
**Scenario:**
大阪市の急性期病棟勤務。TikTokで「看護師転職」動画を見てLINE追加。大阪の求人を期待。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「その他の地域」を選択
5. Bot: il_facility_type表示
6. User: 「急性期」を選択
7. Bot: il_department表示
8. User: 「外科」を選択
9. Bot: il_workstyle表示
10. User: 「夜勤ありOK」を選択
11. Bot: il_urgency表示
12. User: 「すぐ転職したい」を選択
13. Bot: matching_preview → 関東施設5件表示
14. User: 「大阪の求人がないならいらないです」離脱
**System Behavior Evaluation:**
- 大阪からの流入はTikTok全国配信の典型的な副作用
- 大阪→関東の転居は非現実的（大多数のケースで）
- 「すぐ転職したい」高温度ユーザーの取りこぼし
**Results:** Drop-off: matching_preview段階で離脱 / Job Proposal: 地域ミスマッチ / Next Action: なし / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK / **Severity:** High / **Fix Proposal:** TikTok/Instagram広告のターゲット地域を関東に絞る / **Retry Needed:** Yes / **Auditor Comment:** 大阪はw/東京に次ぐ看護師人口。エリア拡大の最優先候補だが、現時点では対応不可。

---

### Case W3-048
- **Prefecture:** 大阪府 / **Region Block:** 関西 / **Case Type:** 境界 / **User Profile:** 40歳、大阪→東京の転居予定 / **Entry Route:** LP→LINE / **Difficulty:** 中
**Scenario:**
大阪在住だが配偶者の転勤で3ヶ月後に東京に引っ越し予定。事前に転職先を確保したい。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. User: 「3ヶ月後に東京に引っ越すのですが、今から探せますか？」（フリーテキスト）
4. Bot: il_area表示（フリーテキスト無視）
5. User: 「東京都」を選択
6. Bot: il_subarea表示
7. User: サブエリア選択
8. Bot: il_facility_type表示
9. User: 「急性期」を選択
10. Bot: il_department表示
11. User: 「内科」を選択
12. Bot: il_workstyle表示
13. User: 「日勤のみ」を選択
14. Bot: il_urgency表示
15. User: 「良い所あれば」を選択
16. Bot: matching_preview → 東京の急性期病院5件表示
**System Behavior Evaluation:**
- 東京を選択したので正常フロー
- ただし「3ヶ月後」という時間軸をBotが拾えない
- 入職時期の調整が必要だが、ヒアリング項目にない
**Results:** Drop-off: 低 / Job Proposal: マッチ / Next Action: 入職時期の調整を人間が対応 / Region Bias: なし / National Expansion Risk: なし
**Failure Category:** なし（正常フロー） / **Severity:** Low / **Fix Proposal:** 入職希望時期のヒアリング項目を追加 / **Retry Needed:** No / **Auditor Comment:** 転居予定者はBotの正常フローで対応可能。時間軸のヒアリングが改善点。

---

## クロステスト: 福岡県（2件）

### Case W3-049
- **Prefecture:** 福岡県 / **Region Block:** 九州 / **Case Type:** 標準 / **User Profile:** 26歳、急性期2年 / **Entry Route:** Instagram→LINE / **Difficulty:** 標準
**Scenario:**
福岡市の急性期病院勤務。Instagram広告からLINE追加。九州の求人を期待。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「その他の地域」を選択
5. Bot: il_facility_type表示
6. User: 「急性期」を選択
7. Bot: il_department表示
8. User: 「循環器」を選択
9. Bot: il_workstyle表示
10. User: 「夜勤ありOK」を選択
11. Bot: il_urgency表示
12. User: 「良い所あれば」を選択
13. Bot: matching_preview → 関東施設5件表示
14. User: 「福岡じゃないんですね...」離脱
**System Behavior Evaluation:**
- 福岡は東京/大阪に次ぐ医療都市。エリア外は大きな機会損失
- 福岡→関東の転居は距離的に非現実的
- Instagram広告の全国配信問題
**Results:** Drop-off: matching_preview段階で離脱 / Job Proposal: 地域ミスマッチ / Next Action: なし / Region Bias: 関東偏重 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK / **Severity:** High / **Fix Proposal:** 広告配信の地域制限 / **Retry Needed:** Yes / **Auditor Comment:** 福岡はエリア拡大候補。現時点ではSNS配信のターゲティングで対応。

---

### Case W3-050
- **Prefecture:** 福岡県 / **Region Block:** 九州 / **Case Type:** 攻撃的 / **User Profile:** 31歳、方言が強い / **Entry Route:** LINE / **Difficulty:** 高
**Scenario:**
博多弁でフリーテキストを送信。選択肢を無視して自然な方言で会話しようとする。
**Conversation Flow:**
1. User: LINE友だち追加
2. Bot: Welcome表示
3. Bot: il_area表示
4. User: 「福岡で看護師の仕事ば探しとっちゃけど、なんかあると？」（博多弁フリーテキスト）
5. Bot: il_area再表示（フリーテキスト無視）
6. User: 「なんでシカトすると？ちゃんと答えてくれん？」
7. Bot: il_area再表示
8. User: 「もうよかー」離脱
**System Behavior Evaluation:**
- 方言のフリーテキスト処理は高難度だが、「福岡」「看護師」「仕事」は標準語
- 方言を使うユーザー=地方在住者の可能性が高い→エリア外リスク高
- 「シカトすると？」は怒りのシグナルだがBotが検出できない
**Results:** Drop-off: 早期離脱 / Job Proposal: なし / Next Action: なし / Region Bias: N/A / National Expansion Risk: 高
**Failure Category:** INPUT_LOCK + GEO_LOCK / **Severity:** High / **Fix Proposal:** (1) フリーテキストから都道府県名を抽出する基本的なNLP (2) 方言に関係なく「福岡」は検出可能なはず (3) 怒りシグナル検出 / **Retry Needed:** Yes / **Auditor Comment:** 方言は難しいが、都道府県名の抽出は方言に関係なく可能。最低限のフリーテキスト解析を実装すべき。

---

## 統計サマリ

### 失敗カテゴリ分布
| Category | Count | % |
|----------|-------|---|
| GEO_LOCK | 36 | 72% |
| INPUT_LOCK | 7 | 14% |
| AMBIG_FAIL | 7 | 14% |
| HUMAN_HANDOFF_FAIL | 5 | 10% |
| JOB_MATCH_FAIL | 5 | 10% |
| UX_DROP | 1 | 2% |
| REENTRY_FAIL | 1 | 2% |
| REGION_EXPANSION_FAIL | 1 | 2% |
| OTHER（セキュリティ） | 1 | 2% |
| 正常フロー | 8 | 16% |

*注: 1ケースに複数カテゴリが該当するため合計は100%を超える*

### Severity分布
| Severity | Count |
|----------|-------|
| Critical | 10 |
| High | 24 |
| Medium | 7 |
| Low | 8 |
| N/A | 1 |

### 主要発見事項
1. **甲信越・北陸6県は全てDB未登録**。全40件の主担当ケースでGEO_LOCKが発生する
2. **「その他の地域」→undecided→関東施設表示**のパターンが最大の問題。ユーザーは全フローを完走してから地域ミスマッチを知らされる
3. **山梨県・長野県東部（軽井沢）は関東隣接県**であり、通勤圏で救済可能なケースが存在する。現行設計ではこの機会を逃している
4. **フリーテキスト未解析**が二番目に大きな問題。都道府県名の抽出すらできていない
5. **高温度ユーザー（すぐ転職したい）+エリア外**の組み合わせが最も深刻。競合に流れるリスクが最大
6. **広告（Instagram/TikTok）の全国配信**がエリア外流入の最大原因。広告費の無駄遣い
7. **クロステスト（関東選択）は全て正常フロー**。Bot自体の機能は関東内では問題なく動作する

### 最優先の改善提案（Worker 3視点）
1. **il_area「その他の地域」選択直後にエリア外告知**。全フロー完走後に知らせるのは最悪のUX
2. **フリーテキストから都道府県名を抽出**し、エリア外の場合は即時通知
3. **SNS広告の配信エリアを関東に限定**（CPA改善に直結）
4. **山梨・長野東部の隣接県ユーザーに「関東への通勤は検討しますか？」と確認**
5. **怒り・緊急・メンタル危機のキーワード検出→即時人間引き継ぎ**
