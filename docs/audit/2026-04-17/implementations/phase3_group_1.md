# Phase 3 Group 1 — SEO/LP/基盤 8項目 実装記録

**実施日**: 2026-04-17
**担当**: Claude（Phase 3 実装エージェント）
**対象**: #52 / #54 / #55 / #56 / #57 / #58 / #61 / #63
**ブランチ**: 作業用（git commit なし）

---

## 完了状態（8件）

| # | 項目 | 状態 | 備考 |
|---|-----|------|------|
| 52 | 非公開求人テーブル + バッジ | ✅ 完了 | D1スキーマ追加、worker.js でバッジ自動表示。データ投入は社長対応 |
| 54 | criticalCSS分離で LCP 改善 | ✅ 完了 | Hero+TrustBar分のみ inline 維持、残りを `index-deferred.css` へ外部化 |
| 55 | Hero画像テキスト → HTML オーバーレイ | ✅ 完了 | `<h1>`/`<p>` を可視化、画像は `alt=""` の装飾扱い |
| 56 | プログレスバー「1/5」ラベル | ✅ 完了 | 「質問 1/5」と aria-valuetext / aria-live 追加 |
| 57 | E-E-AT強化（許可番号・編集方針・著者） | ✅ 完了 | docs/editorial_policy.md 新設・Org JSON-LD に credentials / publishingPrinciples |
| 58 | 競合ベンチマーク取得 + cron化 | ✅ 完了 | 実HTTP取得。Google site: 件数は取得不可 → 手動確認リスト出力 |
| 61 | content/generated/ 月次アーカイブ | ✅ 完了 | 30日以上前を .tar.gz 化。dry-run で 42候補・~530MB対象確認 |
| 63 | Slack送信失敗時の alert_queue.json | ✅ 完了 | slack_utils.py でenqueue、slack_retry.py が30分毎にretry、3回失敗で削除 |

---

## 変更ファイル一覧

### 新規作成
- `api/schema.sql` （`confidential_jobs` テーブル+4インデックス追記）
- `lp/job-seeker/index-deferred.css` （866行、非クリティカルCSS）
- `docs/editorial_policy.md` （編集方針本体）
- `scripts/competitor_benchmark.py`
- `scripts/archive_generated.py`
- `scripts/slack_retry.py`
- `data/competitor_benchmark.json` / `data/competitor_manual_check.md`（初回実行で生成済）

### 編集
- `api/worker.js` (5190+: `facility_id` をD1フォールバック結果に付与、5253以降: 非公開求人バッジ判定、buildFacilityFlexBubble ヘッダにバッジ追加)
- `lp/job-seeker/index.html` （Hero書き換え / criticalCSS分離 / editorial-policy リンク / Organization JSON-LD 強化 / footer 編集部クレジット）
- `lp/job-seeker/shindan.js` （progress bar ARIA + 「質問 X/5」明示）
- `lp/job-seeker/shindan.css` （progress-label 幅拡大）
- `scripts/slack_utils.py` （ALERT_QUEUE_FILE / _enqueue_alert / send_message の最終失敗時enqueue）
- `scripts/notify_slack.py` （失敗時に slack_utils の enqueue を呼ぶ）
- `blog/index.html` + `blog/*.html` 18記事 （BlogPosting JSON-LD に publishingPrinciples、footer に編集部リンク）

---

## 構文チェック

| 対象 | コマンド | 結果 |
|------|----------|------|
| worker.js | `node --check` | OK |
| shindan.js | `node --check` | OK |
| schema.sql | `sqlite3 :memory: < schema.sql` | OK |
| LP index.html + 18 blog JSON-LD | 独自 parse | 全てOK |
| LP index.html | `html.parser` | OK |
| Python 3本 + slack_utils + notify_slack | `python3 -m py_compile` | OK |

---

## Lighthouse 見込みスコア変化

**注**: 実測はしていない（localhost ビルドなし、本番 push もしていない）。
以下はコード変更から推定する**定性評価**。

