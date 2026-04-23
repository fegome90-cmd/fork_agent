"""Unit tests for TemplateDirectory."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.domain.entities.agent_template import (
    AgentTemplate,
    TemplateScope,
)
from src.infrastructure.agent_templates.template_directory import (
    _SAFE_NAME_RE,
    TemplateDirectory,
    _parse_frontmatter,
)


def _make_template(
    name: str = "explorer",
    scope: TemplateScope = TemplateScope.USER,
    **overrides,
) -> AgentTemplate:
    defaults: dict = {
        "id": f"{scope.value.lower()}:{name}",
        "name": name,
        "description": "Test template",
        "scope": scope,
        "system_prompt": "You are a test agent.",
    }
    defaults.update(overrides)
    return AgentTemplate(**defaults)


class TestNameValidation:
    """Tests for template name validation via _SAFE_NAME_RE."""

    def test_valid_names(self) -> None:
        for name in ("explorer", "my-agent", "agent_1", "Agent-2_C"):
            assert _SAFE_NAME_RE.match(name) is not None, f"'{name}' should be valid"

    def test_rejects_path_traversal(self) -> None:
        assert _SAFE_NAME_RE.match("../etc/passwd") is None

    def test_rejects_spaces(self) -> None:
        assert _SAFE_NAME_RE.match("my agent") is None

    def test_rejects_slashes(self) -> None:
        assert _SAFE_NAME_RE.match("foo/bar") is None


class TestSaveTemplate:
    """Tests for TemplateDirectory.save_template()."""

    def test_writes_md_file_to_user_dir(self, tmp_path: Path) -> None:
        """save_template writes a .md file when scope is USER."""
        td = TemplateDirectory()
        t = _make_template(name="test-agent")

        # Monkey-patch the USER dir to tmp_path
        import src.infrastructure.agent_templates.template_directory as td_mod

        original = td_mod._USER_DIR
        td_mod._USER_DIR = tmp_path
        try:
            path = td.save_template(t)
            assert path.exists()
            assert path.name == "test-agent.md"
            content = path.read_text()
            assert "---" in content
            assert "test-agent" in content
        finally:
            td_mod._USER_DIR = original

    def test_rejects_builtin_scope(self, tmp_path: Path) -> None:
        td = TemplateDirectory()
        t = _make_template(scope=TemplateScope.BUILTIN)
        with pytest.raises(ValueError, match="BUILTIN"):
            td.save_template(t)

    def test_creates_directory_with_mode_0700(self, tmp_path: Path) -> None:
        td = TemplateDirectory()
        nested = tmp_path / "sub" / "agents"
        import src.infrastructure.agent_templates.template_directory as td_mod

        original = td_mod._USER_DIR
        td_mod._USER_DIR = nested
        try:
            td.save_template(_make_template(name="test"))
            assert nested.exists()
            # Check directory permissions (may be affected by umask on some systems)
            stat = nested.stat()
            mode = stat.st_mode & 0o777
            assert mode <= 0o700
        finally:
            td_mod._USER_DIR = original


class TestDeleteTemplate:
    """Tests for TemplateDirectory.delete_template()."""

    def test_removes_file(self, tmp_path: Path) -> None:
        td = TemplateDirectory()
        import src.infrastructure.agent_templates.template_directory as td_mod

        original = td_mod._USER_DIR
        td_mod._USER_DIR = tmp_path
        try:
            td.save_template(_make_template(name="to-delete"))
            assert (tmp_path / "to-delete.md").exists()

            result = td.delete_template("to-delete", TemplateScope.USER)
            assert result is True
            assert not (tmp_path / "to-delete.md").exists()
        finally:
            td_mod._USER_DIR = original

    def test_rejects_builtin_scope(self) -> None:
        td = TemplateDirectory()
        with pytest.raises(ValueError, match="BUILTIN"):
            td.delete_template("anything", TemplateScope.BUILTIN)

    def test_returns_false_for_missing_file(self, tmp_path: Path) -> None:
        td = TemplateDirectory()
        import src.infrastructure.agent_templates.template_directory as td_mod

        original = td_mod._USER_DIR
        td_mod._USER_DIR = tmp_path
        try:
            result = td.delete_template("nonexistent", TemplateScope.USER)
            assert result is False
        finally:
            td_mod._USER_DIR = original


class TestParseFrontmatter:
    """Tests for _parse_frontmatter()."""

    def test_parses_valid_yaml_frontmatter(self) -> None:
        content = """---
name: explorer
description: Explore codebase
model: zai/glm-5-turbo
tools: [memory, ctx]
interactive: true
max_depth: 2
---

You are an explorer."""
        fm, body = _parse_frontmatter(content)
        assert fm["name"] == "explorer"
        assert fm["description"] == "Explore codebase"
        assert fm["model"] == "zai/glm-5-turbo"
        assert fm["tools"] == ["memory", "ctx"]
        assert fm["interactive"] is True
        assert fm["max_depth"] == 2
        assert body == "You are an explorer."

    def test_missing_frontmatter_returns_empty_dict(self) -> None:
        content = "Just some text without frontmatter."
        fm, body = _parse_frontmatter(content)
        assert fm == {}
        assert body == "Just some text without frontmatter."

    def test_handles_negative_ints(self) -> None:
        content = """---
name: test
timeout: -1
---

body"""
        fm, body = _parse_frontmatter(content)
        assert fm["timeout"] == -1
