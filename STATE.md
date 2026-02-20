# ROBBY THE MATCH 状態ファイル
# 最終更新: 2026-02-20 11:45 by デプロイ完了

## 運用ルール
- 全PDCAサイクルはこのファイルを最初に読む（他を探し回るな）
- 作業完了後にこのファイルを更新する（次サイクルへ引き継ぎ）
- PROGRESS.mdには履歴として追記（こちらは状態のスナップショット）

## 現在のフェーズ
- マイルストーン: Week 1
- North Star: 看護師1名をA病院に紹介して成約
- 状態: 基盤構築完了、SEO+コンテンツ運用開始

## KPI
| 指標 | 目標 | 現在 | 更新日 |
|------|------|------|--------|
| SEO子ページ数 | 50 | 20（area/9 + guide/11） | 2026-02-20 |
| ブログ記事数 | 10 | 0 | 2026-02-20 |
| 投稿数(TikTok) | Week2:5 | 0 | 2026-02-20 |
| 投稿数(Instagram) | Week2:3 | 0 | 2026-02-20 |
| PV/日 | 100 | 0 | 2026-02-20 |
| LINE登録数 | Month2:5 | 0 | 2026-02-20 |
| 成約数 | Month3:1 | 0 | 2026-02-20 |
| SEO施策数 累計 | - | 19（index.html構造化データ5種 + LP-A構造化データ4種 + area子ページ9 + guide子ページ6 + sitemap.xml + robots.txt x2 + seo_strategy.md + analytics.js = 計29要素。ページ単位では: LP-A最適化1 + 子ページ15 + sitemap1 + robots2 = 19） | 2026-02-20 |

## ファイル構成
```
robby-the-match/
├── .env                          # 環境変数（git管理外）
├── .gitignore
├── 404.html
├── CLAUDE.md                     # 戦略プロンプト v8.0
├── PDCA_SETUP.md                 # PDCAシステム構築記録
├── PROGRESS.md                   # 日次進捗ログ
├── STATE.md                      # このファイル
├── index.html                    # メインLP（構造化データ5種）
├── privacy.html                  # プライバシーポリシー
├── terms.html                    # 利用規約
├── proposal.html / proposal.css  # 提案書ページ
├── dashboard.html / .css / .js   # ダッシュボード
├── chat.css / chat.js            # チャットUI
├── config.js                     # 設定
├── script.js / style.css         # メインJS/CSS
├── robots.txt                    # ルートrobots.txt
├── slack-bot.js / slack-notify.js # Slack連携
├── api/
│   ├── README.md
│   ├── worker.js                 # Cloudflare Worker
│   └── wrangler.toml
├── assets/
│   └── ogp.svg                   # OGP画像
├── content/
│   ├── base-images/              # ベース画像3枚（使い回し用）
│   │   ├── base_ai_chat.png
│   │   ├── base_breakroom.png
│   │   └── base_nurse_station.png
│   ├── generated/                # 生成済みコンテンツ（git管理外）
│   │   ├── 20260220_A01/        # スライド6枚
│   │   ├── 20260220_A02/        # スライド6枚
│   │   ├── test_overlay.png
│   │   ├── test_script_A01.json
│   │   ├── 20260220_A02.json
│   │   └── weekly_batch_20260220/ # 週次バッチ7日分
│   └── templates/
│       ├── prompt_template.md
│       └── weekly_batch.md
├── data/
│   ├── areas.js                  # 地域データ
│   └── jobs.js                   # 求人データ
├── docs/
│   ├── api_key_guide.md
│   ├── google_analytics_setup.md
│   ├── integration_plan.md
│   ├── seo_strategy.md
│   └── archive/                  # 統合済みアーカイブ（22ファイル）
│       ├── migration_log.md
│       └── （旧robby_content、Desktop/claude等から統合）
├── logs/                         # ログ（git管理外）
│   └── healthcheck_2026-02-20.log
├── lp/
│   ├── analytics.js
│   ├── robots.txt
│   ├── sitemap.xml               # 18 URLエントリ
│   └── job-seeker/
│       ├── index.html            # LP-A（構造化データ4種）
│       ├── area/                 # 地域別9ページ
│       │   ├── atsugi.html
│       │   ├── chigasaki.html
│       │   ├── ebina.html
│       │   ├── fujisawa.html
│       │   ├── hadano.html
│       │   ├── hiratsuka.html
│       │   ├── isehara.html
│       │   ├── minamiashigara.html
│       │   └── odawara.html
│       └── guide/                # ガイド6ページ
│           ├── career-change.html
│           ├── interview-tips.html
│           ├── night-shift.html
│           ├── salary-comparison.html
│           ├── transfer-fee.html
│           └── visiting-nurse.html
├── marketing/
│   ├── google-business.md
│   ├── indeed-nurse.md
│   ├── indeed-pt.md
│   └── sns-plan.md
├── reports/
│   ├── ai-architecture.md
│   ├── design-research.md
│   ├── marketing-plan.md
│   └── site-audit.md
└── scripts/
    ├── daily_pipeline.sh
    ├── generate_image_cloudflare.py
    ├── generate_image_imagen.py
    ├── generate_image.py
    ├── generate_slides.py
    ├── notify_slack.py
    ├── overlay_text.py
    ├── pdca_content.sh
    ├── pdca_healthcheck.sh
    ├── pdca_morning.sh
    ├── pdca_review.sh
    ├── pdca_weekly.sh
    ├── post_to_tiktok.py
    ├── slack_commander.py
    ├── slack_report.py
    ├── test_gemini_image_v2.py
    ├── test_gemini_image.py
    └── utils.sh
```

