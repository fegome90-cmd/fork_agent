"""TUI root application."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header

from src.interfaces.tui.screens.list_screen import ListScreen


class TUIApp(App[None]):
    """Memory TUI — browse, search, manage observations."""

    TITLE = "Memory TUI"
    SUB_TITLE = "fork_agent"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("s", "push_search", "Search"),
        ("/", "push_search_focus", "Search"),
        ("a", "push_save", "Add"),
        ("S", "push_stats", "Stats"),
    ]

    def __init__(self, db_path: str | None = None) -> None:
        super().__init__()
        self.db_path = Path(db_path) if db_path else None

    def compose(self) -> ComposeResult:
        yield Header()
        yield ListScreen(db_path=self.db_path)
        yield Footer()

    def action_push_search(self) -> None:
        """Open search screen."""
        from src.interfaces.tui.screens.search_screen import SearchScreen

        self.push_screen(SearchScreen(db_path=self.db_path))

    def action_push_search_focus(self) -> None:
        """Open search screen with input focused."""
        from src.interfaces.tui.screens.search_screen import SearchScreen

        self.push_screen(SearchScreen(db_path=self.db_path))

    def action_push_save(self) -> None:
        """Open save screen."""
        from src.interfaces.tui.screens.save_screen import SaveScreen

        self.push_screen(SaveScreen(db_path=self.db_path))

    def action_push_stats(self) -> None:
        """Open stats screen."""
        from src.interfaces.tui.screens.stats_screen import StatsScreen

        self.push_screen(StatsScreen(db_path=self.db_path))
