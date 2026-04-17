"""Observation repository for SQLite persistence."""

from __future__ import annotations

import json
import re
import sqlite3
from typing import Any

from src.application.exceptions import ObservationNotFoundError, RepositoryError
from src.domain.entities.observation import Observation
from src.infrastructure.persistence.database import DatabaseConnection

_SELECT_COLUMNS = (
    "id, timestamp, content, metadata, idempotency_key, "
    "topic_key, project, type, revision_count, session_id"
)
_SELECT_COLUMNS_PREFIXED = (
    "o.id, o.timestamp, o.content, o.metadata, o.idempotency_key, "
    "o.topic_key, o.project, o.type, o.revision_count, o.session_id"
)


class ObservationRepository:
    """Repository for persisting and retrieving Observation entities.

    Provides CRUD operations and full-text search using SQLite with FTS5.
    """

    __slots__ = ("_connection",)

    def __init__(self, connection: DatabaseConnection) -> None:
        self._connection = connection

    @staticmethod
    def _normalize_project(project: str | None) -> str | None:
        if project is None:
            return None
        return project.lower().strip()

    def create(self, observation: Observation) -> None:
        """Store a new observation in the database.

        Args:
            observation: The observation entity to persist.

        Raises:
            RepositoryError: If the observation ID already exists or database error occurs.
        """
        metadata_json = self._serialize_metadata(observation.metadata)
        project = self._normalize_project(observation.project)

        try:
            with self._connection as conn:
                conn.execute(
                    f"""INSERT INTO observations ({_SELECT_COLUMNS})
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        observation.id,
                        observation.timestamp,
                        observation.content,
                        metadata_json,
                        observation.idempotency_key,
                        observation.topic_key,
                        project,
                        observation.type,
                        observation.revision_count,
                        observation.session_id,
                    ),
                )
        except sqlite3.IntegrityError as e:
            raise RepositoryError(
                f"Observation with id '{observation.id}' already exists",
                e,
            ) from e
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to create observation: {e}", e) from e

    def save_event(
        self,
        content: str,
        metadata: dict[str, Any],
        idempotency_key: str,
    ) -> str:
        """Save an event observation with idempotency guarantee.

        This method is designed for structured events (workflow, agents, etc.)
        and guarantees idempotency via the idempotency_key.

        If an event with the same idempotency_key already exists, this returns
        the existing observation ID without creating a duplicate.

        Args:
            content: Event content/description
            metadata: Event metadata (should follow MemoryEventMetadata contract)
            idempotency_key: Unique key for deduplication

        Returns:
            The observation ID (existing if duplicate, new otherwise)

        Raises:
            RepositoryError: If database error occurs (not duplicate idempotency)
        """
        import time
        import uuid

        # Check if already exists (idempotency check)
        existing = self.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            return existing.id

        # Create new observation
        timestamp = int(time.time() * 1000)
        observation_id = str(uuid.uuid4())

        observation = Observation(
            id=observation_id,
            timestamp=timestamp,
            content=content,
            metadata=metadata,
            idempotency_key=idempotency_key,
        )

        self.create(observation)
        return observation_id

    def get_by_idempotency_key(self, idempotency_key: str) -> Observation | None:
        """Get an observation by its idempotency key.

        Args:
            idempotency_key: The unique idempotency key

        Returns:
            Observation if found, None otherwise
        """
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    f"SELECT {_SELECT_COLUMNS} FROM observations WHERE idempotency_key = ?",
                    (idempotency_key,),
                )
                row = cursor.fetchone()
                if row is None:
                    return None
                return self._row_to_observation(row)
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to get observation by idempotency_key: {e}", e) from e

    def get_by_id(self, observation_id: str) -> Observation:
        """Retrieve an observation by its ID.

        Args:
            observation_id: The unique identifier of the observation.

        Returns:
            The observation entity if found.

        Raises:
            ObservationNotFoundError: If no observation exists with the given ID.
        """
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    f"SELECT {_SELECT_COLUMNS} FROM observations WHERE id = ?",
                    (observation_id,),
                )
                row = cursor.fetchone()

            if row is None:
                raise ObservationNotFoundError(f"Observation '{observation_id}' not found")

            return self._row_to_observation(row)
        except ObservationNotFoundError:
            raise
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to get observation: {e}", e) from e

    def get_all(
        self,
        limit: int | None = None,
        offset: int | None = None,
        type: str | None = None,
    ) -> list[Observation]:
        """Retrieve observations ordered by timestamp descending with optional pagination.

        Args:
            limit: Optional maximum number of observations to return. If None, no limit is applied.
            offset: Optional number of observations to skip before starting to return results.
            type: Optional type filter to narrow results.

        Returns:
            List of observation entities.
        """
        try:
            if type is not None:
                sql = f"SELECT {_SELECT_COLUMNS} FROM observations WHERE type = ? ORDER BY timestamp DESC"
                params: list[str | int] = [type]
            else:
                sql = f"SELECT {_SELECT_COLUMNS} FROM observations ORDER BY timestamp DESC"
                params = []

            if limit is not None:
                sql += " LIMIT ?"
                params.append(limit)
            if offset is not None:
                sql += " OFFSET ?"
                params.append(offset)

            with self._connection as conn:
                cursor = conn.execute(sql, params)
                rows = cursor.fetchall()

            return [self._row_to_observation(row) for row in rows]
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to get observations: {e}", e) from e

    def update(self, observation: Observation) -> None:
        metadata_json = self._serialize_metadata(observation.metadata)
        project = self._normalize_project(observation.project)

        try:
            with self._connection as conn:
                cursor = conn.execute(
                    """UPDATE observations
                       SET timestamp = ?, content = ?, metadata = ?, topic_key = ?,
                           project = ?, type = ?, revision_count = ?,
                           session_id = ?
                       WHERE id = ?""",
                    (
                        observation.timestamp,
                        observation.content,
                        metadata_json,
                        observation.topic_key,
                        project,
                        observation.type,
                        observation.revision_count,
                        observation.session_id,
                        observation.id,
                    ),
                )

                if cursor.rowcount == 0:
                    raise ObservationNotFoundError(f"Observation '{observation.id}' not found")
        except ObservationNotFoundError:
            raise
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to update observation: {e}", e) from e

    def delete(self, observation_id: str) -> None:
        """Delete an observation by its ID.

        Args:
            observation_id: The unique identifier of the observation to delete.

        Raises:
            ObservationNotFoundError: If no observation exists with the given ID.
            RepositoryError: If a database error occurs.
        """
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    "DELETE FROM observations WHERE id = ?",
                    (observation_id,),
                )

                if cursor.rowcount == 0:
                    raise ObservationNotFoundError(f"Observation '{observation_id}' not found")
        except ObservationNotFoundError:
            raise
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to delete observation: {e}", e) from e

    def search(self, query: str, limit: int | None = None) -> list[Observation]:
        """Search observations using full-text search.

        Args:
            query: The search query string.
            limit: Optional maximum number of results to return.

        Returns:
            List of matching observation entities, ordered by timestamp descending.
        """
        try:
            sanitized_query = self._sanitize_fts_query(query)
            if not sanitized_query:
                return []
            sql = f"""
                SELECT {_SELECT_COLUMNS_PREFIXED}
                FROM observations o
                JOIN observations_fts fts ON o.rowid = fts.rowid
                WHERE observations_fts MATCH ?
                ORDER BY o.timestamp DESC
            """
            params: list[str | int] = [sanitized_query]

            if limit is not None:
                sql += " LIMIT ?"
                params.append(limit)

            with self._connection as conn:
                cursor = conn.execute(sql, params)
                rows = cursor.fetchall()

            return [self._row_to_observation(row) for row in rows]
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to search observations: {e}", e) from e

    def get_by_timestamp_range(self, start: int, end: int) -> list[Observation]:
        """Retrieve observations within a timestamp range.

        Args:
            start: Start timestamp (inclusive).
            end: End timestamp (inclusive).

        Returns:
            List of observations within the range, ordered by timestamp descending.
        """
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    f"""SELECT {_SELECT_COLUMNS}
                       FROM observations
                       WHERE timestamp >= ? AND timestamp <= ?
                       ORDER BY timestamp DESC""",
                    (start, end),
                )
                rows = cursor.fetchall()

            return [self._row_to_observation(row) for row in rows]
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to get observations by range: {e}", e) from e

    def upsert_topic_key(self, observation: Observation) -> Observation:
        """Update an existing observation matched by topic_key+project.

        The caller (service) must verify the record exists before calling this.
        Uses UPDATE directly since partial unique indexes don't support ON CONFLICT.

        Args:
            observation: The observation with updated fields.

        Returns:
            The updated observation with incremented revision_count.
        """
        project = self._normalize_project(observation.project)
        metadata_json = json.dumps(observation.metadata) if observation.metadata else "{}"

        sql = f"""
            UPDATE observations SET
                content = ?,
                metadata = COALESCE(?, metadata),
                timestamp = ?,
                type = COALESCE(?, type),
                session_id = COALESCE(?, session_id),
                revision_count = revision_count + 1
            WHERE topic_key = ? AND project = ?
            RETURNING {_SELECT_COLUMNS}
        """
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    sql,
                    (
                        observation.content,
                        metadata_json,
                        observation.timestamp,
                        observation.type,
                        observation.session_id,
                        observation.topic_key,
                        project,
                    ),
                )
                row = cursor.fetchone()
                if row is None:
                    raise RepositoryError(
                        f"No observation found for topic_key={observation.topic_key} "
                        f"project={project}"
                    )
                return self._row_to_observation(row)
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to upsert topic_key: {e}", e) from e

    def get_by_topic_key(self, topic_key: str, project: str) -> Observation | None:
        """Get an observation by topic_key and project.

        Args:
            topic_key: The topic key to search for.
            project: The project scope.

        Returns:
            Observation if found, None otherwise.
        """
        project = self._normalize_project(project) or project
        sql = f"SELECT {_SELECT_COLUMNS} FROM observations WHERE topic_key = ? AND project = ?"
        try:
            with self._connection as conn:
                cursor = conn.execute(sql, (topic_key, project))
                row = cursor.fetchone()
                return self._row_to_observation(row) if row else None
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to get observation by topic_key: {e}", e) from e

    def _row_to_observation(self, row: sqlite3.Row) -> Observation:
        """Convert a database row to an Observation entity."""
        metadata_dict = json.loads(row["metadata"]) if row["metadata"] else {}

        # New fields with backward compat — try DB column, fall back to metadata
        column_names = row.keys()
        topic_key = row["topic_key"] if "topic_key" in column_names else None
        project = (row["project"] if "project" in column_names else None) or metadata_dict.get(
            "project"
        )
        type_ = (row["type"] if "type" in column_names else None) or metadata_dict.get("type")
        revision_count = (row["revision_count"] if "revision_count" in column_names else None) or 1
        session_id = row["session_id"] if "session_id" in column_names else None

        return Observation(
            id=row["id"],
            timestamp=row["timestamp"],
            content=row["content"],
            metadata=metadata_dict,
            idempotency_key=row["idempotency_key"] if "idempotency_key" in column_names else None,
            project=project,
            type=type_,
            topic_key=topic_key,
            revision_count=revision_count,
            session_id=session_id,
        )

    def _serialize_metadata(self, metadata: dict[str, Any] | None) -> str | None:
        """Serialize metadata dict to JSON string."""
        return json.dumps(metadata) if metadata is not None else None

    def _deserialize_metadata(self, metadata_json: str | None) -> dict[str, Any] | None:
        """Deserialize JSON string to metadata dict."""
        return json.loads(metadata_json) if metadata_json is not None else None

    def _sanitize_fts_query(self, query: str) -> str:
        if not query or not query.strip():
            return ""
        sanitized = re.sub(r'[\*\^"\'\(\)\-]', " ", query)
        reserved = {"AND", "OR", "NOT", "NEAR", "COLUMN"}
        words = sanitized.split()
        return " ".join(w for w in words if w.upper() not in reserved)
