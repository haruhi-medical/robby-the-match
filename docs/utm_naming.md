# UTM命名規則 — 神奈川ナース転職

> v1.0 / 2026-04-17 策定
> Phase 1 #21 (M-06 UTM命名規則＋click_cta GA4イベント) 実装ドキュメント
> 参照: `docs/audit/2026-04-17/supervisors/strategy_review.md`

## 目的

- Meta広告/TikTok/Instagram/SEO/LINE 等の流入チャネル別貢献度を GA4 上で分解可能にする
- `click_cta` イベント + UTMパラメータのセットで **チャネル → LP → LINE** のファネルを一本で追跡
- 架空の集計単位を作らず、既存の GA4 標準ディメンション (source/medium/campaign/content) に合わせる

## 基本仕様

すべての外部流入（広告・SNSプロフィールリンク・メール・コラボ）の URL に以下を付与する。

| パラメータ | 必須 | 値の型 | 書式 | 例 |
|-----------|------|--------|------|-----|
| `utm_source` | ✅ | 固定辞書 | snake_case 英数字 | `meta_ad` |
| `utm_medium` | ✅ | 固定辞書 | snake_case 英数字 | `cpc` |
| `utm_campaign` | ✅ | 可変 | `{商材}_{地域}_{年}_{月}` 形式 | `nurse_kanagawa_2026_04` |
| `utm_content` | 推奨 | 固定辞書 | snake_case 英数字 | `hero_cta` |
| `utm_term` | 任意 | 自由文 | 空白なし・英数字+hyphen | `night_shift_off` |

### utm_source（流入元サービス）— 固定辞書

| 値 | 用途 |
|----|------|
| `meta_ad` | Meta広告（Facebook / Instagram広告配信） |
| `tiktok` | TikTok (オーガニック投稿・プロフィール・動画内) |
| `instagram` | Instagram (オーガニック・プロフィールリンク・ストーリー) |
| `google_search` | Google自然検索（SCから手動付与する場合） |
| `direct` | 直接訪問（ノーリファラ扱い・通常は付けない） |
| `line` | LINE公式アカウントからの外部リンク |
| `youtube` | YouTube (動画説明欄・プロフィール) |
| `blog_internal` | 自サイトblog/内部記事から他ページへの誘導測定 |
| `partner` | 将来の提携先（現時点では未使用） |

⚠️ 既存の値を変更する場合は GA4 のセグメント定義も同時に更新する。

### utm_medium（媒体種別）— 固定辞書

| 値 | 用途 |
|----|------|
| `cpc` | クリック課金広告（Meta広告リード目的含む） |
| `organic` | オーガニック投稿（SEO/TikTok/IG/YT自然流入） |
| `social` | SNSプロフィール欄・固定投稿リンク（広告ではない） |
| `referral` | 他サイト・ブログ等からの被リンク |
| `direct` | 直接訪問（付与不要） |
| `email` | 将来のメルマガ（現時点で未使用） |
| `push` | LINEのpushメッセージ内リンク |

### utm_campaign（キャンペーン）

- 書式: `{商材}_{地域}_{年}_{月}` をベースとする
- 例:
  - `nurse_kanagawa_2026_04` — 神奈川向け通常配信（2026年4月）
  - `nurse_kanagawa_2026_04_night_shift` — 「夜勤なし」角度のサブキャンペーン
  - `nurse_tokyo_2026_05_sagyoryo` — 将来の東京拡大時
- 月をまたぐキャンペーンは `_2026_0405` 等の合成ではなく、月別に別キャンペーンで採番する（計測単位を揃えるため）

### utm_content（配信面・クリエイティブ区分）— 固定辞書

LP 内での CTA 位置区分、広告内でのクリエイティブ区分を統一する。

#### LP内CTA（GA4 `click_cta` イベントの `source` と同期）

| 値 | 対応HTML | 説明 |
|----|---------|------|
| `hero_cta` | `.cta-line-hero` | FV 直下の最初のLINE CTA |
| `sticky_cta` | `.mobile-sticky-line` | モバイル底固定CTA |
| `bottom_cta` | `.final-cta .cta-line` | 最下部 Final CTA |
| `shindan_complete` | `shindan.js` CTA | 診断完了時のLINE引き継ぎCTA |
| `chat_widget` | `chat.js` CTA | チャットウィジェットからのLINE誘導（将来） |

