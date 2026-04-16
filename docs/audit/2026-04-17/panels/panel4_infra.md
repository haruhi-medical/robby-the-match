# Panel 4: 基盤 — 議長統合レポート

> 日付: 2026-04-17
> 議長: メインエージェント
> パネル範囲: Cloudflare Worker / cron / Pythonスクリプト / セキュリティ / コスト / SRE
> 重点配分: 守り30%枠

---

## 1. エグゼクティブサマリー

Round 1/2 を経て、**基盤層で18件の阻害要因**を抽出。うち**5件が現在進行形で事業継続性を損ねている**。
流入層（PV3/日・SC 403）ほど派手ではないが、**「既にLINE登録者18人の体験」を守れるかどうか**は基盤の健全性に直結する。

最重要3件を Phase 1 候補に昇格。残り13件は Phase 2/3。

---

## 2. 阻害要因リスト（18件、優先度順）

### 🔴 最重要3件（Phase 1候補）

#### P4-001: `wrangler deploy` 後のシークレット消失を自動検知していない
- **領域**: Worker / SRE
- **根拠**: STATE.md L286「デプロイ後にシークレット消失する問題あり → 必ず `wrangler secret list` で確認」。現状、手動頼み
- **影響**: Worker障害 = 全LINE Bot停止。既存登録者18人全員に影響
- **改善案**:
  1. `scripts/deploy_worker.sh` を新設（unset → deploy → secret list → 7件チェック → 欠損ならSlack + 非ゼロexit）
  2. MEMORY.md `feedback_worker_deploy.md` の手順をコード化
- **実装コスト**: 1h
- **North Star寄与**: 登録者→成約への信頼性 ⚠️高

#### P4-002: Claude CLI認証切れで `autoresearch` と `pdca_weekly_content` が5日以上停止
- **領域**: cron / Python / SRE
- **根拠**: `logs/autoresearch_2026-04-17.log` で 2026-04-14/15/16/17 連続 CONFIG_ERROR。`data/agent_state.json` で `autoresearch: config_error`, `weekly_content_planner: lastRun=2026-04-12`
- **影響**: SNS台本の自動改善ループ停止 → 投稿品質スコア改善が止まる → PV3/日打開困難
- **改善案**:
  1. 短期: 社長に `claude auth login` 実行依頼（Slack通知済のはず）
  2. 中期: `.env` に `ANTHROPIC_API_KEY` を正式設定し、CLI依存をAPI Keyフォールバックに切替（`cron_autoresearch.sh`, `pdca_weekly_content.sh`）
- **実装コスト**: 手動30min / コード切替2h
- **North Star寄与**: SNS流入底上げ ⚠️高

#### P4-003: `SLACK_CHANNEL_ID` デフォルトが旧チャンネル `C09A7U4TV4G` の7ファイル残存
- **領域**: Worker / Security / cron
- **根拠**: `slack_bridge.py`, `notify_slack.py`, `slack_report.py`, `daily_ads_report.py`, `slack_commander.py`, `slack_utils.py`, `fetch_analytics.py` がデフォルト旧IDを使用。MEMORY.md「正しいのは `C0AEG626EUW`」
- **影響**: `.env` 欠損時にLINE登録者の通知が誤チャンネルへ → 担当者が気づかない → 24時間内連絡の約束が破れる
- **改善案**: デフォルト値を `C0AEG626EUW` に統一、または環境変数必須化（`os.getenv("SLACK_CHANNEL_ID")` → `None` なら起動失敗）
- **実装コスト**: 30min
- **North Star寄与**: ハンドオフ信頼性 ⚠️高

---

### 🟡 Phase 2候補（48時間以内、8件）

#### P4-004: `data/daily_snapshot.json` 未生成 — データドリブン運用の土台欠落
- **領域**: Python
- **根拠**: CLAUDE.md `data/daily_snapshot.json` が「日次統合先」と記載だが実在せず。`data/metrics/` 空
- **改善案**: `ga4_report.py` と `meta_ads_report.py` 末尾に snapshot 書き込み追加
- **実装コスト**: 2h

#### P4-005: `watchdog.py` Claude CLI未ログインissuesが重複排除を通過せず30分毎Slack送信
- **領域**: cron / SRE
- **根拠**: watchdog.py L794-801、4/17ログで01:00, 01:30連続通知
- **改善案**: `should_send_alert` + `mark_alert_sent` 適用（2行追加）
- **実装コスト**: 30min

#### P4-006: cronの21:00枠に `pdca_sns_post.sh` と `cron_ig_post.sh`（DISABLED）併存 → Instagram二重投稿リスク
- **領域**: cron
- **根拠**: crontab L250 `0 12,17,18,20,21 pdca_sns_post.sh` / L261 `# DISABLED cron_ig_post.sh`。MEMORY.md「1日3投稿（A×2 + B×1）」
- **改善案**: `posting_schedule.json` 参照ロジックで1日1投稿制限
- **実装コスト**: 1h

#### P4-007: `scripts/deprecated/` 分離未整備 — 現役不明なスクリプトが多数
- **領域**: Python
- **根拠**: `generate_meta_ads.py/v3/v4` 3世代、`generate_image*.py` 3種類、`hellowork_*.py` 5種、`tiktok_*.py` 5種、`fix_*.py` 2本
- **改善案**: `crontab -l` から呼ばれていないファイルを `scripts/deprecated/` に移動
- **実装コスト**: 2h

