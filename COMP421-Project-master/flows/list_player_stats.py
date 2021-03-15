from .flow_base import FlowBase
import util.sql as sql
import tabulate


class ListPlayerStats(FlowBase):
    prompt_text = "List personal statistics about previous games."

    def get_recent_games(self):
        query = """
            WITH recent_games AS (
                SELECT plays.gid,
                       game_sessions.map_name,
                       game_sessions.game_type,
                       game_sessions.winning_team,
                       game_sessions.start_time,
                       game_sessions.end_time
                FROM plays
                         INNER JOIN game_sessions ON plays.gid = game_sessions.gid
                WHERE username = %(username)s
                ORDER BY start_time DESC
                LIMIT 5
            )
            SELECT inventory_name,
                   kills,
                   deaths,
                   assists,
                   map_name,
                   game_type,
                   team_number = winning_team as win,
                   start_time,
                   end_time
            FROM plays
            INNER JOIN recent_games
                ON plays.gid = recent_games.gid
            WHERE username = %(username)s;
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, {
                "username": self.player.username
            })
            game_stats = sql.objects(cursor)

            table = []
            for game in game_stats:
                outcome = 'Win' if game.win else 'Loss'
                start = game.start_time.strftime("%Y-%m-%d %H:%M:%S")
                duration_timedelta = game.end_time - game.start_time
                minutes = duration_timedelta.seconds // 60

                table.append(
                    [start, outcome, game.game_type, game.map_name, game.kills, game.deaths, game.assists,
                     '%.2f' % (game.kills / game.deaths), '%d minutes' % minutes]
                )

            print(tabulate.tabulate(
                table,
                ['Start Time', 'Outcome', 'Game Type', 'Map', 'Kills', 'Deaths', 'Assists', 'KDR', 'Duration']
            ))

    def get_inventory_stats(self):
        # Get the win rate by inventory (coalescing so that inventories that aren't used show up in the list)
        query = """
            SELECT 
                name, 
                coalesce(stats.kdr, 0) as kdr,  
                coalesce(stats.winrate, 0) as winrate, 
                coalesce(stats.games_played, 0) as games_played 
            FROM inventories
            LEFT JOIN (
                SELECT inventory_name,
                       round(sum(kills)::NUMERIC / sum(deaths)::NUMERIC, 2) as kdr,
                       round(
                                   (count(*) FILTER (WHERE game_sessions.winning_team = plays.team_number))::NUMERIC /
                                   count(*)::NUMERIC, 2
                           )                                                as winrate,
                       count(*)                                             AS games_played
                FROM plays
                         INNER JOIN game_sessions ON plays.gid = game_sessions.gid
                WHERE username = %(username)s
                GROUP BY inventory_name
            ) as stats ON inventories.name = stats.inventory_name
            WHERE username = %(username)s
            ORDER BY games_played DESC;
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, {
                "username": self.player.username
            })
            inventory_stats = list(sql.objects(cursor))

        overall_kdr = 0
        overall_winrate = 0
        total_games = 0

        for inventory_entry in inventory_stats:
            overall_kdr += inventory_entry.games_played * inventory_entry.kdr
            overall_winrate += inventory_entry.games_played * inventory_entry.winrate
            total_games += inventory_entry.games_played

        return inventory_stats, overall_kdr / total_games, overall_winrate / total_games, total_games

    def run(self):
        print("%s --- level: %d, experience: %d/%d" %
              (self.player.username, self.player.level, self.player.experience, self.player.exp_requirement))

        inventory_stats, overall_kdr, overall_winrate, total_games = self.get_inventory_stats()
        print("You've played %d games so far." % total_games)
        print("You've won %d games for a win rate of %.2f" % (overall_winrate * total_games, overall_winrate))
        print("Your average kill to death ratio (KDR) is %.2f" % overall_kdr, end='\n\n')

        print("Here are some stats about your inventories")
        table = []

        for inventory_entry in inventory_stats:
            if inventory_entry.games_played > 0:
                table.append(
                    [inventory_entry.name, inventory_entry.games_played, inventory_entry.kdr, inventory_entry.winrate]
                )
            else:
                table.append(
                    [inventory_entry.name, inventory_entry.games_played, 'N/A', 'N/A']
                )

        print(tabulate.tabulate(table, headers=('Inventory Name', 'KDR', 'winrate', 'Games Played')))

        print()
        print("Here are your most recent games")
        self.get_recent_games()