## デプロイ状態
- GitHub Pages: ✅ 公開中
- 公開URL: https://haruhi-medical.github.io/robby-the-match/
- git remote: origin https://github.com/haruhi-medical/robby-the-match.git
- デプロイブランチ: master（mainからforce push）
- 最新commit: d718482
- 最新commit: 8f42fa9 feat: 自律PDCAシステム構築完了

## SEO状態
- 子ページ: area/9ページ + guide/6ページ = 計15ページ
- sitemap.xml: 18 URLエントリ（lp/sitemap.xml）
- robots.txt: あり（ルート直下 + lp/ 配下に各1つ、計2つ）
- GA4: ✅ 設定済み（G-X4G2BYW13B、全27ファイル）
- Search Console: ✅ 登録済み（メタタグ検証、サイトマップ送信済み）
- Googleビジネスプロフィール: 未登録
- 構造化データ(JSON-LD):
  - index.html: WebSite, Organization, BreadcrumbList, EmploymentAgency, FAQPage（5種）
  - LP-A（job-seeker/index.html）: Organization, JobPosting, FAQPage, BreadcrumbList（4種）
  - area子ページ（9ページ）: 各BreadcrumbList + FAQPage（2種）
  - guide子ページ（6ページ）: 各BreadcrumbList + Article（2種）
- 競合ゼロKW: 「神奈川県西部 看護師」「紹介料 10%」

## SNS状態
- TikTokアカウント: 未確認
- Instagramアカウント: 未確認
- Postiz連携: 未設定（POSTIZ_API_KEY=空）
- 今週分素材: 7本生成済み（content/generated/weekly_batch_20260220/）

## Slack状態
- Bot Token: あり（.envにSLACK_BOT_TOKEN設定済み、xoxb-で始まるトークン）
- SLACK_CHANNEL_ID: あり（C08SKJBLW7A）
- slack_report.py: 作成済み（scripts/slack_report.py）
- slack_commander.py: 作成済み（scripts/slack_commander.py）
- 通知テスト: 未テスト

## cron状態
```
# ============================================
# ROBBY THE MATCH 自律PDCAループ
# ============================================
# 日次（月〜土）
0  6 * * 1-6 /bin/bash ~/robby-the-match/scripts/pdca_morning.sh
0  7 * * 1-6 /bin/bash ~/robby-the-match/scripts/pdca_healthcheck.sh
0 15 * * 1-6 /bin/bash ~/robby-the-match/scripts/pdca_content.sh
0 23 * * 1-6 /bin/bash ~/robby-the-match/scripts/pdca_review.sh
# 週次（日曜のみ）
0  8 * * 0   /bin/bash ~/robby-the-match/scripts/pdca_weekly.sh
# ============================================
```

## 未完了の手動作業
- [x] GA4測定ID置換 → ✅ G-X4G2BYW13B 全27ファイル置換完了（2/20）
- [x] LINE URL置換 → ✅ https://lin.ee/HJwmQgp4 全22ファイル置換完了（2/20）
- [x] Search Console登録 → ✅ メタタグ検証完了+サイトマップ送信（2/20）
- [x] GitHubリポジトリpush → ✅ haruhi-medical/robby-the-match デプロイ完了（2/20）
- [x] GitHub Pages有効化 → ✅ https://haruhi-medical.github.io/robby-the-match/（2/20）
- [ ] Search Console登録+サイトマップ送信
- [ ] Googleビジネスプロフィール登録
- [ ] 独自ドメイン取得
- [ ] TikTokアカウント作成/連携
- [ ] Instagramアカウント作成/連携
- [ ] Mac Miniスリープ無効化（sudo pmset -a sleep 0）

## 次にやるべきこと（優先順）
1. ~~GitHub push + Pages有効化~~ → ✅ 完了
2. ~~GA4設定~~ → ✅ 完了（G-X4G2BYW13B）
3. ~~Search Console登録~~ → ✅ 完了
4. ~~LINE URL設定~~ → ✅ 完了（https://lin.ee/HJwmQgp4）
5. TikTok初投稿（素材は準備済み）
6. sitemap.xml / robots.txt のURL統一

## 問題・ブロッカー
- ~~git remoteが未設定~~ → ✅ 解決済み（2/20 デプロイ完了）
- ~~GA4未設定~~ → ✅ 解決済み（2/20 全27ファイルにG-X4G2BYW13B設定完了）
- **sitemap.xmlのURL**: placeholder.github.io のまま。GitHub組織名/リポジトリ名に合わせて更新が必要。
- **robots.txtのURL**: haruhi-medical.github.io（ルート）とplaceholder.github.io（lp/）で不一致。統一が必要。
- **lp/facility/ が空**: LP-B（施設向け）のindex.htmlが未作成。ただしCLAUDE.md v8.0の方針ではPhase1では不要。
- **Postiz API Key未設定**: TikTok自動投稿不可。手動アップロードが必要。
- **.envにAPIキーがハードコード**: セキュリティ上、GitHubにpushする前に.gitignoreで除外されていることを再確認すること（現在.gitignoreに含まれている）。

## 戦略メモ
- 競合ゼロKW: 「神奈川県西部 看護師」「紹介料 10%」
- 3軸: 手数料破壊(10%) x 地域密着(9市) x 転職品質
- 大手の隙間: TikTokオーガニック未参入
- ロードマップ: 即座→地域KW、1-3ヶ月→高競合KW、12ヶ月→検索1位
