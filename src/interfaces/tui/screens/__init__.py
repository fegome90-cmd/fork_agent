"""TUI screens package."""

from src.interfaces.tui.screens.detail_screen import DetailScreen
from src.interfaces.tui.screens.list_screen import ListScreen
from src.interfaces.tui.screens.save_screen import SaveScreen
from src.interfaces.tui.screens.search_screen import SearchScreen
from src.interfaces.tui.screens.stats_screen import StatsScreen

__all__ = [
    "DetailScreen",
    "ListScreen",
    "SaveScreen",
    "SearchScreen",
    "StatsScreen",
]
