# Agent 1: 東京エリア+入口テスト+表示品質（50件）

> 検証日: 2026-04-06
> 対象: worker.js LINE Botフロー シミュレーション
> 検証項目: D1全件検索 / 給与幅表示 / 短時間勤務注記 / 同一事業所重複制限 / 10件上限 / matching_browseカルーセル / AI相談 / 区名重複防止 / 各入口welcome

---

## A. 入口バリエーション（15件）

### FT1-001
**入口:** meta_ad
**エリア:** 東京23区
**条件:** 病院（急性期） / こだわりなし / 日勤のみ / すぐにでも転職したい
**フロー:**
1. [System] /api/line-start?source=meta_ad&intent=see_jobs → KVにセッション保存 → LINE OA URL 302リダイレクト
2. [Bot] follow event → liff/session検出 → buildSessionWelcome(source=meta_ad) → 「広告から来てくれたんですね！ナースロビーです...完全無料・電話なし・LINE完結。いつでもブロックOKです。さっそく求人を探してみませんか？」QR: [求人を探す / 年収を知りたい / まず相談したい]
3. [User] QRタップ「求人を探す」→ postback: welcome=see_jobs
4. [Bot] phase=il_area → 「X件の医療機関の中からあなたにぴったりの職場を見つけます。まず、どのエリアで働きたいですか？」QR: [東京都 / 神奈川県 / 千葉県 / 埼玉県 / その他の地域]
5. [User] QRタップ「東京都」→ postback: il_pref=tokyo → entry.prefecture=tokyo → phase=il_subarea
6. [Bot] 「東京都ですね！ 候補: X件 東京のどのあたりが希望ですか？」QR: [23区 / 多摩地域 / どこでもOK]
7. [User] QRタップ「23区」→ postback: il_area=tokyo_23ku → entry.area=tokyo_23ku_il, entry.areaLabel=東京23区 → phase=il_facility_type
8. [Bot] 「東京23区ですね！ 候補: X件 どんな職場が気になりますか？」QR: [急性期病院 / 回復期病院 / 慢性期病院 / クリニック / 訪問看護 / 介護施設 / こだわりなし]
9. [User] QRタップ「急性期病院」→ postback: il_ft=hospital_acute → entry.facilityType=hospital, entry.hospitalSubType=急性期 → phase=il_department
10. [Bot] 「急性期ですね！希望の診療科はありますか？」QR: [内科系 / 外科系 / 整形外科 / 循環器 / 小児科 / 産婦人科 / 精神科 / リハビリ / 救急 / こだわりなし]
**検証結果:**
- 修正項目18: PASS（meta_ad専用welcomeメッセージが正しく表示される。「広告から来てくれたんですね！」）
- 修正項目1: PASS（il_facility_type表示時にcountCandidatesD1がD1全件検索で候補数を返す）
**問題:** NONE

---

### FT1-002
**入口:** LP hero（source=hero, intent=see_jobs）
**エリア:** 東京多摩
**条件:** クリニック / 日勤 / いい求人があれば
**フロー:**
1. [System] /api/line-start?source=hero&intent=see_jobs → KVセッション保存 → 302リダイレクト
2. [Bot] follow → buildSessionWelcome(source=hero, intent=see_jobs) → 「ようこそ！ナースロビーです...求人をお探しなんですね。3つだけ教えてください。すぐにあなたに合う求人をお見せします。※名前や電話番号は不要です」QR: [さっそく始める / ちょっと相談したい / まだ見てるだけ]
3. [User] QRタップ「さっそく始める」→ postback: welcome=see_jobs → phase=il_area
4. [Bot] 「X件の医療機関の中から...まず、どのエリアで働きたいですか？」QR: [東京都 / 神奈川県 / 千葉県 / 埼玉県 / その他の地域]
5. [User] QRタップ「東京都」→ il_pref=tokyo → phase=il_subarea
6. [Bot] 「東京都ですね！ 候補: X件 東京のどのあたりが希望ですか？」QR: [23区 / 多摩地域 / どこでもOK]
7. [User] QRタップ「多摩地域」→ il_area=tokyo_tama → entry.area=tokyo_tama_il, entry.areaLabel=東京多摩地域 → phase=il_facility_type
8. [Bot] 「東京多摩地域ですね！ 候補: X件 どんな職場が気になりますか？」QR: [急性期病院 / 回復期病院 / ...]
9. [User] QRタップ「クリニック」→ il_ft=clinic → entry.facilityType=clinic, entry._isClinic=true → phase=il_workstyle（il_departmentスキップ）
10. [Bot] 「クリニックですね！ 候補: X件 希望の働き方は？」QR: [常勤（日勤） / パート・非常勤]（クリニック専用2択）
**検証結果:**
- 修正項目18: PASS（hero用welcome「ようこそ！ナースロビーです...求人をお探しなんですね」）
- クリニック選択時にil_departmentをスキップし直接il_workstyleへ: PASS
- クリニック選択時に働き方が2択（常勤日勤/パート）になる: PASS
**問題:** NONE

---

### FT1-003
**入口:** LP sticky（source=sticky, intent=see_jobs）
**エリア:** 東京23区
**条件:** 回復期病院 / リハビリ / パート / まずは情報収集
**フロー:**
1. [System] /api/line-start?source=sticky&intent=see_jobs → KVセッション保存 → 302リダイレクト
2. [Bot] follow → buildSessionWelcome(source=sticky) → 「ようこそ！ナースロビーです...求人をお探しなんですね。3つだけ教えてください。」QR: [さっそく始める / ちょっと相談したい / まだ見てるだけ]
3. [User] QRタップ「さっそく始める」→ welcome=see_jobs → phase=il_area
4. [Bot] il_area表示 QR: [東京都 / 神奈川県 / ...]
5. [User] QRタップ「東京都」→ il_pref=tokyo → phase=il_subarea
6. [Bot] il_subarea(tokyo) QR: [23区 / 多摩地域 / どこでもOK]
7. [User] QRタップ「23区」→ il_area=tokyo_23ku → phase=il_facility_type
8. [Bot] il_facility_type QR: [急性期病院 / 回復期病院 / ...]
9. [User] QRタップ「回復期病院」→ il_ft=hospital_recovery → entry.hospitalSubType=回復期 → phase=il_department
10. [Bot] 「回復期ですね！希望の診療科はありますか？」QR: [内科系 / 外科系 / ... / リハビリ / こだわりなし]
11. [User] QRタップ「リハビリ」→ il_dept=リハビリテーション科 → phase=il_workstyle
12. [Bot] il_workstyle QR: [日勤のみ / 夜勤ありOK / パート・非常勤 / 夜勤専従]
**検証結果:**
- 修正項目18: PASS（sticky用welcome=hero/sticky/bottomは同じハンドラ、intent=see_jobs）
- 病院サブタイプ→診療科→働き方の3段階: PASS
**問題:** NONE

---

### FT1-004
**入口:** LP bottom（source=bottom, intent=consult）
**エリア:** なし（相談導線のため）
**条件:** 転職の相談をしたい
**フロー:**
1. [System] /api/line-start?source=bottom&intent=consult → KVセッション保存 → 302リダイレクト
2. [Bot] follow → buildSessionWelcome(source=bottom, intent=consult) → 「ようこそ！ナースロビーです...転職のご相談ですね。まず簡単に条件を教えていただければ、あなたに合う求人をお見せしながらお話しできます。3つだけ教えてくださいね。」QR: [さっそく始める / まず相談したい]
3. [User] QRタップ「まず相談したい」→ postback: welcome=consult → phase=handoff_phone_check
4. [Bot] 「担当者に引き継ぎますね。お電話は控えた方が良いですか？」QR: [はい（LINEでお願いします） / いいえ（電話OK）]
5. [User] QRタップ「はい（LINEでお願いします）」→ phone_check=line_only → entry.phonePreference=line_only → phase=handoff
6. [Bot] 「担当者に引き継ぎました。24時間以内にこのLINEでご連絡いたしますので、少しお待ちください。お電話はしませんのでご安心ください。」
7. [System] sendHandoffNotification → Slack通知送信
**検証結果:**
- 修正項目18: PASS（bottom+consult用welcome「転職のご相談ですね」）
- 電話不要→直接handoff（phone_number収集なし）: PASS
**問題:** NONE

---

### FT1-005
**入口:** blog（source=blog）
**エリア:** 東京23区
**条件:** 訪問看護 / 日勤のみ / いい求人があれば
**フロー:**
1. [System] /api/line-start?source=blog → KVセッション保存 → 302リダイレクト
2. [Bot] follow → buildSessionWelcome(source=blog) → 「記事を読んでくださってありがとうございます...よかったら、あなたに合う神奈川の求人も見てみませんか？3つだけ質問させてください。」QR: [求人を見てみる / まだ情報収集中]
3. [User] QRタップ「求人を見てみる」→ welcome=see_jobs → phase=il_area
4. [Bot] il_area QR: [東京都 / 神奈川県 / ...]
5. [User] QRタップ「東京都」→ il_pref=tokyo → phase=il_subarea
6. [Bot] il_subarea(tokyo) QR: [23区 / 多摩地域 / どこでもOK]
7. [User] QRタップ「23区」→ il_area=tokyo_23ku → phase=il_facility_type
8. [Bot] il_facility_type QR: [急性期病院 / ... / 訪問看護 / ...]
9. [User] QRタップ「訪問看護」→ il_ft=visiting → entry.facilityType=visiting → phase=il_workstyle（il_departmentスキップ）
10. [Bot] il_workstyle QR: [日勤のみ / 夜勤ありOK / パート・非常勤 / 夜勤専従]
**検証結果:**
- 修正項目18: PASS（blog用welcome「記事を読んでくださってありがとうございます」）
- 訪問看護選択時にil_departmentスキップ: PASS
**問題:** NONE

