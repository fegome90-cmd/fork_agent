"""Structured diff result for observation comparison."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DiffItem:
    """A single diff entry between two observations."""

    topic_key: str
    change_type: str  # "added", "removed", "modified"
    from_content: str | None = None
    to_content: str | None = None
    from_id: str | None = None
    to_id: str | None = None


@dataclass(frozen=True)
class DiffResult:
    """Result of diffing observations between two time windows."""

    added: int = 0
    modified: int = 0
    removed: int = 0
    items: tuple[DiffItem, ...] = ()
    from_timestamp: int = 0
    to_timestamp: int = 0

    def to_json(self) -> dict[str, Any]:
        return {
            "from_timestamp": self.from_timestamp,
            "to_timestamp": self.to_timestamp,
            "summary": {
                "added": self.added,
                "modified": self.modified,
                "removed": self.removed,
                "total_changes": self.added + self.modified + self.removed,
            },
            "items": [
                {
                    "topic_key": item.topic_key,
                    "change_type": item.change_type,
                    "from_content": item.from_content,
                    "to_content": item.to_content,
                    "from_id": item.from_id,
                    "to_id": item.to_id,
                }
                for item in self.items
            ],
        }
