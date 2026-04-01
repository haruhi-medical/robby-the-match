# LINE Bot 全体フロー & 課題一覧

> 2026-04-01 worker.js コード実態ベース

---

## 1. 入口（followイベント → welcome）

友だち追加で以下のメッセージが表示される:

```
はじめまして！
神奈川ナース転職です

神奈川県の看護師さん専門の
転職サポートです。
完全無料・電話なし・LINE完結。

何かお手伝いできますか？

[求人を探したい] [年収を知りたい] [転職の相談をしたい] [まだ見てるだけ]
```

### 4つのボタンの遷移先

| ボタン | postback | 遷移先(nextPhase) | その先 |
|--------|----------|-------------------|--------|
| 求人を探したい | `welcome=see_jobs` | `il_area` | intake_lightフロー開始 |
| 年収を知りたい | `welcome=check_salary` | `ai_consultation_waiting` | 「どうぞ何でも聞いてください！」 |
| 転職の相談をしたい | `welcome=consult` | `ai_consultation_waiting` | 「どうぞ何でも聞いてください！」 |
| まだ見てるだけ | `welcome=browse` | `nurture_warm` | ナーチャリングフロー |

---

## 2. フローA: intake_light（メイン導線）

### 聞く情報: 3問

```
il_area（エリア）
  → 横浜・川崎 / 湘南・鎌倉 / 相模原・県央 / 横須賀・三浦 / 小田原・県西 / 東京も含めて / まだ決めてない
  ↓
il_workstyle（働き方）
  → 日勤のみ / 夜勤ありOK / パート・非常勤 / 夜勤専従
  ↓
il_urgency（温度感）
  → すぐにでも / いい求人があれば / まずは情報収集
  ↓
matching_preview（求人3件表示）
```

### matching_preview のボタン

| ボタン | postback | 遷移先 |
|--------|----------|--------|
| もっと詳しく条件を教える | `matching_preview=deep` | `il_area`（やり直し） |
| 他の求人も見たい | `matching_preview=more` | `matching_browse` |
| この中で気になる | `matching_preview=detail` | `matching`（詳細表示） |
| まだ早いかも | `matching_preview=later` | `nurture_warm` |

※ 結果3件未満の場合「条件を変えて探す」(`matching_preview=deep`)が自動追加

### matching_browse のボタン

| ボタン | postback | 遷移先 |
|--------|----------|--------|
| もっと見る | `matching_browse=more` | `matching_browse`（次の3件） |
| 条件を変えて探す | `matching_browse=change` | `il_area`（やり直し） |
| 気になるのがある | `matching_browse=detail` | `matching`（詳細表示） |
| 今日はここまで | `matching_browse=done` | `nurture_warm` |

### matching（詳細表示）のボタン

```
求人の詳細をお見せしますね！
（各求人の給与・賞与・休日・所在地・交通・雇用形態を表示）

気になる求人があれば、担当者が匿名であなたのプロフィールを病院に打診します。

[この求人が気になる] [相談したい] [逆指名したい] [他の求人も見たい]
```

| ボタン | postback | 遷移先 |
|--------|----------|--------|
| この求人が気になる | `consult=apply` | `apply_info`（個人情報入力） |
| 相談したい | `consult=start` | `ai_consultation`（AIチャット） |
| 逆指名したい | `match=reverse` | `reverse_nomination` |
| 他の求人も見たい | `matching_preview=more` | `matching_browse` |

---

## 3. フローB: Q-flow（旧フロー）

**到達方法**: KVエントリなしのpostback / `fallback=restart` 経由のみ。welcomeの4ボタンからは直接到達不能。

### Q1の回答でフロー分岐

| 回答 | urgency | フロー | 聞く質問 |
|------|---------|--------|----------|
| 今すぐ転職したい | urgent | FULL | Q1→Q2→Q3→Q4→Q5→Q6→Q7→Q8→Q9→Q10→resume→matching |
| いい求人があれば | good | MEDIUM | Q1→Q2→Q3→Q4→Q5→matching |
| まずは情報収集 | info | SHORT | Q1→Q3→Q4→matching |

### 各質問で収集する情報

| 質問 | entry | 内容 | SHORT | MEDIUM | FULL |
|------|-------|------|:-----:|:------:|:----:|
| Q1 | urgency | 転職の温度感 | ✅ | ✅ | ✅ |
| Q2 | change | 変えたいこと | ❌ | ✅ | ✅ |
| Q3 | area | エリア | ✅ | ✅ | ✅ |
| Q4 | experience | 経験年数 | ✅ | ✅ | ✅ |
| Q5 | workStyle | 働き方 | ❌ | ✅ | ✅ |
| Q6 | workplace | 現在の職場タイプ | ❌ | ❌ | ✅ |
| Q7 | strengths | 得意分野(複数) | ❌ | ❌ | ✅ |
| Q8 | concern | 不安なこと | ❌ | ❌ | ✅ |
| Q9 | workHistoryText | 職歴(自由テキスト) | ❌ | ❌ | ✅ |
| Q10 | qualification | 資格 | ❌ | ❌ | ✅ |

