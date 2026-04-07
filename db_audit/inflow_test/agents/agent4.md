# Agent 4: 自由テキストNLP+入力バリエーション テスト結果

> 検証日: 2026-04-06
> 対象: `api/worker.js` — `handleFreeTextInput()` (L5534-L5695)
> 検証項目: 5. 自由テキストNLP / 6. エリア外正直メッセージ / 12. AI相談

---

## NLPロジック概要（コード分析）

`handleFreeTextInput()` は以下のロジックで自由テキストを処理する:

1. **フェーズ判定**: `il_area`, `il_subarea`, `welcome` のいずれかの場合のみ地名NLPが発動
2. **prefMap**: 47都道府県の漢字名 → `kanagawa`/`tokyo`/`chiba`/`saitama`/`other` に分類
3. **cityMap**: 主要都市名17件（横浜/川崎/相模原/藤沢/名古屋/大阪/福岡/札幌/仙台/広島/京都/神戸/さいたま/川口/船橋/柏 + 東京7区市）
4. **マッチ方式**: `text.includes(key)` — 単純部分文字列一致。正規化なし
5. **ひらがな/カタカナ非対応**: 変換処理なし。漢字のみマッチ
6. **マッチ順序**: prefMap → cityMap の順。prefMapが先にヒットすると都道府県レベルで確定

---

## テスト結果一覧

### A. 都道府県名テキスト入力（10件）

| ID | 入力テキスト | phase | 期待動作 | 実際の動作 | 結果 |
|----|-------------|-------|---------|-----------|------|
| FT4-001 | 「東京」 | il_area | prefMap検出→tokyo | `text.includes('東京')` → true。`entry.prefecture='tokyo'`。return `il_pref_detected_tokyo` → il_subareaへ遷移。東京のサブエリア選択QR表示 | PASS |
| FT4-002 | 「神奈川」 | il_area | prefMap検出→kanagawa | `text.includes('神奈川')` → true。`entry.prefecture='kanagawa'`。return `il_pref_detected_kanagawa` → il_subareaへ。神奈川10エリアQR表示 | PASS |
| FT4-003 | 「北海道」 | il_area | prefMap検出→other | `text.includes('北海道')` → true。`entry.prefecture='other'`。return `il_pref_detected_other` → il_subarea遷移。`buildPhaseMessage('il_subarea')` でエリア外メッセージ表示 | PASS |
| FT4-004 | 「大阪」 | il_area | prefMap検出→other | `text.includes('大阪')` → true（prefMapで先にヒット）。`entry.prefecture='other'`。エリア外メッセージ | PASS |
| FT4-005 | 「千葉」 | il_area | prefMap検出→chiba | `text.includes('千葉')` → true。`entry.prefecture='chiba'`。return `il_pref_detected_chiba` → il_subarea遷移。千葉サブエリア選択QR（船橋・松戸・柏/千葉市・内房/成田・印旛/外房・房総/どこでもOK） | PASS |
| FT4-006 | 「埼玉」 | il_area | prefMap検出→saitama | `text.includes('埼玉')` → true。`entry.prefecture='saitama'`。埼玉サブエリア選択QR表示 | PASS |
| FT4-007 | 「沖縄」 | welcome | prefMap検出→other | `text.includes('沖縄')` → true。welcomeフェーズでもNLP発動（L5564条件にwelcome含む）。`entry.prefecture='other'`。エリア外メッセージ | PASS |
| FT4-008 | 「愛知」 | il_subarea | prefMap検出→other | `text.includes('愛知')` → true。il_subareaもNLP発動対象。`entry.prefecture='other'`。エリア外メッセージ | PASS |
| FT4-009 | 「神奈川で働きたい」 | il_area | 文中にprefKey含む→検出 | `text.includes('神奈川')` → true（部分一致）。正常にkanagawa検出 | PASS |
| FT4-010 | 「東京か神奈川」 | il_area | 最初にヒットした方で確定 | prefMap走査順で「北海道」→...→「東京」が先にヒット。`entry.prefecture='tokyo'`。**神奈川は無視される** | WARN |

**FT4-010 注記**: 複数都道府県を含むテキストは最初のprefMapヒットで確定する。ユーザーが「東京か神奈川」と書いた場合、prefMapの走査順（Object.entriesの挿入順）で東京が先にマッチし、神奈川は検出されない。致命的ではないが、ユーザー意図と乖離する可能性あり。

