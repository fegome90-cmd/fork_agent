"""Unit tests for SqliteAgentTemplateRepository and SqliteTeamRepository."""

from __future__ import annotations

import time
from pathlib import Path

from src.domain.entities.agent_template import (
    AgentTemplate,
    TeamDefinition,
    TemplateScope,
    TemplateStatus,
)
from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
from src.infrastructure.persistence.repositories.agent_template_repository import (
    SqliteAgentTemplateRepository,
    SqliteTeamRepository,
)

_MIGRATION = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "src/infrastructure/persistence/migrations/026_create_agent_templates_table.sql"
)


def _make_template_repo(tmp_path: Path) -> SqliteAgentTemplateRepository:
    db_path = tmp_path / "test.db"
    config = DatabaseConfig(db_path=db_path)
    conn = DatabaseConnection(config=config)
    with conn as c:
        c.executescript(_MIGRATION.read_text())
    return SqliteAgentTemplateRepository(connection=conn)


def _make_team_repo(tmp_path: Path) -> SqliteTeamRepository:
    db_path = tmp_path / "test.db"
    config = DatabaseConfig(db_path=db_path)
    conn = DatabaseConnection(config=config)
    with conn as c:
        c.executescript(_MIGRATION.read_text())
    return SqliteTeamRepository(connection=conn)


def _template(**overrides) -> AgentTemplate:
    defaults: dict = {
        "id": "t1",
        "name": "explorer",
        "description": "Explore codebase",
        "scope": TemplateScope.USER,
    }
    defaults.update(overrides)
    return AgentTemplate(**defaults)


def _team(**overrides) -> TeamDefinition:
    defaults: dict = {
        "id": "tm1",
        "name": "review-team",
        "description": "Code review team",
    }
    defaults.update(overrides)
    return TeamDefinition(**defaults)


class TestTemplateSaveGet:
    """Tests for save/get roundtrips."""

    def test_save_and_get_by_id(self, tmp_path: Path) -> None:
        repo = _make_template_repo(tmp_path)
        t = _template()
        repo.save(t)
        result = repo.get_by_id("t1")
        assert result is not None
        assert result.id == "t1"
        assert result.name == "explorer"
        assert result.description == "Explore codebase"
        assert result.scope == TemplateScope.USER
        assert result.status == TemplateStatus.ACTIVE

    def test_save_and_get_by_name(self, tmp_path: Path) -> None:
        repo = _make_template_repo(tmp_path)
        t = _template()
        repo.save(t)
        result = repo.get_by_name("explorer")
        assert result is not None
        assert result.name == "explorer"
        assert result.id == "t1"

    def test_get_by_id_returns_none_for_missing(self, tmp_path: Path) -> None:
        repo = _make_template_repo(tmp_path)
        assert repo.get_by_id("nonexistent") is None

    def test_get_by_name_returns_none_for_missing(self, tmp_path: Path) -> None:
        repo = _make_template_repo(tmp_path)
        assert repo.get_by_name("nonexistent") is None

    def test_save_preserves_created_at_on_upsert(self, tmp_path: Path) -> None:
        """UPSERT should not change created_at on second save."""
        repo = _make_template_repo(tmp_path)
        t = _template()
        repo.save(t)

        with repo._connection as conn:
            row = conn.execute(
                "SELECT created_at FROM agent_templates WHERE id = ?", ("t1",)
            ).fetchone()
        first_created_at = row["created_at"]

        time.sleep(0.01)  # ensure different timestamp
        updated = _template(description="Updated description")
        repo.save(updated)

        with repo._connection as conn:
            row = conn.execute(
                "SELECT created_at, updated_at FROM agent_templates WHERE id = ?", ("t1",)
            ).fetchone()
        assert row["created_at"] == first_created_at
        assert row["updated_at"] >= first_created_at


