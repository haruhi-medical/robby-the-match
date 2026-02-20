# ROBBY THE MATCH マーケティング & コンバージョン最適化 総合計画書

**作成日:** 2026年2月16日
**対象サイト:** ROBBY THE MATCH LP（index.html）
**ターゲット:** 神奈川県西部の看護師（転職検討中・情報収集中）
**目標:** 登録CV率 3%以上 / チャット開始率 8%以上 / CPA 15,000円以下

---

## 目次

1. [現状分析](#1-現状分析)
2. [SEO最適化](#2-seo最適化)
3. [コンバージョンファネル最適化](#3-コンバージョンファネル最適化)
4. [アナリティクス＆トラッキング](#4-アナリティクストラッキング)
5. [ソーシャルプルーフ＆信頼構築](#5-ソーシャルプルーフ信頼構築)
6. [リマーケティング＆ナーチャリング](#6-リマーケティングナーチャリング)
7. [広告プラットフォーム対応](#7-広告プラットフォーム対応)
8. [A/Bテストフレームワーク](#8-abテストフレームワーク)
9. [実装ロードマップ](#9-実装ロードマップ)

---

## 1. 現状分析

### 1.1 サイト構成

| 要素 | 現状 | 評価 |
|------|------|------|
| ページ構成 | LP1枚 + 利用規約 + プライバシーポリシー | シンプルで良いが、SEO面で弱い |
| CTA | ヒーロー / 求人セクション / ミッションセクション / フォーム | 配置は適切だが、sticky CTAなし |
| フォーム項目 | 必須9項目 + 任意5項目 + 同意チェック | 項目が多い（離脱リスク） |
| AIチャット | フローティングボタン + チャットウィンドウ | 実装済みだが訴求が弱い |
| OGP/Twitter Card | 設定済み | og:url が空、og:image パス要確認 |
| 構造化データ | **なし** | 要追加（最優先） |
| GA/トラッキング | **なし** | 要追加（最優先） |
| 信頼セクション | 許可番号（未取得）、個人情報保護、運営会社 | 口コミ・実績数値なし |
| パフォーマンス | canvas + パーティクル + 複数アニメーション | モバイルで重い可能性 |

### 1.2 現状ファネル

```
[検索/広告流入] → [ヒーローセクション閲覧] → [スクロール（特長/求人/流れ）]
    → [登録フォーム送信] or [AIチャット開始]
```

**課題:**
- 中間CTAが「ボタン1つ」のみで、行動の選択肢が少ない
- フォーム項目数が多く、心理的ハードルが高い
- AIチャットの存在感が薄い（右下のフローティングボタンのみ）
- 離脱時のリテンション施策がない
- ソーシャルプルーフが完全に不足

### 1.3 競合との差別化ポイント

| 差別化要素 | 詳細 | マーケティング活用度 |
|-----------|------|---------------------|
| 手数料10% | 業界平均の約半分 | ヒーローで訴求済み |
| AI×人のハイブリッド | 24時間対応 | チャットUIあるが訴求弱い |
| 50%返金保証 | 入職3ヶ月以内 | カード内で言及のみ |
| 地域特化（神奈川県西部） | ニッチ戦略 | ラベルで言及のみ |

---

## 2. SEO最適化

### 2.1 構造化データ（JSON-LD）

index.htmlの`<head>`内に以下の構造化データを追加する。

#### Organization（組織情報）

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "ROBBY THE MATCH",
  "legalName": "株式会社はるひメディカルサービス",
  "url": "https://robby-the-match.com",
  "logo": "https://robby-the-match.com/assets/logo.png",
  "description": "看護師転職の手数料を10%に抑えた、AIと人のハイブリッド型医療人材紹介サービス",
  "foundingDate": "2026",
  "address": {
    "@type": "PostalAddress",
    "addressRegion": "神奈川県",
    "addressCountry": "JP"
  },
  "contactPoint": {
    "@type": "ContactPoint",
    "contactType": "customer service",
    "email": "info@robby-the-match.com",
    "availableLanguage": "Japanese"
  },
  "sameAs": []
}
</script>
```

#### EmploymentAgency（人材紹介業）

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "EmploymentAgency",
  "name": "ROBBY THE MATCH",
  "description": "神奈川県西部に特化した看護師転職サービス。手数料10%でAI×人のハイブリッド紹介。",
  "url": "https://robby-the-match.com",
  "areaServed": {
    "@type": "State",
    "name": "神奈川県"
  },
  "serviceType": "有料職業紹介",
  "priceRange": "求職者無料",
  "openingHoursSpecification": {
    "@type": "OpeningHoursSpecification",
    "dayOfWeek": ["Monday","Tuesday","Wednesday","Thursday","Friday"],
    "opens": "09:00",
    "closes": "18:00"
  }
}
</script>
```

#### FAQPage（よくある質問）

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "求職者は無料で利用できますか？",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "はい、求職者の方は完全無料でご利用いただけます。手数料10%は求人医療機関に対するものであり、看護師の方に費用は一切かかりません。"
      }
    },
    {
      "@type": "Question",
      "name": "なぜ手数料が10%と安いのですか？",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "AI技術を活用して業務を効率化することで、従来のエージェント型紹介に比べて大幅にコストを削減しています。浮いた費用は病院の経営余力となり、看護師の待遇改善に還元されます。"
      }
    },
    {
      "@type": "Question",
      "name": "転職するか決めていなくても相談できますか？",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "もちろんです。情報収集だけでもお気軽にご相談ください。AIチャットで24時間いつでもお話しいただけます。"
      }
    },
    {
      "@type": "Question",
      "name": "入職後に合わなかった場合はどうなりますか？",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "入職後3ヶ月以内の自己都合退職の場合、紹介手数料の50%を求人医療機関に返金する保証制度があります。詳細は利用規約をご確認ください。"
      }
    },
    {
      "@type": "Question",
      "name": "対応エリアはどこですか？",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "神奈川県西部（小田原市、南足柄市、足柄上郡、足柄下郡など）を中心に、神奈川県全域の求人をご紹介しています。"
      }
    }
  ]
}
</script>
```

#### WebSite（サイト検索対応）

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "ROBBY THE MATCH",
  "url": "https://robby-the-match.com",
  "description": "手数料10%の医療人材紹介サービス",
  "inLanguage": "ja"
}
</script>
```

