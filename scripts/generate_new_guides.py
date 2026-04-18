#!/usr/bin/env python3
"""
ロングテールSEO用の新規 guide 10本を一括生成（Editorial Calm 外装）。
各ページ: Meta/JSON-LD(BC+FAQ+Article) / Hero / 本文3セクション / FAQ / CTA-band / Footer

実行:
  python3 scripts/generate_new_guides.py --dry-run   # 1ページだけ出力
  python3 scripts/generate_new_guides.py --apply     # 10本全生成
"""

import argparse
import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
GUIDE = ROOT / "lp/job-seeker/guide"
TEMPLATE_SRC = ROOT / "lp/job-seeker/area/yokohama-naka-v2.html"
BASE_URL = "https://quads-nurse.com"


def load_v2_style():
    m = re.search(r"<style>(.*?)</style>", TEMPLATE_SRC.read_text(encoding="utf-8"), re.DOTALL)
    return m.group(1) if m else ""


# 既存 guide 互換 CSS（apply_editorial_guide.py の GUIDE_COMPAT_CSS と同じ）
from scripts.apply_editorial_guide import GUIDE_COMPAT_CSS  # type: ignore

# コンテンツ
GUIDES = [
    {
        "slug": "nurse-resignation",
        "title": "看護師が「辞めたい」と思ったら読むガイド｜ナースロビー",
        "description": "看護師が辞めたいと感じる理由ランキングと、衝動で辞めない判断軸、転職する場合のスムーズな手順を解説。LINE完結・電話なしで次の職場を静かに探せます。",
        "h1": "看護師が「辞めたい」と思ったら",
        "subtitle": "一度立ち止まって、次の働き方を静かに考える。",
        "bc_name": "辞めたい看護師のためのガイド",
        "sections": [
            ("辞めたいと感じる理由トップ5", "看護師が「辞めたい」と感じる理由で多いのは、①人間関係（特に師長・先輩との相性）②夜勤と体力の限界 ③給与と責任の釣り合い ④患者対応のプレッシャー ⑤プライベートの犠牲 の5つです。自分がどれに当てはまるのか、まず書き出してみてください。原因が特定できれば、辞めるべきか、職場を変えれば解決するのかが見えてきます。"),
            ("衝動で辞めないための判断軸", "疲れのピークで「もう辞める」と決断すると後悔しやすいです。2週間だけ夜勤の回数を減らしてもらう、有給を1週間取る、など一時的な距離を置いてから考えるのが安全です。それでも気持ちが変わらないなら、環境を変える選択は合理的。ナースロビーではLINEで静かに次の求人を眺めるだけ、というスタンスでも大丈夫です。"),
            ("辞めると決めたらやること", "退職の意思表示は「1〜3ヶ月前」が一般的です。まず直属の上司に口頭で伝え、その後に退職願を提出します。引き継ぎ期間と有給消化を重ねて、ブランクを空けずに次の職場に移るのが理想。ナースロビーは手数料10%で病院側の負担が軽いから、あなたに「早く決めて」と急かすことはありません。"),
        ],
        "faq": [
            ("看護師を辞めたいと思うのは甘えですか？", "甘えではありません。看護師は身体的・精神的な負担が大きい職業で、厚労省の調査でも離職理由として「健康上の理由」「家族関係」「人間関係」が上位に入っています。自分の体と気持ちを守る選択は、決して甘えではありません。"),
            ("辞める前に転職活動を始めるべきですか？", "在職中の転職活動を強くおすすめします。収入が途切れないことと、比較検討の余裕が生まれるからです。LINEで5問タップするだけなら、夜勤明けの10分でも動けます。"),
            ("退職の話を師長にしづらいです。", "「体調を整えたい」「家族の事情」など個人的な理由を主軸にすれば、引き止めが少なくなります。具体的な転職先は言わなくて大丈夫です。"),
        ],
    },
    {
        "slug": "nurse-transfer-bareless",
        "title": "看護師が転職活動をバレずに進める方法｜ナースロビー",
        "description": "職場の同僚や師長にバレずに看護師の転職活動を進める具体策を解説。SNS設定・面接時間の工夫・LINE完結で匿名のまま探せるサービスの使い方まで。",
        "h1": "看護師が転職活動をバレずに進める方法",
        "subtitle": "職場に気づかれず、静かに次の選択肢を探る。",
        "bc_name": "転職バレずに進める方法",
        "sections": [
            ("バレる原因トップ3", "看護師の転職活動が職場にバレる原因は、①SNSに求人サイトの名前が残る（Cookie・広告追跡） ②スカウトメールが職場PCに届く ③面接日のシフト希望が不自然 ④担当者の電話が職場の休憩中にかかる、の4つが大半です。この4つを潰せば、ほぼバレません。"),
            ("バレないための具体策", "SNS・ブラウザ: プライベート端末で求人検索、広告Cookieはこまめに削除。連絡手段: メールよりLINEが安全（画面を見られても求人情報が丸見えになりにくい）。面接: 平日の有給・夜勤明けの時間帯を使い、職場近くは避ける。ナースロビーなら電話なし・LINE完結で、そもそも職場に連絡が入る導線がありません。"),
            ("匿名で情報収集できるサービス", "ナースロビーはLINE友だち追加だけで匿名で相談できます。名前・電話番号・メールアドレスは最後まで不要。求人提案はLINEで5件届くだけなので、いつでもブロックで活動終了。「今すぐ辞める気はないが情報だけ」という段階でも使えます。"),
        ],
        "faq": [
            ("同僚にバレずに面接に行けますか？", "有給を半日単位で取得する、夜勤明けの午後を使う、などで対応可能です。職場の近くのカフェで担当者と会うと目撃リスクがあるので、1駅離れた場所を指定しましょう。"),
            ("SNSで求人サイトの広告がよく出ます。", "それは広告Cookieが残っているためです。Chromeならシークレットウィンドウで検索するか、Cookieを定期的に削除してください。職場のパソコンでは絶対に検索しないこと。"),
            ("LINEでのやり取りなら本当に安全？", "ナースロビーは返信のタイミングも自由で、通知を切っておけば画面を見られても分かりにくい設計です。いつでもブロックで終了できます。"),
        ],
    },
    {
        "slug": "mom-nurse-work",
        "title": "ママナースの働き方ガイド｜日勤・時短・両立求人の選び方｜ナースロビー",
        "description": "保育園の送り迎えと両立できる看護師求人の選び方、時短勤務・日勤のみ・クリニック・訪問看護の比較、子育て中ママナースの給与相場まで。LINE完結で静かに探せます。",
        "h1": "ママナースの働き方ガイド",
        "subtitle": "子育てと看護師の仕事を、無理なく両立する。",
        "bc_name": "ママナースの働き方",
        "sections": [
            ("ママナースに人気の働き方4種", "①日勤のみクリニック（外来中心、土日休）②訪問看護ステーション（オンコール条件次第で日勤固定可）③回復期・療養病棟（急性期より落ち着いたペース）④企業看護室・保育園看護師（土日祝休が多い）。それぞれ年収・勤務時間・ブランクOKのハードルが違います。"),
            ("時短勤務が取れる職場の見分け方", "求人票で「時短勤務OK」「子育て支援あり」「院内保育所あり」の記載を確認しましょう。ただし記載があっても実態は違うことも。ナースロビーでは過去の転職者フィードバックをもとに、実質ママナース歓迎の施設だけを提案します。"),
            ("ママナースの年収相場", "神奈川県でフルタイム勤務のママナースは、年収450〜520万円が目安。時短勤務の場合は350〜420万円。夜勤ありなら夜勤手当が加算され、さらに+40〜80万円の水準です。保育料を差し引いて実質収入を計算することをおすすめします。"),
        ],
        "faq": [
            ("子どもが熱を出したとき休めますか？", "看護休暇制度が整っている施設なら、年5日（子2人以上なら10日）まで有給とは別に取得できます。応募前に就業規則を確認してもらえるよう、ナースロビーが担当者経由で確認します。"),
            ("ブランク5年でも復職できますか？", "可能です。クリニックや訪問看護ステーション、介護施設では「ブランクOK」の求人が多く、研修制度も整っています。"),
            ("パートと常勤、どちらが得ですか？", "世帯年収と保育料のバランス次第です。パートで103万／130万の壁を意識する働き方も、常勤で社会保険を手厚くする働き方もあり、LINEで相談いただければ個別にご案内します。"),
        ],
    },
    {
        "slug": "nurse-relationship-trouble",
        "title": "看護師の人間関係トラブル対処法｜転職タイミングの見極め｜ナースロビー",
        "description": "看護師の人間関係トラブル（師長・先輩・医師）の対処法と、我慢すべきか転職すべきかの判断軸を解説。退職前後の注意点とLINEで静かに次の求人を探すコツ。",
        "h1": "看護師の人間関係トラブル対処法",
        "subtitle": "我慢か、場所を変えるか。判断軸を整える。",
        "bc_name": "人間関係トラブル対処",
        "sections": [
            ("よくある人間関係トラブル", "①プリセプターとの相性不良 ②師長のパワハラ傾向 ③医師からの高圧的態度 ④派閥・いじめ ⑤世代ギャップ、の5パターンが主です。相手を変えるのは難しいですが、部署異動やシフト変更で距離を取れる場合もあります。"),
            ("我慢と転職の境界線", "体調に影響が出ている（不眠・食欲低下・出勤前の腹痛）、家族や友人との時間が減っている、仕事中に涙が出る――このいずれかに当てはまるなら、場所を変える検討段階です。健康は取り戻せても、時間は戻ってきません。"),
            ("人間関係重視で職場を選ぶコツ", "面接で「離職率」「産休取得実績」「定着年数」を質問すると、実態が見えます。看護体制（7対1/10対1）も目安になり、余裕のある配置なら人間関係のストレスが軽減されやすいです。ナースロビーでは担当者が過去の転職者の声を把握している施設を優先提案します。"),
        ],
        "faq": [
            ("パワハラを受けています。まず何をすべき？", "記録を残すのが最優先です。日時・発言内容・目撃者をメモし、可能なら録音。労働基準監督署や都道府県の労働局の相談窓口も無料で使えます。"),
            ("師長を飛び越して相談していいですか？", "通常は師長→看護部長の順ですが、師長が原因の場合は看護部長に直接相談して問題ありません。労組があればそちらも併用を。"),
            ("転職先でも人間関係が悪かったら？", "ナースロビーでは、入職後3ヶ月以内に違和感があれば再マッチングを無料で行います。同じミスを繰り返さないよう、判断基準を一緒に整えます。"),
        ],
    },
    {
        "slug": "beauty-clinic-nurse",
        "title": "美容クリニック看護師への転職ガイド｜年収・業務・向いている人｜ナースロビー",
        "description": "美容クリニック看護師の仕事内容・年収相場・未経験からの転職方法を解説。メリット・デメリット、向いている看護師像、神奈川県内の求人動向まで。LINE完結で静かに比較。",
        "h1": "美容クリニック看護師への転職",
        "subtitle": "白衣を変えて、日勤中心のキャリアへ。",
        "bc_name": "美容クリニック看護師転職",
        "sections": [
            ("美容クリニック看護師の仕事内容", "カウンセリング補助、注射（ヒアルロン酸・ボトックス）、医療レーザー機器の操作、アフターケアが中心。夜勤なし・日祝休が基本です。病棟経験は必須ではなく、未経験歓迎の求人も多くあります。"),
            ("年収相場と歩合", "基本給は月30〜40万円。インセンティブ（売上連動歩合）が付くクリニックでは年収600〜800万円も可能です。ただし売上目標のプレッシャーがあるため、固定給重視か歩合重視かで職場を選ぶと失敗しません。"),
            ("向いている人・向いていない人", "向いている: 接客・美容に興味がある／日勤固定希望／機械操作が苦でない／売上意識を持てる。向いていない: 急性期スキル維持したい／美容施術に倫理的抵抗がある／ノルマが苦手。悩むなら、1日見学を希望するのも手です。ナースロビーで調整可能。"),
        ],
        "faq": [
            ("美容クリニック経験ゼロでも転職できますか？", "可能です。大手クリニックは自社研修が充実しており、未経験から3〜6ヶ月で独り立ちできます。病棟経験があるほど歓迎されます。"),
            ("患者さんとの関係は病棟と違いますか？", "健康な方への美容施術なので、病状の急変対応はほぼありません。その分、カウンセリングや接客力が重要になります。"),
            ("神奈川県内の美容クリニック求人は多いですか？", "横浜・川崎を中心に多数あり、常時求人募集の大手チェーンもあります。LINEで希望エリア・勤務形態を教えてください。"),
        ],
    },
    {
        "slug": "corporate-nurse",
        "title": "企業看護師・産業看護師になる方法｜仕事内容と年収｜ナースロビー",
        "description": "企業看護師（産業看護師）の仕事内容、年収相場、求人の探し方、保健師資格の必要性を解説。土日祝休・日勤固定の働き方で子育てと両立したいナース向け。",
        "h1": "企業看護師・産業看護師になる方法",
        "subtitle": "病院を離れ、オフィスで働く選択肢。",
        "bc_name": "企業看護師・産業看護師",
        "sections": [
            ("企業看護師の仕事内容", "健康管理室での従業員健康診断、メンタルヘルス相談、感染症対策、保健指導が中心。夜勤ゼロ・土日祝休・残業少なめが一般的で、看護師のワークライフバランス改善の王道ルートです。"),
            ("年収相場と保健師資格", "年収400〜550万円が目安。夜勤手当がないため病棟より下がりますが、ワークライフバランスは大きく改善。保健師資格があると優遇されますが、看護師免許だけの求人も存在します。"),
            ("求人の探し方", "一般の求人サイトには出にくく、人材紹介経由の非公開求人が多いのが特徴です。ナースロビーでは神奈川・東京の健康管理室求人を担当者経由でご案内します。競争率が高いため、タイミングよく動くことが重要です。"),
        ],
        "faq": [
            ("保健師免許は必須ですか？", "企業によります。大手は保健師資格必須が多いですが、中小企業や健康管理室では看護師のみで働けるポジションも。求人により異なるのでご相談を。"),
            ("病院に戻れなくなりませんか？", "スキル維持は意識的に必要ですが、企業看護師から病棟に戻る人も一定数います。ブランクありOKの病院も多いのでキャリアの行き止まりにはなりません。"),
            ("デスクワーク中心で体力は楽ですか？", "身体負担は軽いですが、社員対応の人間関係やメンタルケアの精神的負荷はあります。向き不向きがあるので面接でしっかり雰囲気を確認しましょう。"),
        ],
    },
    {
        "slug": "nurse-salary-1000man",
        "title": "看護師で年収1000万は可能？現実的なルート｜ナースロビー",
        "description": "看護師が年収1000万円を達成するための現実的なキャリアパス（認定看護師・管理職・訪問看護開業・美容クリニック歩合）を解説。神奈川県の求人相場と合わせて紹介。",
        "h1": "看護師で年収1000万は可能？",
        "subtitle": "現実的なルートと、そうではないルート。",
        "bc_name": "看護師 年収1000万",
        "sections": [
            ("年収1000万を達成する4ルート", "①大病院の看護部長・副部長クラス（15〜20年のキャリアが必要） ②訪問看護ステーションの管理者・開業 ③美容クリニックで歩合制（売上次第） ④夜勤ガッツリ＋応援ナース併用（体力勝負）。それぞれリスクとリターンが違います。"),
            ("最短ルートと現実的ルート", "最短は③の美容クリニック歩合制で、数年で到達する人も。ただし売上プレッシャーが強く、続けられない人も多いです。現実的には②の訪問看護管理者ルートが再現性高く、5〜10年で到達可能です。"),
            ("年収1000万を目指さない選択", "「年収600万でワークライフバランス重視」を選ぶ看護師も増えています。1000万にこだわらず、時給換算・精神的余裕・家族との時間を加味した総合年収で考える視点も大切です。"),
        ],
        "faq": [
            ("20代で年収1000万の看護師はいますか？", "ごく少数ですが、美容クリニックの歩合制で達成する例があります。ただし数年で燃え尽きるケースも多く、長期のキャリア戦略を推奨します。"),
            ("認定看護師で年収はどれくらい上がりますか？", "資格手当は月1〜3万円が相場。直接的な年収増は30〜50万円程度ですが、転職時の市場価値が大きく上がります。"),
            ("訪問看護で独立開業するには？", "管理者要件（常勤3年以上）と初期投資（500〜1000万円）が必要です。ナースロビーの関連メンバーで開業相談できる体制もあります。"),
        ],
    },
    {
        "slug": "nurse-salary-low-reason",
        "title": "看護師の給料が安い原因と給料を上げる5つの方法｜ナースロビー",
        "description": "看護師の給料が「責任の割に安い」と感じる構造的原因（夜勤手当依存、施設格差、昇給カーブ）を解説。給料を上げる実践的な5つの方法とロジックで比較。",
        "h1": "看護師の給料が安い原因と上げる方法",
        "subtitle": "安さの構造を理解して、取れる手を取る。",
        "bc_name": "看護師 給料が安い原因",
        "sections": [
            ("なぜ安く感じるのか", "看護師の給与は基本給が控えめで夜勤手当で底上げされる構造です。夜勤を減らすと手取りが大きく下がり、「夜勤をやめると生活できない」状態に。昇給カーブも緩やかで、5年目と15年目で月2〜4万円しか違わない施設もあります。"),
            ("給料を上げる5つの方法", "①夜勤の多い病院へ転職（月+5〜10万円） ②施設規模の大きい病院へ（基本給+1〜2万円） ③認定・専門看護師資格取得（手当+1〜3万円） ④管理職登用（年収+50〜100万円） ⑤美容クリニック歩合（青天井）。リスクとリターンを比較して選びます。"),
            ("転職で給料を上げる交渉のコツ", "現在の年収を正直に伝えた上で、希望年収を10〜15%上で設定するのが一般的。ナースロビーでは手数料10%の仕組みで病院側の負担が軽いため、給与交渉の余地を残しやすいのが特徴です。"),
        ],
        "faq": [
            ("夜勤なしで手取り25万は可能？", "神奈川県のクリニック・訪問看護なら可能です。ただし経験年数や役割により変動します。"),
            ("昇給は何年目から鈍りますか？", "多くの病院で5〜7年目から月2000〜5000円の微増となります。より上げるには役職や資格、転職が必要です。"),
            ("退職金の有無で総年収はどう変わる？", "10年勤続で200〜500万円の差。ただし転職回数が多いと減るため、定着できる職場選びが重要です。"),
        ],
    },
    {
        "slug": "nurse-power-harassment",
        "title": "看護師のパワハラ相談と転職タイミング｜ナースロビー",
        "description": "看護師のパワハラ実例・記録の取り方・相談窓口・転職タイミングの判断基準を解説。心身に影響が出る前に場所を変える選択肢を、LINEで静かに整えられます。",
        "h1": "看護師のパワハラ相談と転職タイミング",
        "subtitle": "心身に影響が出る前に、選択肢を整える。",
        "bc_name": "看護師 パワハラ相談",
        "sections": [
            ("パワハラの実例と記録方法", "「人格否定の発言」「業務から外される」「過大な要求」「私的な雑用」がパワハラの代表例です。日時・発言内容・目撃者を手書きノートかスマホメモで残しましょう。音声録音も有効な証拠になります。"),
            ("相談先4つ", "①都道府県労働局の総合労働相談コーナー（無料）②都道府県看護協会 ③労働組合（組織がある場合）④弁護士の初回無料相談。いずれも守秘義務があり、職場には伝わりません。"),
            ("転職タイミングの判断", "不眠・食欲不振・出勤前の身体症状が出ている場合は、すぐに場所を変える段階です。心療内科の診断書があれば、有給+休職を経てスムーズに退職できます。ナースロビーでは緊急性の高いご相談にも優先対応します。"),
        ],
        "faq": [
            ("パワハラを証明できないと辞められませんか？", "証明できなくても退職は可能です。退職理由は「一身上の都合」で十分。証明が必要なのは労災申請や損害賠償請求の場合のみです。"),
            ("休職してから退職の流れは？", "診断書を持って休職 → 有給消化 → 退職願提出 → 退職、の流れが一般的。休職期間中の傷病手当金も活用できます。"),
            ("次の職場でもパワハラされないか不安です。", "ナースロビーでは離職率・定着年数・過去の退職理由のフィードバックを活用して、マッチしない職場を除外して提案します。"),
        ],
    },
    {
        "slug": "nurse-resignation-letter",
        "title": "看護師の退職届・退職願の書き方とタイミング｜ナースロビー",
        "description": "看護師の退職届・退職願のテンプレート、提出タイミング、引き止めへの対応を解説。円満退職で有給を使い切り、次の職場にスムーズに移るための実践ガイド。",
        "h1": "看護師の退職届・退職願の書き方",
        "subtitle": "円満に辞めて、静かに次へ進むために。",
        "bc_name": "看護師 退職届 書き方",
        "sections": [
            ("退職届と退職願の違い", "退職「願」は「辞めさせてください」とお願いする書類で、受理されるまで撤回可能。退職「届」は「辞めます」と通知する書類で、提出後の撤回は原則不可。通常はまず退職願で意思を示し、受理後に退職届を出します。"),
            ("退職願の書き方テンプレート", "縦書きで「退職願」→本文「私事、この度、一身上の都合により、令和○年○月○日をもって退職いたしたく、ここにお願い申し上げます」→日付・所属・氏名→宛先（病院長）の順で記載。詳細な理由は書かず「一身上の都合」で十分です。"),
            ("引き止めと有給消化のコツ", "「他の施設から内定をいただいた」と伝えれば引き止めが弱まります。有給は法定の権利なので使い切って問題ありません。転職先の入職日を退職日と同月にせず、1〜2週間の有給消化期間を挟むと体を休められます。"),
        ],
        "faq": [
            ("退職を何ヶ月前に伝えるべきですか？", "民法上は2週間前で退職可能ですが、就業規則で1〜3ヶ月前と定められていることが多いです。引き継ぎ期間を考慮して2ヶ月前が無難です。"),
            ("師長に引き止められたらどう断る？", "「家族の事情で決めています」「次の入職日が決まっています」など変更不可の理由を伝えると引き止めが弱まります。"),
            ("有給を全て消化できますか？", "法的には全消化が認められます。ただし業務状況を考慮した調整が必要なことも。ナースロビーでは担当者が病院側と調整する場面もあります。"),
        ],
    },
]


