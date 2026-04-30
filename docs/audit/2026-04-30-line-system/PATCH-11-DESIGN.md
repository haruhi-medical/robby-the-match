# Patch 11 設計プラン: 問い合わせフロー改修

**起点**: 千恵子ロスト事例（具体的な求人問い合わせ→人間対応待ちで離脱）
**社長指示**: 求人問い合わせ→キャリアシート生成フォーム→電話予約 のAI完走フロー
**位置づけ**: v9.4 「実装前社長承認」対象の大規模実装。プラン承認後に着手

---

## 0. 千恵子ロストの構造的理解

| ステップ | ユーザー行動 | 旧挙動 | 結果 |
|---|---|---|---|
| 1 | 求人カードを見て興味を持つ | - | OK |
| 2 | 「問い合わせる」気持ち発生 | 「⭐気になる」しかなく リスト追加のみ | 熱量が下がる |
| 3 | 自由文で「○○病院について聞きたい」 | handoff phase へ | 人間返信待ち |
| 4 | 社長が休日 or 遅延 | 返信なし | **ロスト** |

→ 「問い合わせる」明示ボタン + その後のAI完走フローが必要。

---

## 1. 改修後フロー（社長指示通り）

```
求人カード
  ├─ ⭐気になる（既存・リスト追加）
  └─ 📨 問い合わせる（新規）  ← 押下
        ↓
  「○○病院へのお問い合わせですね✨
   最適なご案内のため、3分で簡単なフォーム入力をお願いします」
   [📝 キャリアシート作成]
        ↓
  キャリアシート入力フォーム
   - 学歴（選択: 大卒/専門卒/高卒 + 看護系チェック）
   - 経歴（年数選択 + 経験診療科 複数選択）
   - 資格（正看護師/准看護師/その他）
   - 転職理由（選択 + 自由記述任意）
   - 転職で叶えたいこと（自由記述）
        ↓ submit
  /api/career-sheet POST → KV保存（マイページ）
        ↓
  「キャリアシート完成🎉
   最後に、担当者と電話で5分お話しさせてください」
   [📞 日時を選択する]（平日9:00〜16:00）
        ↓
  日時選択UI（Flex Carousel）
   月-金 × 9:00/10:00/11:00/13:00/14:00/15:00/16:00
        ↓ 選択
  /api/booking POST → KV保存 + Slack通知
        ↓
  「○月○日（○）○○:○○ に担当者からお電話します」
        ↓
  社長が予約時刻に手動電話（重要事項説明＋契約意思確認）
```

---

## 2. 実装方針: A案 vs B案 vs MVP案

### A案: LIFF アプリ（フル実装）
- LINE 内ブラウザでフォーム表示
- 工数: **3日**
- 利点: シームレス、UX最高
- 欠点: LIFF設定が必要、開発時間長い

### B案: 既存静的HTML（GitHub Pages活用）
- /career-sheet-form.html（既存LP診断と同じ手法）
- userIdをURLパラメータで渡し、submitでWorker APIへ
- 工数: **1.5日**
- 利点: 既存技術スタック流用、すぐ実装可能
- 欠点: LINE→ブラウザ→LINE の遷移発生

### **推奨: MVP案（B案ベース、最小実装）**
- B案 + 機能を最小化
- 工数: **1日**
- 範囲:
  - 問い合わせボタン追加（worker.js postback handler）
  - 静的HTML キャリアシートフォーム（既存LP同様）
  - /api/career-sheet エンドポイント（KV保存のみ）
  - 電話予約: LINE Flex Carousel（簡易版）
  - /api/booking エンドポイント（Slack通知のみ）
  - マイページ表示（既存mypage簡易拡張 or 後回し）

---

## 3. MVP案の実装内訳

### 3-1. 「問い合わせる」postback 追加（半日）

