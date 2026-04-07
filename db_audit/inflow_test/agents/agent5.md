# Agent 5: handoffフロー + 緊急キーワード + 電話番号収集

> 担当検証項目: #4 緊急キーワード / #8 電話番号収集 / #9 handoffメッセージ / #3 10件上限導線 / #19 0件導線
> テストケース: 50件（FT5-001 〜 FT5-050）
> 対象コード: `api/worker.js`

---

## A. handoff完全フロー: 電話OK（10件 / FT5-001〜FT5-010）

### FT5-001: handoff=ok → 電話OK → 午前中 → 正規携帯番号 → 完了メッセージ

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | postback: `handoff=ok` | phase→`handoff_phone_check` / 「担当者に引き継ぎますね。お電話は控えた方が良いですか？」+ QR[はい（LINEでお願いします）/いいえ（電話OK）] |
| 2 | QRタップ: `phone_check=phone_ok` | phase→`handoff_phone_time` / 「ご都合の良い時間帯はありますか？」+ QR[午前中/午後/夕方以降/いつでもOK] |
| 3 | QRタップ: `phone_time=morning` | phase→`handoff_phone_number` / 「午前中ですね！📞 お電話番号を教えてください。（例: 090-1234-5678）」 |
| 4 | テキスト: `090-1234-5678` | digits=`09012345678` / isPhone=true / entry.phoneNumber=`09012345678` / phase→`handoff` |
| 5 | - | 完了メッセージ: 「担当者に引き継ぎました。24時間以内にご希望の時間帯（午前中）にお電話またはLINEでご連絡いたしますので...」 |
| 6 | - | sendHandoffNotification発火 / Slack通知に「📞 連絡方法: 電話OK（午前中）📱 電話番号: 09012345678」含む |
| 7 | - | KV `handoff:{userId}` 登録（TTL 7日） |

**検証**: 完了メッセージに「24時間以内」+「午前中」が日本語で表示されること。entry.phonePreference=`phone_ok`。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-002: handoff=ok → 電話OK → 午後 → 番号入力 → 完了

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | postback: `handoff=ok` | phase→`handoff_phone_check` |
| 2 | QRタップ: `phone_check=phone_ok` | phase→`handoff_phone_time` |
| 3 | QRタップ: `phone_time=afternoon` | phase→`handoff_phone_number` / 「午後ですね！📞 お電話番号を教えてください。」 |
| 4 | テキスト: `080-9876-5432` | entry.phoneNumber=`08098765432` / phase→`handoff` |
| 5 | - | 「24時間以内にご希望の時間帯（午後）にお電話またはLINE...」 |

**検証**: preferredCallTime=`afternoon` → 完了メッセージに「午後」表示。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-003: handoff=ok → 電話OK → 夕方以降 → 番号入力 → 完了

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | postback: `handoff=ok` | phase→`handoff_phone_check` |
| 2 | QRタップ: `phone_check=phone_ok` | phase→`handoff_phone_time` |
| 3 | QRタップ: `phone_time=evening` | phase→`handoff_phone_number` / 「夕方以降ですね！」 |
| 4 | テキスト: `070-1111-2222` | phase→`handoff` |
| 5 | - | 「24時間以内にご希望の時間帯（夕方以降）にお電話またはLINE...」 |

**検証**: preferredCallTime=`evening` → 完了メッセージに「夕方以降」表示。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-004: handoff=ok → 電話OK → いつでもOK → 番号入力 → 完了

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | postback: `handoff=ok` | phase→`handoff_phone_check` |
| 2 | QRタップ: `phone_check=phone_ok` | phase→`handoff_phone_time` |
| 3 | QRタップ: `phone_time=anytime` | 「いつでもOKですね！📞 お電話番号を教えてください。」 |
| 4 | テキスト: `09012345678`（ハイフンなし） | digits=`09012345678` / isPhone=true / phase→`handoff` |
| 5 | - | 「24時間以内にご希望の時間帯（いつでもOK）にお電話またはLINE...」 |