HEADER = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">

<!-- Meta Pixel Code -->
<script>
!function(f,b,e,v,n,t,s)
{{if(f.fbq)return;n=f.fbq=function(){{n.callMethod?
n.callMethod.apply(n,arguments):n.queue.push(arguments)}};
if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
n.queue=[];t=b.createElement(e);t.async=!0;
t.src=v;s=b.getElementsByTagName(e)[0];
s.parentNode.insertBefore(t,s)}}(window, document,'script',
'https://connect.facebook.net/en_US/fbevents.js');
fbq('init', '2326210157891886');
fbq('track', 'PageView');
</script>
<noscript><img height="1" width="1" style="display:none"
src="https://www.facebook.com/tr?id=2326210157891886&ev=PageView&noscript=1"/></noscript>
<!-- End Meta Pixel Code -->

<link rel="icon" type="image/x-icon" href="/favicon.ico">
<link rel="icon" type="image/png" sizes="32x32" href="/assets/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/assets/favicon-16x16.png">
<link rel="apple-touch-icon" sizes="180x180" href="/assets/apple-touch-icon.png">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#F6F2E8">

<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{canonical}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:type" content="article">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="https://quads-nurse.com/assets/ogp.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:site_name" content="ナースロビー">
<meta property="og:locale" content="ja_JP">
<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="https://quads-nurse.com/assets/ogp.png">

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Shippori+Mincho+B1:wght@400;500;600&family=Noto+Sans+JP:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">

