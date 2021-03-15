from .flow_base import FlowBase
from models import Inventory
import util.prompts as prompts
import util.sql as sql


class InventoryCreate(FlowBase):
    prompt_text = "Create or modify an inventory to use in your games."

    def prompt_for_inventory_option(self, inventories):
        # The options are rename inventory, modify inventory or create a new one
        options = []
        descriptions = []

        for inventory in inventories:
            options.append(('modify', inventory))
            descriptions.append('Modify %s' % inventory.name)
            options.append(('rename', inventory))
            descriptions.append('Rename %s' % inventory.name)

        options.append(('create', None))
        descriptions.append('Create a new inventory')

        return prompts.select_from_list(options, descriptions,
                                        "What would you like to do? Please choose an option from this list.",
                                        interactive_with_single_option=True)

    def prompt_for_name(self):
        while True:
            chosen_name = prompts.get_input_value_with_quit("Please choose a name: ")

            with self.connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM inventories WHERE username=%(username)s AND name=%(name)s", {
                    "username": self.player.username,
                    "name": chosen_name
                })
                count = cursor.fetchone()[0]

            if count == 0:
                return chosen_name

            print("This name is already in use by another one of your inventories, please choose a different name.")

    def rename_inventory(self, inventory):
        print("What would you like to rename %s to?" % inventory.name)
        new_name = self.prompt_for_name()

        with self.connection.cursor() as cursor:
            cursor.execute("UPDATE inventories SET name=%(new_name)s WHERE username=%(username)s AND name=%(old_name)s",
                           {
                               "username": self.player.username,
                               "old_name": inventory.name,
                               "new_name": new_name
                           })

        self.connection.commit()
        print("Inventory renamed successfully!")

    def create_new_inventory(self):
        print("Please choose a name for your new inventory!")
        new_name = self.prompt_for_name()

        with self.connection.cursor() as cursor:
            query = sql.insert_query(
                'inventories',
                ('username', 'name'),
                [(self.player.username, new_name)],
                return_fields='*'
            )
            cursor.execute(query)
            inventory = next(sql.objects(cursor))
            return Inventory(self.connection, inventory)

    def add_item_menu(self, inventory):
        # Add a nil_type so that the NOT IN clause always has a valid syntax if there are no weapons in the
        # inventory
        weapon_types = [w.type for w in inventory.weapons()] + ['nil_type']
        fetch_armors = len(inventory.armors()) == 0

        weapons_query = """
            SELECT items.*, weapons.* FROM weapons
            INNER JOIN items ON weapons.item_id = items.id
            WHERE weapons.type NOT IN {0}
              AND weapons.item_id IN (SELECT item_id FROM owns WHERE username=%(username)s)
        """.format(sql.sql_format_tuple(weapon_types))

        armors_query = """
            SELECT items.*, armors.* FROM armors
            INNER JOIN items ON armors.item_id = items.id
            WHERE armors.item_id IN (SELECT item_id FROM owns WHERE username=%(username)s)
        """

        armors = []

        with self.connection.cursor() as cursor:
            cursor.execute(weapons_query, {
                "username": self.player.username
            })
            weapons = list(sql.objects(cursor))

            if fetch_armors:
                cursor.execute(armors_query, {
                    "username": self.player.username
                })
                armors = list(sql.objects(cursor))

        options = weapons + armors
        descriptions = []

        for weapon in weapons:
            descriptions.append('%s -- %s, weight: %d, range: %d, damage: %d' %
                                (weapon.name, weapon.type, weapon.weight, weapon.range, weapon.damage))

        for armor in armors:
            descriptions.append('%s -- Armor, weight: %d, protection: %d' %
                                (armor.name, armor.weight, armor.protection))

        if len(options) == 0:
            print("Your inventory is already full! Please remove items first"
                  " if you want to add a different weapon or armor.")
        else:
            new_item = prompts.select_from_list(options, descriptions, "Please select an item from this list to add"
                                                " to your inventory",
                                                interactive_with_single_option=True)
            with self.connection.cursor() as cursor:
                cursor.execute("INSERT INTO inventory_contains (username, name, item_id)"
                               "VALUES (%(username)s, %(name)s, %(item_id)s)", {
                                   "username": self.player.username,
                                   "name": inventory.name,
                                   "item_id": new_item.id
                               })

    def remove_item_menu(self, inventory):
        options = inventory.weapons() + inventory.armors()
        descriptions = [item.name for item in options]

        item_to_remove = prompts.select_from_list(options, descriptions, "Choose an item to remove:",
                                                  interactive_with_single_option=True)
        delete_query = """
            DELETE FROM inventory_contains
            WHERE username=%(username)s AND name=%(name)s AND item_id=%(item_id)s
        """
        with self.connection.cursor() as cursor:
            cursor.execute(delete_query, {
                "username": self.player.username,
                "name": inventory.name,
                "item_id": item_to_remove.id
            })

        print("Item successfully removed!")

    def add_new_attachment(self, inventory, weapon, current_attachments):
        query = """
            SELECT items.id, items.name, items.weight FROM attachments
            INNER JOIN items ON attachments.item_id = items.id
            WHERE attachments.attaches_to_id = %(weapon_item_id)s
              AND attachments.item_id NOT IN (
                SELECT item_id AS id FROM inventory_contains
                WHERE username=%(username)s AND name=%(name)s
              )
              AND attachments.item_id IN (
                SELECT item_id AS id FROM owns
                WHERE username=%(username)s
              )
        """

        with self.connection.cursor() as cursor:
            cursor.execute(query, {
                "weapon_item_id": weapon.id,
                "username": self.player.username,
                "name": inventory.name
            })
            attachments = list(sql.objects(cursor))

        if len(attachments) == 0:
            print("You don't own any additional attachments for this item!")
        else:
            print("Which attachment would you like to add.")
            descriptions = ["%s, weight: %d" % (a.name, a.weight) for a in attachments]
            attachment = prompts.select_from_list(attachments, descriptions, "Choose a number from this list:",
                                                  interactive_with_single_option=True)
            with self.connection.cursor() as cursor:
                cursor.execute("INSERT INTO inventory_contains (username, name, item_id)"
                               "VALUES (%(username)s, %(name)s, %(item_id)s)", {
                                   "username": self.player.username,
                                   "name": inventory.name,
                                   "item_id": attachment.id
                               })

    def remove_attachment(self, inventory, current_attachments):
        print("Which attachment would you like to remove?")
        attachment = prompts.select_from_list(
            current_attachments,
            [a.name for a in current_attachments],
            "Enter a number from this list:",
            interactive_with_single_option=True
        )

        with self.connection.cursor() as cursor:
            cursor.execute("DELETE FROM inventory_contains WHERE "
                           "username=%(username)s AND name=%(name)s AND item_id=%(item_id)s", {
                               "username": self.player.username,
                               "name": inventory.name,
                               "item_id": attachment.id
                           })

        print("Attachment removed!")

    def modify_attachments_menu(self, inventory):
        descriptions = [w.name for w in inventory.weapons()]
        print("Which weapon would you like to modify attachments for?")
        weapon = prompts.select_from_list(inventory.weapons(), descriptions, "Choose a weapon from this list: ",
                                          interactive_with_single_option=True)

        while True:
            current_attachments = [a for a in inventory.attachments() if a.attaches_to_id == weapon.id]

            options = ['add_new']
            descriptions = ['Add a new attachment']

            if len(current_attachments) > 0:
                options.append('remove')
                descriptions.append('Remove an attachment')

            options.append('finished')
            descriptions.append('Exit to previous menu.')

            print("What would you like to do?")
            option = prompts.select_from_list(options, descriptions, "Please select a number from this list: ",
                                              interactive_with_single_option=True)

            if option == 'add_new':
                self.add_new_attachment(inventory, weapon, current_attachments)
            elif option == 'remove':
                self.remove_attachment(inventory, current_attachments)
            else:
                return

            inventory.invalidate_cache()
            self.connection.commit()

    def inventory_modify_menu(self, inventory):

        while True:
            print()
            print(inventory.describe_current_inventory())

            print("What would you like to do to this inventory?")
            options = ['add_item', 'remove_item', 'modify_attachments', 'finished']
            descriptions = [
                'Add a weapon or armor',
                'Remove a weapon or armor',
                'Modify attachments for a weapon',
                'Finish modifying, go back to main menu.'
            ]

            option = prompts.select_from_list(options, descriptions, "Please choose an option from this list.",
                                              interactive_with_single_option=True)

            if option == 'add_item':
                self.add_item_menu(inventory)
            elif option == 'remove_item':
                self.remove_item_menu(inventory)
            elif option == 'modify_attachments':
                self.modify_attachments_menu(inventory)
            elif option == 'finished':
                return

            self.connection.commit()
            inventory.invalidate_cache()

    def run(self):
        print("Creating an inventory!")

        inventories = Inventory.get_for_player(self.connection, self.player.username)
        option, inventory = self.prompt_for_inventory_option(inventories)

        if option == 'rename':
            self.rename_inventory(inventory)
        else:
            if option == 'create':
                inventory = self.create_new_inventory()

            self.inventory_modify_menu(inventory)
