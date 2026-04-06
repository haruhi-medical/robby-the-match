# LINE Bot 深層調査・改修計画書

**作成日:** 2026-04-06
**対象ファイル:** `api/worker.js`（6,911行）
**ベース情報:** 400件全国シミュレーション最終レポート（`robby_line_simulation/final_report.md`）

---

## 1. 現状の既知問題一覧（コード分析 + シミュレーション結果）

### Critical（即時対応）

| # | 問題 | 該当行 | 影響 |
|---|------|--------|------|
| C1 | **「その他の地域」選択時にエリア外であることを一切告知しない** | L3619（`il_pref=other`）→ L4958（`other: 'undecided'`）→ L3661-3676（il_subareaで施設種別質問へ直行） | 400件中253件（63.2%）がGEO_LOCK。ユーザーは全5ステップ完走後に関東求人を見せられ混乱 |
| C2 | **「24,488件」等の全国施設数を表示** | L3609-3612（`countCandidatesD1({}, env)`で全件カウント） | 全国の数字を見せて関東しか出さないのは虚偽表示に近い |
| C3 | **緊急キーワード検出が一切ない** | `handleFreeTextInput`（L5275-5354）にキーワードチェックなし | 「限界」「辞めたい」「死にたい」「パワハラ」等に無反応。人命リスク |
| C4 | **スタンプ受信に未対応** | worker.js全体にsticker/スタンプの処理なし | LINEの基本UXとして致命的。スタンプ送信→完全無視 |
| C5 | **自由テキスト入力を全フェーズで拒否** | L5327-5332（il_area〜matching_preview全てで`return null`→Quick Reply再表示） | INPUT_LOCK 39件。LINEはチャットUIなのにテキスト無視 |

### High（重要）

| # | 問題 | 該当行 | 影響 |
|---|------|--------|------|
| H1 | **同一テキスト3回入力→handoffは実装済みだが、NLP的テキスト解析なし** | L6252-6258（unexpectedTextCount >= 3 → handoff） | 3回待つ前に1回目でテキスト理解を試みるべき |
| H2 | **LIFF経由の旧ウェルカムメッセージに神奈川県のみの選択肢** | L2804-2810（横浜/相模原/湘南/横須賀/県西/東京のみ） | 千葉・埼玉の選択肢がない。旧フォーマットが残存 |
| H3 | **`il_pref=other`→`undecided`→マッチングで全エリア検索** | L4958（`other: 'undecided'`）→ L595（`undecided`はフィルタなし） | エリア外ユーザーに関東全域の求人を無差別提示 |
| H4 | **エリア拡大通知のオプトイン機能なし** | 該当コード不在 | エリア外ユーザーのリード回収手段がゼロ |
| H5 | **怒り/不満の感情検出なし** | `handleFreeTextInput`（L5275-5354）に感情分析なし | 怒っているユーザーをBotで無限ループさせる |
| H6 | **ai_consultationの「神奈川県の給与データを使う」固定** | L6381（systemPrompt内: 「神奈川県の給与・求人データを使う」） | 千葉/埼玉/東京選択者にも神奈川データで回答 |

### Medium（中程度）

| # | 問題 | 該当行 | 影響 |
|---|------|--------|------|
| M1 | **ICU/NICU/美容/透析/OP室のサブカテゴリなし** | L3686-3700（il_departmentの選択肢に専門診療科不足） | JOB_MATCH_FAIL 16件 |
| M2 | **il_workstyleに「時短勤務」なし** | L3704付近（il_workstyleの選択肢） | ペルソナ「ミサキ」的属性を拾えない |
| M3 | **セッション24h超放置時の再開確認なし** | `createLineEntry`（L3390付近）にTTL管理なし | 離脱→再訪問時に途中のフェーズから再開し混乱 |
| M4 | **ADJACENT_AREAS による隣接エリア拡大の告知なし** | L4474-4487（隣接エリア拡大時にユーザーに伝えない） | 「横須賀で探したのに湘南の求人が出た」と混乱 |
| M5 | **AREA_CITY_MAP に `kensei` キーがない（旧フォーマット）** | L2808（`il_area=kensei`）vs L570（`odawara_kensei`のみ） | LIFF経由で`kensei`が来ると市区町村フィルタが空で全件ヒット |