<script async src="https://www.googletagmanager.com/gtag/js?id=G-X4G2BYW13B"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-X4G2BYW13B');</script>

<script type="application/ld+json">{bc_json}</script>
<script type="application/ld+json">{faq_json}</script>
<script type="application/ld+json">{article_json}</script>
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"Organization","name":"神奈川ナース転職","alternateName":"ナースロビー","url":"https://quads-nurse.com/"}}</script>

<style>
{v2_style}
{compat_css}
</style>
</head>
<body>

<nav class="site-nav" role="navigation" aria-label="メインナビゲーション">
  <div class="site-nav__inner">
    <a href="/" class="brand" aria-label="ナースロビー トップ">
      <span>ナースロビー</span>
      <span class="brand-tagline">Nurse Robby</span>
    </a>
    <a href="https://lin.ee/oUgDB3x" class="nav-cta" aria-label="LINEで求人を見る" rel="noopener">LINEで求人を見る →</a>
  </div>
</nav>

<nav class="breadcrumb" aria-label="パンくずリスト">
  <a href="/">TOP</a>
  <span class="breadcrumb__sep">/</span>
  <a href="/lp/job-seeker/guide/">ガイド</a>
  <span class="breadcrumb__sep">/</span>
  <span aria-current="page">{bc_name}</span>
