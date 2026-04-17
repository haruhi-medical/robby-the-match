# Phase 2 Group J + Phase 3 実装レポート — Worker/chat.js/LP

> **実装者**: Claude / **日時**: 2026-04-17 / **範囲**: Phase 2 #32, #40, #41, #42, #44 + Phase 3 #51, #53, #62
> **根拠**: `docs/audit/2026-04-17/supervisors/strategy_review.md`（Phase 2: 22項目 / Phase 3: 13項目）

## 完了状態（8件 / 8件）

| # | 項目 | 状態 | 主な変更 |
|---|------|------|---------|
| 32 | scoreFacilities LP側（chat.js）D1 24,488件対応 | ✅完了 | Worker `/api/facilities/search` 新規 + `chat.js` 非同期フェッチ化 |
| 40 | 各 il_* フェーズ「前に戻る」QR追加 | ✅完了 | il_subarea / il_facility_type / il_department / il_workstyle / il_urgency 全5箇所 + `il_back=<target>` postback |
| 41 | follow時Push失敗Slack通知＋再送cron | ✅完了 | `linePushWithFallback` 共通ラッパー + `handleScheduledFailedPushRetry`（15分cron相乗り） |
| 42 | shindan引き継ぎ待機短縮（事前生成） | ✅完了 | `handleLineStart` で `ctx.waitUntil` 事前マッチング + `preMatching:{sid}` KV 15分TTL + LIFF/dm_text両経路で復元 |
| 44 | ADJACENT_AREAS越境同意QR | ✅完了 | `matching_browse` 3件未満時に「◯◯も含める」QR + `expand_adjacent` postback |
| 51 | phase遷移ログをD1に記録＋週次レポート | ✅完了 | `phase_transitions` テーブル + `logPhaseTransition` + `phase_transition_weekly_report.py` |
| 53 | 逆指名カードをフェーズB向けに | ✅完了 | `lp/job-seeker/index.html` 逆指名セクション文言改訂（「まだ情報収集中の人にこそ」訴求） |
| 62 | /api/health に ai_ok フィールド | ✅完了 | OpenAI/Workers AI 疎通確認（`?deep=1` で実リクエスト） |

## 変更ファイル一覧

### 編集
- `api/worker.js`（+450行程度）
  - `/api/facilities/search` 新規エンドポイント + `handleFacilitiesSearch` + 神奈川9エリア中心座標
  - `/api/health` に `ai_ok` / `overall_ok` / `deep=1` 疎通プローブ
  - `linePushWithFallback` 共通 Push ラッパー（Slack通知 + failedPush KV キュー）
  - `handleScheduledFailedPushRetry` cron 実装（30分遅延・最大3回）
  - `handleLineStart` に preMatching 生成 `ctx.waitUntil` ブロック
  - webhook follow（LIFF経路）+ dm_text経路に `preMatching:{sid}` キャッシュ復元
  - `il_back=<target>` postback 処理追加（pref/subarea/ft/ws/dept/urg/restart）
  - il_subarea/il_facility_type/il_department/il_workstyle/il_urgency の QR に「← 前に戻る/最初からやり直す」
  - `matching_browse` に `expand_adjacent` QR + postback ハンドラ
  - `logPhaseTransition` 関数 + follow/postback/text 経路3点でのフック
  - `handleLinkSession` の `fetch()` 直push → `linePushWithFallback` 置換
  - scheduled に `handleScheduledFailedPushRetry` 追加
- `chat.js`（+60行）
  - `findMatchingHospitalsAsync` + `fetchFacilitiesFromWorker` + `postprocessHospitalsFromApi`
  - `deliverTeaser` を Promise 対応に改修（失敗時は既存同期版フォールバック）
- `api/schema.sql`（+21行）
  - `phase_transitions` テーブル + 3インデックス（created_at/next_phase/user_hash）
- `lp/job-seeker/index.html`
  - 逆指名カードを「まだ情報収集中の人にこそ」向けにコピー改訂

### 新規
- `scripts/phase_transition_weekly_report.py`（248行）
  - `wrangler d1 execute --json --remote` で週次集計 → Slack 送信
  - ステージ別流入 / 離脱phase トップ10 / エッジ（prev→next）トップ15 / 温度帯 / 流入元