### 2.2 メタタグ最適化

#### 現状の問題点と改善

```html
<!-- 改善版 title（32文字以内） -->
<title>看護師転職 神奈川|手数料10%のROBBY THE MATCH</title>

<!-- 改善版 description（120文字以内、行動喚起含む） -->
<meta name="description" content="神奈川県西部の看護師転職なら手数料10%のROBBY THE MATCH。AI×専門エージェントのハイブリッドサポートで24時間相談可能。入職後50%返金保証付き。3分で無料登録。">

<!-- canonical URL 追加 -->
<link rel="canonical" href="https://robby-the-match.com/">

<!-- robots 追加 -->
<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">

<!-- OGP 修正 -->
<meta property="og:url" content="https://robby-the-match.com/">
<meta property="og:site_name" content="ROBBY THE MATCH">
<meta property="og:image" content="https://robby-the-match.com/assets/ogp.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">

<!-- 追加メタタグ -->
<meta name="theme-color" content="#0D1B2A">
<meta name="format-detection" content="telephone=no">
<link rel="icon" type="image/png" href="/assets/favicon.png">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
```

### 2.3 ターゲットキーワード戦略

#### 主要キーワード（月間検索ボリューム目安）

| 優先度 | キーワード | 想定月間検索数 | 競合度 | 対策ページ |
|--------|----------|---------------|--------|-----------|
| S | 看護師 転職 神奈川 | 1,000-2,000 | 高 | LP + 将来的にコンテンツ |
| S | 看護師 求人 小田原 | 100-300 | 中 | LP（地域特化） |
| A | 看護師 転職 手数料 安い | 50-200 | 低 | LP（差別化ポイント） |
| A | 神奈川県西部 看護師 求人 | 50-150 | 低 | LP |
| A | 訪問看護 求人 神奈川 | 200-500 | 中 | LP + 将来記事 |
| B | 看護師 転職 相談 無料 | 300-800 | 中 | LP（CTA文言） |
| B | 看護師 転職 AI | 50-100 | 低 | LP（差別化） |
| B | 看護師 転職サイト おすすめ | 5,000+ | 高 | 将来的にコンテンツ |
| C | 看護師 夜勤 転職 | 200-500 | 中 | 将来記事 |
| C | 看護師 ブランク 復帰 神奈川 | 50-100 | 低 | 将来記事 |

#### LP内キーワード最適化

**h1タグ:**
現在: 「あなたの経験に、ふさわしい職場を。」
改善案: 変更不要（ブランドメッセージとして優秀）。ただしh1の直下にキーワード含有テキスト追加を推奨。

**セクション見出し内にキーワード自然配置:**
- `#features`: 「看護師転職で選ばれる4つの理由」（キーワード「看護師転職」追加）
- `#hospitals`: 「神奈川県西部の看護師求人情報」（キーワード「神奈川県西部」「看護師求人」追加）
- `#flow`: 変更不要

**img alt属性追加（将来画像追加時）:**
- ヒーロー画像: `alt="神奈川県西部の看護師転職相談 ROBBY THE MATCH"`
- 各セクション画像: 関連キーワードを含む自然な説明文

### 2.4 内部リンク構造

```
index.html（メインLP）
├── #features（特長） ← ヘッダーナビ + フッター
├── #hospitals（求人情報） ← ヘッダーナビ + フッター
├── #flow（利用の流れ） ← ヘッダーナビ + フッター
├── #mission（ミッション）← ヘッダーナビ
├── #register（登録フォーム）← 全CTAボタン
├── privacy.html ← フッター + フォーム同意文
├── terms.html ← フッター + フォーム同意文
└── [将来] /blog/ ← フッター + 各セクション関連記事リンク
```

**改善点:**
- privacy.html / terms.html に `rel="nofollow"` は不要（法的ページはクロール許可）
- 将来のブログ/コラムページからLPへの内部リンクを戦略的に設計
- sitemap.xml の作成（ドメイン確定後）

### 2.5 サイトスピード最適化

#### 現状の問題点

1. **canvas パーティクルアニメーション**: モバイルで30パーティクル + 接続線描画は重い
2. **ローディングスクリーン**: 800msの強制待機はFCP（First Contentful Paint）に悪影響
3. **カスタムカーソル**: requestAnimationFrame常時実行
4. **CSS/JS未圧縮**: minify未実施

#### 改善施策

| 施策 | 効果 | 実装難度 | 優先度 |
|------|------|---------|--------|
| CSS/JS minify | FCP改善 | 低 | S |
| ローディングスクリーン短縮（400ms以下） | FCP改善 | 低 | S |
| パーティクル数削減（モバイル15個） | LCP/CLS改善 | 低 | A |
| 画像遅延読み込み（将来画像追加時） | LCP改善 | 低 | A |
| フォントpreload | FCP改善 | 低 | A |
| Service Worker導入 | オフライン対応+キャッシュ | 中 | B |
| CSS critical path分離 | FCP改善 | 中 | B |