**検証**: ハイフンなし入力でもバリデーション通過。timeLabels[anytime]=`いつでもOK`表示。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-005: consult=direct_handoff → 電話OK → 午前中 → 番号 → 完了

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | postback: `consult=direct_handoff` | entry.handoffRequestedByUser=true / phase→`handoff_phone_check` |
| 2 | QRタップ: `phone_check=phone_ok` | phase→`handoff_phone_time` |
| 3 | QRタップ: `phone_time=morning` | phase→`handoff_phone_number` |
| 4 | テキスト: `045-123-4567`（固定電話） | digits=`0451234567` / isPhone=true（10桁） / phase→`handoff` |
| 5 | - | 完了メッセージ + Slack通知に「本人から「相談したい」」含む |

**検証**: 固定電話(10桁)もバリデーション通過。handoffReasons に「本人から「相談したい」」が含まれる。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-006: welcome=consult → 電話OK → 午後 → 番号 → 完了（welcomeからの直接handoff）

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | postback: `welcome=consult` | entry.welcomeIntent=`consult` / phase→`handoff_phone_check` |
| 2 | QRタップ: `phone_check=phone_ok` | phase→`handoff_phone_time` |
| 3 | QRタップ: `phone_time=afternoon` | phase→`handoff_phone_number` |
| 4 | テキスト: `090-0000-1111` | phase→`handoff` |
| 5 | - | 完了メッセージ + Slack通知 |

**検証**: welcomeからの直接相談導線が正常にhandoffまで完走すること。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-007: facility付きhandoff（マッチング結果から「この施設について聞く」）

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | postback: `handoff=ok&facility=%E5%B0%8F%E6%9E%97%E7%97%85%E9%99%A2` | entry.interestedFacility=`小林病院` / phase→`handoff_phone_check` |
| 2 | QRタップ: `phone_check=phone_ok` | phase→`handoff_phone_time` |
| 3 | QRタップ: `phone_time=morning` | phase→`handoff_phone_number` |
| 4 | テキスト: `080-1234-5678` | phase→`handoff` |
| 5 | - | Slack通知に「求人詳細タップ（小林病院）」含む / ⭐ 興味のある施設: 小林病院 |

**検証**: facility名がURLデコードされinterestedFacilityに格納。handoffReasonsに反映。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-008: 応募済み状態からのhandoff（appliedAt設定時）

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | （前提: entry.appliedAt が設定済み） | - |
| 2 | phase→`handoff`（apply_confirm経由） | 「✅ 担当者が名前を伏せて施設に確認します。🔒 お名前や連絡先は、先方が関心を示すまで開示しません。」 |
| 3 | - | 「回答があり次第ご連絡しますね」含む |

**検証**: appliedAt設定時は応募フロー用の完了メッセージが表示されること（電話確認メッセージではない）。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-009: 逆指名→handoff（matching_browse=reverse）

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | postback: `matching_browse=reverse` | entry.reverseNomination=true / phase→`handoff_phone_check` |
| 2 | QRタップ: `phone_check=phone_ok` | phase→`handoff_phone_time` |
| 3 | QRタップ: `phone_time=evening` | phase→`handoff_phone_number` |
| 4 | テキスト: `090-5555-6666` | phase→`handoff` |
| 5 | - | Slack通知に「逆指名」含む |

**検証**: 逆指名フラグ→handoffReasons に反映。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-010: consult=handoff → consult_handoff_choice → handoff_phone_check（AI相談からの引き継ぎ）

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | postback: `consult=handoff` | entry.handoffRequestedByUser=true / nextPhase=`consult_handoff_choice` |
| 2 | - | consult_handoff_choice処理: entry.phase→`handoff_phone_check` / buildPhaseMessage実行 |
| 3 | QRタップ: `phone_check=phone_ok` | phase→`handoff_phone_time` |
| 4 | QRタップ: `phone_time=anytime` | phase→`handoff_phone_number` |
| 5 | テキスト: `080-7777-8888` | phase→`handoff` |
| 6 | - | 完了メッセージ + Slack「本人から「相談したい」」含む |

