from .flow_base import FlowBase
import util.prompts as prompts
import util.sql as sql


class CreateGuild(FlowBase):
    prompt_text = "Join or create a guild."

    def prompt_for_name(self):
        while True:
            chosen_name = prompts.get_input_value_with_quit("Please choose a name: ")

            with self.connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM guilds WHERE name=%(name)s", {
                    "name": chosen_name
                })
                count = cursor.fetchone()[0]

            if count == 0:
                return chosen_name

            print("This name is already in use by another guild, please choose a different name.")

    def set_player_guild(self, player, guild):
        query = """
        UPDATE players
        SET
            guild_name=%(guild_name)s,
            guild_join_date=now()
        WHERE username=%(username)s
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, {
                "guild_name": guild.name,
                "username": player.username
            })

    def create_new_guild(self):
        print("Please choose a name for your guild")
        new_name = self.prompt_for_name()

        with self.connection.cursor() as cursor:
            query = sql.insert_query(
                'guilds',
                ('admin_username', 'name'),
                [(self.player.username, new_name)],
                return_fields='*'
            )
            cursor.execute(query)
            guild = next(sql.objects(cursor))

        self.set_player_guild(self.player, guild)
        self.connection.commit()

    def join_a_guild(self):
        query = "SELECT admin_username, name, created_date FROM guilds"
        with self.connection.cursor() as cursor:
            cursor.execute(query)
            guilds = list(sql.objects(cursor))

        descriptions = [
            '%s -- Admin: %s, active since %s' % (g.name, g.admin_username, g.created_date.strftime("%Y-%m-%d"))
            for g in guilds
        ] + ['Exit without joining anything']
        guilds.append('exit')

        option = prompts.select_from_list(guilds, descriptions, "Which guild would you like to join?")
        if option == 'exit':
            return

        self.set_player_guild(self.player, option)
        self.connection.commit()
        print("Welcome to %s!" % option.name)

    def leave_guild(self):
        query = """
        UPDATE players
        SET
            guild_name = NULL,
            guild_join_date = NULL
        WHERE username=%(username)s
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, {
                "username": self.player.username
            })

    def delete_guild(self, guild_name):
        with self.connection.cursor() as cursor:
            cursor.execute("DELETE FROM guilds WHERE name=%(guild_name)s", {
                "guild_name": guild_name
            })

    def leave_guild_prompt(self):
        guild_name = self.player.guild_name

        query = """
        SELECT guilds.admin_username, count(*) - 1 as num_non_admins FROM guilds
        INNER JOIN players
          ON guilds.name = players.guild_name
        WHERE guild_name=%(guild_name)s
        GROUP BY guilds.admin_username;
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, {
                "guild_name": guild_name
            })
            admin, num_non_admins = cursor.fetchone()

        if admin == self.player.username:
            if num_non_admins == 0:
                print("Since you're the admin and the sole member of the guild, the guild will be deleted.")
                value = prompts.get_input_value_with_quit(
                    'Confirm that this is what you want to do by entering y or Y: ')
                if value == 'y':
                    self.leave_guild()
                    self.delete_guild(guild_name)
            else:
                print("Since you're the admin you should assign a new admin first before leaving.")
                with self.connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT username FROM players WHERE guild_name=%(guild_name)s AND username<>%(username)s", {
                            "guild_name": guild_name,
                            "username": self.player.username
                        })
                    members = [row[0] for row in cursor]

                    new_admin = prompts.select_from_list(members, members, 'Who would you like to make the admin?',
                                                         interactive_with_single_option=True)
                    query = """
                    UPDATE guilds SET admin_username=%(new_admin)s WHERE name=%(guild_name)s
                    """
                    cursor.execute(query, {
                        "new_admin": new_admin,
                        "guild_name": guild_name
                    })
                    self.leave_guild()
        else:
            self.leave_guild()

    def show_guild_members(self):

        query = """
        SELECT username FROM players
        WHERE guild_name=%(guild_name)s
          AND username <> %(username)s
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, {
                "guild_name": self.player.guild_name,
                "username": self.player.username
            })

            if cursor.rowcount > 0:
                print("These are your fellow guild members:")
                for (username,) in cursor:
                    print(username)

    def run(self):
        if self.player.guild_name is not None:
            self.show_guild_members()
            print()
            print("You've been a member of %s since %s" %
                  (self.player.guild_name, self.player.guild_join_date.strftime('%Y-%m-%d')))
            print("If you want to join/create another guild you must leave first.")

            print("Would you like to leave the guild? Enter y or Y to leave, and enter anything else to continue")
            value = prompts.get_input_value_with_quit('Input: ')
            if value.lower().strip() == 'y':
                self.leave_guild_prompt()
        else:
            options = ['join_guild', 'create_guild', 'finished']
            descriptions = ['Join a guild', 'Create a new guild', 'Exit back to main menu']

            option = prompts.select_from_list(options, descriptions, 'What would you like to do?')
            if option == 'create_guild':
                print("Creating a guild")
                self.create_new_guild()
            elif option == 'join_guild':
                self.join_a_guild()

