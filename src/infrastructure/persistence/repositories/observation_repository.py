"""Observation repository for SQLite persistence."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from src.application.exceptions import ObservationNotFoundError, RepositoryError
from src.domain.entities.observation import Observation
from src.infrastructure.persistence.database import DatabaseConnection


class ObservationRepository:
    """Repository for persisting and retrieving Observation entities.

    Provides CRUD operations and full-text search using SQLite with FTS5.
    """

    __slots__ = ("_connection",)

    def __init__(self, connection: DatabaseConnection) -> None:
        self._connection = connection

    def create(self, observation: Observation) -> None:
        """Store a new observation in the database.

        Args:
            observation: The observation entity to persist.

        Raises:
            RepositoryError: If the observation ID already exists or database error occurs.
        """
        metadata_json = self._serialize_metadata(observation.metadata)

        try:
            with self._connection as conn:
                conn.execute(
                    """INSERT INTO observations (id, timestamp, content, metadata)
                       VALUES (?, ?, ?, ?)""",
                    (observation.id, observation.timestamp, observation.content, metadata_json),
                )
        except sqlite3.IntegrityError as e:
            raise RepositoryError(
                f"Observation with id '{observation.id}' already exists",
                e,
            ) from e
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to create observation: {e}", e) from e

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
                    "SELECT id, timestamp, content, metadata FROM observations WHERE id = ?",
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

    def get_all(self) -> list[Observation]:
        """Retrieve all observations ordered by timestamp descending.

        Returns:
            List of all observation entities.
        """
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    "SELECT id, timestamp, content, metadata FROM observations ORDER BY timestamp DESC"
                )
                rows = cursor.fetchall()

            return [self._row_to_observation(row) for row in rows]
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to get observations: {e}", e) from e

    def update(self, observation: Observation) -> None:
        """Update an existing observation.

        Args:
            observation: The observation entity with updated values.

        Raises:
            ObservationNotFoundError: If no observation exists with the given ID.
            RepositoryError: If a database error occurs.
        """
        metadata_json = self._serialize_metadata(observation.metadata)

        try:
            with self._connection as conn:
                cursor = conn.execute(
                    """UPDATE observations
                       SET timestamp = ?, content = ?, metadata = ?
                       WHERE id = ?""",
                    (observation.timestamp, observation.content, metadata_json, observation.id),
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
            sql = """
                SELECT o.id, o.timestamp, o.content, o.metadata
                FROM observations o
                JOIN observations_fts fts ON o.rowid = fts.rowid
                WHERE observations_fts MATCH ?
                ORDER BY o.timestamp DESC
            """
            params: list[str | int] = [query]

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
                    """SELECT id, timestamp, content, metadata
                       FROM observations
                       WHERE timestamp >= ? AND timestamp <= ?
                       ORDER BY timestamp DESC""",
                    (start, end),
                )
                rows = cursor.fetchall()

            return [self._row_to_observation(row) for row in rows]
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to get observations by range: {e}", e) from e

    def _row_to_observation(self, row: sqlite3.Row) -> Observation:
        """Convert a database row to an Observation entity."""
        metadata = self._deserialize_metadata(row["metadata"])
        return Observation(
            id=row["id"],
            timestamp=row["timestamp"],
            content=row["content"],
            metadata=metadata,
        )

    def _serialize_metadata(self, metadata: dict[str, Any] | None) -> str | None:
        """Serialize metadata dict to JSON string."""
        return json.dumps(metadata) if metadata is not None else None

    def _deserialize_metadata(self, metadata_json: str | None) -> dict[str, Any] | None:
        """Deserialize JSON string to metadata dict."""
        return json.loads(metadata_json) if metadata_json is not None else None