---

## 4. 共通: 個人情報入力 → 匿名打診フロー

### apply_info（4ステップ）

```
① 名前入力（2文字以上）        → entry.fullName
② 生年月日入力（日付形式）      → entry.birthDate
③ 電話番号入力（10桁以上）      → entry.phone
④ 勤務先入力（自由テキスト）    → entry.currentWorkplace
```

各ステップで「病院には開示しません。社内管理用です」と明記。

### apply_consent（匿名打診確認）

```
以下の施設に、担当者が匿名プロフィールで打診します。

1. ○○病院（月給30万円）
2. △△クリニック（月給28万円）
3. □□施設（月給32万円）

📋 病院に伝える情報（匿名）: 資格、経験年数、スキル、希望条件、転職理由
🔒 伝えない情報: お名前、電話番号、生年月日、現在の勤務先

[✅ お願いします] [施設を選び直す] [やめておく]
```

### career_sheet（匿名プロフィール表示）

`generateAnonymousProfile(entry)` で生成。以下のフィールドを表示:

| 項目 | entryフィールド | intake_lightで取得? |
|------|----------------|:-------------------:|
| 資格 | qualification | ❌ |
| 経験年数 | experience | ❌ |
| 得意分野 | strengths | ❌ |
| 職務経歴 | workHistoryText | ❌ |
| 転職理由 | change → reasonMap | ❌ |
| 希望エリア | area / areaLabel | ✅ |
| 働き方 | workStyle | ✅ |
| 重視すること | change | ❌ |
| 懸念事項 | concern | ❌ |

### apply_confirm（打診開始）→ handoff

```
✅ 担当者が匿名プロフィールで病院に打診します！
🔒 あなたのお名前や連絡先は、病院が興味を示すまで開示しません。

[面接対策を見る] [わかりました]
```

→ Slack通知（社内用個人情報 + 匿名プロフィール）
→ handoff（担当者引き継ぎ）

---

## 5. AI相談フロー

### 入口

- `welcome=check_salary` → 「どうぞ、何でも聞いてください！」
- `welcome=consult` → 「どうぞ、何でも聞いてください！」
- matching → 「相談したい」(`consult=start`) → 同上

### テキスト入力 → AI応答

1. ユーザーがテキスト送信
2. Webhookは即200返却（Push APIで後から返答）
3. OpenAI GPT-4o-mini を呼び出し（タイムアウト8秒）
4. 失敗時: Cloudflare Workers AI（Llama 3 8B）にフォールバック
5. 全失敗: 「回答の生成に時間がかかっています」メッセージ

### ターン上限

- 通常: 5ターン → 「まとめますね」+ [もう少し話す / 担当者に相談する]
- 延長後: 8ターン → 同じメッセージ
- 「もう少し話す」で `consult=extend` → `consultExtended=true` → 上限8に

### AI相談からの出口

| ボタン | postback | 遷移先 |
|--------|----------|--------|
| もう少し話す | `consult=extend` | `ai_consultation`（上限+3） |
| 担当者と話したい | `consult=handoff` | `consult_handoff_choice` |
| もう一度聞く | `consult=continue` | `ai_consultation`（継続） |

### consult_handoff_choice

```
応募に進みますか？それとも担当者と話しますか？

[応募に進む] [担当者と話したい]
```

---

## 6. ナーチャリング

### 入口

- `welcome=browse` → nurture_warm
- `matching_preview=later` → nurture_warm
- `matching_browse=done` → nurture_warm

### メッセージ

```
了解です！
必要な時にいつでも話しかけてくださいね。

新着求人が出たらお知らせすることもできます。

[新着をお知らせして] [大丈夫です]
```

### Cron配信（自動Push）

| タイミング | 内容 |
|-----------|------|
| Day 3 | エリア新着情報（「{エリア}エリアの看護師求人に動きがありました」） |
| Day 7 | 転職ガイド情報 |
| Day 14 | チェックイン（「お久しぶりです！」） |
| Day 30 | KVキー削除（ナーチャリング終了） |

---

## 7. 逆指名フロー

```
matching → 「逆指名したい」
→ 「希望の病院名を教えてください！」
→ テキスト入力（病院名）→ entry.reverseNominationHospital
→ 「{病院名}ですね！匿名プロフィールでこの病院に打診します」
→ [はい、進めてください] [他の病院も考えたい]
→ apply_info（個人情報入力）→ 以降共通フロー
```

---

## 8. ハンドオフ後