</nav>

<header class="hero">
  <div class="container">
    <h1>{h1}</h1>
    <p class="subtitle">{subtitle}</p>
    <a href="https://lin.ee/oUgDB3x" class="cta-button" rel="noopener">LINEで求人を見る →</a>
  </div>
</header>

<div class="container">
{sections_html}
</div>

<section>
  <div class="container">
    <h2>よくある質問</h2>
    <div class="faq-list">
{faq_html}
    </div>
  </div>
</section>

<section class="cta-band">
  <h2>まずはLINEで、静かに始める</h2>
  <p>名前もメールも不要。5問タップするだけで、神奈川の看護師求人が届きます。</p>
  <a href="https://lin.ee/oUgDB3x" class="cta-button" rel="noopener">LINEで求人を見る →</a>
</section>

<footer class="footer" role="contentinfo">
  <div class="container">
    <div class="footer__grid">
      <div>
        <div class="brand" style="font-size: 1.15rem;"><span>ナースロビー</span><span class="brand-tagline">Nurse Robby</span></div>
        <p style="margin-top: 16px; font-size: 0.85rem; color: var(--ink-soft); max-width: 380px; line-height: 1.85;">神奈川県の看護師転職を、LINE で静かに完結させる AI コンシェルジュ。手数料 10% で、電話営業ゼロの転職体験を。</p>
      </div>
      <nav aria-label="エリア"><div class="footer__label">Areas</div><div class="footer__links"><a href="/lp/job-seeker/area/yokohama.html">横浜市</a><a href="/lp/job-seeker/area/kawasaki.html">川崎市</a><a href="/lp/job-seeker/area/sagamihara.html">相模原市</a><a href="/lp/job-seeker/area/">全エリア</a></div></nav>
      <nav aria-label="ガイド"><div class="footer__label">Guides</div><div class="footer__links"><a href="/lp/job-seeker/guide/">転職ガイド</a><a href="/lp/job-seeker/guide/career-change.html">キャリアチェンジ</a><a href="/lp/job-seeker/guide/fee-comparison.html">手数料について</a></div></nav>
    </div>
    <div class="legal"><div><span class="permit"><span class="permit__dot"></span>有料職業紹介事業許可 23-ユ-302928</span></div><div>© 2026 神奈川ナース転職 All Rights Reserved.</div></div>
  </div>
