"""Save screen — create a new observation with live preview."""

from __future__ import annotations

import logging
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Input, Static, TextArea

from src.domain.entities.observation import Observation

logger = logging.getLogger(__name__)


class SaveScreen(Screen[None]):
    """Form to create a new observation."""

    BINDINGS = [
        Binding("escape", "pop_screen", "Cancel"),
        Binding("ctrl+s", "save", "Save"),
    ]

    def __init__(self, db_path: Path | None = None) -> None:
        super().__init__()
        self._db_path = db_path
        self._service: object | None = None

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Static("[bold]Create New Observation[/bold]")
            yield Static("Content:")
            yield TextArea(id="save-content", language="markdown")
            with Horizontal():
                with Vertical(classes="field-col"):
                    yield Static("Type:")
                    yield Input(placeholder="decision, bugfix, pattern...", id="save-type")
                with Vertical(classes="field-col"):
                    yield Static("Topic Key:")
                    yield Input(placeholder="no-spaces-allowed", id="save-topic-key")
            with Horizontal():
                with Vertical(classes="field-col"):
                    yield Static("Project:")
                    yield Input(placeholder="project name", id="save-project")
                with Vertical(classes="field-col"):
                    yield Static("Title:")
                    yield Input(placeholder="optional title", id="save-title")
            yield Static("[bold]Preview[/bold]", id="preview-label")
            yield Static("", id="save-preview")
            yield Static("", id="save-validation")
        yield Static("[dim][ctrl+s] Save  [Escape] Cancel[/dim]", id="save-footer")

    def on_mount(self) -> None:
        self.query_one("#save-content", TextArea).focus()

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

    def on_input_changed(self, event: Input.Changed) -> None:
        _ = event
        self._update_preview()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        _ = event
        self._update_preview()

    def _update_preview(self) -> None:
        content = self.query_one("#save-content", TextArea).text.strip()
        obs_type = self.query_one("#save-type", Input).value.strip()
        topic_key = self.query_one("#save-topic-key", Input).value.strip()
        project = self.query_one("#save-project", Input).value.strip()
        title = self.query_one("#save-title", Input).value.strip()

        lines: list[str] = []
        if obs_type:
            lines.append(f"Type: {obs_type}")
        if project:
            lines.append(f"Project: {project}")
        if topic_key:
            lines.append(f"Topic: {topic_key}")
        if title:
            lines.append(f"Title: {title}")
        if content:
            preview = content[:100] + ("..." if len(content) > 100 else "")
            lines.append(f"Content: {preview}")

        self.query_one("#save-preview", Static).update(
            "\n".join(lines) if lines else "[dim]Fill in the form above...[/dim]"
        )

    def _validate(self) -> list[str]:
        errors: list[str] = []
        content = self.query_one("#save-content", TextArea).text.strip()
        if not content:
            errors.append("Content is required")

        type_val = self.query_one("#save-type", Input).value.strip()
        if type_val and type_val not in Observation._ALLOWED_TYPES:
            allowed = ", ".join(sorted(Observation._ALLOWED_TYPES))
            errors.append(f"Invalid type '{type_val}'. Allowed: {allowed}")

        topic_key = self.query_one("#save-topic-key", Input).value.strip()
        if topic_key and " " in topic_key:
            errors.append("Topic key cannot contain spaces")

        return errors

    def action_save(self) -> None:
        errors = self._validate()
        if errors:
            self.query_one("#save-validation", Static).update(
                "[red]" + "\n".join(f"- {e}" for e in errors) + "[/red]"
            )
            return

        content = self.query_one("#save-content", TextArea).text.strip()
        obs_type = self.query_one("#save-type", Input).value.strip() or None
        topic_key = self.query_one("#save-topic-key", Input).value.strip() or None
        project = self.query_one("#save-project", Input).value.strip() or None
        title = self.query_one("#save-title", Input).value.strip() or None

        service = self._get_service()
        try:
            service.save(
                content=content,
                type=obs_type,
                topic_key=topic_key,
                project=project,
                title=title,
            )
        except Exception as e:
            logger.error("Save failed: %s", e)
            self.query_one("#save-validation", Static).update(f"Save failed: {e}")
            return
        self.notify("Observation saved", severity="information")
        self.app.pop_screen()
