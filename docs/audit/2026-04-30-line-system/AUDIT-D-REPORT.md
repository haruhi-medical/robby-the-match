# スキーマ・cron設計（D群）

**作成日**: 2026-04-30
**位置づけ**: aica構想を実装に落とすための DDL 案＋移行手順
**前提**: D1既存テーブル（facilities/jobs/confidential_jobs/phase_transitions）は維持。新規4テーブルを追加

---

## サマリ

| # | 課題 | 対応 |
|---|---|---|
| D1 | candidates DDL | api-aica/schema.sql の草案を本番D1に適用＋ALTER追加 |
| D2 | applications DDL | 同上＋status遷移マシン定義 |
| D3 | KV ⇄ D1 責務分離 | KV=セッション/フラグ（揮発性）、D1=候補者プロファイル/応募/メッセージ（永続性） |
| D4 | cron 衝突回避 | Worker scheduled `*/15 * * * *` で follow_ups poll、既存21cron との時間帯分離 |
| D5 | PDF生成 | Workers無料枠ではOOM懸念。Browser Rendering API（有料）or HTML+png変換+R2推奨 |

---

## D1. candidates テーブル DDL

### 既存草案（`api-aica/schema.sql`）の問題点
- カラム不足（aica-conversation-flow.md で言及される項目が網羅されていない）
- インデックス不足（line_user_id検索に必要）
- 個人情報暗号化の方針未定

### 推奨DDL

```sql
-- ============================================
-- 求職者テーブル v2.0（D1運用想定）
-- ============================================
CREATE TABLE IF NOT EXISTS candidates (
  id TEXT PRIMARY KEY,                       -- LINE userId をそのまま使用 (例: "U1234abcd...")
  display_name TEXT,                         -- LINE表示名

  -- フェーズ管理
  phase TEXT NOT NULL DEFAULT 'new',         -- aica_turn1, condition_hearing, matching, applied, etc.
  prev_phase TEXT,                           -- 直前フェーズ（離脱分析用）
  turn_count INTEGER NOT NULL DEFAULT 0,     -- 4ターンヒアリングのカウント

  -- AICA 心理ヒアリング結果
  axis TEXT,                                 -- time/relationship/salary/career/family/vague/emergency
  root_cause TEXT,                           -- AI抽出の根本原因（free text）
  summary_json TEXT,                         -- {pain_points, must_have_conditions, nice_to_have}

  -- 条件カルテ（CONDITION_HEARING）
  experience_years INTEGER,                  -- 看護師経験年数
  desired_prefecture TEXT,                   -- 希望勤務地（都道府県）
  desired_city TEXT,                         -- 希望勤務地（市区町村）
  desired_facility_type TEXT,                -- 急性期/回復期/慢性期/クリニック/訪問看護/施設
  desired_salary_min INTEGER,                -- 希望年収下限（万円）
  desired_salary_max INTEGER,                -- 希望年収上限
  desired_start_timing TEXT,                 -- 即/3M以内/半年以内/未定
  profile_json TEXT,                         -- 拡張用JSON（追加質問の回答等）

  -- マッチング結果
  presented_jobs_json TEXT,                  -- [{job_id, score, presented_at}]
  favorited_jobs_json TEXT,                  -- [{job_id, favorited_at}]

  -- 個人情報（APPLY_INFO以降のみ取得・暗号化推奨）
  full_name TEXT,                            -- 氏名 ※暗号化検討
  full_name_kana TEXT,                       -- フリガナ
  birth_date TEXT,                           -- YYYY-MM-DD ※暗号化検討
  phone TEXT,                                -- 電話番号 ※暗号化検討
  email TEXT,                                -- メール
  current_workplace TEXT,                    -- 現職場名
  license_acquired TEXT,                     -- 看護師免許取得年
  school_name TEXT,                          -- 出身校
  work_history_json TEXT,                    -- [{employer, period, role}]
  certifications_json TEXT,                  -- ["BLS", "認定看護師(緩和ケア)"]
  strengths_text TEXT,                       -- AI抽出の強み3点

  -- 同意・プライバシー
  privacy_consent_at INTEGER,                -- 個人情報取扱同意のタイムスタンプ
  marketing_consent BOOLEAN DEFAULT FALSE,

  -- メタ
  source TEXT,                               -- 流入元: ad_meta/seo/sns/direct
  utm_campaign TEXT,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,

  -- 沈黙・離脱
  last_user_message_at INTEGER,              -- 最後のユーザー発言時刻
  silence_alert_24h_sent BOOLEAN DEFAULT FALSE,
  silence_alert_3d_sent BOOLEAN DEFAULT FALSE,
  paused_at INTEGER                          -- PAUSED状態への遷移時刻（14日無応答）
);

CREATE INDEX IF NOT EXISTS idx_candidates_phase ON candidates(phase);
CREATE INDEX IF NOT EXISTS idx_candidates_updated_at ON candidates(updated_at);
CREATE INDEX IF NOT EXISTS idx_candidates_last_msg ON candidates(last_user_message_at);
CREATE INDEX IF NOT EXISTS idx_candidates_source ON candidates(source);
```

