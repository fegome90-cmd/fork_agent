"""List screen — paginated DataTable of observations."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Static


class ListScreen(Screen[None]):
    """Displays observations in a paginated DataTable."""

    BINDINGS = [
        Binding("n", "next_page", "Next"),
        Binding("p", "prev_page", "Prev"),
        Binding("d", "detail", "Detail"),
        Binding("/", "search", "Search"),
    ]

    PAGE_SIZE = 50

    def __init__(self, db_path: Path | None = None) -> None:
        super().__init__()
        self._db_path = db_path
        self._page = 0
        self._service: object | None = None  # lazy init, cached

    def compose(self) -> ComposeResult:
        table = DataTable()
        table.add_columns("ID", "Type", "Project", "Topic Key", "Title", "Created")
        table.cursor_type = "row"
        yield table
        yield Static(id="status")

    def on_mount(self) -> None:
        self._load_data()

    def _get_service(self) -> object:
        if self._service is None:
            from src.infrastructure.persistence.container import (
                create_container,
                get_default_db_path,
            )

            db = self._db_path or get_default_db_path()
            container = create_container(db_path=db)
            self._service = container.memory_service()
        return self._service

    def _load_data(self) -> None:
        service = self._get_service()

        offset = self._page * self.PAGE_SIZE
        observations = service.get_recent(limit=self.PAGE_SIZE, offset=offset)

        table = self.query_one(DataTable)
        table.clear()

        for obs in observations:
            ts = (
                datetime.fromtimestamp(obs.timestamp / 1000).strftime("%Y-%m-%d %H:%M")
                if obs.timestamp
                else ""
            )
            title = obs.title if obs.title else (obs.content[:40] + "..." if len(obs.content) > 40 else obs.content)
            table.add_row(
                obs.id[:8],
                obs.type or "",
                obs.project or "",
                obs.topic_key or "",
                title,
                ts,
            )

        self.query_one("#status", Static).update(
            f"Page {self._page + 1} | {len(observations)} observations"
        )

    def action_next_page(self) -> None:
        self._page += 1
        self._load_data()

    def action_prev_page(self) -> None:
        if self._page > 0:
            self._page -= 1
            self._load_data()

    def action_detail(self) -> None:
        """Show detail for selected row (future: detail screen)."""
        pass

    def action_search(self) -> None:
        """Activate search (future: search screen)."""
        pass