**検証**: AI相談中のconsult=handoff→consult_handoff_choice→handoff_phone_checkの遷移が正常。
**判定**: [ ] PASS / [ ] FAIL

---

## B. handoff LINE希望フロー（10件 / FT5-011〜FT5-020）

### FT5-011: handoff=ok → LINE希望 → 完了（「電話しません」確認）

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | postback: `handoff=ok` | phase→`handoff_phone_check` / 「お電話は控えた方が良いですか？」 |
| 2 | QRタップ: `phone_check=line_only` | entry.phonePreference=`line_only` / phase→`handoff`（phone_timeスキップ） |
| 3 | - | 「担当者に引き継ぎました。24時間以内にこのLINEでご連絡いたしますので、少しお待ちください。お電話はしませんのでご安心ください。」 |
| 4 | - | sendHandoffNotification発火 / Slack「📞 連絡方法: LINEのみ希望」 |

**検証**: LINE希望時は電話番号収集フェーズをスキップ。完了メッセージに「お電話はしませんのでご安心ください」含む。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-012: consult=direct_handoff → LINE希望 → 完了

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | postback: `consult=direct_handoff` | phase→`handoff_phone_check` |
| 2 | QRタップ: `phone_check=line_only` | phase→`handoff` |
| 3 | - | 「お電話はしませんのでご安心ください」含む完了メッセージ |

**検証**: direct_handoff経由でもLINE希望が正常動作。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-013: welcome=consult → LINE希望 → 完了

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | postback: `welcome=consult` | phase→`handoff_phone_check` |
| 2 | QRタップ: `phone_check=line_only` | phase→`handoff` |
| 3 | - | 「お電話はしませんのでご安心ください」含む |
| 4 | - | Slack通知に「LINEのみ希望」表示 |

**検証**: welcomeからの直接相談+LINE希望。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-014: facility付きhandoff → LINE希望 → 完了

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | postback: `handoff=ok&facility=%E6%B9%98%E5%8D%97%E9%8E%8C%E5%80%89%E7%97%85%E9%99%A2` | entry.interestedFacility設定 / phase→`handoff_phone_check` |
| 2 | QRタップ: `phone_check=line_only` | phase→`handoff` |
| 3 | - | 完了メッセージ + Slack通知に施設名+LINEのみ希望 |

**検証**: 施設指定+LINE希望の組み合わせ。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-015: 逆指名→LINE希望→完了

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | postback: `matching_browse=reverse` | phase→`handoff_phone_check` |
| 2 | QRタップ: `phone_check=line_only` | phase→`handoff` |
| 3 | - | 「お電話はしませんのでご安心ください」+ Slack「逆指名」 |

**検証**: 逆指名+LINE希望。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-016: consult=handoff（AI相談後）→ LINE希望 → 完了

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | postback: `consult=handoff` | nextPhase=`consult_handoff_choice` → phase→`handoff_phone_check` |
| 2 | QRタップ: `phone_check=line_only` | phase→`handoff` |
| 3 | - | 「お電話はしませんのでご安心ください」 |

**検証**: AI相談からの引き継ぎ+LINE希望。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-017: urgency=urgent時のhandoff+LINE希望

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | （前提: entry.urgency=`urgent`設定済み） | - |
| 2 | postback: `handoff=ok` | phase→`handoff_phone_check` |
| 3 | QRタップ: `phone_check=line_only` | phase→`handoff` |
| 4 | - | Slack通知に「温度感A（すぐ転職したい）」含む |

**検証**: urgency=urgentがhandoffReasonsに正しく反映。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-018: messageCount>=5時のhandoff+LINE希望

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | （前提: entry.messageCount=7設定済み） | - |
| 2 | postback: `handoff=ok` | phase→`handoff_phone_check` |
| 3 | QRタップ: `phone_check=line_only` | phase→`handoff` |
| 4 | - | Slack通知に「会話7ターン（高エンゲージメント）」含む |