```html
<!-- preconnect/preload追加 -->
<link rel="preconnect" href="https://fonts.googleapis.com" crossorigin>
<link rel="dns-prefetch" href="https://hooks.slack.com">
```

---

## 3. コンバージョンファネル最適化

### 3.1 CTA配置・メッセージ最適化

#### 現状のCTA配置

| 場所 | CTAテキスト | 課題 |
|------|-----------|------|
| ヒーロー | 「無料で相談する」 | OK |
| 求人セクション下 | 「この求人についてもっと詳しく聞く」 | 文言が長い |
| ミッションセクション下 | 「私たちに相談してみませんか？」 | 弱い（疑問形） |
| ヘッダーナビ | 「無料で相談する」 | OK |
| AIチャットボタン | 吹き出しアイコン | 何のボタンか不明確 |

#### 改善案

**ヒーローCTA:** そのまま維持。サブテキスト「登録は3分。まずはお気軽にご相談ください。」は効果的。

**求人セクションCTA:**
```
現在: 「この求人についてもっと詳しく聞く」
改善: 「この求人に応募可能か確認する」（行動の具体性UP）
```

**ミッションセクションCTA:**
```
現在: 「私たちに相談してみませんか？」
改善: 「無料で転職相談する」（疑問形→命令形、行動喚起強化）
```

**AIチャットボタン:**
```
現在: 吹き出しアイコンのみ
改善: ラベル付きバッジ「AIに相談（無料）」+ パルスアニメーション
初回訪問3秒後に自動でツールチップ表示「転職の悩み、AIが24時間お答えします」
```

#### 追加CTAポイント

**特長セクション下に追加:**
```html
<div class="section-cta">
  <p class="cta-question">今の職場に不満はありますか？</p>
  <a href="#register" class="btn btn-primary">3分で無料登録</a>
  <span class="cta-or">または</span>
  <button class="btn btn-outline" id="startChat">AIに相談してみる</button>
</div>
```

### 3.2 離脱防止ポップアップ（Exit-Intent）

**トリガー条件:**
- デスクトップ: マウスがビューポート上部に移動した時
- モバイル: 「戻る」ボタンタップ時（history API利用）
- 共通: ページ滞在30秒以上 かつ フォーム未送信 かつ チャット未開始
- 表示は1セッション1回のみ（sessionStorage管理）

**ポップアップデザイン:**

```
┌──────────────────────────────────────┐
│                  ×                    │
│                                      │
│   転職、まだ迷っていますか？          │
│                                      │
│   情報収集だけでもOK。               │
│   AIが24時間あなたの相談に乗ります。  │
│                                      │
│   [今すぐAIに相談する]  ← Primary    │
│   [フォームで登録する]  ← Secondary  │
│                                      │
│   後で検討する                        │
└──────────────────────────────────────┘
```

**実装（vanilla JS）:**

```javascript
// exit-intent-popup.js
(function() {
  let shown = false;
  const DELAY = 30000; // 30秒後から有効化
  let ready = false;

  setTimeout(() => { ready = true; }, DELAY);

  // Desktop: mouse leave viewport top
  document.addEventListener('mouseout', function(e) {
    if (!ready || shown) return;
    if (e.clientY <= 0 && !sessionStorage.getItem('exit_popup_shown')) {
      showPopup();
    }
  });

  // Mobile: back button intercept
  if (/Mobi|Android/i.test(navigator.userAgent)) {
    history.pushState(null, '', location.href);
    window.addEventListener('popstate', function() {
      if (!shown && ready && !sessionStorage.getItem('exit_popup_shown')) {
        history.pushState(null, '', location.href);
        showPopup();
      }
    });
  }

  function showPopup() {
    shown = true;
    sessionStorage.setItem('exit_popup_shown', '1');
    // ポップアップDOM生成・表示ロジック
    // GA4イベント送信: exit_intent_shown
  }
})();
```

### 3.3 モバイル スティッキーCTAバー

**デザイン:**
画面下部に固定表示。スクロールでフォームセクションが見えている時は非表示。

```css
.sticky-cta-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  width: 100%;
  background: rgba(13, 27, 42, 0.95);
  backdrop-filter: blur(20px);
  border-top: 1px solid rgba(0, 180, 216, 0.3);
  padding: 12px 16px;
  display: flex;
  gap: 8px;
  align-items: center;
  z-index: 900;
  transform: translateY(100%);
  transition: transform 0.3s ease;
}

.sticky-cta-bar.visible {
  transform: translateY(0);
}

.sticky-cta-bar .btn {
  flex: 1;
  padding: 12px;
  font-size: 0.9rem;
}
```

```html
<!-- モバイル用スティッキーCTA -->
<div class="sticky-cta-bar" id="stickyCta">
  <a href="#register" class="btn btn-primary">無料で相談する</a>
  <button class="btn btn-outline" id="stickyChat">AIに質問</button>
</div>
```

**表示ロジック:**
- ヒーローセクション通過後に表示
- フォームセクションが画面内に入ったら非表示
- 900px以上のデスクトップでは非表示（`display: none`）

### 3.4 フォーム最適化

#### ステップフォーム化（段階的開示）

現在のフォームは一画面に全項目を表示しているが、ステップ分割でCVR向上を狙う。

```
Step 1（必須・最小限）: 氏名 + 電話番号 + 経験年数
  → 「次へ」ボタン（プログレスバー 1/3）

Step 2（条件確認）: 希望転職時期 + 希望給与 + 現在の勤務状況
  → 「次へ」ボタン（プログレスバー 2/3）

Step 3（任意・詳細）: メール + 勤務形態 + 夜勤 + その他
  → 「送信する」ボタン（プログレスバー 3/3）
  ※ Step 3はスキップ可能
```

