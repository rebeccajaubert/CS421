import database
import util.sql


GUILD_NAMES = ['Tempest Noobs', 'Abandoned Helix', 'Hallowed Apocalypse', 'Honored Admirals']
GUILD_ADMIN_USERNAMES = ['gabriel', 'yunus', 'owen', 'rebecca']


def find_by_name(players, name):
    filtered = [p for p in players if p.username == name]
    if filtered:
        return filtered[0]


def partition_players_evenly(other_players, k=4):
    quotient = len(other_players) // k

    for _ in range(k):
        next_chunk = other_players[:quotient]
        yield next_chunk

        other_players = other_players[quotient:]


def create_guild(guild, admin, members, conn):
    with conn.cursor() as cursor:
        # Insert the guild first
        query = util.sql.insert_query('guilds', ('name', 'admin_username'), [(guild, admin.username)])
        print(query)
        cursor.execute(query)
        print("%d Rows Affected" % cursor.rowcount)

        member_names = [p.username for p in [admin] + members]

        # Update the players to set their guild membership
        query = """
        UPDATE players SET
           guild_name='%s',
           guild_join_date=NOW()
        WHERE username IN %s
        """ % (guild, util.sql.sql_format_tuple(member_names))
        print(query)
        cursor.execute(query)
        print("%d Rows Affected" % cursor.rowcount)


def fetch_players(conn):
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM players ORDER BY username ASC")
        return list(util.sql.objects(cursor))


def run():
    with database.connect() as conn:
        players = fetch_players(conn)
        admins = [find_by_name(players, name) for name in GUILD_ADMIN_USERNAMES]
        other_players = [p for p in players if p.username not in GUILD_ADMIN_USERNAMES]
        partitions = partition_players_evenly(other_players, k=len(admins))

        for guild, admin, members in zip(GUILD_NAMES, admins, partitions):
            create_guild(guild, admin, members, conn)


if __name__ == "__main__":
    run()
