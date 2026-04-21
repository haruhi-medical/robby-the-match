-- ナースロビー AIキャリアアドバイザー D1 スキーマ v0.1
-- 作成: 2026-04-21

-- 求職者テーブル
CREATE TABLE IF NOT EXISTS candidates (
  id TEXT PRIMARY KEY,
  display_name TEXT,
  phase TEXT NOT NULL DEFAULT 'new',
  turn_count INTEGER NOT NULL DEFAULT 0,
  axis TEXT,
  root_cause TEXT,
  profile_json TEXT,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_candidates_phase ON candidates(phase);
CREATE INDEX IF NOT EXISTS idx_candidates_updated_at ON candidates(updated_at);

-- 会話ログ
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  candidate_id TEXT NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  phase TEXT,
  turn_index INTEGER,
  tokens_used INTEGER,
  provider TEXT,
  created_at INTEGER NOT NULL,
  FOREIGN KEY (candidate_id) REFERENCES candidates(id)
);

CREATE INDEX IF NOT EXISTS idx_messages_candidate_id ON messages(candidate_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);

-- 応募履歴
CREATE TABLE IF NOT EXISTS applications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  candidate_id TEXT NOT NULL,
  facility_id TEXT,
  facility_name TEXT,
  job_title TEXT,
  status TEXT NOT NULL,
  recommendation_letter TEXT,
  applied_at INTEGER,
  interview_at INTEGER,
  offered_at INTEGER,
  accepted_at INTEGER,
  joined_at INTEGER,
  notes TEXT,
  FOREIGN KEY (candidate_id) REFERENCES candidates(id)
);

CREATE INDEX IF NOT EXISTS idx_applications_candidate_id ON applications(candidate_id);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);

-- 入職後フォロー
CREATE TABLE IF NOT EXISTS follow_ups (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  candidate_id TEXT NOT NULL,
  application_id INTEGER,
  trigger_at INTEGER NOT NULL,
  push_type TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'scheduled',
  sent_at INTEGER,
  response_at INTEGER,
  response_sentiment TEXT,
  response_text TEXT,
  FOREIGN KEY (candidate_id) REFERENCES candidates(id),
  FOREIGN KEY (application_id) REFERENCES applications(id)
);

CREATE INDEX IF NOT EXISTS idx_follow_ups_trigger ON follow_ups(trigger_at, status);

-- 人間引き継ぎログ
CREATE TABLE IF NOT EXISTS handoffs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  candidate_id TEXT NOT NULL,
  reason TEXT NOT NULL,
  urgency TEXT NOT NULL,
  phase TEXT,
  slack_channel TEXT,
  resolved_at INTEGER,
  resolution_notes TEXT,
  created_at INTEGER NOT NULL,
  FOREIGN KEY (candidate_id) REFERENCES candidates(id)
);

CREATE INDEX IF NOT EXISTS idx_handoffs_created_at ON handoffs(created_at);
