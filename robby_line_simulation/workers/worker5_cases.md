# Worker 5: 関西ブロック テストケース（50件）

> 担当: 滋賀(5), 京都(6), 大阪(8), 兵庫(7), 奈良(5), 和歌山(5), 予備(4), クロス(10)
> Mix: 標準30件, 境界12件, 攻撃的8件
> 作成日: 2026-04-06

---

## 標準ケース（30件）

### Case W5-001
- **Prefecture:** 大阪府 / **Region Block:** 関西 / **Case Type:** 標準 / **User Profile:** 28歳女性、急性期病院3年目、夜勤あり常勤 / **Entry Route:** Instagram広告→LINE / **Difficulty:** 低
**Scenario:**
大阪市内の急性期病院で勤務中の看護師。通勤圏内で転職希望。LINE登録後にフローを開始。
**Conversation Flow:**
1. User: LINE友達追加
2. Bot: ウェルカムメッセージ + 「求人を見る」ボタン
3. User: 「求人を見る」タップ
4. Bot: 「X件の医療機関の中から...どのエリアで働きたいですか？」→ 東京都/神奈川県/千葉県/埼玉県/その他の地域
5. User: 「大阪」と自由テキスト入力（Quick Replyを無視）
6. Bot: Quick Reply再表示（il_areaフェーズでの自由テキスト→再表示処理）
7. User: 「その他の地域」をタップ
8. Bot: il_subarea表示 → 「その他の地域ですね！ 候補: X件」→ 施設タイプ選択へ（サブエリアなし）
9. User: 「急性期病院」タップ → 診療科選択 → 「内科系」→ 働き方「日勤・夜勤両方」→ 温度感「すぐにでも」
10. Bot: matching_preview → 関東の施設5件を表示
**System Behavior Evaluation:**
- 「大阪」の自由テキスト入力は無視され、Quick Reply再表示のみ。大阪府の選択肢が存在しない
- 「その他の地域」→ area=undecided → AREA_ZONE_MAP=["横浜","川崎","23区","多摩","さいたま","千葉"] → 関東施設のみ表示
- 大阪希望のユーザーに横浜・川崎の病院を提案。完全なミスマッチ
**Results:** Drop-off: 極めて高い / Job Proposal: 関東施設のみ（大阪ゼロ） / Next Action: 離脱→ブロック / Region Bias: 関東限定 / National Expansion Risk: 致命的
**Failure Category:** GEO_LOCK + REGION_EXPANSION_FAIL
**Severity:** Critical
**Fix Proposal:** (1) il_prefに関西圏の選択肢追加 (2) DB未対応エリアの場合「現在準備中」メッセージ+人間引き継ぎ (3) 自由テキスト「大阪」をNLP解析してエリア外通知
**Retry Needed:** Yes
**Auditor Comment:** 大阪は日本第2の都市圏。DB 0件で「その他の地域」扱いは事業上の致命的欠陥。

---

### Case W5-002
- **Prefecture:** 京都府 / **Region Block:** 関西 / **Case Type:** 標準 / **User Profile:** 35歳女性、大学病院ICU 10年、専門看護師 / **Entry Route:** Google検索→LP→LINE / **Difficulty:** 低
**Scenario:**
京都市内の大学病院ICUでキャリアを積んだベテラン。京都府内でスキルを活かせる転職先を探している。
**Conversation Flow:**
1. User: LINE友達追加
2. Bot: ウェルカムメッセージ
3. User: 「求人を見る」タップ
4. Bot: エリア選択 Quick Reply表示
5. User: 「その他の地域」タップ
6. Bot: 「その他の地域ですね！ 候補: X件」→ 施設タイプ選択
7. User: 「急性期病院」→「救急」→「日勤・夜勤両方」→「すぐにでも」
8. Bot: matching_preview → 関東の急性期病院を表示
**System Behavior Evaluation:**
- 京都の大学病院ICU経験者に横浜・川崎の病院を提案
- 専門看護師という高スキル人材の期待値と提案内容の乖離が大きい
- 「その他の地域」というラベル自体が京都在住者にとって侮辱的
**Results:** Drop-off: 高い / Job Proposal: 関東のみ / Next Action: 即離脱 / Region Bias: 関東限定 / National Expansion Risk: 高スキル人材の取りこぼし
**Failure Category:** GEO_LOCK + JOB_MATCH_FAIL
**Severity:** Critical
**Fix Proposal:** エリア外ユーザーに対して「京都府は準備中です。関東エリアの求人をご覧になりますか？それとも準備ができたらお知らせしましょうか？」の分岐を追加
**Retry Needed:** Yes
**Auditor Comment:** 高スキル人材ほど期待値が高く、ミスマッチ時の離脱・悪評リスクが大きい。

---

### Case W5-003
- **Prefecture:** 兵庫県 / **Region Block:** 関西 / **Case Type:** 標準 / **User Profile:** 32歳女性、総合病院外科3年、子育て中（時短希望） / **Entry Route:** TikTok→プロフィールリンク→LINE / **Difficulty:** 低
**Scenario:**
神戸市在住。子どもの保育園の関係で神戸市内もしくは明石市周辺でパート勤務を探している。
**Conversation Flow:**
1. User: LINE友達追加
2. Bot: ウェルカムメッセージ
3. User: 「求人を見る」タップ
4. Bot: エリア選択
5. User: 「神戸で働きたいんですけど」と自由テキスト
6. Bot: Quick Reply再表示（自由テキスト→再表示）
7. User: 「その他の地域」タップ
8. Bot: 施設タイプ選択へ
9. User: 「クリニック」→ 温度感「3ヶ月以内」
10. Bot: matching_preview → 関東のクリニックを表示
**System Behavior Evaluation:**
- 「神戸で働きたい」という明確な地域希望が無視される
- 時短・パート希望の子育て看護師に関東の求人提示は論外
- 通勤圏の制約が最も強いユーザー層に対して最もミスマッチな結果
**Results:** Drop-off: 即離脱 / Job Proposal: 関東のみ / Next Action: ブロック / Region Bias: 関東限定 / National Expansion Risk: 致命的
**Failure Category:** GEO_LOCK + AMBIG_FAIL
**Severity:** Critical
**Fix Proposal:** 自由テキストで地名検出→「神戸エリアは現在準備中です」と正直に伝える。ウェイトリスト登録→エリア拡大時に通知
**Retry Needed:** Yes
**Auditor Comment:** 子育て中の時短希望者は通勤圏が最重要。関東提案は完全に無意味。

---

### Case W5-004
- **Prefecture:** 滋賀県 / **Region Block:** 関西 / **Case Type:** 標準 / **User Profile:** 26歳女性、回復期リハ病院2年目 / **Entry Route:** Instagram広告→LINE / **Difficulty:** 低
**Scenario:**
大津市在住。京都駅まで電車20分の立地を活かし、滋賀か京都で回復期病院を探している。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「その他の地域」タップ
4. Bot: 「その他の地域ですね！ 候補: X件」→ 施設タイプ
5. User: 「回復期病院」→「リハビリ」→「日勤のみ」→「3ヶ月以内」
6. Bot: matching_preview → 関東の回復期病院表示
**System Behavior Evaluation:**
- 滋賀・京都圏の希望に対して神奈川・東京の回復期病院を提案
- 「候補: X件」の数字が関東の件数であることをユーザーは知らない（期待値の裏切り）
- 滋賀県は関西でもDBが最も薄いエリアだが、そもそもDB自体が0件
**Results:** Drop-off: 高い / Job Proposal: 関東のみ / Next Action: 離脱 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK
**Severity:** Critical
**Fix Proposal:** 候補件数表示時に「関東エリアの求人です」と明記。エリア外は件数0と正直に表示
**Retry Needed:** Yes
**Auditor Comment:** 候補X件という数字表示が関東の数字であることを隠しているのは不誠実。

---

### Case W5-005
- **Prefecture:** 奈良県 / **Region Block:** 関西 / **Case Type:** 標準 / **User Profile:** 40歳女性、訪問看護5年、管理者経験あり / **Entry Route:** Google検索「奈良 看護師 転職」→LP→LINE / **Difficulty:** 低
**Scenario:**
奈良市在住。訪問看護ステーションの管理者として転職希望。奈良県内もしくは大阪東部で探している。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「その他の地域」タップ
4. Bot: 施設タイプ選択
5. User: 「訪問看護」→「日勤のみ」→「すぐにでも」
6. Bot: matching_preview → 関東の訪問看護ステーション表示
**System Behavior Evaluation:**
- 奈良からの検索流入に対して関東の訪問看護を提案
- SEO「神奈川ナース転職」で奈良からの流入は少ないはずだが、広告経由だと起こりうる
- 訪問看護は通勤圏が特に重要（訪問先への移動があるため）
**Results:** Drop-off: 即離脱 / Job Proposal: 関東のみ / Next Action: ブロック / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + JOB_MATCH_FAIL
**Severity:** Critical
**Fix Proposal:** 訪問看護は特に通勤圏が重要。エリア外の場合は即座に「対応エリア外」と通知し、人間引き継ぎへ
**Retry Needed:** Yes
**Auditor Comment:** 訪問看護の管理者クラスは希少人材。取りこぼしの機会損失が大きい。

---

### Case W5-006
- **Prefecture:** 和歌山県 / **Region Block:** 関西 / **Case Type:** 標準 / **User Profile:** 24歳女性、新卒1年目、急性期病院 / **Entry Route:** TikTok→LINE / **Difficulty:** 低
**Scenario:**
和歌山市在住の新人看護師。1年目で転職を考えている。和歌山か大阪南部で探したい。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「その他の地域」タップ
4. Bot: 施設タイプ選択
5. User: 「急性期病院」→「外科系」→「日勤・夜勤両方」→「情報収集中」
6. Bot: matching_preview → 関東の急性期病院表示
**System Behavior Evaluation:**
- 和歌山の新人看護師に関東の病院を提案
- 「情報収集中」の温度感ユーザーに対してミスマッチな提案は即離脱の原因
- 新卒1年目は転職サポートが特に必要な層だが、地域外で放置される
**Results:** Drop-off: 高い / Job Proposal: 関東のみ / Next Action: 離脱 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK
**Severity:** High
**Fix Proposal:** 温度感「情報収集中」のエリア外ユーザーはナーチャリングリストに登録し、エリア拡大時に再アプローチ
**Retry Needed:** Yes
**Auditor Comment:** 若手は将来の引越し可能性もある。ナーチャリングで関東提案の余地あり。

---

