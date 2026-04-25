---
paths:
  - "**/*.html"
  - "lp/**/*.html"
  - "blog/**/*.html"
---
# HTML Pages Rules

- IMPORTANT: 「平島禎之」「はるひメディカルサービス」をHTMLに書くな（privacy.html/terms.html/proposal.htmlのみ例外）
- 全ページにMeta Pixel（ID: 2326210157891886）を含めること
- LINE CTAリンクは `https://lin.ee/oUgDB3x` を使え
- マーケティング戦略コメント（損失回避、アンカリング、フレーミング等）をHTMLに書くな
- モバイルファースト: FVにCTAが収まるか常に意識

## ブランド使い分け（2026-04-03 リブランド決定 / 2026-04-26 全国対応で更新）

### LP・トップ・404・サポートページ（顧客接点）
- 著者名: 「ナースロビー編集部」
- JSON-LD Organization.name: 「ナースロビー」 / alternateName: 「神奈川ナース転職」（旧ブランドのSEO捕捉）
- フッター: `© 2026 ナースロビー All Rights Reserved.`
- 対象ファイル: `lp/job-seeker/index.html`, `404.html`, `index.html` 等

### SEOページ（地域ロングテール武器、触るな）
- 著者名: 「神奈川ナース転職編集部」維持
- JSON-LD Organization.name: 「神奈川ナース転職」維持
- フッター: `© 2026 神奈川ナース転職 All Rights Reserved.` 維持
- 対象ファイル: `lp/job-seeker/area/`, `lp/job-seeker/guide/`, `lp/job-seeker/hospitals/`, `blog/` 配下305ページ

### 法務文書（併記OK）
- 「神奈川ナース転職／ナースロビー」併記が安全
- 対象ファイル: `privacy.html`, `terms.html`, `proposal.html`
