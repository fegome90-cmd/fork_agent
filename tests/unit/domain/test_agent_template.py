"""Unit tests for AgentTemplate entity."""

from __future__ import annotations

import pytest

from src.domain.entities.agent_template import (
    AgentTemplate,
    TeamDefinition,
    TemplateScope,
    TemplateStatus,
)


class TestTemplateScope:
    """Tests for TemplateScope enum."""

    def test_all_scopes_exist(self) -> None:
        expected = {"BUILTIN", "USER", "PROJECT"}
        actual = {s.value for s in TemplateScope}
        assert actual == expected

    def test_str_enum_behavior(self) -> None:
        assert TemplateScope.BUILTIN == "BUILTIN"
        assert TemplateScope.USER == "USER"
        assert TemplateScope.PROJECT == "PROJECT"


class TestTemplateStatus:
    """Tests for TemplateStatus enum."""

    def test_all_statuses_exist(self) -> None:
        expected = {"ACTIVE", "DISABLED"}
        actual = {s.value for s in TemplateStatus}
        assert actual == expected


class TestAgentTemplateCreation:
    """Tests for AgentTemplate entity creation."""

    def test_valid_creation_all_fields(self) -> None:
        t = AgentTemplate(
            id="t1",
            name="explorer",
            description="Explore codebase",
            scope=TemplateScope.USER,
            model="zai/glm-5-turbo",
            system_prompt="You are an explorer",
            tools=["memory", "ctx"],
            skills=["codebase-explorer"],
            output="/tmp/explorer.md",
            default_reads=["README.md"],
            interactive=True,
            max_depth=2,
            file_path="/tmp/explorer.md",
            team_id="team-1",
        )
        assert t.id == "t1"
        assert t.name == "explorer"
        assert t.description == "Explore codebase"
        assert t.scope == TemplateScope.USER
        assert t.model == "zai/glm-5-turbo"
        assert t.system_prompt == "You are an explorer"
        assert t.tools == ["memory", "ctx"]
        assert t.skills == ["codebase-explorer"]
        assert t.output == "/tmp/explorer.md"
        assert t.default_reads == ["README.md"]
        assert t.interactive is True
        assert t.max_depth == 2
        assert t.team_id == "team-1"

    def test_default_values(self) -> None:
        t = AgentTemplate(
            id="t1",
            name="explorer",
            description="Explore codebase",
            scope=TemplateScope.USER,
        )
        assert t.model == ""
        assert t.system_prompt == ""
        assert t.tools == ()
        assert t.skills == ()
        assert t.output == ""
        assert t.default_reads == ()
        assert t.interactive is True
        assert t.max_depth == 1
        assert t.file_path == ""
        assert t.team_id is None
        assert t.status == TemplateStatus.ACTIVE

    def test_invalid_id_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="id"):
            AgentTemplate(
                id="",
                name="explorer",
                description="desc",
                scope=TemplateScope.USER,
            )

    def test_invalid_id_non_string_raises(self) -> None:
        with pytest.raises(ValueError, match="id"):
            AgentTemplate(
                id=123,  # type: ignore[arg-type]
                name="explorer",
                description="desc",
                scope=TemplateScope.USER,
            )

    def test_invalid_name_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="name"):
            AgentTemplate(
                id="t1",
                name="",
                description="desc",
                scope=TemplateScope.USER,
            )

    def test_invalid_name_non_string_raises(self) -> None:
        with pytest.raises(ValueError, match="name"):
            AgentTemplate(
                id="t1",
                name=42,  # type: ignore[arg-type]
                description="desc",
                scope=TemplateScope.USER,
            )

    def test_team_id_none_vs_set(self) -> None:
        t_none = AgentTemplate(id="t1", name="a", description="d", scope=TemplateScope.USER)
        assert t_none.team_id is None

        t_set = AgentTemplate(
            id="t2", name="b", description="d", scope=TemplateScope.USER, team_id="team-1"
        )
        assert t_set.team_id == "team-1"

    def test_frozen(self) -> None:
        t = AgentTemplate(id="t1", name="a", description="d", scope=TemplateScope.USER)
        with pytest.raises(AttributeError):
            t.name = "new"  # type: ignore[misc]


class TestAgentTemplateMethods:
    """Tests for AgentTemplate methods."""

    def test_is_active_true_for_active(self) -> None:
        t = AgentTemplate(
            id="t1",
            name="a",
            description="d",
            scope=TemplateScope.USER,
            status=TemplateStatus.ACTIVE,
        )
        assert t.is_active() is True

    def test_is_active_false_for_disabled(self) -> None:
        t = AgentTemplate(
            id="t1",
            name="a",
            description="d",
            scope=TemplateScope.USER,
            status=TemplateStatus.DISABLED,
        )
        assert t.is_active() is False


class TestToFrontmatterDict:
    """Tests for to_frontmatter_dict()."""

    def test_includes_expected_keys(self) -> None:
        t = AgentTemplate(
            id="t1",
            name="explorer",
            description="Explore",
            scope=TemplateScope.USER,
            model="zai/glm-5-turbo",
            tools=["memory"],
            skills=["codebase-explorer"],
            output="/tmp/out.md",
            default_reads=["README.md"],
            interactive=False,
            max_depth=3,
        )
        fm = t.to_frontmatter_dict()
        assert fm["name"] == "explorer"
        assert fm["description"] == "Explore"
        assert fm["model"] == "zai/glm-5-turbo"
        assert fm["tools"] == ["memory"]
        assert fm["skills"] == ["codebase-explorer"]
        assert fm["output"] == "/tmp/out.md"
        assert fm["default_reads"] == ["README.md"]
        assert fm["interactive"] is False
        assert fm["max_depth"] == 3

    def test_excludes_team_id_when_none(self) -> None:
        t = AgentTemplate(id="t1", name="a", description="d", scope=TemplateScope.USER)
        fm = t.to_frontmatter_dict()
        assert "team_id" not in fm

    def test_includes_team_id_when_set(self) -> None:
        t = AgentTemplate(
            id="t1",
            name="a",
            description="d",
            scope=TemplateScope.USER,
            team_id="team-1",
        )
        fm = t.to_frontmatter_dict()
        assert fm["team_id"] == "team-1"

    def test_excludes_internal_fields(self) -> None:
        """id, scope, status, system_prompt, file_path are not in frontmatter."""
        t = AgentTemplate(id="t1", name="a", description="d", scope=TemplateScope.USER)
        fm = t.to_frontmatter_dict()
        for key in ("id", "scope", "status", "system_prompt", "file_path"):
            assert key not in fm


class TestTeamDefinition:
    """Tests for TeamDefinition entity."""

    def test_basic_creation(self) -> None:
        team = TeamDefinition(
            id="tm1",
            name="review-team",
            description="Code review team",
            agent_names=["reviewer", "writer"],
            team_dir="/tmp/teams/review",
        )
        assert team.id == "tm1"
        assert team.name == "review-team"
        assert team.description == "Code review team"
        assert team.agent_names == ["reviewer", "writer"]
        assert team.team_dir == "/tmp/teams/review"

    def test_default_agent_names(self) -> None:
        team = TeamDefinition(id="tm1", name="team", description="d")
        assert team.agent_names == ()

    def test_invalid_id_raises(self) -> None:
        with pytest.raises(ValueError, match="id"):
            TeamDefinition(id="", name="team", description="d")

    def test_invalid_name_raises(self) -> None:
        with pytest.raises(ValueError, match="name"):
            TeamDefinition(id="tm1", name="", description="d")