---

## 2. 6名スペシャリスト担当割り当て

---

### Specialist 1: エリア外対応（GEO_LOCK修正）

**担当範囲:** 「その他の地域」選択時の正直な説明文 + エリア拡大通知オプトイン

**調査対象ファイル・行:**
- `api/worker.js` L3608-3622: `il_area` の buildPhaseMessage（「その他の地域」ボタン定義）
- `api/worker.js` L3625-3677: `il_subarea` の buildPhaseMessage（other選択後の遷移）
- `api/worker.js` L4942-4964: `handleLinePostback` の `il_pref` 処理（`other` → `undecided` マッピング）
- `api/worker.js` L586-640: `countCandidatesD1`（候補数カウント。`undecided`時にフィルタなし）
- `api/worker.js` L5490-5502: follow時ウェルカムメッセージ（対応エリア未記載）

**修正内容:**
1. `il_pref=other` 選択時、`il_subarea` で「現在は東京・神奈川・千葉・埼玉のみ対応中」メッセージを表示
2. 3つの選択肢を提示: [関東の求人を見てみる] [エリア拡大時に通知] [スタッフに直接相談]
3. 「通知希望」選択 → KVに `notify:{userId}` を保存（都道府県名も記録）
4. 「スタッフに相談」選択 → 即Slack通知 + handoff遷移
5. follow時ウェルカム文（L5492）に「対応エリア: 東京/神奈川/千葉/埼玉」を追記
6. `il_area` の候補件数表示（L3609-3612）を関東限定の件数に修正
7. `il_subarea` の `other` 分岐で5ステップ完走させず**即座に分岐**させる

**修正しないこと:**
- AREA_CITY_MAP自体の拡張（エリア拡大は経営判断）
- 広告ジオターゲティング（Bot外の施策）

**完了基準:**
- [ ] `il_pref=other` タップ → 「関東のみ対応中」メッセージが表示される
- [ ] 通知希望 → KVに保存される（`notify:{userId}` キーで検証）
- [ ] 相談希望 → Slackに通知が飛ぶ
- [ ] 関東を見る → 通常の `il_facility_type` フローに進む
- [ ] follow時ウェルカムに対応エリアが明記されている
- [ ] `il_area` の件数表示が関東限定になっている

---

### Specialist 2: 自由テキストNLP

**担当範囲:** intakeフェーズ中の自由テキスト解析（都道府県名・市区町村名・施設種別・働き方キーワード）

**調査対象ファイル・行:**
- `api/worker.js` L5275-5354: `handleFreeTextInput` 関数全体
- `api/worker.js` L5327-5332: intake_light/matching中のテキスト→`return null`（Quick Reply再表示）
- `api/worker.js` L5335-5349: `phaseToExpectedPrefix`（現在は空オブジェクト＝未実装）
- `api/worker.js` L3013-3042: `TEXT_TO_POSTBACK` マッピング辞書
- `api/worker.js` L6251-6286: unexpectedTextCount による3段階フォールバック

**修正内容:**
1. **都道府県名辞書**を作成（47都道府県 + 主要市区名50件程度）
   - エリア内: 「横浜」→ `il_pref=kanagawa` + `il_area=yokohama_kawasaki` に自動マッピング
   - エリア外: 「大阪」「名古屋」「北海道」→ エリア外告知メッセージ（Specialist 1の成果物を呼び出し）
2. **施設種別キーワード辞書**（`il_facility_type` フェーズ用）
   - 「ICU」「救急」→ `hospital_acute`
   - 「訪問」→ `visiting`
   - 「老健」「特養」→ `care`
3. **働き方キーワード辞書**（`il_workstyle` フェーズ用）
   - 「日勤のみ」「日勤だけ」→ `day`
   - 「夜勤」→ `twoshift`
   - 「パート」「非常勤」→ `part`
4. **フェーズ対応テキスト解析**: `handleFreeTextInput` 内で現在のphaseに応じた辞書を参照
   - `il_area`/`il_subarea` フェーズ → 地名辞書
   - `il_facility_type` フェーズ → 施設種別辞書
   - `il_workstyle` フェーズ → 働き方辞書
