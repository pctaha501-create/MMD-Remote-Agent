-- Session- and device-bound, count-limited auto-approval grants.
CREATE TABLE IF NOT EXISTS auto_approval_grants (
 id TEXT PRIMARY KEY,
 session_id TEXT NOT NULL,
 device_id TEXT NOT NULL,
 initial_count INTEGER NOT NULL,
 remaining_count INTEGER NOT NULL,
 created_at INTEGER NOT NULL,
 expires_at INTEGER NOT NULL,
 revoked_at INTEGER,
 updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_auto_approval_active
ON auto_approval_grants(session_id,device_id,revoked_at,expires_at);
ALTER TABLE jobs ADD COLUMN approval_grant_id TEXT;
CREATE TABLE IF NOT EXISTS auto_approval_events (
 id TEXT PRIMARY KEY,
 grant_id TEXT,
 session_id TEXT NOT NULL,
 device_id TEXT NOT NULL,
 job_id TEXT,
 event TEXT NOT NULL,
 created_at INTEGER NOT NULL,
 details TEXT
);