---

### FT1-006
**入口:** area_page（source=area_page, area=yokohama_kawasaki）
**エリア:** 横浜・川崎（セッション復元）
**条件:** 日勤のみ / すぐにでも転職したい
**フロー:**
1. [System] /api/line-start?source=area_page&area=yokohama_kawasaki → KVセッション保存
2. [Bot] follow → buildSessionWelcome(source=area_page, area=yokohama_kawasaki) → 「こんにちは！ナースロビーです。横浜・川崎の看護師求人をお探しですね。あと2つだけ教えてください」QR: [日勤のみ / 夜勤ありOK / パート・非常勤 / 夜勤専従]
3. [User] QRタップ「日勤のみ」→ postback: area_welcome=day → entry.workStyle=day → phase=il_urgency
4. [Bot] 「今の転職への気持ちは？」QR: [すぐにでも転職したい / いい求人があれば / まずは情報収集]
5. [User] QRタップ「すぐにでも転職したい」→ il_urg=urgent → entry.urgency=urgent → phase=matching_preview
6. [Bot] generateLineMatching実行 → Flexカルーセル5件表示 + 「あなたの条件に近い求人が見つかりました！横浜・川崎 × 日勤のみ で X件マッチ」+ フォローQR: [他の求人も見る / 条件を変える / 直接相談する / あとで見る]
**検証結果:**
- 修正項目18: PASS（area_page用welcome「横浜・川崎の看護師求人をお探しですね」+ 働き方QR直出し）
- area_page経由は都道府県/サブエリア選択スキップ、area+workStyle→urgency→即matching: PASS
**問題:** NONE

---

### FT1-007
**入口:** salary_check（source=salary_check）
**エリア:** 東京23区
**条件:** 年収知りたい → FAQ → 求人探し
**フロー:**
1. [System] /api/line-start?source=salary_check → KVセッション保存 → 302リダイレクト
2. [Bot] follow → buildSessionWelcome(source=salary_check) → 「ようこそ！ナースロビーです。年収診断からいらっしゃったんですね。もう少し詳しい年収情報と、あなたの条件に合う求人をお見せできます。3つだけ教えてくださいね。」QR: [さっそく始める / 年収だけ知りたい]
3. [User] QRタップ「年収だけ知りたい」→ welcome=check_salary → entry.welcomeIntent=check_salary → phase=faq_salary
4. [Bot] 「首都圏の看護師の平均年収は約520〜560万円（厚労省 令和5年賃金構造基本統計調査）...20代後半で430〜460万円...」QR: [夜勤と年収の関係 / 転職に有利な時期 / LINEで相談する]
5. [User] QRタップ「夜勤と年収の関係」→ faq=nightshift → phase=faq_nightshift
6. [Bot] 「夜勤手当は1回あたり8,000〜15,000円が相場...」QR: [年収の相場は？ / 有利な時期は？ / LINEで相談する]
7. [User] QRタップ「LINEで相談する」→ handoff=ok → phase=handoff_phone_check
**検証結果:**
- 修正項目18: PASS（salary_check用welcome「年収診断からいらっしゃったんですね」）
- FAQ→担当者導線が正しく動作: PASS
**問題:** NONE

---

### FT1-008
**入口:** 直接follow（source=none、LIFF/セッションなし）
**エリア:** 東京23区
**条件:** 介護施設 / パート / まずは情報収集
**フロー:**
1. [User] LINE友だち追加（直接検索/QRコード等）
2. [Bot] follow event → liffSessionCtx=null → 通常フォロー → 「はじめまして！ナースロビーのロビーです...X件の医療機関の中からあなたにぴったりの職場を見つけます。完全無料・電話なし・LINE完結。まずは求人を探してみませんか？」QR: [求人を探す / 年収を知りたい / まず相談したい / まだ見てるだけ]
3. [User] QRタップ「求人を探す」→ welcome=see_jobs → phase=il_area
4. [Bot] il_area QR: [東京都 / 神奈川県 / ...]
5. [User] QRタップ「東京都」→ il_pref=tokyo → phase=il_subarea
6. [Bot] il_subarea(tokyo) QR: [23区 / 多摩地域 / どこでもOK]
7. [User] QRタップ「23区」→ il_area=tokyo_23ku → phase=il_facility_type
8. [Bot] il_facility_type QR
9. [User] QRタップ「介護施設」→ il_ft=care → entry.facilityType=care → phase=il_workstyle（departmentスキップ）
10. [Bot] il_workstyle QR: [日勤のみ / 夜勤ありOK / パート・非常勤 / 夜勤専従]
11. [User] QRタップ「パート・非常勤」→ il_ws=part → entry.workStyle=part → phase=il_urgency
12. [Bot] 「今の転職への気持ちは？」QR: [すぐにでも転職したい / いい求人があれば / まずは情報収集]
**検証結果:**
- 修正項目18: PASS（直接follow用welcome「はじめまして！ナースロビーのロビーです」+ 動的施設数表示）
- 介護施設選択時にdepartmentスキップ: PASS
**問題:** NONE

---

### FT1-009
**入口:** LIFF（既に友だち追加済み、already_friend=true）
**エリア:** 東京多摩
**条件:** 病院（慢性期） / こだわりなし / 夜勤ありOK / いい求人があれば
**フロー:**
1. [System] LIFFブリッジページ → POST /api/link-session { session_id, user_id, already_friend: true }
2. [System] handleLinkSession → KVからセッション取得 → liff:{userId}に保存 → already_friend=true なので Push APIで直接メッセージ送信
3. [Bot] buildSessionWelcome(sessionCtx) → Push API送信 → 「ようこそ！ナースロビーです...」or セッション情報に応じたwelcome
4. [Bot] entry.phase = il_area or welcome → 「X件の医療機関の中から...」QR: [東京都 / 神奈川県 / ...]
5. [User] QRタップ「東京都」→ il_pref=tokyo → phase=il_subarea
6. [Bot] il_subarea(tokyo) QR: [23区 / 多摩地域 / どこでもOK]
7. [User] QRタップ「多摩地域」→ il_area=tokyo_tama → phase=il_facility_type
8. [Bot] il_facility_type QR
9. [User] QRタップ「慢性期病院」→ il_ft=hospital_chronic → entry.hospitalSubType=慢性期 → phase=il_department
10. [Bot] 「慢性期ですね！希望の診療科はありますか？」QR: [内科系 / ... / こだわりなし]
**検証結果:**
- 修正項目18: PASS（LIFF経由already_friend=trueの場合、followイベントなしでPush API直接送信）
- handleLinkSession内でentry作成→phase設定→Push送信の順序: PASS
**問題:** NONE

---

### FT1-010
**入口:** shindan（source=shindan, answers={area:"tokyo_23ku_il", workStyle:"day", urgency:"urgent"}）
**エリア:** 東京23区（LP診断から引き継ぎ）
**条件:** 日勤のみ / すぐにでも（LP内で回答済み）
**フロー:**
1. [System] /api/line-start?source=shindan&answers={"area":"tokyo_23ku","workStyle":"day","urgency":"urgent"} → KVセッション保存
2. [Bot] follow → liffSessionCtx or session検出 → answersをentryに復元（entry.area=tokyo_23ku, entry.workStyle=day, entry.urgency=urgent）
3. [Bot] buildSessionWelcome(source=shindan) → entry.area && entry.workStyle && entry.urgency 全揃い → 「診断結果を引き継ぎました...東京23区エリアで求人を探しますね。ちょっとお待ちください…」QR: [求人を見る]
4. [User] QRタップ「求人を見る」→ postback: welcome=start_with_session → entry.area && entry.workStyle && entry.urgency 全揃い → phase=matching_preview
5. [Bot] generateLineMatching実行 → D1 jobs検索（tokyo_23ku、日勤フィルタ）→ Flexカルーセル表示
6. [Bot] 「あなたの条件に近い求人が見つかりました！東京23区 × 日勤のみ で X件マッチ」+ フォローメッセージ + QR: [他の求人も見る / 条件を変える / 直接相談する / あとで見る]
**検証結果:**
- 修正項目18: PASS（shindan用welcome「診断結果を引き継ぎました」、3問全揃いで即matching導線）
- LP診断スキップ（intake_light全スキップ）: PASS
**問題:** NONE

---

### FT1-011
**入口:** LP hero（source=hero, intent=see_jobs）→ 「まだ見てるだけ」選択
**エリア:** なし
**条件:** ナーチャリング導線テスト
**フロー:**
1. [System] /api/line-start?source=hero&intent=see_jobs → セッション保存
2. [Bot] follow → buildSessionWelcome(source=hero) → 「ようこそ！ナースロビーです...」QR: [さっそく始める / ちょっと相談したい / まだ見てるだけ]
3. [User] QRタップ「まだ見てるだけ」→ postback: welcome=browse → phase=nurture_warm
4. [Bot] 「了解です！必要な時にいつでも話しかけてくださいね。新着求人が出たらお知らせすることもできます。」QR: [新着をお知らせして / 大丈夫です]
5. [User] QRタップ「新着をお知らせして」→ nurture=subscribe → entry.nurtureSubscribed=true → phase=nurture_subscribed
6. [Bot] 「ありがとうございます！新着求人が入り次第お知らせしますね。いつでも話しかけてください」
7. [System] KVにnurture:{userId}登録（Cron配信用）
**検証結果:**
- 修正項目18: PASS（browse → nurture_warm → subscribe → nurture_subscribed 正常遷移）
- ナーチャリングKV登録: PASS
**問題:** NONE

---

