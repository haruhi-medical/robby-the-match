# Phase 1 実装記録（グループA残り + グループB）

> 実装日: 2026-04-17
> 実装者: Claude Code（サブエージェント）
> 参照: `docs/audit/2026-04-17/supervisors/strategy_review.md`
> 制約遵守: CTA緑維持 / 金額非変更 / 個人名非露出 / 派遣除外 / 架空データ禁止

## 完了項目（12件 / 12件）

### グループA（LP・welcome文言・UI）7件

#### #6 welcome QR 3択化
- **ファイル**: `api/worker.js`
- **変更**: `buildSessionWelcome()` のshindan/area_page以外の共通welcomeメッセージのQR。1択だった「求人を見てみる」を3択（`求人を見る` / `相場が知りたい` / `相談したい`）に拡張。LIFF未経由のfollow-up welcomeメッセージ（line 6175付近）も同じ3択QRに統一。
- **postback対応確認済み**: `handleLinePostback`（line 5694付近）で既に `welcome=see_jobs` / `welcome=see_salary` / `welcome=consult` を処理（`welcomeIntent` 設定 → `il_area` / `faq_salary` / `handoff_phone_check` へ遷移）

#### #12 Hero CTA文言「1分で診断する（電話なし）」
- **ファイル**: `lp/job-seeker/index.html` L1438
- **変更前**: `LINEで求人検索する`
- **変更後**: `1分で診断する（電話なし）`
- **CTA色**: `.cta-line-hero`（LINE緑 `#06C755` グラデーション）維持。コーラル不使用

#### #13 welcomeコピー短縮 ＋ 感情訴求分離
- **ファイル**: `api/worker.js`（buildSessionWelcome共通EP + フォロー時両方）
- **変更前**: `「職場を変えたい」は、「もっと自分らしく働きたい」の裏返しだと思う。\n\n5つタップするだけ。名前も聞きません。\n\nLINEで静かに、転職活動。`（約65文字）
- **変更後**: 時間帯グリーティング + `ナースロビーです。\nまずはどのエリアで働きたいですか？`（約28文字 + グリーティング）。3択QRを即表示

#### #23 「いつでもブロックOK」 Final CTA 1箇所に集約
- **ファイル**: `lp/job-seeker/index.html`
- **変更**: Hero CTA直下 `.hero-note`（L1440）から「いつでもブロックOK」を削除 → Final CTA（L1734）のみ残す。`grep 'いつでもブロック' lp/job-seeker/index.html` 実行で1箇所のみ確認済

#### #24 Final CTA文言差別化「匿名で相談」
- **ファイル**: `lp/job-seeker/index.html` L1729-1733
- **変更前**: `または直接相談する` / `無料で求人を受け取る`
- **変更後**: `または匿名で相談する` / `匿名でLINE相談する`
- Hero CTA（`1分で診断する（電話なし）`）との被りを回避

#### #25 hero-note フォントUP＋視認性改善
- **ファイル**: `lp/job-seeker/index.html` L468-476
- **変更前**: `font-size: 0.78rem; color: var(--text-muted); margin-top: 4px`
- **変更後**: `font-size: 1.05rem`（約1.35倍）、 `color: var(--text-secondary)`（コントラスト改善）、`font-weight: 600`、`margin-top: 10px`、`line-height: 1.6`
- 先頭の `※` も不要化（視認性優先で削除）

#### #28 安心バー 許可番号サイズ調整
- **ファイル**: `lp/job-seeker/index.html` L1446
- **変更前**: `<span style="color:var(--primary);font-weight:600;">許可番号 23-ユ-302928</span>`
- **変更後**: `<span aria-label="有料職業紹介事業許可番号 23-ユ-302928" style="font-size:0.68rem;color:var(--text-muted);font-weight:400;margin-left:6px;">（許可 23-ユ-302928）</span>` — primary色を外し、フォント小さく、aria-labelで完全表記を残しつつ視覚ノイズを削減

### グループB（求人マッチング・除外フィルタ）5件

#### #16 hellowork 派遣 `emp_type` 除外フィルタ
- **ファイル**: `scripts/hellowork_to_d1.py`
- **変更**: `should_exclude_job()` 関数を新設。`details.emp_type` または `job_title` に「派遣」を含むレコードを除外。D1投入の直前で二重チェック（上流 `hellowork_rank.py` の除外が漏れた場合のセーフティネット）

