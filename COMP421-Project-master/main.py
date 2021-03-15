import util.sql as sql
import util.prompts as prompts
import database
import flows


def reload_player(player, connection):
    query = "SELECT *, exp_requirement(level) as exp_requirement FROM players WHERE username=%(username)s"
    with connection.cursor() as cursor:
        cursor.execute(query, {
            "username": player.username
        })
        return next(sql.objects(cursor))


def main():
    with database.connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT *, exp_requirement(level) as exp_requirement FROM players WHERE banned_date IS NULL "
                "ORDER BY username")

            players = list(sql.objects(cursor))

    try:
        print("Type q or Q at any time to exit the application.")
        # First step is to select a player
        player = prompts.select_from_list(
            players,
            [p.username for p in players],
            "Please pick a user from this list to play as")

        print("Welcome back %s!" % player.username)

        menu_item_descriptions = [flow.prompt_text for flow in flows.menu_items]

        while True:
            print(end='\n\n')

            flow_class = prompts.select_from_list(
                flows.menu_items,
                menu_item_descriptions,
                "Please select something to do!"
            )

            with database.connect() as connection:
                flow_object = flow_class(player, connection)
                flow_object.run()

                # Reload the player as data may have changed
                player = reload_player(player, connection)

    except prompts.QuitException:
        return


if __name__ == "__main__":
    main()
