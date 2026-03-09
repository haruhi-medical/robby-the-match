# ナースロビー Meta Pixel 実装監査レポート

監査日: 2026-03-09
対象サイト: https://quads-nurse.com/lp/job-seeker/
Meta Pixel ID: 2326210157891886
監査対象ファイル:
- lp/job-seeker/index.html (LP-A、メインLP)
- index.html (トップページ)
- chat.js (チャットウィジェット)
- lp/job-seeker/area/ (22ページ)
- lp/job-seeker/guide/ (44ページ)
- blog/ (19ページ)
- api/worker.js (Cloudflare Worker)

---

## 総合評価

| カテゴリ | スコア | 評価 |
|----------|--------|------|
| Pixel基本実装 | 70/100 | WARNING |
| イベント実装 | 65/100 | WARNING |
| カバレッジ | 20/100 | FAIL |
| データ品質 | 40/100 | FAIL |
| 総合 | 49/100 | FAIL |

**広告出稿前に Critical 項目3つを必ず修正すること。このまま出稿すると計測不能なリードが発生し、最適化シグナルが機能しない。**

---

## チェック結果詳細（全11項目）

### M01 — Meta Pixel base code インストール

| 項目 | 結果 |
|------|------|
| 判定 | WARNING |
| LP-A (lp/job-seeker/index.html) | PASS — `<head>`内49行目にbase code配置 |
| トップページ (index.html) | PASS — `<head>`内45行目にbase code配置 |
| Pixel ID | `2326210157891886` — 両ページで一致 |
| fbevents.js バージョン | `en_US/fbevents.js` — 最新バージョン使用 |

**問題点:**
- コード内に `<!-- TODO: 2326210157891886 を Meta Business Manager で取得後に置換 -->` というコメントが残っている。Pixel IDはすでに正しく設定されているが、このコメントは「未確認」の印象を与え混乱の原因になる。削除すること。
- Pixel base codeの配置がGA4スクリプト（39行目）の直後（49行目）。Pixel base codeはGA4より前、`<head>`の最上部（GA4・他スクリプトより前）に配置するのがMetaの推奨。現状でもPageViewは計測されるが、レンダリングブロックのタイミングによっては初回セッションの数%がロストする可能性がある。

---

### M02 — Conversions API (CAPI) の実装

| 項目 | 結果 |
|------|------|
| 判定 | FAIL (Critical) |
| Cloudflare Worker | CAPIコード 0行 — 実装なし |
| サーバーサイドイベント送信 | なし |
| graph.facebook.com/events コール | なし |

**影響:** iOS 14.5以降、SafariのITP（Intelligent Tracking Prevention）によりブラウザ側Pixelのデータは約30〜40%ロストしていると推定される。CAPIがない現状では、Leadイベントの実態の6〜7割しかMetaに届いていない。EMQスコアも低下する。

**修正方法 (優先):** Cloudflare Worker（`api/worker.js`）にCAPIエンドポイントを追加する。LINEボタンがクリックされた際にWorkerへPOSTし、WorkerがGraph API `/ID/events` へサーバーサイド送信する。費用0円（Cloudflareの無料枠で十分）。

```
フロント（chat.js / LP-A onclick）→ POST /api/capi-lead → Worker → graph.facebook.com/v20.0/{PIXEL_ID}/events
```

---

### M03 — イベント重複排除 (Deduplication)

| 項目 | 結果 |
|------|------|
| 判定 | FAIL (Critical) |
| event_id 設定 | なし |
| CAPIとPixelのマッチング | 不可 (CAPIそのものが未実装) |

**影響:** 将来CAPIを追加したとき、event_idが設定されていないと同一イベントがブラウザPixelとCAPISの両方からMetaに届き、Leadが2重カウントされる。これはCPA計算を歪め、広告最適化が誤方向に進む。

**修正方法:** LeadイベントのfbqコールとCAPIの両方に同一の`event_id`を付与する。

```javascript
// フロント側
const eventId = 'lead_' + Date.now() + '_' + Math.random().toString(36).substr(2,9);
fbq('track', 'Lead', {}, {eventID: eventId});
// 同じeventIdをWorkerのCAPIコールにも渡す
```

---

### M04 — Event Match Quality (EMQ)

| 項目 | 結果 |
|------|------|
| 判定 | FAIL (Critical) |
| Advanced Matching | 未設定 |
| fbq('init') のパラメータ | IDのみ（ユーザー情報なし） |
| 推定EMQスコア | <5.0（Pixelのみ、ユーザー識別情報なし） |