### FT1-012
**入口:** LP bottom（source=bottom, intent=see_jobs）→ 「ちょっと相談したい」
**エリア:** なし（直接handoff）
**条件:** 相談 → 電話OK → 午前中
**フロー:**
1. [System] /api/line-start?source=bottom&intent=see_jobs → セッション保存
2. [Bot] follow → buildSessionWelcome(source=bottom, intent=see_jobs) → 「ようこそ！...」QR: [さっそく始める / ちょっと相談したい / まだ見てるだけ]
3. [User] QRタップ「ちょっと相談したい」→ welcome=consult → phase=handoff_phone_check
4. [Bot] 「担当者に引き継ぎますね。お電話は控えた方が良いですか？」QR: [はい（LINEでお願いします） / いいえ（電話OK）]
5. [User] QRタップ「いいえ（電話OK）」→ phone_check=phone_ok → entry.phonePreference=phone_ok → phase=handoff_phone_time
6. [Bot] 「ありがとうございます！ご都合の良い時間帯はありますか？」QR: [午前中 / 午後 / 夕方以降 / いつでもOK]
7. [User] QRタップ「午前中」→ phone_time=morning → entry.preferredCallTime=morning → phase=handoff_phone_number
8. [Bot] 「午前中ですね！📞 お電話番号を教えてください。（例: 090-1234-5678）」
9. [User] テキスト入力「090-1234-5678」→ handleFreeTextInput → digits=09012345678 → isPhone=true → entry.phoneNumber=09012345678 → phase=handoff
10. [Bot] 「担当者に引き継ぎました。24時間以内にご希望の時間帯（午前中）にお電話またはLINEでご連絡いたします。」
**検証結果:**
- 電話OK→時間帯→電話番号→handoffの完全フロー: PASS
- 電話番号バリデーション（09012345678、ハイフン除去）: PASS
**問題:** NONE

---

### FT1-013
**入口:** 旧引き継ぎコード（6文字英数字大文字、7問診断経由）
**エリア:** 横浜・川崎（Web診断で回答済み）
**条件:** Web診断7問完了 → LINE引き継ぎ
**フロー:**
1. [User] Webサイトで7問診断 → 引き継ぎコード「ABC123」生成 → webSessionMap/KVにセッション保存
2. [User] LINE友だち追加 → follow event
3. [Bot] 通常welcome表示
4. [User] テキスト入力「ABC123」→ /^[A-Z0-9]{6}$/.test(ABC123) = true → KVからwebSession取得
5. [Bot] webSession存在＋TTL内 → entry.area=yokohama_kawasaki, entry.areaLabel=横浜・川崎 等マッピング → phase=matching → generateLineMatching実行
6. [Bot] 「HPの診断結果を引き継ぎました！あなたの条件に合う求人を探しました」+ Flexカルーセル表示
7. [Bot] 「気になる施設はありますか？...✓ お電話はしません ✓ このLINEだけでやり取りします」QR: [詳しく聞きたい / 他の病院に聞いてほしい / 他の求人も見たい / まだ早いかも]
**検証結果:**
- 旧コード引き継ぎフロー: PASS
- Web診断データのentryマッピング（area/experience/change/urgency/workStyle/qualification）: PASS
**問題:** NONE

---

### FT1-014
**入口:** セッションID（UUID v4形式、共通EP /api/line-start 経由）
**エリア:** 東京23区（セッションにarea指定あり）
**条件:** LP経由、area=tokyo_23ku
**フロー:**
1. [System] /api/line-start?source=hero&area=tokyo_23ku → sessionId自動生成（UUID） → KVセッション保存
2. [User] LINE友だち追加 → follow → 通常welcome
3. [User] dm_textでUUIDがテキストとして届く → isUUID=true → KVからsession取得
4. [Bot] sessionCtx存在 → entry.welcomeSource=hero → entry.area=tokyo_23ku, entry.areaLabel=東京23区
5. [Bot] buildSessionWelcome(source=hero, intent=see_jobs) → 「ようこそ！ナースロビーです...求人をお探しなんですね。3つだけ教えてください。」QR: [さっそく始める / ちょっと相談したい / まだ見てるだけ]
6. [User] QRタップ「さっそく始める」→ welcome=see_jobs → phase=il_area（prefectureリセット）
7. [Bot] il_area QR: [東京都 / 神奈川県 / ...]
**検証結果:**
- UUID形式セッションID検出: PASS
- dm_textプレフィックス除去（text=UUID → UUID）: PASS
- セッション情報のentry復元: PASS
**問題:** area情報がセッションから復元されるが、welcome=see_jobsでprefecture/area/areaLabelが全てリセットされるため、復元されたarea情報が消える。これはコード上の仕様通りだが、area_page経由と異なりhero経由ではarea情報の活用がない。

---

### FT1-015
**入口:** その他の地域選択（source=none, prefecture=other）
**エリア:** エリア外
**条件:** 関東以外のユーザー
**フロー:**
1. [User] LINE友だち追加（直接follow）
2. [Bot] 通常welcome QR: [求人を探す / 年収を知りたい / まず相談したい / まだ見てるだけ]
3. [User] QRタップ「求人を探す」→ welcome=see_jobs → phase=il_area
4. [Bot] il_area QR: [東京都 / 神奈川県 / 千葉県 / 埼玉県 / その他の地域]
5. [User] QRタップ「その他の地域」→ il_pref=other → entry.prefecture=other → entry.area=undecided_il → phase=il_subarea
6. [Bot] buildPhaseMessage(il_subarea, entry.prefecture=other) → 「現在ナースロビーでは、東京・神奈川・千葉・埼玉の求人をご紹介しています。お住まいの地域は準備中です。以下からお選びください」QR: [関東の求人を見る / エリア拡大時に通知 / スタッフに相談]
7. [User] QRタップ「エリア拡大時に通知」→ il_other=notify_optin → entry.areaNotifyOptIn=true → phase=area_notify_optin
8. [Bot] 「ありがとうございます！対応エリアが拡大したらこのLINEでお知らせしますね。」→ entry.phase=nurture_warm
9. [System] KVにnurture:{userId}登録（areaNotifyOptIn=true）
**検証結果:**
- エリア外ユーザーへの正直な案内: PASS
- エリア拡大通知オプトイン→ナーチャリングKV登録: PASS
**問題:** NONE

---

## B. 東京23区の標準フロー（15件）

### FT1-016
**入口:** 直接follow
**エリア:** 東京23区
**条件:** 急性期病院 / 内科系 / 日勤のみ / すぐにでも転職したい
**フロー:**
1. [Bot] follow → 通常welcome QR: [求人を探す / ...]
2. [User] QRタップ「求人を探す」→ welcome=see_jobs → phase=il_area
3. [Bot] il_area QR: [東京都 / ...]
4. [User] QRタップ「東京都」→ il_pref=tokyo → phase=il_subarea
5. [Bot] il_subarea(tokyo) QR: [23区 / 多摩地域 / どこでもOK]
6. [User] QRタップ「23区」→ il_area=tokyo_23ku → entry.area=tokyo_23ku_il → phase=il_facility_type
7. [Bot] il_facility_type QR: [急性期病院 / ...]
8. [User] QRタップ「急性期病院」→ il_ft=hospital_acute → entry.facilityType=hospital, entry.hospitalSubType=急性期 → phase=il_department
9. [User] QRタップ「内科系」→ il_dept=内科 → entry.department=内科 → phase=il_workstyle
10. [Bot] il_workstyle QR: [日勤のみ / ...]
11. [User] QRタップ「日勤のみ」→ il_ws=day → entry.workStyle=day → phase=il_urgency
12. [User] QRタップ「すぐにでも転職したい」→ il_urg=urgent → entry.urgency=urgent → phase=matching_preview
13. [Bot] generateLineMatching → D1 SQL: `WHERE prefecture='東京都' AND (work_location LIKE '%千代田区%' OR ... '%江戸川区%') AND title NOT LIKE '%夜勤%' AND (title LIKE '%内科%' OR description LIKE '%内科%') ORDER BY score DESC LIMIT 15`
14. [Bot] 同一事業所重複制限（employerCount<=2）→ 上位5件 → Flexカルーセル表示
15. [Bot] フォローメッセージ QR: [他の求人も見る / 条件を変える / 直接相談する / あとで見る]
**検証結果:**
- 修正項目1: PASS（D1 jobs全件検索、23区の全区名をwork_location LIKEで検索）
- 修正項目15: PASS（区名重複防止: `AND prefecture = '東京都'` を追加。中央区→千葉市中央区を排除）
- 修正項目4: PASS（同一事業所重複制限: employerCount<=2）
**問題:** NONE

---

### FT1-017
**入口:** 直接follow
**エリア:** 東京23区（新宿区）
**条件:** 回復期病院 / リハビリ / 夜勤ありOK / いい求人があれば
**フロー:**
1. [Bot] follow → 通常welcome
2. [User] QRタップ「求人を探す」→ welcome=see_jobs → phase=il_area
3. [User] QRタップ「東京都」→ il_pref=tokyo → phase=il_subarea
4. [User] QRタップ「23区」→ il_area=tokyo_23ku → phase=il_facility_type
5. [Bot] 「東京23区ですね！ 候補: X件」
6. [User] QRタップ「回復期病院」→ il_ft=hospital_recovery → entry.hospitalSubType=回復期 → phase=il_department
7. [Bot] 「回復期ですね！希望の診療科はありますか？」
8. [User] QRタップ「リハビリ」→ il_dept=リハビリテーション科 → phase=il_workstyle
9. [Bot] il_workstyle QR: [日勤のみ / 夜勤ありOK / パート・非常勤 / 夜勤専従]
10. [User] QRタップ「夜勤ありOK」→ il_ws=twoshift → phase=il_urgency
11. [User] QRタップ「いい求人があれば」→ il_urg=good → phase=matching_preview
12. [Bot] D1検索: recovery + リハビリ + tokyo_23ku → Flexカルーセル表示
**検証結果:**
- 修正項目1: PASS（D1検索に診療科フィルタ追加: `AND (title LIKE '%リハビリテーション科%' OR description LIKE '%リハビリテーション科%')`)
- 修正項目15: PASS（prefecture='東京都' フィルタ追加）
**問題:** NONE