### Case W5-007
- **Prefecture:** 大阪府 / **Region Block:** 関西 / **Case Type:** 標準 / **User Profile:** 30歳男性、救急看護師5年 / **Entry Route:** Instagram広告→LINE / **Difficulty:** 低
**Scenario:**
大阪市内の三次救急で5年勤務。バーンアウト気味で環境を変えたい。大阪府内で二次救急を探している。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「大阪の病院探してるんですけど」と自由テキスト
4. Bot: Quick Reply再表示「ボタンをタップしてください」
5. User: 「え、大阪ないの？」と自由テキスト
6. Bot: Quick Reply再表示（2回目）
7. User: 「その他の地域」タップ（しぶしぶ）
8. Bot: 施設タイプ選択
9. User: 離脱
**System Behavior Evaluation:**
- 「大阪の病院探してるんですけど」という自然な入力が2回無視される
- ユーザーの不信感が2回のQuick Reply再表示で急上昇
- 「え、大阪ないの？」という疑問に対してボットが説明せず機械的に再表示
**Results:** Drop-off: ステップ9で離脱 / Job Proposal: なし / Next Action: ブロック / Region Bias: 関東限定 / National Expansion Risk: 致命的
**Failure Category:** GEO_LOCK + AMBIG_FAIL + UX_DROP
**Severity:** Critical
**Fix Proposal:** 自由テキスト「大阪」検出時に「申し訳ございません、現在は関東エリア（東京・神奈川・千葉・埼玉）の求人を取り扱っております。大阪エリアは準備中です。」と正直に返答
**Retry Needed:** Yes
**Auditor Comment:** 自由テキストで地名を2回入力しても無視されるのは最悪のUX。

---

### Case W5-008
- **Prefecture:** 京都府 / **Region Block:** 関西 / **Case Type:** 標準 / **User Profile:** 45歳女性、慢性期病院15年、主任 / **Entry Route:** 知人紹介→LINE / **Difficulty:** 低
**Scenario:**
京都市伏見区在住。長年勤めた病院の経営悪化で転職を検討。京都南部か大阪北部で慢性期病院を探している。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「その他の地域」タップ
4. Bot: 施設タイプ選択
5. User: 「慢性期病院」→「内科系」→「日勤のみ」→「すぐにでも」
6. Bot: matching_preview → 関東の慢性期病院表示
7. User: 「京都の病院はないんですか？」自由テキスト
8. Bot: Quick Reply再表示（matching_preview中の自由テキスト）
**System Behavior Evaluation:**
- 経営悪化による緊急転職ニーズに対して無関係な関東の施設を提示
- matching_preview表示後に「京都の病院はないんですか？」と聞いても回答なし
- 「すぐにでも」の緊急度の高いユーザーを逃している
**Results:** Drop-off: 高い / Job Proposal: 関東のみ / Next Action: 離脱+他社利用 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + UX_DROP
**Severity:** Critical
**Fix Proposal:** matching_preview後の自由テキストで地名が含まれる場合、「現在{地名}エリアは準備中です」と回答+人間引き継ぎ提案
**Retry Needed:** Yes
**Auditor Comment:** 緊急度の高いユーザーの離脱は即座に他社流出を意味する。

---

### Case W5-009
- **Prefecture:** 兵庫県 / **Region Block:** 関西 / **Case Type:** 標準 / **User Profile:** 29歳女性、産婦人科クリニック4年 / **Entry Route:** Instagram→LINE / **Difficulty:** 低
**Scenario:**
西宮市在住。産婦人科経験を活かして兵庫県内の総合病院産科に転職希望。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「その他の地域」タップ
4. Bot: 施設タイプ選択
5. User: 「急性期病院」→「産婦人科」→「日勤・夜勤両方」→「3ヶ月以内」
6. Bot: matching_preview → 関東の病院表示（産婦人科フィルタ）
**System Behavior Evaluation:**
- 産婦人科という専門性の高い希望に対して関東のランダムな病院を提示
- 産婦人科は施設ごとの特色が大きく、地域外の提案は特に無意味
- 西宮→関東は通勤不可能
**Results:** Drop-off: 高い / Job Proposal: 関東のみ / Next Action: 離脱 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + JOB_MATCH_FAIL
**Severity:** High
**Fix Proposal:** 専門科指定+エリア外の場合、「{科}の求人は{エリア}では準備中です。関東エリアに{科}のある病院がX件あります。ご興味ありますか？」と明示的に確認
**Retry Needed:** Yes
**Auditor Comment:** 専門科の希望が明確なユーザーほどミスマッチのダメージが大きい。

---

### Case W5-010
- **Prefecture:** 大阪府 / **Region Block:** 関西 / **Case Type:** 標準 / **User Profile:** 33歳女性、整形外科クリニック5年、Uターン検討中 / **Entry Route:** Google検索→LP→LINE / **Difficulty:** 中
**Scenario:**
東京で5年勤務後、実家のある大阪に戻ることを検討中。東京と大阪両方の求人を見たい。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「東京都」タップ
4. Bot: 「東京都ですね！」→ サブエリア選択（23区/多摩/どこでもOK）
5. User: 「23区」→「クリニック」→「日勤のみ」→「3ヶ月以内」
6. Bot: matching_preview → 東京23区のクリニック表示
7. User: 「条件を変える」タップ → intake_lightやり直し
8. Bot: エリア選択
9. User: 「その他の地域」タップ（大阪を見たい）
10. Bot: 施設タイプ選択 → 結果は関東施設のみ
**System Behavior Evaluation:**
- Uターン検討者の「東京も大阪も見たい」ニーズに対応不可
- 条件変更で「その他の地域」を選んでも関東施設が出るため、大阪の比較ができない
- 2回目のフローで期待が裏切られる落差が大きい
**Results:** Drop-off: 2回目のフローで離脱 / Job Proposal: 東京のみ / Next Action: 他社で大阪を検索 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + REGION_EXPANSION_FAIL
**Severity:** High
**Fix Proposal:** 条件変更時に「大阪の求人も見たい」等のニーズを拾い、エリア外の場合はウェイトリスト+東京の結果を維持
**Retry Needed:** Yes
**Auditor Comment:** Uターン・Iターン需要は今後の全国展開の先行指標。

---

### Case W5-011
- **Prefecture:** 兵庫県 / **Region Block:** 関西 / **Case Type:** 標準 / **User Profile:** 27歳女性、介護施設2年 / **Entry Route:** TikTok→LINE / **Difficulty:** 低
**Scenario:**
姫路市在住。介護施設から病院に転職したい。兵庫県西部で探している。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「その他の地域」タップ
4. Bot: 施設タイプ選択
5. User: 「急性期病院」→「整形外科」→「日勤・夜勤両方」→「3ヶ月以内」
6. Bot: matching_preview → 関東の病院表示
**System Behavior Evaluation:**
- 姫路（兵庫県西部）から関東への通勤は不可能
- 介護施設→病院というキャリアチェンジ希望は支援が必要な層
**Results:** Drop-off: 高い / Job Proposal: 関東のみ / Next Action: 離脱 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK
**Severity:** High
**Fix Proposal:** エリア外通知+キャリアチェンジ相談は人間引き継ぎ
**Retry Needed:** Yes
**Auditor Comment:** キャリアチェンジ希望者にはコンサルタント対応が最適。自動フローで逃すのは損失。

---

### Case W5-012
- **Prefecture:** 大阪府 / **Region Block:** 関西 / **Case Type:** 標準 / **User Profile:** 38歳女性、精神科病院8年 / **Entry Route:** Instagram広告→LINE / **Difficulty:** 低
**Scenario:**
堺市在住。精神科の経験を活かしつつ、大阪府内で訪問看護に転職したい。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「その他の地域」タップ
4. Bot: 施設タイプ選択
5. User: 「訪問看護」→「日勤のみ」→「すぐにでも」
6. Bot: matching_preview → 関東の訪問看護表示
**System Behavior Evaluation:**
- 精神科→訪問看護という専門的なキャリアパス希望が完全に無視される
- 訪問看護は地域密着型で、関東の提案は無意味
**Results:** Drop-off: 即離脱 / Job Proposal: 関東のみ / Next Action: 他社利用 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + JOB_MATCH_FAIL
**Severity:** High
**Fix Proposal:** 訪問看護+エリア外の場合、ハローワーク求人APIの該当エリア情報を参考提示する選択肢を追加
**Retry Needed:** Yes
**Auditor Comment:** ハローワークAPIに大阪の訪問看護データがあるなら参考表示の余地あり。

---

### Case W5-013
- **Prefecture:** 京都府 / **Region Block:** 関西 / **Case Type:** 標準 / **User Profile:** 31歳男性、オペ室5年 / **Entry Route:** Google検索→LINE / **Difficulty:** 低
**Scenario:**
京都市左京区在住。オペ室経験を活かして京都府内の大きな病院で働きたい。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「その他の地域」タップ
4. Bot: 施設タイプ選択
5. User: 「急性期病院」→「外科系」→「日勤・夜勤両方」→「すぐにでも」
6. Bot: matching_preview → 関東の病院表示
**System Behavior Evaluation:**
- オペ室経験者は希少人材。京都の大病院を希望しているが関東のみ提示
- 手術室看護師の転職は施設見学が重要で、遠方提案は非現実的
**Results:** Drop-off: 高い / Job Proposal: 関東のみ / Next Action: 離脱 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK
**Severity:** High
**Fix Proposal:** 希少スキル（オペ室・ICU・NICU等）のエリア外ユーザーは自動で人間引き継ぎ
**Retry Needed:** Yes
**Auditor Comment:** 手術室看護師は人材紹介で最も単価が高い層の一つ。逃すのは大きな機会損失。

---

### Case W5-014
- **Prefecture:** 兵庫県 / **Region Block:** 関西 / **Case Type:** 標準 / **User Profile:** 50歳女性、看護部長経験あり / **Entry Route:** 知人紹介→LINE / **Difficulty:** 低
**Scenario:**
宝塚市在住。看護部長を退任し、小規模クリニックでゆっくり働きたい。兵庫か大阪で探している。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「その他の地域」タップ
4. Bot: 施設タイプ選択
5. User: 「クリニック」→ 温度感「情報収集中」
6. Bot: matching_preview → 関東のクリニック表示
**System Behavior Evaluation:**
- 看護部長経験者に関東のクリニックを提案。経歴に見合わない対応
- 知人紹介の場合、紹介者の信頼も損なう
**Results:** Drop-off: 即離脱 / Job Proposal: 関東のみ / Next Action: 離脱+知人にネガティブ報告 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + HUMAN_HANDOFF_FAIL
**Severity:** High
**Fix Proposal:** 管理職経験者は即人間引き継ぎ。エリア外でも紹介元との関係維持のためフォロー必須
**Retry Needed:** Yes
**Auditor Comment:** 知人紹介経由の離脱は口コミでのマイナス波及効果がある。

---

### Case W5-015
- **Prefecture:** 滋賀県 / **Region Block:** 関西 / **Case Type:** 標準 / **User Profile:** 28歳女性、小児科病棟3年 / **Entry Route:** Instagram→LINE / **Difficulty:** 低
**Scenario:**
草津市在住。小児科経験を活かして滋賀か京都の小児科クリニックで働きたい。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「その他の地域」タップ
4. Bot: 施設タイプ選択
5. User: 「クリニック」→ 温度感「3ヶ月以内」
6. Bot: matching_preview → 関東のクリニック表示
**System Behavior Evaluation:**
- 小児科希望が施設タイプ「クリニック」に集約され、専門科情報が失われる
- クリニック選択時はil_departmentがスキップされるため、小児科希望が記録されない
**Results:** Drop-off: 高い / Job Proposal: 関東のみ（小児科フィルタなし） / Next Action: 離脱 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + INPUT_LOCK
**Severity:** High
**Fix Proposal:** クリニック選択時も簡易的な診療科希望を聞く。エリア外は通知
**Retry Needed:** Yes
**Auditor Comment:** クリニック選択時にil_departmentスキップは設計上の問題。小児科・皮膚科等の専門希望が消える。