**現状のPixel init:**
```javascript
fbq('init', '2326210157891886');  // ユーザーデータなし
```

**影響:** EMQが低いとMetaのAIがイベントをユーザープロファイルにマッチできず、類似オーディエンス・再ターゲティングの精度が大幅に低下する。EMQ 8.0以上が目標。

**対応方針:**
1. LINEクリック時にメールアドレス・電話番号は収集できないため、Pixelのみでの改善は限界がある
2. CAPIでサーバーサイドからIPアドレス・User-Agent・クライアントユーザーエージェントを送信することでEMQを4〜6ポイント改善できる
3. 将来的にLINE登録完了後のWebhookでCAPIにメールアドレスをハッシュ化して送信できれば EMQ 8.0に到達できる

---

### M-Pixel-1 — PageView イベント

| 項目 | 結果 |
|------|------|
| 判定 | WARNING |
| LP-A | PASS — `fbq('track', 'PageView')` が init直後に発火 |
| トップページ | PASS — `fbq('track', 'PageView')` が init直後に発火 |
| area/ (22ページ) | FAIL — Pixel未設置、PageView計測ゼロ |
| guide/ (44ページ) | FAIL — Pixel未設置、PageView計測ゼロ |
| blog/ (19ページ) | FAIL — Pixel未設置、PageView計測ゼロ |

合計85ページのうち2ページのみPageViewを計測 (カバレッジ2.4%)

---

### M-Pixel-2 — noscript フォールバック

| 項目 | 結果 |
|------|------|
| 判定 | PASS |
| LP-A | PASS — `<noscript><img>` タグあり（行63） |
| トップページ | PASS — `<noscript><img>` タグあり（行58） |

```html
<noscript><img height="1" width="1" style="display:none"
  src="https://www.facebook.com/tr?id=2326210157891886&ev=PageView&noscript=1"
/></noscript>
```

JavaScriptを無効にしているユーザーのページビューも計測される。

---

### M-Pixel-3 — Lead イベント実装

| 項目 | 結果 |
|------|------|
| 判定 | PASS（実装は十分） |
| LP-A のLead発火箇所 | 7箇所 |
| トップページのLead発火箇所 | 1箇所 |
| chat.js（LINEカード表示時） | 1箇所 |
| 実装方式 | `onclick` インライン + `typeof fbq!=='undefined'` ガード |

**LP-Aの7箇所の内訳:**

| ラベル | 場所 |
|--------|------|
| header_line_button | ヒーローセクション |
| steps_line_button | 3ステップセクション |
| fee_comparison_line_button | 手数料比較セクション |
| faq_line_button | FAQセクション |
| footer_line_button | フッターCTA |
| sticky_mobile_cta | モバイルスティッキーバー |
| exit_popup | 離脱インテントポップアップ |

**問題点（軽微）:**
- `typeof fbq!=='undefined'` ガードは正しいが、これはPixelの非同期読み込みが完了する前にユーザーが素早くボタンをクリックした場合にLeadが発火しない可能性がある。発火率を上げるには`fbq.queue`を確認するより確実な手法として、Pixelのロード後にハンドラを再設定する方式が望ましい。影響は軽微（5%以下）。
- `content_name`、`content_category`等のイベントパラメータが設定されていない（後述のM-Pixel-4参照）。

---

### M-Pixel-4 — イベントパラメータ

| 項目 | 結果 |
|------|------|
| 判定 | FAIL |
| content_name | 未設定 |
| content_category | 未設定 |
| content_type | 未設定 |
| value / currency | 未設定 |
| custom_data | 未設定 |

**現状:**
```javascript
fbq('track','Lead');  // パラメータなし
```

**推奨:**
```javascript
fbq('track', 'Lead', {
  content_name: 'LINE登録_看護師転職相談',
  content_category: '看護師転職',
  content_type: 'product',
  value: 0,
  currency: 'JPY'
}, {eventID: eventId});
```

イベントパラメータがあるとMetaのAIが「どのような価値のLeadか」を学習でき、類似オーディエンス精度が向上する。特にvlue/currencyはAEM（Aggregated Event Measurement）の設定でも必要になる。

---

### M-Pixel-5 — ChatOpen カスタムイベント

| 項目 | 結果 |
|------|------|
| 判定 | PASS（実装あり、但し注意点あり） |
| 実装箇所 | chat.js 333行目 |
| イベント種別 | `fbq("trackCustom", "ChatOpen")` |
| LINEカードクリック | `fbq("track", "Lead")` — 941行目 |