5. テキストが辞書にマッチ → 対応するpostbackデータを生成して `handleLinePostback` に渡す
6. マッチしない → 従来通り `unexpectedTextCount++`

**修正しないこと:**
- OpenAI APIを使った文脈理解（Phase 3は将来対応）
- ai_consultation内のテキスト処理（既に正常動作）

**完了基準:**
- [ ] `il_area` フェーズで「横浜」入力 → 神奈川県・横浜川崎エリアとして処理される
- [ ] `il_area` フェーズで「大阪」入力 → エリア外メッセージが表示される
- [ ] `il_facility_type` フェーズで「訪問看護」入力 → visiting として処理される
- [ ] `il_workstyle` フェーズで「日勤のみ」入力 → day として処理される
- [ ] 辞書にない自由テキスト → 従来通り Quick Reply 再表示（既存動作が壊れない）
- [ ] 全フェーズで unexpectedTextCount のリセットが正しく動作

---

### Specialist 3: マッチング品質

**担当範囲:** AREA_CITY_MAP検証 + マッチングSQL品質 + エッジケース

**調査対象ファイル・行:**
- `api/worker.js` L565-578: `AREA_CITY_MAP` 定義（全キーと市区町村の網羅性確認）
- `api/worker.js` L586-640: `countCandidatesD1`（D1 SQL組み立て）
- `api/worker.js` L4456-4555: `generateLineMatching`（EXTERNAL_JOBSマッチング + D1フォールバック）
- `api/worker.js` L4488-4532: 3条件フィルタ（workStyle/facilityType/matchCount）
- `api/worker.js` L4534-4547: 施設タイプハードフィルタ
- `api/worker.js` L4549-4600: D1フォールバック
- `api/worker.js` L4763-4806: `buildMatchingMessages`（結果0件時の処理）
- `api/worker_facilities.js`: FACILITY_DATABASE / EXTERNAL_JOBS の実データ確認

**調査項目:**
1. **AREA_CITY_MAP の完全性**
   - `yokosuka_miura` に逗子市・葉山町が含まれていない（L569: shonan_kamakuraに含まれている）→ 正しいか？
   - `odawara_kensei` に平塚市・秦野市・伊勢原市が含まれている（L570）→ 湘南ではなく県西扱いでよいか？
   - `kensei`（旧キー、L2808）が AREA_CITY_MAP に存在しない → LIFF経由で来ると空マッチ
2. **D1 SQLインジェクション安全性**: L590-635のパラメータバインドが正しいか
3. **マッチング精度**
   - `workStyle=day` の判定（L4497-4498: `!j.t || !j.t.includes('夜勤')`）→ 「夜勤なし」テキストがある求人を誤除外しないか
   - `facilityType=hospital` の逆マッチ（L4515-4517: 訪問/クリニック/介護でなければ病院）→ 精度検証
   - `hospitalSubType`（急性期/回復期/慢性期）がマッチングに使われていない → 使うべきか
4. **0件時の隣接エリア拡大**（L4474-4487）
   - `ADJACENT_AREAS` の定義確認（全キーに隣接エリアが設定されているか）
   - 拡大時にユーザーに「隣接エリアに広げました」と告知していない → 告知追加
5. **千葉・埼玉のマッチング品質**
   - `chiba_all`/`saitama_all` → AREA_CITY_MAP で空配列 → prefectureフィルタのみ → D1に千葉/埼玉の施設データがあるか

**修正内容:**
1. `kensei` → `odawara_kensei` のエイリアス追加（L2808互換性修正）
2. AREA_CITY_MAP の市区町村漏れ修正（調査結果に基づく）
3. `hospitalSubType` をD1検索に反映（急性期→病床機能「高度急性期」「急性期」でフィルタ）
4. 隣接エリア拡大時の告知メッセージ追加
5. 0件時メッセージの改善（「条件を緩めて再検索」ボタン追加）

**完了基準:**
- [ ] AREA_CITY_MAP の全キーが EXTERNAL_JOBS / D1 と整合している
- [ ] `kensei` キーでマッチングしても正しい結果が返る
- [ ] 千葉県・埼玉県選択時にD1から施設が返る
- [ ] 隣接エリア拡大時にユーザーに告知される
- [ ] `hospitalSubType=急性期` 選択時に回復期病院が上位に来ない
- [ ] SQLインジェクション不可能であることを確認