**効果:** 初回ステップの心理的ハードルを下げ、コミットメント効果で完了率向上。

#### マイクロコピー追加

```html
<!-- フォーム上部 -->
<p class="form-trust-line">
  <span class="trust-icon">&#128274;</span>
  情報はSSL暗号化で保護されています。営業電話は一切いたしません。
</p>

<!-- 電話番号入力欄下 -->
<small class="field-hint">エージェントからの連絡に使用します。LINEでの連絡も可能です。</small>

<!-- 送信ボタン直上 -->
<p class="submit-reassurance">
  &#10003; 登録は完全無料 &#10003; 営業電話なし &#10003; いつでも退会可能
</p>
```

---

## 4. アナリティクス＆トラッキング

### 4.1 GA4 実装計画

#### 基本設定

```html
<!-- GA4 タグ（head内に追加） -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX', {
    'send_page_view': true,
    'cookie_flags': 'SameSite=None;Secure'
  });
</script>
```

#### カスタムイベント設計

| イベント名 | トリガー | パラメータ | 重要度 |
|-----------|---------|-----------|--------|
| `form_start` | フォーム初回入力 | `field_name` | 高 |
| `form_step_complete` | ステップフォーム各段階完了 | `step_number`, `step_name` | 高 |
| `form_submit` | フォーム送信成功 | `urgency_level`, `experience`, `timing` | 最高（コンバージョン） |
| `form_error` | バリデーションエラー | `field_name`, `error_type` | 中 |
| `form_abandon` | フォーム入力開始後離脱 | `last_field`, `fields_completed` | 高 |
| `chat_open` | チャットウィンドウ展開 | `trigger_source` | 高 |
| `chat_consent` | チャット同意クリック | - | 高 |
| `chat_message_sent` | ユーザーメッセージ送信 | `step_number`, `message_length` | 中 |
| `chat_complete` | チャット完了（サマリー表示） | `completion_score`, `duration_seconds` | 最高（コンバージョン） |
| `chat_abandon` | チャット途中離脱 | `last_step`, `messages_sent` | 高 |
| `cta_click` | CTAボタンクリック | `cta_location`, `cta_text` | 中 |
| `section_view` | セクションの80%が表示 | `section_id` | 中 |
| `scroll_depth` | 25%, 50%, 75%, 100% | `depth_percent` | 低 |
| `exit_intent_shown` | 離脱ポップアップ表示 | - | 中 |
| `exit_intent_click` | 離脱ポップアップCTAクリック | `action_type` | 高 |
| `phone_click` | 電話番号タップ | `source_section` | 高 |
| `external_link` | 外部リンククリック | `link_url` | 低 |

#### コンバージョン設定

GA4管理画面で以下をコンバージョンとしてマーク:
1. `form_submit`（最重要）
2. `chat_complete`（重要）
3. `chat_consent`（マイクロコンバージョン）
4. `phone_click`（マイクロコンバージョン）

#### カスタムディメンション

| ディメンション名 | スコープ | 値の例 |
|----------------|--------|--------|
| `traffic_source_detail` | セッション | google_ads, line_ads, organic, direct |
| `user_device_category` | セッション | mobile, desktop, tablet |
| `user_first_visit` | ユーザー | true, false |
| `form_urgency_level` | イベント | A, B, C, D |
| `chat_completion_step` | イベント | 1, 2, 3, 4, 5 |

### 4.2 イベントトラッキング実装コード

```javascript
// analytics.js - GA4イベントトラッキング

(function() {
  'use strict';

  // ユーティリティ: gtag安全呼び出し
  function trackEvent(eventName, params) {
    if (typeof gtag === 'function') {
      gtag('event', eventName, params || {});
    }
  }

  // --- スクロール深度トラッキング ---
  const scrollThresholds = [25, 50, 75, 100];
  const scrollTracked = new Set();

  function checkScrollDepth() {
    const scrollTop = window.scrollY;
    const docHeight = document.documentElement.scrollHeight - window.innerHeight;
    const percent = docHeight > 0 ? Math.round((scrollTop / docHeight) * 100) : 0;

    scrollThresholds.forEach(function(threshold) {
      if (percent >= threshold && !scrollTracked.has(threshold)) {
        scrollTracked.add(threshold);
        trackEvent('scroll_depth', { depth_percent: threshold });
      }
    });
  }

  // --- セクション表示トラッキング ---
  var sectionObserver = new IntersectionObserver(function(entries) {
    entries.forEach(function(entry) {
      if (entry.isIntersecting) {
        trackEvent('section_view', { section_id: entry.target.id });
        sectionObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.8 });

  document.querySelectorAll('section[id]').forEach(function(section) {
    sectionObserver.observe(section);
  });

  // --- CTAクリックトラッキング ---
  document.querySelectorAll('.btn').forEach(function(btn) {
    btn.addEventListener('click', function() {
      var section = btn.closest('section');
      trackEvent('cta_click', {
        cta_text: btn.textContent.trim(),
        cta_location: section ? section.id : 'header'
      });
    });
  });

  // --- フォームトラッキング ---
  var formStarted = false;
  var form = document.getElementById('registerForm');
  if (form) {
    form.addEventListener('focusin', function(e) {
      if (!formStarted && e.target.matches('input, select, textarea')) {
        formStarted = true;
        trackEvent('form_start', { field_name: e.target.name });
      }
    });
  }

  // --- スクロールリスナー ---
  var scrollTicking = false;
  window.addEventListener('scroll', function() {
    if (!scrollTicking) {
      requestAnimationFrame(function() {
        checkScrollDepth();
        scrollTicking = false;
      });
      scrollTicking = true;
    }
  }, { passive: true });

  // --- UTMパラメータ保存 ---
  var urlParams = new URLSearchParams(window.location.search);
  var utmKeys = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content'];
  var utmData = {};
  utmKeys.forEach(function(key) {
    var val = urlParams.get(key);
    if (val) utmData[key] = val;
  });
  if (Object.keys(utmData).length > 0) {
    sessionStorage.setItem('utm_data', JSON.stringify(utmData));
  }

})();
```

