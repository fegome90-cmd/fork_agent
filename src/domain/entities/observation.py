"""Observation entity for memory storage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Observation:
    """Immutable observation entity for memory storage.

    Represents a single observation/memory entry with content,
    timestamp, and optional metadata.

    Attributes:
        id: Unique identifier for the observation.
        timestamp: Unix timestamp in milliseconds.
        content: The main content/text of the observation.
        metadata: Optional JSON-serializable metadata dictionary.
        idempotency_key: Optional unique key for deduplication.
    """

    id: str
    timestamp: int
    content: str
    metadata: dict[str, Any] | None = None
    idempotency_key: str | None = None

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