### #54 criticalCSS 分離
- `<style>` 内部CSS: 約1220行 → 353行（-870行、~29KB 削減）
- 残りは `index-deferred.css`（866行、media=print swap-to-all で非ブロッキング）
- 見込み: **LCP 300-800ms 改善**（特にモバイル3G相当）。FCP も約100ms 改善見込み
- Lighthouse Performance: 既存 ~65 → **~75-80 予想**（⚠️ 未実測、要Lighthouse実行）

### #55 Hero画像テキスト → HTMLオーバーレイ
- `alt=""` + `role="presentation"` で画像を装飾扱いに。`<h1>` が可視化
- 見込み: **Accessibility スコア +3〜5pt**、SEO `<h1>` 実体化で Indexability 改善
- 画像サイズは同じなので LCP 直接変化なし（FCP 微増の可能性あり: テキスト描画分）

**共通**: 既存デザインは維持（フォント Noto Sans JP / 色は CSS 変数のまま / CTA緑維持）。

---

## #57 許可番号・編集方針・著者

- **許可番号**: `23-ユ-302928`（FACT_PACK.md に明記の通り、既存 LP にも記載あり）
- **編集方針ページ**: `https://quads-nurse.com/about/editorial-policy.html`（既存、社長が2月に構築）
- **著者**: `神奈川ナース転職編集部`（JSON-LD BlogPosting.author / meta name=author / footer）
- **LP Organization JSON-LD に追加**:
  - `hasCredential` → `EducationalOccupationalCredential` で許可番号を構造化
  - `publishingPrinciples` / `ethicsPolicy` → editorial-policy.html 指定
- **「平島禎之」「はるひメディカルサービス」の露出**: LP / blog / scripts 公開ページに**なし**（grep確認済）

---

## #58 競合ベンチマーク 実取得結果

| 競合 | Google `site:` 件数 | robots.txt | sitemap.xml | トップページtitle取得 | 許可番号検出 |
|------|---------------------|-----------|-------------|----------------------|--------------|
| レバウェル看護 | ❌ 取得不可 | ✅ 3424B | ✅ 25 loc | ✅ | `13-ユ-309623` |
| マイナビ看護師 | ❌ 取得不可 | ✅ 1122B | ❌ 404 | ✅ | ─ |
| ナース人材バンク | ❌ 取得不可 | 実行時取得可（ログ参照） | 実行時取得可 | ✅ | ─ |

- Google検索の `site:` 件数は HTML 構造/bot ガードで pattern 未検出 → `not_available` として扱い `data/competitor_manual_check.md` に手動確認タスクを列挙
- **ドメインレーティング相当（Ahrefs DR / SimilarWeb Rank）は有料APIのため未取得**。手動確認推奨に留める
- 架空データは一切注入していない（実装の run() 内で取得失敗 = `status: not_available` のまま保存）
- cron推奨: `0 4 1 * *`（月1日04:00、SlackサマリはPRで --cron 付き実行）

---

## 未解決・懸念

1. **#52 実データ投入**: `confidential_jobs` は空のまま。社長/担当者が SQL INSERT する運用設計が別途必要。UI 上は 0件時に何も表示されないため害はない
2. **#54 Lighthouse 未実測**: 本番 push 前のためスコアは推定値。デプロイ後に `lighthouse https://quads-nurse.com/lp/job-seeker/` で実測推奨
3. **#55 Hero 画像**: 既存画像には文字焼き込みが残っている。画像差し替え（文字なし背景のみ版）は別タスク（社長デザイン判断待ち）。現状は画像+HTMLテキスト重複が視覚的に起きる可能性あり → 画像側の文字はそのまま装飾として許容、HTMLテキストは画像下部に配置することで重複回避
4. **#58 Google site: 件数**: UI変更に脆弱。将来的には手動 GSC (Search Console) の平均掲載順位取得に切り替えるのが現実的
5. **#63 alert_queue.json サイズ**: 無制限に増えないよう 3 retry 上限で削除しているが、send頻度が高い場合は別途ローテート検討要
6. **既存 /about/editorial-policy.html**: 内容は既存のまま。`docs/editorial_policy.md` は Markdown 版として新設した（社内参照用）。HTML側との整合性は別途レビュー推奨

---

## git commit について

指示通り **git commit はしていない**。全ファイルが作業ツリーに残っている状態。
`git status` で差分確認後、社長承認を経てコミットすること。