---

### Case W5-016
- **Prefecture:** 大阪府 / **Region Block:** 関西 / **Case Type:** 標準 / **User Profile:** 36歳女性、透析クリニック7年 / **Entry Route:** Google検索→LP→LINE / **Difficulty:** 低
**Scenario:**
豊中市在住。透析看護の経験を活かしたい。大阪北部で透析クリニックを探している。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「その他の地域」タップ
4. Bot: 施設タイプ選択
5. User: 「クリニック」→ 温度感「すぐにでも」
6. Bot: matching_preview → 関東のクリニック表示
**System Behavior Evaluation:**
- 透析クリニックという高度専門ニーズが拾えない（施設タイプにない）
- 大阪の透析クリニック需要は高いが、DB 0件
**Results:** Drop-off: 高い / Job Proposal: 関東のみ / Next Action: 他社利用 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + JOB_MATCH_FAIL
**Severity:** High
**Fix Proposal:** 施設タイプに「透析クリニック」を追加。エリア外は人間引き継ぎ
**Retry Needed:** Yes
**Auditor Comment:** 透析は専門人材の需要が極めて高い分野。

---

### Case W5-017
- **Prefecture:** 和歌山県 / **Region Block:** 関西 / **Case Type:** 標準 / **User Profile:** 42歳女性、訪問看護管理者 / **Entry Route:** 紹介→LINE / **Difficulty:** 低
**Scenario:**
田辺市在住。過疎地域の訪問看護に限界を感じ、和歌山市内か大阪南部への転職を検討。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「その他の地域」タップ
4. Bot: 施設タイプ選択
5. User: 「訪問看護」→「日勤のみ」→「3ヶ月以内」
6. Bot: matching_preview → 関東の訪問看護表示
**System Behavior Evaluation:**
- 過疎地域→都市部への転職希望だが、関東は遠すぎる
- 和歌山南部の看護師は特に情報弱者で、LINEでの転職相談に期待が大きい
**Results:** Drop-off: 高い / Job Proposal: 関東のみ / Next Action: 離脱 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK
**Severity:** High
**Fix Proposal:** 過疎地域からのアクセスは人間引き継ぎ優先。地域の転職事情に詳しいコンサルタントが対応すべき
**Retry Needed:** Yes
**Auditor Comment:** 地方在住者ほどオンライン転職支援への期待値が高い。

---

### Case W5-018
- **Prefecture:** 奈良県 / **Region Block:** 関西 / **Case Type:** 標準 / **User Profile:** 25歳女性、急性期病院2年目、夜勤がつらい / **Entry Route:** TikTok→LINE / **Difficulty:** 低
**Scenario:**
生駒市在住。大阪市内の病院に通勤中だが、夜勤がきつくて日勤のみの職場を探している。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「その他の地域」タップ
4. Bot: 施設タイプ選択
5. User: 「クリニック」→ 温度感「すぐにでも」
6. Bot: matching_preview → 関東のクリニック表示
**System Behavior Evaluation:**
- 夜勤→日勤シフトという切実なニーズに対して無関係な地域を提案
- 生駒→大阪のように県境通勤は関西では一般的だが、システムは対応不可
**Results:** Drop-off: 高い / Job Proposal: 関東のみ / Next Action: 離脱 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK
**Severity:** High
**Fix Proposal:** 県境通勤パターン（奈良↔大阪、滋賀↔京都等）の理解をシステムに組み込む
**Retry Needed:** Yes
**Auditor Comment:** 関西の県境通勤は極めて一般的。1県だけでなく通勤圏で考える必要あり。

---

### Case W5-019
- **Prefecture:** 大阪府 / **Region Block:** 関西 / **Case Type:** 標準 / **User Profile:** 34歳女性、NICU 6年 / **Entry Route:** Instagram広告→LINE / **Difficulty:** 低
**Scenario:**
吹田市在住。NICU経験を活かして大阪府内の周産期センターで働きたい。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「その他の地域」タップ
4. Bot: 施設タイプ選択
5. User: 「急性期病院」→「小児科」→「日勤・夜勤両方」→「すぐにでも」
6. Bot: matching_preview → 関東の病院表示
**System Behavior Evaluation:**
- NICU/周産期センターという超専門ニーズに対して一般的な急性期病院を提示
- 小児科フィルタはあるがNICU特化ではない
- 大阪のNICU求人は需要が高いが対応不可
**Results:** Drop-off: 即離脱 / Job Proposal: 関東のみ / Next Action: 専門エージェント利用 / Region Bias: 関東限定 / National Expansion Risk: 致命的
**Failure Category:** GEO_LOCK + JOB_MATCH_FAIL
**Severity:** Critical
**Fix Proposal:** NICU/SCU等の超専門ニーズは自動マッチング不可。即座に人間引き継ぎ
**Retry Needed:** Yes
**Auditor Comment:** NICU看護師は紹介手数料が最高クラス。絶対に逃してはいけない。

---

### Case W5-020
- **Prefecture:** 京都府 / **Region Block:** 関西 / **Case Type:** 標準 / **User Profile:** 37歳女性、回復期リハ病院6年、理学療法士との連携経験豊富 / **Entry Route:** Google検索→LINE / **Difficulty:** 低
**Scenario:**
宇治市在住。回復期リハビリテーション病院で勤務中。京都南部か大阪で同様の環境を希望。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「その他の地域」タップ
4. Bot: 施設タイプ選択
5. User: 「回復期病院」→「リハビリ」→「日勤のみ」→「情報収集中」
6. Bot: matching_preview → 関東の回復期病院表示
**System Behavior Evaluation:**
- 回復期+リハビリという明確な希望に対して関東の施設を提示
- 宇治→関東は非現実的
**Results:** Drop-off: 高い / Job Proposal: 関東のみ / Next Action: 離脱 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK
**Severity:** High
**Fix Proposal:** エリア外+情報収集中のユーザーはメルマガ登録的なナーチャリング導線へ
**Retry Needed:** Yes
**Auditor Comment:** 「情報収集中」のユーザーは温度感が低いからこそ、長期ナーチャリングの対象として価値がある。

---

### Case W5-021
- **Prefecture:** 兵庫県 / **Region Block:** 関西 / **Case Type:** 標準 / **User Profile:** 23歳女性、急性期病院1年目（第二新卒） / **Entry Route:** TikTok→LINE / **Difficulty:** 低
**Scenario:**
尼崎市在住。新卒で入った病院が合わず、3ヶ月で退職。次は兵庫か大阪で慢性期か回復期を希望。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「その他の地域」タップ
4. Bot: 施設タイプ選択
5. User: 「回復期病院」→「こだわりなし」→「日勤・夜勤両方」→「すぐにでも」
6. Bot: matching_preview → 関東の回復期病院表示
**System Behavior Evaluation:**
- 第二新卒は転職に不安を抱えている層。関東の知らない病院を提示されると不安が増大
- 尼崎→大阪は電車10分だが、関東は別世界
**Results:** Drop-off: 高い / Job Proposal: 関東のみ / Next Action: 離脱+不安増大 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK
**Severity:** High
**Fix Proposal:** 第二新卒・早期離職者は特にケアが必要。エリア外でも人間引き継ぎでキャリア相談を提供
**Retry Needed:** Yes
**Auditor Comment:** 早期離職者はメンタル面のケアも含めた対応が求められる。

---

### Case W5-022
- **Prefecture:** 大阪府 / **Region Block:** 関西 / **Case Type:** 標準 / **User Profile:** 44歳女性、美容クリニック10年 / **Entry Route:** Instagram→LINE / **Difficulty:** 中
**Scenario:**
大阪市中央区（心斎橋）の美容クリニック勤務。美容看護の経験を活かして別の美容クリニックに転職希望。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「その他の地域」タップ
4. Bot: 施設タイプ選択
5. User: 「クリニック」→ 温度感「3ヶ月以内」
6. Bot: matching_preview → 関東のクリニック表示
**System Behavior Evaluation:**
- 美容クリニックという専門ニーズが「クリニック」に丸められる
- 施設タイプに「美容クリニック」カテゴリがない
- 大阪心斎橋は美容クリニック激戦区で需要は高い
**Results:** Drop-off: 高い / Job Proposal: 関東のみ / Next Action: 美容専門エージェント利用 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + JOB_MATCH_FAIL
**Severity:** High
**Fix Proposal:** 美容クリニック需要は高いが手数料モデルが異なる可能性。まずは対応可否の判断が必要
**Retry Needed:** Yes
**Auditor Comment:** 美容看護は給与水準が高く、紹介手数料も高くなる傾向。

---

### Case W5-023
- **Prefecture:** 京都府 / **Region Block:** 関西 / **Case Type:** 標準 / **User Profile:** 29歳女性、循環器内科病棟4年 / **Entry Route:** LP→LINE / **Difficulty:** 低
**Scenario:**
京都市山科区在住。循環器の経験を活かして京都か滋賀でカテーテル室のある病院を希望。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「その他の地域」タップ
4. Bot: 施設タイプ選択
5. User: 「急性期病院」→「循環器」→「日勤・夜勤両方」→「3ヶ月以内」
6. Bot: matching_preview → 関東の病院表示
**System Behavior Evaluation:**
- 循環器+カテーテル室という専門希望を拾えない（カテーテル室はフィルタにない）
- 京都山科→滋賀は近距離だが、関東は対象外
**Results:** Drop-off: 高い / Job Proposal: 関東のみ / Next Action: 離脱 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK
**Severity:** High
**Fix Proposal:** 診療科選択後に「特に希望する部門はありますか？」（カテ室/オペ室/外来等）の追加質問
**Retry Needed:** Yes
**Auditor Comment:** 循環器+カテーテル室は高需要ポジション。

---

### Case W5-024
- **Prefecture:** 兵庫県 / **Region Block:** 関西 / **Case Type:** 標準 / **User Profile:** 39歳女性、介護老人保健施設8年 / **Entry Route:** 知人紹介→LINE / **Difficulty:** 低
**Scenario:**
明石市在住。老健から病院に戻りたい。兵庫県内で療養型か回復期を希望。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「その他の地域」タップ
4. Bot: 施設タイプ選択
5. User: 「介護施設」→「日勤のみ」→「情報収集中」
6. Bot: matching_preview → 関東の介護施設表示
**System Behavior Evaluation:**
- 介護施設から「病院に戻りたい」という希望だが、施設タイプで「介護施設」を選んでしまう矛盾
- ユーザーの真のニーズ（病院復帰）と選択（介護施設）のギャップをシステムが検知できない
**Results:** Drop-off: 高い / Job Proposal: 関東の介護施設（本人の希望と逆） / Next Action: 離脱 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + AMBIG_FAIL
**Severity:** High
**Fix Proposal:** 「現在の職場」と「希望の職場」を分けて聞く設計に変更
**Retry Needed:** Yes
**Auditor Comment:** 現職と希望職を混同する設計は根本的なUX問題。

