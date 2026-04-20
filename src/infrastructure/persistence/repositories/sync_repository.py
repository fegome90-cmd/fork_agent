"""Sync repository implementation for SQLite persistence."""

from __future__ import annotations

import sqlite3
from typing import Any

from src.application.exceptions import RepositoryError
from src.domain.entities.sync import SyncChunk, SyncMutation, SyncStatus
from src.infrastructure.persistence.database import DatabaseConnection


class SyncRepositoryImpl:
    """Repository for sync operations: chunks, mutations, and status."""

    __slots__ = ("_connection",)

    def __init__(self, connection: DatabaseConnection) -> None:
        self._connection = connection

    def record_chunk(self, chunk: SyncChunk) -> None:
        """Record a successfully imported chunk."""
        try:
            with self._connection as conn:
                conn.execute(
                    """
                    INSERT INTO sync_chunks (chunk_id, source, imported_at, observation_count, checksum)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        chunk.chunk_id,
                        chunk.source,
                        chunk.imported_at,
                        chunk.observation_count,
                        chunk.checksum,
                    ),
                )
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to record chunk: {e}", e) from e

    def get_chunk_by_id(self, chunk_id: str) -> SyncChunk | None:
        """Get a chunk by its ID."""
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    """
                    SELECT chunk_id, source, imported_at, observation_count, checksum
                    FROM sync_chunks WHERE chunk_id = ?
                    """,
                    (chunk_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    return None
                return self._row_to_chunk(row)
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to get chunk by id: {e}", e) from e

    def list_chunks(self, source: str | None = None) -> list[SyncChunk]:
        """List all recorded chunks, optionally filtered by source."""
        try:
            with self._connection as conn:
                if source:
                    cursor = conn.execute(
                        """
                        SELECT chunk_id, source, imported_at, observation_count, checksum
                        FROM sync_chunks WHERE source = ? ORDER BY imported_at DESC
                        """,
                        (source,),
                    )
                else:
                    cursor = conn.execute(
                        """
                        SELECT chunk_id, source, imported_at, observation_count, checksum
                        FROM sync_chunks ORDER BY imported_at DESC
                        """
                    )
                rows = cursor.fetchall()
                return [self._row_to_chunk(row) for row in rows]
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to list chunks: {e}", e) from e

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

        Returns: The sequence number of the recorded mutation.
        """
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO sync_mutations (entity, entity_key, op, payload, source, project)
                    VALUES (?, ?, ?, ?, ?, ?)
                    RETURNING seq
                    """,
                    (entity, entity_key, op, payload, source, project),
                )
                row = cursor.fetchone()
                if row is None:
                    raise RepositoryError(
                        "Failed to get sequence number from mutation insert",
                    )
                # Increment mutation_count in sync_status
                conn.execute("UPDATE sync_status SET mutation_count = mutation_count + 1")
                return row["seq"]
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to record mutation: {e}", e) from e

    def get_mutations_since(self, seq: int, limit: int | None = None) -> list[SyncMutation]:
        """Get mutations since a given sequence number."""
        try:
            with self._connection as conn:
                sql = """
                SELECT seq, entity, entity_key, op, payload, source, project, created_at
                FROM sync_mutations WHERE seq > ? ORDER BY seq
                """
                params: list[int] = [seq]
                if limit:
                    sql += " LIMIT ?"
                    params.append(limit)
                cursor = conn.execute(sql, params)
                rows = cursor.fetchall()
                return [self._row_to_mutation(row) for row in rows]
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to get mutations since: {e}", e) from e

    def get_latest_seq(self) -> int:
        """Get the latest sequence number."""
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    "SELECT COALESCE(MAX(seq), 0) as latest_seq FROM sync_mutations",
                )
                row = cursor.fetchone()
                return row["latest_seq"] if row else 0
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to get latest seq: {e}", e) from e

    def get_status(self) -> SyncStatus:
        """Get the global sync status."""
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    """
                    SELECT last_export_at, last_import_at, last_export_seq, mutation_count
                    FROM sync_status WHERE id = 1
                    """,
                )
                row = cursor.fetchone()
                if row is None:
                    return SyncStatus()
                return SyncStatus(
                    last_export_at=row["last_export_at"],
                    last_import_at=row["last_import_at"],
                    last_export_seq=row["last_export_seq"],
                    mutation_count=row["mutation_count"],
                )
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to get sync status: {e}", e) from e

    def update_status(
        self,
        last_export_at: int | None = None,
        last_import_at: int | None = None,
        last_export_seq: int | None = None,
        mutation_count: int | None = None,
    ) -> None:
        """Update the global sync status."""
        try:
            with self._connection as conn:
                # Build SET clause dynamically
                set_parts: list[str] = []
                params: list[Any] = []
                if last_export_at is not None:
                    set_parts.append("last_export_at = ?")
                    params.append(last_export_at)
                if last_import_at is not None:
                    set_parts.append("last_import_at = ?")
                    params.append(last_import_at)
                if last_export_seq is not None:
                    set_parts.append("last_export_seq = ?")
                    params.append(last_export_seq)
                if mutation_count is not None:
                    set_parts.append("mutation_count = ?")
                    params.append(mutation_count)
                if not set_parts:
                    return
                set_clause = ", ".join(set_parts)
                conn.execute(
                    f"UPDATE sync_status SET {set_clause} WHERE id = 1",
                    params,
                )
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to update sync status: {e}", e) from e

    def _row_to_chunk(self, row: sqlite3.Row) -> SyncChunk:
        """Convert a database row to a SyncChunk entity."""
        return SyncChunk(
            chunk_id=row["chunk_id"],
            source=row["source"],
            imported_at=row["imported_at"],
            observation_count=row["observation_count"],
            checksum=row["checksum"],
        )

    def _row_to_mutation(self, row: sqlite3.Row) -> SyncMutation:
        """Convert a database row to a SyncMutation entity."""
        return SyncMutation(
            seq=row["seq"],
            entity=row["entity"],
            entity_key=row["entity_key"],
            op=row["op"],
            payload=row["payload"],
            source=row["source"],
            project=row["project"],
            created_at=row["created_at"],
        )
