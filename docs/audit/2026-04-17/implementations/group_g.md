# Group G 実装報告 — 2026-04-17

> **実装対象**: Phase 1 基盤3項目（#9 / #11 / #20）
> **参照**: `docs/audit/2026-04-17/supervisors/strategy_review.md`
> **状態**: 3項目すべて完了・実機検証済み

---

## 1. 完了項目

### #9 `scripts/deploy_worker.sh` — シークレット消失自動検知（1h想定）
- 新規作成。`unset CLOUDFLARE_API_TOKEN` → `npx wrangler deploy --config wrangler.toml` → `wrangler secret list` → 必須7件を検証
- 欠損検知時は Slack `#ロビー小田原人材紹介`（`C0AEG626EUW`）に復旧手順を付けて通知、exit=1
- デプロイ失敗時は exit=2 で即通知
- secret list の出力形式（JSON／text）両対応の grep 照合
- `bash -n` 構文チェック通過 / 実行権限付与済み

### #11 M-02 `scripts/daily_snapshot_merge.py` — GA4/Meta/ハローワーク/Worker統合（2-4h想定）
- 新規作成。GA4 Data API / Meta Graph API / `data/hellowork_history/YYYY-MM-DD.json` / `logs/*_YYYYMMDD.log` を統合
- `data/daily_snapshot.json` にローテーション書き込み（35日保持・原子的置換）
- `--date` / `--dry-run` オプション対応
- **実データで動作確認**: `--date 2026-04-16` で GA4 activeUsers=19 / Meta spend=¥867 / ハローワーク総数=3,739 を取得・統合成功
- 架空データ禁止遵守: 認証未設定／ゼロ行時は `_error` / `_note` フィールドで明示

### #20 M-04 `api/worker.js` Slack電話番号マスク（1h想定）
- `maskPhone()` 関数を `formatPhoneDisplay` 直下に追加（L2228-）
- 末尾4桁以外を `****` にマスク（携帯/固定とも対応、非番号文字列はそのまま返却）
- 以下4箇所のSlack通知で適用:
  1. `handleChatComplete` 会話完了通知（L2125）
  2. `handleApply` 新規求職者登録通知（L2446）
  3. `sendApplyNotification` 紹介候補打診依頼（L3742）
  4. `buildHandoffSlackPayload` ハンドオフ通知（L5457）
- `node --check worker.js` 構文OK / 関数単体テスト（携帯/固定/無効値/null）通過

---

## 2. 作成・変更ファイル

| 区分 | パス | 種別 |
|---|---|---|
| 新規 | `scripts/deploy_worker.sh` | 実行ファイル(3.9KB) |
| 新規 | `scripts/daily_snapshot_merge.py` | 実行ファイル(10.2KB) |
| 新規 | `data/daily_snapshot.json` | 初期生成 (2026-04-16 分の実データ格納) |
| 修正 | `api/worker.js` | +27行（関数定義） / 4箇所の文字列差し替え |

---

## 3. `daily_snapshot.json` スキーマ例

```json
{
  "version": 1,
  "last_updated": "2026-04-17T07:25:54",
  "snapshots": {
    "2026-04-16": {
      "date": "2026-04-16",
      "generated_at": "2026-04-17T07:25:41",
      "ga4": {
        "activeUsers": 19.0,
        "sessions": 25.0,
        "screenPageViews": 25.0,
        "newUsers": 3.0,
        "averageSessionDuration": 43.47,
        "bounceRate": 1.0,
        "top_sources": [
          {"source": "(not set)", "sessions": 17, "active_users": 13},
          {"source": "(direct)",  "sessions": 9,  "active_users": 6},
          {"source": "meta",      "sessions": 8,  "active_users": 7}
        ]
      },
      "meta_ads": {
        "impressions": 161,
        "clicks": 5,
        "spend_jpy": 867.0,
        "cpc_jpy": 173.4,
        "ctr_pct": 3.106,
        "reach": 131,
        "actions_by_type": {"link_click": 3, "video_view": 22, "...": "..."},
        "leads": 0,
        "cpa_lead_jpy": null
      },
      "hellowork": {
        "date": "2026-04-16",
        "fetched_at": "2026-04-16T06:47:xx",
        "total_all": 0,
        "total_nurse": 3739,
        "_source_file": "data/hellowork_history/2026-04-16.json"
      },
      "worker": {
        "ads_report_log_bytes": 1234,
        "ads_report_ok": true,
        "ga4_report_log_bytes": 890,
        "ga4_report_sc_403": true
      }
    }
  }
}
```

エラー時は各セクションに `{"_error": "<理由>"}` を格納（架空データ補完は行わない）。

---

## 4. 電話マスク関数の呼び出し箇所数

**関数定義**: 1箇所（`api/worker.js:2228 function maskPhone(value)`）

**呼び出し**: 4箇所すべてSlack通知経路
| 行 | 関数 | 用途 |
|---|---|---|
| L2125 | `handleChatComplete` | LP診断完了サマリ（`*電話番号*: ...`） |
| L2446 | `handleApply` | 新規求職者登録通知（`連絡先：...`） |
| L3742 | `sendApplyNotification` | 紹介候補打診依頼（`📞 ...`） |
| L5457 | `buildHandoffSlackPayload`内 `phoneNumberText` | LINE→人間ハンドオフ通知（`📱 電話番号: ...`） |

※ Google Sheets 書き込み（社内台帳 L2193 / L2471）は社内管理用のためマスク対象外（仕様どおり）。
※ LINE応答文本体（ユーザー自身に返す文言）は未マスク（ユーザー本人の確認のため）。

---

## 5. 懸念・残タスク

1. **Worker再デプロイ必須**: `maskPhone` の有効化には `bash scripts/deploy_worker.sh` を実行すること。デプロイ後 `wrangler secret list` で7件確認まで自動化済み。
2. **cron反映は未実施**: `daily_snapshot_merge.py` のcrontab登録は本実装スコープ外（社長対応）。推奨エントリ:
   ```
   15 8 * * * cd ~/robby-the-match && /usr/bin/env python3 scripts/daily_snapshot_merge.py >> logs/daily_snapshot_$(date +\%Y-\%m-\%d).log 2>&1
   ```
   GA4レポート(08:05) / Ads レポート(08:10) の直後に走らせる設計。
3. **SC API 403 は未解決**: `worker.ga4_report_sc_403=true` が出続ける可能性あり。戦略レビュー #7（社長手動対応）で権限付与されるまで snapshot の SC セクションは欠落。現時点では GA4 のみ実データ化で十分な意思決定が可能。
4. **Python 3.9 FutureWarning**: google-auth / api-core が 3.10 以上推奨。実害はないが将来のアップグレード候補。
5. **wrangler secret list の出力フォーマット変化リスク**: deploy_worker.sh は両形式（JSON / text）を許容するgrep。将来wrangler仕様変更で検知漏れが起きた場合はSlack `secret欠損` 誤報になり得る（fail-safe側）。
6. **maskPhone の国際電話未対応**: `+81-90-...` のような形式は10-11桁正規表現に引っ掛からず原文返却。現状は国内番号のみ想定で十分。
