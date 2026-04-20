#!/usr/bin/env python3
"""診療科×エリア ロングテールSEOページ生成（Editorial Calm外装）。

5専門科 × 5主要市 = 最大25ページ（薄いコンテンツ回避のため施設数<3は除外）

実行:
    python3 -m scripts.generate_specialty_area --apply
    python3 -m scripts.generate_specialty_area --apply --force
"""
import argparse
import html
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
AREA_DIR = ROOT / "lp/job-seeker/area"
BASE_URL = "https://quads-nurse.com"
STATS_SRC = ROOT / "data" / "specialty_stats.json"

sys.path.insert(0, str(ROOT / "scripts"))
from generate_area_condition import load_v2_style, HEADER  # type: ignore
from apply_editorial_guide import GUIDE_COMPAT_CSS  # type: ignore

# 各専門科の固有テキスト
SPECIALTY_CONTENT = {
    "junkanki": {
        "ja": "循環器内科",
        "title_suffix": "の循環器内科看護師求人",
        "subtitle": "心臓・血管を専門に扱う、命に直結する領域。",
        "sections": [
            ("循環器内科看護師の仕事内容", "循環器内科看護師は、狭心症・心筋梗塞・心不全・不整脈などの患者さんのケアを担当します。心電図モニター観察、バイタル管理、心臓カテーテル検査の介助、術後管理が主な業務。ICU・CCU（循環器集中治療室）配属ではハイレベルなモニタリング能力が求められます。"),
            ("循環器内科で身につくスキル", "不整脈の種類判別、心不全徴候の早期発見、心カテ・ペースメーカー管理など、心臓全般の専門知識と緊急対応能力が養われます。急性期病院での循環器経験は転職市場で高く評価され、次の専門科・認定看護師ルートへの足場にもなります。"),
            ("循環器看護師の年収相場", "神奈川県の循環器病棟看護師の年収は約470〜580万円。急性期CCU・ICU配属は夜勤手当＋特殊手当で+30〜60万円のプレミアム。心電図検定や慢性心不全看護認定看護師の資格取得で、さらにキャリア価値が上がります。"),
        ],
        "faq": [
            ("循環器未経験でも転職できますか？", "一般内科経験があれば研修で十分追いつけます。心電図の読み取り・急変対応がハードルですが、3〜6ヶ月の研修制度を持つ施設を選ぶと安心です。"),
            ("CCUはどんな場所ですか？", "心疾患患者専用の集中治療室。モニター監視が多く、急変対応が頻繁。体力・判断力が重要で、やりがいと責任感が最も大きな配属先の一つです。"),
            ("心電図検定は役立ちますか？", "役立ちます。2級以上を持つと配属・昇進で評価されることが多く、自己学習のモチベーション維持にもなります。"),
        ],
    },
    "shokaki": {
        "ja": "消化器内科",
        "title_suffix": "の消化器内科看護師求人",
        "subtitle": "内視鏡と生活指導、バランスの良い専門領域。",
        "sections": [
            ("消化器内科看護師の仕事内容", "消化器内科看護師は、胃潰瘍・大腸がん・肝臓疾患・膵炎などの患者さんを担当。内視鏡検査の介助、化学療法の管理、栄養指導、術前後ケアが中心業務です。内視鏡室配属では専門介助スキルを磨けます。"),
            ("消化器内科の魅力", "がん看護と生活指導の両方が学べ、患者さんとの長期的な関わりが持てます。急性期ほどの緊張感はないが、化学療法や緩和ケアで精神的ケアも求められる、バランスの良い配属先です。"),
            ("消化器看護師の年収相場", "神奈川県の消化器病棟看護師の年収は約450〜540万円。内視鏡室は特殊手当で+20〜30万円、がん化学療法看護認定看護師の資格で月3〜5万円の手当が上乗せされます。"),
        ],
        "faq": [
            ("内視鏡介助は難しいですか？", "手順を覚えれば慣れますが、医師との呼吸・感染対策が重要。経験者の先輩指導で3〜6ヶ月で独り立ちできます。"),
            ("化学療法の管理は看護師の役割？", "主要役割です。投与管理・副作用観察・患者指導を担当。がん化学療法看護認定看護師資格取得で専門性を高める道もあります。"),
            ("消化器から他科へ転向できますか？", "しやすい領域です。がん看護・緩和ケア・栄養サポートチーム（NST）など幅広い次のステップが開けます。"),
        ],
    },
    "geka": {
        "ja": "外科",
        "title_suffix": "の外科看護師求人",
        "subtitle": "手術と周術期ケア、急性期看護の王道。",
        "sections": [
            ("外科看護師の仕事内容", "外科看護師は、消化器外科・乳腺外科・血管外科・形成外科などの手術を受ける患者さんを担当します。術前説明、術後の早期離床支援、創傷管理、疼痛管理が中心。手術室配属では器械出し・外回り看護師として専門スキルを磨けます。"),
            ("外科で身につくスキル", "周術期ケア、創傷処置、疼痛アセスメント、早期離床支援、術後合併症の早期発見。手術侵襲からの回復を見届ける達成感が得られ、急性期看護の基礎が網羅的に身につく配属先です。"),
            ("外科看護師の年収相場", "神奈川県の外科病棟看護師の年収は約470〜570万円。手術室配属は手術手当で+20〜40万円。皮膚・排泄ケア認定看護師やクリティカルケア認定看護師など、外科ルートでも認定取得の選択肢が広いです。"),
        ],
        "faq": [
            ("手術室と病棟、新卒はどちらが良い？", "病棟で基礎を積むのが一般的ですが、新卒から手術室配属の施設も増えています。器械出し・外回りは3〜6ヶ月で基本を習得できます。"),
            ("早期離床支援が難しそうです。", "痛みのアセスメントと段階的な離床計画が重要。先輩看護師とPT（理学療法士）との連携で学べます。"),
            ("外科から訪問看護は可能？", "十分可能です。術後在宅管理・ストーマケア・創傷処置は訪問看護でも必要なスキル。経験が活きる転向ルートです。"),
        ],
    },
    "ganka": {
        "ja": "眼科",
        "title_suffix": "の眼科看護師求人",
        "subtitle": "繊細な処置と日勤中心、ライフスタイル重視の選択肢。",
        "sections": [
            ("眼科看護師の仕事内容", "眼科看護師は、白内障・緑内障・網膜疾患などの患者さんを担当。外来処置の介助、手術室の器械出し、点眼指導、視力検査補助が主な業務。日勤中心・残業少なめ・夜勤なしのクリニック求人が多く、ライフスタイル重視の看護師に人気です。"),
            ("眼科看護の特徴", "精密な器具扱いと繊細な処置介助が中心。急変対応は少なく、身体・精神負担が比較的軽め。高齢化で白内障手術需要が増加しており、眼科クリニックの求人は神奈川県でも安定供給されています。"),
            ("眼科看護師の年収相場", "神奈川県の眼科クリニック看護師の年収は約380〜460万円。大規模眼科病院は420〜500万円レンジ。夜勤手当がない分、基本給と昇給ペースで判断することが大切です。"),
        ],
        "faq": [
            ("眼科未経験でも応募できますか？", "未経験歓迎の求人が多数あります。点眼・視力検査の手順は研修で1〜2ヶ月で習得可能。細かい作業が苦にならない方に向いています。"),
            ("眼科認定看護師はありますか？", "専門看護師・認定看護師としては独立分野でないですが、手術室看護認定看護師が眼科手術介助にも活きます。"),
            ("土日休みの眼科求人はありますか？", "クリニックには日曜休・祝日休の求人が多数。土曜午前のみ診療の施設が多く、完全土日祝休に近い働き方も可能です。"),
        ],
    },
    "hifuka": {
        "ja": "皮膚科",
        "title_suffix": "の皮膚科看護師求人",
        "subtitle": "処置と接遇、美容連携の選択肢も。",
        "sections": [
            ("皮膚科看護師の仕事内容", "皮膚科看護師は、アトピー性皮膚炎・乾癬・皮膚がんなどの患者さんを担当。処置介助（パッチテスト・生検）、光線治療の管理、塗り薬指導が中心業務です。美容皮膚科と連携する施設では美容処置介助も含まれます。"),
            ("皮膚科看護の魅力", "夜勤なし・日勤固定・残業少なめの求人が中心。患者さんとの接客要素が大きく、コミュニケーションスキルを磨けます。美容皮膚科ルートへの転向も比較的スムーズで、キャリアの幅が広げやすい領域です。"),
            ("皮膚科看護師の年収相場", "神奈川県の皮膚科クリニック看護師の年収は約370〜450万円。大規模総合病院の皮膚科病棟は420〜500万円。美容皮膚科は歩合制で年収500〜700万円レンジも可能です。"),
        ],
        "faq": [
            ("美容皮膚科との違いは？", "一般皮膚科は保険診療中心、美容皮膚科は自由診療中心。業務内容・給与体系が大きく異なります。興味があれば見学・面接で確認を。"),
            ("皮膚科未経験でも転職できますか？", "可能です。処置・塗り薬指導は研修で1〜2ヶ月で習得可能。接客経験がある方は有利です。"),
            ("土日休の皮膚科求人は？", "クリニックに多数あります。美容皮膚科は週末診療が多い傾向があるため、ライフスタイル重視なら一般皮膚科を選ぶと良いです。"),
        ],
    },
    "rehabilitation": {
        "ja": "リハビリテーション科",
        "title_suffix": "のリハビリ病棟看護師求人",
        "subtitle": "回復期看護で、患者さんの日常を取り戻す。",
        "sections": [
            ("リハビリ病棟看護師の仕事内容", "回復期リハビリテーション病棟看護師は、脳血管疾患・骨折・脊髄損傷の患者さんのADL（日常生活動作）自立を支援します。食事・排泄・移乗の介助とリハビリスタッフとの連携、退院支援が中心業務。急性期の喧騒がなく、ペースが落ち着いています。"),
            ("回復期リハビリの魅力", "患者さんの回復過程を長期（2〜6ヶ月）で見届けられ、退院時の達成感が大きい配属先。急性期より夜勤負担が軽く、家庭と両立しやすい環境です。看護体制13対1や15対1が中心で、一人あたりの受け持ち患者数は急性期より多め。"),
            ("リハビリ病棟看護師の年収相場", "神奈川県の回復期リハ病棟看護師の年収は約440〜530万円。急性期より若干下がりますが、夜勤回数が月4〜5回と少なめで、ワークライフバランス重視の看護師に人気です。"),
        ],
        "faq": [
            ("急性期からリハビリに移れますか？", "スムーズに移れます。急性期で身につけたアセスメント能力が活き、リハビリの視点も新たに学べる転向です。"),
            ("受け持ち患者数が多いと聞きました。", "急性期より多め（13〜15対1）ですが、急変が少ないため密度は低め。タイムマネジメント能力が重要になります。"),
            ("リハビリスタッフとの連携は？", "PT/OT/STとの連携が密で、チーム医療の好例。カンファレンスが多く、多職種協働を学べる環境です。"),
        ],
    },
    "nokeigeka": {
        "ja": "脳神経外科",
        "title_suffix": "の脳神経外科看護師求人",
        "subtitle": "脳卒中・脳腫瘍の急性期看護で高度な専門性を。",
        "sections": [
            ("脳神経外科看護師の仕事内容", "脳神経外科看護師は、脳卒中・脳腫瘍・頭部外傷などの患者さんを担当します。意識レベル・瞳孔反応・麻痺の観察、術前後の管理、早期リハビリ介入が主な業務。SCU（脳卒中集中治療室）配属では急性期のハイレベルケアが中心です。"),
            ("脳神経外科で身につくスキル", "JCS/GCSでの意識評価、神経学的所見の観察、脳浮腫・再出血の早期発見、リハビリ早期介入の知識。急性期の中でも専門性が高く、転職市場での評価も高い配属先です。"),
            ("脳神経外科看護師の年収相場", "神奈川県の脳神経外科病棟看護師の年収は約480〜580万円。SCU配属は特殊手当で+30〜50万円。脳卒中リハビリテーション看護認定看護師の資格取得で、専門性と年収の両方を高められます。"),
        ],
        "faq": [
            ("脳神経外科は難しそうで不安です。", "神経学的所見の観察は勉強することが多いですが、先輩・医師の丁寧な教育がある施設なら1年で基本が身につきます。"),
            ("急変対応は多いですか？", "脳ヘルニア・再出血など急変対応は他科より多め。体力・判断力が求められますが、やりがいも大きい配属先です。"),
            ("認定看護師を取るなら？", "脳卒中リハビリテーション看護認定看護師が代表的。取得後は専従で活躍でき、転職市場価値も上がります。"),
        ],
    },
    "seishinka": {
        "ja": "精神科",
        "title_suffix": "の精神科看護師求人",
        "subtitle": "心のケアに向き合う看護師の転職を、静かに。",
        "sections": [
            ("精神科看護師の仕事内容", "精神科看護師は、統合失調症・うつ病・認知症・発達障害など、心の病を抱える患者さんの看護を担当します。身体疾患と異なり、コミュニケーションと観察力が重要で、急性期病棟・療養病棟・外来・訪問看護・デイケア・グループホームなど多様な配属先があります。医療行為よりも対話・環境調整・服薬管理の比重が高いのが特徴です。"),
            ("精神科看護の魅力と難しさ", "精神科の魅力は、患者さんの回復を中長期で見守れること、一般科より穏やかな勤務環境（急変が少ない）、夜勤負担が比較的軽いケースが多いこと。一方で難しさは、暴言・暴力のリスク、治療効果が見えにくい、看護観が揺らぎやすい、の3点。入職前に実際の現場を1日見学できる施設を選ぶと失敗が減ります。"),
            ("精神科看護師の年収相場", "精神科病院の看護師年収は神奈川県で約420〜520万円が相場。一般急性期より若干下がりますが、夜勤回数が月4回以下の施設も多く、ワークライフバランスを重視する方に人気です。精神科認定看護師資格を取得すると月3〜5万円の資格手当がつくケースもあります。"),
        ],
        "faq": [
            ("精神科未経験でも転職できますか？", "可能です。多くの精神科病院は未経験者向けの研修制度を持っており、3〜6ヶ月で独り立ちできます。身体合併症ケアもあるため、一般科経験があると重宝されます。"),
            ("暴力リスクが心配です。", "患者さんとの適切な距離の取り方・デエスカレーション技術を研修で学びます。看護師配置に余裕がある施設ほど安全対策が充実しています。"),
            ("夜勤の負担は？", "精神科の夜勤は急変が少ない分、身体負担は軽めです。ただし見守り業務が多く精神的負担は別の形で存在します。月4〜6回が一般的です。"),
        ],
    },
    "seikeigeka": {
        "ja": "整形外科",
        "title_suffix": "の整形外科看護師求人",
        "subtitle": "リハビリと手術、両面から回復を支える。",
        "sections": [
            ("整形外科看護師の仕事内容", "整形外科看護師は、骨折・脊椎疾患・関節疾患・スポーツ障害の患者さんの看護を担当します。手術前後のケア、リハビリテーション支援、ADL自立に向けた生活援助が中心業務。病棟だけでなく外来・手術室・リハビリ科との連携が多く、チーム医療の経験が積めます。"),
            ("整形外科看護の魅力", "患者さんの回復が目に見えやすく、退院時の笑顔を何度も見られる達成感が魅力です。急性期でも急変が比較的少なく、精神的負担が一般急性期より軽め。手術室配属では器械出し・外回り看護師として専門スキルを磨けます。"),
            ("整形外科看護師の年収相場", "神奈川県の整形外科病棟看護師の年収は約450〜560万円。急性期病院の中では標準的なレンジです。手術室配属は手術手当がつくケースもあり、年収+20〜40万円のプラスになることも。整形外科認定看護師資格で専門性を高める道もあります。"),
        ],
        "faq": [
            ("体力的にきついですか？", "患者さんの移乗・体位変換が多く腰への負担はあります。リフトや福祉機器が整った施設を選ぶと負担軽減につながります。"),
            ("手術室と病棟、どちらが先？", "病棟で基礎スキルを積んでから手術室配属が一般的。ただし新卒から手術室配属の施設もあります。どちらも体力と集中力が重要です。"),
            ("整形外科認定看護師の取得は大変？", "6ヶ月〜1年の教育課程＋実務経験5年が必要。資格取得後は月3〜5万円の手当＋転職市場価値UPが期待できます。"),
        ],
    },
    "naika": {
        "ja": "内科",
        "title_suffix": "の内科看護師求人",
        "subtitle": "幅広い疾患に対応する、看護の基本領域。",
        "sections": [
            ("内科看護師の仕事内容", "内科看護師は、生活習慣病・循環器・消化器・呼吸器・腎臓・糖尿病など幅広い疾患の患者さんを担当します。急性期から慢性期、外来まで配属先が多様で、看護師としての基礎スキルを総合的に身につけられる領域です。点滴・採血・検査介助・服薬指導・生活指導が主な業務。"),
            ("内科で身につくスキル", "アセスメント能力（バイタル変化から何を疑うか）、複数疾患を抱える患者さんへの全体観、服薬・栄養・生活指導の実践力が養われます。循環器内科→集中治療室、消化器内科→内視鏡室などへのキャリアパスも広く、次の専門分野への足場として理想的です。"),
            ("内科看護師の年収相場", "神奈川県の内科病棟看護師の年収は約450〜550万円。急性期病院なら夜勤手当込みで550〜600万円レンジ。外来クリニックは年収380〜450万円で日勤固定が中心。ライフステージに応じて急性期から外来へ移行する看護師も多いです。"),
        ],
        "faq": [
            ("内科と外科、どちらが新人に向いていますか？", "内科は観察眼・全体観を養いやすく、外科は処置・手技を早く覚えられる違いがあります。内科は将来他科へ移る際の応用が効きやすいため基礎として人気です。"),
            ("内科から専門科へ転向できますか？", "十分可能です。内科経験3年以上あれば循環器・消化器・腎臓・糖尿病などの専門病棟に移る道が多数開けます。"),
            ("外来内科の需要は？", "クリニック開業数が増えており、外来内科看護師の求人は神奈川県で常時多数あります。土日休・日勤固定を希望する方に人気です。"),
        ],
    },
    "shonika": {
        "ja": "小児科",
        "title_suffix": "の小児科看護師求人",
        "subtitle": "成長する子どもとご家族に寄り添う看護。",
        "sections": [
            ("小児科看護師の仕事内容", "小児科看護師は、新生児から思春期までの子どもの看護を担当します。一般小児科・NICU（新生児集中治療室）・PICU（小児集中治療室）・小児外科病棟など配属先は多様。処置への不安を和らげる関わり、ご家族への支援、成長・発達への配慮が業務の中心です。"),
            ("小児科看護の魅力", "子どもの回復力の高さ、日々の成長を感じられる喜びが最大の魅力。ご家族との長期的な関係構築もやりがいにつながります。一方、重症例や看取りに立ち会う精神的負担、感染症・事故予防の緊張感は常にあります。保育士資格があると配属に有利なケースも。"),
            ("小児科看護師の年収相場", "神奈川県の小児科病棟看護師の年収は約450〜550万円。NICU・PICUは夜勤手当＋特殊手当で年収+30〜60万円のプレミアムがつきます。大学病院の小児専門病棟はキャリア価値が高く、転職市場でも引く手あまたです。"),
        ],
        "faq": [
            ("小児科未経験でも転職できますか？", "一般病棟経験があれば十分歓迎されます。プリセプター制度が手厚い施設を選ぶと安心。新生児・乳幼児ケアの基礎は研修でカバーできます。"),
            ("NICUは倍率が高いですか？", "高めです。新卒よりも一般病棟で基礎を積んでからの応募が有利。配属希望は早めに出し、面接で熱意を伝えることが重要です。"),
            ("子育て中でも働けますか？", "院内保育所がある病院が多く、ママナースが活躍する病棟です。ただし夜勤・オンコール対応の負担があるため、日勤固定求人を選ぶ選択肢もあります。"),
        ],
    },
    "sanfujinka": {
        "ja": "産婦人科",
        "title_suffix": "の産婦人科看護師求人",
        "subtitle": "命の誕生と女性の健康を、そっと支える。",
        "sections": [
            ("産婦人科看護師の仕事内容", "産婦人科看護師は、妊娠・出産・産褥期のケアに加え、婦人科疾患（子宮筋腫・卵巣疾患・更年期障害等）の患者さんも担当します。配属先は産婦人科病棟・外来・分娩室・NICUなど多岐にわたり、助産師資格があると分娩介助の中心的役割を担えます。"),
            ("産婦人科看護の魅力と負担", "出産の瞬間に立ち会える感動、女性のライフステージ全般に関わる奥深さが魅力。一方で夜間・休日の分娩対応、不妊治療や死産への対応、感情労働の負担は大きめ。助産師資格取得による専門性アップで、より中心的な役割を担える道も。"),
            ("産婦人科看護師の年収相場", "神奈川県の産婦人科病棟看護師の年収は約460〜560万円。助産師資格があれば+30〜50万円のプレミアムで500〜610万円に。産科専門病院・大学病院の周産期センターは給与水準が高めで、専門性を評価される環境です。"),
        ],
        "faq": [
            ("助産師資格は必須ですか？", "必須ではありません。看護師でも産婦人科病棟・外来で多くの業務に携われます。分娩介助の中心役割は助産師が担いますが、チームの一員として十分活躍できます。"),
            ("男性看護師でも応募できますか？", "可能です。ただし患者層の関係で病棟内業務に配慮が必要な場面もあります。NICU・婦人科外来などは男女問わず配属されます。"),
            ("夜勤・オンコールは厳しい？", "分娩対応があるため夜間の緊張感は高めです。月4〜5回の夜勤が一般的で、分娩件数の多い病院ほど負担が大きくなります。"),
        ],
    },
}

