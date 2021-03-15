import database
import util.sql
import random
import itertools


FETCH_WEAPONS = """
SELECT items.*, weapons.* FROM weapons
INNER JOIN items ON 
  items.id = weapons.item_id
"""

FETCH_ARMORS = """
SELECT items.*, weapons.* FROM weapons
INNER JOIN items ON 
  items.id = weapons.item_id
"""

FETCH_ATTACHMENTS = """
SELECT items.*, attachments.* FROM attachments
INNER JOIN items ON 
  items.id = attachments.item_id
"""


def fetch_items(conn):
    with conn.cursor() as cursor:
        cursor.execute(FETCH_WEAPONS)
        weapons = list(util.sql.objects(cursor))

        cursor.execute(FETCH_ARMORS)
        armors = list(util.sql.objects(cursor))

        cursor.execute(FETCH_ATTACHMENTS)
        attachments = list(util.sql.objects(cursor))

        for item in itertools.chain(weapons, armors):
            item.attachments = []

            for attachment in attachments:
                if attachment.attaches_to_id == item.id:
                    item.attachments.append(attachment)

        return weapons, armors


def fetch_players(conn):
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM players")

        return list(util.sql.objects(cursor))


def count_inventories_for(player, conn):
    with conn.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM inventories WHERE username = '%s'" % player.username)
        return cursor.fetchone()[0]


def sample_inventories(weapons_by_type, armors, k):
    primaries = random.sample(weapons_by_type['primary'], 2)
    sidearms = random.sample(weapons_by_type['sidearm'], 2)
    melee_weapons = random.sample(weapons_by_type['melee'], 2)
    armors = random.sample(armors, k)

    for primary, sidearm, melee, armor in zip(primaries, sidearms, melee_weapons, armors):
        attachments = []

        for item in [primary, sidearm, melee, armor]:
            if len(item.attachments) > 0:
                attachments.append(random.choice(item.attachments))

        yield [primary, sidearm, melee, armor] + attachments


def insert_inventory(player, name, items, conn):
    with conn.cursor() as cursor:
        columns = ["username", "item_id"]
        tuples = [(player.username, item.id) for item in items]

        query = util.sql.insert_query('owns', columns, tuples)
        print(query)
        cursor.execute(query)
        print("%d Rows Affected" % cursor.rowcount)

        columns = ['username', 'name']
        tuples = [(player.username, name)]

        query = util.sql.insert_query('inventories', columns, tuples)
        print(query)
        cursor.execute(query)
        print("%d Rows Affected" % cursor.rowcount)

        columns = ['username', 'name', 'item_id']
        tuples = [(player.username, name, item.id) for item in items]

        query = util.sql.insert_query('inventory_contains', columns, tuples)
        print(query)
        cursor.execute(query)
        print("%d Rows Affected" % cursor.rowcount)


def run():
    with database.connect() as conn:
        weapons, armors = fetch_items(conn)
        players = fetch_players(conn)

        weapons_by_type = {}
        for key, grouper in itertools.groupby(weapons, key=lambda weapon: weapon.type):
            weapons_by_type[key] = list(grouper)

        # Generate 2 inventories per player
        for player in players:
            num_inventories = count_inventories_for(player, conn)
            num_to_create = 2 - num_inventories

            if num_to_create > 0:
                for i, items in enumerate(sample_inventories(weapons_by_type, armors, num_to_create)):
                    name = player.username + "-" + str(num_inventories + i)

                    # Insert the inventories
                    insert_inventory(player, name, items, conn)


if __name__ == "__main__":
    run()