**検証**: messageCount>=5がhandoffReasonsに反映。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-019: handoff完了メッセージでphonePreference未設定の場合

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | （phonePreferenceを経由せず直接handoffに遷移するケース: 緊急キーワード検出時） | - |
| 2 | phase→`handoff` | buildPhaseMessage: phonePreference未設定 → デフォルト分岐 |
| 3 | - | 「担当者に引き継ぎました。24時間以内にこのLINEでご連絡いたしますので...お電話はしませんのでご安心ください。」 |

**検証**: phonePreference未設定時はデフォルトでLINE連絡メッセージ。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-020: Slack通知のphoneInfoLine表示確認（LINE希望・電話番号なし）

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | postback: `handoff=ok` → QR: `phone_check=line_only` → phase=`handoff` | - |
| 2 | - | sendHandoffNotification内: phonePrefText=`LINEのみ希望` / phoneTimeText=`` / phoneNumberText=`` |
| 3 | - | Slack通知: 「📞 連絡方法: LINEのみ希望」（電話番号行なし） |

**検証**: LINE希望時はSlack通知に電話番号行が表示されないこと。
**判定**: [ ] PASS / [ ] FAIL

---

## C. 緊急キーワード検出（10件 / FT5-021〜FT5-030）

### FT5-021: 「死にたい」→ 即handoff + ホットライン案内

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | テキスト: `もう死にたい` | EMERGENCY_KEYWORDS検出: `死にたい` |
| 2 | - | isEmergency=true |
| 3 | - | Slack即時通知: 「🚨 緊急 LINE緊急メッセージ検出」+ userId + メッセージ内容 |
| 4 | - | entry.phase→`handoff` / entry.handoffAt設定 / entry.handoffRequestedByUser=true |
| 5 | - | LINE返信: 「おつらい状況なんですね。担当スタッフに今すぐお繋ぎします。」 |
| 6 | - | 「※緊急の場合は、よりそいホットライン（0120-279-338、24時間対応）もご利用ください。」含む |
| 7 | - | continue（handleFreeTextInput未呼出） |

**検証**: 「死にたい」でisEmergency=true。ホットライン番号0120-279-338が表示。即座にhandoff。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-022: 「パワハラ」→ 即handoff + ホットライン案内

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | テキスト: `上司のパワハラがひどくて` | EMERGENCY_KEYWORDS検出: `パワハラ` |
| 2 | - | isEmergency=true / Slack「🚨 緊急」通知 |
| 3 | - | phase→`handoff` + ホットライン案内 |

**検証**: 「パワハラ」含む文章でEMERGENCY検出。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-023: 「もう限界」→ 即handoff + ホットライン案内

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | テキスト: `精神的にもう限界です` | EMERGENCY_KEYWORDS検出: `限界` |
| 2 | - | isEmergency=true / phase→`handoff` |
| 3 | - | ホットライン案内含む返信 |

**検証**: 「限界」単体でEMERGENCY検出。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-024: 「いじめ」→ 即handoff + ホットライン案内

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | テキスト: `職場でいじめに遭っています` | EMERGENCY_KEYWORDS検出: `いじめ` |
| 2 | - | isEmergency=true / Slack「🚨 緊急」 |
| 3 | - | phase→`handoff` + ホットライン案内 |

**検証**: 「いじめ」でEMERGENCY検出。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-025: 「セクハラ」→ 即handoff + ホットライン案内

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | テキスト: `セクハラされて本当につらい` | EMERGENCY_KEYWORDS検出: `セクハラ` |
| 2 | - | isEmergency=true / phase→`handoff` |
| 3 | - | ホットライン案内 |

**検証**: 「セクハラ」でEMERGENCY検出。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-026: 「もう無理」→ 即handoff + ホットライン案内

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | テキスト: `もう無理、続けられない` | EMERGENCY_KEYWORDS検出: `もう無理` |
| 2 | - | isEmergency=true / phase→`handoff` |
| 3 | - | ホットライン案内 |

