"""AgentTemplate and TeamDefinition repositories for SQLite persistence."""

from __future__ import annotations

import json
import logging
import sqlite3
import time

from src.application.exceptions import RepositoryError
from src.domain.entities.agent_template import (
    AgentTemplate,
    TeamDefinition,
    TemplateScope,
    TemplateStatus,
)
from src.infrastructure.persistence.database import DatabaseConnection

_logger = logging.getLogger(__name__)

_TEMPLATE_COLUMNS = (
    "id, name, description, scope, status, model, system_prompt, "
    "tools, skills, output, default_reads, interactive, max_depth, "
    "file_path, team_id, created_at, updated_at"
)

_TEAM_COLUMNS = "id, name, description, agent_names, team_dir, created_at, updated_at"


class SqliteAgentTemplateRepository:
    """Repository for persisting and retrieving AgentTemplate entities."""

    __slots__ = ("_connection",)

    def __init__(self, connection: DatabaseConnection) -> None:
        self._connection = connection

    def save(self, template: AgentTemplate) -> None:
        """Insert or update a template, preserving created_at on update."""
        tools_json = json.dumps(template.tools)
        skills_json = json.dumps(template.skills)
        reads_json = json.dumps(template.default_reads)
        now_ms = int(time.time() * 1000)

        try:
            with self._connection as conn:
                conn.execute(
                    f"""INSERT INTO agent_templates
                       ({_TEMPLATE_COLUMNS})
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(id) DO UPDATE SET
                         name=excluded.name,
                         description=excluded.description,
                         scope=excluded.scope,
                         status=excluded.status,
                         model=excluded.model,
                         system_prompt=excluded.system_prompt,
                         tools=excluded.tools,
                         skills=excluded.skills,
                         output=excluded.output,
                         default_reads=excluded.default_reads,
                         interactive=excluded.interactive,
                         max_depth=excluded.max_depth,
                         file_path=excluded.file_path,
                         team_id=excluded.team_id,
                         updated_at=excluded.updated_at
                    """,
                    (
                        template.id,
                        template.name,
                        template.description,
                        template.scope.value,
                        template.status.value,
                        template.model,
                        template.system_prompt,
                        tools_json,
                        skills_json,
                        template.output,
                        reads_json,
                        int(template.interactive),
                        template.max_depth,
                        template.file_path,
                        template.team_id,
                        now_ms,
                        now_ms,
                    ),
                )
        except sqlite3.IntegrityError as e:
            raise RepositoryError(
                f"AgentTemplate with id '{template.id}' constraint violation",
                e,
            ) from e
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to save agent template: {e}", e) from e

    def get_by_id(self, template_id: str) -> AgentTemplate | None:
        """Retrieve an agent template by its ID."""
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    f"SELECT {_TEMPLATE_COLUMNS} FROM agent_templates WHERE id = ?",
                    (template_id,),
                )
                row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_template(row)
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to get agent template: {e}", e) from e

    def get_by_name(self, name: str) -> AgentTemplate | None:
        """Retrieve an agent template by its name."""
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    f"SELECT {_TEMPLATE_COLUMNS} FROM agent_templates WHERE name = ?",
                    (name,),
                )
                row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_template(row)
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to get agent template by name: {e}", e) from e

    def list_by_scope(self, scope: str) -> list[AgentTemplate]:
        """List templates by scope (case-insensitive)."""
        normalized = scope.upper()
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    f"SELECT {_TEMPLATE_COLUMNS} FROM agent_templates "
                    "WHERE scope = ? ORDER BY name",
                    (normalized,),
                )
                return [self._row_to_template(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to list agent templates by scope: {e}", e) from e

    def list_by_team(self, team_id: str) -> list[AgentTemplate]:
        """Retrieve all agent templates belonging to a team."""
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    f"SELECT {_TEMPLATE_COLUMNS} FROM agent_templates "
                    "WHERE team_id = ? ORDER BY name",
                    (team_id,),
                )
                return [self._row_to_template(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to list agent templates by team: {e}", e) from e

    def list_active(self) -> list[AgentTemplate]:
        """Retrieve all active agent templates."""
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    f"SELECT {_TEMPLATE_COLUMNS} FROM agent_templates "
                    "WHERE status = 'ACTIVE' ORDER BY name",
                )
                return [self._row_to_template(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to list active agent templates: {e}", e) from e

    def remove(self, template_id: str) -> bool:
        """Hard-delete an agent template by its ID.

        Returns True if a row was deleted, False if not found.
        """
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    "DELETE FROM agent_templates WHERE id = ?",
                    (template_id,),
                )
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to remove agent template: {e}", e) from e

    def update_status(self, template_id: str, status: str) -> bool:
        """Update an agent template's status using CAS.

        Only succeeds if the current status differs from the new one.
        Returns True if the row was updated, False otherwise.
        """
        now_ms = int(time.time() * 1000)
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    """UPDATE agent_templates SET status = ?, updated_at = ?
                       WHERE id = ? AND status != ?""",
                    (status, now_ms, template_id, status),
                )
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to update agent template status: {e}", e) from e

    @staticmethod
    def _row_to_template(row: sqlite3.Row) -> AgentTemplate:
        """Convert a database row to an AgentTemplate entity."""
        try:
            scope = TemplateScope(row["scope"])
        except ValueError as e:
            raise RepositoryError(
                f"Invalid scope '{row['scope']}' for template '{row['id']}'"
            ) from e
        try:
            status = TemplateStatus(row["status"])
        except ValueError as e:
            raise RepositoryError(
                f"Invalid status '{row['status']}' for template '{row['id']}'"
            ) from e
        return AgentTemplate(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            scope=scope,
            status=status,
            model=row["model"],
            system_prompt=row["system_prompt"],
            tools=_json_load_tuple(row["tools"]),
            skills=_json_load_tuple(row["skills"]),
            output=row["output"],
            default_reads=_json_load_tuple(row["default_reads"]),
            interactive=bool(row["interactive"]),
            max_depth=row["max_depth"],
            file_path=row["file_path"],
            team_id=row["team_id"] if row["team_id"] else None,
        )


class SqliteTeamRepository:
    """Repository for persisting and retrieving TeamDefinition entities."""

    __slots__ = ("_connection",)

    def __init__(self, connection: DatabaseConnection) -> None:
        self._connection = connection

    def save(self, team: TeamDefinition) -> None:
        """Insert or update a team definition, preserving created_at on update."""
        now_ms = int(time.time() * 1000)
        try:
            with self._connection as conn:
                conn.execute(
                    f"""INSERT INTO team_definitions
                       ({_TEAM_COLUMNS})
                       VALUES (?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(id) DO UPDATE SET
                         name=excluded.name,
                         description=excluded.description,
                         agent_names=excluded.agent_names,
                         team_dir=excluded.team_dir,
                         updated_at=excluded.updated_at
                    """,
                    (
                        team.id,
                        team.name,
                        team.description,
                        json.dumps(team.agent_names),
                        team.team_dir,
                        now_ms,
                        now_ms,
                    ),
                )
        except sqlite3.IntegrityError as e:
            raise RepositoryError(
                f"TeamDefinition with id '{team.id}' constraint violation",
                e,
            ) from e
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to save team definition: {e}", e) from e

    def get_by_id(self, team_id: str) -> TeamDefinition | None:
        """Retrieve a team definition by its ID."""
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    """SELECT id, name, description, agent_names, team_dir
                       FROM team_definitions WHERE id = ?""",
                    (team_id,),
                )
                row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_team(row)
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to get team definition: {e}", e) from e

    def get_by_name(self, name: str) -> TeamDefinition | None:
        """Retrieve a team definition by its name."""
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    """SELECT id, name, description, agent_names, team_dir
                       FROM team_definitions WHERE name = ?""",
                    (name,),
                )
                row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_team(row)
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to get team definition by name: {e}", e) from e

    def list_all(self) -> list[TeamDefinition]:
        """Retrieve all team definitions ordered by name."""
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    """SELECT id, name, description, agent_names, team_dir
                       FROM team_definitions ORDER BY name""",
                )
                return [self._row_to_team(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to list team definitions: {e}", e) from e

    def remove(self, team_id: str) -> bool:
        """Hard-delete a team definition by its ID.

        Returns True if a row was deleted, False if not found.
        """
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    "DELETE FROM team_definitions WHERE id = ?",
                    (team_id,),
                )
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to remove team definition: {e}", e) from e

    @staticmethod
    def _row_to_team(row: sqlite3.Row) -> TeamDefinition:
        """Convert a database row to a TeamDefinition entity."""
        return TeamDefinition(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            agent_names=_json_load_tuple(row["agent_names"]),
            team_dir=row["team_dir"],
        )


def _json_load_tuple(value: str | None) -> tuple[str, ...]:
    """Deserialize a JSON array string into a tuple of strings.

    Returns an empty tuple if the value is None, empty, or malformed.
    Logs a warning if JSON parsing fails to surface data corruption.
    """
    if value is None or value == "[]":
        return ()
    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, ValueError):
        _logger.warning("Malformed JSON in database column: %r", value[:50] if value else None)
        return ()
    if not isinstance(parsed, list):
        return ()
    return tuple(str(item) for item in parsed)