---

### Specialist 4: handoff/人間引き継ぎ

**担当範囲:** handoffフロー全体監査 + 緊急キーワード検出 + Slack通知品質

**調査対象ファイル・行:**
- `api/worker.js` L4255-4294: handoff関連 buildPhaseMessage（phone_check/phone_time/handoff）
- `api/worker.js` L4808-4910: `sendHandoffNotification`（Slack通知構築）
- `api/worker.js` L5110-5120: handoff postbackハンドラ
- `api/worker.js` L5566-5575: handoff中のpostbackガード
- `api/worker.js` L6101-6150: handoff中のテキスト→Slack転送
- `api/worker.js` L6252-6258: unexpectedText 3回→自動handoff
- `api/worker.js` L6336-6338: handoff遷移時のSlack通知トリガー

**調査項目:**
1. **緊急キーワード検出の新規実装**
   - キーワードリスト: 「限界」「辞めたい」「死にたい」「パワハラ」「セクハラ」「被災」「いじめ」「うつ」
   - 検出位置: `handleFreeTextInput` の冒頭（全フェーズ共通チェック）
   - 検出時: 即Slack通知（`sendEmergencyNotification`新関数）+ ユーザーに「すぐに担当者におつなぎします」メッセージ
   - handoffフェーズに遷移
2. **handoff中のBot沈黙の完全性**
   - L5566-5575: postbackガード（FAQ以外ブロック）→ 正しく動作するか
   - L6101-6118: テキスト→Slack転送のみ → LINE応答なし → 正常
   - `welcome=start` 等のpostbackがhandoff中にブロックされるか確認
3. **Slack通知の品質**
   - L4877-4907: 通知テキストに必要情報が揃っているか
   - `!reply` コマンドの使い方が明記されているか
   - 通知先チャンネル（`C0AEG626EUW`）が正しいか
4. **handoff理由の5条件**（L4851-4857）が網羅的か
   - 追加すべき: 「緊急キーワード検出」「エリア外+urgent」「ループ3回」
5. **handoff後の再エンゲージ導線**
   - handoffメッセージ（L4283-4293）にFAQ Quick Replyがない → 追加すべき
   - handoff後にユーザーが「やっぱりBotで見たい」と言った場合の復帰パスがあるか

**修正内容:**
1. 緊急キーワード辞書 + 検出ロジック追加（`handleFreeTextInput` 冒頭）
2. `sendEmergencyNotification` 関数の新規作成（Slack通知に `🚨 緊急` プレフィックス）
3. handoff理由に「緊急キーワード」「エリア外+urgent」を追加
4. handoffメッセージにFAQ Quick Reply追加（L4290-4293）
5. Slack通知にユーザーの全会話履歴（直近10件）を含める

**完了基準:**
- [ ] 「辞めたい」入力 → 即Slack通知 + handoff遷移
- [ ] 「限界」入力 → 同上
- [ ] handoff中にテキスト送信 → Slackに転送 + LINEは沈黙
- [ ] handoff中に `welcome=start` postback → ブロックされる
- [ ] Slack通知に `!reply {userId} メッセージ` の使い方が記載されている
- [ ] 緊急キーワード検出時のSlack通知に `🚨` マークが付く
- [ ] handoffメッセージにFAQボタンが表示される

---

### Specialist 5: AI相談/UX

**担当範囲:** AI consultation フロー監査 + エラーハンドリング + 会話品質

**調査対象ファイル・行:**
- `api/worker.js` L6366-6460: `handleLineAIConsultation` 関数全体
- `api/worker.js` L6376-6397: AI systemPrompt（ロビーの性格設定）
- `api/worker.js` L6399-6480: 多層フォールバック（OpenAI → Claude Haiku → Workers AI → 定型文）
- `api/worker.js` L6153-6243: AI consultation のPush API送信 + エラーハンドリング
- `api/worker.js` L6370-6374: ターン数制限（5ターン/延長8ターン）
- `api/worker.js` L4140-4150: `consult=handoff` の遷移
- `api/worker.js` L5310-5313: ai_consultation中の自由テキスト → `ai_consultation_reply`

