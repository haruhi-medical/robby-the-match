# Meta広告 計測・動線 設計欠陥の深掘り解説 — 2026-04-17

> チーム共有用。非エンジニアにも分かるように動作フローから解説。

---

## 🏗 全体の設計意図（あるべき姿）

```
① 看護師が広告を見る (Instagram/Facebook)
   ↓
② 広告タップ → LP (quads-nurse.com/lp/job-seeker/?utm_source=meta_ad)
   ↓ (Meta Pixel PageView 発火)
③ LP上のCTAボタン "LINEで相談する" タップ
   ↓ (Meta Pixel Lead 発火 ← LINEに流れたシグナル)
   ↓
④ Worker /api/line-start?source=meta_ad&session_id=XXX にブラウザが飛ぶ
   ↓ Worker: session情報をKVに保存 (source=meta_ad 記録)
   ↓ 302 redirect → line.me 友だち追加画面
   ↓
⑤ ユーザーが「友だち追加」タップ
   ↓ LINE側: session_id を dm_text で事前入力状態にする
   ↓
⑥ ユーザーが LINE チャットで session_id テキストを "送信"
   ↓ Worker: テキスト受信 → session_id 認識 → KV から source 復元
   ↓
⑦ Worker: entry.welcomeSource = 'meta_ad' と保存
   ↓ Meta CAPI: CompleteRegistration イベント送信 (本物の登録Lead)
   ↓
⑧ 広告経由の本物登録者として集計完了
```

理想: ①〜⑧が全部動けば「広告経由の本物Lead」が計測できる。

---

## 🔴 欠陥1: LP CTAが utm_source を継承しない

### 症状
広告経由でLPに来ても、CTAクリック時に `source=hero/sticky/bottom` と固定で送られる。
広告由来でも `source=meta_ad` にならない。

### 該当コード
**ファイル**: `lp/job-seeker/index.html` 1137-1171行

```javascript
(function() {
  'use strict';
  function uuid() { /* UUIDv4生成 */ }
  var sid = uuid();
  window.__lineSessionId = sid;
  var WORKER_BASE = 'https://robby-the-match-api.robby-the-robot-2026.workers.dev';

  function lineUrl(source, intent) {
    return WORKER_BASE + '/api/line-start'
      + '?source=' + encodeURIComponent(source)       // ← ハードコード
      + '&intent=' + encodeURIComponent(intent)
      + '&session_id=' + encodeURIComponent(sid)
      + '&page_type=paid_lp';
  }

  // Hero CTA → source='hero' 固定
  if (heroCta) heroCta.href = lineUrl('hero', 'see_jobs');
  // Mobile Sticky CTA → source='sticky' 固定
  if (stickyCta) stickyCta.href = lineUrl('sticky', 'see_jobs');
  // Bottom CTA → source='bottom' 固定
  if (bottomLine) bottomLine.href = lineUrl('bottom', 'consult');
})();
```

### 問題点
1. `lineUrl()` の第1引数 `source` が `'hero'`, `'sticky'`, `'bottom'` にハードコード
2. URL queryの `utm_source=meta_ad` を読む処理が一切ない
3. 結果 → Worker側では `source=hero` として記録

### 影響
- 広告経由の登録者が**何人いるか特定できない**
- Custom Audience「Meta広告経由登録者」を作れない
- キャンペーン別のLINE登録CVRが追跡不能

### 再現
```
広告をタップ → LP URL: https://quads-nurse.com/lp/job-seeker/?utm_source=meta&utm_campaign=v7
 ↓
LP上のCTAタップ → /api/line-start?source=hero&intent=see_jobs ← meta が消えてる
 ↓
Worker KV保存: {source: 'hero', ...}
```

