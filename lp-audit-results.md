# 神奈川ナース転職 LP品質監査レポート
## ポストクリック体験（Post-Click Experience）監査

監査対象: https://quads-nurse.com/lp/job-seeker/
監査日: 2026-03-09
広告: AD1（ad1_local）/ AD3（ad3_empathy）
ファイル: /Users/robby2/robby-the-match/lp/job-seeker/index.html

---

## 総合スコア: 74 / 100（グレードB）

| カテゴリ | 配点 | 得点 | 評価 |
|---|---|---|---|
| メッセージマッチ | 25 | 17 | WARNING |
| ファーストビュー / CTA設計 | 20 | 16 | PASS |
| モバイル最適化 | 15 | 13 | PASS |
| ページ速度・技術品質 | 10 | 7 | WARNING |
| 信頼シグナル | 15 | 12 | PASS |
| Meta Pixelとの整合性 | 10 | 6 | WARNING |
| UTM処理・パーソナライズ | 5 | 3 | WARNING |

---

## 1. メッセージマッチ　17/25（WARNING）

### AD1「地域密着型」との整合性

**広告コピー（AD1）のメッセージ:**
- 「もっと近くで、もっと良い条件の職場ないかな」
- 「AIでマッチング → 人間が丁寧にサポート」
- 「紹介手数料10%だから病院も安心」

**LP冒頭（ファーストビュー）の実際:**
- H1: 「看護師5年目の平均年収は480万円。今の給与と比べてみませんか？」
- サブタイトル: 「大手エージェントの手数料は25%。神奈川ナース転職は10%」
- CTA: 「30秒で年収診断する」

**評価: WARNING**

手数料10%はヘッダー内サブタイトルで即座に視認できる（PASS）。ただし広告の「地域密着・近くで働く」というメッセージがファーストビューで弱い。LPのH1は「年収診断」フックで統一されており、AD1が伝えた「エリア感」との直接的な接続が薄い。看護師は「地域で探したい」という動機でクリックしているのに、LPに着地した瞬間は「年収の話」にシフトする。

**修正推奨:**
H1またはその直上に「神奈川県のあなたに合う職場、AIが30秒で見つけます」のような一文を入れることで、エリア感とAIマッチングの両方を接続できる。

---

### AD3「共感型」との整合性

**広告コピー（AD3）のメッセージ:**
- フック:「前にも言ったよね」（人間関係のしんどさへの共感）
- 「人間関係がしんどい。残業が当たり前。夜勤明けなのに呼び出される。」
- 「環境が合ってないだけかもしれない」
- 「転職するかどうかは後で決めていい」

**LPの実際:**
- H1は「年収480万円と比べてみませんか？」（給与比較フレーム）
- ファーストビューのサブ文言：「費用は完全無料 / 最短2週間で内定 / いつでもブロックOK」

**評価: FAIL**

これは明確なメッセージミスマッチ。AD3のユーザーは「前にも言ったよね」という感情的共感でクリックしている。人間関係のしんどさに寄り添ったコピーを読んで、心が動いてLPに来る。ところがLP冒頭は「年収480万円」という論理・金銭フレームに切り替わる。この感情の断絶がバウンス率を押し上げる主因になる。

AD3専用のLPが理想だが、最低限UTMで検知して冒頭文言を動的に変えるべきケース。現状UTMによる動的パーソナライズはtiktokのみ対応しており、`utm_campaign=ad3_empathy`は処理されない。

**修正推奨（即時実装可能）:**
```javascript
// 既存のTikTok personalizationスクリプトを拡張
if (params.get('utm_campaign') === 'ad3_empathy') {
    // loss-aversion-hookの文言を変える
    document.querySelector('.loss-aversion-hook').textContent =
        '「前にも言ったよね」その言葉に傷ついていませんか？';
    // H1サブテキストも変える
}
```

---

## 2. ファーストビュー / CTA設計　16/20（PASS）

### ファーストビューの可視要素（スクロールなし・モバイル想定）

| 要素 | 実装状況 |
|---|---|
| ブランド名（神奈川ナース転職） | PASS — サイトヘッダーに常設 |
| 手数料10%の訴求 | PASS — サブタイトルに「手数料10%」が太字・目立つ色で表示 |
| LINEへのCTAボタン | PASS — ヘッダー内にグリーンボタン（30秒で年収診断する） |
| 摩擦解除文言 | PASS — 「費用は完全無料 / いつでもブロックOK」 |
| 信頼バッジ | PASS — ヘッダー直後に許可番号・SSL・無料の3バッジ |

### CTAの数と配置

LINEへの誘導ボタンが合計7箇所。スクロールに合わせた適切な配置。