**検証**: 「もう無理」でEMERGENCY検出。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-027: 「自殺」→ 即handoff + ホットライン案内

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | テキスト: `自殺を考えてしまう` | EMERGENCY_KEYWORDS検出: `自殺` |
| 2 | - | isEmergency=true / phase→`handoff` + ホットライン案内 |

**検証**: 「自殺」でEMERGENCY検出。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-028: 「体調崩した」→ Slack通知のみ（URGENT、会話続行）

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | テキスト: `夜勤続きで体調崩した` | URGENT_KEYWORDS検出: `体調崩した` |
| 2 | - | isEmergency=false / isUrgent=true |
| 3 | - | Slack通知: 「⚠️ 要注意 LINE緊急メッセージ検出」 |
| 4 | - | **会話は続行**（handoffに遷移しない）。handleFreeTextInputが呼ばれる |

**検証**: URGENT_KEYWORDSはSlack通知のみ。phaseは変更しない。Bot応答は通常フロー。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-029: 「辞めたい」→ Slack通知のみ（URGENT、会話続行）

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | テキスト: `もう辞めたい` | URGENT_KEYWORDS検出: `辞めたい` |
| 2 | - | isUrgent=true / Slack「⚠️ 要注意」通知 |
| 3 | - | 会話続行（handoff遷移なし） |

**検証**: 「辞めたい」はURGENT（非EMERGENCY）。Slack通知するが即handoffしない。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-030: 「暴力」→ 即handoff + ホットライン案内

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | テキスト: `患者さんから暴力を受けた` | EMERGENCY_KEYWORDS検出: `暴力` |
| 2 | - | isEmergency=true / phase→`handoff` |
| 3 | - | ホットライン案内（0120-279-338）含む返信 |

**検証**: 「暴力」でEMERGENCY検出。
**判定**: [ ] PASS / [ ] FAIL

---

## D. 電話番号バリデーション（5件 / FT5-031〜FT5-035）

### FT5-031: 正規携帯番号（ハイフン付き）→ バリデーション通過

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | （前提: phase=`handoff_phone_number`） | - |
| 2 | テキスト: `090-1234-5678` | replace(/[\s\-\u3000（）()]/g, '') → `09012345678` |
| 3 | - | /^0[0-9]{9,10}$/.test(`09012345678`) → true |
| 4 | - | entry.phoneNumber=`09012345678` / phase→`handoff` |

**検証**: ハイフン付き11桁携帯がバリデーション通過。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-032: ハイフンなし携帯番号 → バリデーション通過

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | テキスト: `08012345678` | digits=`08012345678` / isPhone=true |
| 2 | - | entry.phoneNumber=`08012345678` / phase→`handoff` |

**検証**: ハイフンなしでもバリデーション通過。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-033: 固定電話（10桁）→ バリデーション通過

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | テキスト: `045-123-4567` | digits=`0451234567` / isPhone=true（10桁、0始まり） |
| 2 | - | entry.phoneNumber=`0451234567` / phase→`handoff` |

**検証**: 固定電話10桁（/^0[0-9]{9,10}$/）もバリデーション通過。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-034: 不正入力（桁不足・英字混入）→ エラーメッセージ → 2回失敗でhandoff

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | テキスト: `123-456` | digits=`123456` / isPhone=false（0始まりでない+桁不足） |
| 2 | - | unexpectedTextCount=1 / 「電話番号の形式で入力してください。（例: 090-1234-5678）電話番号を伝えたくない場合は「LINE希望」と送ってください。」 |
| 3 | - | QR[LINEでお願いします]表示 |
| 4 | テキスト: `abcdefg` | digits=`abcdefg`→replace後空文字 / isPhone=false |
| 5 | - | unexpectedTextCount=2 / **2回失敗 → 電話番号なしでhandoffへ**（phase→`handoff`） |