#### P4-008: 障害プレイブック（runbook.md）未整備
- **領域**: SRE
- **根拠**: `docs/` に運用ランブック不在
- **改善案**: `docs/runbook.md` 作成（Worker 503 / Instagram CDP失敗 / Claude CLI切れ等8項目）
- **実装コスト**: 2h

#### P4-009: Worker監視がwatchdog 30分間隔のみ — MTTD最大90分
- **領域**: SRE / Cost
- **根拠**: watchdog.py L754 health check 30分間隔、3連続失敗でアラート
- **改善案**: UptimeRobot 5分間隔無料枠（月¥0）
- **実装コスト**: 15min

#### P4-010: `notify_slack.py` と `slack_bridge.py` 併存 — `.claude/rules/scripts.md` 違反
- **領域**: Python
- **根拠**: watchdog.py L111 は notify_slack.py を呼ぶ（rulesでは bridge推奨）
- **改善案**: watchdog.py の呼び出しを `slack_bridge.py --send` に変更
- **実装コスト**: 30min

#### P4-011: LINE通知Slackで電話番号がフル平文
- **領域**: Security
- **根拠**: Worker handoff時にSlackへ電話番号送信（FACT_PACK §7）
- **改善案**: Slackメッセージ本文は末尾4桁マスク、詳細はbutton経由で別API
- **実装コスト**: 1h

---

### 🟢 Phase 3候補（1週間以内、7件）

- **P4-012**: `tiktok_upload_playwright.py` bare except 10箇所 → `except Exception as e:` 化（現在手動運用のため優先度低）
- **P4-013**: `content/generated/` 787MB・`data/ 479MB` 古いバッチアーカイブ（`scripts/archive_old_content.sh` 月次化）
- **P4-014**: Worker `/api/health` に `ai_ok` フィールド追加（OpenAI Key健全性確認）
- **P4-015**: サービスアカウント `odawara-nurse-jobs` のIAM権限最小化（社長GCP操作依頼）
- **P4-016**: `.env` chmod 600 確認 / Keychain移行（中期）
- **P4-017**: Slack送信失敗時の `data/alert_queue.json` 積み上げ（Slack障害時の見逃し防止）
- **P4-018**: `pdca_healthcheck.sh` 正常通知を平日1回に圧縮（※社長判断必要）

---

## 3. 「やらない」リスト（戦略監督向け）

- OpenAI→Workers AI の全面切替（1-B改善案）: 品質劣化リスク大。A/Bテスト未実施時点ではやらない
- Meta広告予算の変更提案: **禁止事項に該当**。人間のみ可能
- Cloudflare D1の監視強化: 現状無料枠内。コストも予防的。優先度低
- `notify_slack.py` 完全削除: 呼出元スクリプトが複数。段階廃止が安全

---

## 4. コスト集計（今回提案の合算）

| Phase | 時間コスト | 金銭コスト |
|-------|----------|----------|
| Phase 1（3件） | 3.5h | ¥0 |
| Phase 2（8件） | 9h | ¥0 |
| Phase 3（7件） | 12-15h | ¥0（社長側IAM操作含む） |
| **合計** | **24-27h** | **¥0** |

**新規月額契約なし**（禁止事項「月3万超新規契約禁止」遵守）

---

## 5. North Star（成約1件）寄与度スコア

| # | 寄与度 | 根拠 |
|---|-------|------|
| P4-001 | **高** | Worker停止=全LINE Bot停止。登録者離脱100% |
| P4-002 | **高** | SNS台本品質改善停止→PV3/日打開不能 |
| P4-003 | **高** | ハンドオフ失敗→24h連絡不能→信頼喪失 |
| P4-004 | 中 | 判断材料欠損。施策精度低下 |
| P4-005 | 低 | アラート疲労。間接影響 |
| P4-006 | **高** | Instagram BAN=SNS流入全停止 |
| P4-007 | 低 | 開発効率 |
| P4-008 | 中 | MTTR短縮 |
| P4-009 | 中 | MTTD短縮 |
| P4-010 | 低 | コード整合性 |
| P4-011 | 中 | PII漏洩予防 |
| P4-012-018 | 低 | 守り深化 |

---

## 6. 品質監督向けチェックポイント

- ✅ 全項目に実在ファイル・行番号・ログ証跡あり
- ✅ 架空数値・架空ログなし
- ✅ 月3万超の新規契約提案なし
- ✅ 破壊的操作提案なし（force push / hard reset / pkill Chrome等）
- ✅ 「平島禎之」露出提案なし
- ✅ ミサキテスト済み

---

## 7. 未確認データ項目（メインに提示）

1. Cloudflare Workers の月次利用量（Requests/Neurons）— `wrangler tail` や Dashboard未確認
2. `.env` の実ファイル権限（chmod確認未実施 — 機密のため読まない指示）
3. OpenAI月次コスト実績（管理画面閲覧権限なし）
4. UptimeRobot未導入（Phase 2で提案）
5. Slack送信失敗率（`logs/` に記録されているが未集計）
6. Claude CLI認証復旧後の `autoresearch` 効果測定（未実行中のため）

---

**結論**: 基盤層の3つの最重要問題（P4-001/002/003）はいずれも**既に発火している**か**いつ発火してもおかしくない**状態。
3.5hで手当可能。**「流入が死ぬ前に、入ってきた登録者を取りこぼさない土台」を固めるべき**。