CITIES = {
    "yokohama": ("横浜市", "関内・みなとみらい", "横浜市立大学附属市民総合医療センター"),
    "kawasaki": ("川崎市", "川崎駅・溝の口", "川崎市立川崎病院"),
    "sagamihara": ("相模原市", "橋本・町田境", "北里大学病院"),
    "fujisawa": ("藤沢市", "藤沢駅・湘南台", "藤沢市民病院"),
    "yokosuka": ("横須賀市", "横須賀中央", "横須賀共済病院"),
}

MIN_FACILITY_COUNT = 3  # これ未満は薄判定リスクで生成しない


def build_stats_section(stats: dict, specialty_ja: str, city_ja: str) -> str:
    """診療科×エリア固有の統計セクションを生成。"""
    parts = [f"      <h2>{html.escape(city_ja)}の{html.escape(specialty_ja)}求人データ</h2>"]

    summary = []
    if stats.get("facility_count"):
        summary.append(f"対象施設数 <strong>{stats['facility_count']}</strong>施設")
    if stats.get("job_count"):
        summary.append(f"現在の関連求人数 <strong>{stats['job_count']}</strong>件")
    if stats.get("annual_min") and stats.get("annual_max"):
        lo = round(stats["annual_min"] / 10000)
        hi = round(stats["annual_max"] / 10000)
        # 上下限が同値 or 差が小さい場合は単値表示（サンプル数少ないときのノイズ回避）
        if abs(hi - lo) < 30:
            mid = round((lo + hi) / 2)
            summary.append(f"月給平均からの年収換算 <strong>約{mid}万円</strong>（求人件数が少ない場合は参考値）")
        else:
            summary.append(f"月給平均からの年収換算 <strong>{lo}〜{hi}万円</strong>")
    if summary:
        parts.append(
            "      <p>" + " / ".join(summary) +
            f"（{specialty_ja}を標榜する施設を厚労省医療機能情報提供制度より抽出、求人はハローワーク公開データの関連キーワード集計）。</p>"
        )

    top = stats.get("top_facilities") or []
    if top:
        parts.append(f"      <h3>{specialty_ja}を標榜する代表施設</h3>")
        parts.append("      <ul>")
        for f in top[:5]:
            name = f.get("name") or ""
            if not name:
                continue
            sfx = []
            if f.get("sub_type"):
                sfx.append(f["sub_type"])
            if f.get("beds"):
                sfx.append(f"{f['beds']}床")
            if f.get("station"):
                st = f["station"]
                if f.get("minutes"):
                    st += f" 徒歩{f['minutes']}分"
                sfx.append(st)
            suf = "（" + " / ".join(sfx) + "）" if sfx else ""
            parts.append(f"        <li>{html.escape(name)}{html.escape(suf)}</li>")
        parts.append("      </ul>")
        parts.append(f"      <p>各施設との契約関係は個別異なります。応募前にナースロビーLINEで取扱い状況をご確認ください。</p>")

    inner = "\n".join(parts)
    return (
        "  <section>\n"
        "    <div class=\"container\">\n"
        f"{inner}\n"
        "    </div>\n"
        "  </section>"
    )