**検証**: 2回連続バリデーション失敗→電話番号なしでhandoff遷移。unexpectedTextCount閾値=2。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-035: 「LINE希望」ボタンタップ（phone_check=line_only postback）

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | （前提: phase=`handoff_phone_number` / エラーメッセージ表示後） | - |
| 2 | QRタップ: `phone_check=line_only`（エラーメッセージのQR） | handleLinePostback: entry.phonePreference=`line_only` / phase→`handoff` |
| 3 | - | 「お電話はしませんのでご安心ください」含む完了メッセージ |

**検証**: 電話番号入力フェーズからのLINE希望ボタンで正常にhandoff遷移。phonePreference上書き。
**判定**: [ ] PASS / [ ] FAIL

---

## E. 10件上限後の「担当者に探してもらう」→ handoff（5件 / FT5-036〜FT5-040）

### FT5-036: matching_browse 10件表示済み → 「担当者に探してもらう」→ handoff完走

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | （前提: 5件表示済み、matchingOffset=5） | - |
| 2 | postback: `matching_preview=more` | newOffset=10 / 10件上限到達 |
| 3 | - | 「ここまで10件の求人をご紹介しました。担当者があなたの条件に合う求人を直接お探しします。」 |
| 4 | - | QR[担当者に探してもらう/条件を変えて探す/今日はここまで] |
| 5 | QRタップ: `handoff=ok` | phase→`handoff_phone_check` |
| 6 | QRタップ: `phone_check=line_only` | phase→`handoff` |
| 7 | - | 完了メッセージ |

**検証**: 10件上限→担当者ボタン→handoff完走。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-037: postback内matching_browseから10件上限 → 電話OK → handoff完走

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | （前提: matchingOffset=5） | - |
| 2 | matching_browse でnewOffset>=10 | 「ここまで10件の求人をご紹介しました。」 |
| 3 | QRタップ: `handoff=ok` | phase→`handoff_phone_check` |
| 4 | QRタップ: `phone_check=phone_ok` | phase→`handoff_phone_time` |
| 5 | QRタップ: `phone_time=morning` | phase→`handoff_phone_number` |
| 6 | テキスト: `090-1111-2222` | phase→`handoff` |
| 7 | - | 「24時間以内にご希望の時間帯（午前中）にお電話またはLINE...」 |

**検証**: 10件上限→電話OKルートのhandoff完走。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-038: 求人が10件未満で尽きた場合 → 「担当者に探してもらう」

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | （前提: matchingOffset=5、追加検索でmoreResults.length=0） | - |
| 2 | postback: `matching_preview=more` | generateLineMatching → 0件 |
| 3 | - | 「この条件の求人は以上です。担当者があなたに合う求人を直接お探しすることもできます。」 |
| 4 | - | QR[担当者に探してもらう/条件を変えて探す/今日はここまで] |
| 5 | QRタップ: `handoff=ok` | phase→`handoff_phone_check` → handoff完走 |

**検証**: 10件未満で尽きた場合も担当者提案が表示されhandoff導線が機能する。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-039: matching詳細表示後「この求人が気になる」→ handoff

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | （前提: matching詳細表示後のQR） | - |
| 2 | QRタップ: `handoff=ok` | phase→`handoff_phone_check` |
| 3 | QRタップ: `phone_check=line_only` | phase→`handoff` |
| 4 | - | 完了メッセージ + Slack通知 |

**検証**: matching詳細閲覧→「気になる」→handoff導線。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-040: 10件上限メッセージ中「条件を変えて探す」→ 再検索 → 再度10件上限 → handoff

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | （10件上限到達） | 「ここまで10件の求人をご紹介しました。」 |
| 2 | QRタップ: `matching_preview=deep` | 条件変更画面 → 再検索 |
| 3 | （条件変更後再度10件表示） | 再度10件上限メッセージ |
| 4 | QRタップ: `handoff=ok` | phase→`handoff_phone_check` |
| 5 | QRタップ: `phone_check=phone_ok` → `phone_time=afternoon` → 番号入力 | phase→`handoff` |
| 6 | - | 完了メッセージ |

