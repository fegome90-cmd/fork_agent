"""Sync entities for mutation tracking and chunk management."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SyncChunk:
    """Represents a sync chunk that has been imported.

    Attributes:
        chunk_id: Unique identifier for the chunk (e.g., "fork_agent_chunk_01")
        source: Source identifier (e.g., "fork_agent", "engram")
        imported_at: Unix timestamp in milliseconds when chunk was imported
        observation_count: Number of observations in this chunk
        checksum: SHA256 checksum of the chunk file
    """

    chunk_id: str
    source: str
    imported_at: int
    observation_count: int
    checksum: str

    def __post_init__(self) -> None:
        if not isinstance(self.chunk_id, str):
            raise TypeError("chunk_id must be a string")
        if not self.chunk_id:
            raise ValueError("chunk_id cannot be empty")
        if not isinstance(self.source, str):
            raise TypeError("source must be a string")
        if not self.source:
            raise ValueError("source cannot be empty")
        if not isinstance(self.imported_at, int):
            raise TypeError("imported_at must be an integer")
        if self.imported_at < 0:
            raise ValueError("imported_at must be non-negative")
        if not isinstance(self.observation_count, int):
            raise TypeError("observation_count must be an integer")
        if self.observation_count < 0:
            raise ValueError("observation_count must be non-negative")
        if not isinstance(self.checksum, str):
            raise TypeError("checksum must be a string")
        if not self.checksum:
            raise ValueError("checksum cannot be empty")


@dataclass(frozen=True)
class SyncMutation:
    """Represents a mutation in the change journal.

    Attributes:
        seq: Auto-incrementing sequence number
        entity: Entity type (e.g., "observation", "session")
        entity_key: Unique key for the entity (e.g., observation ID, topic_key)
        op: Operation type (insert, update, delete)
        payload: JSON string containing the mutation data
        source: Source of the mutation
        project: Project scope for the mutation
        created_at: Unix timestamp in milliseconds
    """

    seq: int
    entity: str
    entity_key: str
    op: str
    payload: str
    source: str
    project: str
    created_at: int

    def __post_init__(self) -> None:
        if not isinstance(self.seq, int):
            raise TypeError("seq must be an integer")
        if self.seq < 0:
            raise ValueError("seq must be non-negative")
        if not isinstance(self.entity, str):
            raise TypeError("entity must be a string")
        if not self.entity:
            raise ValueError("entity cannot be empty")
        if not isinstance(self.entity_key, str):
            raise TypeError("entity_key must be a string")
        if not self.entity_key:
            raise ValueError("entity_key cannot be empty")
        if not isinstance(self.op, str):
            raise TypeError("op must be a string")
        if self.op not in ("insert", "update", "delete"):
            raise ValueError("op must be one of: insert, update, delete")
        if not isinstance(self.payload, str):
            raise TypeError("payload must be a string")
        if not isinstance(self.source, str):
            raise TypeError("source must be a string")
        if not self.source:
            raise ValueError("source cannot be empty")
        if not isinstance(self.project, str):
            raise TypeError("project must be a string")
        if not isinstance(self.created_at, int):
            raise TypeError("created_at must be an integer")
        if self.created_at < 0:
            raise ValueError("created_at must be non-negative")


@dataclass(frozen=True)
class SyncStatus:
    """Global sync status singleton.

    Attributes:
        last_export_at: Unix timestamp of last export
        last_import_at: Unix timestamp of last import
        last_export_seq: Sequence number at last export
        mutation_count: Total number of mutations recorded
    """

    last_export_at: int | None = None
    last_import_at: int | None = None
    last_export_seq: int = 0
    mutation_count: int = 0

    def __post_init__(self) -> None:
        if self.last_export_at is not None and not isinstance(self.last_export_at, int):
            raise TypeError("last_export_at must be an integer or None")
        if self.last_import_at is not None and not isinstance(self.last_import_at, int):
            raise TypeError("last_import_at must be an integer or None")
        if not isinstance(self.last_export_seq, int):
            raise TypeError("last_export_seq must be an integer")
        if self.last_export_seq < 0:
            raise ValueError("last_export_seq must be non-negative")
        if not isinstance(self.mutation_count, int):
            raise TypeError("mutation_count must be an integer")
        if self.mutation_count < 0:
            raise ValueError("mutation_count must be non-negative")
