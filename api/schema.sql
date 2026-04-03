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
