from .create_guild import CreateGuild
from .inventory_create import InventoryCreate
from .list_player_stats import ListPlayerStats
from .marketplace import Marketplace
from .simulate_game import SimulateGame
from .data_visualization import VisualizeData


menu_items = [
    SimulateGame,
    InventoryCreate,
    ListPlayerStats,
    CreateGuild,
    Marketplace,
    VisualizeData
]