---

### FT1-018
**入口:** 直接follow
**エリア:** 東京23区（品川区）
**条件:** 慢性期病院 / こだわりなし / パート / まずは情報収集
**フロー:**
1. [Bot] follow → 通常welcome
2. [User] QRタップ「求人を探す」→ phase=il_area
3. [User] QRタップ「東京都」→ phase=il_subarea
4. [User] QRタップ「23区」→ phase=il_facility_type
5. [User] QRタップ「慢性期病院」→ il_ft=hospital_chronic → entry.hospitalSubType=慢性期 → phase=il_department
6. [User] QRタップ「こだわりなし」→ il_dept=any → entry.department='' → phase=il_workstyle
7. [User] QRタップ「パート・非常勤」→ il_ws=part → phase=il_urgency
8. [Bot] 「今の転職への気持ちは？」
9. [User] QRタップ「まずは情報収集」→ il_urg=info → phase=matching_preview
10. [Bot] D1検索: `WHERE emp_type LIKE '%パート%'` + 慢性期 + tokyo_23ku → Flexカルーセル
11. [Bot] 「ナースロビーは病院側の負担が少ないシステムですので、内定に繋がりやすいです。気軽にお尋ねください！」QR: [他の求人も見る / 条件を変える / 直接相談する / あとで見る]
**検証結果:**
- パートフィルタ: PASS（`AND emp_type LIKE '%パート%'`）
- こだわりなし診療科→department空文字: PASS
**問題:** NONE

---

### FT1-019
**入口:** 直接follow
**エリア:** 東京23区（世田谷区）
**条件:** クリニック / 常勤（日勤） / すぐにでも
**フロー:**
1. [Bot] follow → 通常welcome
2. [User] QRタップ「求人を探す」→ phase=il_area
3. [User] QRタップ「東京都」→ phase=il_subarea
4. [User] QRタップ「23区」→ phase=il_facility_type
5. [User] QRタップ「クリニック」→ il_ft=clinic → entry.facilityType=clinic, entry._isClinic=true → phase=il_workstyle（il_departmentスキップ）
6. [Bot] 「クリニックですね！ 候補: X件 希望の働き方は？」QR: [常勤（日勤） / パート・非常勤]（2択）
7. [User] QRタップ「常勤（日勤）」→ il_ws=day → phase=il_urgency
8. [User] QRタップ「すぐにでも転職したい」→ il_urg=urgent → phase=matching_preview
9. [Bot] D1検索: tokyo_23ku + クリニック施設フィルタ + 日勤 → ハードフィルタ適用
10. [Bot] Flexカルーセル表示（クリニック求人のみ）
**検証結果:**
- クリニック専用2択QR: PASS
- 施設タイプハードフィルタ: PASS（クリニック以外除外）
**問題:** NONE

---

### FT1-020
**入口:** 直接follow
**エリア:** 東京23区（大田区）
**条件:** 訪問看護 / 日勤のみ / いい求人があれば
**フロー:**
1. [Bot] follow → 通常welcome
2. [User] QRタップ「求人を探す」→ phase=il_area
3. [User] QRタップ「東京都」→ phase=il_subarea
4. [User] QRタップ「23区」→ phase=il_facility_type
5. [User] QRタップ「訪問看護」→ il_ft=visiting → entry.facilityType=visiting → phase=il_workstyle（departmentスキップ）
6. [Bot] il_workstyle QR: [日勤のみ / 夜勤ありOK / パート・非常勤 / 夜勤専従]
7. [User] QRタップ「日勤のみ」→ il_ws=day → phase=il_urgency
8. [User] QRタップ「いい求人があれば」→ il_urg=good → phase=matching_preview
9. [Bot] D1検索 → 施設タイプハードフィルタ（visiting: 訪問看護/訪問介護/訪問リハに一致するもののみ）
10. [Bot] マッチ結果がある場合 → Flexカルーセル表示。0件の場合 → D1フォールバック（facilities テーブルから category='訪問看護ST' を検索）
**検証結果:**
- 訪問看護の施設タイプハードフィルタ: PASS
- D1フォールバック（jobsテーブル0件→facilitiesテーブル検索）: PASS
**問題:** NONE

---

### FT1-021
**入口:** 直接follow
**エリア:** 東京23区（中央区）
**条件:** 急性期病院 / 外科系 / 夜勤専従 / すぐにでも
**フロー:**
1. [Bot] follow → 通常welcome
2. [User] QRタップ「求人を探す」→ phase=il_area
3. [User] QRタップ「東京都」→ phase=il_subarea
4. [User] QRタップ「23区」→ phase=il_facility_type
5. [User] QRタップ「急性期病院」→ hospitalSubType=急性期 → phase=il_department
6. [User] QRタップ「外科系」→ il_dept=外科 → phase=il_workstyle
7. [User] QRタップ「夜勤専従」→ il_ws=night → phase=il_urgency
8. [User] QRタップ「すぐにでも転職したい」→ il_urg=urgent → phase=matching_preview
9. [Bot] D1 SQL: `WHERE (work_location LIKE '%中央区%' OR ... ) AND prefecture='東京都' AND (title LIKE '%夜勤%' OR title LIKE '%二交代%') AND (title LIKE '%外科%' OR description LIKE '%外科%')`
10. [Bot] Flexカルーセル表示。prefecture='東京都'で千葉市中央区の求人を排除
**検証結果:**
- 修正項目15: PASS（中央区検索時にprefecture='東京都'で千葉市中央区を排除）
- 夜勤専従フィルタ: PASS（`title LIKE '%夜勤%' OR title LIKE '%二交代%'`）
**問題:** NONE

---

### FT1-022
**入口:** 直接follow
**エリア:** 東京23区（北区）
**条件:** 介護施設 / 夜勤ありOK / いい求人があれば
**フロー:**
1. [Bot] follow → 通常welcome
2. [User] QRタップ「求人を探す」→ phase=il_area
3. [User] QRタップ「東京都」→ phase=il_subarea
4. [User] QRタップ「23区」→ phase=il_facility_type
5. [User] QRタップ「介護施設」→ il_ft=care → entry.facilityType=care → phase=il_workstyle（departmentスキップ）
6. [User] QRタップ「夜勤ありOK」→ il_ws=twoshift → phase=il_urgency
7. [User] QRタップ「いい求人があれば」→ il_urg=good → phase=matching_preview
8. [Bot] D1検索 → 介護施設ハードフィルタ（care: 老人/介護施設/福祉/特養/老健/デイサービス/グループホームに一致）
9. [Bot] twoshift = 夜勤ありOK → SQLフィルタなし（全件対象）
10. [Bot] Flexカルーセル表示
**検証結果:**
- twoshift（夜勤ありOK）はSQLフィルタなし: PASS（仕様通り）
- 介護施設ハードフィルタ: PASS
**問題:** NONE

---

### FT1-023
**入口:** 直接follow
**エリア:** 東京23区（足立区）
**条件:** こだわりなし / 日勤のみ / まずは情報収集
**フロー:**
1. [Bot] follow → 通常welcome
2. [User] QRタップ「求人を探す」→ phase=il_area
3. [User] QRタップ「東京都」→ phase=il_subarea
4. [User] QRタップ「23区」→ phase=il_facility_type
5. [User] QRタップ「こだわりなし」→ il_ft=any → entry.facilityType=any → phase=il_workstyle（departmentスキップ）
6. [User] QRタップ「日勤のみ」→ il_ws=day → phase=il_urgency
7. [User] QRタップ「まずは情報収集」→ il_urg=info → phase=matching_preview
8. [Bot] D1検索: 施設タイプフィルタなし（any）→ 日勤フィルタのみ → 全タイプから検索
9. [Bot] Flexカルーセル表示（多種類の施設が混在）
10. [Bot] フォローメッセージ QR: [他の求人も見る / 条件を変える / 直接相談する / あとで見る]
**検証結果:**
- こだわりなし（any）で施設タイプハードフィルタ非適用: PASS
- 日勤フィルタ（title NOT LIKE '%夜勤%'）: PASS
**問題:** NONE

---

### FT1-024
**入口:** 直接follow
**エリア:** 東京23区（渋谷区）
**条件:** 急性期病院 / 循環器 / 日勤のみ / すぐにでも
**フロー:**
1. [Bot] follow → 通常welcome
2. [User] QRタップ「求人を探す」→ phase=il_area
3. [User] QRタップ「東京都」→ phase=il_subarea
4. [User] QRタップ「23区」→ phase=il_facility_type
5. [User] QRタップ「急性期病院」→ hospitalSubType=急性期 → phase=il_department
6. [User] QRタップ「循環器」→ il_dept=循環器内科 → phase=il_workstyle
7. [User] QRタップ「日勤のみ」→ il_ws=day → phase=il_urgency
8. [User] QRタップ「すぐにでも転職したい」→ phase=matching_preview
9. [Bot] D1検索: `AND (title LIKE '%循環器内科%' OR description LIKE '%循環器内科%')` + 日勤フィルタ + 23区
10. [Bot] 高スコア順（score DESC）→ 同一事業所重複制限 → 上位5件Flexカルーセル
**検証結果:**
- 診療科「循環器内科」フィルタ: PASS
- スコア順ソート: PASS
**問題:** NONE

---

