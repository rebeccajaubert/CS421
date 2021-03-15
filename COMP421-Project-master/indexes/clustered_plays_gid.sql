
CREATE INDEX IF NOT EXISTS plays_gid ON plays
USING btree
(gid);

CLUSTER plays USING plays_gid