### 4.3 UTMパラメータ運用

#### 命名規則

```
utm_source=   広告プラットフォーム（google, line, meta, indeed, nurse_navi）
utm_medium=   媒体タイプ（cpc, display, social, email, referral）
utm_campaign= キャンペーン名（spring_2026, odawara_nurse, night_shift）
utm_term=     キーワード（看護師_転職_神奈川）
utm_content=  クリエイティブ識別子（banner_a, text_01, video_15s）
```

#### UTM例

```
# Google検索広告
?utm_source=google&utm_medium=cpc&utm_campaign=nurse_kanagawa&utm_term=看護師_転職_神奈川

# LINE広告
?utm_source=line&utm_medium=display&utm_campaign=spring_2026&utm_content=carousel_a

# Indeed
?utm_source=indeed&utm_medium=referral&utm_campaign=odawara_hospital_a
```

---

## 5. ソーシャルプルーフ＆信頼構築

### 5.1 利用者の声セクション（新規追加）

**配置場所:** 「利用の流れ」セクションと「ミッション」セクションの間

```html
<!-- ========== 利用者の声 ========== -->
<section class="testimonials parallax-section" id="testimonials">
  <div class="container">
    <h2 class="section-title">転職された<span class="highlight">看護師の声</span></h2>
    <div class="testimonial-slider">
      <div class="testimonial-card">
        <div class="testimonial-rating">★★★★★</div>
        <p class="testimonial-text">
          「夜勤明けの深夜にAIチャットで相談できたのが本当に助かりました。
          翌日にはエージェントさんから電話があり、2週間で内定をいただけました。」
        </p>
        <div class="testimonial-author">
          <div class="author-info">
            <strong>A.Sさん（30代女性）</strong>
            <span>小田原市・総合病院 → 訪問看護ステーション</span>
            <span class="salary-change">月給28万円 → 35万円</span>
          </div>
        </div>
      </div>
      <!-- 追加の口コミカード -->
    </div>
  </div>
</section>
```

**注意:** 実際の利用者が出るまでは「想定される利用シーン」として掲載し、実績が蓄積され次第、実際の声に差し替える。

### 5.2 信頼バッジ戦略

#### 現状の信頼セクション改善

```html
<!-- 信頼バッジ（ヒーローセクション下部に小さく表示） -->
<div class="trust-badges">
  <div class="badge">
    <span class="badge-icon">&#128737;</span>
    <span>有料職業紹介許可</span>
  </div>
  <div class="badge">
    <span class="badge-icon">&#128274;</span>
    <span>SSL暗号化通信</span>
  </div>
  <div class="badge">
    <span class="badge-icon">&#128176;</span>
    <span>求職者完全無料</span>
  </div>
  <div class="badge">
    <span class="badge-icon">&#128260;</span>
    <span>50%返金保証</span>
  </div>
</div>
```

**配置場所:** ヒーローCTA直下 + フォーム送信ボタン直上

### 5.3 実績数値セクション（新規追加）

**配置場所:** ヒーローセクション直下（features の前）

```html
<!-- ========== 数字で見る実績 ========== -->
<section class="stats-bar">
  <div class="container">
    <div class="stats-grid">
      <div class="stat-item">
        <span class="stat-number count-up" data-target="10" data-suffix="%">10%</span>
        <span class="stat-label">紹介手数料</span>
      </div>
      <div class="stat-item">
        <span class="stat-number">24<small>時間</small></span>
        <span class="stat-label">AI相談対応</span>
      </div>
      <div class="stat-item">
        <span class="stat-number">50<small>%</small></span>
        <span class="stat-label">返金保証</span>
      </div>
      <div class="stat-item">
        <span class="stat-number">0<small>円</small></span>
        <span class="stat-label">求職者負担</span>
      </div>
    </div>
  </div>
</section>
```

**将来追加予定の数値:**
- 紹介実績数（XX名以上）
- 利用者満足度（XX%）
- 平均年収アップ額（+XX万円）
- 提携医療機関数（XX施設）

### 5.4 提携医療機関ロゴ表示

将来的に病院側の許可が得られたら、提携先ロゴをスクロール表示:

```html
<div class="partner-logos">
  <p class="partner-label">提携医療機関</p>
  <div class="logo-scroll">
    <!-- 匿名表示でも「提携XX施設」のような数値表示が有効 -->
    <span class="partner-count">神奈川県西部を中心に厳選された医療機関と提携</span>
  </div>
</div>
```

---

## 6. リマーケティング＆ナーチャリング

### 6.1 LINE公式アカウント統合

#### 戦略

看護師の日常コミュニケーションツールであるLINEを最重要チャネルとして位置づける。

#### 統合ポイント

**1. 友だち追加ボタン設置**