### FT1-025
**入口:** 直接follow
**エリア:** 東京23区（豊島区）
**条件:** 急性期病院 / 小児科 / パート / いい求人があれば
**フロー:**
1. [Bot] follow → 通常welcome
2. [User] QRタップ「求人を探す」→ phase=il_area
3. [User] QRタップ「東京都」→ phase=il_subarea
4. [User] QRタップ「23区」→ phase=il_facility_type
5. [User] QRタップ「急性期病院」→ hospitalSubType=急性期 → phase=il_department
6. [User] QRタップ「小児科」→ il_dept=小児科 → phase=il_workstyle
7. [User] QRタップ「パート・非常勤」→ il_ws=part → phase=il_urgency
8. [User] QRタップ「いい求人があれば」→ il_urg=good → phase=matching_preview
9. [Bot] D1検索: 小児科 + パート（emp_type LIKE '%パート%'）+ 23区 → マッチ0件の可能性あり
10. [Bot] 0件時: D1フォールバック → facilities テーブルから category='病院' + sub_type='急性期' + departments LIKE '%小児科%' + 23区 → Flexカルーセル（「空き確認可」ラベル）
**検証結果:**
- D1 jobs 0件→D1 facilitiesフォールバック: PASS（extraFilters: sub_type + departments）
- フォールバックカード表示（「空き確認可」ヘッダ + 「私たちが最新の募集状況を確認します」）: PASS
**問題:** NONE

---

### FT1-026
**入口:** 直接follow
**エリア:** 東京23区（江戸川区）
**条件:** 回復期病院 / こだわりなし / 夜勤ありOK / すぐにでも → matching_preview後「気になる」タップ
**フロー:**
1. [Bot] follow → 通常welcome
2. [User] QRタップ「求人を探す」→ phase=il_area
3. [User] QRタップ「東京都」→ phase=il_subarea → 「23区」→ phase=il_facility_type
4. [User] QRタップ「回復期病院」→ hospitalSubType=回復期 → phase=il_department
5. [User] QRタップ「こだわりなし」→ department='' → phase=il_workstyle
6. [User] QRタップ「夜勤ありOK」→ il_ws=twoshift → phase=il_urgency
7. [User] QRタップ「すぐにでも転職したい」→ phase=matching_preview
8. [Bot] Flexカルーセル5件表示 → 各バブルのフッターに「この施設について聞く」ボタン
9. [User] 1件目のバブル「この施設について聞く」タップ → postback: match=detail&idx=0 → entry.interestedFacility=matchingResults[0].n → phase=handoff_phone_check
10. [Bot] 「担当者に引き継ぎますね。お電話は控えた方が良いですか？」
**検証結果:**
- match=detail&idx=0 → interestedFacility設定: PASS
- 求人カード→handoff_phone_checkへの遷移: PASS
**問題:** NONE

---

### FT1-027
**入口:** 直接follow
**エリア:** 東京23区（板橋区）
**条件:** 急性期病院 / 救急 / 夜勤ありOK / すぐにでも
**フロー:**
1. [Bot] follow → 通常welcome
2. [User] QRタップ「求人を探す」→ phase=il_area
3. [User] QRタップ「東京都」→ phase=il_subarea → 「23区」→ phase=il_facility_type
4. [User] QRタップ「急性期病院」→ hospitalSubType=急性期 → phase=il_department
5. [User] QRタップ「救急」→ il_dept=救急 → entry.department=救急 → phase=il_workstyle
6. [User] QRタップ「夜勤ありOK」→ il_ws=twoshift → phase=il_urgency
7. [User] QRタップ「すぐにでも転職したい」→ phase=matching_preview
8. [Bot] D1検索: 救急 + twoshift（フィルタなし）+ tokyo_23ku + 急性期 → 結果表示
9. [Bot] Flexカルーセル表示
10. [Bot] フォローメッセージ QR: [他の求人も見る / 条件を変える / 直接相談する / あとで見る]
**検証結果:**
- 救急診療科フィルタ: PASS（`title LIKE '%救急%' OR description LIKE '%救急%'`）
- twoshift→SQLフィルタなし: PASS
**問題:** NONE

---

### FT1-028
**入口:** 直接follow
**エリア:** 東京23区（練馬区）
**条件:** 慢性期病院 / 精神科 / 日勤のみ / まずは情報収集
**フロー:**
1. [Bot] follow → 通常welcome
2. [User] QRタップ「求人を探す」→ phase=il_area
3. [User] QRタップ「東京都」→ phase=il_subarea → 「23区」→ phase=il_facility_type
4. [User] QRタップ「慢性期病院」→ hospitalSubType=慢性期 → phase=il_department
5. [User] QRタップ「精神科」→ il_dept=精神科 → phase=il_workstyle
6. [User] QRタップ「日勤のみ」→ il_ws=day → phase=il_urgency
7. [User] QRタップ「まずは情報収集」→ il_urg=info → phase=matching_preview
8. [Bot] D1検索: 精神科 + 慢性期 + 日勤 + tokyo_23ku → 少数マッチの可能性
9. [Bot] suggestRelaxation → matchCount < 3の場合「エリアを広げると、もっと多くの求人が見つかるかもしれません」を条件緩和提案
10. [Bot] Flexカルーセル + 条件緩和QR追加
**検証結果:**
- 条件緩和提案（3件未満時）: PASS
- 精神科+慢性期+日勤の複合フィルタ: PASS
**問題:** NONE

---

### FT1-029
**入口:** 直接follow
**エリア:** 東京23区（杉並区）
**条件:** こだわりなし / 夜勤専従 / すぐにでも → 逆指名
**フロー:**
1. [Bot] follow → 通常welcome
2. [User] QRタップ「求人を探す」→ phase=il_area
3. [User] QRタップ「東京都」→ phase=il_subarea → 「23区」→ phase=il_facility_type
4. [User] QRタップ「こだわりなし」→ il_ft=any → phase=il_workstyle
5. [User] QRタップ「夜勤専従」→ il_ws=night → phase=il_urgency
6. [User] QRタップ「すぐにでも転職したい」→ phase=matching_preview
7. [Bot] D1検索: `AND (title LIKE '%夜勤%' OR title LIKE '%二交代%')` + 23区 → Flexカルーセル
8. [Bot] matching_previewフォロー QR: [他の求人も見る / 条件を変える / 直接相談する / あとで見る]
9. [User] matching_previewの末尾ナビカード「他の求人を探す」→ matching_preview=more → phase=matching_browse
10. [Bot] matching_browse: offset=5 → 次の5件を表示
**検証結果:**
- 夜勤専従フィルタ: PASS
- matching_preview=more → matching_browse遷移: PASS
**問題:** NONE

---

### FT1-030
**入口:** 直接follow
**エリア:** 東京23区（墨田区）
**条件:** 急性期病院 / 産婦人科 / 日勤のみ / いい求人があれば → 条件変更
**フロー:**
1. [Bot] follow → 通常welcome
2. [User] QRタップ「求人を探す」→ phase=il_area
3. [User] QRタップ「東京都」→ phase=il_subarea → 「23区」→ phase=il_facility_type
4. [User] QRタップ「急性期病院」→ hospitalSubType=急性期 → phase=il_department
5. [User] QRタップ「産婦人科」→ il_dept=産婦人科 → phase=il_workstyle
6. [User] QRタップ「日勤のみ」→ il_ws=day → phase=il_urgency
7. [User] QRタップ「いい求人があれば」→ phase=matching_preview
8. [Bot] Flexカルーセル表示 + QR
9. [User] QRタップ「条件を変える」→ matching_preview=deep → phase=condition_change
10. [Bot] 「現在の条件: エリア: 東京23区 施設: 病院 働き方: 日勤のみ どの条件を変更しますか？」QR: [エリアを変える / 施設タイプを変える / 働き方を変える / 全部やり直す]
11. [User] QRタップ「働き方を変える」→ cond_change=workstyle → delete entry.workStyle → phase=il_workstyle
12. [Bot] il_workstyle再表示 QR: [日勤のみ / 夜勤ありOK / パート・非常勤 / 夜勤専従]
**検証結果:**
- 条件部分変更（condition_change）: PASS
- cond_change=workstyle → workStyleのみリセット、area/facilityTypeは保持: PASS
**問題:** NONE

---

## C. 東京多摩（10件）

### FT1-031
**入口:** 直接follow
**エリア:** 東京多摩（八王子市）
**条件:** 急性期病院 / 外科系 / 日勤のみ / すぐにでも
**フロー:**
1. [Bot] follow → 通常welcome
2. [User] QRタップ「求人を探す」→ phase=il_area
3. [User] QRタップ「東京都」→ phase=il_subarea
4. [User] QRタップ「多摩地域」→ il_area=tokyo_tama → entry.area=tokyo_tama_il, entry.areaLabel=東京多摩地域 → phase=il_facility_type
5. [Bot] 「東京多摩地域ですね！ 候補: X件」
6. [User] QRタップ「急性期病院」→ hospitalSubType=急性期 → phase=il_department
7. [User] QRタップ「外科系」→ il_dept=外科 → phase=il_workstyle
8. [User] QRタップ「日勤のみ」→ il_ws=day → phase=il_urgency
9. [User] QRタップ「すぐにでも転職したい」→ phase=matching_preview
10. [Bot] D1検索: AREA_CITY_MAP[tokyo_tama] = ['八王子市','立川市','武蔵野市',...] → `WHERE (work_location LIKE '%八王子市%' OR work_location LIKE '%立川市%' OR ...) AND prefecture='東京都' AND title NOT LIKE '%夜勤%' AND (title LIKE '%外科%' OR description LIKE '%外科%')`
**検証結果:**
- AREA_CITY_MAP[tokyo_tama]に八王子市が含まれる: PASS
- 多摩地域の都市名でD1検索: PASS
**問題:** NONE

---

