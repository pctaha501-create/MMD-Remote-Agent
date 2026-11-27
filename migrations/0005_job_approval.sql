-- Atomic, one-time approval for each MCP job.
ALTER TABLE jobs ADD COLUMN approval_status TEXT NOT NULL DEFAULT 'pending';
ALTER TABLE jobs ADD COLUMN approval_source TEXT;