class TestTemplateList:
    """Tests for list operations."""

    def test_list_by_scope_filters_correctly(self, tmp_path: Path) -> None:
        repo = _make_template_repo(tmp_path)
        repo.save(_template(id="t1", name="a", scope=TemplateScope.USER))
        repo.save(_template(id="t2", name="b", scope=TemplateScope.BUILTIN))
        repo.save(_template(id="t3", name="c", scope=TemplateScope.PROJECT))

        user = repo.list_by_scope("USER")
        assert len(user) == 1
        assert user[0].name == "a"

        builtin = repo.list_by_scope("BUILTIN")
        assert len(builtin) == 1
        assert builtin[0].name == "b"

    def test_list_active_excludes_disabled(self, tmp_path: Path) -> None:
        repo = _make_template_repo(tmp_path)
        repo.save(_template(id="t1", name="active", status=TemplateStatus.ACTIVE))
        repo.save(_template(id="t2", name="disabled", status=TemplateStatus.DISABLED))

        active = repo.list_active()
        assert len(active) == 1
        assert active[0].name == "active"

    def test_list_by_team_filters_by_team_id(self, tmp_path: Path) -> None:
        repo = _make_template_repo(tmp_path)
        repo.save(_template(id="t1", name="a", team_id="team-1"))
        repo.save(_template(id="t2", name="b", team_id="team-2"))
        repo.save(_template(id="t3", name="c", team_id=None))

        team1 = repo.list_by_team("team-1")
        assert len(team1) == 1
        assert team1[0].name == "a"

        team2 = repo.list_by_team("team-2")
        assert len(team2) == 1
        assert team2[0].name == "b"


class TestTemplateUpdateStatus:
    """Tests for CAS update_status."""

    def test_update_status_cas_succeeds(self, tmp_path: Path) -> None:
        repo = _make_template_repo(tmp_path)
        repo.save(_template(id="t1", name="a", status=TemplateStatus.ACTIVE))

        result = repo.update_status("t1", "DISABLED")
        assert result is True

        updated = repo.get_by_id("t1")
        assert updated is not None
        assert updated.status == TemplateStatus.DISABLED

    def test_update_status_cas_fails_when_status_matches(self, tmp_path: Path) -> None:
        """CAS fails if current status already equals new status."""
        repo = _make_template_repo(tmp_path)
        repo.save(_template(id="t1", name="a", status=TemplateStatus.DISABLED))

        result = repo.update_status("t1", "DISABLED")
        assert result is False

    def test_update_status_returns_false_for_missing(self, tmp_path: Path) -> None:
        repo = _make_template_repo(tmp_path)
        result = repo.update_status("nonexistent", "DISABLED")
        assert result is False


class TestTemplateRemove:
    """Tests for remove operation."""

    def test_remove_returns_true(self, tmp_path: Path) -> None:
        repo = _make_template_repo(tmp_path)
        repo.save(_template())
        assert repo.remove("t1") is True
        assert repo.get_by_id("t1") is None

    def test_remove_returns_false_for_missing(self, tmp_path: Path) -> None:
        repo = _make_template_repo(tmp_path)
        assert repo.remove("nonexistent") is False


class TestTeamRepository:
    """Tests for SqliteTeamRepository."""

    def test_save_and_list_all(self, tmp_path: Path) -> None:
        repo = _make_team_repo(tmp_path)
        repo.save(_team(id="tm1", name="alpha"))
        repo.save(_team(id="tm2", name="beta"))

        teams = repo.list_all()
        assert len(teams) == 2
        names = [t.name for t in teams]
        assert "alpha" in names
        assert "beta" in names

    def test_get_by_name(self, tmp_path: Path) -> None:
        repo = _make_team_repo(tmp_path)
        repo.save(_team())
        result = repo.get_by_name("review-team")
        assert result is not None
        assert result.id == "tm1"

    def test_get_by_name_returns_none(self, tmp_path: Path) -> None:
        repo = _make_team_repo(tmp_path)
        assert repo.get_by_name("nonexistent") is None

    def test_remove(self, tmp_path: Path) -> None:
        repo = _make_team_repo(tmp_path)
        repo.save(_team())
        assert repo.remove("tm1") is True
        assert repo.get_by_id("tm1") is None

    def test_remove_returns_false_for_missing(self, tmp_path: Path) -> None:
        repo = _make_team_repo(tmp_path)
        assert repo.remove("nonexistent") is False
