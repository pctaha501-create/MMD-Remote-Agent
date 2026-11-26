CREATE TABLE IF NOT EXISTS agent_pair_requests (code_hash TEXT PRIMARY KEY, secret_hash TEXT NOT NULL, session_id TEXT, created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL, used_at INTEGER);
CREATE INDEX IF NOT EXISTS idx_agent_pair_requests_expiry ON agent_pair_requests(expires_at);
CREATE TABLE IF NOT EXISTS agent_pair_attempts (ip_hash TEXT PRIMARY KEY, window_started_at INTEGER NOT NULL, attempts INTEGER NOT NULL DEFAULT 0);
