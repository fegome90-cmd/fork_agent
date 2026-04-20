"""Search screen — query input + filtered results DataTable."""

from __future__ import annotations

import logging
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Input, Static

from src.domain.entities.observation import Observation

logger = logging.getLogger(__name__)


class SearchScreen(Screen[None]):
    """Search observations with optional type/project filters."""

    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
        Binding("ctrl+s", "focus_search", "Focus Search"),
    ]

    def __init__(self, db_path: Path | None = None, initial_query: str = "") -> None:
        super().__init__()
        self._db_path = db_path
        self._initial_query = initial_query
        self._service: object | None = None
        self._result_ids: list[str] = []

    def compose(self) -> ComposeResult:
        with Vertical():
            with Horizontal(id="search-input-row"):
                yield Input(
                    placeholder="Search query...",
                    id="search-input",
                )
                yield Button("Search", variant="primary", id="search-btn")
            with Horizontal(id="search-filter-row"):
                yield Input(placeholder="Type filter (optional)", id="type-filter")
                yield Input(placeholder="Project filter (optional)", id="project-filter")
            yield DataTable(id="search-results")
            yield Static(id="search-status")

    def on_mount(self) -> None:
        table = self.query_one("#search-results", DataTable)
        table.add_columns("ID", "Type", "Project", "Topic Key", "Title")
        table.cursor_type = "row"

        if self._initial_query:
            self.query_one("#search-input", Input).value = self._initial_query
            self._do_search()
        else:
            self.query_one("#search-input", Input).focus()

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

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search-input":
            self._do_search()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "search-btn":
            self._do_search()

    def _do_search(self) -> None:
        query = self.query_one("#search-input", Input).value.strip()
        if not query:
            self.query_one("#search-status", Static).update("[yellow]Enter a search query[/yellow]")
            return

        type_filter = self.query_one("#type-filter", Input).value.strip() or None
        project_filter = self.query_one("#project-filter", Input).value.strip() or None

        service = self._get_service()
        try:
            results: list[Observation] = service.search(query, limit=100, project=project_filter)
        except Exception as e:
            logger.error("Search failed: %s", e)
            self.query_one("#search-status", Static).update(f"Search failed: {e}")
            return

        # Post-filter by type if specified
        if type_filter:
            results = [obs for obs in results if obs.type == type_filter]

        table = self.query_one("#search-results", DataTable)
        table.clear()
        self._result_ids = []

        for obs in results:
            title = obs.title or (obs.content[:40] + "..." if len(obs.content) > 40 else obs.content)
            table.add_row(
                obs.id[:8],
                obs.type or "",
                obs.project or "",
                obs.topic_key or "",
                title,
            )
            self._result_ids.append(obs.id)

        self.query_one("#search-status", Static).update(
            f"{len(results)} results for: [bold]{query}[/bold]"
        )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        _ = event
        self.action_open_detail()

    def action_open_detail(self) -> None:
        table = self.query_one("#search-results", DataTable)
        row_index = table.cursor_row
        if 0 <= row_index < len(self._result_ids):
            from src.interfaces.tui.screens.detail_screen import DetailScreen

            self.app.push_screen(
                DetailScreen(db_path=self._db_path, obs_id=self._result_ids[row_index])
            )

    def action_focus_search(self) -> None:
        inp = self.query_one("#search-input", Input)
        inp.value = ""
        inp.focus()