### 修正案
```javascript
function lineUrl(defaultSource, intent) {
  // URL paramから広告source取得、優先継承
  var params = new URLSearchParams(window.location.search);
  var actualSource = params.get('utm_source') || defaultSource;
  var campaign = params.get('utm_campaign') || '';
  
  return WORKER_BASE + '/api/line-start'
    + '?source=' + encodeURIComponent(actualSource)
    + '&intent=' + encodeURIComponent(intent)
    + '&session_id=' + encodeURIComponent(sid)
    + '&page_type=paid_lp'
    + (campaign ? '&campaign=' + encodeURIComponent(campaign) : '');
}
```

### 工数
30分（LPスクリプト修正 + デプロイ + 検証）

---

## 🔴 欠陥2: dm_text「送信ボタン」押下が必要な2段階構造

### 症状
LINE友だち追加後、セッション情報の紐付けにユーザーの能動操作が必要。67%のユーザーが放置。

### 該当コード・仕組み
**ファイル**: `api/worker.js` 3196-3206行

```javascript
// dm_text にsession_idを埋め込んでLINE友だち追加URLへリダイレクト
const dmText = encodeURIComponent(effectiveSessionId);
const redirectUrl = `${LINE_START_OA_URL}?dm_text=${dmText}`;

return new Response(null, {
  status: 302,
  headers: {
    'Location': redirectUrl,
    // Locationは https://line.me/R/ti/p/@174cxnev?dm_text=<UUID>
  },
});
```

**ファイル**: `api/worker.js` 7041-7056行

```javascript
} else {
  // 通常フォロー（LIFF未経由 or dm_text方式）
  // dm_text が届いた場合はテキストメッセージハンドラでsession検出→welcome再送する。
  entry.welcomeSource = 'none';   // ← ここで一旦 'none' で保存
  await saveLineEntry(userId, entry, env);
  // welcome メッセージだけ返す（sourceはまだ分からない）
  ...
}
```

**ファイル**: `api/worker.js` 7696-7699行

```javascript
// 後からテキストメッセージを受信した時
if (sessionCtx) {
  entry.webSessionData = sessionCtx;
  entry.welcomeSource = sessionCtx.source || 'none';   // ← ここで上書き
  entry.welcomeIntent = sessionCtx.intent || 'see_jobs';
  ...
}
```

### 動作フロー（詳細）
```
[LP CTAタップ]
  ↓
[Worker: session_id生成、KVに { source, intent, ... } 保存]
  ↓
[302 redirect → line.me/R/ti/p/@174cxnev?dm_text=session-uuid]
  ↓
[LINEアプリ/Web起動]
  ↓
[ユーザー「友だち追加」タップ]
  ↓
[Worker followイベント受信]
  ↓ entry.welcomeSource = 'none' で初期化 ← (A) ここで記録完了
  ↓ welcome メッセージ送信
  ↓
[LINEチャット画面: dm_text=session-uuid が入力欄に事前入力される]
  ↓
[ユーザーが「送信」ボタンを押す ← ★★★ ここで67%が離脱 ★★★]
  ↓ (押さない場合、welcomeSource='none' のまま永遠)
  ↓
[Worker: テキストメッセージ受信 → session_id 認識 → KV復元]
  ↓ entry.welcomeSource = 'meta_ad' に上書き ← (B) ようやく正しい記録
```

### 問題の本質
- **(A)時点**では広告由来か分からない（follow単独のイベントにsourceは含まれない）
- **(B)時点**でやっと判定できるが、ユーザー能動操作が必要
- LINE Messaging APIの仕様上、followイベント単独で source を渡す方法は限定的

### LINE仕様の裏事情
- `dm_text` は LINE公式アカウントの「事前入力メッセージ」機能
- iOS版LINE: 入力欄に文字が入った状態で表示、送信ボタンタップで送信
- Android版LINE: 同上
- LINE Web版: 同上
- **いずれも「送信」タップが必要**（自動送信される仕様ではない）
- ユーザーから見ると「知らない長いUUIDを送信するのは怖い」心理バリア