#### 広告クリエイティブ（Meta Ads v7）

| 値 | 説明 |
|----|------|
| `video_01` | 動画クリエイティブ v7-1 |
| `image_01` | 静止画クリエイティブ v7-2 |
| `image_02` | 静止画クリエイティブ v7-3 |

配信面別の詳細は Meta 広告の配置レポートで取得するため `utm_content` には含めない。

## 既存の実装との整合

### analytics.js (lp/analytics.js)

- `parseUTMParams()` が `utm_source` / `utm_medium` / `utm_campaign` / `utm_term` / `utm_content` を sessionStorage (`robby_utm`) に保存
- LP内の LINE CTA クリック時に `gtag('event', 'click_cta', {...})` を発火。この時 `source` / `intent` / `page_type` / `session_id` / `utm_*` を同時に送る
- `detectLineSource()` が class 名から `hero_cta` / `mobile_sticky` / `bottom_cta` / `cta_line` を判定
  - 本命名規則との差分: `mobile_sticky` → utm_content 上は `sticky_cta` に揃えるのが望ましいが、既存 GA4 に履歴が残っているため破壊的変更はしない。レポート側で同一カテゴリとして扱う

### shindan.js (lp/job-seeker/shindan.js)

- 診断完了時の CTA クリックで `ga('click_cta', { source:'shindan', intent:'diagnose', ... })` 発火
- `utm_content=shindan_complete` と揃えるためには広告側の URL で `utm_content=shindan_complete` を付けるのはやめ、診断完了経由はイベント `source` で識別する運用とする

### Meta Pixel

- LP内 LINE CTA クリックで `fbq('track', 'Lead', {content_name, content_category})` をインライン発火（index.html:1985付近）
- Meta側のイベント名 `Lead` と GA4 `click_cta` を別系統として扱う（両方を補完的に観測）

## サンプル URL

```
# Meta広告（動画1・4月）
https://quads-nurse.com/lp/job-seeker/
  ?utm_source=meta_ad
  &utm_medium=cpc
  &utm_campaign=nurse_kanagawa_2026_04
  &utm_content=video_01

# TikTokプロフィールリンク
https://quads-nurse.com/lp/job-seeker/
  ?utm_source=tiktok
  &utm_medium=social
  &utm_campaign=nurse_kanagawa_2026_04
  &utm_content=bio_link

# LINE Pushメッセージ内リンク
https://quads-nurse.com/blog/kanagawa-nurse-salary.html
  ?utm_source=line
  &utm_medium=push
  &utm_campaign=nurse_kanagawa_2026_04
  &utm_content=blog_salary
```

## 運用ルール

1. **広告の新規URL作成時は必ず本ドキュメントの固定辞書から値を選ぶ**。新しい値を追加したい場合は本ドキュメントを更新してから使う
2. **Meta広告管理画面のURLパラメータ機能を使う**。手書きでクエリを組まない
3. **短縮URL (lin.ee / bit.ly) を挟む場合は、リダイレクト先の URL に UTM を含める**
4. **sessionStorage (`robby_utm`) は広告LP → 診断 → LINEまで引き継がれる**。worker.js 側での UTM 連携も将来実装予定（現時点は GA4 のみ）
5. **Phase 2 以降: `utm_source=meta_ad` の CPA を GA4 の `click_cta` 合計から逆算 → CAPI実装と突合**

## click_cta イベントの GA4 設定

GA4 管理画面で以下を実施する想定（手動作業・社長判断）:

- [ ] `click_cta` を「コンバージョン」としてマーク
- [ ] カスタムディメンション登録:
  - `source` (イベントスコープ)
  - `intent` (イベントスコープ)
  - `page_type` (イベントスコープ)
  - `session_id` (ユーザースコープ)
  - `utm_source` / `utm_medium` / `utm_campaign` (イベントスコープ)
- [ ] 目標到達プロセス: `page_view` → `click_cta` → (LINE 友だち追加) の3段で定義

## 変更履歴

| 日付 | 変更内容 |
|------|---------|
| 2026-04-17 | v1.0 初版（Phase 1 #21 M-06 として策定） |