**注意点:**
- `trackCustom` はカスタムイベントとして正しい形式。
- ただしカスタムイベントはMetaのAEMダッシュボードでは「コンバージョンイベント」として設定できない（標準イベントのみAEMで最適化可能）。ChatOpenは計測目的にとどまり、広告最適化のターゲットイベントとしては使えない。
- チャットウィジェットからのLeadイベント（941行目）は標準イベントなので問題なし。

---

### M-Pixel-6 — サイト全体へのPixelカバレッジ

| 項目 | 結果 |
|------|------|
| 判定 | FAIL (Critical) |

| ページグループ | 総ページ数 | Pixel設置 | カバレッジ |
|--------------|-----------|----------|----------|
| LP-A | 1 | 1 | 100% |
| トップページ | 1 | 1 | 100% |
| area/ | 22 | 0 | 0% |
| guide/ | 44 | 0 | 0% |
| blog/ | 19 | 0 | 0% |
| **合計** | **87** | **2** | **2.3%** |

**影響:**
- SEOから流入するユーザー（area/・guide/・blog/経由）の行動がMetaに全く届かない
- カスタムオーディエンス「サイト訪問者」の母数が極めて小さくなる（LP-Aとトップページのみ）
- Meta広告のリターゲティング精度が著しく低下する
- ドメイン全体のPixelシグナルが弱くなりEMQが下がる

---

### M-Pixel-7 — Advanced Matching（自動詳細マッチング）

| 項目 | 結果 |
|------|------|
| 判定 | FAIL |
| 設定状態 | 未設定 |

`fbq('init', '2326210157891886')` のみで、第2引数のユーザーデータオブジェクトなし。

ナースロビーの場合、LPではメールアドレスや電話番号をフォームで収集していないためブラウザ側Advanced Matchingは適用困難。ただしLINE Webhook経由でCAPIを使うことで電話番号のハッシュ化送信は将来的に実現可能。

---

### M-Pixel-8 — iOS 14.5対応（AEM: Aggregated Event Measurement）

| 項目 | 結果 |
|------|------|
| 判定 | WARNING |
| ドメイン認証 | 部分的に実施済みと推定 |
| d6fd8814a7634eda8deaa2629270133d.txt | 存在確認 — これはSearch Console認証ファイルでありMeta認証ではない |
| Meta Business Managerでのドメイン認証 | 不明（Ads Managerで確認が必要） |
| 優先イベント設定（最大8個） | 設定不明 |

**確認が必要な手動作業:**
1. Meta Business Manager > イベントマネージャー > ウェブイベント設定ツール で `quads-nurse.com` のドメイン認証状態を確認
2. 認証方法: DNSレコード追加 または ファイル認証（Metaが指定するHTMLファイルをルートに配置）
3. 認証完了後、優先コンバージョンイベントを設定（Leadを最優先に設定）

**ドメイン認証がない場合の影響:** iOS 14.5以降のSafariユーザーからのLeadイベントがMetaに届かない（ゼロになる）。

---

### M-Pixel-9 — Conversions API (CAPI) — 詳細

| 項目 | 結果 |
|------|------|
| 判定 | FAIL (Critical) |
| api/worker.js | Facebook/Meta関連コード 0行 |
| scripts/ 内 | CAPI関連スクリプト なし |
| LINE Webhook → CAPI 連携 | なし |

**推奨実装パス（Cloudflareベース、費用0円）:**