### 影響
- LINE登録者の**67%が source=none で分類**
- 広告経由 vs オーガニック vs 紹介の区別不能
- CRM上の「Meta広告経由のお客様リスト」が作れない

### 修正案（複数ある）
#### 案A: LINE LIFF経由に統一
LP CTAから直接LIFF URLを開き、LIFF内で LINE SDK経由で source を LINE側に渡す
- メリット: ユーザー操作0で source 受け渡し可能
- デメリット: LIFF実装・LINE Developersコンソール設定が必要

#### 案B: 友だち追加時の「友だち追加パラメータ」機能利用
LINE Messaging API の「友だち追加パラメータ」機能で、友だち追加URLに対してパラメータを付与
- `line.me/R/ti/p/@174cxnev?utmSource=meta_ad` の形式
- Webhook側で followイベントの postback data から取得可能
- メリット: dm_text不要、ユーザー操作0
- デメリット: LINE公式アカウント側での有効化が必要

#### 案C: follow時のWebhook event_source から推定（不完全）
Meta広告経由のフォローは referer ヘッダに Meta系ドメインが入る可能性
- メリット: 実装最小
- デメリット: LINE webhook はreferer 渡さない → 不採用

### 推奨
**案A(LIFF)** — 既にLIFF 2009683996-7pCYfOP7 が設定済み、一部経路で動作中

### 工数
2時間（LP CTAをLIFF遷移に書き換え + 動作確認）

---

## 🔴 欠陥3: Pixel Lead乱発（4/14で14倍の乖離）

### 症状
4/14の実績:
- 広告レポート上のLead: **2件**
- Pixel API 生データ上のLead: **25件**
- 乖離 14倍

### 該当コード
**ファイル**: `lp/job-seeker/index.html` 1180-1211行

```javascript
<script>
(function() {
  'use strict';
  function fireLeadOnLineClick() {
    var selectors = '.cta-line-hero, .cta-line, .mobile-sticky-line, a[href*="lin.ee"], a[href*="line.me"], a[href*="line-start"], a[href*="liff.html"]';
    var buttons = document.querySelectorAll(selectors);
    buttons.forEach(function(btn) {
      if (btn.dataset.leadTracked) return;   // ← 1つのボタンに対して1回のみ発火
      btn.dataset.leadTracked = 'true';
      btn.addEventListener('click', function() {
        if (typeof fbq === 'function') {
          var eid = window.__lineSessionId || '';
          fbq('track', 'Lead', {
            content_name: btn.className || 'line_cta',
            content_category: 'line_cta_click'
          }, eid ? { eventID: eid } : undefined);
        }
      });
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', fireLeadOnLineClick);
  } else {
    fireLeadOnLineClick();
  }
})();
</script>
```

**ファイル**: `api/worker.js` 3096-3122行

```javascript
// LP から /api/line-start に飛んできた時、CAPI Leadも同時発火
if (env?.META_ACCESS_TOKEN && env?.META_PIXEL_ID && ctx) {
  ctx.waitUntil(sendMetaConversionEvent(
    env,
    'Lead',                          // ← 必ず Lead発火
    effectiveSessionId,
    { area, source, intent, pageType },
    {
      eventId: effectiveSessionId,   // ★ LP側の event_id と同じ値で dedup
      ...
    },
  ));
}
```

### 問題の連鎖（なぜ14倍になるか）
**原因A: session_id がページロードごとに再生成**
```javascript
// lp/job-seeker/index.html:1144
var sid = uuid();  // ← ページロード毎に新規UUID
```
→ 同一ユーザーがLPを複数回訪問 → 毎回違うsession_id → event_id dedup 不能

**原因B: 1セッション内で複数CTAクリックすると発火**
`btn.dataset.leadTracked` は**ボタン単位**のフラグ。同じボタンは1回のみだが、`.cta-line-hero`, `.cta-line`, `.mobile-sticky-line` と複数ボタンがあるので**それぞれ1回ずつ発火**可能。

