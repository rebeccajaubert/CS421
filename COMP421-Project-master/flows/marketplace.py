from .flow_base import FlowBase
import util.prompts as prompts
import util.sql as sql
import psycopg2.errors


class Marketplace(FlowBase):
    prompt_text = "Buy new items for use in games."

    def reload_player(self):
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT * FROM players WHERE username=%(username)s", {
                "username": self.player.username
            })
            self.player = next(sql.objects(cursor))

    def purchase_menu_loop(self, items, formatter, empty_message):
        updated_balance = self.player.coin_balance

        while True:
            if len(items) == 0:
                print(empty_message)
                self.reload_player()
                return

            print("Your balance is now %d" % updated_balance)

            options = items + ['exit']
            descriptions = [formatter(item) for item in items] + ['Exit']
            choice = prompts.select_from_list(
                options,
                descriptions,
                'What would you like to purchase? You may exit without purchasing anything.')

            if choice == 'exit':
                # Reload player so balance is up to date in future menus
                self.reload_player()
                return

            try:
                # Purchase the item using the stored procedure we created
                with self.connection.cursor() as cursor:
                    cursor.execute("SELECT purchase_item(%(item_id)s, %(username)s)", {
                        "item_id": choice.id,
                        "username": self.player.username
                    })
                    updated_balance = cursor.fetchone()[0]

                self.connection.commit()

                print("You now own %s" % choice.name)
                items.remove(choice)
            except psycopg2.errors.RaiseException as err:
                # The transaction likely raised due to insufficient balance
                print("Your balance is insufficient to purchase this item.")

    def weapons_menu(self):
        query = """
            SELECT items.*, weapons.* FROM weapons 
            INNER JOIN items ON weapons.item_id = items.id
            WHERE items.id NOT IN (SELECT item_id FROM owns WHERE username=%(username)s)
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, {
                "username": self.player.username
            })
            weapons = list(sql.objects(cursor))

        def formatter(w):
            return 'Price: %d -- %s -- weight: %d, range: %d, damage: %d' % \
                    (w.price, w.name, w.weight, w.range, w.damage)
        self.purchase_menu_loop(weapons, formatter, 'You have already purchased all the weapons in the game!')

    def armors_menu(self):
        query = """
            SELECT items.*, armors.* FROM armors 
            INNER JOIN items ON armors.item_id = items.id
            WHERE items.id NOT IN (SELECT item_id FROM owns WHERE username=%(username)s)
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, {
                "username": self.player.username
            })
            armors = list(sql.objects(cursor))

        def formatter(armor):
            return 'Price: %d -- %s -- weight: %d, protection: %d' % \
                   (armor.price, armor.name, armor.weight, armor.protection)
        self.purchase_menu_loop(armors, formatter, 'You have already purchased all the armors in the game!')

    def attachments_menu(self):
        query = """
            SELECT items.*, attaches_to.name as attaches_to_name FROM attachments
            INNER JOIN items ON attachments.item_id = items.id
            INNER JOIN items AS attaches_to ON attachments.attaches_to_id = attaches_to.id
            WHERE attaches_to.id IN (SELECT item_id FROM owns WHERE username=%(username)s)
              AND items.id NOT IN (SELECT item_id FROM owns WHERE username=%(username)s)
            ORDER BY attaches_to_name
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, {
                "username": self.player.username
            })
            attachments = list(sql.objects(cursor))

        def formatter(att):
            return 'Price: %d -- For: %s -- %s -- weight: %d' % \
                   (att.price, att.attaches_to_name, att.name, att.weight)
        self.purchase_menu_loop(attachments, formatter,
                                "None of the items you own have any attachments available, or you've already purchased"
                                " all the available ones!")

    def run(self):
        print("You have %d coins in your balance" % self.player.coin_balance)

        while True:
            options = ['weapons', 'armors', 'attachments', 'finished']
            descriptions = ['Browse weapons', 'Browse armors', 'Browse attachments for your weapons',
                            'Exit the marketplace']
            option = prompts.select_from_list(options, descriptions, 'What would you like to do?')

            if option == 'weapons':
                self.weapons_menu()
            elif option == 'armors':
                self.armors_menu()
            elif option == 'attachments':
                self.attachments_menu()
            else:
                return