```html
<!-- フォーム横に配置 -->
<div class="line-cta">
  <p>LINEでも相談できます</p>
  <a href="https://lin.ee/XXXXXXX" class="line-btn" target="_blank" rel="noopener">
    <img src="assets/line-icon.svg" alt="LINE" width="24" height="24">
    LINEで無料相談
  </a>
  <small>友だち追加後、メッセージをお送りください</small>
</div>
```

**配置場所:**
- フォームセクション内（フォームの横 or 上部に選択肢として）
- スティッキーCTAバー（モバイル）
- 離脱ポップアップ内
- サンクスページ（登録後のLINE追加促進）

**2. LINE公式アカウント運用計画**

| 配信タイプ | 内容 | 頻度 |
|-----------|------|------|
| ウェルカムメッセージ | 友だち追加直後の自己紹介+相談促進 | 追加時1回 |
| 新着求人通知 | 新しい求人情報のお知らせ | 週1回 |
| 転職コラム | 面接対策、給与交渉のコツなど | 月2回 |
| 季節メッセージ | 転職シーズンの啓蒙（4月入職向けは12-1月） | 季節 |

**3. リッチメニュー設計**

```
┌─────────────┬─────────────┐
│  求人を見る  │  AIに相談   │
├─────────────┼─────────────┤
│  転職コラム  │  電話相談   │
└─────────────┴─────────────┘
```

### 6.2 メールキャプチャ戦略

**メインフォームのメールアドレス活用:**

フォーム送信後のフォローメールフロー:

```
[登録直後] → 登録確認メール + 転職ガイドPDF添付
[1日後]   → エージェント紹介メール + 相談予約リンク
[3日後]   → 類似求人レコメンドメール
[7日後]   → 転職活動アドバイスメール
[14日後]  → チェックイン（状況確認）メール
[30日後]  → 再アプローチ（未進行の場合）
```

**簡易メールキャプチャ（フォーム未送信者向け）:**

離脱ポップアップのサブオプションとして:
```
「まだ転職は先かも...」という方へ
メールアドレスだけ登録で、神奈川県の最新求人情報をお届けします。

[メールアドレス入力] [登録する]
※ 週1回以下の配信。いつでも解除可能。
```

### 6.3 リターゲティングピクセル設定

#### Google広告タグ

```html
<!-- Google Ads Remarketing Tag -->
<script async src="https://www.googletagmanager.com/gtag/js?id=AW-XXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'AW-XXXXXXXXX');
</script>
```

**リマーケティングリスト:**

| リスト名 | 条件 | 有効期間 | 用途 |
|---------|------|---------|------|
| 全訪問者 | LP訪問 | 30日 | 一般リマケ |
| フォーム開始未完了 | form_start発火 & form_submit未発火 | 14日 | 高意向リマケ |
| チャット開始未完了 | chat_open発火 & chat_complete未発火 | 14日 | 高意向リマケ |
| 求人セクション閲覧 | section_view(hospitals) | 30日 | 求人訴求リマケ |
| コンバージョン済み | form_submit or chat_complete | 180日 | 除外リスト |

#### LINE Tag

```html
<!-- LINE Tag -->
<script>
  (function(g,d,o){
    g._ltq=g._ltq||[];g._lt=g._lt||function(){g._ltq.push(arguments)};
    var h=d.getElementsByTagName(o)[0];
    var s=d.createElement(o);s.async=1;
    s.src='https://s.yjtag.jp/tag.js#site=XXXXXXXX';
    h.parentNode.insertBefore(s,h);
  })(window,document,'script');
  _lt('init', { customerType: 'account', tagId: 'XXXXXXXX' });
  _lt('send', 'pv', ['XXXXXXXX']);
</script>
```

#### Meta (Facebook/Instagram) Pixel

```html
<!-- Meta Pixel -->
<script>
  !function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?
  n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;
  n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;
  t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}(window,
  document,'script','https://connect.facebook.net/en_US/fbevents.js');
  fbq('init', 'XXXXXXXXXXXXXXX');
  fbq('track', 'PageView');
</script>
```

**コンバージョンイベント送信:**
```javascript
// フォーム送信時
fbq('track', 'Lead', { content_name: 'nurse_registration' });
_lt('send', 'cv', { type: 'Signup' });
gtag('event', 'conversion', { 'send_to': 'AW-XXXXXXXXX/YYYYYY' });

// チャット完了時
fbq('track', 'CompleteRegistration', { content_name: 'chat_complete' });
_lt('send', 'cv', { type: 'Registration' });
```

---

## 7. 広告プラットフォーム対応

### 7.1 Google広告 ランディングページ要件

#### チェックリスト

| 要件 | 現状 | 対応 |
|------|------|------|
| モバイルフレンドリー | OK | responsive design実装済み |
| HTTPS | 要確認 | ドメイン設定時にSSL必須 |
| ページ速度 | 要改善 | パーティクル最適化 + minify |
| 明確なCTA | OK | 「無料で相談する」 |
| 事業者情報 | OK | フッターに記載 |
| プライバシーポリシー | OK | リンク設置済み |
| 利用規約 | OK | リンク設置済み |
| 有料職業紹介許可番号 | 未取得 | 取得次第掲載 |
| ナビゲーション | OK | ヘッダーメニュー |
| 広告と一致するコンテンツ | - | 広告文作成時に合わせる |

#### Google広告テキスト案

**検索広告（レスポンシブ）:**

見出し（15個）:
1. 看護師転職 手数料10%
2. 神奈川県の看護師求人
3. AI×エージェントの転職支援
4. 24時間AI相談無料
5. 入職後50%返金保証
6. 小田原市の看護師転職
7. 月給28〜40万円の求人
8. 転職するか迷っている方へ
9. 3分で無料登録
10. 夜勤明けでも相談OK
11. 手数料が安いから待遇UP
12. 看護師の転職をフェアに
13. 神奈川県西部に特化
14. 訪問看護の求人あり
15. 年間休日110日以上の求人