def build_page(city_slug, specialty_slug, stats_all, v2_style, compat_css):
    key = f"{city_slug}-{specialty_slug}"
    stats = stats_all.get(key, {})
    if stats.get("facility_count", 0) < MIN_FACILITY_COUNT:
        return None, None  # 薄判定回避でスキップ

    city_ja, area_desc, main_hospital = CITIES[city_slug]
    spec = SPECIALTY_CONTENT[specialty_slug]
    specialty_ja = spec["ja"]
    slug = f"{city_slug}-{specialty_slug}"
    canonical = f"{BASE_URL}/lp/job-seeker/area/{slug}.html"
    title = f"{city_ja}{spec['title_suffix']}｜ナースロビー"
    description = f"{city_ja}の{specialty_ja}看護師求人を探す。{area_desc}エリアから{main_hospital}まで、{specialty_ja}を標榜する施設のSEOまとめ。LINE完結・電話なし・手数料10%。"
    h1 = f"{city_ja}{spec['title_suffix']}"

    bc_payload = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "トップ", "item": f"{BASE_URL}/"},
            {"@type": "ListItem", "position": 2, "name": "地域別求人", "item": f"{BASE_URL}/lp/job-seeker/area/"},
            {"@type": "ListItem", "position": 3, "name": city_ja, "item": f"{BASE_URL}/lp/job-seeker/area/{city_slug}.html"},
            {"@type": "ListItem", "position": 4, "name": specialty_ja, "item": canonical},
        ],
    }
    faq_payload = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in spec["faq"]
        ],
    }
    article_payload = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": h1,
        "description": description,
        "author": {"@type": "Organization", "name": "神奈川ナース転職編集部"},
        "publisher": {"@type": "Organization", "name": "ナースロビー",
                      "logo": {"@type": "ImageObject", "url": f"{BASE_URL}/assets/ogp.png"}},
        "datePublished": "2026-04-21",
        "dateModified": "2026-04-21",
        "mainEntityOfPage": canonical,
    }

    sections_html_parts = []
    for h, body in spec["sections"]:
        body_local = body.replace("神奈川県", city_ja, 1) if city_ja != "神奈川県" else body
        sections_html_parts.append(
            "  <section>\n"
            "    <div class=\"container\">\n"
            f"      <h2>{html.escape(h)}</h2>\n"
            f"      <p>{html.escape(body_local)}</p>\n"
            "    </div>\n"
            "  </section>"
        )
    sections_html_parts.append(build_stats_section(stats, specialty_ja, city_ja))
    sections_html = "\n".join(sections_html_parts)

    faq_html_parts = []
    for q, a in spec["faq"]:
        faq_html_parts.append(
            "      <details class=\"faq-item\">\n"
            f"        <summary>{html.escape(q)}</summary>\n"
            f"        <div class=\"faq-body\">{html.escape(a)}</div>\n"
            "      </details>"
        )
    faq_html = "\n".join(faq_html_parts)

    content = HEADER.format(
        title=html.escape(title, quote=True),
        description=html.escape(description, quote=True),
        canonical=html.escape(canonical, quote=True),
        bc_json=json.dumps(bc_payload, ensure_ascii=False),
        faq_json=json.dumps(faq_payload, ensure_ascii=False),
        article_json=json.dumps(article_payload, ensure_ascii=False),
        area_slug=city_slug,
        area_ja=city_ja,
        condition_ja=specialty_ja,
        h1=html.escape(h1),
        subtitle=html.escape(spec["subtitle"]),
        sections_html=sections_html,
        faq_html=faq_html,
        v2_style=v2_style,
        compat_css=compat_css,
    )
    return slug, content


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    if not (args.dry_run or args.apply):
        print("--dry-run または --apply", file=sys.stderr)
        sys.exit(1)

    v2_style = load_v2_style()
    stats_all = json.loads(STATS_SRC.read_text(encoding="utf-8")) if STATS_SRC.exists() else {}
    if not stats_all:
        print("⚠️ specialty_stats.json が空。seo_fetch_specialty_stats.py を先に実行")
        return

    generated = 0
    skipped_thin = 0
    skipped_exists = 0
    for city_slug in CITIES:
        for spec_slug in SPECIALTY_CONTENT:
            slug, content = build_page(city_slug, spec_slug, stats_all, v2_style, GUIDE_COMPAT_CSS)
            if slug is None:
                skipped_thin += 1
                continue
            path = AREA_DIR / f"{slug}.html"
            if path.exists() and not args.force:
                skipped_exists += 1
                continue
            if args.apply:
                path.write_text(content, encoding="utf-8")
                print(f"  ✓ {slug}.html ({len(content)} bytes)")
            else:
                print(f"  [dry] {slug}.html ({len(content)} bytes)")
            generated += 1

    print(f"\n生成 {generated} / 施設数不足スキップ {skipped_thin} / 既存スキップ {skipped_exists}")


if __name__ == "__main__":
    main()
