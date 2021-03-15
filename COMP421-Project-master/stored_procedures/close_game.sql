-- Returns the experience required to level up based on the current level, the formula is 1000 * sqrt(player level)
CREATE OR REPLACE FUNCTION exp_requirement(plevel INTEGER)
RETURNS INTEGER
AS $$
DECLARE
    base_level_up_exp INTEGER := 1000;
BEGIN
    RETURN round(sqrt(plevel) * base_level_up_exp)::INTEGER;
END;
$$
LANGUAGE plpgsql;

-- Closes a game session and updates the experience of the participants.
CREATE OR REPLACE FUNCTION close_game(session_gid INTEGER, winning_team_nb INTEGER, game_end_time TIMESTAMP)
    -- Returns a leaderboard of players in the game and their performances
    RETURNS TABLE (
        username VARCHAR,
        kills INTEGER,
        deaths INTEGER,
        assists INTEGER,
        team_number INTEGER,
        exp_gained INTEGER
    )
AS $$
DECLARE
    win_exp INTEGER := 250;
    loss_exp INTEGER := 100;
BEGIN
    -- Close the game session
    UPDATE game_sessions
    SET
      winning_team=winning_team_nb,
      end_time=game_end_time
    WHERE
      gid=session_gid;

    -- Update the experience of the players that participated in the game
    -- If necessary we level them up
    UPDATE players
    SET
        --
        experience = CASE WHEN experience + participants.exp_gain >= exp_requirement(players.level) THEN
                            -- Carry over any leftover experience, level will be incremented
                            experience + participants.exp_gain - exp_requirement(players.level)
                          ELSE
                            -- Simply add the exp gain to experience
                            experience + participants.exp_gain
                          END,
        level = CASE WHEN experience + participants.exp_gain >= exp_requirement(players.level) THEN
                       -- Increment level
                       level + 1
                     ELSE
                       -- Don't increment level
                       level
                     END
    FROM (
        SELECT
          players_wins.username,
          CASE WHEN win THEN win_exp
          ELSE loss_exp
          END AS exp_gain
        FROM (
            SELECT plays.username, plays.team_number = game_sessions.winning_team as win FROM plays
            INNER JOIN game_sessions on plays.gid = game_sessions.gid
            WHERE plays.gid = session_gid
        ) AS players_wins
    ) AS participants
    WHERE players.username = participants.username;

    RETURN QUERY
        SELECT
            plays.username,
            plays.kills,
            plays.deaths,
            plays.assists,
            plays.team_number,
            CASE WHEN plays.team_number = winning_team_nb THEN
                   win_exp
                 ELSE
                   loss_exp
                 END as exp_gained
        FROM plays
        WHERE plays.gid = session_gid
        ORDER BY
          -- Coerces it so that the winning team's players are shown first in the output, since this field has
          -- A boolean output and True > False
          plays.team_number = winning_team_nb DESC,
          plays.kills DESC,
          plays.deaths,
          plays.assists DESC;
END;
$$
LANGUAGE plpgsql;
