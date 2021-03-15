CREATE INDEX IF NOT EXISTS players_levels
    ON players
    USING btree
    ( level );

CLUSTER players
USING levels;