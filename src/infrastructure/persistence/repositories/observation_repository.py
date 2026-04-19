"""Observation repository for SQLite persistence."""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from typing import Any

from src.application.exceptions import ObservationNotFoundError, RepositoryError
from src.domain.entities.observation import Observation
from src.domain.ports.sync_repository import SyncRepository
from src.infrastructure.persistence.database import DatabaseConnection

logger = logging.getLogger(__name__)

_SELECT_COLUMNS = (
    "id, timestamp, content, title, metadata, idempotency_key, "
    "topic_key, project, type, revision_count, session_id"
)
_SELECT_COLUMNS_PREFIXED = (
    "o.id, o.timestamp, o.content, o.title, o.metadata, o.idempotency_key, "
    "o.topic_key, o.project, o.type, o.revision_count, o.session_id"
)


class ObservationRepository:
    """Repository for persisting and retrieving Observation entities.

    Provides CRUD operations and full-text search using SQLite with FTS5.
    """

    __slots__ = ("_connection", "_sync_repo", "_mutation_recording_enabled")

    def __init__(
        self,
        connection: DatabaseConnection,
        sync_repo: SyncRepository | None = None,
    ) -> None:
        self._connection = connection
        self._sync_repo = sync_repo
        self._mutation_recording_enabled = True

    @staticmethod
    def _normalize_project(project: str | None) -> str | None:
        if project is None:
            return None
        from src.application.services.memory_service import MemoryService

        return MemoryService._normalize_project_name(project)

    @staticmethod
    def _normalize_topic_key(topic_key: str) -> str:
        """Normalize topic_key for case-insensitive comparison."""
        return topic_key.lower().strip()

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
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        observation.id,
                        observation.timestamp,
                        observation.content,
                        observation.title,
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

        self._record_mutation(
            "insert",
            observation.id,
            observation.project,
            {
                "id": observation.id,
                "content": observation.content,
                "metadata": observation.metadata,
                "type": observation.type,
                "topic_key": observation.topic_key,
            },
        )

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
        project: str | None = None,
    ) -> list[Observation]:
        """Retrieve observations ordered by timestamp descending with optional pagination.

        Args:
            limit: Optional maximum number of observations to return. If None, no limit is applied.
            offset: Optional number of observations to skip before starting to return results.
            type: Optional type filter to narrow results.
            project: Optional project filter to narrow results.

        Returns:
            List of observation entities.
        """
        try:
            conditions: list[str] = []
            params: list[str | int] = []

            if type is not None:
                conditions.append("type = ?")
                params.append(type)
            if project is not None:
                normalized = self._normalize_project(project)
                if normalized:
                    conditions.append("project = ?")
                    params.append(normalized)

            where_clause = (" WHERE " + " AND ".join(conditions)) if conditions else ""
            sql = f"SELECT {_SELECT_COLUMNS} FROM observations{where_clause} ORDER BY timestamp DESC"

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

    def _record_mutation(
        self,
        op: str,
        entity_key: str,
        project: str | None,
        payload: dict[str, Any],
    ) -> None:
        """Record a mutation in the sync journal if sync_repo is configured."""
        if not self._mutation_recording_enabled or self._sync_repo is None:
            return
        try:
            self._sync_repo.record_mutation(
                entity="observation",
                entity_key=entity_key,
                op=op,
                payload=json.dumps(payload),
                source="local",
                project=project or "",
            )
        except Exception:
            logger.debug(
                "Mutation recording failed for %s: %s",
                entity_key,
                op,
                exc_info=True,
            )

    def disable_mutation_recording(self) -> None:
        """Disable mutation recording (for import operations)."""
        self._mutation_recording_enabled = False

    def enable_mutation_recording(self) -> None:
        """Enable mutation recording (default state)."""
        self._mutation_recording_enabled = True

    def update(self, observation: Observation) -> None:
        metadata_json = self._serialize_metadata(observation.metadata)
        project = self._normalize_project(observation.project)

        try:
            with self._connection as conn:
                cursor = conn.execute(
                    """UPDATE observations
                       SET timestamp = ?, content = ?, title = ?, metadata = ?, topic_key = ?,
                           project = ?, type = ?, revision_count = ?,
                           session_id = ?, idempotency_key = ?
                       WHERE id = ?""",
                    (
                        observation.timestamp,
                        observation.content,
                        observation.title,
                        metadata_json,
                        observation.topic_key,
                        project,
                        observation.type,
                        observation.revision_count,
                        observation.session_id,
                        observation.idempotency_key,
                        observation.id,
                    ),
                )

                if cursor.rowcount == 0:
                    raise ObservationNotFoundError(f"Observation '{observation.id}' not found")
        except ObservationNotFoundError:
            raise
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to update observation: {e}", e) from e

        self._record_mutation(
            "update",
            observation.id,
            observation.project,
            {
                "id": observation.id,
                "content": observation.content,
                "metadata": observation.metadata,
                "type": observation.type,
                "topic_key": observation.topic_key,
            },
        )

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

        self._record_mutation("delete", observation_id, None, {"id": observation_id})

    def search(self, query: str, limit: int | None = None, project: str | None = None) -> list[Observation]:
        """Search observations using full-text search.

        Args:
            query: The search query string.
            limit: Optional maximum number of results to return.
            project: Optional project filter to narrow results.

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
            """
            params: list[str | int] = [sanitized_query]

            if project is not None:
                normalized = self._normalize_project(project)
                if normalized:
                    sql += " AND o.project = ?"
                    params.append(normalized)

            sql += " ORDER BY o.timestamp DESC"

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
        """Update an existing observation matched by topic_key and project.

        The caller (service) must verify the record exists before calling this.
        When project is provided, matches both topic_key and project to avoid
        UNIQUE constraint violations on the (topic_key, project) index.
        When project is None, matches topic_key only (project-agnostic upsert).

        Args:
            observation: The observation with updated fields.

        Returns:
            The updated observation with incremented revision_count.

        Raises:
            RepositoryError: If topic_key is None/empty or database error occurs.
        """
        if observation.topic_key is None:
            raise RepositoryError("topic_key is required for upsert")
        normalized_key = self._normalize_topic_key(observation.topic_key)
        if not normalized_key:
            raise RepositoryError("topic_key cannot be empty for upsert")

        project = self._normalize_project(observation.project)
        metadata_json = json.dumps(observation.metadata) if observation.metadata else "{}"

        # Use a subquery to pick exactly ONE row to update, avoiding
        # UNIQUE constraint violations when multiple rows share the same
        # topic_key with different projects.
        # Prefer same-project match, fall back to project=NULL.
        if project:
            where_clause = """id = (
                SELECT id FROM observations
                WHERE LOWER(topic_key) = ? AND (project = ? OR project IS NULL)
                ORDER BY project = ? DESC
                LIMIT 1
            )"""
            where_params: tuple[str, ...] = (normalized_key, project, project)
        else:
            where_clause = "LOWER(topic_key) = ?"
            where_params = (normalized_key,)

        sql = f"""
            UPDATE observations SET
                content = ?,
                title = ?,
                metadata = ?,
                timestamp = ?,
                type = ?,
                session_id = ?,
                project = ?,
                topic_key = ?,
                revision_count = revision_count + 1
            WHERE {where_clause}
            RETURNING {_SELECT_COLUMNS}
        """
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    sql,
                    (
                        observation.content,
                        observation.title,
                        metadata_json,
                        observation.timestamp,
                        observation.type,
                        observation.session_id,
                        project,
                        normalized_key,
                        *where_params,
                    ),
                )
                row = cursor.fetchone()
                if row is None:
                    raise RepositoryError(
                        f"No observation found for topic_key={observation.topic_key}"
                    )
                result = self._row_to_observation(row)
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to upsert topic_key: {e}", e) from e

        self._record_mutation(
            "update",
            observation.topic_key or "",
            observation.project,
            {
                "id": result.id,
                "content": observation.content,
                "metadata": observation.metadata,
                "type": observation.type,
                "topic_key": observation.topic_key,
            },
        )

        return result

    def get_by_topic_key(self, topic_key: str, project: str | None) -> Observation | None:
        """Get an observation by topic_key, preferring same-project match.

        When project is provided, first tries to match both topic_key and project.
        Falls back to project-agnostic match if no same-project entry exists.

        Args:
            topic_key: The topic key to search for.
            project: Preferred project for matching.

        Returns:
            Observation if found, None otherwise.
        """
        normalized_topic = self._normalize_topic_key(topic_key)
        try:
            with self._connection as conn:
                if project:
                    # Prefer same-project match first
                    sql = f"SELECT {_SELECT_COLUMNS} FROM observations WHERE LOWER(topic_key) = ? AND (project = ? OR project IS NULL) ORDER BY project = ? DESC"
                    cursor = conn.execute(sql, (normalized_topic, project, project))
                    row = cursor.fetchone()
                else:
                    sql = f"SELECT {_SELECT_COLUMNS} FROM observations WHERE LOWER(topic_key) = ?"
                    cursor = conn.execute(sql, (normalized_topic,))
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
        type_ = row["type"] if "type" in column_names else None
        # Normalize hyphenated type values to underscored (e.g. "file-ops" -> "file_ops")
        if type_ is not None and type_ not in Observation._ALLOWED_TYPES:
            normalized = type_.replace("-", "_")
            type_ = normalized if normalized in Observation._ALLOWED_TYPES else None  # Unknown type, discard
        if type_ is None and isinstance(metadata_dict, dict):
            meta_type = metadata_dict.get("type")
            if isinstance(meta_type, str):
                if meta_type in Observation._ALLOWED_TYPES:
                    type_ = meta_type
                else:
                    normalized = meta_type.replace("-", "_")
                    if normalized in Observation._ALLOWED_TYPES:
                        type_ = normalized
        revision_count = (row["revision_count"] if "revision_count" in column_names else None) or 1
        session_id = row["session_id"] if "session_id" in column_names else None

        return Observation(
            id=row["id"],
            timestamp=row["timestamp"],
            content=row["content"],
            title=row["title"],
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
        # Strip characters that break FTS5 syntax
        sanitized = re.sub(r'[\*\^"\'\'\(\)\-\/\\\:\.\{\}\[\]\~\!\<\>\+\=\@\,\;]', " ", query)
        reserved = {"AND", "OR", "NOT", "NEAR", "COLUMN"}
        words = sanitized.split()
        # Append * to each token for prefix matching (e.g. "FastAP" -> "FastAP*")
        return " ".join(f"{w}*" for w in words if w.upper() not in reserved)

    def save_prompt(
        self,
        content: str,
        session_id: str | None,
        role: str | None = None,
        model: str | None = None,
        provider: str | None = None,
    ) -> int:
        """Insert a prompt into the prompts table. Returns the prompt ID."""
        _role = role or ""
        _model = model or ""
        _provider = provider or ""
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    "INSERT INTO prompts (prompt_text, role, model, provider, session_id) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (content, _role, _model, _provider, session_id),
                )
                return cursor.lastrowid or 0
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to save prompt: {e}", e) from e

    def merge_projects(
        self,
        canonical: str,
        sources: list[str],
    ) -> dict[str, Any]:
        """Merge observations and sessions from source projects into canonical.

        Transactional: all or nothing. Returns stats dict.
        """
        obs_updated = 0
        sessions_updated = 0
        try:
            with self._connection as conn:
                canonical_normalized = self._normalize_project(canonical)
                for src in sources:
                    src_normalized = self._normalize_project(src)
                    cur = conn.execute(
                        "UPDATE observations SET project = ? WHERE project = ?",
                        (canonical_normalized, src_normalized),
                    )
                    obs_updated += cur.rowcount
                    cur = conn.execute(
                        "UPDATE sessions SET project = ? WHERE project = ?",
                        (canonical_normalized, src_normalized),
                    )
                    sessions_updated += cur.rowcount
            return {
                "canonical": canonical,
                "sources_merged": sources,
                "observations_updated": obs_updated,
                "sessions_updated": sessions_updated,
            }
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to merge projects: {e}", e) from e