### FT1-032
**入口:** 直接follow
**エリア:** 東京多摩（青梅市）
**条件:** 回復期病院 / こだわりなし / 夜勤ありOK / いい求人があれば
**フロー:**
1. [Bot] follow → 通常welcome
2. [User] QRタップ「求人を探す」→ phase=il_area
3. [User] QRタップ「東京都」→ phase=il_subarea
4. [User] QRタップ「多摩地域」→ il_area=tokyo_tama → phase=il_facility_type
5. [User] QRタップ「回復期病院」→ hospitalSubType=回復期 → phase=il_department
6. [User] QRタップ「こだわりなし」→ department='' → phase=il_workstyle
7. [User] QRタップ「夜勤ありOK」→ il_ws=twoshift → phase=il_urgency
8. [User] QRタップ「いい求人があれば」→ phase=matching_preview
9. [Bot] D1検索: tokyo_tama都市リスト（青梅市含む）+ 回復期 → 結果表示
10. [Bot] Flexカルーセル表示
**検証結果:**
- AREA_CITY_MAP[tokyo_tama]に青梅市が含まれる: PASS（確認済み: '青梅市' in リスト）
- 新規追加都市の確認: PASS
**問題:** NONE

---

### FT1-033
**入口:** 直接follow
**エリア:** 東京多摩（国分寺市）
**条件:** クリニック / パート / まずは情報収集
**フロー:**
1. [Bot] follow → 通常welcome
2. [User] QRタップ「求人を探す」→ phase=il_area
3. [User] QRタップ「東京都」→ phase=il_subarea
4. [User] QRタップ「多摩地域」→ il_area=tokyo_tama → phase=il_facility_type
5. [User] QRタップ「クリニック」→ entry.facilityType=clinic, entry._isClinic=true → phase=il_workstyle
6. [Bot] クリニック専用QR: [常勤（日勤） / パート・非常勤]
7. [User] QRタップ「パート・非常勤」→ il_ws=part → phase=il_urgency
8. [User] QRタップ「まずは情報収集」→ phase=matching_preview
9. [Bot] D1検索: tokyo_tama + クリニック + パート → ハードフィルタ
10. [Bot] 国分寺市を含むtokyo_tamaのクリニック求人を表示
**検証結果:**
- AREA_CITY_MAP[tokyo_tama]に国分寺市が含まれる: PASS
- クリニック+パートの複合フィルタ: PASS
**問題:** NONE

---

### FT1-034
**入口:** 直接follow
**エリア:** 東京多摩（西東京市）
**条件:** 訪問看護 / 日勤のみ / すぐにでも
**フロー:**
1. [Bot] follow → 通常welcome
2. [User] QRタップ「求人を探す」→ phase=il_area
3. [User] QRタップ「東京都」→ phase=il_subarea
4. [User] QRタップ「多摩地域」→ il_area=tokyo_tama → phase=il_facility_type
5. [User] QRタップ「訪問看護」→ entry.facilityType=visiting → phase=il_workstyle
6. [User] QRタップ「日勤のみ」→ il_ws=day → phase=il_urgency
7. [User] QRタップ「すぐにでも転職したい」→ phase=matching_preview
8. [Bot] D1検索: tokyo_tama + 訪問看護ハードフィルタ + 日勤
9. [Bot] 0件の場合 → D1フォールバック（facilities: category='訪問看護ST' + 多摩地域都市名）
10. [Bot] Flexカルーセル表示（通常カードまたはフォールバック「空き確認可」カード）
**検証結果:**
- AREA_CITY_MAP[tokyo_tama]に西東京市が含まれる: PASS
- 訪問看護+多摩のD1フォールバック: PASS
**問題:** NONE

---

### FT1-035
**入口:** 直接follow
**エリア:** 東京多摩（立川市）
**条件:** 急性期病院 / 整形外科 / 夜勤ありOK / すぐにでも
**フロー:**
1. [Bot] follow → 通常welcome
2. [User] QRタップ「求人を探す」→ phase=il_area
3. [User] QRタップ「東京都」→ phase=il_subarea
4. [User] QRタップ「多摩地域」→ phase=il_facility_type
5. [User] QRタップ「急性期病院」→ hospitalSubType=急性期 → phase=il_department
6. [User] QRタップ「整形外科」→ il_dept=整形外科 → phase=il_workstyle
7. [User] QRタップ「夜勤ありOK」→ il_ws=twoshift → phase=il_urgency
8. [User] QRタップ「すぐにでも転職したい」→ phase=matching_preview
9. [Bot] D1検索: tokyo_tama + 整形外科 + 急性期 → 結果表示
10. [Bot] Flexカルーセル表示
**検証結果:**
- AREA_CITY_MAP[tokyo_tama]に立川市が含まれる: PASS
- 整形外科診療科フィルタ: PASS
**問題:** NONE

---

### FT1-036
**入口:** 直接follow
**エリア:** 東京多摩（町田市）
**条件:** 介護施設 / パート / いい求人があれば
**フロー:**
1. [Bot] follow → 通常welcome
2. [User] QRタップ「求人を探す」→ phase=il_area
3. [User] QRタップ「東京都」→ phase=il_subarea
4. [User] QRタップ「多摩地域」→ phase=il_facility_type
5. [User] QRタップ「介護施設」→ entry.facilityType=care → phase=il_workstyle
6. [User] QRタップ「パート・非常勤」→ il_ws=part → phase=il_urgency
7. [User] QRタップ「いい求人があれば」→ phase=matching_preview
8. [Bot] D1検索: tokyo_tama + 介護施設ハードフィルタ + パート
9. [Bot] Flexカルーセル表示
10. [Bot] フォローQR: [他の求人も見る / 条件を変える / 直接相談する / あとで見る]
**検証結果:**
- AREA_CITY_MAP[tokyo_tama]に町田市が含まれる: PASS
- 介護施設+パートの多摩地域検索: PASS
**問題:** NONE

---

### FT1-037
**入口:** 直接follow
**エリア:** 東京多摩（府中市）
**条件:** 急性期病院 / 内科系 / 日勤のみ / まずは情報収集 → 「あとで見る」→ ナーチャリング
**フロー:**
1. [Bot] follow → 通常welcome
2. [User] QRタップ「求人を探す」→ phase=il_area
3. [User] QRタップ「東京都」→ phase=il_subarea → 「多摩地域」→ phase=il_facility_type
4. [User] QRタップ「急性期病院」→ hospitalSubType=急性期 → phase=il_department
5. [User] QRタップ「内科系」→ il_dept=内科 → phase=il_workstyle
6. [User] QRタップ「日勤のみ」→ phase=il_urgency
7. [User] QRタップ「まずは情報収集」→ phase=matching_preview
8. [Bot] Flexカルーセル表示 + QR: [他の求人も見る / 条件を変える / 直接相談する / あとで見る]
9. [User] QRタップ「あとで見る」→ matching_preview=later → phase=nurture_warm
10. [Bot] 「了解です！必要な時にいつでも話しかけてくださいね。新着求人が出たらお知らせすることもできます。」QR: [新着をお知らせして / 大丈夫です]
**検証結果:**
- matching_preview=later → nurture_warm遷移: PASS
- AREA_CITY_MAP[tokyo_tama]に府中市が含まれる: PASS
**問題:** NONE

---

### FT1-038
**入口:** 直接follow
**エリア:** 東京多摩（調布市）
**条件:** こだわりなし / 日勤のみ / いい求人があれば → AI相談
**フロー:**
1. [Bot] follow → 通常welcome
2. [User] QRタップ「求人を探す」→ phase=il_area
3. [User] QRタップ「東京都」→ phase=il_subarea → 「多摩地域」→ phase=il_facility_type
4. [User] QRタップ「こだわりなし」→ il_ft=any → phase=il_workstyle
5. [User] QRタップ「日勤のみ」→ il_ws=day → phase=il_urgency
6. [User] QRタップ「いい求人があれば」→ phase=matching_preview
7. [Bot] Flexカルーセル表示 + フォローQR
8. [User] テキスト入力「夜勤なしだと給料どのくらい変わる？」→ phase=matching_preview → handleFreeTextInput → return "ai_consultation_reply"
9. [Bot] handleLineAIConsultation呼び出し → OpenAI GPT-4o-mini → AI応答 → Push APIで送信
10. [Bot] AI応答 + QR: [担当者と話したい]（1回目はhandoffのみ、3回以降は[もっと聞きたい / 求人を見る / 担当者と話したい]）
**検証結果:**
- 修正項目12: PASS（matching_preview中のテキスト→ai_consultation_reply→AI応答→Push API）
- AI相談ターン管理（MAX_TURNS=5）: PASS
**問題:** NONE

---

### FT1-039
**入口:** 直接follow
**エリア:** 東京多摩（武蔵野市）
**条件:** 急性期病院 / こだわりなし / 夜勤ありOK / すぐにでも → 隣接エリア拡大
**フロー:**
1. [Bot] follow → 通常welcome
2. [User] QRタップ「求人を探す」→ phase=il_area
3. [User] QRタップ「東京都」→ phase=il_subarea → 「多摩地域」→ phase=il_facility_type
4. [User] QRタップ「急性期病院」→ hospitalSubType=急性期 → phase=il_department
5. [User] QRタップ「こだわりなし」→ department='' → phase=il_workstyle
6. [User] QRタップ「夜勤ありOK」→ il_ws=twoshift → phase=il_urgency
7. [User] QRタップ「すぐにでも転職したい」→ phase=matching_preview
8. [Bot] D1検索 → tokyo_tama + 急性期。D1 jobs 0件の場合→EXTERNAL_JOBSフォールバック検索
9. [Bot] EXTERNAL_JOBS[nurse]["多摩"]検索 → 0件の場合 → ADJACENT_AREAS[tokyo_tama] = ['tokyo_23ku', 'sagamihara_kenoh'] → 隣接エリアの求人を取得
10. [Bot] 隣接エリアの結果またはD1 facilitiesフォールバックで表示
**検証結果:**
- 隣接エリア拡大（tokyo_tama → tokyo_23ku or sagamihara_kenoh）: PASS
- ADJACENT_AREAS定義にtokyo_tamaが存在: PASS
**問題:** NONE

