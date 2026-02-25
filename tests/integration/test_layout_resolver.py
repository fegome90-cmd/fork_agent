"""Integration tests for LayoutResolver.

These tests verify:
- NESTED layout path resolution
- OUTER_NESTED layout path resolution
- SIBLING layout path resolution
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.application.services.workspace.entities import LayoutType, WorkspaceConfig
from src.application.services.workspace.workspace_manager import LayoutResolver


class TestLayoutResolver:
    """Tests for LayoutResolver path resolution."""

    @pytest.fixture
    def nested_config(self) -> WorkspaceConfig:
        """Fixture for NESTED layout configuration."""
        return WorkspaceConfig(
            default_layout=LayoutType.NESTED,
            auto_cleanup=False,
            hooks_dir=None,
        )

    @pytest.fixture
    def outer_nested_config(self) -> WorkspaceConfig:
        """Fixture for OUTER_NESTED layout configuration."""
        return WorkspaceConfig(
            default_layout=LayoutType.OUTER_NESTED,
            auto_cleanup=False,
            hooks_dir=None,
        )

    @pytest.fixture
    def sibling_config(self) -> WorkspaceConfig:
        """Fixture for SIBLING layout configuration."""
        return WorkspaceConfig(
            default_layout=LayoutType.SIBLING,
            auto_cleanup=False,
            hooks_dir=None,
        )


class TestNestedLayoutResolution(TestLayoutResolver):
    """Tests for NESTED layout path resolution."""

    def test_nested_layout_resolves_correctly(self, nested_config: WorkspaceConfig) -> None:
        """Test NESTED layout resolves to .worktrees/<name> within repo."""
        resolver = LayoutResolver(nested_config)

        path = resolver.resolve_path("feature-branch", Path("/home/user/myrepo"))

        assert path == Path("/home/user/myrepo/.worktrees/feature-branch")

    def test_nested_layout_with_underscore_in_name(self, nested_config: WorkspaceConfig) -> None:
        """Test NESTED layout with underscore in branch name."""
        resolver = LayoutResolver(nested_config)

        path = resolver.resolve_path("feature_branch", Path("/home/user/myrepo"))

        assert path == Path("/home/user/myrepo/.worktrees/feature_branch")

    def test_nested_layout_with_slash_in_name(self, nested_config: WorkspaceConfig) -> None:
        """Test NESTED layout with slash in branch name (git branch naming)."""
        resolver = LayoutResolver(nested_config)

        # Git branch names can have slashes (e.g., "feature/sub-branch")
        path = resolver.resolve_path("feature/sub-branch", Path("/home/user/myrepo"))

        assert path == Path("/home/user/myrepo/.worktrees/feature/sub-branch")

    def test_nested_layout_deep_path(self, nested_config: WorkspaceConfig) -> None:
        """Test NESTED layout with deep repo path."""
        resolver = LayoutResolver(nested_config)

        path = resolver.resolve_path("develop", Path("/var/repos/my-awesome-project"))

        assert path == Path("/var/repos/my-awesome-project/.worktrees/develop")


class TestOuterNestedLayoutResolution(TestLayoutResolver):
    """Tests for OUTER_NESTED layout path resolution."""

    def test_outer_nested_layout_resolves_correctly(
        self, outer_nested_config: WorkspaceConfig
    ) -> None:
        """Test OUTER_NESTED layout resolves to ../<repo>.worktrees/<name>."""
        resolver = LayoutResolver(outer_nested_config)

        path = resolver.resolve_path("feature-branch", Path("/home/user/myrepo"))

        assert path == Path("/home/user/myrepo.worktrees/feature-branch")

    def test_outer_nested_layout_uses_repo_name(self, outer_nested_config: WorkspaceConfig) -> None:
        """Test OUTER_NESTED layout correctly uses repo name (not full path)."""
        resolver = LayoutResolver(outer_nested_config)

        path = resolver.resolve_path("bugfix", Path("/home/user/my-long-repo-name"))

        assert path == Path("/home/user/my-long-repo-name.worktrees/bugfix")

    def test_outer_nested_layout_parent_directory(
        self, outer_nested_config: WorkspaceConfig
    ) -> None:
        """Test OUTER_NESTED layout places worktrees in parent directory."""
        resolver = LayoutResolver(outer_nested_config)

        path = resolver.resolve_path("test-branch", Path("/var/git/project"))

        # Should be in /var/git, not /var/git/project
        assert path == Path("/var/git/project.worktrees/test-branch")
        assert path.parent.name == "project.worktrees"

    def test_outer_nested_layout_nested_repo(self, outer_nested_config: WorkspaceConfig) -> None:
        """Test OUTER_NESTED layout with deeply nested repo."""
        resolver = LayoutResolver(outer_nested_config)

        path = resolver.resolve_path("release-v1", Path("/home/user/code/projects/main"))

        # Parent is /home/user/code/projects
        assert path == Path("/home/user/code/projects/main.worktrees/release-v1")


class TestSiblingLayoutResolution(TestLayoutResolver):
    """Tests for SIBLING layout path resolution."""

    def test_sibling_layout_resolves_correctly(self, sibling_config: WorkspaceConfig) -> None:
        """Test SIBLING layout resolves to ../<repo>-<name>."""
        resolver = LayoutResolver(sibling_config)

        path = resolver.resolve_path("feature-branch", Path("/home/user/myrepo"))

        assert path == Path("/home/user/myrepo-feature-branch")

    def test_sibling_layout_uses_repo_name(self, sibling_config: WorkspaceConfig) -> None:
        """Test SIBLING layout correctly uses repo name."""
        resolver = LayoutResolver(sibling_config)

        path = resolver.resolve_path("experiment", Path("/home/user/test-repo"))

        assert path == Path("/home/user/test-repo-experiment")

    def test_sibling_layout_places_beside_repo(self, sibling_config: WorkspaceConfig) -> None:
        """Test SIBLING layout places worktrees in parent directory, beside repo."""
        resolver = LayoutResolver(sibling_config)

        path = resolver.resolve_path("hotfix", Path("/home/user/myproject"))

        # Should be /home/user/myproject-hotfix (beside /home/user/myproject)
        assert path == Path("/home/user/myproject-hotfix")
        assert path.parent == Path("/home/user")

    def test_sibling_layout_complex_repo_name(self, sibling_config: WorkspaceConfig) -> None:
        """Test SIBLING layout with complex repo name."""
        resolver = LayoutResolver(sibling_config)

        path = resolver.resolve_path("dev", Path("/var/www/html/my-web-app"))

        assert path == Path("/var/www/html/my-web-app-dev")


class TestLayoutResolverEdgeCases:
    """Edge case tests for LayoutResolver."""

    def test_resolver_with_custom_layout_override(self) -> None:
        """Test resolver can use custom layout via config."""
        config = WorkspaceConfig(
            default_layout=LayoutType.NESTED,
            auto_cleanup=True,
            hooks_dir=Path("/tmp/hooks"),
        )
        resolver = LayoutResolver(config)

        # The default should be NESTED
        path = resolver.resolve_path("test", Path("/repo"))

        assert path == Path("/repo/.worktrees/test")

    def test_layout_type_enum_values(self) -> None:
        """Test that LayoutType enum has expected values."""
        assert LayoutType.NESTED.value == ".worktrees/<branch>/"
        assert LayoutType.OUTER_NESTED.value == "../<repo>.worktrees/<branch>/"
        assert LayoutType.SIBLING.value == "../<repo>-<branch>/"
