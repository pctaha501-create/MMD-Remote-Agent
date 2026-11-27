-- Platform metadata for independently paired Windows and Linux agents.
ALTER TABLE devices ADD COLUMN os TEXT;
UPDATE devices SET os='windows' WHERE os IS NULL OR trim(os)='';
