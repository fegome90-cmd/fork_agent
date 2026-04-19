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
    BINDINGS = [("q", "quit", "Quit"), ("s", "search", "Search")]

    def __init__(self, db_path: str | None = None) -> None:
        super().__init__()
        self.db_path = Path(db_path) if db_path else None

    def compose(self) -> ComposeResult:
        yield Header()
        yield ListScreen(db_path=self.db_path)
        yield Footer()

    def action_search(self) -> None:
        """Focus search input (future: inline search bar)."""
        pass