---

### Case W5-025
- **Prefecture:** 滋賀県 / **Region Block:** 関西 / **Case Type:** 標準 / **User Profile:** 33歳女性、透析クリニック5年 / **Entry Route:** Instagram→LINE / **Difficulty:** 低
**Scenario:**
彦根市在住。透析看護の経験を活かして滋賀県内か京都で働きたい。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「その他の地域」タップ
4. Bot: 施設タイプ選択
5. User: 「クリニック」→ 温度感「3ヶ月以内」
6. Bot: matching_preview → 関東のクリニック表示
**System Behavior Evaluation:**
- 彦根→関東は非現実的
- 透析専門のフィルタがないため一般クリニックが提示される
**Results:** Drop-off: 高い / Job Proposal: 関東のみ / Next Action: 離脱 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK
**Severity:** High
**Fix Proposal:** 透析クリニックカテゴリ追加+エリア外通知
**Retry Needed:** Yes
**Auditor Comment:** 透析は全国的に人手不足。専門カテゴリの追加は優先度高。

---

### Case W5-026
- **Prefecture:** 大阪府 / **Region Block:** 関西 / **Case Type:** 標準 / **User Profile:** 46歳女性、外来看護師15年 / **Entry Route:** Google検索→LINE / **Difficulty:** 低
**Scenario:**
東大阪市在住。外来勤務のみ希望。大阪府内のクリニックか病院外来で探している。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「その他の地域」タップ
4. Bot: 施設タイプ選択
5. User: 「クリニック」→ 温度感「すぐにでも」
6. Bot: matching_preview → 関東のクリニック表示
**System Behavior Evaluation:**
- 外来限定という勤務形態の希望がシステムに反映されない
- 働き方の選択肢は「日勤のみ/夜勤あり/パート」であって「外来のみ」ではない
**Results:** Drop-off: 高い / Job Proposal: 関東のみ / Next Action: 離脱 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + INPUT_LOCK
**Severity:** High
**Fix Proposal:** 働き方に「外来のみ」オプション追加。エリア外通知
**Retry Needed:** Yes
**Auditor Comment:** 外来のみ希望は中高年看護師に多い。重要なセグメント。

---

### Case W5-027
- **Prefecture:** 和歌山県 / **Region Block:** 関西 / **Case Type:** 標準 / **User Profile:** 30歳女性、急性期病院5年、引越し可能 / **Entry Route:** TikTok→LINE / **Difficulty:** 中
**Scenario:**
和歌山市在住だが、条件が良ければ関東への引越しも検討可能。まずは和歌山周辺を見て、なければ関東も。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「その他の地域」タップ
4. Bot: 施設タイプ選択
5. User: 「急性期病院」→「こだわりなし」→「日勤・夜勤両方」→「すぐにでも」
6. Bot: matching_preview → 関東の病院表示
7. User: 「あ、関東の病院なんですね。引越ししてもいいかも」
8. Bot: Quick Reply再表示（matching_preview中の自由テキスト）
**System Behavior Evaluation:**
- 珍しく関東提案が「引越し可能」ユーザーに刺さるケース
- しかし「引越ししてもいいかも」という前向きな反応がQuick Reply再表示で潰される
- ポジティブな自由テキストを拾えず、温度の高いリードを逃す
**Results:** Drop-off: 中 / Job Proposal: 関東施設表示済み / Next Action: Quick Replyに戻るか離脱 / Region Bias: 関東限定だが偶然マッチ / National Expansion Risk: 中
**Failure Category:** AMBIG_FAIL + UX_DROP
**Severity:** Medium
**Fix Proposal:** matching_preview中の前向きテキスト検出→「気になる求人はありますか？」と深掘り
**Retry Needed:** Yes
**Auditor Comment:** 引越し可能なユーザーは関西からでも成約可能性あり。自由テキストの感情分析が必要。

---

### Case W5-028
- **Prefecture:** 奈良県 / **Region Block:** 関西 / **Case Type:** 標準 / **User Profile:** 31歳女性、産科クリニック4年 / **Entry Route:** Instagram→LINE / **Difficulty:** 低
**Scenario:**
橿原市在住。産科の経験を活かして奈良県内か大阪南部で勤務希望。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「その他の地域」タップ
4. Bot: 施設タイプ選択
5. User: 「クリニック」→ 温度感「3ヶ月以内」
6. Bot: matching_preview → 関東のクリニック表示
**System Behavior Evaluation:**
- 産科クリニック専門希望が「クリニック」に丸められる
- 橿原→関東は非現実的
**Results:** Drop-off: 高い / Job Proposal: 関東のみ / Next Action: 離脱 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK
**Severity:** High
**Fix Proposal:** エリア外通知
**Retry Needed:** Yes
**Auditor Comment:** 産科は分娩施設の減少で全国的に人手不足。

---

### Case W5-029
- **Prefecture:** 滋賀県 / **Region Block:** 関西 / **Case Type:** 標準 / **User Profile:** 27歳男性、救急看護師3年 / **Entry Route:** TikTok→LINE / **Difficulty:** 低
**Scenario:**
大津市在住。救急から離れて訪問看護に挑戦したい。滋賀か京都で探している。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「その他の地域」タップ
4. Bot: 施設タイプ選択
5. User: 「訪問看護」→「日勤のみ」→「3ヶ月以内」
6. Bot: matching_preview → 関東の訪問看護表示
**System Behavior Evaluation:**
- 救急→訪問看護というキャリアチェンジ希望にアドバイスが必要だが自動フローのみ
- 滋賀の訪問看護は地域包括ケアの観点で需要が高い
**Results:** Drop-off: 高い / Job Proposal: 関東のみ / Next Action: 離脱 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK
**Severity:** High
**Fix Proposal:** キャリアチェンジ希望者は人間引き継ぎ推奨
**Retry Needed:** Yes
**Auditor Comment:** 男性看護師のキャリアチェンジは丁寧な対応が必要。

---

### Case W5-030
- **Prefecture:** 大阪府 / **Region Block:** 関西 / **Case Type:** 標準 / **User Profile:** 41歳女性、健診センター10年 / **Entry Route:** Google検索→LINE / **Difficulty:** 低
**Scenario:**
大阪市北区在住。健診センターの経験を活かして大阪市内で転職希望。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「その他の地域」タップ
4. Bot: 施設タイプ選択（急性期病院/回復期病院/慢性期病院/クリニック/訪問看護/介護施設/こだわりなし）
5. User: 「こだわりなし」→「日勤のみ」→「すぐにでも」
6. Bot: matching_preview → 関東の施設表示
**System Behavior Evaluation:**
- 健診センターが施設タイプ選択肢にない
- 「こだわりなし」を選ばざるを得ないが、本当は健診センター希望
- 大阪市北区は関西最大のビジネス街で健診センターが多数ある
**Results:** Drop-off: 高い / Job Proposal: 関東のみ / Next Action: 離脱 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + INPUT_LOCK
**Severity:** High
**Fix Proposal:** 施設タイプに「健診センター」「企業内診療所」等を追加
**Retry Needed:** Yes
**Auditor Comment:** 健診センターは日勤のみで人気が高い。施設タイプの追加を推奨。

---

## 境界ケース（12件）

### Case W5-031
- **Prefecture:** 大阪府 / **Region Block:** 関西 / **Case Type:** 境界 / **User Profile:** 30歳女性、急性期病院5年、東京に引越し予定 / **Entry Route:** Instagram→LINE / **Difficulty:** 中
**Scenario:**
大阪在住だが、夫の転勤で3ヶ月後に東京に引越し確定。東京の病院を事前に探したい。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「東京都」タップ
4. Bot: 「東京都ですね！」→ サブエリア選択
5. User: 「23区」→「急性期病院」→「内科系」→「日勤・夜勤両方」→「3ヶ月以内」
6. Bot: matching_preview → 東京23区の病院表示
7. User: 「この求人が気になる」タップ
8. Bot: 詳細ヒアリングへ
**System Behavior Evaluation:**
- 関西在住だが東京を希望→正常に機能するレアケース
- 引越し前の転職活動というニーズに対してBotは問題なく動作
- ただし「引越し3ヶ月後」という時期情報はシステムに反映されない
**Results:** Drop-off: 低い / Job Proposal: 東京23区の病院（適切） / Next Action: 詳細ヒアリング / Region Bias: 東京選択で正常 / National Expansion Risk: なし
**Failure Category:** なし（正常動作）
**Severity:** Low
**Fix Proposal:** 入職希望時期のフィールドを追加（「すぐにでも」「3ヶ月以内」だけでは不十分）
**Retry Needed:** No
**Auditor Comment:** 関西→関東の引越し転職は正常動作するが、逆（関東→関西）は不可能という非対称性。

---

### Case W5-032
- **Prefecture:** 兵庫県 / **Region Block:** 関西 / **Case Type:** 境界 / **User Profile:** 28歳女性、急性期3年、関東か関西で迷い中 / **Entry Route:** TikTok→LINE / **Difficulty:** 高
**Scenario:**
三田市在住。彼氏が東京にいるため東京への引越しも考えているが、実家（兵庫）の近くも捨てがたい。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「東京と兵庫で迷ってるんですけど」自由テキスト
4. Bot: Quick Reply再表示
5. User: 「東京都」タップ（まず東京を見る）
6. Bot: サブエリア → 施設タイプ → 診療科 → 働き方 → 温度感
7. Bot: matching_preview → 東京の病院表示
8. User: 「条件を変える」タップ
9. Bot: エリア選択に戻る
10. User: 「その他の地域」タップ（兵庫を見たい）→ 関東の施設が出る
**System Behavior Evaluation:**
- 「東京と兵庫で迷っている」という自由テキストが無視される
- 条件変更で「その他の地域」を選んでも兵庫の施設は出ない
- 2地域比較のニーズに完全に対応不可
**Results:** Drop-off: 2回目のフローで離脱 / Job Proposal: 東京のみ / Next Action: 兵庫の求人が見られず離脱 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + AMBIG_FAIL + REGION_EXPANSION_FAIL
**Severity:** Critical
**Fix Proposal:** (1) 複数エリア比較機能 (2) エリア外は正直に「兵庫は準備中」と伝える (3) 自由テキストで地名2つ検出→比較ニーズを把握
**Retry Needed:** Yes
**Auditor Comment:** 遠距離恋愛による2地域検討は実際に多いパターン。

---

