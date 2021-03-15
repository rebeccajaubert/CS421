CREATE INDEX IF NOT EXISTS players_guilds ON players
USING btree
(guild_name);