```
担当者に引き継ぎました。
お返事まで少しお待ちくださいね。

[本当に無料？] [電話は来ない？] [他の求人も見たい]
```

- テキスト入力 → Bot沈黙、Slack転送のみ
- FAQ → 回答表示（phaseはhandoffのまま）
- 2時間後にCronでフォローアップPush送信

---

## 9. その他の入口

### LP診断引き継ぎ（6文字コード）
LP診断7問 → コード生成 → LINE友だち追加 → コード送信 → 即matching直行

### 共通EP（session UUID）
LP CTA → `/api/line-start` → follow → UUID送信 → source別welcome分岐

### 想定外テキストの3段階エスカレーション
1回目: Quick Reply再表示 / 2回目: フォールバック選択肢 / 3回目: 強制handoff

---

---

# 課題一覧

## P0（致命的 — 機能が壊れている / ユーザーに嘘をつく）

### P0-1: intake_lightで匿名プロフィールがほぼ空白
- intake_lightは3問（エリア・働き方・温度感）しか聞かない
- 匿名プロフィールに必要な「資格・経験年数・スキル・転職理由」は全て「（未回答）」
- apply_consentで「資格・経験年数・スキルを伝えます」と約束しているのに中身がない
- **病院に打診するプロフィールとして機能しない**

### P0-2: handoffメッセージに「応募手続き完了！書類選考3営業日以内」が残存
- L3708: `entry.appliedAt`がtruthyの場合のhandoffメッセージ
- 匿名打診フローなのに「応募完了」「書類選考」は事実と異なる

### P0-3: AI相談のターン延長が無限ループ
- 8ターン到達 → `consult=extend`ボタン表示 → タップしても上限は8のまま
- 次の発言で即ターン上限 → 同じボタン → **永久ループ**

### P0-4: area_page経由のwelcomeで4ボタンが全て同じpostback
- L2756-2759: 働き方ボタン4つが全て`welcome=see_jobs`を送信
- workStyleが記録されず、「あと2つだけ教えてください」は嘘

### P0-5: AI相談でテキスト送信しても返答がない可能性
- AI応答はPush API（非同期）。OpenAI APIキー無効 or Worker secret消失で**完全無応答**
- エラーはcatch内でPush送信されるが、Push自体が失敗するとログのみ

---

## P1（重要 — ユーザー混乱 / 旧表現残留）

### P1-1: 「応募」の旧表現が5箇所に残存
| 箇所 | 内容 |
|------|------|
| L2584 POSTBACK_LABELS | `"同意して応募する"` |
| L2696 TEXT_TO_POSTBACK | `"同意して応募"`, `"応募する"` |
| L3708 handoff | `"応募手続き完了です！"` |
| L5057 consult_handoff_choice | `"応募に進みますか？"` |
| L5060 Quick Reply | `"応募に進む"` |

### P1-2: 「年収を知りたい」と「転職の相談」が同じ遷移先
- どちらも`ai_consultation_waiting` → 「どうぞ何でも聞いてください！」
- 年収を知りたいユーザーには具体的な誘導（エリア・経験年数を聞く等）が必要

### P1-3: SHORTフローでworkStyle/changeが未設定のままmatchingに入る
- Q5(workStyle)とQ2(change)がスキップされる
- 匿名プロフィールで「（未回答）」表示

### P1-4: AI相談5回目の質問がAI回答なしで上限メッセージ
- ターン上限チェックがメッセージ追加後
- 5回目の質問は保存されるが回答されない

### P1-5: 「まとめますね」と言ってまとめない
- L5667のターン上限メッセージが虚偽

### P1-6: 逆指名→apply_consentで施設リストが空
- matchingResultsを参照するが逆指名先(reverseNominationHospital)が反映されない
- 「（マッチング結果を確認中）」が表示される

### P1-7: career_sheet_editの例に「電話番号を修正」
- 匿名プロフィールに電話番号は含まれないので例として不適切

---

## P2（軽微 — UX改善推奨）

| # | 問題 |
|---|------|
| 1 | nurture_warmに「求人を再検索」ボタンなし。テキスト3回で強制handoff |
| 2 | handoff後「他の求人も見たい」タップでhandoff状態が解除されBotが復活 |
| 3 | FAQ回答後にQuick Replyなし。次に何をすべきか不明 |
| 4 | apply_cancelled → handoffでFAQ Quick Reply表示なし |
| 5 | apply_confirm直後に「面接対策を見る」は時期尚早（まだ打診段階） |
| 6 | getMenuStateForPhaseに`q9_timing`（存在しないフェーズ名。正しくは`q9_work_history`） |
| 7 | Q1メッセージで「まずは」が2回連続 |
| 8 | matching_browse「気になるのがある」で特定1件を選ぶUIがない |