**検証**: 条件変更→再検索→再度上限→handoffのループが正常動作。
**判定**: [ ] PASS / [ ] FAIL

---

## F. 0件時の「担当者に相談する」→ handoff（5件 / FT5-041〜FT5-045）

### FT5-041: matching_preview 0件 → 通知受取選択 → 条件変更 → 再度0件 → handoff

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | （前提: matchingResults=[] or null） | - |
| 2 | - | buildPhaseMessage(`matching_preview`): 「お伝えいただいた条件だと、今はぴったりの求人が見つかりませんでした。」 |
| 3 | - | QR[通知を受け取る/条件を変えて探す] |
| 4 | QRタップ: `welcome=see_jobs` | intake_light再開 → 再検索 → 再度0件 |
| 5 | （matching_preview 0件メッセージ再表示） | QR[通知を受け取る/条件を変えて探す] |

**検証**: 0件時のメッセージとQR選択肢が正しく表示。0件メッセージに「担当者に相談する」選択肢はmatching_preview直下にはないが、条件変更後のbuildMatchingMessagesには存在する。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-042: buildMatchingMessages 0件 → 「担当者に相談する」→ handoff完走

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | （前提: matching_browse経由でmatchingResults=[]） | - |
| 2 | - | buildMatchingMessages: 「申し訳ありません、条件に合う施設が見つかりませんでした。条件を変えて探すか、担当者が直接お探しすることもできます。」 |
| 3 | - | QR[条件を変えて探す/担当者に相談する] |
| 4 | QRタップ: `handoff=ok` | phase→`handoff_phone_check` |
| 5 | QRタップ: `phone_check=line_only` | phase→`handoff` |
| 6 | - | 完了メッセージ |

**検証**: buildMatchingMessages 0件時の「担当者に相談する」(handoff=ok)からhandoff完走。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-043: 0件 → 担当者に相談 → 電話OK → handoff

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | buildMatchingMessages 0件表示 | QR[条件を変えて探す/担当者に相談する] |
| 2 | QRタップ: `handoff=ok` | phase→`handoff_phone_check` |
| 3 | QRタップ: `phone_check=phone_ok` | phase→`handoff_phone_time` |
| 4 | QRタップ: `phone_time=evening` | phase→`handoff_phone_number` |
| 5 | テキスト: `070-9999-8888` | phase→`handoff` |
| 6 | - | 「24時間以内にご希望の時間帯（夕方以降）にお電話...」 |

**検証**: 0件→電話OKルートのhandoff完走。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-044: 0件 → 条件変えて再検索 → 結果あり → 10件上限 → 担当者探してもらう → handoff

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | buildMatchingMessages 0件 | QR[条件を変えて探す/担当者に相談する] |
| 2 | QRタップ: `matching_preview=deep` | 条件変更 → 再検索 → 結果あり |
| 3 | matching_browse × 2回 | 10件上限到達 |
| 4 | - | 「ここまで10件の求人をご紹介しました。」 |
| 5 | QRタップ: `handoff=ok` | phase→`handoff_phone_check` → handoff完走 |

**検証**: 0件→条件変更→結果あり→10件上限→handoffの長いフロー。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-045: matching_preview 0件（エリア外）→ consult=handoff導線

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | （前提: 極端な条件で0件） | matching_preview 0件メッセージ |
| 2 | QRタップ: `welcome=see_jobs` → 別条件で再検索 → 再度0件は厳しいのでAI相談へ | - |
| 3 | postback: `consult=start` → AI相談 | AI応答 |
| 4 | postback: `consult=handoff` | nextPhase=`consult_handoff_choice` → phase→`handoff_phone_check` |
| 5 | QRタップ: `phone_check=line_only` | phase→`handoff` |
| 6 | - | 完了メッセージ |

**検証**: 0件→AI相談→担当者引き継ぎのフロー。
**判定**: [ ] PASS / [ ] FAIL

---

## G. handoff後のBot沈黙 + Slack転送確認（5件 / FT5-046〜FT5-050）