**調査項目:**
1. **systemPromptの品質**
   - L6381: 「神奈川県の給与・求人データを使う」→ 千葉/埼玉/東京ユーザーにも神奈川固定は不適切
   - `entry.areaLabel` を使ってエリア別データに切り替えるべき
   - 給与データ（`SALARY_DATA`）の内容確認 → 関東全域のデータがあるか
2. **多層フォールバックの信頼性**
   - OpenAI 8秒タイムアウト（L6407）→ 十分か
   - Claude Haiku のモデル名（L6437: `claude-haiku-4-5-20251001`）→ 最新か確認
   - Workers AI フォールバック → 存在するか確認（レポートでは「不安定」とされている）
   - 全失敗時の定型文（L6216-6225）→ ユーザー体験として十分か
3. **ターン数制限の UX**
   - 5ターンで「担当者に聞いてみましょうか？」→ 表示されるか確認
   - 延長+3ターンの仕組みが正しく動作するか
4. **Push API の信頼性**
   - L6182-6200: Push送信失敗時のSlack通知 → 正しく動作するか
   - L6210-6231: 安全メッセージ Push → 二重フォールバック → Slack → OK
5. **AI応答の安全性**
   - 施設の個別評判・口コミを答えないルール → systemPromptにあるが実効性は？
   - 「転職しなさい」等の断定的アドバイスを防止できているか

**修正内容:**
1. systemPromptのエリア情報を `entry.prefecture` / `entry.areaLabel` で動的化
2. 千葉/埼玉/東京の給与データを追加（`SALARY_DATA` に不足があれば）
3. AI応答の後にQuick Reply追加（「もっと聞く」「担当者に相談」「求人を見る」）
4. ターン制限メッセージの改善（残りターン数を表示しない代わりに自然な形で担当者提案）
5. Workers AI フォールバックのモデル名を最新に更新

**完了基準:**
- [ ] 東京選択ユーザーにAI相談 → 「東京の」給与データで回答される
- [ ] OpenAI API タイムアウト → Claude Haiku にフォールバック → ユーザーに応答届く
- [ ] 全AI失敗 → 安全メッセージが送信される + Slack通知
- [ ] 5ターン目 → 担当者提案が表示される
- [ ] AI応答の後にQuick Replyが常に付いている
- [ ] 施設名を含む質問 → 「担当者に確認します」と返答（口コミを語らない）

---

### Specialist 6: Welcome/Entry/離脱防止

**担当範囲:** 全エントリルート監査 + 再エントリ処理 + ナーチャリング

**調査対象ファイル・行:**
- `api/worker.js` L5413-5530: follow イベント（通常 + LIFF経由）
- `api/worker.js` L2770-2834: `/api/link-session` エンドポイント（LIFF橋渡し）
- `api/worker.js` L3043-3140: `buildSessionWelcome`（source別ウェルカム分岐）
- `api/worker.js` L5940-6005: テキストメッセージ内 session_id / 旧引き継ぎコード検出
- `api/worker.js` L5930-5935: KVエントリなし時の新規セッション作成
- `api/worker.js` L3380-3420: `createLineEntry`（初期エントリ構造）
- `api/worker.js` L5533-5550: unfollowイベント
- `api/worker.js` L4283-4294: handoffメッセージ（再エンゲージ導線なし）
- `api/worker.js` L5042-5050: nurture postback ハンドラ

**調査項目:**
1. **エントリルートの完全性**
   - 通常follow（L5475-5503）→ ウェルカム4選択肢 → 正常
   - LIFF経由follow（L5442-5474）→ セッション復元 → 正常か確認
   - dm_text方式（L5940-6005）→ UUID検出 → 正常か確認
   - 旧引き継ぎコード（L6007-6092）→ 6文字コード → matching直行 → 正常か確認
   - KVエントリなしでテキスト受信（L5932-5935）→ `il_area` に遷移 → ウェルカムメッセージなし!
2. **再フォロー（ブロック解除）時の処理**
   - L5414-5423: phaseを `welcome` にリセット → OK
   - 既存の回答データ（area/workStyle等）は保持される → **途中のデータでwelcome表示は混乱しないか？**
3. **離脱防止策**
   - `nurture_warm`/`nurture_subscribed` の実装確認
   - ナーチャリングCronの存在確認（KV `nurture:{userId}` の利用状況）
   - `nurture_stay` の次フェーズが定義されているか
