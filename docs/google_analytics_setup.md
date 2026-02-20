# Google Analytics 4 (GA4) 設定ガイド — ROBBY THE MATCH

> このドキュメントは、ROBBY THE MATCHの全LPおよびSEOページにGA4を設定するための手順書です。

---

## 1. GA4プロパティ作成手順

### 1-1. Googleアカウント準備

- はるひメディカルサービスのGoogleアカウントでログイン
- https://analytics.google.com/ にアクセス

### 1-2. プロパティ作成

1. 左下の **管理（歯車アイコン）** をクリック
2. **プロパティを作成** をクリック
3. 以下を入力:
   - プロパティ名: `ROBBY THE MATCH`
   - レポートのタイムゾーン: `日本`
   - 通貨: `日本円 (JPY)`
4. **次へ** をクリック
5. ビジネスの説明:
   - 業種: `ビジネスおよび産業マーケット` (または最も近いもの)
   - ビジネスの規模: `小規模`
6. ビジネス目標: `リードの生成` を選択
7. **作成** をクリック

### 1-3. データストリーム作成

1. プロパティ作成後、**ウェブ** を選択
2. ウェブサイトのURL: `robby-the-match.pages.dev` (実際のドメイン)
3. ストリーム名: `ROBBY LP`
4. **ストリームを作成** をクリック

---

## 2. 測定IDの取得方法

1. **管理** > **データストリーム** > 作成したストリームをクリック
2. 画面上部に表示される **測定ID** をコピー
   - 形式: `G-XXXXXXXXXX`
3. この測定IDを以下のファイルに設定:
   - `/lp/analytics.js` の `GA_MEASUREMENT_ID` 変数
   - `.env` に `GA_MEASUREMENT_ID=G-XXXXXXXXXX` を追加（任意）

---

## 3. 全ページへの設置確認チェックリスト

### 設置対象ファイル

| ファイル | 種別 | 設置状態 |
|---------|------|---------|
| `lp/job-seeker/index.html` | LP-A (求職者向け) | [ ] |
| `lp/facility/index.html` | LP-B (施設向け) | [ ] |
| `lp/` 以下の全SEO子ページ | SEOコンテンツ | [ ] |

### 設置方法

各HTMLファイルの `<head>` 内に以下を追加:

```html
<!-- Google Analytics 4 -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script src="/analytics.js"></script>
```

または、analytics.js を使わずインラインで設置する場合:

```html
<!-- Google Analytics 4 -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX');
</script>
```

### 設置確認手順

1. ページをブラウザで開く
2. Chrome DevTools > **Network** タブを開く
3. `collect` でフィルタ
4. ページを再読み込み
5. `https://www.google-analytics.com/g/collect?...` へのリクエストがあることを確認
6. GA4の **リアルタイム** レポートでアクティブユーザーが表示されることを確認

---

## 4. カスタムイベント設定

### 4-1. LINE登録クリック

LINEボタンのクリックを計測する。

```javascript
// analytics.js に組み込み済み
gtag('event', 'line_click', {
  event_category: 'engagement',
  event_label: 'LINE登録ボタン',
  page_location: window.location.href
});
```

**設定場所:** LINE登録ボタンの `onclick` 属性、または analytics.js の自動バインド

### 4-2. ページスクロール深度

25%, 50%, 75%, 100% のスクロール到達を計測する。

```javascript
// analytics.js に組み込み済み（自動トラッキング）
gtag('event', 'scroll_depth', {
  event_category: 'engagement',
  event_label: '50%',
  value: 50
});
```

**GA4デフォルト:** GA4はデフォルトで90%スクロールを計測するが、
より細かい粒度 (25%, 50%, 75%) を analytics.js でカスタム計測する。

### 4-3. フォーム送信

問い合わせフォーム（LP-B施設向け）の送信を計測する。

```javascript
gtag('event', 'form_submit', {
  event_category: 'lead',
  event_label: 'facility_inquiry',
  page_location: window.location.href
});
```

### 4-4. 電話番号クリック

`tel:` リンクのクリックを計測する。

```javascript
gtag('event', 'phone_click', {
  event_category: 'lead',
  event_label: '電話問い合わせ',
  page_location: window.location.href
});
```

---

## 5. コンバージョン設定方法

### 5-1. GA4管理画面でのコンバージョン設定