---

### B. 都市名テキスト入力（10件）

| ID | 入力テキスト | phase | 期待動作 | 実際の動作 | 結果 |
|----|-------------|-------|---------|-----------|------|
| FT4-011 | 「横浜で探したい」 | il_area | cityMap検出→kanagawa | prefMapに「横浜」なし → cityMap走査。`text.includes('横浜')` → true。`entry.prefecture='kanagawa'`。return `il_pref_detected_kanagawa` | PASS |
| FT4-012 | 「柏」 | il_area | cityMap検出→chiba | prefMapにヒットなし → cityMap走査。`text.includes('柏')` → true。`entry.prefecture='chiba'`。千葉サブエリア選択へ | PASS |
| FT4-013 | 「川越」 | il_area | cityMapに川越なし→未検出 | prefMap/cityMapともに「川越」なし。`unexpectedTextCount++`。return null → QR再表示（1回目） | FAIL |
| FT4-014 | 「名古屋」 | il_area | cityMap検出→other | prefMapにヒットなし → cityMap `text.includes('名古屋')` → true。`entry.prefecture='other'`。エリア外メッセージ | PASS |
| FT4-015 | 「藤沢」 | il_area | cityMap検出→kanagawa | `text.includes('藤沢')` → true。kanagawa確定 | PASS |
| FT4-016 | 「町田」 | il_area | cityMap検出→tokyo | `text.includes('町田')` → true。tokyo確定 | PASS |
| FT4-017 | 「川崎市」 | il_area | cityMap検出→kanagawa | `text.includes('川崎')` → true（「川崎市」は「川崎」を含む）。kanagawa確定 | PASS |
| FT4-018 | 「さいたま」 | il_area | cityMap検出→saitama | `text.includes('さいたま')` → true（cityMapに「さいたま」あり）。saitama確定 | PASS |
| FT4-019 | 「船橋」 | il_area | cityMap検出→chiba | `text.includes('船橋')` → true。chiba確定 | PASS |
| FT4-020 | 「厚木」 | il_area | cityMapに厚木なし→未検出 | prefMap/cityMapともに「厚木」なし。`unexpectedTextCount++`。return null → QR再表示 | FAIL |

**FT4-013, FT4-020 不具合**: cityMapに登録されていない都市名（川越、厚木、秦野、大和、海老名、鎌倉、茅ヶ崎、平塚、横須賀、八王子以外の東京市部など）はNLPで検出できない。`buildSessionWelcome` の `AREA_LABELS` には `atsugi`, `hadano`, `yamato`, `ebina`, `chigasaki`, `kamakura` 等があるが、cityMapには未登録。

---

### C. 条件テキスト入力（10件）— matching後のAI応答確認

| ID | 入力テキスト | phase | 期待動作 | 実際の動作 | 結果 |
|----|-------------|-------|---------|-----------|------|
| FT4-021 | 「夜勤なしがいい」 | matching_preview | AI相談に回す | phase=matching_preview → L5663条件ヒット。return `ai_consultation_reply`。OpenAI GPT-4o-miniにシステムプロンプト+ユーザー入力を送信。AI応答をPush APIで送信 | PASS |
| FT4-022 | 「クリニック希望」 | matching_browse | AI相談に回す | phase=matching_browse → L5663条件ヒット。return `ai_consultation_reply`。AI回答後、元のQRを再表示 | PASS |
| FT4-023 | 「ICUで働きたい」 | ai_consultation | AI相談続行 | phase=ai_consultation → L5647条件ヒット。return `ai_consultation_reply`。`consultMessages`に追加してAI応答 | PASS |
| FT4-024 | 「給料はどのくらい？」 | ai_consultation | AI相談続行 | 同上。AI応答にSALARY_DATAが参照される。「看護師の平均年収は...」等の回答 | PASS |
| FT4-025 | 「残業少ないところ」 | il_facility_type | QR再表示 | phase=il_facility_type → L5668条件ヒット。`unexpectedTextCount++`。return null → QR再表示（施設タイプ選択ボタン） | PASS |
| FT4-026 | 「日勤のみ希望」 | il_workstyle | QR再表示 | phase=il_workstyle → L5669条件ヒット。`unexpectedTextCount++`。return null → QR再表示（働き方選択ボタン） | PASS |
| FT4-027 | 「転職迷ってる」 | welcome | NLP地名検出試行→失敗→QR再表示 | phase=welcome → L5564条件でNLP発動。prefMap/cityMapにヒットなし → L5668以降のphaseチェックにwelcomeなし → L5692到達。`unexpectedTextCount++`。return null | PASS |
| FT4-028 | 「相談したい」 | matching_preview | TEXT_TO_POSTBACKではなくAI相談へ | phase=matching_preview → L5663でAI相談に回される。TEXT_TO_POSTBACKの「相談したい」→`consult=start`はphaseToExpectedPrefixが空オブジェクトのため発動しない（L5677-5678: `phaseToExpectedPrefix`は`{}`） | PASS |
| FT4-029 | 「訪問看護に興味ある」 | ai_consultation | AI相談続行 | AI応答。訪問看護の一般情報を回答。具体的な紹介は小林病院以外はしない旨 | PASS |
| FT4-030 | 「有給取れるところ」 | matching_browse | AI相談に回す | phase=matching_browse → AI相談。有給取得率等の一般的な回答 | PASS |