### Case W5-033
- **Prefecture:** 京都府 / **Region Block:** 関西 / **Case Type:** 境界 / **User Profile:** 35歳女性、英語堪能、外国人患者対応経験あり / **Entry Route:** Google検索→LINE / **Difficulty:** 高
**Scenario:**
京都市東山区在住。外国人観光客の多い京都で英語対応の看護経験を活かしたい。東京のインターナショナルクリニックも視野に入れている。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「京都か東京で英語が使える病院を探してます」自由テキスト
4. Bot: Quick Reply再表示
5. User: 「東京都」タップ
6. Bot: サブエリア → 「23区」→「クリニック」→ 温度感「情報収集中」
7. Bot: matching_preview → 東京のクリニック表示（英語対応フィルタなし）
**System Behavior Evaluation:**
- 「英語が使える病院」という条件はシステムに存在しない
- 京都のインバウンド需要に対応する求人はDB 0件
- 東京のクリニックは表示されるが英語対応のフィルタがない
**Results:** Drop-off: 中 / Job Proposal: 東京クリニック（英語フィルタなし） / Next Action: 興味がなければ離脱 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + INPUT_LOCK + JOB_MATCH_FAIL
**Severity:** High
**Fix Proposal:** (1) 言語スキルフィルタ追加 (2) 京都エリア対応 (3) 特殊スキル検出→人間引き継ぎ
**Retry Needed:** Yes
**Auditor Comment:** 英語対応看護師はインバウンド需要で今後さらに重要になる。

---

### Case W5-034
- **Prefecture:** 大阪府 / **Region Block:** 関西 / **Case Type:** 境界 / **User Profile:** 26歳女性、1年ブランク（メンタル離職） / **Entry Route:** Instagram→LINE / **Difficulty:** 高
**Scenario:**
大阪市住吉区在住。メンタル不調で1年休職後に退職。復職に不安があり、まずは情報収集から。
**Conversation Flow:**
1. User: LINE友達追加
2. Bot: ウェルカムメッセージ
3. User: 「ブランクがあるんですけど大丈夫ですか？」自由テキスト
4. Bot: Quick Reply再表示（welcomeフェーズの自由テキスト）
5. User: 「求人を見る」タップ
6. Bot: エリア選択
7. User: 「その他の地域」タップ
8. Bot: 施設タイプ選択
9. User: 「回復期病院」→「こだわりなし」→「パート」→「情報収集中」
10. Bot: matching_preview → 関東の回復期病院表示
**System Behavior Evaluation:**
- 「ブランクがあるんですけど大丈夫ですか？」という不安の声がQuick Reply再表示で無視される
- メンタル離職後の復職は最もデリケートな対応が必要な層
- 自動フローでの対応が不適切。人間が対応すべき
**Results:** Drop-off: 「ブランク大丈夫？」の段階で不信感 / Job Proposal: 関東のみ / Next Action: 離脱+復職への不安増大 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + AMBIG_FAIL + HUMAN_HANDOFF_FAIL
**Severity:** Critical
**Fix Proposal:** (1) 「ブランク」「休職」「メンタル」等のキーワード検出→ 即人間引き継ぎ (2) Bot回答として「ブランクがあっても大丈夫です。一緒に探しましょう」の安心メッセージ
**Retry Needed:** Yes
**Auditor Comment:** メンタル離職者への対応は事業の信頼に直結する。ボットの冷たい対応は最悪。

---

### Case W5-035
- **Prefecture:** 兵庫県 / **Region Block:** 関西 / **Case Type:** 境界 / **User Profile:** 55歳女性、定年前の最後の転職 / **Entry Route:** 知人紹介→LINE / **Difficulty:** 高
**Scenario:**
芦屋市在住。60歳定年を見据えて、最後の職場を兵庫県内で探したい。慢性期かクリニック希望。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「兵庫県」自由テキスト
4. Bot: Quick Reply再表示
5. User: 「兵庫県がないの？神奈川の転職サービスなの？」自由テキスト
6. Bot: Quick Reply再表示（2回目）
7. User: 離脱
**System Behavior Evaluation:**
- 「神奈川の転職サービスなの？」という的確な指摘にBotが回答できない
- 年配ユーザーはQuick Replyの操作に不慣れな可能性もある
- 知人紹介経由での離脱は特にダメージが大きい
**Results:** Drop-off: ステップ7で離脱 / Job Proposal: なし / Next Action: ブロック+知人に報告 / Region Bias: 関東限定 / National Expansion Risk: 致命的
**Failure Category:** GEO_LOCK + UX_DROP + AMBIG_FAIL
**Severity:** Critical
**Fix Proposal:** (1) 自由テキスト「兵庫」検出→「関東エリア中心のサービスです。兵庫は準備中です」 (2) サービス説明を事前に明示
**Retry Needed:** Yes
**Auditor Comment:** サービスの対応エリアをウェルカムメッセージに明記すべき。

---

### Case W5-036
- **Prefecture:** 京都府 / **Region Block:** 関西 / **Case Type:** 境界 / **User Profile:** 32歳女性、LP内診断済みでLINE遷移 / **Entry Route:** LP診断→LINE引き継ぎ / **Difficulty:** 中
**Scenario:**
LP上でミニ診断を3問回答済み（エリア:その他/施設:クリニック/働き方:日勤のみ）。引き継ぎコードでLINE遷移。
**Conversation Flow:**
1. User: LP診断でエリア「その他」、施設「クリニック」、日勤のみを選択
2. User: 引き継ぎコード発行→LINE友達追加→コード入力
3. Bot: 診断結果引き継ぎ → intake_lightスキップ → 即matching_preview
4. Bot: matching_preview → 関東のクリニック表示
5. User: 「京都のクリニック探してたんですけど...」自由テキスト
6. Bot: Quick Reply再表示
**System Behavior Evaluation:**
- LP診断でも「その他」を選んだユーザーの引き継ぎが正常に動作するか確認
- LP→LINE引き継ぎで即matching_previewに飛ぶため、エリア外の説明が一切ない
- ユーザーは「京都のクリニック」が出ると期待してLINE登録した可能性
**Results:** Drop-off: 即離脱 / Job Proposal: 関東クリニック / Next Action: ブロック / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + UX_DROP + REENTRY_FAIL
**Severity:** Critical
**Fix Proposal:** LP診断で「その他」選択時にLP上で「現在は関東エリアの求人です」と明示。LINE引き継ぎ前にユーザーが理解できるようにする
**Retry Needed:** Yes
**Auditor Comment:** LP→LINE引き継ぎでの期待値ギャップは最悪のUX。LP側の改修が必須。

---

### Case W5-037
- **Prefecture:** 大阪府 / **Region Block:** 関西 / **Case Type:** 境界 / **User Profile:** 28歳女性、夜勤専従で稼ぎたい / **Entry Route:** TikTok→LINE / **Difficulty:** 中
**Scenario:**
大阪市城東区在住。夜勤専従で月収40万以上を狙いたい。大阪か神戸で探している。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「その他の地域」タップ
4. Bot: 施設タイプ選択
5. User: 「急性期病院」→「こだわりなし」→「夜勤あり」→「すぐにでも」
6. Bot: matching_preview → 関東の病院表示
7. User: 「夜勤専従で月40万以上ってありますか？」自由テキスト
8. Bot: Quick Reply再表示
**System Behavior Evaluation:**
- 「夜勤専従」は働き方「夜勤あり」とは異なるが区別がない
- 月収条件のフィルタがない
- 大阪・神戸の夜勤専従求人はDB 0件
- 給与条件の自由テキストが無視される
**Results:** Drop-off: 高い / Job Proposal: 関東のみ（夜勤専従フィルタなし） / Next Action: 離脱 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + INPUT_LOCK + AMBIG_FAIL
**Severity:** High
**Fix Proposal:** (1) 夜勤専従オプション追加 (2) 給与条件フィルタ (3) エリア外通知
**Retry Needed:** Yes
**Auditor Comment:** 夜勤専従は看護師転職の重要セグメント。フィルタなしは痛い。

---

### Case W5-038
- **Prefecture:** 奈良県 / **Region Block:** 関西 / **Case Type:** 境界 / **User Profile:** 22歳女性、新卒で就職先を探し中 / **Entry Route:** Instagram→LINE / **Difficulty:** 高
**Scenario:**
奈良市在住の看護学生。来春卒業予定。奈良か大阪で最初の就職先を探している。
**Conversation Flow:**
1. User: LINE友達追加
2. Bot: ウェルカムメッセージ
3. User: 「来年の4月から働ける病院を探してます。新卒です」自由テキスト
4. Bot: Quick Reply再表示
5. User: 「求人を見る」タップ
6. Bot: エリア選択
7. User: 「その他の地域」タップ
8. Bot: 施設タイプ選択
9. User: 「急性期病院」→「こだわりなし」→「日勤・夜勤両方」→「情報収集中」
10. Bot: matching_preview → 関東の病院表示
**System Behavior Evaluation:**
- 「新卒」キーワードの検出なし。新卒向けの対応フローがない
- 新卒採用は中途採用と選考プロセスが異なる
- 来年4月入職という時期情報がシステムに反映されない
- 奈良の新卒看護師に関東の病院を提示
**Results:** Drop-off: 高い / Job Proposal: 関東のみ（中途求人） / Next Action: 離脱→病院の採用サイト直接 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + INPUT_LOCK + JOB_MATCH_FAIL
**Severity:** High
**Fix Proposal:** (1) 新卒検出→「新卒採用は病院の採用サイトが最適です。中途採用のサポートを行っています」と案内 (2) エリア外通知
**Retry Needed:** Yes
**Auditor Comment:** 新卒は通常の人材紹介の対象外。早期に案内すべき。

---

### Case W5-039
- **Prefecture:** 和歌山県 / **Region Block:** 関西 / **Case Type:** 境界 / **User Profile:** 48歳女性、看護教員10年 / **Entry Route:** Google検索→LINE / **Difficulty:** 高
**Scenario:**
和歌山市在住。看護専門学校の教員を10年務めたが、臨床に戻りたい。和歌山か大阪で受け入れてくれる病院を探している。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「看護教員から臨床に戻りたいんですが」自由テキスト
4. Bot: Quick Reply再表示
5. User: 「その他の地域」タップ
6. Bot: 施設タイプ選択
7. User: 「回復期病院」→「こだわりなし」→「日勤のみ」→「3ヶ月以内」
8. Bot: matching_preview → 関東の回復期病院表示
**System Behavior Evaluation:**
- 「看護教員から臨床に戻りたい」というキャリア相談的な自由テキストが無視される
- 10年の臨床ブランクは大きなハードルで、人間の相談が必要
- 和歌山・大阪の病院はDB 0件
**Results:** Drop-off: 高い / Job Proposal: 関東のみ / Next Action: 離脱 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + AMBIG_FAIL + HUMAN_HANDOFF_FAIL
**Severity:** High
**Fix Proposal:** 長文の自由テキストや相談的な内容を検出→人間引き継ぎ
**Retry Needed:** Yes
**Auditor Comment:** 看護教員→臨床復帰は特殊なキャリアパス。自動マッチングでは対応不可。

---