1. GA4 > **管理** > **イベント** を開く
2. カスタムイベントが記録されていることを確認
3. 以下のイベントを **コンバージョンとしてマーク**:

| イベント名 | コンバージョン | 説明 |
|-----------|:-----------:|------|
| `line_click` | ON | LINE登録ボタンクリック (最重要KPI) |
| `form_submit` | ON | 施設向け問い合わせフォーム送信 |
| `phone_click` | ON | 電話番号クリック |
| `scroll_depth` | OFF | エンゲージメント指標（コンバージョンにしない） |

### 5-2. コンバージョンに値を設定（任意）

1. **管理** > **イベント** > 対象イベントを編集
2. **イベントの値** に金額を設定:
   - `line_click`: 5,000円（LINE登録1件あたりの想定価値）
   - `form_submit`: 50,000円（施設問い合わせ1件あたりの想定価値）

### 5-3. ファネル分析用のイベント設計

```
page_view (自動)
  → scroll_depth_50 (ページ半分まで読んだ)
    → line_click (LINE登録ボタンクリック)
      → [LINE側で登録完了を計測]
```

---

## 6. Search Console 連携手順

### 6-1. Search Console にサイトを追加

1. https://search.google.com/search-console/ にアクセス
2. **プロパティを追加** をクリック
3. **URLプレフィックス** を選択
4. サイトのURL（例: `https://robby-the-match.pages.dev`）を入力
5. 所有権の確認方法:
   - **HTMLタグ** を選択（最も簡単）
   - 表示されたmetaタグをLPの `<head>` に追加:
     ```html
     <meta name="google-site-verification" content="xxxxxxxxxxxxxx" />
     ```
   - **確認** をクリック

### 6-2. GA4とSearch Consoleを連携

1. GA4 > **管理** > **Search Consoleのリンク**
2. **リンク** をクリック
3. 先ほど追加したSearch Consoleプロパティを選択
4. ウェブストリームを選択
5. **送信** をクリック

### 6-3. 連携後にできること

- GA4の **集客** > **Search Console** レポートで以下が確認可能:
  - 検索クエリ（どんなキーワードで検索されているか）
  - 検索順位の平均
  - クリック数 / 表示回数 / CTR
  - ランディングページ別パフォーマンス
- ローカルSEO施策の効果測定に使用:
  - 「小田原 看護師 転職」等のキーワードでの表示回数推移
  - LP-AとSEO子ページそれぞれのパフォーマンス比較

### 6-4. サイトマップ送信

1. Search Console > **サイトマップ**
2. `sitemap.xml` のURLを入力して送信
   - 例: `https://robby-the-match.pages.dev/sitemap.xml`
3. ステータスが「成功」になることを確認

---

## 確認チェックリスト（全手順完了後）

- [ ] GA4プロパティが作成されている
- [ ] 測定IDが取得できている (G-XXXXXXXXXX)
- [ ] `lp/analytics.js` に測定IDが設定されている
- [ ] LP-A (`lp/job-seeker/index.html`) にGA4タグが設置されている
- [ ] LP-B (`lp/facility/index.html`) にGA4タグが設置されている（ファイルが存在する場合）
- [ ] SEO子ページにGA4タグが設置されている
- [ ] リアルタイムレポートでデータが確認できる
- [ ] `line_click` イベントがコンバージョンに設定されている
- [ ] `form_submit` イベントがコンバージョンに設定されている
- [ ] Search Console にサイトが追加されている
- [ ] GA4とSearch Consoleが連携されている
- [ ] サイトマップが送信されている

---

## トラブルシューティング

### GA4にデータが来ない

1. ブラウザの広告ブロッカーを無効にして確認
2. DevTools > Console でJavaScriptエラーがないか確認
3. `analytics.js` のパスが正しいか確認
4. 測定IDが正しいか確認 (`G-` で始まること)

### Search Console で所有権が確認できない

1. HTMLタグが `<head>` 内に正しく配置されているか確認
2. ページが公開（デプロイ済み）であることを確認
3. Cloudflare Pages のキャッシュをパージしてから再試行

### カスタムイベントが記録されない

1. DevTools > Network で `collect` リクエストのパラメータを確認
2. `en` パラメータにイベント名が含まれているか確認
3. GA4 > リアルタイム > イベント数 で確認（反映に数秒かかる）