**変更**: `api/worker.js` 求人カード Flex
- 既存「⭐気になる」(`fav_add=`) に並んで「📨 問い合わせる」(`inquire_job=<jobId>`) ボタン追加

**新規 postback handler**:
```javascript
if (dataStr.startsWith("inquire_job=")) {
  const jobId = decodeURIComponent(dataStr.slice("inquire_job=".length));
  entry.inquireJobId = jobId;
  entry.phase = "inquire_form_pending";
  await saveLineEntry(userId, entry, env);
  
  // フォームURL生成（userIdをparam）
  const formUrl = `https://quads-nurse.com/career-sheet.html?u=${userId}&job=${encodeURIComponent(jobId)}`;
  
  await lineReply(event.replyToken, [{
    type: "text",
    text: `「${jobName}」へのお問い合わせ、ありがとうございます✨\n\n最適なご案内のため、3分で簡単なフォーム入力をお願いします。\n\n${formUrl}`,
  }], channelAccessToken);
  continue;
}
```

### 3-2. キャリアシートフォーム（半日）

**新規ファイル**: `~/robby-the-match/career-sheet.html`
- 既存LP診断（chat.js）と同じスタイル
- 5項目（学歴・経歴・資格・転職理由・叶えたいこと）
- Submit → POST /api/career-sheet

**実装**:
```html
<form id="career-sheet-form">
  <input type="hidden" name="userId" id="userId">
  <input type="hidden" name="jobId" id="jobId">
  <fieldset><legend>学歴</legend>
    <select name="education">
      <option>大学卒業</option>
      <option>専門学校卒業</option>
      <option>高校卒業</option>
    </select>
    <label><input type="checkbox" name="nursingSchool"> 看護系の学校</label>
  </fieldset>
  <fieldset><legend>経歴</legend>
    <select name="experienceYears">...</select>
    <input type="checkbox" name="dept" value="ICU">ICU
    <!-- 複数選択 -->
  </fieldset>
  <!-- 資格、転職理由、叶えたいこと -->
  <button type="submit">送信</button>
