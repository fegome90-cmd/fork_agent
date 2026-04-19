"""Colored type badge widget."""

from __future__ import annotations

from textual.widgets import Static

TYPE_COLORS: dict[str, str] = {
    "decision": "green",
    "learning": "blue",
    "bugfix": "red",
    "discovery": "yellow",
    "pattern": "magenta",
    "config": "cyan",
    "preference": "white",
    "session-summary": "dim",
    "architecture": "bold green",
    "security": "bold red",
    "performance": "bold yellow",
}


class TypeBadge(Static):
    """Renders an observation type with a color."""

    def __init__(self, obs_type: str) -> None:
        color = TYPE_COLORS.get(obs_type, "white")
        super().__init__(f"[{color}]{obs_type}[/{color}]")
