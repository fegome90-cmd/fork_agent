"""Unit tests for TemplateService."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from src.application.services.template_service import TemplateService
from src.domain.entities.agent_template import (
    AgentTemplate,
    TeamDefinition,
    TemplateScope,
    TemplateStatus,
)
from src.domain.ports.agent_template_repository import (
    AgentTemplateRepository,
    TeamRepository,
)
from src.infrastructure.agent_templates.template_directory import TemplateDirectory


def _make_service():
    repo = MagicMock(spec=AgentTemplateRepository)
    team_repo = MagicMock(spec=TeamRepository)
    template_dir = MagicMock(spec=TemplateDirectory)
    service = TemplateService(repo, team_repo, template_dir)
    return service, repo, team_repo, template_dir


def _template(
    id: str = "t1",
    name: str = "explorer",
    status: TemplateStatus = TemplateStatus.ACTIVE,
    **overrides,
) -> AgentTemplate:
    defaults: dict = {
        "id": id,
        "name": name,
        "description": "Test",
        "scope": TemplateScope.USER,
        "status": status,
    }
    defaults.update(overrides)
    return AgentTemplate(**defaults)


class TestSaveTemplate:
    """Tests for TemplateService.save_template()."""

    def test_save_creates_template_in_db(self) -> None:
        svc, repo, _, template_dir = _make_service()
        repo.get_by_name.return_value = None
        template_dir.save_template.return_value = Path("/tmp/explorer.md")

        result = svc.save_template(name="explorer", description="Explore codebase")

        assert result.name == "explorer"
        repo.save.assert_called_once()
        saved_arg = repo.save.call_args[0][0]
        assert saved_arg.name == "explorer"

    def test_save_updates_existing_template(self) -> None:
        svc, repo, _, template_dir = _make_service()
        existing = _template(id="old-id", name="explorer")
        repo.get_by_name.return_value = existing
        template_dir.save_template.return_value = Path("/tmp/explorer.md")

        result = svc.save_template(name="explorer", description="Updated desc")

        assert result.id == "old-id"
        repo.save.assert_called_once()


class TestGetTemplate:
    """Tests for TemplateService.get_template()."""

    def test_finds_by_name(self) -> None:
        svc, repo, _, _ = _make_service()
        expected = _template()
        repo.get_by_name.return_value = expected

        result = svc.get_template("explorer")

        assert result is expected
        repo.get_by_name.assert_called_once_with("explorer")
        repo.get_by_id.assert_not_called()

    def test_falls_back_to_id(self) -> None:
        svc, repo, _, _ = _make_service()
        repo.get_by_name.return_value = None
        expected = _template()
        repo.get_by_id.return_value = expected

        result = svc.get_template("t1")

        assert result is expected
        repo.get_by_id.assert_called_once_with("t1")

    def test_returns_none_when_not_found(self) -> None:
        svc, repo, _, _ = _make_service()
        repo.get_by_name.return_value = None
        repo.get_by_id.return_value = None

        result = svc.get_template("nonexistent")

        assert result is None


class TestListTemplates:
    """Tests for TemplateService.list_templates()."""

    def test_returns_active_only_by_default(self) -> None:
        svc, repo, _, _ = _make_service()
        active = _template(id="t1", name="active", status=TemplateStatus.ACTIVE)
        repo.list_active.return_value = [active]

        result = svc.list_templates()

        assert len(result) == 1
        assert result[0].name == "active"
        repo.list_active.assert_called_once()

    def test_with_team_id_filter(self) -> None:
        svc, repo, _, _ = _make_service()
        t1 = _template(id="t1", name="a", team_id="team-1")
        repo.list_by_team.return_value = [t1]

        result = svc.list_templates(team_id="team-1")

        assert len(result) == 1
        repo.list_by_team.assert_called_once_with("team-1")

    def test_with_scope_filter(self) -> None:
        svc, repo, _, _ = _make_service()
        repo.list_by_scope.return_value = [
            _template(id="t1", name="a", scope=TemplateScope.BUILTIN),
        ]

        result = svc.list_templates(scope="BUILTIN")

        assert len(result) == 1
        repo.list_by_scope.assert_called_once_with("BUILTIN")


class TestToggleTemplate:
    """Tests for TemplateService.toggle_template()."""

    def test_toggle_active_to_disabled(self) -> None:
        svc, repo, _, _ = _make_service()
        active = _template(id="t1", name="explorer", status=TemplateStatus.ACTIVE)
        disabled = _template(id="t1", name="explorer", status=TemplateStatus.DISABLED)
        repo.get_by_name.return_value = active
        repo.update_status.return_value = True
        repo.get_by_id.return_value = disabled

        result = svc.toggle_template("explorer")

        assert result is not None
        assert result.status == TemplateStatus.DISABLED
        repo.update_status.assert_called_once_with("t1", "DISABLED")

    def test_toggle_disabled_to_active(self) -> None:
        svc, repo, _, _ = _make_service()
        disabled = _template(id="t1", name="explorer", status=TemplateStatus.DISABLED)
        active = _template(id="t1", name="explorer", status=TemplateStatus.ACTIVE)
        repo.get_by_name.return_value = disabled
        repo.update_status.return_value = True
        repo.get_by_id.return_value = active

        result = svc.toggle_template("explorer")

        assert result is not None
        assert result.status == TemplateStatus.ACTIVE

    def test_toggle_returns_none_for_missing(self) -> None:
        svc, repo, _, _ = _make_service()
        repo.get_by_name.return_value = None

        result = svc.toggle_template("nonexistent")

        assert result is None


class TestDeleteTemplate:
    """Tests for TemplateService.delete_template()."""

    def test_removes_from_db(self) -> None:
        svc, repo, _, template_dir = _make_service()
        t = _template()
        repo.get_by_name.return_value = t
        repo.remove.return_value = True

        result = svc.delete_template("explorer")

        assert result is True
        template_dir.delete_template.assert_called_once_with("explorer", TemplateScope.USER)
        repo.remove.assert_called_once_with("t1")

    def test_returns_false_for_missing(self) -> None:
        svc, repo, _, _ = _make_service()
        repo.get_by_name.return_value = None

        result = svc.delete_template("nonexistent")

        assert result is False


class TestTeamOperations:
    """Tests for team CRUD operations."""

    def test_create_team_and_list(self) -> None:
        svc, _, team_repo, _ = _make_service()
        svc.create_team(name="review-team", description="Reviewers")
        svc.create_team(name="deploy-team", description="Deployers")

        team_repo.list_all.return_value = [
            TeamDefinition(id="tm1", name="review-team", description="Reviewers"),
            TeamDefinition(id="tm2", name="deploy-team", description="Deployers"),
        ]
        teams = svc.list_teams()
        assert len(teams) == 2
        assert teams[0].name == "review-team"
        team_repo.save.assert_called()
        team_repo.list_all.assert_called_once()

    def test_get_team_by_name(self) -> None:
        svc, _, team_repo, _ = _make_service()
        expected = TeamDefinition(id="tm1", name="review-team", description="Reviewers")
        team_repo.get_by_name.return_value = expected

        result = svc.get_team("review-team")

        assert result is expected
        team_repo.get_by_name.assert_called_once_with("review-team")

    def test_delete_team(self) -> None:
        svc, _, team_repo, _ = _make_service()
        team = TeamDefinition(id="tm1", name="review-team", description="Reviewers")
        team_repo.get_by_name.return_value = team
        team_repo.remove.return_value = True

        result = svc.delete_team("review-team")

        assert result is True
        team_repo.remove.assert_called_once_with("tm1")