| 場所 | ラベル |
|---|---|
| ヘッダー | 30秒で年収診断する |
| 3ステップセクション | あなたの市場価値を確認する |
| 手数料比較セクション | 他の看護師が知っている情報をチェック |
| FAQセクション | LINEで気軽に質問する |
| 最終CTAセクション | LINEで無料相談する |
| モバイルスティッキーバー | 今すぐ無料診断する |
| 離脱インテントポップアップ | 無料で年収診断する |

**評価:** CTA数・配置は十分。ただしCTAのラベルが毎回異なるため、「どれが一番の行動か」というヒエラルキーが読みにくい面もある。最終CTAセクションの「LINEで無料相談する」が最もシンプルで最良のラベル。

---

## 3. モバイル最適化　13/15（PASS）

### 確認済みの実装

| チェック項目 | 状態 |
|---|---|
| `viewport` メタタグ | PASS — `width=device-width, initial-scale=1.0` |
| レスポンシブブレイクポイント | PASS — `@media (max-width: 768px)` でレイアウト切り替え |
| モバイルスティッキーCTAバー | PASS — 768px以下でfixed bottom表示、スクロール400px後に出現 |
| モバイルハンバーガーメニュー | PASS — site-nav-hamburger実装 |
| CTAボタンのタップサイズ | PASS — padding: 18px 50px（十分なタップ領域） |
| テーブルの横スクロール | PASS — `.comparison-table-wrap`でoverflow-x: auto |
| エリアカードのモバイル対応 | WARNING — 3列グリッドのまま。モバイルでは2列推奨 |
| チャットボタンの位置 | PASS — スティッキーCTAと重ならないよう `bottom: 100px` |
| フォントサイズ | PASS — h1が1.5rem（モバイル）、本文は読みやすいサイズ |

**モバイル上の軽微な課題:**
エリアカードが `grid-template-columns: repeat(3, 1fr)` のままモバイルでも3列。神奈川県の21エリア名が3列に並ぶと各カード幅が狭く、文字が潰れる可能性。2列に変更推奨。

---

## 4. ページ速度・技術品質　7/10（WARNING）

### 外部スクリプトの読み込み

```
1. Google Analytics (async)              — 問題なし
2. Microsoft Clarity (同期ブロック)       — WARNING
3. Meta Pixel (同期ブロック)              — WARNING
4. chat.css (link rel)                   — 問題なし
5. config.js (defer)                     — 問題なし
6. chat.js (defer)                       — 問題なし
7. /track.js (defer)                     — WARNING（存在不明）
```

**Clarity スクリプトが同期ブロッキング**（</head>直前に配置、asyncなし）。LCPへの影響あり。`async`属性を追加するだけで改善できる。

**Meta Pixelも同期ブロッキング**。標準的な設置方法だが、Metaの公式推奨はasyncを明示している。現状のコードはfbevents.jsのロードが非同期（`t.async=!0`）なので実害は限定的だが、スクリプトブロック自体はHTMLパースを止める。

**`/track.js`が不明**（ページ末尾でdefer読み込み）。このファイルの存在がリポジトリ内で確認できない。404になっている場合はネットワークエラーが発生し、ブラウザコンソールが汚れる。確認要。

**画像最適化:**
- `hero-2.webp` を背景画像（CSS）として使用 — WebPでOK
- `consultation.webp` をインライン画像で使用、`loading="lazy"` — PASS
- `ogp.png`（OGP）はPNG。WebP変換の優先度は低い

---

## 5. 信頼シグナル　12/15（PASS）

| 信頼要素 | 実装状況 |
|---|---|
| 有料職業紹介事業許可番号（23-ユ-302928） | PASS — 4箇所（Trust Badges、3ステップ後、Social Proof、フッター） |
| 「しつこい電話なし」の明示 | PASS — 複数箇所に記載 |
| 「完全無料」の明示 | PASS — ヘッダー・CTA・FAQ・フッターに記載 |
| 「いつでもブロックOK」の記載 | PASS — 心理的安全性を高める効果的なコピー |
| 50%返金保証（病院側への保証） | WARNING — 実装はあるが「求職者側に費用なし」と混同しやすい説明 |
| 元病院人事の経験 | PASS — advantage-cardに記載（ただしヘッダーには不在） |
| 口コミ・実績数値 | WARNING — 212施設・21エリアは記載あり。ただし「登録者数」「成約件数」など実績数字が不在 |
| 写真・顔 | FAIL — 運営者の顔・写真が一切なし。テキストのみ |

**最重要の欠如: 登録者・成約実績**