### Case W5-040
- **Prefecture:** 滋賀県 / **Region Block:** 関西 / **Case Type:** 境界 / **User Profile:** 35歳女性、保健師資格あり / **Entry Route:** Instagram→LINE / **Difficulty:** 中
**Scenario:**
守山市在住。看護師+保健師のダブルライセンス。滋賀県内で保健師としての求人も視野に入れている。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「保健師の求人もありますか？」自由テキスト
4. Bot: Quick Reply再表示
5. User: 「その他の地域」タップ
6. Bot: 施設タイプ選択（看護師の施設タイプしかない）
7. User: 「こだわりなし」→「日勤のみ」→「情報収集中」
8. Bot: matching_preview → 関東の施設表示
**System Behavior Evaluation:**
- 保健師求人はシステムの対象外だが、それが伝わらない
- 「保健師の求人もありますか？」の質問がQuick Reply再表示で無視される
- 施設タイプに行政機関・企業等がなく、保健師の職場が選べない
**Results:** Drop-off: 高い / Job Proposal: 関東のみ（看護師求人） / Next Action: 離脱 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + INPUT_LOCK + JOB_MATCH_FAIL
**Severity:** High
**Fix Proposal:** 「保健師」「助産師」等の職種検出→「看護師求人のサービスです」と明示+保健師求人の紹介先案内
**Retry Needed:** Yes
**Auditor Comment:** 保健師求人は対象外なら早期に伝えるべき。

---

### Case W5-041
- **Prefecture:** 兵庫県 / **Region Block:** 関西 / **Case Type:** 境界 / **User Profile:** 29歳女性、離島・へき地医療経験あり / **Entry Route:** TikTok→LINE / **Difficulty:** 高
**Scenario:**
淡路島在住。島内での転職先が限られるため、神戸か大阪への通勤も検討中。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「淡路島なんですけど、神戸に通うのもありかなと」自由テキスト
4. Bot: Quick Reply再表示
5. User: 「その他の地域」タップ
6. Bot: 施設タイプ選択
7. User: 「急性期病院」→「こだわりなし」→「日勤・夜勤両方」→「3ヶ月以内」
8. Bot: matching_preview → 関東の病院表示
**System Behavior Evaluation:**
- 淡路島→神戸という独特の通勤パターンをシステムが理解できない
- 離島医療経験者は地域医療に貴重な人材
- 関東の病院を提示されても淡路島から通勤不可能
**Results:** Drop-off: 高い / Job Proposal: 関東のみ / Next Action: 離脱 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + AMBIG_FAIL
**Severity:** High
**Fix Proposal:** 離島・へき地キーワード検出→特別対応フロー。地域医療経験者は人材価値が高い
**Retry Needed:** Yes
**Auditor Comment:** 離島医療の経験は全国的に引く手あまた。

---

### Case W5-042
- **Prefecture:** 大阪府 / **Region Block:** 関西 / **Case Type:** 境界 / **User Profile:** 33歳女性、深夜3時にアクセス / **Entry Route:** Instagram→LINE / **Difficulty:** 中
**Scenario:**
大阪市旭区在住。夜勤の休憩中にLINE登録。深夜3時に求人を見たい。
**Conversation Flow:**
1. User: 深夜3:00にLINE友達追加
2. Bot: ウェルカムメッセージ（24時間対応）
3. User: 「求人を見る」タップ
4. Bot: エリア選択
5. User: 「その他の地域」タップ
6. Bot: 施設タイプ選択
7. User: 「クリニック」→ 温度感「すぐにでも」
8. Bot: matching_preview → 関東のクリニック表示
9. User: 「大阪のはないですか？」自由テキスト
10. Bot: Quick Reply再表示（深夜のため人間引き継ぎも不可）
**System Behavior Evaluation:**
- 深夜アクセスは夜勤看護師の典型的なパターン
- 24時間対応のBot がミスマッチな提案をして離脱させている
- 深夜は人間引き継ぎも不可能なため、Botの対応品質が特に重要
**Results:** Drop-off: 高い / Job Proposal: 関東のみ / Next Action: 離脱（翌日は忘れてる） / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + UX_DROP
**Severity:** High
**Fix Proposal:** 深夜アクセス+エリア外の場合、「翌朝に担当者からご連絡します」のメッセージでリード保持
**Retry Needed:** Yes
**Auditor Comment:** 夜勤中のスマホ操作は看護師転職の黄金時間。逃してはいけない。

---

## 攻撃的ケース（8件）

### Case W5-043
- **Prefecture:** 大阪府 / **Region Block:** 関西 / **Case Type:** 攻撃的 / **User Profile:** 不明（Bot探り） / **Entry Route:** 直接LINE追加 / **Difficulty:** 極高
**Scenario:**
競合の人材紹介会社がBotの動作を調査するために登録。システムの挙動を確認しようとしている。
**Conversation Flow:**
1. User: LINE友達追加
2. Bot: ウェルカムメッセージ
3. User: 「対応エリアを教えてください」自由テキスト
4. Bot: Quick Reply再表示
5. User: 「求人を見る」タップ
6. Bot: エリア選択
7. User: 「その他の地域」タップ → 全フロー完走
8. User: 「条件を変える」→ 「東京都」→ 全フロー完走
9. User: 「条件を変える」→ 「神奈川県」→ 全フロー完走
10. User: 全エリアの施設数を記録
**System Behavior Evaluation:**
- 「対応エリアを教えてください」という基本的な質問に回答できない
- 競合がシステムの弱点（関西未対応）を容易に発見可能
- 全エリアの施設数がUIに表示されるため、DB規模が筒抜け
**Results:** Drop-off: なし（完走） / Job Proposal: 各エリアの施設を確認 / Next Action: 競合分析に利用 / Region Bias: 関東限定が露呈 / National Expansion Risk: 競合に弱点を知られる
**Failure Category:** OTHER（セキュリティ/情報露出）
**Severity:** Medium
**Fix Proposal:** 施設数の具体的な数字を「多数」等に曖昧化。連続条件変更の検知+レート制限
**Retry Needed:** No
**Auditor Comment:** 候補数のリアルタイム表示は競合に情報を渡すリスクがある。

---

### Case W5-044
- **Prefecture:** 京都府 / **Region Block:** 関西 / **Case Type:** 攻撃的 / **User Profile:** 不明 / **Entry Route:** 直接LINE追加 / **Difficulty:** 極高
**Scenario:**
「大阪 看護師 転職」とGoogle検索して辿り着いたユーザー。怒りのメッセージを送信。
**Conversation Flow:**
1. User: LINE友達追加
2. Bot: ウェルカムメッセージ
3. User: 「大阪の求人って書いてあったから登録したのに神奈川の転職サービスじゃないですか。詐欺ですよね？」
4. Bot: Quick Reply再表示
5. User: 「返事しろよ。消費者センターに通報するぞ」
6. Bot: Quick Reply再表示
7. User: ブロック+通報
**System Behavior Evaluation:**
- 怒りのメッセージにBotが一切対応できない
- 「詐欺」「通報」等の深刻なキーワードを検知しない
- 広告やSEOで関西ユーザーを誘引している場合、景品表示法上の問題になりうる
**Results:** Drop-off: 即離脱+通報 / Job Proposal: なし / Next Action: 消費者センター通報 / Region Bias: 関東限定 / National Expansion Risk: 法的リスク
**Failure Category:** GEO_LOCK + HUMAN_HANDOFF_FAIL + OTHER（法的リスク）
**Severity:** Critical
**Fix Proposal:** (1) 「詐欺」「通報」「消費者センター」検出→即人間引き継ぎ (2) 広告・SEOで関西ユーザーを誘引していないか確認 (3) サービス対応エリアをLINEプロフィールに明記
**Retry Needed:** Yes
**Auditor Comment:** 法的リスクを含むクレームへのBot無応答は危険。即時の人間引き継ぎが必須。

---

### Case W5-045
- **Prefecture:** 大阪府 / **Region Block:** 関西 / **Case Type:** 攻撃的 / **User Profile:** 30歳女性、看護師（実在の可能性あり） / **Entry Route:** Meta広告→LINE / **Difficulty:** 極高
**Scenario:**
Meta広告が関西圏にも配信されている場合のケース。「AI転職」に興味を持ってLINE登録したが、大阪の求人がない。
**Conversation Flow:**
1. User: Meta広告「シン・AI転職」をタップ→LP→LINE登録
2. Bot: ウェルカムメッセージ
3. User: 「広告見て登録しました！大阪の看護師です。AIで求人探してください」
4. Bot: Quick Reply再表示
5. User: 「求人を見る」タップ
6. Bot: エリア選択（大阪なし）
7. User: 「あれ？大阪がない...」
8. User: 「その他の地域」タップ
9. Bot: matching_preview → 関東の施設表示
10. User: 「広告と違うじゃないですか。大阪の求人がないなんて一言も書いてなかった」
**System Behavior Evaluation:**
- Meta広告のターゲティングが関西を含んでいる場合、広告費の無駄+ユーザーの怒りを招く
- 「シン・AI転職」のブランドメッセージと実態（関東のみ）の乖離
- 広告→LP→LINE→エリアなしという最悪のファネル体験
**Results:** Drop-off: 即離脱+悪評 / Job Proposal: 関東のみ / Next Action: ブロック+SNSで悪評投稿 / Region Bias: 関東限定 / National Expansion Risk: 広告費の無駄+ブランド毀損
**Failure Category:** GEO_LOCK + REGION_EXPANSION_FAIL + OTHER（広告費の浪費）
**Severity:** Critical
**Fix Proposal:** (1) Meta広告の地域ターゲティングを関東限定に設定 (2) LP上に「対応エリア: 関東」を明記 (3) エリア外ユーザーへの正直な説明メッセージ
**Retry Needed:** Yes
**Auditor Comment:** 広告費をかけて関西ユーザーを呼び込み、がっかりさせるのは最悪のROI。

---

### Case W5-046
- **Prefecture:** 兵庫県 / **Region Block:** 関西 / **Case Type:** 攻撃的 / **User Profile:** 不明（スパム） / **Entry Route:** 直接LINE追加 / **Difficulty:** 極高
**Scenario:**
スパムアカウントが自動的にLINE友達追加し、無関係なメッセージを大量送信。
**Conversation Flow:**
1. User: LINE友達追加
2. Bot: ウェルカムメッセージ
3. User: 「副業で月100万稼げます！今すぐこちら→ https://scam-url.com」
4. Bot: Quick Reply再表示
5. User: 同じスパムメッセージを5回連続送信
6. Bot: Quick Reply再表示（毎回）→ unexpectedTextCountが5に到達
7. Bot: 人間引き継ぎ発動
**System Behavior Evaluation:**
- unexpectedTextCountが一定数で人間引き継ぎに遷移する設計は確認必要
- スパムURLの検出・ブロック機能があるか
- Slack通知がスパムで溢れるリスク
**Results:** Drop-off: N/A / Job Proposal: なし / Next Action: スパム処理 / Region Bias: N/A / National Expansion Risk: N/A
**Failure Category:** OTHER（スパム対策）
**Severity:** Medium
**Fix Proposal:** (1) URL含有メッセージの自動ブロック (2) スパム検知→人間引き継ぎではなく自動ブロック (3) Slack通知フィルタ
**Retry Needed:** No
**Auditor Comment:** スパムで人間引き継ぎが発動すると、Slack通知が汚染される。