</form>
```

### 3-3. /api/career-sheet エンドポイント（30分）

**新規ルート**: `worker.js` の fetch handler に追加
```javascript
if (url.pathname === "/api/career-sheet" && request.method === "POST") {
  const body = await request.json();
  const userId = body.userId;
  if (!userId) return new Response(JSON.stringify({ error: "userId required" }), { status: 400 });
  
  // KV保存
  await env.LINE_SESSIONS.put(`career_sheet:${userId}`, JSON.stringify({
    ...body,
    submittedAt: Date.now(),
  }));
  
  // entry 更新
  const entry = await getLineEntryAsync(userId, env);
  if (entry) {
    entry.careerSheetCompleted = true;
    entry.phase = "inquire_booking_pending";
    await saveLineEntry(userId, entry, env);
    
    // LINE Push: 完了通知 + 電話予約Flex
    await pushTo(userId, [
      { type: "text", text: "キャリアシート完成しました🎉\n\n最後に、担当者とお電話で5分お話しさせてください📞" },
      buildBookingFlex(),
    ]);
  }
  return new Response(JSON.stringify({ ok: true }), { headers: { "Content-Type": "application/json" } });
}
```

### 3-4. 電話予約 LINE Flex（半日）

**実装**: 平日（次の週の月-金）× 7時間枠（9/10/11/13/14/15/16時）の Flex Carousel

```javascript
function buildBookingFlex() {
  const slots = generateNextWeekdays(); // 平日10日分
  return {
    type: "flex",
    altText: "電話予約日時を選んでください",
    contents: {
      type: "carousel",
      contents: slots.map(date => ({
        type: "bubble",
        body: {
          type: "box",
          layout: "vertical",
          contents: [
            { type: "text", text: date.label, weight: "bold", size: "lg" },
            ...["9:00","10:00","11:00","13:00","14:00","15:00","16:00"].map(t => ({
              type: "button",
              style: "primary",
              color: "#E8756D",
              action: {
                type: "postback",
                label: t,
                data: `book=${date.iso}T${t}`,
                displayText: `${date.label} ${t} で予約`,
              },
            })),
          ],
        },
      })),
    },
  };
}
```

### 3-5. /api/booking + 予約完了処理（30分）

**postback handler**:
```javascript
if (dataStr.startsWith("book=")) {
  const datetime = dataStr.slice("book=".length);
  entry.bookingDatetime = datetime;
  entry.phase = "booked";
  await saveLineEntry(userId, entry, env);
  
  // Slack通知（社長手動電話用）
  await fetch(slackPostMessageUrl, {
    body: JSON.stringify({
      channel: "C0AEG626EUW",
      text: `📞 *新規電話予約*\nユーザー: ${displayName} \`${userId}\`\n日時: ${datetime}\n求人: ${entry.inquireJobId}\nキャリアシート: ${entry.careerSheetCompleted ? '✅' : '❌'}\n\n💬 \`!reply ${userId} メッセージ\``,
    }),
  });
  
  await lineReply(event.replyToken, [{
    type: "text",
    text: `ありがとうございます！\n${formatDatetimeJa(datetime)} に担当者からお電話します📞\n\n事前にキャリアシートを拝見し、ご希望に沿ったお話ができるよう準備しております🌸`,
  }], channelAccessToken);
}
```

### 3-6. マイページ拡張（後回し可）

既存 `mypage` 機能を活用するか、本Patchでは Push 通知だけで済ませて MVP2 でマイページ拡張する判断もあり。

---

## 4. 工数とスケジュール

| ステップ | 工数 | 着手判断 |
|---|---|---|
| 3-1. 問い合わせpostback | 0.5日 | 即着手OK |
| 3-2. フォームHTML | 0.5日 | 即着手OK |
| 3-3. /api/career-sheet | 0.25日 | 即着手OK |
| 3-4. 電話予約Flex | 0.5日 | 即着手OK |
| 3-5. /api/booking | 0.25日 | 即着手OK |
| 3-6. マイページ | 0日（MVP1で省略） | MVP2で実装 |
| 合計 | **2日** | - |

---

## 5. リスクと対応

| リスク | 影響 | 対策 |
|---|---|---|
| フォーム入力中の離脱 | 機会損失 | 5分以内の所要時間明示・選択式中心 |
| 予約日時変更要求 | 運用負荷 | MVP2で「予約変更」postback追加 |
| 平日9-16時以外の予約希望 | 機会損失 | 「営業時間外希望」自由文受付（Slack通知） |
| 社長が予約時刻に電話できない | 信頼失墜 | カレンダー連携 or 24h前リマインダーSlack |
| キャリアシート未入力で予約だけする人 | 当日電話で困る | フォーム未完了時は予約UI出さない（careerSheetCompleted=trueをガード） |

---

## 6. 社長承認待ち項目

- [ ] **MVP案（2日工数）でOKか** / LIFF版（3日）に格上げするか
- [ ] **フォームURL**: quads-nurse.com/career-sheet.html でOKか
- [ ] **予約時間枠**: 平日9-16時の7枠 × 10日分でOKか
- [ ] **マイページ拡張は MVP2 で OK** か
- [ ] **電話予約後のリマインダー**: 24h前自動Push を入れるか（cron追加）

承認後すぐ着手します。

---

## 7. v9.4 ガードレール考慮

- 本Patch は AI API呼び出しを増やす変更ではない（フォーム=静的HTML、予約=postback）
- 既存ユーザー導線は変更（求人カードに新ボタン追加）→ 承認必要
- コスト構造影響: 軽微（Worker呼び出し数微増、KV書き込み増、AI API無し）
- 業務フロー影響: handoff削減＋AI完走化（社長戦略と一致）

→ 設計確認後、実装着手 + デプロイ前再承認の流れで進めます。
