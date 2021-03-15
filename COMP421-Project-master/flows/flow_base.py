import abc


class FlowBase(abc.ABC):
    """
    When the user selects a menu item the flow will be initiated with the currently logged in
    player and the run method will be called.

    Use the connection class attribute as a connection to the database in your code.
    """
    prompt_text = ""

    def __init__(self, player, connection):
        self.player = player
        self.connection = connection

    @abc.abstractmethod
    def run(self):
        pass