</footer>

</body>
</html>
"""


def build_page(guide, v2_style, compat_css):
    canonical = f"{BASE_URL}/lp/job-seeker/guide/{guide['slug']}.html"

    bc_payload = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "トップ", "item": f"{BASE_URL}/"},
            {"@type": "ListItem", "position": 2, "name": "お役立ちガイド", "item": f"{BASE_URL}/lp/job-seeker/guide/"},
            {"@type": "ListItem", "position": 3, "name": guide["bc_name"], "item": canonical},
        ],
    }

    faq_payload = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in guide["faq"]
        ],
    }

    article_payload = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": guide["h1"],
        "description": guide["description"],
        "author": {"@type": "Organization", "name": "神奈川ナース転職編集部"},
        "publisher": {
            "@type": "Organization",
            "name": "ナースロビー",
            "logo": {"@type": "ImageObject", "url": f"{BASE_URL}/assets/ogp.png"},
        },
        "datePublished": "2026-04-18",
        "dateModified": "2026-04-18",
        "mainEntityOfPage": canonical,
    }

    # Sections HTML
    sections_html_parts = []
    for i, (h, body) in enumerate(guide["sections"]):
        sections_html_parts.append(
            "  <section>\n"
            "    <div class=\"container\">\n"
            f"      <h2>{html.escape(h)}</h2>\n"
            f"      <p>{html.escape(body)}</p>\n"
            "    </div>\n"
            "  </section>"
        )
    sections_html = "\n".join(sections_html_parts)

    faq_html_parts = []
    for q, a in guide["faq"]:
        faq_html_parts.append(
            "      <details class=\"faq-item\">\n"
            f"        <summary>{html.escape(q)}</summary>\n"
            f"        <div class=\"faq-body\">{html.escape(a)}</div>\n"
            "      </details>"
        )
    faq_html = "\n".join(faq_html_parts)

    return HEADER.format(
        title=html.escape(guide["title"], quote=True),
        description=html.escape(guide["description"], quote=True),
        canonical=html.escape(canonical, quote=True),
        bc_json=json.dumps(bc_payload, ensure_ascii=False),
        faq_json=json.dumps(faq_payload, ensure_ascii=False),
        article_json=json.dumps(article_payload, ensure_ascii=False),
        bc_name=html.escape(guide["bc_name"]),
        h1=html.escape(guide["h1"]),
        subtitle=html.escape(guide["subtitle"]),
        sections_html=sections_html,
        faq_html=faq_html,
        v2_style=v2_style,
        compat_css=compat_css,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not (args.dry_run or args.apply):
        print("--dry-run または --apply を指定してください", file=sys.stderr)
        sys.exit(1)

    v2_style = load_v2_style()

    for g in GUIDES:
        out_path = GUIDE / f"{g['slug']}.html"
        if out_path.exists():
            print(f"  [skip] {g['slug']}.html 既存（上書き回避）")
            continue
        html_text = build_page(g, v2_style, GUIDE_COMPAT_CSS)
        if args.apply:
            out_path.write_text(html_text, encoding="utf-8")
            print(f"  ✓ {g['slug']}.html ({len(html_text)} bytes)")
        else:
            print(f"  [dry] {g['slug']}.html ({len(html_text)} bytes)")

    print(f"\n完了: {len(GUIDES)} ページ")


if __name__ == "__main__":
    main()