4. **スタンプ受信対応**（新規実装）
   - message.type === "sticker" のハンドラが存在しない
   - 実装: フェーズに応じた軽い応答 + 現フェーズのQuick Reply再表示
5. **「まだ見てるだけ」「まず相談したい」の遷移先**（L5495-5498のwelcome postback）
   - `welcome=browse` / `welcome=consult` が正しいフェーズに遷移するか確認

**修正内容:**
1. KVエントリなし+テキスト受信時（L5932-5935）にウェルカムメッセージを送信
2. スタンプ受信ハンドラ追加（sticker event → 「ありがとうございます！」+ 現フェーズQuick Reply）
3. 再フォロー時に既存回答データをクリアするか保持するかのロジック明確化
4. `nurture_warm` → `nurture_subscribed` → 定期配信の動線確認と修正
5. handoffメッセージにFAQ Quick Reply追加（Specialist 4と連携）
6. 24時間以上経過したセッションの再開時に「おかえりなさい」メッセージ + 継続/やり直し選択肢

**完了基準:**
- [ ] 全5つのエントリルートで正しいウェルカムメッセージが表示される
- [ ] KVなし+テキスト送信 → ウェルカムメッセージが表示される（無言にならない）
- [ ] スタンプ送信 → 応答がある + Quick Replyが表示される
- [ ] ブロック解除→再フォロー → 適切なウェルカムメッセージが表示される
- [ ] `welcome=browse` / `welcome=consult` → 正しいフェーズに遷移
- [ ] 24時間放置後のテキスト送信 → 再開確認メッセージが表示される

---

## 3. Quality Gates（品質ゲート）

### 全スペシャリスト共通

| ゲート | 基準 |
|--------|------|
| コンパイル | worker.js が `wrangler deploy --dry-run --config wrangler.toml` でエラーなし |
| 既存テスト | 既存の正常フロー（関東4都県 standard ケース）が壊れていない |
| LINE API制限 | 1レスポンスあたりメッセージ数 <= 5（LINE API制限） |
| Quick Reply制限 | 1メッセージあたりQuick Reply items <= 13（LINE API制限） |
| KV整合性 | 新しいKVキーの TTL が設定されている（無期限保存の禁止） |
| コードサイズ | worker.js の行数が 7,500行を超えない（現在6,911行） |
| Slack通知 | 全ての新しいSlack通知が `env.SLACK_BOT_TOKEN` チェック付き |

### スペシャリスト別ゲート

| # | 担当 | 合格基準 |
|---|------|---------|
| 1 | エリア外対応 | 「その他の地域」→5ステップ完走の導線が**完全に遮断**されている |
| 2 | 自由テキストNLP | 関東4都県の主要20市区名が正しくマッピングされる |
| 3 | マッチング品質 | 神奈川5エリア + 東京2エリア + 千葉 + 埼玉の全9パターンで求人が返る |
| 4 | handoff/引き継ぎ | 緊急キーワード8語が全て検出→Slack通知される |
| 5 | AI相談/UX | AI全失敗 → ユーザーに必ず応答が届く（無応答ゼロ） |
| 6 | Welcome/Entry | 5つのエントリルート全てでウェルカムが表示される |

---

## 4. リスクエリア（変更による既存機能破壊リスク）

### HIGH RISK

| リスク | 影響範囲 | 対策 |
|--------|---------|------|
| `handleLinePostback` の `il_pref=other` 分岐変更 | 既存の「その他→undecided→マッチング」フローが壊れる | 「関東を見る」選択時は従来と同じ `undecided` パスを維持 |
| `handleFreeTextInput` への NLP 追加 | 既存の unexpectedTextCount ロジックに干渉 | NLP マッチ時のみ postback にリダイレクト。マッチしない場合は従来パス |
| `countCandidatesD1` の件数変更 | 全フェーズの候補件数表示に影響 | `il_area` のみ変更。`il_subarea` 以降は既存ロジック維持 |
| handoff フェーズへの自動遷移追加 | 通常会話中に誤って handoff に入るリスク | 緊急キーワードは完全一致 or 「文頭/文末」パターンで誤検出を防止 |