---

### D. 誤字/曖昧入力（10件）

| ID | 入力テキスト | phase | 期待動作 | 実際の動作 | 結果 |
|----|-------------|-------|---------|-----------|------|
| FT4-031 | 「とうきょう」 | il_area | ひらがな→東京を検出したい | prefMap/cityMapは漢字のみ。`text.includes('東京')` → false。全prefMap/cityMap走査 → ヒットなし。`unexpectedTextCount++`。return null → **QR再表示** | FAIL |
| FT4-032 | 「かながわ」 | il_area | ひらがな→神奈川を検出したい | 同上。ひらがな非対応。`unexpectedTextCount++`。QR再表示 | FAIL |
| FT4-033 | 「よこはま」 | il_area | ひらがな→横浜を検出したい | cityMapに「よこはま」なし。未検出。QR再表示 | FAIL |
| FT4-034 | 「びょういん」 | il_facility_type | 施設タイプ検出→不可 | handleFreeTextInputに施設タイプのNLPなし。L5668条件ヒット。`unexpectedTextCount++`。QR再表示 | FAIL |
| FT4-035 | 「トウキョウ」 | il_area | カタカナ→東京を検出したい | カタカナ非対応。未検出。QR再表示 | FAIL |
| FT4-036 | 「カナガワ」 | il_area | カタカナ→神奈川を検出したい | 同上。未検出。QR再表示 | FAIL |
| FT4-037 | 「東京都」 | il_area | 「東京」を含む→検出 | `text.includes('東京')` → true（「東京都」は「東京」を含む）。tokyo確定 | PASS |
| FT4-038 | 「神奈川県」 | il_area | 「神奈川」を含む→検出 | `text.includes('神奈川')` → true。kanagawa確定 | PASS |
| FT4-039 | 「yokohama」 | il_area | ローマ字→非対応 | 英字非対応。未検出。QR再表示 | FAIL |
| FT4-040 | 「東京 神奈川 どっちも」 | il_area | 複数地名→最初のヒットで確定 | prefMap走査で「東京」が先にヒット。tokyo確定。神奈川は無視 | WARN |

**重大な問題**: ひらがな（FT4-031〜033）、カタカナ（FT4-035〜036）、ローマ字（FT4-039）での地名入力は全く検出できない。NLPと呼べるレベルの処理ではなく、単純な漢字部分文字列マッチに過ぎない。ユーザーがQuick Replyを使わずテキスト入力した場合、ひらがな入力は十分起こりうる。

---

### E. エリア外テキスト（5件）

| ID | 入力テキスト | phase | 期待動作 | 実際の動作 | 結果 |
|----|-------------|-------|---------|-----------|------|
| FT4-041 | 「福岡」 | il_area | エリア外メッセージ表示 | prefMap `text.includes('福岡')` → true。`entry.prefecture='other'`。return `il_pref_detected_other` → L6683: detectedPref==='other' → `entry.area='undecided_il'`, `entry.areaLabel='全エリア'`。entry.phase='il_subarea'。`buildPhaseMessage('il_subarea')` → L3681: `entry.prefecture==='other'` → **「現在ナースロビーでは、東京・神奈川・千葉・埼玉の求人をご紹介しています。お住まいの地域は準備中です。以下からお選びください」** + QR3択（関東の求人を見る/エリア拡大時に通知/スタッフに相談） | PASS |
| FT4-042 | 「札幌」 | il_area | エリア外メッセージ表示 | cityMap `text.includes('札幌')` → true。`entry.prefecture='other'`。同上のエリア外メッセージ | PASS |
| FT4-043 | 「広島」 | welcome | エリア外メッセージ表示 | prefMap `text.includes('広島')` → true。other確定。welcomeからでもNLP発動。エリア外メッセージ | PASS |
| FT4-044 | 「仙台」 | il_area | エリア外メッセージ表示 | cityMap `text.includes('仙台')` → true。other確定。エリア外メッセージ | PASS |
| FT4-045 | 「鹿児島」 | il_area | エリア外メッセージ表示 | prefMap `text.includes('鹿児島')` → true。other確定。エリア外メッセージ。QR3択表示 | PASS |

