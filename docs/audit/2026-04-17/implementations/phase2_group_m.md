# Phase 2 Group M 実装レポート — 基盤4項目

> **実装者**: Claude / **日時**: 2026-04-17 / **範囲**: Phase 2 #45, #48, #49, #50
> **根拠**: `docs/audit/2026-04-17/supervisors/strategy_review.md` + `docs/audit/2026-04-17/panels/panel4_infra.md`

## 完了状態

| # | 項目 | 状態 | 成果物 |
|---|------|------|-------|
| 45 | Slack Block Kit化（長文折りたたみ） | ✅完了 | `scripts/slack_utils.py` に `build_block_kit_message` + `send_slack` 追加 |
| 48 | watchdog Claude CLI 重複排除修正 | ✅完了 | `scripts/watchdog.py` L779-L820付近を改修 |
| 49 | `scripts/deprecated/` 分離整備 | ✅完了 | 8ファイル移動 + README.md 作成 |
| 50 | `docs/runbook.md` 作成 | ✅完了 | 6カテゴリ障害対応手順 |

## 変更/新規作成ファイル

### 編集
- `scripts/slack_utils.py` — Block Kit ヘルパー追加（既存 `send_message` は無変更で互換性維持）
- `scripts/watchdog.py` — Claude CLI認証チェックを `get_job_recovery` + `should_send_alert` + `mark_alert_sent` 経由に統合

### 新規
- `docs/runbook.md` — 障害対応ランブック（6カテゴリ + 共通フロー + 禁止事項）
- `scripts/deprecated/README.md` — 廃止ファイル一覧＋復活手順
- `docs/audit/2026-04-17/implementations/phase2_group_m.md` — 本ファイル

### 移動（scripts/ → scripts/deprecated/）
- `generate_meta_ads.py`（v2.0 旧版 → v4 へ）
- `generate_meta_ads_v3.py`（v3 旧版 → v4 へ）
- `generate_image.py`（Gemini直接生成 → Playwrightカルーセルへ）
- `generate_image_cloudflare.py`（CF Workers AI試作）
- `generate_image_imagen.py`（Imagen 4 Fast試作）
- `post_to_tiktok.py`（Postiz連携 → tiktok_post.py + tiktok_upload_playwright.py へ）
- `daily_pipeline.sh`（Postiz時代の日次パイプライン、cron登録なし）
- `fix_meta_tags.py`（一度限りのmeta統一修正スクリプト）

**移動ファイル数: 8**

## deprecated/ に移動した内容の要約

- **Meta広告クリエイティブ生成**: v2/v3 → v4（最新）のみ残す。2世代分を隔離
- **画像生成（3種）**: 全てPlaywright+HTMLカルーセル方式に置き換え済み（MEMORY.md `playwright_carousel_system.md`）。3ファイルとも呼び出し元なし
- **TikTok投稿（Postiz系）**: 現行は `tiktok_post.py`（tiktokautouploader主力）+ `tiktok_upload_playwright.py`（フォールバック）。Postizは未契約
- **日次パイプライン**: crontabに存在せず、内容もPostiz/notify_slack.py（旧式）依存
- **meta統一修正**: 1回限りの修正スクリプト、過去処理完了

すべて `grep -r` で呼び出し元を検証し、cron/active scriptsからの参照ゼロを確認した。

## runbook.md の目次

1. **Worker障害（Cloudflare `robby-the-match-api`）** — `/api/health` 監視、シークレット欠損時の wrangler復旧手順、`--config wrangler.toml` 必須の注意
2. **cron失敗（pdca_*.sh / watchdog.py / sns_post）** — CONFIG_ERROR vs TRANSIENT分岐、`--reset` フラグ、sns_post/instagram_engage/autoresearchの個別注意点
3. **Slack通知途絶（bridge / webhook / bot）** — チャンネルID新旧混同（`C09A7U4TV4G` vs `C0AEG626EUW`）、Bot Token検証、Webhookフォールバック
4. **LINE Bot応答停止（ハンドオフ/AI応答）** — Webhook疎通確認、OpenAI Key失効チェック、AI応答フォールバック（Phase 1 #2関連）、handoff沈黙（Phase 1 #14関連）
5. **Meta広告 Lead計測異常（Pixel / CAPI）** — Test Events手動発火、Pixel ID確認、CAPI未実装の検知、**予算変更禁止**の明記
6. **SEOインデックス異常（GSC / sitemap / Pages）** — GitHub Actions `deploy-pages.yml` 確認、sitemap 87URL検証、GSC API 403対応、IndexNow ping

共通: エスカレーション3レベル（Claude自動 / 併走 / 社長対応）、連絡先、PROGRESS.md記録テンプレ、runbook全体の禁止事項

## 構文チェック結果

```
$ python3 -c "import ast; ast.parse(open('/Users/robby2/robby-the-match/scripts/slack_utils.py').read()); print('OK')"
OK

$ python3 -c "import ast; ast.parse(open('/Users/robby2/robby-the-match/scripts/watchdog.py').read()); print('OK')"
OK
```

Block Kit ヘルパーの動作検証（3500文字本文 + 15件details）:
```
ブロック数: 8
  [0] header
  [1] section (34文字) — details折りたたみ（summary）
  [2] divider
  [3] section (170文字) — 失敗ジョブ詳細（15件→8件+残り7件要約）
  [4] divider
  [5] section (2800文字) — 長文本文 前半
  [6] section (700文字) — 長文本文 後半（自動分割）
  [7] context — タイムスタンプ
```

期待通り、3000文字制限と50ブロック制限の両方を自動回避。

## 確認事項・残存リスク

1. **deprecated/README.md** の「復活が必要になったら」手順は git mv で履歴保持を前提。必要時は慎重に
2. **watchdog.py の 修正** は `claude_cli_auth` を新規ジョブ名として recovery_log に登録。既存の recovery_log 構造と互換
3. **Block Kit の `send_slack` 関数**は新規API。既存呼び出し元はゼロ（互換性問題なし）。今後 slack_bridge.py 側から段階的に利用を推奨
4. **fix_ready_posts.py** / **netlify_unpause.mjs** は判定保留（理由: 前者は手動運用可能性、後者はNetlify帯域復帰待ち）
5. **hellowork_*.py（5種）・tiktok_*.py（6種）**は全て現役のため**対象外**

## 遵守チェック

- ✅ 破壊的操作なし（rm/pkillなし）
- ✅ 参照中スクリプトの移動なし（grep -rで確認済）
- ✅ 架空データなし
- ✅ 「平島禎之」露出なし
- ✅ git commit 実行せず

**完了**
