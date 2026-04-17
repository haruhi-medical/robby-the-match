# scripts/deprecated/ — 廃止スクリプト置き場

> 2026-04-17 作成（audit Phase 2 #49 / panel4_infra P4-007 対応）

このディレクトリには「**過去のバージョン**」「**置き換え先が明確に存在**」する旧世代スクリプトを隔離している。
cronや他スクリプトからの参照は**すべて解消済み**（移動前に `grep -r` 確認）。

## 原則

1. **削除しない**: コード履歴として残す。Git履歴＋このフォルダで二重管理
2. **復活させない**: ここに入ったものは基本使わない。必要なら置き換え先を直せ
3. **ここにあるコードは動作保証外**: 依存バージョン・API仕様が古い可能性大

## 廃止ファイル一覧

| ファイル | 廃止理由 | 置き換え先 |
|---------|---------|-----------|
| `generate_meta_ads.py` | v2.0（旧クリエイティブ生成） | `scripts/generate_meta_ads_v4.py` |
| `generate_meta_ads_v3.py` | v3（API変更前の旧版） | `scripts/generate_meta_ads_v4.py` |
| `generate_image.py` | Google Gemini 2.0 Flash試作 / 画像直接生成方式 | `scripts/generate_carousel.py` + Playwright（MEMORY.md `playwright_carousel_system.md`）|
| `generate_image_cloudflare.py` | Cloudflare Workers AI試作 / 画像直接生成方式 | `scripts/generate_carousel.py` + Playwright |
| `generate_image_imagen.py` | Google Imagen 4 Fast試作 / 画像直接生成方式 | `scripts/generate_carousel.py` + Playwright |
| `post_to_tiktok.py` | Postiz経由TikTok下書き投稿（Postizサービス未契約） | `scripts/tiktok_post.py` + `scripts/tiktok_upload_playwright.py` |
| `daily_pipeline.sh` | Postiz時代の日次パイプライン（cron登録なし） | `scripts/pdca_sns_post.sh` + `scripts/cron_tiktok_post.sh` |
| `fix_meta_tags.py` | 一度全HTMLに meta robots/og 統一した1回限りの修正スクリプト | 同様の修正が必要なら新規作成 |

## 確認済み事項（2026-04-17）

- 現行 `crontab -l` に廃止ファイルの参照なし
- `scripts/*.sh` および `scripts/*.py` から廃止ファイルの呼び出しなし（`pdca_sns_post.sh` は `ai_content_engine.py` / `sns_workflow.py` / `ig_post_meta_suite.py` を使用）
- `hellowork_*.py` （5種）は全て `pdca_hellowork.sh` から呼ばれるため**廃止せず**
- `tiktok_auth.py` / `tiktok_analytics.py` / `tiktok_carousel.py` / `tiktok_post.py` / `tiktok_upload_playwright.py` / `tiktok_profile_update.py` は全て現役のため**廃止せず**
- `fix_ready_posts.py` は手動運用可能性があるため保留（要判断）
- `netlify_unpause.mjs` は Netlify 帯域復帰待ち（2026-03-25〜）のため保留

## 復活が必要になったら

```
git log --all --oneline -- scripts/deprecated/<file>     # 履歴確認
mv scripts/deprecated/<file> scripts/<file>              # 復活
# 新しい呼び出し元を追加（cron / *.sh）する前に動作確認すること
```

## 関連ドキュメント

- `docs/audit/2026-04-17/panels/panel4_infra.md` §P4-007
- `docs/audit/2026-04-17/supervisors/strategy_review.md` 項目#49
- `docs/audit/2026-04-17/implementations/phase2_group_m.md`