**エリア外処理の評価**: 正直に対応エリア外であることを伝え、3つの選択肢（関東求人閲覧/通知オプトイン/スタッフ相談）を提示する設計は良好。職業安定法の観点からも、できないことを正直に伝える姿勢は適切。

---

### F. 攻撃的入力（5件）

| ID | 入力テキスト | phase | 期待動作 | 実際の動作 | 結果 |
|----|-------------|-------|---------|-----------|------|
| FT4-046 | `'; DROP TABLE users;--` | il_area | 安全に処理 | prefMap/cityMap走査 → ヒットなし。`unexpectedTextCount++`。return null → QR再表示。**KVストレージはNoSQL（Cloudflare KV）のためSQLインジェクション自体が成立しない**。テキストはentry内に文字列として格納されるが、SQL文として実行される箇所は存在しない | PASS |
| FT4-047 | `<script>alert('xss')</script>` | il_area | 安全に処理 | prefMap/cityMap走査 → ヒットなし。`unexpectedTextCount++`。QR再表示。LINE Messaging APIはHTMLをレンダリングしないため、XSSは成立しない。Slack通知時にもHTMLタグはそのまま文字列として表示される | PASS |
| FT4-048 | 「あ」×1000（1000文字） | il_area | 安全に処理 | prefMap/cityMap走査（各キーについて`includes`呼び出し）→ 全て不一致。`unexpectedTextCount++`。QR再表示。**パフォーマンス懸念**: prefMap47件+cityMap17件=64回のincludes呼び出しが1000文字文字列に対して実行されるが、V8エンジンでは問題ないレベル | PASS |
| FT4-049 | `{{constructor.constructor('return this')()}}` | il_area | テンプレートインジェクション耐性 | 文字列として処理。`includes`は単なる部分文字列検索のため、プロトタイプ汚染やテンプレートインジェクションは成立しない。QR再表示 | PASS |
| FT4-050 | 空文字列 `""` | il_area | 安全に処理 | prefMap走査 → `"".includes('北海道')` → false（全て）。cityMap走査 → 同様。`unexpectedTextCount++`。QR再表示。**注意**: LINE Messaging APIは空文字列のテキストメッセージを送信しないため、通常このケースは発生しない | PASS |

**セキュリティ評価**: Cloudflare Workers + KV + LINE Messaging APIの構成上、SQLインジェクション・XSS・テンプレートインジェクションの攻撃面は存在しない。自由テキスト入力は文字列としてKVに保存されるのみで、コード実行やHTML描画のコンテキストに渡されない。Slack通知時もBlock Kitではなくプレーンテキストとして送信される。

---

## 集計

| カテゴリ | 件数 | PASS | FAIL | WARN |
|---------|------|------|------|------|
| A. 都道府県名テキスト | 10 | 9 | 0 | 1 |
| B. 都市名テキスト | 10 | 8 | 2 | 0 |
| C. 条件テキスト | 10 | 10 | 0 | 0 |
| D. 誤字/曖昧入力 | 10 | 2 | 7 | 1 |
| E. エリア外テキスト | 5 | 5 | 0 | 0 |
| F. 攻撃的入力 | 5 | 5 | 0 | 0 |
| **合計** | **50** | **39** | **9** | **2** |

**通過率: 78%（39/50）、WARN含む: 82%（41/50）**

---

## 検出された不具合・改善提案

### BUG-NLP-01: ひらがな/カタカナ地名が検出できない（重要度: 中）