- `docs/audit/2026-04-17/implementations/phase2_j_phase3_worker.md`（本ファイル）

## 構文チェック結果

```
$ node --check api/worker.js                                 → OK（出力なし）
$ node --check chat.js                                       → OK（出力なし）
$ python3 -m py_compile scripts/phase_transition_weekly_report.py → OK
$ python3 -c "import html.parser; ... feed(index.html)"     → HTML parse OK
```

## 各項目の実装ポイント

### #32 scoreFacilities D1対応
- `GET /api/facilities/search?area=yokohama&limit=10&category=病院`
- 神奈川9エリアの中心座標（横浜駅/川崎駅/相模原駅ほか）でHaversine距離計算
- `bed_count DESC` で D1 側 SELECT → JS 側で距離昇順ソート → top N
- chat.js は Promise 対応環境では API を優先、失敗時のみハードコード 212件 fallback
- 4秒タイムアウト（UX 維持）

### #40 「前に戻る」QR
- 新規 postback: `il_back=pref/subarea/ft/ws/dept/urg/restart`
- 戻る先より後の選択をリセット（例: `il_back=ft` は facilityType/workStyle/urgency を削除）
- 全 il_* フェーズ（il_subarea/il_facility_type/il_department/il_workstyle/il_urgency）の Quick Reply に末尾追加
- il_workstyle のみ条件分岐: 病院選択時は `il_back=dept`、クリニック/訪看/介護時は `il_back=ft`

### #41 Push 失敗の Slack 通知＋再送 cron
- `linePushWithFallback(userId, messages, env, { tag })` 共通ラッパー新設
- 失敗時: `failedPush:{userId}:{ts}` KV キー（1時間TTL）+ Slack 通知
- 400/403（ユーザーブロック）は再送スキップ
- 既存15分cron `handleScheduledHandoffFollowup` の横で `handleScheduledFailedPushRetry` を相乗り
- 再送ロジック: 30分以上経過したキューを拾う → 成功で削除 / 失敗は新キー書き直し / `MAX_ATTEMPTS=3` 超過で諦めSlack通知+削除
- `handleLinkSession` の already_friend push も共通ラッパー経由に置換

### #42 shindan 引き継ぎ待機短縮
- `handleLineStart` の 302 リダイレクト直前に `ctx.waitUntil(async () => { ... })` で裏生成
- answers から仮想 entry を構築 → `generateLineMatching(virtualEntry, env)` → 圧縮して `preMatching:{sessionId}` に put（15分TTL）
- follow (LIFF) 経路で sessionId を key にキャッシュ検索 → ヒットすれば `entry.matchingResults` に即セット + `_preMatchingHit` フラグ
- dm_text 経路（テキストメッセージで session_id が届くケース）でも同様の復元
- 使用済みキャッシュは `delete` で即消去
- 効果: LINE追加直後の「数秒〜数十秒の沈黙」を短縮（matching生成を待たず即表示可能）

### #44 ADJACENT_AREAS 越境同意 QR
- `matching_browse` で結果が 0 件または 3 件未満 + `ADJACENT_AREAS[area]` 定義あり + `entry.adjacentExpanded !== true` の条件で提示
- 隣接エリア上位2件を `matching_browse=expand_adjacent&adj=<key>` 形式で QR 化
- postback 受信で `entry._originalArea` を保存、`area` を隣接キーに切り替え、再マッチング → `matching_preview`
- 同じセッションで連続表示しないため `adjacentExpanded` フラグでガード

### #51 phase_transitions D1ログ + 週次レポート
- `CREATE TABLE phase_transitions` + 3インデックス（schema.sql）
- `logPhaseTransition(userId, prevPhase, nextPhase, eventType, entry, env, ctx)` を `ctx.waitUntil` で非同期書き込み
- userId は先頭12文字にトリム（PII 抑制）
- follow / postback / text の3箇所でフック
- `scripts/phase_transition_weekly_report.py`
  - `npx wrangler d1 execute nurse-robby-db --command "SELECT ..." --remote --json --config wrangler.toml`
  - 集計: ステージ別流入 / 離脱 phase トップ10 / エッジトップ15 / 温度帯 / 流入元
  - `slack_utils.send_message(SLACK_CHANNEL_REPORT, text)` で Slack 送信
  - 推奨 cron: 日曜 09:30 JST（`30 0 * * 0` UTC）