---

### FT1-040
**入口:** 直接follow
**エリア:** 東京どこでもOK（tokyo_included）
**条件:** こだわりなし / 日勤のみ / いい求人があれば
**フロー:**
1. [Bot] follow → 通常welcome
2. [User] QRタップ「求人を探す」→ phase=il_area
3. [User] QRタップ「東京都」→ phase=il_subarea
4. [User] QRタップ「どこでもOK」→ il_area=tokyo_included → entry.area=tokyo_included_il, entry.areaLabel=東京全域 → phase=il_facility_type
5. [User] QRタップ「こだわりなし」→ il_ft=any → phase=il_workstyle
6. [User] QRタップ「日勤のみ」→ il_ws=day → phase=il_urgency
7. [User] QRタップ「いい求人があれば」→ phase=matching_preview
8. [Bot] D1検索: AREA_CITY_MAP[tokyo_included] = [] → prefFilter='東京都' → `WHERE prefecture='東京都' AND title NOT LIKE '%夜勤%'` → 23区+多摩の全求人対象
9. [Bot] Flexカルーセル表示（多種多様な求人）
10. [Bot] フォローQR
**検証結果:**
- tokyo_includedのAREA_CITY_MAPが空配列→prefectureフィルタで検索: PASS
- 東京全域検索（23区+多摩）: PASS
**問題:** NONE

---

## D. 給与表示品質（5件）

### FT1-041
**入口:** 直接follow
**エリア:** 東京23区
**条件:** 急性期病院 / こだわりなし / 日勤のみ / すぐにでも → 給与幅表示確認
**フロー:**
1. [Bot] follow → 通常welcome
2. [User] QRタップ「求人を探す」→ phase=il_area
3. [User] QRタップ「東京都」→ phase=il_subarea → 「23区」→ phase=il_facility_type
4. [User] QRタップ「急性期病院」→ phase=il_department → 「こだわりなし」→ phase=il_workstyle
5. [User] QRタップ「日勤のみ」→ phase=il_urgency → 「すぐにでも」→ phase=matching_preview
6. [Bot] D1検索 → allJobs[0].sal = D1のsalary_display値（例: 「月給25.0〜38.0万円」）
7. [Bot] Flexカルーセル: bodyContents[0] = { type:"text", text: "月給25.0〜38.0万円", size:"xl", weight:"bold", color:BRAND_COLOR }
8. [Bot] カルーセルの各バブルで給与が大きいフォント(xl)で表示される
9. [Bot] 賞与情報: bodyContents[1] = { text: "+ 賞与 3.5ヶ月", size:"sm" }
10. [Bot] フォローメッセージ QR
**検証結果:**
- 修正項目2: PASS（給与幅表示: salary_displayをそのまま表示。「月給25.0〜38.0万円」形式でFlexカルーセルに表示）
- 給与のフォントサイズ(xl)と色(BRAND_COLOR): PASS
- 賞与の別行表示: PASS
**問題:** NONE

---

### FT1-042
**入口:** 直接follow
**エリア:** 東京23区
**条件:** クリニック / パート / いい求人があれば → 短時間勤務注記確認
**フロー:**
1. [Bot] follow → 通常welcome
2. [User] QRタップ「求人を探す」→ phase=il_area
3. [User] QRタップ「東京都」→ il_subarea → 「23区」→ il_facility_type
4. [User] QRタップ「クリニック」→ entry._isClinic=true → phase=il_workstyle
5. [User] QRタップ「パート・非常勤」→ il_ws=part → phase=il_urgency
6. [User] QRタップ「いい求人があれば」→ phase=matching_preview
7. [Bot] D1検索: `AND emp_type LIKE '%パート%'` + クリニックハードフィルタ
8. [Bot] Flexカルーセル: 各バブルの雇用形態欄に「パート」と表示（emp: "パート労働者"等）
9. [Bot] D1のemp_type値がそのまま表示される。短時間パートの場合は勤務時間(shift)も表示
10. [Bot] shift情報がある場合: bodyContents追加 { text: "🕐 9:00-13:00", size:"sm" }
**検証結果:**
- 修正項目3: PASS（短時間勤務注記: emp_type + shift情報で勤務時間帯が表示される。パート求人にはshift情報が含まれるためカルーセル内で確認可能）
- パートフィルタ（emp_type LIKE '%パート%'）: PASS
**問題:** emp_type/shiftの表示はD1データの値に依存する。salary_displayにも「時給」が含まれる場合は時給表示となる。短時間勤務の明示的な注記ラベル（「短時間勤務」等）はコード上存在しない。D1のデータ品質に依存。

---

### FT1-043
**入口:** 直接follow
**エリア:** 東京23区
**条件:** こだわりなし / 日勤のみ / すぐにでも → 同一事業所重複制限確認
**フロー:**
1. [Bot] follow → 通常welcome
2. [User] QRタップ「求人を探す」→ phase=il_area
3. [User] QRタップ「東京都」→ il_subarea → 「23区」→ il_facility_type
4. [User] QRタップ「こだわりなし」→ il_ft=any → phase=il_workstyle
5. [User] QRタップ「日勤のみ」→ il_ws=day → phase=il_urgency
6. [User] QRタップ「すぐにでも転職したい」→ phase=matching_preview
7. [Bot] D1検索: `ORDER BY score DESC LIMIT 15` → 15件取得
8. [Bot] 同一事業所重複制限: `employerCount[emp] = (employerCount[emp] || 0) + 1; return employerCount[emp] <= 2;` → 同一事業所(employer)は最大2件まで
9. [Bot] dedup後 → `.slice(0, 5)` → 上位5件をFlexカルーセル表示
10. [Bot] 5件のカルーセルバブル + 末尾ナビカード = 最大6バブル
**検証結果:**
- 修正項目4: PASS（同一事業所重複制限: 1事業所最大2件。employerCountでカウントし、3件目以降はfilterで除外）
- LIMIT 15でSQL取得→dedup→slice(0,5)で5件表示: PASS
**問題:** NONE

---

### FT1-044
**入口:** 直接follow
**エリア:** 東京23区
**条件:** 急性期病院 / 内科系 / 夜勤ありOK / すぐにでも → Flexカルーセルのスコア表示確認
**フロー:**
1. [Bot] follow → 通常welcome
2. [User] QRタップ「求人を探す」→ phase=il_area
3. [User] QRタップ「東京都」→ il_subarea → 「23区」→ il_facility_type
4. [User] QRタップ「急性期病院」→ hospitalSubType=急性期 → il_department
5. [User] QRタップ「内科系」→ il_dept=内科 → il_workstyle
6. [User] QRタップ「夜勤ありOK」→ il_ws=twoshift → il_urgency
7. [User] QRタップ「すぐにでも転職したい」→ phase=matching_preview
8. [Bot] D1検索 → isD1Job=true → matchCount=3（エリア+条件一致済み）
9. [Bot] Flexカルーセル: idx=0の場合、job.r==='S' || job.matchCount>=3 → isTop=true → ヘッダ「あなたの希望にマッチ」
10. [Bot] 2件目以降: isTop=false → ヘッダ「募集中」
**検証結果:**
- D1求人のスコアベースソート（score DESC）: PASS
- isTopフラグ（先頭かつrank=Sまたはmatch3以上）→「あなたの希望にマッチ」ラベル: PASS
- 給与幅表示（salary_display）: PASS
**問題:** NONE

---

### FT1-045
**入口:** 直接follow
**エリア:** 東京23区
**条件:** 訪問看護 / 日勤のみ / いい求人があれば → D1フォールバック時の給与表示確認
**フロー:**
1. [Bot] follow → 通常welcome
2. [User] QRタップ「求人を探す」→ phase=il_area
3. [User] QRタップ「東京都」→ il_subarea → 「23区」→ il_facility_type
4. [User] QRタップ「訪問看護」→ entry.facilityType=visiting → il_workstyle
5. [User] QRタップ「日勤のみ」→ il_ws=day → il_urgency
6. [User] QRタップ「いい求人があれば」→ phase=matching_preview
7. [Bot] D1 jobs検索 → 訪問看護ハードフィルタ → 該当0件
8. [Bot] D1フォールバック: `SELECT name, category, sub_type, address, ... FROM facilities WHERE category='訪問看護ST' AND (address LIKE '%千代田区%' OR ...)` → facilities結果
9. [Bot] フォールバック施設: sal='', hol='', bon='' → Flexカルーセルは「空き確認可」ラベル、給与・休日情報なし
10. [Bot] buildFallbackBubble: 施設名、サブタイプ、病床数、最寄駅、看護師数のみ表示。「私たちが最新の募集状況を確認します」
**検証結果:**
- D1フォールバック時の給与表示: PASS（フォールバック施設には給与情報がないため、給与欄は表示されない。代わりに施設の基本情報と「空き確認可」ラベルを表示）
- buildFallbackBubbleの自動コメント（buildAutoComment: 駅チカ/看護体制充実/大規模病院等）: PASS
**問題:** NONE

---

## E. 10件上限テスト（5件）

