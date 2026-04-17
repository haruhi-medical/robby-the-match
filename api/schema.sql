-- ナースロビー 施設DB スキーマ
-- Cloudflare D1 (SQLite)

CREATE TABLE IF NOT EXISTS facilities (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  category TEXT,           -- 病院/クリニック/訪問看護ST/介護施設/健診センター/その他
  sub_type TEXT,           -- 急性期/慢性期/回復期/精神科/療養型
  prefecture TEXT NOT NULL,
  city TEXT,
  address TEXT,
  lat REAL,
  lng REAL,
  nearest_station TEXT,
  station_minutes INTEGER,
  bed_count INTEGER,
  departments TEXT,        -- カンマ区切り
  has_active_jobs INTEGER DEFAULT 0,
  active_job_count INTEGER DEFAULT 0,
  source TEXT DEFAULT 'egov_csv',
  last_synced_at TEXT
);

-- エリア検索用インデックス
CREATE INDEX IF NOT EXISTS idx_facilities_prefecture ON facilities(prefecture);
CREATE INDEX IF NOT EXISTS idx_facilities_lat_lng ON facilities(lat, lng);
CREATE INDEX IF NOT EXISTS idx_facilities_category ON facilities(category);
CREATE INDEX IF NOT EXISTS idx_facilities_has_jobs ON facilities(has_active_jobs);

-- 求人テーブル
CREATE TABLE IF NOT EXISTS jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  facility_id INTEGER,
  source TEXT DEFAULT 'hellowork',  -- hellowork/direct
  title TEXT,
  license_required TEXT,            -- 正看/准看/保健師/助産師
  work_style TEXT,                  -- 常勤/パート/夜勤専従
  shift_type TEXT,                  -- 日勤のみ/二交代/三交代
  salary_min INTEGER,
  salary_max INTEGER,
  bonus_text TEXT,
  holidays_per_year INTEGER,
  posted_at TEXT,
  expires_at TEXT,
  status TEXT DEFAULT 'active',
  last_synced_at TEXT,
  FOREIGN KEY (facility_id) REFERENCES facilities(id)
);

CREATE INDEX IF NOT EXISTS idx_jobs_facility ON jobs(facility_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_work_style ON jobs(work_style);

-- 非公開求人テーブル（Phase 3 #52）
-- 社長/担当者だけが把握する「表に出せない求人」を管理する。
-- LP/LINE には「🔒 非公開求人あり」バッジだけを出し、詳細はハンドオフ後に紹介する運用。
CREATE TABLE IF NOT EXISTS confidential_jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  facility_id INTEGER,              -- facilities.id への参照（NULL 可: 施設確定前の案件）
  facility_name TEXT,               -- 公開してよい場合の施設名（表示は社長が明示的に許可した時のみ）
  title TEXT,                       -- 社内向けタイトル（例: "急性期病棟 主任候補"）
  license_required TEXT,            -- 正看/准看/保健師 等
  work_style TEXT,                  -- 常勤/夜勤専従/パート
  shift_type TEXT,                  -- 日勤のみ/二交代/三交代
  salary_min INTEGER,
  salary_max INTEGER,
  note TEXT,                        -- 社内メモ（非公開、LINEには絶対出さない）
  status TEXT DEFAULT 'active',     -- active / paused / filled
  visibility TEXT DEFAULT 'badge_only',  -- badge_only / summary_ok / name_ok
  area_tag TEXT,                    -- yokohama_kawasaki 等のエリアタグ（バッジ出し分け用）
  prefecture TEXT,
  posted_at TEXT,
  expires_at TEXT,
  last_synced_at TEXT,
  FOREIGN KEY (facility_id) REFERENCES facilities(id)
);

CREATE INDEX IF NOT EXISTS idx_confidential_facility ON confidential_jobs(facility_id);
CREATE INDEX IF NOT EXISTS idx_confidential_status ON confidential_jobs(status);
CREATE INDEX IF NOT EXISTS idx_confidential_area ON confidential_jobs(area_tag);
CREATE INDEX IF NOT EXISTS idx_confidential_pref ON confidential_jobs(prefecture);

-- #51 Phase 3: LINE Bot フェーズ遷移ログ（どこで離脱が多いかを可視化）
-- 保存粒度: userIdハッシュ化済 + prev_phase + next_phase + event + timestamp
-- 週次レポート（scripts/phase_transition_weekly_report.py）が Slack 送信
CREATE TABLE IF NOT EXISTS phase_transitions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_hash TEXT NOT NULL,          -- userId の先頭12文字（PII回避）
  prev_phase TEXT,                   -- 遷移前の phase（null可）
  next_phase TEXT NOT NULL,          -- 遷移後の phase
  event_type TEXT,                   -- postback/text/follow/ai_consult など
  area TEXT,                         -- 遷移時の area
  prefecture TEXT,                   -- 遷移時の prefecture
  urgency TEXT,                      -- 遷移時の urgency
  work_style TEXT,                   -- 遷移時の workStyle
  facility_type TEXT,                -- 遷移時の facilityType
  source TEXT,                       -- welcomeSource（hero/sticky/bottom/shindan/none等）
  created_at TEXT NOT NULL           -- ISO8601 UTC
);

CREATE INDEX IF NOT EXISTS idx_pt_created_at ON phase_transitions(created_at);
CREATE INDEX IF NOT EXISTS idx_pt_next_phase ON phase_transitions(next_phase);
CREATE INDEX IF NOT EXISTS idx_pt_user_hash ON phase_transitions(user_hash);