「神奈川ナース転職の強み」セクションに記載されている数値：
- 10%（手数料）
- 0円（求職者費用）
- 2週間（最短内定）
- 212（提携施設）
- 21（対応エリア）

これらはすべてサービス側の「スペック」であり、「利用者の実績」ではない。看護師が最も安心するのは「同じ境遇の人が使って良かった」という声だが、サービス開始初期で実績がないため現状は仕方ない。ただし将来的には「登録者数XX名」「内定率XX%」といった数字に差し替えることで信頼性が大幅向上する。

---

## 6. Meta Pixelとの整合性　6/10（WARNING）

### Pixel設定の確認

```javascript
fbq('init', '2326210157891886');
fbq('track', 'PageView');  // 自動
```

### コード内のfbqイベント

| 場所 | イベント |
|---|---|
| ヘッダーCTA | `fbq('track', 'Lead')` |
| 3ステップCTA | `fbq('track', 'Lead')` |
| 手数料比較CTA | `fbq('track', 'Lead')` |
| FAQセクションCTA | `fbq('track', 'Lead')` |
| 最終CTAセクション | `fbq('track', 'Lead')` |
| モバイルスティッキー | `fbq('track', 'Lead')` |
| 離脱インテントポップアップ | `fbq('track', 'Lead')` |

**問題1: TODOコメントがコードに残存**

```html
<!-- TODO: 2326210157891886 を Meta Business Manager で取得後に置換 -->
```

このコメントはPixelが実際に設置済みであることと矛盾している。PixelID `2326210157891886` が既にコードに埋め込まれているにも関わらず「取得後に置換」と書いてある。このTODOコメントは削除すべき。

**問題2: LeadイベントとLineクリックの混在**

全てのCTAで `gtag` のGA4イベントと `fbq('track', 'Lead')` が同時発火する。これは正しい設計だが、「Lead」はMeta標準の「問い合わせ完了」を意味するのに対し、ここではLINEのリンクをクリックした時点で発火している。LINEの友だち追加が完了したわけではない。

正確なトラッキングには2段階が必要:
1. LINEリンクclick → `fbq('track', 'InitiateCheckout')` または `fbq('track', 'Contact')`
2. LINE上でのメッセージ送信 or 友だち追加 → `fbq('track', 'Lead')` （LINE側からのCAPIかWebhookが必要）

現状は「LINEクリック = Lead」としており、LINEを開いただけでブロックした人も「Lead」にカウントされている。広告の最適化精度に影響する。

**問題3: CAPI（Conversions API）未実装**

LPからはブラウザPixelのみ。iOS 14.5以降のITP環境ではイベントの30-40%がブラウザでは計測不能。CloudflareのWorkerがAPIに繋がっているなら、サーバーサイドでのCAPI送信を実装すべき最優先事項。

---

## 7. UTMパラメータの処理　3/5（WARNING）

### 現在の実装

```javascript
var params = new URLSearchParams(window.location.search);
if (params.get('utm_source') === 'tiktok') {
    // TikTok向けウェルカムバナーを表示
}
```

### 問題点

`utm_source=instagram` および `utm_campaign=ad1_local` / `utm_campaign=ad3_empathy` は**処理されていない**。

AD1・AD3どちらのUTMで来ても、LPの表示内容は完全に同じ。

| UTM | 現在の処理 | 推奨 |
|---|---|---|
| `utm_source=tiktok` | バナー表示あり | OK |
| `utm_source=instagram` | 何もしない | Instagram向けウェルカム or なにもしない（許容） |
| `utm_campaign=ad1_local` | 何もしない | H1をエリア訴求に変更 |
| `utm_campaign=ad3_empathy` | 何もしない | H1を共感訴求に変更（最優先修正） |

---

## 8. チャットウィジェット → LINE導線　評価: PASS（設計は良好）

- チャットボタンは固定表示（chat-toggle）
- `chat.css` / `chat.js` / `config.js` の3ファイル構成
- チャットヘッダーに「30秒で年収診断」という訴求あり
- モバイルでは `bottom: 100px` で sticky CTAバーと重ならない

チャットの最終的な誘導先がLINEへの誘導になっているかはchat.jsの詳細確認が必要だが、LINEのwebhook連携は実装済みとのことで、LINE → Cloudflare Worker → ヒアリングフローが機能していれば導線として問題ない。

---

## 優先度別 Quick Wins

### 最優先（5分以内）

**QW-1: TODOコメントの削除**
```html
<!-- TODO: 2326210157891886 を Meta Business Manager で取得後に置換 -->
```
このコメントを削除する。コードの信頼性・Pixel設定への誤解を防ぐ。