### 移行手順

```bash
# 1. ローカルで動作確認
cd ~/robby-the-match/api
unset CLOUDFLARE_API_TOKEN
npx wrangler d1 execute nurse-robby-db --config wrangler.toml --local \
  --file=migrations/0001_candidates.sql

# 2. 本番適用（dry-run）
npx wrangler d1 execute nurse-robby-db --config wrangler.toml --remote --dry-run \
  --file=migrations/0001_candidates.sql

# 3. 本番適用
npx wrangler d1 execute nurse-robby-db --config wrangler.toml --remote \
  --file=migrations/0001_candidates.sql

# 4. KV からの移行（既存ユーザー）
node scripts/migrate_kv_to_d1_candidates.js
```

---

## D2. applications テーブル DDL

### Status遷移マシン

```
applied → interview_scheduled → interview_done → result_waiting
       ↓                                                ↓
   (キャンセル)                                  ┌─ offer → negotiation → accepted
                                                  ├─ rejected
                                                  └─ withdrawn
                            accepted → resignation_prep → resignation_in_progress
                                    → resignation_done → pre_onboard → onboarded → stable
```

### 推奨DDL

```sql
CREATE TABLE IF NOT EXISTS applications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  candidate_id TEXT NOT NULL,
  facility_id INTEGER,                       -- D1.facilities.id への外部参照
  facility_name TEXT NOT NULL,               -- スナップショット
  job_id INTEGER,                            -- D1.jobs.id への外部参照
  job_title TEXT,
  
  status TEXT NOT NULL CHECK(status IN (
    'applied', 'interview_scheduled', 'interview_done', 'result_waiting',
    'offer', 'negotiation', 'accepted', 'rejected', 'withdrawn',
    'resignation_prep', 'resignation_in_progress', 'resignation_done',
    'pre_onboard', 'onboarded', 'stable', 'churned'
  )),
  
  -- 重要日時
  applied_at INTEGER,                        -- 応募送信
  interview_at INTEGER,                      -- 面接日時
  interview_done_at INTEGER,                 -- 面接終了
  offered_at INTEGER,                        -- 内定通知
  accepted_at INTEGER,                       -- 承諾
  resignation_announced_at INTEGER,          -- 退職届提出
  joined_at INTEGER,                         -- 入職
  stabilized_at INTEGER,                     -- 90日定着
  
  -- 文書
  recommendation_letter TEXT,                -- AI生成推薦文（社長承認済）
  resume_pdf_url TEXT,                       -- R2のPDF URL
  cv_pdf_url TEXT,
  
  -- 交渉
  offer_conditions_json TEXT,                -- {salary, bonus, holidays, ...}
  negotiation_log_json TEXT,                 -- AI生成交渉文の履歴
  
  notes TEXT,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  
  FOREIGN KEY (candidate_id) REFERENCES candidates(id)
);

CREATE INDEX IF NOT EXISTS idx_applications_candidate_id ON applications(candidate_id);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
CREATE INDEX IF NOT EXISTS idx_applications_facility_id ON applications(facility_id);

-- ステータス変更履歴
CREATE TABLE IF NOT EXISTS application_status_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  application_id INTEGER NOT NULL,
  prev_status TEXT,
  next_status TEXT NOT NULL,
  changed_at INTEGER NOT NULL,
  changed_by TEXT,                           -- 'ai' / 'human:robby2' / 'cron'
  notes TEXT,
  FOREIGN KEY (application_id) REFERENCES applications(id)
);

CREATE INDEX IF NOT EXISTS idx_status_history_app ON application_status_history(application_id);
```

---

## D3. KV ⇄ D1 責務分離

### 現状（KV のみ運用）