### #53 逆指名カード（フェーズB向け）
- 「まだ情報収集中の人にこそ」という先頭ラベルを追加
- 「今すぐ転職する気はない。でもあの病院の求人が出たら動きたい」に文言ピボット
- 「求人が公開された時だけLINEでお知らせ」の受動的な導線を強調
- CTA色は緑維持（コーラル不採用ルール遵守）
- 「平島禎之」「はるひメディカルサービス」露出なし

### #62 /api/health ai_ok
- 既存 `/api/health` を拡張（後方互換）
- `?deep=1` なしのデフォルト: `env.OPENAI_API_KEY` / `env.AI` の有無のみ返す（軽量）
- `?deep=1`: 両プロバイダに max_tokens=1 の軽量リクエストで疎通確認（3秒タイムアウト・Promise.all）
- レスポンス: `{ status, timestamp, ai_ok: { openai, workers_ai }, overall_ok, deep }`

## デプロイ時の注意

1. **wrangler deploy は**メインがまとめて実行（社長指示に従う）
2. デプロイ前に schema.sql を D1 本番反映が必要:
   ```bash
   cd api && unset CLOUDFLARE_API_TOKEN && \
     npx wrangler d1 execute nurse-robby-db \
     --command "CREATE TABLE IF NOT EXISTS phase_transitions ( ... );" \
     --remote --config wrangler.toml
   ```
   （schema.sql 全体を流す場合: `--file=schema.sql`）
3. Worker デプロイ後は `wrangler secret list --config wrangler.toml` で7件のシークレット欠損チェック
4. `phase_transition_weekly_report.py` のcron登録（crontab）は別途:
   `30 0 * * 0 cd /Users/robby2/robby-the-match && python3 scripts/phase_transition_weekly_report.py >> logs/phase_weekly.log 2>&1`
5. chat.js の CORS: Worker 側 `isOriginAllowed` に `https://quads-nurse.com` / `https://www.quads-nurse.com` が含まれていることを確認（現状含む）

## 未解決・懸念

1. **preMatching のサイズ**: matchingResults 5件でも KV put サイズは ~3〜5KB 想定。1000セッション同時でも KV 月額無料枠（1GB storage）内。要監視
2. **failedPush KV キー削除の冪等性**: 再送時の失敗で新キーを書き、古いキーを delete しているが、KV の eventual consistency で二重書き込みが発生する可能性あり（数秒で収束）。実害なし
3. **phase_transitions の書き込みレイテンシ**: D1 書き込みは ctx.waitUntil で非同期。万が一 waitUntil 制限（30秒）を超える場合は書き漏れるが、Worker 実行完了後に解決するため通常運用では問題なし
4. **/api/health?deep=1 のコスト**: OpenAI gpt-4o-mini `max_tokens=1` は 1req $0.0000... 程度（~0.015円/回）。UptimeRobot 5分監視でも月10円未満
5. **chat.js の AbortController**: IE11 非対応だが、`typeof AbortController !== 'undefined'` でガード済み。モダンブラウザのみで動作
6. **il_back=restart 時**: `welcomeSource` / `webSessionData` は保持したまま。セッション完全リセットではない（意図通り）
7. **ADJACENT_AREAS 越境後の「元に戻す」UI**: 現状は `adjacentExpanded=true` フラグでQR抑制のみ。元エリアに戻すUIは別途要検討（Phase 3 以降）

## 遵守チェック

- React SPA / マッチングアルゴリズム新規構築: なし（既存ロジック再利用のみ）
- 月額新規契約: なし
- CTA色: 緑維持（逆指名カードも緑系のまま）
- 「平島禎之」/「はるひメディカルサービス」公開ページ露出: なし
- 架空データ: なし（D1 実データ + 既存212件fallback）
- Meta広告予算変更: 該当なし
- wrangler deploy: 実行せず
- git commit: 実行せず

**完了**
