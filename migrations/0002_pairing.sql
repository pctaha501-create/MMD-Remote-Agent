CREATE TABLE IF NOT EXISTS browser_sessions (id TEXT PRIMARY KEY, created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS pair_codes (code_hash TEXT PRIMARY KEY, session_id TEXT NOT NULL, expires_at INTEGER NOT NULL, used_at INTEGER);
CREATE TABLE IF NOT EXISTS devices (id TEXT PRIMARY KEY, session_id TEXT NOT NULL, token_hash TEXT NOT NULL UNIQUE, state TEXT NOT NULL DEFAULT 'stopped', paired_at INTEGER NOT NULL, last_seen INTEGER NOT NULL, version TEXT);
CREATE INDEX IF NOT EXISTS idx_pair_codes_expiry ON pair_codes(expires_at);
CREATE INDEX IF NOT EXISTS idx_devices_session ON devices(session_id);