```
LINE_SESSIONS KV:
├─ line:{userId}                  → メイン状態（phase, messages, profile_json...）
├─ ver:{userId}                   → KVバージョン
├─ member:{userId}                → 会員フラグ
├─ member:{userId}:resume         → 履歴書ドラフト
├─ member:{userId}:favorites      → お気に入り求人
├─ newjobs_notify:{userId}        → 新着通知設定
└─ waitlist:{userId}              → 順番待ち
```

### 提案: 責務分離

| 役割 | 保管先 | 理由 |
|---|---|---|
| **セッション直近状態**（最新メッセージ・現在phase） | KV `line:{userId}` | 高速読み書き、TTL不要 |
| **候補者プロファイル**（個人情報・条件・履歴） | D1 candidates | 集計・検索・退会対応 |
| **メッセージ全履歴** | D1 messages | 監査・QA・分析用 |
| **応募履歴** | D1 applications | 病院別集計・KPI測定 |
| **お気に入り** | KV または D1 favorites | 中間。当面KV、後にD1へ |
| **一時フラグ**（未読Slack数等） | KV（短期TTL） | 揮発性で十分 |

### 二重書き込み戦略（移行期）

```javascript
// KV と D1 両方に書き込み（D1優先・KVは互換維持）
async function saveCandidateState(userId, state, env) {
  // D1 (永続)
  await env.DB.prepare(`
    UPDATE candidates SET phase = ?, updated_at = ?, ... WHERE id = ?
  `).bind(state.phase, Date.now(), userId).run();
  
  // KV (互換・高速読み出し用キャッシュ)
  await env.LINE_SESSIONS.put(`line:${userId}`, JSON.stringify(state), {
    expirationTtl: 7 * 24 * 60 * 60  // 7日
  });
}
```

→ 既存worker.jsの読み出しロジック（`line:{userId}` 参照）は**そのまま動く**。書き込み時にD1にも複製。

---

## D4. cron 衝突回避

### 既存21cron（crontab）

```
00:00  ─
04:00  pdca_seo_batch.sh
05:00  pdca_weekly_content.sh (日曜のみ)
06:00  pdca_ai_marketing.sh / pdca_weekly.sh (日曜)
07:00  pdca_healthcheck.sh
10:00  pdca_competitor.sh
12:00  instagram_engage.py / pdca_sns_post.sh
15:00  pdca_content.sh
16:00  pdca_quality_gate.sh
17:00  pdca_sns_post.sh
18:00  pdca_sns_post.sh
20:00  pdca_sns_post.sh
21:00  pdca_sns_post.sh / Instagram投稿
23:00  pdca_review.sh
*/30   watchdog.py
```

### 既存Worker scheduled

```
api/wrangler.toml: crons = ["0 1 * * *", "*/15 * * * *"]
  - 0 1 * * *      → 毎日01:00 (UTC前日 16:00) - データクリーニング想定
  - */15 * * * *  → 15分毎 - 待機中Push処理
```

### aica追加分の cron 設計

**方針**: 新規 macOS crontab を増やさず、Worker scheduled の `*/15 * * * *` で全部処理。`follow_ups` テーブル方式。

```sql
CREATE TABLE IF NOT EXISTS follow_ups (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  candidate_id TEXT NOT NULL,
  application_id INTEGER,
  trigger_at INTEGER NOT NULL,               -- 発火予定時刻 (Unix ms)
  push_type TEXT NOT NULL,                   -- 'silence_24h', 'silence_3d', 'silence_14d_pause',
                                             --  'interview_3d_before', 'interview_day_morning',
                                             --  'interview_done_eve', 'onboard_d1', 'onboard_d3',
                                             --  'onboard_d7', 'onboard_d30', 'onboard_d90'
  status TEXT NOT NULL DEFAULT 'scheduled',  -- 'scheduled', 'sent', 'failed', 'cancelled'
  sent_at INTEGER,
  attempt_count INTEGER DEFAULT 0,
  payload_json TEXT,                         -- カスタムメッセージ用
  FOREIGN KEY (candidate_id) REFERENCES candidates(id)
);

CREATE INDEX IF NOT EXISTS idx_follow_ups_trigger ON follow_ups(trigger_at, status);
```

```javascript
// worker.js scheduled handler の追記
async scheduled(event, env, ctx) {
  if (event.cron === "*/15 * * * *") {
    // 既存処理 + aica follow_ups poll
    const now = Date.now();
    const due = await env.DB.prepare(`
      SELECT * FROM follow_ups
      WHERE status = 'scheduled' AND trigger_at <= ?
      LIMIT 50
    `).bind(now).all();
    
    for (const f of due.results) {
      try {
        await sendFollowUpPush(f, env);
        await env.DB.prepare(`UPDATE follow_ups SET status='sent', sent_at=? WHERE id=?`)
          .bind(now, f.id).run();
      } catch (e) {
        await env.DB.prepare(`UPDATE follow_ups SET attempt_count=attempt_count+1 WHERE id=?`)
          .bind(f.id).run();
      }
    }
  }
}
```