---

### Case W5-047
- **Prefecture:** 大阪府 / **Region Block:** 関西 / **Case Type:** 攻撃的 / **User Profile:** 28歳女性（実在） / **Entry Route:** TikTok→LINE / **Difficulty:** 極高
**Scenario:**
大阪のTikTokフォロワーが「神奈川の転職サービスなのに全国向けに発信してるのはおかしい」とTikTokコメントで指摘した上でLINE登録して検証。
**Conversation Flow:**
1. User: LINE友達追加
2. Bot: ウェルカムメッセージ
3. User: 「TikTokで全国の看護師向けに発信してるのに、関東しか対応してないって本当ですか？」
4. Bot: Quick Reply再表示
5. User: 「求人を見る」タップ
6. Bot: エリア選択（東京/神奈川/千葉/埼玉/その他）
7. User: スクリーンショット撮影→TikTokに投稿「やっぱり関東だけだった」
8. User: ブロック
**System Behavior Evaluation:**
- SNS発信のリーチと実サービスのカバレッジのギャップが露呈
- TikTokコメント・投稿で悪評が拡散するリスク
- エリア選択画面のスクリーンショットが証拠として使われる
**Results:** Drop-off: 即離脱+SNS拡散 / Job Proposal: なし / Next Action: TikTokで暴露 / Region Bias: 関東限定が全国に露呈 / National Expansion Risk: ブランド毀損
**Failure Category:** GEO_LOCK + REGION_EXPANSION_FAIL + OTHER（SNSリスク）
**Severity:** Critical
**Fix Proposal:** (1) TikTok/Instagramで対応エリアを明記 (2) プロフィールに「関東エリアの看護師転職」と記載 (3) エリア拡大のロードマップを示す
**Retry Needed:** Yes
**Auditor Comment:** SNSの全国リーチとサービスの関東限定は根本的な矛盾。SNSプロフィールの修正が最優先。

---

### Case W5-048
- **Prefecture:** 京都府 / **Region Block:** 関西 / **Case Type:** 攻撃的 / **User Profile:** 不明（日本語が不自然） / **Entry Route:** 直接LINE追加 / **Difficulty:** 極高
**Scenario:**
外国人看護師（EPA等）が日本語で転職相談。京都の病院で働きたい。
**Conversation Flow:**
1. User: LINE友達追加
2. Bot: ウェルカムメッセージ
3. User: 「わたし フィリピン の かんごし です。きょうと で はたらきたい」
4. Bot: Quick Reply再表示
5. User: 「求人を見る」タップ
6. Bot: エリア選択
7. User: 「その他の地域」タップ
8. Bot: 施設タイプ選択
9. User: 「急性期病院」→「こだわりなし」→「日勤・夜勤両方」→「すぐにでも」
10. Bot: matching_preview → 関東の病院表示
**System Behavior Evaluation:**
- 外国人看護師への対応フローがない
- EPA看護師の在留資格・就労制限の確認が必要だがシステムにない
- 日本語の不自然さを検知する機能がない
- 京都エリアはDB 0件
**Results:** Drop-off: 高い / Job Proposal: 関東のみ / Next Action: 離脱 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + INPUT_LOCK + OTHER（外国人対応）
**Severity:** High
**Fix Proposal:** 外国人看護師キーワード検出→在留資格確認→人間引き継ぎ。簡易英語対応メッセージ
**Retry Needed:** Yes
**Auditor Comment:** EPA看護師の紹介は法的要件が複雑。自動フローでは対応不可。

---

### Case W5-049
- **Prefecture:** 大阪府 / **Region Block:** 関西 / **Case Type:** 攻撃的 / **User Profile:** 35歳女性 / **Entry Route:** Instagram→LINE / **Difficulty:** 極高
**Scenario:**
大阪在住の看護師が条件を何度も変更し、システムの限界をテスト。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」→ 「その他の地域」→ 全フロー完走
2. Bot: matching_preview → 関東施設表示
3. User: 「条件を変える」→ 「東京都」→「23区」→「急性期」→「外科」→「夜勤あり」→「すぐ」
4. Bot: matching_preview
5. User: 「条件を変える」→ 「神奈川県」→「横浜・川崎」→ 全フロー
6. Bot: matching_preview
7. User: 「条件を変える」→ 「千葉県」→ 全フロー
8. Bot: matching_preview
9. User: 「条件を変える」→ 「埼玉県」→ 全フロー
10. Bot: matching_preview → 同じ施設が繰り返し出る
**System Behavior Evaluation:**
- 条件変更を5回繰り返した場合のシステム挙動
- matchingResultsのリセットが正しく行われるか
- 同じ施設が何度も表示される可能性
- KV/D1のクエリ負荷
**Results:** Drop-off: 5回目で離脱 / Job Proposal: 各エリアの施設を表示（繰り返しあり） / Next Action: 離脱 / Region Bias: 関東のみ確認 / National Expansion Risk: 中
**Failure Category:** UX_DROP + OTHER（パフォーマンス）
**Severity:** Medium
**Fix Proposal:** 条件変更回数のトラッキング。3回以上で「お探しの条件が見つかりにくいようですね。直接ご相談しませんか？」→ 人間引き継ぎ
**Retry Needed:** No
**Auditor Comment:** 過度な条件変更はユーザーの迷いの表れ。人間対応に切り替えるべき。

---

### Case W5-050
- **Prefecture:** 兵庫県 / **Region Block:** 関西 / **Case Type:** 攻撃的 / **User Profile:** 30歳女性 / **Entry Route:** LINE→離脱→1ヶ月後に再アクセス / **Difficulty:** 高
**Scenario:**
1ヶ月前に「その他の地域」→関東施設表示→離脱した兵庫県のユーザーが再アクセス。エリアが拡大されたか確認しに来た。
**Conversation Flow:**
1. User: 1ヶ月ぶりにLINEトーク画面を開く
2. User: 「求人を見る」タップ（前回のセッションが残っている？）
3. Bot: エリア選択（前回と同じ：東京/神奈川/千葉/埼玉/その他）
4. User: 「まだ兵庫ないんですか...」
5. Bot: Quick Reply再表示
6. User: ブロック
**System Behavior Evaluation:**
- 再訪ユーザーの検知ができるか（KVにセッション残存？）
- 1ヶ月経過しても対応エリアが変わっていない場合のユーザー体験
- 再訪ユーザーへの特別対応（「お久しぶりです」等）があるか
- nurture_warmからの復帰パスが機能するか
**Results:** Drop-off: 即ブロック / Job Proposal: なし / Next Action: 永久離脱 / Region Bias: 関東限定 / National Expansion Risk: 再訪ユーザーを完全に失う
**Failure Category:** GEO_LOCK + REENTRY_FAIL + UX_DROP
**Severity:** High
**Fix Proposal:** (1) 再訪ユーザー検知→「前回ご利用ありがとうございました」 (2) エリア外で離脱した履歴がある場合→「{エリア}は引き続き準備中です。ご登録いただければ拡大時にお知らせします」 (3) ウェイトリスト機能
**Retry Needed:** Yes
**Auditor Comment:** 再訪ユーザーは興味が持続している貴重なリード。2回目の離脱は永久に戻ってこない。

---

## クロスリージョンケース（10件）

### Case W5-C01
- **Prefecture:** 東京都 / **Region Block:** 関東 / **Case Type:** クロス / **User Profile:** 32歳女性、急性期病院5年、大阪から上京予定 / **Entry Route:** Instagram→LINE / **Difficulty:** 中
**Scenario:**
大阪から東京への転職。関西出身者が関東の病院を探すケース。正常フローで動作確認。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「東京都」タップ
4. Bot: サブエリア選択 → 「23区」
5. User: 「急性期病院」→「循環器」→「日勤・夜勤両方」→「すぐにでも」
6. Bot: matching_preview → 東京23区の病院表示
**System Behavior Evaluation:**
- 関西出身者が東京を選択→正常に動作
- 東京の施設が適切に表示される
**Results:** Drop-off: 低い / Job Proposal: 東京23区の病院（適切） / Next Action: 詳細ヒアリング / Region Bias: なし / National Expansion Risk: なし
**Failure Category:** なし（正常動作）
**Severity:** Low
**Fix Proposal:** なし
**Retry Needed:** No
**Auditor Comment:** 関西→関東の転職は正常系。Botは問題なく機能する。

---

### Case W5-C02
- **Prefecture:** 東京都 / **Region Block:** 関東 / **Case Type:** クロス / **User Profile:** 28歳女性、美容クリニック3年 / **Entry Route:** TikTok→LINE / **Difficulty:** 中
**Scenario:**
東京在住だが「神奈川でもいい」という柔軟な希望。東京+神奈川の両方を見たい。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「東京都」→「どこでもOK」→「クリニック」→ 温度感「3ヶ月以内」
4. Bot: matching_preview → 東京+横浜川崎の施設表示
5. User: 「条件を変える」→「神奈川県」→「横浜・川崎」→「クリニック」→「すぐにでも」
6. Bot: matching_preview → 横浜川崎のクリニック表示
**System Behavior Evaluation:**
- 2エリア比較のニーズに条件変更で対応可能
- tokyo_included_ilは東京+横浜川崎をカバーするため、一部のクロスニーズに対応
**Results:** Drop-off: 低い / Job Proposal: 東京+神奈川（適切） / Next Action: 詳細検討 / Region Bias: なし / National Expansion Risk: なし
**Failure Category:** なし（正常動作）
**Severity:** Low
**Fix Proposal:** 複数エリア同時表示機能があるとUX改善
**Retry Needed:** No
**Auditor Comment:** 関東内のクロスリージョンは正常動作。

---

### Case W5-C03
- **Prefecture:** 愛知県 / **Region Block:** 中部 / **Case Type:** クロス / **User Profile:** 35歳女性、大学病院10年 / **Entry Route:** Instagram→LINE / **Difficulty:** 中
**Scenario:**
名古屋在住。名古屋での転職を希望しているが、「その他の地域」しか選べない。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「名古屋の求人ありますか？」自由テキスト
4. Bot: Quick Reply再表示
5. User: 「その他の地域」タップ
6. Bot: 施設タイプ → 全フロー完走
7. Bot: matching_preview → 関東の施設表示
**System Behavior Evaluation:**
- 名古屋（愛知県）は日本第3の都市圏だがDB 0件
- 大阪に次いで深刻な地域カバレッジの欠如
**Results:** Drop-off: 高い / Job Proposal: 関東のみ / Next Action: 離脱 / Region Bias: 関東限定 / National Expansion Risk: 致命的
**Failure Category:** GEO_LOCK + REGION_EXPANSION_FAIL
**Severity:** Critical
**Fix Proposal:** 名古屋・大阪・福岡は早期のDB構築が必須
**Retry Needed:** Yes
**Auditor Comment:** 日本の3大都市圏のうち2つ（大阪・名古屋）が未対応は事業として致命的。