- **影響**: FT4-031〜036の6件がFAIL
- **原因**: `handleFreeTextInput`は漢字の部分文字列一致のみ。ひらがな→漢字、カタカナ→漢字の変換処理がない
- **対象ユーザー**: スマホのフリック入力で変換せずに送信するユーザー
- **修正案**: prefMap/cityMapにひらがな・カタカナのキーを追加するか、入力テキストをひらがな→漢字変換するマッピングテーブルを追加
```javascript
const kanaMap = {
  'とうきょう': '東京', 'かながわ': '神奈川', 'ちば': '千葉',
  'さいたま': 'さいたま', // 既にcityMapにある
  'よこはま': '横浜', 'かわさき': '川崎', 'ふじさわ': '藤沢',
  // カタカナも同様に追加
};
// text前処理でkanaMapを適用してからprefMap/cityMap走査
```

### BUG-NLP-02: cityMapの登録都市が少ない（重要度: 低〜中）

- **影響**: FT4-013（川越）、FT4-020（厚木）がFAIL
- **原因**: cityMapに17都市しか登録されていない。神奈川県内でも厚木・秦野・大和・海老名・茅ヶ崎・鎌倉・平塚・横須賀が未登録
- **修正案**: `AREA_LABELS`に存在する都市名をcityMapにも追加
```javascript
// 追加候補（神奈川県）
'厚木': 'kanagawa', '秦野': 'kanagawa', '大和': 'kanagawa',
'海老名': 'kanagawa', '茅ヶ崎': 'kanagawa', '鎌倉': 'kanagawa',
'平塚': 'kanagawa', '横須賀': 'kanagawa', '小田原': 'kanagawa',
// 追加候補（埼玉県）
'川越': 'saitama', '所沢': 'saitama', '越谷': 'saitama', '春日部': 'saitama',
// 追加候補（千葉県）
'市川': 'chiba', '松戸': 'chiba', '浦安': 'chiba',
// 追加候補（東京都）
'吉祥寺': 'tokyo', '三鷹': 'tokyo', '調布': 'tokyo', '府中': 'tokyo',
```

### BUG-NLP-03: ローマ字入力非対応（重要度: 低）

- **影響**: FT4-039（yokohama）がFAIL
- **原因**: ローマ字→日本語変換なし
- **優先度低**: 日本語ネイティブユーザーがローマ字で地名入力するケースは稀

### WARN-NLP-01: 複数地名入力時の挙動（重要度: 低）

- **影響**: FT4-010、FT4-040
- **動作**: prefMapの走査順（挿入順）で最初にヒットした都道府県が確定される
- **改善案**: 対応エリア（tokyo/kanagawa/chiba/saitama）を優先的にマッチさせるロジックの追加

### GOOD-01: エリア外対応は適切

- エリア外ユーザーに正直に「準備中」と伝える
- 3つの代替選択肢（関東求人閲覧/通知オプトイン/スタッフ相談）を提示
- 通知オプトイン時にSlack通知+ナーチャリング移行

### GOOD-02: unexpectedTextCountによる段階的フォールバック

- 1回目: QR再表示（「下のボタンからお選びいただけますか？」）
- 2回目: フォールバック3択（やり直す/求人を見せてほしい/人に相談したい）
- 3回目: 自動handoff（「担当者に引き継ぎました」）
- 3段階のエスカレーションは適切

### GOOD-03: セキュリティは問題なし

- SQL/XSS/テンプレートインジェクション: アーキテクチャ上成立しない
- 長文入力: パフォーマンス影響は軽微
- 空文字列: LINE API側で防止される

### GOOD-04: AI相談フローは堅牢

- matching_preview/matching_browseからの自由テキスト → AI相談に自動ルーティング
- ai_consultationフェーズでの連続会話対応
- 5ターン制限+延長の仕組み
- AI応答はctx.waitUntilでバックグラウンド実行（Webhookタイムアウト回避）
- 4段階フォールバック（OpenAI → Claude Haiku → Workers AI → テンプレート応答）

---

## 検証項目別サマリ

| # | 検証項目 | 判定 | 詳細 |
|---|---------|------|------|
| 5 | 自由テキストNLP | PARTIAL | 漢字地名は検出OK。ひらがな/カタカナ/ローマ字は全滅。cityMapの登録不足あり |
| 6 | エリア外正直メッセージ | PASS | 「準備中です」と正直に伝え、3択を提示。Slack通知もあり |
| 12 | AI相談 | PASS | matching後の自由テキストはAI相談に適切にルーティング。多層フォールバック完備 |
