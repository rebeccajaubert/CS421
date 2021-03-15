import database
import util.sql
import math
import random
import itertools
from datetime import datetime, timedelta


GAME_TYPES = ['search-and-destroy', 'team-deathmatch', 'capture-the-flag']
MAPS = ['Rust', 'Verdun', 'Vimy Ridge']

PLAYERS_PER_TEAM = 2
TEAMS = 2

PLAYER_TIERS = {
    'gabriel': 2,
    'yunus': 2,
    'owen': 2,
    'rebecca': 2,
    'dimdim75': 1,
    'conduit420': 1,
    'inesK22': 1,
    'gadu94zer': 1,
    'rouDouBreh': 0,
    'zingalax': 0,
    'lyrink': 0,
    'jokazer': 0,
    'pestoHu94': 0,
    'mamounek': 0,
}

GAMES_TO_MAKE = 125

START_DATE = datetime.now() - timedelta(days=366)

AVERAGE_GAME_LENGTH = 20
STDDEV = 3

ASSIST_MULTIPLIER_MEAN = 0.2
ASSIST_MULTIPLIER_STDDEV = 0.05

KILL_DISTRIBUTIONS = {
    (0, 0): (4, 1),
    (1, 1): (4, 1),
    (2, 2): (4, 1),
    (0, 1): (3, 1),
    (0, 2): (2, 1),
    (1, 0): (5, 1),
    (1, 2): (3, 1),
    (2, 1): (5, 1),
    (2, 0): (8, 1)
}


def sample_kill_death_assist(team_1, team_2):
    kills = {}
    deaths = {}
    assists = {}

    for p1, p2 in itertools.chain(itertools.product(team_1, team_2), itertools.product(team_2, team_1)):
        # How many kills does p1 get against p2 on average
        p1_level = PLAYER_TIERS[p1.username]
        p2_level = PLAYER_TIERS[p2.username]

        mean, stddev = KILL_DISTRIBUTIONS[(p1_level, p2_level)]
        pair_kills = max(0, round(random.gauss(mean, stddev)))
        kills[p1.username] = kills.get(p1.username, 0) + pair_kills
        deaths[p2.username] = deaths.get(p2.username, 0) + pair_kills

    for team in [team_1, team_2]:
        for player in team:
            teammates = [p for p in team if p.username != player.username]
            teammate_kills = sum(kills[p.username] for p in teammates)
            assist_multiplier = max(0, random.gauss(ASSIST_MULTIPLIER_MEAN, ASSIST_MULTIPLIER_STDDEV))
            assists[player.username] = round(assist_multiplier * teammate_kills)

    return kills, deaths, assists


def sample_game_duration():
    delta = datetime.now() - START_DATE
    seconds = random.randint(0, int(delta.total_seconds()))

    start_date = START_DATE + timedelta(seconds=seconds)
    duration_minutes = random.gauss(AVERAGE_GAME_LENGTH, STDDEV)

    return start_date, start_date + timedelta(minutes=duration_minutes)


def find_player_by_name(players, username):
    filtered = [p for p in players if p.username == username]
    return filtered[0]


def fetch_players(conn):
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM players")
        return list(util.sql.objects(cursor))


def fetch_inventories(conn, players):
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM inventories")

        for player in players:
            player.inventories = []

        for inventory in util.sql.objects(cursor):
            owner = find_player_by_name(players, inventory.username)
            owner.inventories.append(inventory)


def create_plays_tuples(players, team_number, gid, kills, deaths, assists):
    tuples = []

    for player in players:
        inventory = random.choice(player.inventories)
        tuples.append(
            (player.username,
             inventory.name,
             gid,
             kills[player.username],
             deaths[player.username],
             assists[player.username],
             team_number)
        )

    return tuples


def create_game(gid, team_1, team_2, winning_team, conn):
    game_map = random.choice(MAPS)
    game_type = random.choice(GAME_TYPES)
    start_date, end_date = sample_game_duration()

    with conn.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM plays WHERE gid=%d" % gid)
        count = cursor.fetchone()[0]

        if count > 0:
            # We've already done this
            return

        columns = ('gid', 'game_type', 'map_name', 'winning_team', 'start_time', 'end_time')

        tuples = [(gid, game_type, game_map, winning_team, start_date, end_date)]

        # Create the game session object
        query = util.sql.insert_query('game_sessions', columns, tuples)
        print(query)
        cursor.execute(query)
        print("Rows Affected: %d" % cursor.rowcount)

        kills, deaths, assists = sample_kill_death_assist(team_1, team_2)

        columns = ('username', 'inventory_name', 'gid', 'kills', 'deaths', 'assists', 'team_number')
        tuples = create_plays_tuples(team_1, 1, gid, kills, deaths, assists) \
            + create_plays_tuples(team_2, 2, gid, kills, deaths, assists)

        query = util.sql.insert_query('plays', columns, tuples)
        print(query)
        cursor.execute(query)
        print("Rows Affected: %d" % cursor.rowcount)


def run():
    with database.connect() as conn:
        players = fetch_players(conn)
        fetch_inventories(conn, players)

        for gid in range(GAMES_TO_MAKE):
            players_in_game = random.sample(players, k=4)
            team_1 = players_in_game[:2]
            team_2 = players_in_game[2:]

            team_1_rank = sum(PLAYER_TIERS[p.username] for p in team_1)
            team_2_rank = sum(PLAYER_TIERS[p.username] for p in team_2)

            team_1_prob = math.exp(team_1_rank) / (math.exp(team_1_rank) + math.exp(team_2_rank))
            winning_team = 1 if random.uniform(0, 1) <= team_1_prob else 2

            create_game(gid, team_1, team_2, winning_team, conn)


if __name__ == "__main__":
    run()