### MEDIUM RISK

| リスク | 影響範囲 | 対策 |
|--------|---------|------|
| AREA_CITY_MAP の修正 | マッチング結果が変わる | 変更前後でマッチング件数を比較ログ出力 |
| スタンプハンドラ追加 | 未知のevent.messageタイプへの影響 | `event.message.type === "sticker"` の明示的チェックのみ |
| AI systemPrompt のエリア動的化 | AI応答品質が変わる可能性 | テスト: 東京/千葉/埼玉/神奈川それぞれでAI相談テスト |
| follow時ウェルカム文変更 | 既存ユーザーの初回体験変化 | テキスト変更のみ。Quick Reply構造は維持 |

### LOW RISK

| リスク | 影響範囲 | 対策 |
|--------|---------|------|
| KV新キー（`notify:{userId}`）追加 | KV容量 | TTL設定（90日） |
| Slack通知の追加 | Slack API レートリミット | 既存と同じ `fetch` パターン。waitUntil使用 |
| handoffメッセージへのQuick Reply追加 | 表示のみ変更 | 既存テキストは維持。Quick Replyを末尾に追加 |

---

## 5. 依存関係と作業順序

```
Specialist 1（エリア外対応）  ←── 最優先。他の全修正の前提条件
    ↓
Specialist 2（自由テキストNLP） ←── Specialist 1 のエリア外メッセージを呼び出す
    ↓（並列可能）
Specialist 3（マッチング品質）  ←── 独立して作業可能
Specialist 4（handoff/引き継ぎ） ←── 独立して作業可能（ただしSpecialist 1のhandoff導線と整合性確認）
Specialist 5（AI相談/UX）       ←── 独立して作業可能
Specialist 6（Welcome/Entry）    ←── Specialist 1 のウェルカム文変更と整合性確認
```

**推奨作業順序:**
1. Specialist 1 → 2 → 6（エリア外→テキスト→エントリ: 直列）
2. Specialist 3, 4, 5（マッチング、handoff、AI: 並列）
3. 全員の成果物を統合テスト

---

## 6. テストシナリオ（統合テスト用）

### 最低限テストすべき20シナリオ

| # | シナリオ | 期待結果 |
|---|---------|---------|
| 1 | 新規follow → 「求人を探す」 | ウェルカム + il_area 表示（対応エリア明記） |
| 2 | il_area → 「その他の地域」 | エリア外メッセージ + 3選択肢 |
| 3 | エリア外 → 「通知希望」 | KV保存 + お礼メッセージ |
| 4 | エリア外 → 「スタッフに相談」 | Slack通知 + handoff |
| 5 | エリア外 → 「関東を見る」 | 通常フロー（il_facility_type）|
| 6 | il_area フェーズで「横浜」入力 | 神奈川・横浜川崎として処理 |
| 7 | il_area フェーズで「名古屋」入力 | エリア外メッセージ |
| 8 | 神奈川・横浜川崎 → 急性期 → 日勤 → すぐ → matching_preview | 横浜/川崎の急性期病院が表示 |
| 9 | 千葉県 → こだわりなし → 日勤 → すぐ → matching_preview | 千葉の施設が表示 |
| 10 | matching 0件 | 隣接エリア拡大告知 + 担当者紹介ボタン |
| 11 | 「辞めたい」入力（任意フェーズ） | 即Slack通知 + handoff |
| 12 | 「限界」入力 | 同上 |
| 13 | 同一テキスト3回入力 | Stage 1→2→3 + handoff |
| 14 | handoff中にテキスト送信 | Slack転送 + LINE沈黙 |
| 15 | AI相談 → 5ターン | 担当者提案メッセージ |
| 16 | AI全フォールバック失敗 | 安全メッセージ送信 |
| 17 | スタンプ送信 | 応答 + Quick Reply再表示 |
| 18 | LIFF経由follow | セッション復元 + カスタムウェルカム |
| 19 | 旧6文字コード（期限切れ） | エラーメッセージ + il_area |
| 20 | ブロック解除→再follow | ウェルカムメッセージ |

---

*本計画書は `api/worker.js` のコード分析と400件シミュレーション結果に基づき作成。*
*各スペシャリストは担当範囲の行番号を起点に調査を開始すること。*