### FT5-046: handoff後にテキスト送信 → Bot無応答 + Slack転送

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | （前提: phase=`handoff`） | - |
| 2 | テキスト: `すみません、追加で質問があります` | L6527: phase===`handoff`直接チェック |
| 3 | - | Slack通知: 「💬 LINE受信（引き継ぎ済み・要返信）」+ メッセージ内容 + `!reply`コマンド |
| 4 | - | saveLineEntry実行 + **continue**（lineReply呼び出しなし = Bot沈黙） |

**検証**: handoff中のテキストに対してBot応答なし。Slackに転送されること。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-047: handoff後にpostback（FAQ以外）→ 無視（handoff状態維持）

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | （前提: phase=`handoff`） | - |
| 2 | postback: `welcome=see_jobs` | L5907-5916: handoffガード発動 |
| 3 | - | `Handoff guard: blocked postback "welcome=see_jobs"` ログ出力 |
| 4 | - | saveLineEntry + continue（Bot応答なし、phase変更なし） |

**検証**: handoff中のFAQ以外のpostbackは全て無視。phase=`handoff`が維持される。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-048: handoff後にFAQ postback → FAQ応答は許可

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | （前提: phase=`handoff`） | - |
| 2 | postback: `faq=salary` | L5910: pbParams.has("faq")=true → ガード通過 |
| 3 | - | FAQ応答が返される（handoffガードを通過） |

**検証**: handoff中でもFAQ postbackは許可される（唯一の例外）。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-049: handoff_silent後の追加テキスト → 再びSlack転送 + Bot沈黙

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | （前提: phase=`handoff`、前回テキストでhandoff_silent処理済み） | - |
| 2 | テキスト: `お返事まだですか？` | 再度L6527のhandoff直接チェックに到達 |
| 3 | - | Slack転送: 「💬 LINE受信（引き継ぎ済み・要返信）」 |
| 4 | - | Bot沈黙（continue） |
| 5 | テキスト: `急ぎです` | 再度同じ処理 → Slack転送 + Bot沈黙 |

**検証**: 何度テキストを送ってもBot沈黙が維持され、毎回Slackに転送される。
**判定**: [ ] PASS / [ ] FAIL

---

### FT5-050: handoff後のSlack転送に含まれる情報の確認

| Step | ユーザー操作 | 期待Bot応答 |
|------|-------------|------------|
| 1 | （前提: phase=`handoff` / entry.areaLabel=`横浜市` / extractedProfile.area=`横浜`） | - |
| 2 | テキスト: `横浜で日勤の求人ありますか` | Slack転送発火 |
| 3 | - | Slack通知内容確認: |
| 4 | - | `💬 *LINE受信（引き継ぎ済み・要返信）*` |
| 5 | - | `ユーザーID: \`{userId}\`` |
| 6 | - | `エリア: 横浜市`（entry.areaLabel優先） |
| 7 | - | `メッセージ: 横浜で日勤の求人ありますか` |
| 8 | - | `時刻: {JST}` |
| 9 | - | `返信するには: \`!reply {userId} ここに返信メッセージ\`` |

**検証**: Slack転送メッセージに必要な全フィールドが含まれること。areaLabel → extractedProfile.area のフォールバック順。`!reply`コマンド形式の案内。
**判定**: [ ] PASS / [ ] FAIL

---

## 集計

| セクション | 件数 | PASS | FAIL | WARN |
|-----------|------|------|------|------|
| A. handoff完全フロー（電話OK） | 10 | | | |
| B. handoff LINE希望フロー | 10 | | | |
| C. 緊急キーワード検出 | 10 | | | |
| D. 電話番号バリデーション | 5 | | | |
| E. 10件上限→handoff | 5 | | | |
| F. 0件→handoff | 5 | | | |
| G. handoff後Bot沈黙+Slack転送 | 5 | | | |
| **合計** | **50** | | | |

**全体PASS率**: ___/50 = ___%
**致命的バグ**: ___件
**合格判定**: [ ] PASS / [ ] FAIL
