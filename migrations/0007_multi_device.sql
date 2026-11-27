-- Multiple independently selectable agents and device-scoped command queues.
ALTER TABLE devices ADD COLUMN name TEXT;
ALTER TABLE jobs ADD COLUMN device_id TEXT;
UPDATE jobs SET device_id=(SELECT d.id FROM devices d WHERE d.session_id=jobs.owner_session_id ORDER BY d.paired_at DESC LIMIT 1) WHERE device_id IS NULL AND owner_session_id IS NOT NULL;
UPDATE devices SET name='Windows '||substr(id,1,6) WHERE name IS NULL OR trim(name)='';
CREATE INDEX IF NOT EXISTS idx_jobs_device_queue ON jobs(device_id,status,created_at);
CREATE INDEX IF NOT EXISTS idx_devices_session_paired ON devices(session_id,paired_at);