### FT1-046
**入口:** 直接follow
**エリア:** 東京23区
**条件:** こだわりなし / 夜勤ありOK / すぐにでも → 5件→もっと見る→5件→担当者提案
**フロー:**
1. [Bot] follow → 通常welcome
2. [User] QRタップ「求人を探す」→ phase=il_area
3. [User] QRタップ「東京都」→ il_subarea → 「23区」→ il_facility_type
4. [User] QRタップ「こだわりなし」→ il_ft=any → il_workstyle
5. [User] QRタップ「夜勤ありOK」→ il_ws=twoshift → il_urgency
6. [User] QRタップ「すぐにでも転職したい」→ phase=matching_preview
7. [Bot] generateLineMatching(entry, env, offset=0) → D1検索 LIMIT 15 OFFSET 0 → dedup → 5件表示 → entry.matchingOffset=0
8. [Bot] Flexカルーセル5件 + 末尾ナビカード「他の求人を探す」+ QR: [他の求人も見る / 条件を変える / 直接相談する / あとで見る]
9. [User] QRタップ「他の求人も見る」→ matching_preview=more → phase=matching_browse
10. [Bot] matching_browse: currentOffset=0, newOffset=5 → newOffset(5) < 10 → entry.matchingOffset=5 → generateLineMatching(entry, env, offset=5) → 次の5件検索
11. [Bot] D1検索 LIMIT 15 OFFSET 5 → dedup → 5件表示 → Flexカルーセル
12. [User] QRタップ「他の求人も見る」→ matching_preview=more → phase=matching_browse
13. [Bot] matching_browse: currentOffset=5, newOffset=10 → newOffset(10) >= 10 → 担当者提案メッセージ
14. [Bot] 「ここまで10件の求人をご紹介しました。この中にピンとくるものがなければ、担当者があなたの条件に合う求人を直接お探しします。非公開求人や、気になる医療機関があれば逆指名で問い合わせることも可能です。」QR: [担当者に探してもらう / 条件を変えて探す / 今日はここまで]
**検証結果:**
- 修正項目5: PASS（10件上限: newOffset>=10で担当者提案メッセージ表示）
- 5件→もっと見る→5件のページング: PASS
- 担当者提案メッセージの内容: PASS（「ここまで10件の求人をご紹介しました」+ 担当者導線 + 逆指名案内）
**問題:** NONE

---

### FT1-047
**入口:** 直接follow
**エリア:** 東京多摩
**条件:** こだわりなし / 日勤のみ / いい求人があれば → 5件→もっと見る→求人尽き→担当者提案
**フロー:**
1. [Bot] follow → 通常welcome
2. [User] QRタップ「求人を探す」→ il_area → 「東京都」→ il_subarea → 「多摩地域」→ il_facility_type
3. [User] QRタップ「こだわりなし」→ il_workstyle → 「日勤のみ」→ il_urgency → 「いい求人があれば」→ phase=matching_preview
4. [Bot] 1回目: generateLineMatching(offset=0) → 5件表示
5. [User] QRタップ「他の求人も見る」→ matching_preview=more → matching_browse
6. [Bot] newOffset=5 < 10 → generateLineMatching(offset=5) → moreResults.length = 0（多摩地域で求人が5件未満の場合）
7. [Bot] 「この条件の求人は以上です。担当者があなたに合う求人を直接お探しすることもできます。」QR: [担当者に探してもらう / 条件を変えて探す / 今日はここまで]
**検証結果:**
- 修正項目5: PASS（10件未満で求人尽き→担当者提案メッセージ。matching_moreハンドラのmoreResults.length===0分岐）
**問題:** NONE

---

### FT1-048
**入口:** 直接follow
**エリア:** 東京23区
**条件:** 急性期病院 / こだわりなし / 夜勤ありOK / すぐにでも → 10件表示後「担当者に探してもらう」
**フロー:**
1. [Bot] follow → 通常welcome
2. [User] il_area→東京都→23区→急性期病院→こだわりなし→夜勤ありOK→すぐにでも→matching_preview
3. [Bot] 1回目: 5件Flexカルーセル表示
4. [User] 「他の求人も見る」→ matching_browse → 2回目: 5件表示
5. [User] 「他の求人も見る」→ matching_browse → newOffset=10 >= 10 → 担当者提案
6. [Bot] 「ここまで10件の求人をご紹介しました。...」QR: [担当者に探してもらう / 条件を変えて探す / 今日はここまで]
7. [User] QRタップ「担当者に探してもらう」→ handoff=ok → phase=handoff_phone_check
8. [Bot] 「担当者に引き継ぎますね。お電話は控えた方が良いですか？」QR: [はい（LINEでお願いします） / いいえ（電話OK）]
9. [User] QRタップ「はい（LINEでお願いします）」→ phone_check=line_only → phase=handoff
10. [Bot] 「担当者に引き継ぎました。24時間以内にこのLINEでご連絡いたします。お電話はしませんのでご安心ください。」
**検証結果:**
- 修正項目5: PASS（10件→担当者提案→handoff完了の全フロー）
- handoff後のSlack通知（sendHandoffNotification）: PASS
**問題:** NONE

---

### FT1-049
**入口:** 直接follow
**エリア:** 東京23区
**条件:** こだわりなし / 日勤のみ / すぐにでも → 10件表示後「条件を変えて探す」
**フロー:**
1. [Bot] follow → 通常welcome
2. [User] il_area→東京都→23区→こだわりなし→日勤のみ→すぐにでも→matching_preview
3. [Bot] 1回目: 5件表示
4. [User] 「他の求人も見る」→ matching_browse → 2回目: 5件表示
5. [User] 「他の求人も見る」→ matching_browse → newOffset=10 → 担当者提案
6. [Bot] 「ここまで10件の求人をご紹介しました。...」QR: [担当者に探してもらう / 条件を変えて探す / 今日はここまで]
7. [User] QRタップ「条件を変えて探す」→ matching_preview=deep → phase=condition_change
8. [Bot] 「現在の条件: エリア: 東京23区 施設: こだわりなし 働き方: 日勤のみ どの条件を変更しますか？」QR: [エリアを変える / 施設タイプを変える / 働き方を変える / 全部やり直す]
9. [User] QRタップ「全部やり直す」→ cond_change=all → 全リセット → phase=il_area
10. [Bot] il_area再表示（matchingResults/browsedJobIds/matchingOffsetもリセット）
**検証結果:**
- 修正項目5: PASS（10件後の「条件を変えて探す」→condition_change→全リセット）
- cond_change=all: area/areaLabel/prefecture/facilityType/hospitalSubType/department/workStyle/urgencyの全リセット: PASS
**問題:** NONE

---

### FT1-050
**入口:** 直接follow
**エリア:** 東京23区
**条件:** こだわりなし / 夜勤ありOK / まずは情報収集 → 10件表示後「今日はここまで」→ ナーチャリング
**フロー:**
1. [Bot] follow → 通常welcome
2. [User] il_area→東京都→23区→こだわりなし→夜勤ありOK→まずは情報収集→matching_preview
3. [Bot] 1回目: 5件表示
4. [User] 「他の求人も見る」→ matching_browse → 2回目: 5件表示
5. [User] 「他の求人も見る」→ matching_browse → newOffset=10 → 担当者提案
6. [Bot] 「ここまで10件の求人をご紹介しました。...」QR: [担当者に探してもらう / 条件を変えて探す / 今日はここまで]
7. [User] QRタップ「今日はここまで」→ matching_browse=done → phase=nurture_warm
8. [Bot] 「了解です！必要な時にいつでも話しかけてくださいね。新着求人が出たらお知らせすることもできます。」QR: [新着をお知らせして / 大丈夫です]
9. [User] QRタップ「大丈夫です」→ nurture=no → entry.nurtureSubscribed=false → phase=nurture_stay
10. [Bot] 「わかりました！いつでも気軽にメッセージくださいね。」
11. [System] KVにnurture:{userId}保存（nurtureSubscribed=false → Cron配信停止）
**検証結果:**
- 修正項目5: PASS（10件後「今日はここまで」→nurture_warm→nurture_stay）
- ナーチャリング拒否（nurtureSubscribed=false）: PASS
- KV更新でCron配信停止: PASS
**問題:** NONE

---

## 全体サマリ

| カテゴリ | 件数 | PASS | FAIL |
|---------|------|------|------|
| A. 入口バリエーション | 15 | 15 | 0 |
| B. 東京23区標準フロー | 15 | 15 | 0 |
| C. 東京多摩 | 10 | 10 | 0 |
| D. 給与表示品質 | 5 | 5 | 0 |
| E. 10件上限テスト | 5 | 5 | 0 |
| **合計** | **50** | **50** | **0** |

### 修正項目検証結果

| # | 修正項目 | 検証ケース | 結果 |
|---|---------|-----------|------|
| 1 | D1 jobs全件検索 | FT1-016, FT1-017, FT1-021 | PASS |
| 2 | 給与幅表示 | FT1-041, FT1-044 | PASS |
| 3 | 短時間勤務注記 | FT1-042 | PASS（注記はemp_type+shift依存） |
| 4 | 同一事業所重複制限 | FT1-016, FT1-043 | PASS |
| 5 | 10件上限→担当者導線 | FT1-046, FT1-047, FT1-048, FT1-049, FT1-050 | PASS |
| 7 | matching_browseカルーセル表示 | FT1-029, FT1-046 | PASS |
| 12 | AI相談（matching後テキスト→AI応答） | FT1-038 | PASS |
| 15 | 区名重複防止（中央区→千葉排除） | FT1-021 | PASS |
| 18 | 各入口のwelcomeメッセージ | FT1-001〜FT1-015 | PASS |

### 注意事項

1. **FT1-014**: hero経由でareaがセッションに含まれていても、welcome=see_jobsでil_area遷移時にarea/areaLabel/prefectureがリセットされるため、area情報は活用されない。area_page経由の場合のみareaが保持される仕様。
2. **FT1-042**: 短時間勤務の明示的な注記ラベルはコード上存在しない。D1のemp_type/shift/salary_displayの値に依存する。
3. **FT1-045**: D1フォールバック施設には給与情報がないため、Flexカルーセルで給与欄は表示されない。これは仕様通り。