**原因C: LP側Pixel + CAPI で2重発火**
- LP側 `fbq('track','Lead', {}, {eventID: sid})` 発火
- Worker側 CAPI Lead (eventId: sid) も発火
- event_id 同じなら Meta側で dedup されるはず
- **ただし** event 送信タイミングのズレ（LP側は即時、CAPI側は302リダイレクト後）でdedup window（Meta仕様で24時間以内）に入らないケースあり

**原因D: 社長のテストクリック**
ヘビーユーザー U7e23b5... (messageCount 592) = 社長本人のテスト
- LPをテストで複数回訪問 → session_id毎回違う → Lead毎回発火
- 1日で10回LPアクセス × 3CTAボタン = Lead 30件誤発火可能

### 影響
- 広告Lead数が実態の14倍膨張
- CPL が実際より 1/14 に見えて「優秀な広告」と誤判断
- Meta AI が偽Lead信号で学習 → 本物看護師にフォーカスせず「テストクリック好きな人」に似た層に配信

### 修正案
```javascript
// session_id を localStorage で永続化
var sid = localStorage.getItem('__nurseRobbySid')
          || (function() {
              var newSid = uuid();
              localStorage.setItem('__nurseRobbySid', newSid);
              return newSid;
          })();

// Lead発火を sid ごと1回のみに制限
function fireLead(btn) {
  var alreadyFired = localStorage.getItem('__leadFired_' + sid);
  if (alreadyFired) return;
  localStorage.setItem('__leadFired_' + sid, '1');
  fbq('track', 'Lead', {...}, {eventID: sid});
}

// さらに、sid を 7日で自動ローテ
var sidCreatedAt = localStorage.getItem('__nurseRobbySidTime');
if (!sidCreatedAt || Date.now() - parseInt(sidCreatedAt) > 7*24*3600*1000) {
  localStorage.removeItem('__nurseRobbySid');
  localStorage.removeItem('__leadFired_' + sid);
  sid = uuid();
  localStorage.setItem('__nurseRobbySid', sid);
  localStorage.setItem('__nurseRobbySidTime', Date.now().toString());
}
```

### さらなる根本対処
**Lead定義自体を変える**:
- 現: LP CTAクリック時 → 軽すぎる、誤発火多い
- 新: LINE 友だち追加完了時 (CAPI CompleteRegistration を Lead に格上げ)
- Meta Ads Manager で最適化目標を `Lead` → `CompleteRegistration` に変更

### 工数
LP修正: 1時間 / CAPI定義変更: 30分 / Ads Manager: 5分

---

## 📊 3欠陥の影響総合まとめ

| 欠陥 | 検出方法 | 広告に与える影響 | 見積工数 |
|------|---------|-----------------|---------|
| 1. source継承なし | KV 15人調査 welcomeSource=none | 広告経由登録者特定不能 | 30分 |
| 2. dm_text送信摩擦 | messageCount=0 が67% | 登録者67%がロスト | 2時間 |
| 3. Pixel Lead乱発 | Pixel統計25件 vs 広告2件 | CPL 14倍誤評価 | 1時間30分 |

### 修正順序の提案
1. **[最優先]** 欠陥3修正 — Lead定義正常化。これがないと最適化シグナルが汚染され続ける
2. **[次点]** 欠陥1修正 — source継承。Custom Audience化の前提条件
3. **[余裕あれば]** 欠陥2修正 — LIFF化は大規模。短期は他2件で代替可

### 合計工数
約4時間（1日で完了可能）

---

## 🎯 修正完了後に期待できる改善

- 広告Lead数 = 本物の LINE 友だち追加数（乖離ゼロ）
- 広告経由登録者の Custom Audience 構築可能
- キャンペーン別・クリエイティブ別CVRの正確な測定
- 本物の数字で戦略判断できるようになる
