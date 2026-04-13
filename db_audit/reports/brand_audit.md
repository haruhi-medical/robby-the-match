# ブランド整合性監査レポート

**監査日**: 2026-04-06
**基準ページ**: `/lp/job-seeker/index.html`（LP-A）

---

## 1. トップページ（LP-A）のブランド基準

| 要素 | 基準値 |
|------|--------|
| サービス名 | **ナースロビー** |
| ロゴ画像 | `../../assets/logo-nursrobby.png`（`<img>` タグ使用） |
| ロゴ alt | `ナースロビー` |
| ブランドカラー（primary） | `--primary: #1a9de0`（青系） |
| ブランドカラー（accent） | `--accent: #50c8a0`（緑系） |
| フッター著作権 | `(C) 2026 ナースロビー All Rights Reserved.` |
| フッターロゴ | `logo-nursrobby.png`（height:72px） |
| OGP画像 | `https://quads-nurse.com/assets/ogp.png` |
| og:site_name | `ナースロビー` |
| favicon | `/favicon.ico` + `/assets/favicon-32x32.png` + `16x16` |
| apple-touch-icon | `/assets/apple-touch-icon.png` |
| Meta Pixel | 2326210157891886 あり |
| GA4 | G-X4G2BYW13B あり |
| JSON-LD Organization.name | `ナースロビー` |
| フォント | Noto Sans JP |

---

## 2. 各ページの現状と差異

### 2.1 index.html（ルート / リダイレクトページ）
- **サービス名**: `ナースロビー` -- OK
- **ロゴ**: なし（リダイレクト専用ページなので問題なし）
- **カラー**: リンク色 `#1a7f64`（旧テーマの緑） -- **不一致**
- **フッター**: なし（リダイレクトのみ）
- **OGP**: なし
- **favicon**: なし
- **Meta Pixel / GA4**: なし
- **影響度**: 低（即リダイレクトなのでユーザーは見ない）

### 2.2 privacy.html
- **サービス名**: `神奈川ナース転職` -- **不一致**（ただしSEOページは「神奈川ナース転職」維持が方針）
- **ロゴ**: テキストロゴ `神奈川<span class="logo-accent">ナース転職</span>` -- **画像ロゴなし**
- **カラー**: CSS変数未使用。ハードコードカラーだが具体的な色記載なし
- **フッター**: `(C) 2026 神奈川ナース転職 All Rights Reserved.` -- **不一致**
- **og:site_name**: `神奈川ナース転職` -- **不一致**
- **OGP画像**: `assets/ogp.png` -- OK
- **favicon**: **なし** -- 要修正
- **apple-touch-icon**: **なし** -- 要修正
- **Meta Pixel / GA4**: あり -- OK

### 2.3 terms.html
- **サービス名**: `神奈川ナース転職` -- **不一致**
- **ロゴ**: テキストロゴ `神奈川<span class="logo-accent">ナース転職</span>` -- **画像ロゴなし**
- **カラー**: CSS変数未使用
- **フッター**: `(C) 2026 神奈川ナース転職 All Rights Reserved.` -- **不一致**
- **og:site_name**: `神奈川ナース転職` -- **不一致**
- **OGP画像**: `assets/ogp.png` -- OK
- **favicon**: **なし** -- 要修正
- **apple-touch-icon**: **なし** -- 要修正
- **Meta Pixel / GA4**: あり -- OK

### 2.4 about.html
- **サービス名**: `ナースロビー` -- OK
- **ロゴ**: テキストロゴ `神奈川<span class="logo-accent">ナース転職</span>` -- **不一致**（テキストは旧ブランド名）
- **カラー**: CSS変数未使用。LINE CTA `#06C755` のみ
- **フッター**: `(C) 2026 ナースロビー All Rights Reserved.` -- OK
- **og:site_name**: `ナースロビー` -- OK
- **OGP画像**: `assets/ogp.png` -- OK
- **favicon**: **なし** -- 要修正
- **apple-touch-icon**: **なし** -- 要修正
- **Meta Pixel**: **なし** -- 要修正
- **GA4**: あり -- OK
- **JSON-LD Organization.name**: `ナースロビー` -- OK

### 2.5 lp/ad/index.html（広告LP）
- **サービス名**: `ナースロビー` -- OK
- **ロゴ**: **ヘッダーにロゴ要素なし** -- 要修正（header自体がない広告LP形式）
- **カラー**: `--primary: #4DA0CC` / `--accent: #EF8B7F` -- **不一致**（LP-Aは `#1a9de0` / `#50c8a0`）
- **フッター**: `(C) 2026 ナースロビー All Rights Reserved.` -- OK
- **og:site_name**: `ナースロビー` -- OK
- **OGP画像**: `assets/ogp.png` -- OK
- **favicon**: あり -- OK
- **apple-touch-icon**: あり -- OK
- **Meta Pixel / GA4**: Pixel あり、GA4の有無は要確認（ファイル内検索では189 files match）

### 2.6 salary-check/index.html
- **サービス名**: `ナースロビー` -- OK
- **ロゴ**: **ヘッダーにロゴ画像なし**（ページ構造的にヘッダーがない可能性）
- **カラー**: `--primary: #3D8FBF` / `--accent: #E8756A` -- **不一致**（LP-Aは `#1a9de0` / `#50c8a0`）
- **フッター**: `(C) 2026 ナースロビー All Rights Reserved.` -- OK
- **og:site_name**: `ナースロビー` -- OK
- **OGP画像**: `assets/ogp.png` -- OK
- **favicon**: あり -- OK
- **apple-touch-icon**: あり -- OK
- **Meta Pixel / GA4**: あり -- OK

