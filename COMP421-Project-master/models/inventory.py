import util.sql as sql
import tabulate


class Inventory:

    def __init__(self, connection, inventory_record):
        self.connection = connection
        self.inventory_record = inventory_record

        self.cache = {}

    @property
    def username(self):
        return self.inventory_record.username

    @property
    def name(self):
        return self.inventory_record.name

    @staticmethod
    def get_for_player(connection, username):
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM inventories WHERE username=%(username)s", {
                "username": username
            })

            return [Inventory(connection, record) for record in sql.objects(cursor)]

    def weapons(self):
        if 'weapons' in self.cache:
            return self.cache['weapons']

        with self.connection.cursor() as cursor:
            query = """
            SELECT items.id, items.name, weapons.type FROM inventory_contains
            INNER JOIN items 
              ON items.id = inventory_contains.item_id
            INNER JOIN weapons 
              ON items.id = weapons.item_id
            WHERE inventory_contains.username = %(username)s 
              AND inventory_contains.name = %(name)s
            """
            cursor.execute(query, {
                "username": self.inventory_record.username,
                "name": self.inventory_record.name
            })

            weapons = list(sql.objects(cursor))
            self.cache['weapons'] = weapons

            return weapons

    def armors(self):
        if 'armors' in self.cache:
            return self.cache['armors']

        with self.connection.cursor() as cursor:
            query = """
            SELECT items.id, items.name, armors.protection FROM inventory_contains
            INNER JOIN items 
              ON items.id = inventory_contains.item_id
            INNER JOIN armors 
              ON items.id = armors.item_id
            WHERE inventory_contains.username = %(username)s 
              AND inventory_contains.name = %(name)s
            """
            cursor.execute(query, {
                "username": self.inventory_record.username,
                "name": self.inventory_record.name
            })

            armors = list(sql.objects(cursor))
            self.cache['armors'] = armors

            return armors

    def attachments(self):
        if 'attachments' in self.cache:
            return self.cache['attachments']

        with self.connection.cursor() as cursor:
            query = """
            SELECT items.id, items.name, attachments.attaches_to_id FROM inventory_contains
            INNER JOIN items 
              ON items.id = inventory_contains.item_id
            INNER JOIN attachments 
              ON items.id = attachments.item_id
            WHERE inventory_contains.username = %(username)s 
              AND inventory_contains.name = %(name)s
            """
            cursor.execute(query, {
                "username": self.inventory_record.username,
                "name": self.inventory_record.name
            })

            attachments = list(sql.objects(cursor))
            self.cache['attachments'] = attachments

            return attachments

    def invalidate_cache(self):
        self.cache = {}

    def describe_current_inventory(self):
        desc = self.name + "\n"

        weapons = self.weapons()
        armors = self.armors()
        attachments = self.attachments()

        items_table = []

        for weapon in weapons:
            attached = [a.name for a in attachments if a.attaches_to_id == weapon.id]

            items_table.append(
                [weapon.name, weapon.type, ', '.join(attached)]
            )

        for armor in armors:
            items_table.append(
                [armor.name, 'Armor', '']
            )

        desc += tabulate.tabulate(items_table, headers=["Item Name", "Type", "Attachments in Use"])

        return desc