#### #17 保育園/幼稚園/学校求人 除外
- **ファイル**: `scripts/hellowork_to_d1.py`
- **変更**: `EXCLUDE_FACILITY_KEYWORDS` に `保育園`, `幼稚園`, `保育所`, `認定こども園`, `こども園`, `学校`, `小学校`, `中学校`, `高等学校`, `高校`, `特別支援学校` を登録。`employer` / `job_title` / `work_location` / `employer_address` / `industry` / `job_description[:300]` に含むレコードを除外。除外件数のサマリをSQLヘッダとstdoutに出力

#### #18 Dランク低品質求人 エリア15件以上時のみ除外
- **ファイル**: `api/worker.js` L4710-4743付近（D1 jobs検索）
- **変更**: D1 jobsテーブル検索時、まず同一エリア候補件数を `SELECT COUNT(*)` で取得。**15件以上のみ** `AND (rank IS NULL OR rank != 'D')` を追加適用。15件未満のエリアでは全件（D含む）残すことで「求人ゼロ」を回避

#### #19 クリニック検索時 departments フィルタbypass
- **ファイル**: `api/worker.js` L4724-4729（D1 jobs）/ L5024-5028（D1 facilities fallback）
- **変更**: `entry.facilityType === 'clinic'` または `entry._isClinic === true` の場合、`department` フィルタ（`LIKE '%${dept}%'`）をスキップ。クリニックは診療科メタデータが不足しているためフィルタで落ちる問題を解消

#### #26 緊急キーワード粒度調整（「限界」降格）
- **ファイル**: `api/worker.js` L6822-6823
- **変更**: `EMERGENCY_KEYWORDS` から `限界` を削除 → `URGENT_KEYWORDS` へ移動。EMERGENCYは即handoff遷移するが、URGENTはSlack通知のみで会話継続。多義的な「限界（仕事の限界/体力の限界/我慢の限界）」が即handoffになる過検知を抑止

---

## 禁止事項の確認

- **CTA色**: 全て緑（#06C755）維持。コーラル化なし ✓
- **個人名・社名**: HTML公開ページに未記載 ✓
- **金額・予算**: 未変更 ✓
- **ロゴ・デザイン素材**: 未変更 ✓
- **派遣求人**: #16で明示的に除外強化 ✓
- **カテゴリMIX比率**: 変更なし ✓
- **Meta広告設定**: 変更なし ✓
- **架空データ**: 生成していない ✓
- **React化・新規マッチングアルゴリズム**: なし ✓

## 変更ファイル

1. `/Users/robby2/robby-the-match/api/worker.js`（#6, #13, #18, #19, #26）
2. `/Users/robby2/robby-the-match/lp/job-seeker/index.html`（#12, #23, #24, #25, #28）
3. `/Users/robby2/robby-the-match/scripts/hellowork_to_d1.py`（#16, #17）

## 検証

- `node --check api/worker.js` → OK
- `python3 -m py_compile scripts/hellowork_to_d1.py` → OK
- Hero CTA色: `.cta-line-hero` は `linear-gradient(135deg, #06C755 0%, #05b34c 100%)` のまま
- 「いつでもブロックOK」: `index.html` で1箇所のみ（Final CTA, L1734）

## 次の担当（メイン）への注意事項

1. **Worker再デプロイ必須**: #6/#13/#18/#19/#26 の挙動反映には `cd api && unset CLOUDFLARE_API_TOKEN && npx wrangler deploy --config wrangler.toml` が必要。デプロイ後は `wrangler secret list --config wrangler.toml` で secrets 消失チェックを忘れず（`MEMORY.md` 参照）
2. **hellowork_to_d1.py の再実行**: #16/#17 は次回の `cron（06:30）→ hellowork_to_d1.py` 実行時から有効化。即時反映したい場合は手動で `python3 scripts/hellowork_to_d1.py` を実行し除外件数をログで確認
3. **#18 の COUNT(*) SQL コスト**: D1 jobs検索の冒頭で1回の COUNT 発行が増える。遅延が気になる場合はD1の `idx_jobs_area` / `idx_jobs_prefecture` インデックスで十分高速（既に設定済）
4. **#6 の welcomeIntent 分岐動作確認**: `welcome=see_salary` → `faq_salary`、`welcome=consult` → `handoff_phone_check` が既存分岐で対応済。フローテストでミサキ（28歳）視点の動作確認推奨
5. **#23 他のLP派生物**: `area/` `guide/` 配下のSEOページには同じ「いつでもブロックOK」が残存。LP-A改修スコープ外だが、後続タスクで統一する場合はメインエージェントが判断
6. **残りのグループ項目（#1-5, #7-11, #14-15, #20-22, #27）は別担当**: 本実装では対象外。戦略監督レポートの優先度順で実行推奨（特に #1 session_id復旧 / #2 AI try/catch / #3 Meta Pixel Lead はNS寄与度9-10でゲートキーパー級）
