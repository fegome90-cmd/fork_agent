"""Detail screen — full observation view with scrollable content."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import RichLog, Static

from src.domain.entities.observation import Observation
from src.interfaces.tui.widgets.type_badge import TypeBadge


class DetailScreen(Screen[None]):
    """Displays a single observation in full detail."""

    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
        Binding("e", "edit", "Edit"),
        Binding("d", "delete", "Delete"),
    ]

    def __init__(self, db_path: Path | None, obs_id: str) -> None:
        super().__init__()
        self._db_path = db_path
        self._obs_id = obs_id
        self._observation: Observation | None = None
        self._service: object | None = None

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Static(id="detail-header")
            with Horizontal(id="detail-badges"):
                yield TypeBadge("—")
                yield Static(id="detail-project-info")
            yield Static(id="detail-meta")
            yield RichLog(id="detail-content", auto_scroll=False, markup=True)
            yield Static(id="detail-metadata")
        yield Static("[dim][e] Edit  [d] Delete  [Esc] Back[/dim]", id="detail-footer")

    def on_mount(self) -> None:
        self._load_observation()

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

    def _load_observation(self) -> None:
        service = self._get_service()
        obs = service.get_by_id(self._obs_id)
        self._observation = obs

        # Header
        title_text = obs.title or obs.content[:60]
        self.query_one("#detail-header", Static).update(
            f"[bold]{title_text}[/bold]\n[dim]ID: {obs.id}[/dim]"
        )

        # Replace TypeBadge — must remove old and add new
        old_badge = self.query_one(TypeBadge)
        new_badge = TypeBadge(obs.type or "unknown")
        old_badge.replace(new_badge)

        # Project info
        parts: list[str] = []
        if obs.project:
            parts.append(f"Project: {obs.project}")
        if obs.topic_key:
            parts.append(f"Topic: {obs.topic_key}")
        if obs.revision_count and obs.revision_count > 1:
            parts.append(f"Rev: {obs.revision_count}")
        self.query_one("#detail-project-info", Static).update("  |  ".join(parts))

        # Meta
        ts_str = (
            datetime.fromtimestamp(obs.timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S")
            if obs.timestamp
            else "Unknown"
        )
        self.query_one("#detail-meta", Static).update(f"Created: {ts_str}")

        # Content
        content_log = self.query_one("#detail-content", RichLog)
        content_log.write(obs.content)

        # Metadata
        if obs.metadata:
            meta_str = json.dumps(obs.metadata, indent=2, default=str)
            self.query_one("#detail-metadata", Static).update(
                f"[bold]Metadata:[/bold]\n[dim]{meta_str}[/dim]"
            )
        else:
            self.query_one("#detail-metadata", Static).update("")

    def action_delete(self) -> None:
        def _on_confirm(confirmed: bool) -> None:
            if confirmed:
                service = self._get_service()
                service.delete(self._obs_id)
                self.notify("Observation deleted", severity="information")
                self.app.pop_screen()

        from src.interfaces.tui.widgets.confirm_modal import ConfirmModal

        self.app.push_screen(ConfirmModal("Delete this observation?"), _on_confirm)

    def action_edit(self) -> None:
        self.notify("Edit coming in Phase 3", severity="warning")