### 衝突リスクと回避

| 既存cron | 新規aica処理 | 衝突 | 対策 |
|---|---|---|---|
| pdca系 (4-23時) | follow_ups Push | ❌ なし（独立） | - |
| sns_post 17/18/20/21時 | interview/onboard Push | ⚠️ LINE側で同ユーザーへの集中 | `follow_ups.payload_json` でユーザー別レート制限（同userIdに15分以内に複数Pushしない） |
| watchdog */30 | scheduled */15 | ❌ なし | - |
| scheduled */15 | follow_ups poll | ❌ なし（同一処理内） | - |

→ 既存21cron との衝突なし。Worker scheduled で完結。

---

## D5. PDF生成（aica §フェーズ12）

### Workers の制約
- CPU時間: Free 10ms / Paid 50ms（30秒バーストあり）
- メモリ: 128MB
- 直接 pdf-lib で履歴書PDF（複数ページ・画像埋込）生成は **OOM/タイムアウトリスクあり**

### 選択肢

| 案 | 実装 | コスト | 速度 | 推奨度 |
|---|---|---|---|---|
| **(a) Browser Rendering API**（Cloudflare有料機能） | HTMLテンプレ→PDF変換 | $5/月+ | 高速 | ★★★★ |
| (b) HTML→Canvas→PNG→PDF（Workers内） | HTMLレイアウト+react-pdf-renderer互換 | 無料 | 中（OOMリスク） | ★★ |
| (c) 外部サービス（Browserless, PDFShift） | API call | $9-29/月 | 高速 | ★★★ |
| (d) Mac Mini ローカル生成 | Puppeteer + cron | 0円 | 遅延あり（Workersから呼べない） | ★ |
| (e) PDF生成自体を遅延（応募時のみ） | 候補者プレビューはHTML、応募確定時のみPDF | - | - | ★★★★ |

### 推奨

**(a) Browser Rendering API + (e) 遅延生成 のハイブリッド**:
- 候補者には**HTMLプレビュー**（リアルタイム表示）
- 病院送付時に**Browser Rendering APIでPDF化**（社長承認後・1日数件想定）
- R2に保存（1時間TTLは短すぎる、推奨は **30日TTL**）

```javascript
// 病院送付時のPDF生成
const browser = await env.BROWSER.fetch(htmlUrl);
const pdf = await browser.pdf();
const r2Key = `resumes/${candidateId}_${Date.now()}.pdf`;
await env.PDF_BUCKET.put(r2Key, pdf, {
  customMetadata: { candidate_id: candidateId },
  httpMetadata: { contentType: 'application/pdf' }
});
const signedUrl = await env.PDF_BUCKET.createPresignedUrl(r2Key, 60 * 60 * 24 * 30);
```

### 制限・注意

- Browser Rendering API は **Cloudflare Workers Paid Plan** 必須（$5/月）
- PDFには個人情報含むため、**署名付きURL（Pre-signed URL）必須**
- 平文URLでR2公開は厳禁
- R2 GETに認証ヘッダー入れるか、Workers経由で配信

---

## まとめ: 推奨実装順序

| 優先度 | タスク | 工数 | 影響 |
|---|---|---|---|
| **P0** | candidates テーブル作成＋移行スクリプト | 1日 | aica前提崩壊の解消 |
| **P0** | applications テーブル作成 | 0.5日 | 応募管理の永続化 |
| **P1** | KV→D1 二重書き込み実装 | 1日 | 既存worker.js互換維持 |
| **P1** | follow_ups テーブル + Worker scheduled拡張 | 1日 | 沈黙Push・面接フォロー実装 |
| **P2** | Browser Rendering API 契約＋PDF生成 | 0.5日 | 履歴書PDF実装 |
| **P2** | application_status_history (監査用) | 0.5日 | 状態遷移トレース |

**総工数: 4.5日**

### 実装着手前の社長判断事項

- [ ] 個人情報の暗号化方針（KMS/AESどちらで何を暗号化するか）
- [ ] Browser Rendering API契約（$5/月追加OKか）
- [ ] R2バケット作成OKか
- [ ] 既存KVのデータをD1に移行するか、新規ユーザーのみD1運用か