**QW-2: Clarity scriptにasyncを追加**
```html
<!-- 変更前 -->
<script type="text/javascript">
    (function(c,l,a,r,i,t,y){ ...

<!-- 変更後 -->
<script async type="text/javascript">
    (function(c,l,a,r,i,t,y){ ...
```

**QW-3: /track.jsの存在確認**
```bash
ls /Users/robby2/robby-the-match/track.js
```
存在しない場合はindex.htmlから `<script src="/track.js" defer></script>` を削除。

---

### 高優先（15分以内）

**QW-4: AD3（empathy）のメッセージマッチ修正**

既存のTikTokパーソナライゼーションスクリプトを拡張し、`utm_campaign=ad3_empathy`を検知してヘッダーの冒頭文言を変更する。

```javascript
// 既存スクリプトブロックに追記（行1783付近）
if (params.get('utm_campaign') === 'ad3_empathy') {
    var hook = document.querySelector('.loss-aversion-hook');
    if (hook) hook.textContent = 'その「前にも言ったよね」、あなたのせいじゃない';
    var h1 = document.querySelector('h1');
    if (h1) {
        h1.innerHTML = '環境が合っていないだけ。<br>神奈川県には、あなたに合う職場がある。<br><small style="font-size: 0.55em;">神奈川県全域の看護師転職サポート — 相談無料</small>';
    }
}
```

**QW-5: エリアカードをモバイル2列に変更**

```css
@media (max-width: 768px) {
    .area-cards {
        grid-template-columns: repeat(2, 1fr); /* 3列 → 2列 */
        gap: 8px;
    }
}
```

---

### 中優先（1-2時間）

**QW-6: Pixelイベントの精緻化**

LINEクリックイベントを `Lead` から `Contact` に変更し、友だち追加完了を区別する。

```javascript
// 現状: fbq('track','Lead')
// 変更後:
fbq('track', 'Contact'); // LINEリンクのクリック
// 友だち追加完了はCAPI（サーバーサイド）で別途Leadとして送信
```

**QW-7: AD1専用の冒頭パーソナライズ**

```javascript
if (params.get('utm_campaign') === 'ad1_local') {
    var hook = document.querySelector('.loss-aversion-hook');
    if (hook) hook.textContent = '神奈川県で、あなたに合う近くの職場を探しています';
}
```

---

### 将来的な改善（1日以上）

**QW-8: CAPIの実装**

Cloudflare Worker（robby-the-match-api）に`/api/meta-event`エンドポイントを追加し、LINEクリック時にサーバーサイドでもMeta Conversions APIにイベントを送信。event_idによるデデュープを必ず実装すること。

**QW-9: 社会的証明の強化**

最初の成約が完了したタイミングで「登録看護師数」「紹介実績」などの数字をProof Sectionに追加。現状の「212施設・21エリア」はサービス側の数字であり、利用者視点の信頼シグナルに差し替えていく。

**QW-10: AD3専用LP（将来）**

AD3（共感型）は感情訴求の強い広告なので、専用LPを作成することでコンバージョン率が大幅に改善する可能性がある。ただし現フェーズではUTMによる動的文言変更（QW-4）で代替し、月間LINE登録が10名を超えてから専用LP化を検討。

---

## 確認が必要な事項（平島さんへ）

1. **`/track.js`** — このファイルはどこにありますか？存在しない場合はHTMLから参照を削除してください
2. **Meta Pixel ID `2326210157891886`** — Business Manager上でイベントが正常に受信されていますか？Test Events Toolで確認してください
3. **「2週間で内定」という表記** — 現時点でまだ成約実績がない場合、この表記は景品表示法・職業安定法の観点からリスクになる可能性があります。「最短」という修飾語が付いているので即座の問題ではありませんが、根拠となる実績が出たらその数字に差し替えることを推奨します
4. **50%返金保証のセクション** — 「病院に返金する」保証であることが分かりにくい。看護師が「自分に返金される」と誤解する可能性があるため、「病院への返金保証 = あなたのリスクが下がる」という説明構造に変えることを推奨します

---

## まとめ

LPの基本品質は高い。手数料10%の訴求、許可番号の明示、CTAの配置数、モバイルのスティッキーバー、FAQ設計など、コンバージョン最適化の要素が丁寧に実装されている。

最大の問題点はAD3（共感型）とのメッセージマッチの断絶。感情的共感でクリックしてきた看護師が、LPで「年収480万円」という論理的フレームに転換されることでバウンスが起きている可能性がある。QW-4の動的文言変更を最優先で実装すること。

次の優先事項はMeta PixelのTODOコメント削除（QW-1）と、/track.jsの存在確認（QW-3）。これらは数分で対応可能。
