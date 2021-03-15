
class QuitException(BaseException):
    pass


def get_input_value_with_quit(prompt):
    value = input(prompt)
    if value.lower() == "q":
        raise QuitException()

    return value


def select_from_list(values, descriptions, prompt, interactive_with_single_option=False):
    # Assists in generalizing, most calling code which dynamically geHnerates a list of options
    # shouldn't have to perform this check every time.
    if len(values) == 1 and not interactive_with_single_option:
        return values[0]

    print(prompt)

    for i, description in enumerate(descriptions):
        print("%d) %s" % (i, description))

    while True:
        value = get_input_value_with_quit("Enter a number from this list: ")

        try:
            index = int(value)
            selected = values[index]
            print()
            return selected
        except IndexError:
            print("The selected number isn't an item from the above list.")
        except ValueError:
            print("Input invalid, please try again.")
