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
            "learning-batch",
            "workflow-event",
            "security",
            "performance",
            "preference",
            "file_ops",
            "file-ops",
            "artifacts-index",
        }
    )

    id: str
    timestamp: int
    content: str
    title: str | None = None
    metadata: dict[str, Any] | None = None
    idempotency_key: str | None = None
    project: str | None = None
    type: str | None = None
    topic_key: str | None = None
    revision_count: int = 1
    session_id: str | None = None

    _MAX_TOPIC_KEY_LENGTH: ClassVar[int] = 128

    def __post_init__(self) -> None:
        if not isinstance(self.id, str):
            raise TypeError("id must be a string")
        if not self.id:
            raise ValueError("id must not be empty")
        if not isinstance(self.timestamp, int):
            raise TypeError("timestamp must be an integer")
        if self.timestamp < 0:
            raise ValueError("timestamp must be non-negative")
        if not isinstance(self.content, str):
            raise TypeError("content must be a string")
        # Null bytes are silently truncated by SQLite — reject early (RIPPER-001/002)
        if "\x00" in self.content:
            raise ValueError("content must not contain null bytes (\\x00)")
        if not self.content:
            raise ValueError("content must not be empty")
        if self.metadata is not None and not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dict or None")
        if self.idempotency_key is not None and not isinstance(self.idempotency_key, str):
            raise TypeError("idempotency_key must be a string or None")
        if self.idempotency_key is not None and not self.idempotency_key:
            raise ValueError("idempotency_key must not be empty")
        if self.topic_key is not None and not isinstance(self.topic_key, str):
            raise TypeError("topic_key must be a string or None")
        if self.topic_key is not None and not self.topic_key:
            raise ValueError("topic_key must not be empty")
        if self.topic_key is not None and " " in self.topic_key:
            raise ValueError("topic_key must not contain spaces")
        if self.topic_key is not None and "\x00" in self.topic_key:
            raise ValueError("topic_key must not contain null bytes")
        if self.topic_key is not None and len(self.topic_key) > self._MAX_TOPIC_KEY_LENGTH:
            raise ValueError(
                f"topic_key must not exceed {self._MAX_TOPIC_KEY_LENGTH} characters "
                f"(got {len(self.topic_key)})"
            )
        if not isinstance(self.revision_count, int):
            raise TypeError("revision_count must be an integer")
        if self.revision_count < 1:
            raise ValueError("revision_count must be at least 1")
        if self.type is not None and not isinstance(self.type, str):
            raise TypeError("type must be a string or None")
        if self.type is not None and self.type not in self._ALLOWED_TYPES:
            raise ValueError(f"type must be one of {sorted(self._ALLOWED_TYPES)} or None")
        if self.project is not None and not isinstance(self.project, str):
            raise TypeError("project must be a string or None")
        if self.project is not None and not self.project.strip():
            raise ValueError("project must not be empty or whitespace-only")
        if self.project is not None and "\x00" in self.project:
            raise ValueError("project must not contain null bytes")