### 2.7 area/（地域SEOページ x 22）-- サンプル: yokohama.html, fujisawa.html
- **サービス名**: `神奈川ナース転職` -- **不一致**（ただしSEOページは「神奈川ナース転職」維持が方針として正しい）
- **ロゴ**: テキスト `神奈川ナース転職<span class="header-tagline">シン・AI転職</span>` -- **画像ロゴなし**
- **カラー**: CSS変数未使用（インラインスタイル中心）
- **フッター**: `(C) 2026 神奈川ナース転職 All Rights Reserved.` -- **SEO方針上は正しい**
- **og:site_name**: `神奈川ナース転職` -- SEO方針上は正しい
- **OGP画像**: `assets/ogp.png` -- OK
- **favicon**: あり -- OK
- **apple-touch-icon**: あり -- OK
- **Meta Pixel / GA4**: あり -- OK

### 2.8 guide/（転職ガイドSEOページ x 44）-- サンプル: first-transfer.html, career-change.html
- area/ と同じパターン -- SEOページとして「神奈川ナース転職」は方針上正しい
- **favicon / apple-touch-icon**: あり -- OK
- **Meta Pixel / GA4**: あり -- OK

### 2.9 blog/index.html + blog記事（x 19）
- **サービス名**: `神奈川ナース転職` -- SEOページ方針上は正しい
- **ロゴ**: テキストのみ（色 `#1a7f64`） -- **画像ロゴなし、色も旧テーマ**
- **カラー**: ハードコード `#1a7f64`（暗い緑） -- **LP-Aの `#1a9de0`（青）と完全に異なる**
- **フッター**: `(C) 2026 神奈川ナース転職 All Rights Reserved.` -- SEO方針上は正しい
- **og:site_name**: `神奈川ナース転職` -- SEO方針上は正しい
- **OGP画像**: `assets/ogp.png` -- OK
- **favicon**: blog/index.html は **なし** / 個別記事は あり -- **blog/index.htmlのみ要修正**
- **Meta Pixel / GA4**: あり -- OK
- **フォント**: システムフォント（-apple-system等） -- **LP-AはNoto Sans JP**

---

## 3. 修正が必要なファイルと修正箇所

### 優先度: 高（ブランド表示の直接的不整合）

| # | ファイル | 修正箇所 | 詳細 |
|---|---------|---------|------|
| 1 | `about.html` | ヘッダーロゴ | テキスト「神奈川ナース転職」→ 画像ロゴ `logo-nursrobby.png` + alt「ナースロビー」に変更 |
| 2 | `about.html` | favicon / apple-touch-icon | 追加が必要 |
| 3 | `about.html` | Meta Pixel | 追加が必要 |
| 4 | `lp/ad/index.html` | ブランドカラー | `--primary: #4DA0CC` → `#1a9de0` / `--accent: #EF8B7F` → `#50c8a0` |
| 5 | `salary-check/index.html` | ブランドカラー | `--primary: #3D8FBF` → `#1a9de0` / `--accent: #E8756A` → `#50c8a0` |
| 6 | `privacy.html` | favicon / apple-touch-icon | 追加が必要 |
| 7 | `terms.html` | favicon / apple-touch-icon | 追加が必要 |
| 8 | `blog/index.html` | favicon / apple-touch-icon | 追加が必要 |

### 優先度: 中（色味の統一）

| # | ファイル | 修正箇所 | 詳細 |
|---|---------|---------|------|
| 9 | `blog/index.html` | テーマカラー | `#1a7f64`（旧緑）が多用されている → LP-Aの青系 `#1a9de0` に統一すべき |
| 10 | `blog/*.html`（18記事） | テーマカラー | 記事ページも `#1a7f64` 使用 → 統一検討 |
| 11 | `blog/index.html` + 記事 | フォント | システムフォント → Noto Sans JP に統一検討 |

### 優先度: 低（方針上許容だが注意）

| # | ファイル群 | 状況 | 備考 |
|---|----------|------|------|
| 12 | `privacy.html` / `terms.html` | サービス名「神奈川ナース転職」/ フッター同 | noindex,nofollowページ。法的ページなので現状維持で問題なし |
| 13 | `area/`（22ページ）/ `guide/`（44ページ） | サービス名「神奈川ナース転職」 | MEMORY.md方針「SEOページは神奈川ナース転職維持」に準拠。問題なし |
| 14 | `area/` / `guide/` | テキストロゴ（画像ロゴなし） | SEOページは軽量テキストロゴで統一されており、整合はある |
| 15 | `index.html`（ルート） | リンク色 `#1a7f64` | 即リダイレクトなので実害なし |

---

## 4. 影響範囲サマリ

| 修正レベル | ファイル数 | 内訳 |
|-----------|----------|------|
| 高（必須修正） | **5ファイル** | about.html, lp/ad/index.html, salary-check/index.html, privacy.html, terms.html |
| 中（統一推奨） | **20ファイル** | blog/index.html + blog記事18件 + blog/index.html（favicon） |
| 低（現状維持可） | **67ファイル** | area/22 + guide/44 + index.html |
| 問題なし | **1ファイル** | lp/job-seeker/index.html（基準） |

**合計修正推奨: 25ファイル**（高5 + 中20）

---

## 5. 主な不整合パターンまとめ

1. **ブランドカラーが3系統存在**: LP-A青(`#1a9de0`), 広告LP/給与診断の別青(`#4DA0CC`/`#3D8FBF`), blog旧緑(`#1a7f64`)
2. **ロゴが画像なのはLP-Aのみ**: 他全ページはテキストロゴ（しかも一部は旧名「神奈川ナース転職」）
3. **favicon/apple-touch-icon欠落**: privacy, terms, about, blog/index の4ファイル
4. **Meta Pixel欠落**: about.html の1ファイル
5. **フォント不統一**: LP-AはNoto Sans JP、blogはシステムフォント
