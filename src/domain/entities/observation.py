"""Observation entity for memory storage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar


@dataclass(frozen=True)
class Observation:
    """Immutable observation entity for memory storage.

    Attributes:
        id: Unique identifier for the observation.
        timestamp: Unix timestamp in milliseconds.
        content: The main content/text of the observation.
        metadata: Optional JSON-serializable metadata dictionary.
        idempotency_key: Optional unique key for deduplication.
        project: Optional project name for scoping.
        type: Optional category (decision, architecture, bugfix, etc).
        topic_key: Optional stable key for upserts (no spaces).
        revision_count: Number of revisions (>= 1).
        session_id: Optional session identifier.
    """

    _ALLOWED_TYPES: ClassVar[frozenset[str]] = frozenset(
        {
            "decision",
            "architecture",
            "bugfix",
            "pattern",
            "config",
            "discovery",
            "learning",
            "manual",
            "tool_use",
            "file_change",
            "command",
            "file_read",
            "search",
            "session-summary",
        }
    )

    id: str
    timestamp: int
    content: str
    metadata: dict[str, Any] | None = None
    idempotency_key: str | None = None
    project: str | None = None
    type: str | None = None
    topic_key: str | None = None
    revision_count: int = 1
    session_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, str):
            raise TypeError("id debe ser un string")
        if not self.id:
            raise ValueError("id no puede estar vacío")
        if not isinstance(self.timestamp, int):
            raise TypeError("timestamp debe ser un entero")
        if self.timestamp < 0:
            raise ValueError("timestamp debe ser no negativo")
        if not isinstance(self.content, str):
            raise TypeError("content debe ser un string")
        if not self.content:
            raise ValueError("content no puede estar vacío")
        if self.metadata is not None and not isinstance(self.metadata, dict):
            raise TypeError("metadata debe ser un diccionario o None")
        if self.idempotency_key is not None and not isinstance(self.idempotency_key, str):
            raise TypeError("idempotency_key debe ser un string o None")
        if self.idempotency_key is not None and not self.idempotency_key:
            raise ValueError("idempotency_key no puede estar vacío")
        if self.topic_key is not None and not isinstance(self.topic_key, str):
            raise TypeError("topic_key debe ser un string o None")
        if self.topic_key is not None and not self.topic_key:
            raise ValueError("topic_key no puede estar vacío")
        if self.topic_key is not None and " " in self.topic_key:
            raise ValueError("topic_key no puede contener espacios")
        if not isinstance(self.revision_count, int):
            raise TypeError("revision_count debe ser un entero")
        if self.revision_count < 1:
            raise ValueError("revision_count debe ser al menos 1")
        if self.type is not None and not isinstance(self.type, str):
            raise TypeError("type debe ser un string o None")
        if self.type is not None and self.type not in self._ALLOWED_TYPES:
            raise ValueError(f"type debe ser uno de {sorted(self._ALLOWED_TYPES)} o None")
        if self.project is not None and not isinstance(self.project, str):
            raise TypeError("project debe ser un string o None")
        if self.project is not None and not self.project.strip():
            raise ValueError("project no puede estar vacío o solo espacios")