```javascript
// api/worker.js に追加する処理
async function sendCAPIEvent(request, env) {
  const body = await request.json();
  const pixelId = '2326210157891886';
  const accessToken = env.META_CAPI_TOKEN; // Cloudflare Secretに設定

  const payload = {
    data: [{
      event_name: body.event_name,       // 'Lead'
      event_time: Math.floor(Date.now() / 1000),
      event_id: body.event_id,           // フロントと同一IDでdedup
      action_source: 'website',
      event_source_url: body.url,
      user_data: {
        client_ip_address: request.headers.get('CF-Connecting-IP'),
        client_user_agent: request.headers.get('User-Agent'),
        fbp: body.fbp,                   // _fbpクッキー値
        fbc: body.fbc,                   // _fbcクッキー値
      }
    }]
  };

  await fetch(`https://graph.facebook.com/v20.0/${pixelId}/events?access_token=${accessToken}`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload)
  });
}
```

---

## 優先修正リスト（Quick Wins）

### Critical — 広告出稿前に必須

| 優先度 | 対応内容 | 工数 | 影響 |
|--------|----------|------|------|
| 1 | Pixelを全87ページに追加（area/22、guide/44、blog/19） | 30分（スクリプト一括置換） | カバレッジ 2.3% → 100% |
| 2 | イベントパラメータ追加（Lead イベントに content_name, content_type, currency） | 15分 | EMQスコア改善、AEM設定可能化 |
| 3 | Meta Business Managerでドメイン認証を完了する | 15分（手動作業） | iOS 14.5対応、AEM有効化 |

### High — 出稿後1週間以内

| 優先度 | 対応内容 | 工数 | 影響 |
|--------|----------|------|------|
| 4 | event_id を Lead イベントに追加（CAPI実装の前準備） | 20分 | 将来の重複排除を保証 |
| 5 | CAPI実装（Cloudflare Worker経由） | 2〜3時間 | データロス30〜40%を回復 |
| 6 | TODOコメントの削除 | 5分 | コード品質、誤解防止 |

### Medium — 中期（月1以内）

| 優先度 | 対応内容 | 工数 | 影響 |
|--------|----------|------|------|
| 7 | LINE Webhook → CAPI連携（電話番号ハッシュ化送信） | 4〜6時間 | EMQ 4〜6ポイント改善 |
| 8 | Pixel base codeをGA4より前に移動 | 5分 | 初回セッションロスト微減 |

---

## Quick Win: Pixel 一括追加スクリプト

以下のスクリプトをターミナルで実行すると、area/・guide/・blog/ の全ページにPixelを追加できる。

```bash
#!/bin/bash
PIXEL_ID="2326210157891886"
PIXEL_CODE='    <!-- Meta Pixel -->
    <script>
      !function(f,b,e,v,n,t,s)
      {if(f.fbq)return;n=f.fbq=function(){n.callMethod?
      n.callMethod.apply(n,arguments):n.queue.push(arguments)};
      if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version="2.0";
      n.queue=[];t=b.createElement(e);t.async=!0;
      t.src=v;s=b.getElementsByTagName(e)[0];
      s.parentNode.insertBefore(t,s)}(window, document,"script",
      "https://connect.facebook.net/en_US/fbevents.js");
      fbq("init", "'"$PIXEL_ID"'");
      fbq("track", "PageView");
    </script>
    <noscript><img height="1" width="1" style="display:none"
      src="https://www.facebook.com/tr?id='"$PIXEL_ID"'&ev=PageView&noscript=1"
    /></noscript>'

DIRS=(
  "/Users/robby2/robby-the-match/lp/job-seeker/area"
  "/Users/robby2/robby-the-match/lp/job-seeker/guide"
  "/Users/robby2/robby-the-match/blog"
)

for dir in "${DIRS[@]}"; do
  for f in "$dir"/*.html; do
    if ! grep -q "fbq('init'" "$f" 2>/dev/null && ! grep -q 'fbq("init"' "$f" 2>/dev/null; then
      sed -i '' 's|</head>|'"$PIXEL_CODE"'\n  </head>|' "$f"
      echo "Added Pixel to: $f"
    fi
  done
done
```

実行前に1ファイルで動作確認してから全体適用すること。

---

## 手動確認が必要な項目

以下はファイル確認では判断できず、Meta Ads Manager / Events Manager での目視確認が必要。

| 確認事項 | 確認場所 |
|----------|----------|
| Pixelがリアルタイムで発火しているか | Events Manager > テストイベント |
| ドメイン認証の完了状態 | Business Manager > ブランドセーフティ > ドメイン |
| AEM 優先イベント設定（Lead が上位8位以内か） | Events Manager > ウェブイベント設定ツール |
| EMQスコアの実際の数値 | Events Manager > 概要 > イベントマッチ品質 |
| 重複排除率 | Events Manager > Pixel診断 |
| 実際のLeadイベント受信数 vs LINEクリック数 | Events Manager > イベントデータ vs GA4比較 |

---

## まとめ

**出稿可能な最低条件（3点セット）:**

1. Pixel全ページ設置（2.3% → 100%カバレッジ）
2. Meta Business Managerでドメイン認証完了
3. AEMで「Lead」を優先コンバージョンイベントに設定

この3点なしに¥500/日の出稿を開始しても、iOS 14.5ユーザー（想定ターゲットのミサキ世代がメイン利用者のiPhone率は高い）からのデータが届かず、Metaの最適化AIが正しく学習できない。

**CAPIは現時点では「すぐやる」ではなく「1週間以内にやる」扱いでよい。** まずドメイン認証とPixel全ページ設置を今日中に完了させることが最優先。