説明文（4個）:
1. 看護師転職の手数料を業界最低水準の10%に。浮いた費用があなたの待遇改善に還元されます。3分で無料登録。
2. AIが24時間あなたの希望を丁寧にヒアリング。専門エージェントが最適な職場をご提案します。情報収集だけでもOK。
3. 神奈川県西部（小田原・南足柄・足柄上郡）の厳選された医療機関と提携。月給28〜40万円、年間休日110日以上の求人多数。
4. 入職後3ヶ月以内の退職は手数料50%返金保証。「合わなかったらどうしよう」という不安を解消します。

#### キーワード構成

| キャンペーン | 広告グループ | キーワード例 |
|------------|------------|------------|
| ブランド | ブランド名 | robby the match, ロビーザマッチ |
| 地域×職種 | 神奈川看護師 | 看護師 転職 神奈川, 看護師 求人 小田原 |
| 地域×職種 | 訪問看護 | 訪問看護 求人 神奈川, 訪問看護師 転職 |
| 条件×職種 | 手数料安い | 看護師 転職 手数料 安い, 紹介手数料 安い 看護師 |
| 行動×職種 | 転職相談 | 看護師 転職 相談 無料, 看護師 転職 AI |

### 7.2 LINE広告対応

#### LP要件

- **ページ読み込み速度:** 3秒以内（LINE広告の品質スコアに影響）
- **LINEログイン連携:** 将来的に検討（友だち追加からのCV導線）
- **電話番号タップ対応:** `tel:` リンク設置

#### LINE広告クリエイティブ方針

**ターゲティング:**
- 年齢: 25-50歳
- 性別: 女性（看護師の約93%が女性）
- 地域: 神奈川県
- 興味関心: 医療・看護、転職

**クリエイティブパターン:**

1. **問題提起型:** 「今の給料に不満はありませんか？手数料10%だから、あなたの給与が変わります」
2. **数字訴求型:** 「看護師転職の手数料、10%で十分です。浮いた費用 = あなたの年収UP」
3. **共感型:** 「夜勤明けでも大丈夫。AIが24時間、あなたの転職相談に乗ります」
4. **地域特化型:** 「神奈川県西部の看護師さんへ。月給28〜40万円の厳選求人」

### 7.3 Indeed / 看護師専門求人サイト連携

#### Indeed対応

- 求人情報をIndeedに掲載するためのXMLフィード生成
- 将来的に `/jobs/` 配下に個別求人ページを作成
- Indeed応募ボタンからLPのフォームへ遷移

#### 看護師専門サイト連携

| サイト | 連携方法 | 優先度 |
|--------|---------|--------|
| ナースではたらこ | 求人掲載依頼 | A |
| マイナビ看護師 | 広告掲載 | B |
| 看護roo! | 記事タイアップ | B |
| ジョブメドレー | 求人掲載 | A |

---

## 8. A/Bテストフレームワーク

### 8.1 テスト対象要素

#### 優先度S（最初にテスト）

| テスト名 | 要素 | バリアントA（現行） | バリアントB |
|---------|------|-------------------|------------|
| hero_cta_text | ヒーローCTAテキスト | 「無料で相談する」 | 「3分で転職相談を始める」 |
| hero_subtitle | ヒーローサブタイトル | 手数料訴求 | 給与アップ訴求 |
| form_type | フォーム形式 | 一括表示 | ステップフォーム |
| chat_trigger | チャットの初期表示 | ボタンのみ | 3秒後に自動ポップアップ |

#### 優先度A

| テスト名 | 要素 | バリアントA | バリアントB |
|---------|------|-----------|------------|
| social_proof | 口コミセクション | なし | あり |
| trust_badges | 信頼バッジ | なし | ヒーロー下に表示 |
| sticky_cta | モバイルスティッキーCTA | なし | あり |
| exit_popup | 離脱ポップアップ | なし | あり |

#### 優先度B

| テスト名 | 要素 | バリアントA | バリアントB |
|---------|------|-----------|------------|
| color_accent | CTAボタン色 | グラデーション（現行） | 単色オレンジ |
| mission_position | ミッションセクション位置 | 流れの後 | 特長の後 |
| form_reassurance | フォームマイクロコピー | なし | 安心メッセージ表示 |

### 8.2 A/Bテスト実装（vanilla JS）

```javascript
// ab-test.js - 軽量A/Bテストフレームワーク（外部依存なし）

var ABTest = (function() {
  'use strict';

  var STORAGE_KEY = 'rtm_ab_variants';

  // 保存済みバリアントを取得
  function getStoredVariants() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {};
    } catch(e) {
      return {};
    }
  }

  // バリアントを保存
  function storeVariants(variants) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(variants));
    } catch(e) {}
  }

  // バリアント割り当て（50/50）
  function assignVariant(testName) {
    var stored = getStoredVariants();
    if (stored[testName]) return stored[testName];

    var variant = Math.random() < 0.5 ? 'A' : 'B';
    stored[testName] = variant;
    storeVariants(stored);

    // GA4にバリアント送信
    if (typeof gtag === 'function') {
      gtag('event', 'ab_test_assignment', {
        test_name: testName,
        variant: variant
      });
    }

    return variant;
  }

  // テスト実行
  function run(testName, callbacks) {
    var variant = assignVariant(testName);
    if (callbacks[variant]) {
      callbacks[variant]();
    }
    return variant;
  }

  return { run: run, assignVariant: assignVariant };
})();

// === テスト実行例 ===

// ヒーローCTAテキストテスト
ABTest.run('hero_cta_text', {
  A: function() { /* 現行のまま */ },
  B: function() {
    var cta = document.querySelector('.hero-cta');
    if (cta) cta.textContent = '3分で転職相談を始める';
  }
});

// チャット自動ポップアップテスト
ABTest.run('chat_trigger', {
  A: function() { /* 現行のまま（ボタンのみ） */ },
  B: function() {
    setTimeout(function() {
      var toggle = document.getElementById('chatToggle');
      if (toggle) {
        // ツールチップ表示
        var tip = document.createElement('div');
        tip.className = 'chat-tooltip';
        tip.textContent = '転職の悩み、AIが24時間お答えします';
        toggle.parentNode.appendChild(tip);
        setTimeout(function() { tip.classList.add('visible'); }, 100);
        setTimeout(function() { tip.classList.remove('visible'); }, 8000);
      }
    }, 5000);
  }
});
```