---

### Case W5-C04
- **Prefecture:** 愛知県 / **Region Block:** 中部 / **Case Type:** クロス / **User Profile:** 29歳女性、急性期3年、東京に引越し可能 / **Entry Route:** Google検索→LINE / **Difficulty:** 中
**Scenario:**
名古屋在住だが東京への引越しを検討中。東京の求人を見て判断したい。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「東京都」タップ → 「23区」→「急性期病院」→「内科系」→「日勤・夜勤両方」→「すぐにでも」
4. Bot: matching_preview → 東京23区の病院表示
5. User: 「この求人が気になる」タップ
**System Behavior Evaluation:**
- 中部→関東の転職は正常に機能
- 引越し前提のユーザーには適切に動作
**Results:** Drop-off: 低い / Job Proposal: 東京23区の病院（適切） / Next Action: 詳細ヒアリング / Region Bias: なし / National Expansion Risk: なし
**Failure Category:** なし（正常動作）
**Severity:** Low
**Fix Proposal:** なし
**Retry Needed:** No
**Auditor Comment:** 引越し前提なら正常動作。

---

### Case W5-C05
- **Prefecture:** 福岡県 / **Region Block:** 九州 / **Case Type:** クロス / **User Profile:** 27歳女性、急性期2年 / **Entry Route:** TikTok→LINE / **Difficulty:** 中
**Scenario:**
福岡在住。福岡での転職を希望。TikTokで見て登録したが、福岡の求人がない。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「福岡で探してます」自由テキスト
4. Bot: Quick Reply再表示
5. User: 「その他の地域」タップ → 全フロー
6. Bot: matching_preview → 関東の施設表示
7. User: 「福岡のはないんですね...」→ 離脱
**System Behavior Evaluation:**
- 福岡は日本第5の都市圏だがDB 0件
- TikTokの全国配信で福岡からの流入は多いはず
**Results:** Drop-off: 高い / Job Proposal: 関東のみ / Next Action: 離脱 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK + REGION_EXPANSION_FAIL
**Severity:** High
**Fix Proposal:** TikTokの配信地域を限定するか、エリア外通知を改善
**Retry Needed:** Yes
**Auditor Comment:** 福岡は看護師需要が高い。早期の対応エリア拡大が望まれる。

---

### Case W5-C06
- **Prefecture:** 福岡県 / **Region Block:** 九州 / **Case Type:** クロス / **User Profile:** 33歳女性、ICU 8年、東京への転職を決意 / **Entry Route:** Instagram→LINE / **Difficulty:** 低
**Scenario:**
福岡から東京への転職を決意済み。関東の病院を積極的に探している。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「東京都」タップ → 「23区」→「急性期病院」→「救急」→「日勤・夜勤両方」→「すぐにでも」
4. Bot: matching_preview → 東京の救急病院表示
5. User: 「この求人が気になる」タップ
**System Behavior Evaluation:**
- 福岡→東京の転職は正常動作
- ICU経験者は高価値人材として適切にマッチング
**Results:** Drop-off: 低い / Job Proposal: 東京の救急病院（適切） / Next Action: 詳細ヒアリング / Region Bias: なし / National Expansion Risk: なし
**Failure Category:** なし（正常動作）
**Severity:** Low
**Fix Proposal:** なし
**Retry Needed:** No
**Auditor Comment:** 関東移住確定ユーザーには問題なく機能。

---

### Case W5-C07
- **Prefecture:** 北海道 / **Region Block:** 北海道 / **Case Type:** クロス / **User Profile:** 30歳女性、急性期5年 / **Entry Route:** Instagram→LINE / **Difficulty:** 中
**Scenario:**
札幌在住。札幌での転職を希望。「その他の地域」しか選べない。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「その他の地域」タップ → 全フロー
4. Bot: matching_preview → 関東の施設表示
5. User: 「札幌の病院はないんですか？」→ Quick Reply再表示
6. User: 離脱
**System Behavior Evaluation:**
- 北海道（札幌）はDB 0件
- 札幌→関東は物理的に最も遠い組み合わせの一つ
**Results:** Drop-off: 高い / Job Proposal: 関東のみ / Next Action: 離脱 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK
**Severity:** High
**Fix Proposal:** エリア外通知
**Retry Needed:** Yes
**Auditor Comment:** 札幌→関東は飛行機距離。関東施設の提案は完全に無意味。

---

### Case W5-C08
- **Prefecture:** 北海道 / **Region Block:** 北海道 / **Case Type:** クロス / **User Profile:** 25歳女性、2年目、関東に行きたい / **Entry Route:** TikTok→LINE / **Difficulty:** 低
**Scenario:**
旭川在住。地元に残るより関東で経験を積みたい。東京か神奈川を希望。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「神奈川県」タップ → 「横浜・川崎」→「急性期病院」→「こだわりなし」→「日勤・夜勤両方」→「すぐにでも」
4. Bot: matching_preview → 横浜川崎の病院表示
5. User: 「他の求人も見たい」タップ
6. Bot: matching_browse → 追加施設表示
**System Behavior Evaluation:**
- 北海道→関東の転職は正常動作
- 関東希望のユーザーには問題なくサービス提供
**Results:** Drop-off: 低い / Job Proposal: 横浜川崎の病院（適切） / Next Action: 閲覧継続 / Region Bias: なし / National Expansion Risk: なし
**Failure Category:** なし（正常動作）
**Severity:** Low
**Fix Proposal:** なし
**Retry Needed:** No
**Auditor Comment:** 地方→関東の転職は正常系。

---

### Case W5-C09
- **Prefecture:** 広島県 / **Region Block:** 中国 / **Case Type:** クロス / **User Profile:** 31歳女性、回復期3年 / **Entry Route:** Instagram→LINE / **Difficulty:** 中
**Scenario:**
広島在住。広島での転職を希望しているが、エリア外。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「その他の地域」タップ → 全フロー
4. Bot: matching_preview → 関東の施設表示
5. User: 「広島の回復期病院ないですか？」→ Quick Reply再表示
6. User: 離脱
**System Behavior Evaluation:**
- 広島はDB 0件
- 地方都市の看護師にとって関東の施設は無関係
**Results:** Drop-off: 高い / Job Proposal: 関東のみ / Next Action: 離脱 / Region Bias: 関東限定 / National Expansion Risk: 高
**Failure Category:** GEO_LOCK
**Severity:** High
**Fix Proposal:** エリア外通知+ウェイトリスト
**Retry Needed:** Yes
**Auditor Comment:** 広島は中国地方最大の都市。将来の拡大先候補。

---

### Case W5-C10
- **Prefecture:** 広島県 / **Region Block:** 中国 / **Case Type:** クロス / **User Profile:** 28歳女性、急性期4年、関東移住検討中 / **Entry Route:** Google検索→LINE / **Difficulty:** 中
**Scenario:**
広島から東京に引越しを考えている。まずは東京の求人を見て判断したい。
**Conversation Flow:**
1. User: LINE友達追加 → 「求人を見る」
2. Bot: エリア選択
3. User: 「東京都」タップ → 「どこでもOK」→「急性期病院」→「内科系」→「日勤・夜勤両方」→「3ヶ月以内」
4. Bot: matching_preview → 東京+横浜川崎の病院表示
5. User: 「この求人が気になる」タップ
**System Behavior Evaluation:**
- 広島→東京の転職は正常動作
- 「どこでもOK」で東京+横浜川崎がカバーされる
**Results:** Drop-off: 低い / Job Proposal: 東京圏の病院（適切） / Next Action: 詳細ヒアリング / Region Bias: なし / National Expansion Risk: なし
**Failure Category:** なし（正常動作）
**Severity:** Low
**Fix Proposal:** なし
**Retry Needed:** No
**Auditor Comment:** 関東移住前提なら正常動作。

---

## 統計サマリ

| カテゴリ | 件数 |
|---------|------|
| 総ケース数 | 50 |
| 標準ケース | 30 |
| 境界ケース | 12 |
| 攻撃的ケース | 8 |

### 県別内訳
| 県 | 件数 |
|----|------|
| 滋賀県 | 5 (W5-004, W5-015, W5-025, W5-029, W5-040) |
| 京都府 | 6 (W5-002, W5-008, W5-013, W5-020, W5-023, W5-033) |
| 大阪府 | 8 (W5-001, W5-007, W5-010, W5-012, W5-016, W5-019, W5-022, W5-026) |
| 兵庫県 | 7 (W5-003, W5-009, W5-011, W5-014, W5-021, W5-024, W5-041) |
| 奈良県 | 5 (W5-005, W5-018, W5-028, W5-034, W5-038) |
| 和歌山県 | 5 (W5-006, W5-017, W5-027, W5-030, W5-039) |
| 予備 | 4 (W5-035兵庫, W5-036京都, W5-037大阪, W5-042大阪) |
| 東京都(クロス) | 2 (W5-C01, W5-C02) |
| 愛知県(クロス) | 2 (W5-C03, W5-C04) |
| 福岡県(クロス) | 2 (W5-C05, W5-C06) |
| 北海道(クロス) | 2 (W5-C07, W5-C08) |
| 広島県(クロス) | 2 (W5-C09, W5-C10) |

### Severity分布
| Severity | 件数 |
|----------|------|
| Critical | 16 |
| High | 24 |
| Medium | 4 |
| Low | 6 |

### Failure Category分布
| Category | 件数 |
|----------|------|
| GEO_LOCK | 40 (単独 or 複合) |
| REGION_EXPANSION_FAIL | 8 |
| JOB_MATCH_FAIL | 9 |
| AMBIG_FAIL | 9 |
| UX_DROP | 8 |
| INPUT_LOCK | 7 |
| HUMAN_HANDOFF_FAIL | 5 |
| REENTRY_FAIL | 2 |
| OTHER | 5 |
| 正常動作（failure なし） | 6 |

### 主要発見事項
1. **関西6府県全てでDB 0件** — 大阪（日本第2都市圏）を含む関西圏の完全未対応は事業上の致命的欠陥
2. **「その他の地域」ラベルの問題** — 大阪・京都・神戸の住民にとって「その他」扱いは侮辱的
3. **自由テキストの地名無視** — 「大阪の病院探してる」等の明確な意図表示がQuick Reply再表示で無視される
4. **エリア外の説明なし** — matching_previewで関東施設を表示する際に「関東エリアの求人です」という説明がない
5. **候補件数の誤解** — 「X件の候補」が関東の数字であることをユーザーは知らない
6. **SNSの全国配信 vs 関東限定サービス** — TikTok/Instagramで全国に発信しつつ関東しか対応しない矛盾
7. **Meta広告の地域ターゲティング** — 関西にも配信されている場合、広告費の浪費+ユーザーの怒り
8. **高価値人材の取りこぼし** — NICU/ICU/オペ室等の専門看護師が関西にいても対応不可
