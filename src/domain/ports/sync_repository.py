"""Ports (Protocols) for sync operations."""
from __future__ import annotations

from typing import Protocol

from src.domain.entities.sync import SyncChunk, SyncMutation, SyncStatus


class SyncRepository(Protocol):
    """Protocol for sync persistence operations."""

    def record_chunk(self, chunk: SyncChunk) -> None:
        """Record a successfully imported chunk.

        Args:
            chunk: The sync chunk to record.
        """
        ...

    def get_chunk_by_id(self, chunk_id: str) -> SyncChunk | None:
        """Get a chunk by its ID.

        Args:
            chunk_id: The unique chunk identifier.

        Returns:
            The sync chunk if found, None otherwise.
        """
        ...

    def list_chunks(self, source: str | None = None) -> list[SyncChunk]:
        """List all recorded chunks, optionally filtered by source.

        Args:
            source: Optional source filter.

        Returns:
            List of sync chunks ordered by imported_at descending.
        """
        ...

    def record_mutation(
        self,
        entity: str,
        entity_key: str,
        op: str,
        payload: str,
        source: str = "local",
        project: str = "",
    ) -> int:
        """Record a mutation in the journal.

        Args:
            entity: Entity type (e.g., "observation")
            entity_key: Unique key for the entity
            op: Operation type (insert, update, delete)
            payload: JSON string containing mutation data
            source: Source of the mutation
            project: Project scope

        Returns:
            The sequence number of the recorded mutation.
        """
        ...

    def get_mutations_since(self, seq: int, limit: int | None = None) -> list[SyncMutation]:
        """Get mutations since a given sequence number.

        Args:
            seq: The sequence number to start from (exclusive)
            limit: Optional maximum number of mutations to return

        Returns:
            List of mutations ordered by sequence number.
        """
        ...

    def get_latest_seq(self) -> int:
        """Get the latest sequence number.

        Returns:
            The highest sequence number recorded, or 0 if none.
        """
        ...

    def get_status(self) -> SyncStatus:
        """Get the global sync status.

        Returns:
            The current sync status.
        """
        ...

    def update_status(
        self,
        last_export_at: int | None = None,
        last_import_at: int | None = None,
        last_export_seq: int | None = None,
        mutation_count: int | None = None,
    ) -> None:
        """Update the global sync status.

        Args:
            last_export_at: Timestamp of last export
            last_import_at: Timestamp of last import
            last_export_seq: Sequence number at last export
            mutation_count: Total mutation count
        """
        ...