### 8.3 テスト評価基準

| KPI | 計測方法 | 統計的有意性基準 |
|-----|---------|----------------|
| CVR（フォーム送信） | form_submit / セッション数 | p < 0.05, サンプル500以上 |
| チャット開始率 | chat_consent / セッション数 | p < 0.05, サンプル500以上 |
| チャット完了率 | chat_complete / chat_consent | p < 0.05, サンプル200以上 |
| 直帰率 | GA4標準 | 参考指標 |
| 滞在時間 | GA4標準 | 参考指標 |

---

## 9. 実装ロードマップ

### Phase 1: 基盤整備（1-2週間）

| タスク | 優先度 | 工数 |
|--------|--------|------|
| GA4 タグ設置 + 基本イベント実装 | 最高 | 2-3時間 |
| 構造化データ（JSON-LD）4種追加 | 最高 | 1-2時間 |
| メタタグ最適化（title, description, canonical） | 最高 | 30分 |
| OGP修正（og:url追加） | 高 | 15分 |
| CSS/JS minify設定 | 高 | 1時間 |
| ローディングスクリーン短縮 | 高 | 15分 |
| sitemap.xml 作成 | 高 | 30分 |
| robots.txt 作成 | 高 | 15分 |

### Phase 2: コンバージョン最適化（2-3週間）

| タスク | 優先度 | 工数 |
|--------|--------|------|
| モバイルスティッキーCTAバー実装 | 最高 | 2-3時間 |
| フォームマイクロコピー追加 | 高 | 1時間 |
| CTA文言改善（ミッションセクション他） | 高 | 30分 |
| AIチャットボタンのラベル・ツールチップ追加 | 高 | 1-2時間 |
| 信頼バッジ（ヒーロー下+フォーム上） | 高 | 1-2時間 |
| 実績数値セクション追加 | 中 | 2時間 |
| 離脱防止ポップアップ実装 | 中 | 3-4時間 |
| ステップフォーム化 | 中 | 4-6時間 |

### Phase 3: リマーケティング＆広告（3-4週間）

| タスク | 優先度 | 工数 |
|--------|--------|------|
| Google広告タグ設置 + コンバージョン設定 | 最高 | 1-2時間 |
| LINE Tag設置 | 高 | 1時間 |
| Meta Pixel設置 | 中 | 1時間 |
| LINE公式アカウント開設 + LP統合 | 高 | 3-4時間 |
| Google広告キャンペーン構築 | 高 | 1-2日 |
| LINE広告クリエイティブ制作 | 中 | 1-2日 |
| UTMパラメータ運用ルール策定 | 中 | 1時間 |

### Phase 4: A/Bテスト＆改善サイクル（継続）

| タスク | 優先度 | 工数 |
|--------|--------|------|
| A/Bテストフレームワーク実装 | 高 | 2-3時間 |
| テスト1: ヒーローCTA文言 | 最高 | 実行2週間 |
| テスト2: フォーム形式（一括 vs ステップ） | 最高 | 実行2週間 |
| テスト3: チャット自動ポップアップ | 高 | 実行2週間 |
| テスト4: 口コミセクション有無 | 高 | 実行2週間 |
| 月次レポート作成・改善提案 | 中 | 毎月 |

### Phase 5: コンテンツ拡張（長期）

| タスク | 優先度 | 工数 |
|--------|--------|------|
| FAQセクション実装（LP内） | 高 | 2-3時間 |
| ブログ/コラムページ設計 | 中 | 1-2日 |
| 記事制作（月2-4記事） | 中 | 継続 |
| 個別求人ページテンプレート | 低 | 1日 |
| 地域別ランディングページ | 低 | 1日/ページ |

---

## 付録: KPIダッシュボード設計

### 週次モニタリング指標

| カテゴリ | 指標 | 目標値 |
|---------|------|--------|
| トラフィック | セッション数 | 週500以上 |
| トラフィック | 新規ユーザー率 | 80%以上 |
| トラフィック | 直帰率 | 50%以下 |
| エンゲージメント | 平均滞在時間 | 2分以上 |
| エンゲージメント | スクロール75%到達率 | 40%以上 |
| コンバージョン | フォーム送信率 | 3%以上 |
| コンバージョン | チャット開始率 | 8%以上 |
| コンバージョン | チャット完了率 | 50%以上（開始者ベース） |
| 広告 | CPA（フォーム送信） | 15,000円以下 |
| 広告 | ROAS | 計測・改善 |

---

**本計画書は、サイトの成長フェーズに応じて継続的に更新すること。**

**作成: マーケティング計画AI**
**最終更新: 2026年2月16日**
