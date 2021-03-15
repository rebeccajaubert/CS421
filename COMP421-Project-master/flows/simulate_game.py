from .flow_base import FlowBase
from datetime import timedelta
import random
import tabulate
import util.prompts as prompts
import util.sql as sql
import util.misc
import models
import itertools


GAME_TYPES = ['search-and-destroy', 'team-deathmatch', 'capture-the-flag']
MAPS = ['Rust', 'Verdun', 'Vimy Ridge']


class SimulateGame(FlowBase):
    prompt_text = "Simulate playing a game!"

    def select_teams_and_inventories(self):
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT username FROM players WHERE username <> %(username)s AND banned_date IS NULL",
                           {
                               "username": self.player.username
                           })
            other_player_usernames = [row[0] for row in cursor]
            choices = random.sample(other_player_usernames, k=3)

            teams = [
                {self.player.username, choices[0]},
                set(choices[1:])
            ]

        other_player_inventories = {}

        for username in other_player_usernames:
            inventories = models.Inventory.get_for_player(self.connection, username)
            other_player_inventories[username] = random.choice(inventories)

        random.shuffle(teams)
        return teams, other_player_inventories

    def initialize_game_session(self, teams, game_map, game_type, player_inventories):
        with self.connection.cursor() as cursor:
            insert_query = sql.insert_query(
                'game_sessions',
                ['game_type', 'map_name'],
                [(game_type, game_map)],
                return_fields=['*'])
            cursor.execute(insert_query)

            game_session = next(sql.objects(cursor))

            # Insert records into the plays table
            plays_tuples = []

            for i, team in enumerate(teams):
                for player in team:
                    plays_tuples.append(
                        (player, player_inventories[player].name, game_session.gid, i + 1)
                    )

            plays_insert_query = sql.insert_query(
                'plays',
                ('username', 'inventory_name', 'gid', 'team_number'),
                plays_tuples
            )
            cursor.execute(plays_insert_query)

        return game_session

    def choose_inventory(self):
        inventories = models.Inventory.get_for_player(self.connection, self.player.username)
        inventory_descriptions = [inventory.describe_current_inventory() for inventory in inventories]

        return prompts.select_from_list(
            inventories,
            inventory_descriptions,
            "Select an inventory to bring into the game.")

    def simulate_game_events(self, teams, game_session):
        players = list(itertools.chain(*teams))

        # Randomize what happens in the game
        kills = {
            p: 0 for p in players
        }
        deaths = {
            p: 0 for p in players
        }
        assists = {
            p: 0 for p in players
        }

        # Make a game 20 minutes in duration, have an even every 30 to 45 seconds
        game_duration = 20*60
        timestamp = random.gauss(60, 20)

        while timestamp < game_duration:

            team_with_kill = random.choice(teams)
            killer = random.choice(list(team_with_kill))
            other_team = [team for team in teams if team != team_with_kill][0]
            killed = random.choice(list(other_team))

            is_there_assist = random.random() > 0.5
            assister = [p for p in team_with_kill if p != killer][0]

            kills[killer] += 1
            deaths[killed] += 1

            print("%02d:%02d" % (timestamp / 60, timestamp % 60), end=') ')
            print("%s killed %s" % (killer, killed), end='')
            if is_there_assist:
                assists[assister] += 1
                print(' with an assist from %s' % assister)
            else:
                print()

            timestamp += int(random.gauss(40, 7))

        winning_team = util.misc.argmax(sum(kills[p] for p in team) for team in teams)

        print("20:00) Team %d won the game!" % (winning_team + 1))

        return kills, deaths, assists, winning_team + 1

    def update_player_kda(self, game_session, kills, deaths, assists):
        with self.connection.cursor() as cursor:
            for player in kills.keys():
                query = """
                    UPDATE plays 
                    SET
                      kills=%(kills)s, 
                      deaths=%(deaths)s, 
                      assists=%(assists)s 
                    WHERE 
                      gid=%(gid)s AND
                      username=%(username)s"""
                cursor.execute(query, {
                    "kills": kills[player],
                    "deaths": deaths[player],
                    "assists": assists[player],
                    "gid": game_session.gid,
                    "username": player
                })

    def run(self):
        print()
        print("Simulating a game!")

        teams, player_inventories = self.select_teams_and_inventories()
        print(tabulate.tabulate(teams, headers=["Team1", "Team2"]))
        print()

        game_map = random.choice(MAPS)
        game_type = random.choice(GAME_TYPES)

        print("Playing %s on the map: %s" % (game_type.replace("-", " "), game_map))
        print()

        inventory = self.choose_inventory()
        player_inventories[self.player.username] = inventory

        game_session = self.initialize_game_session(teams, game_map, game_type, player_inventories)
        kills, deaths, assists, winning_team = self.simulate_game_events(teams, game_session)

        self.update_player_kda(game_session, kills, deaths, assists)

        previous_level = self.player.level

        # Close out the game session using the close_game prepared statement.
        query = """
            SELECT * FROM close_game(%(gid)s, %(winning_team)s, %(game_end)s);
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, {
                "gid": game_session.gid,
                "winning_team": winning_team,
                "game_end": game_session.start_time + timedelta(minutes=20)
            })
            leaderboard = list(sql.objects(cursor))

        print("\nFinal leaderboard:")
        for team, players in itertools.groupby(leaderboard, key=lambda player: player.team_number):
            print("Team %d" % team)

            table = [
                [i + 1, player.username, player.kills, player.deaths, player.assists, player.exp_gained]
                for i, player in enumerate(players)
            ]

            print(tabulate.tabulate(table, headers=['Rank', 'Player', 'Kills', 'Deaths', 'Assists', 'XP Gain']))
            print()

        self.connection.commit()

        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT level, experience, exp_requirement(level) as req FROM players WHERE username=%(username)s", {
                    "username": self.player.username
                })
            updated_pts = next(sql.objects(cursor))

        exp_we_gained = [p.exp_gained for p in leaderboard if p.username == self.player.username][0]

        if updated_pts.level > previous_level:
            print("Congratulations, you've leveled up to %d!" % updated_pts.level)
            print("You have %d/%d experience points to reach level %d" %
                  (updated_pts.experience, updated_pts.req, updated_pts.level + 1))
        else:
            print("You gained %d experience points, you now have %d/%d experience points required to reach level %d" %
                  (exp_we_gained, updated_pts.experience, updated_pts.req, updated_pts.level + 1))
