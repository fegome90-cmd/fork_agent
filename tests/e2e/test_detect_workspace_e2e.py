"""End-to-end tests for workspace detect command.

Tests:
- Detect workspace from its path
- Detect workspace from a subdirectory inside it
- Detect returns None when not inside a workspace
- Detect returns None from the main repo
- Detect after creation and removal cycle
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.application.services.workspace.workspace_manager import WorkspaceManager


class TestDetectWorkspaceE2E:
    """E2E tests for workspace detection."""

    def test_detect_workspace_from_worktree_path(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test that detecting from a worktree path returns the workspace."""
        workspace = workspace_manager.create_workspace("detect-direct")

        detected = workspace_manager.detect_workspace(workspace.path)

        assert detected is not None
        assert detected.name == "detect-direct"
        assert detected.path == workspace.path

    def test_detect_workspace_from_subdirectory(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test that detecting from a subdirectory inside a worktree works."""
        workspace = workspace_manager.create_workspace("detect-subdir")
        subdir = workspace.path / "src" / "app"
        subdir.mkdir(parents=True)

        detected = workspace_manager.detect_workspace(subdir)

        assert detected is not None
        assert detected.name == "detect-subdir"

    def test_detect_returns_none_from_main_repo(
        self,
        workspace_manager: WorkspaceManager,
        git_repo: Path,
    ) -> None:
        """Test that detecting from the main repo returns None."""
        detected = workspace_manager.detect_workspace(git_repo)

        assert detected is None

    def test_detect_returns_none_outside_repo(
        self,
        workspace_manager: WorkspaceManager,
        tmp_path: Path,
    ) -> None:
        """Test that detecting from outside the repo returns None."""
        outside = tmp_path / "outside" / "nowhere"
        outside.mkdir(parents=True)

        detected = workspace_manager.detect_workspace(outside)

        assert detected is None

    def test_detect_after_removal_returns_none(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test that detecting a removed workspace returns None."""
        workspace = workspace_manager.create_workspace("detect-remove")
        assert workspace_manager.detect_workspace(workspace.path) is not None

        workspace_manager.remove_workspace("detect-remove", force=True)

        detected = workspace_manager.detect_workspace(workspace.path)
        assert detected is None

    def test_detect_multiple_workspaces(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test detecting from each of multiple workspaces returns the correct one."""
        ws_a = workspace_manager.create_workspace("detect-a")
        ws_b = workspace_manager.create_workspace("detect-b")

        detected_a = workspace_manager.detect_workspace(ws_a.path)
        detected_b = workspace_manager.detect_workspace(ws_b.path)

        assert detected_a is not None
        assert detected_b is not None
        assert detected_a.name == "detect-a"
        assert detected_b.name == "detect-b"
        assert detected_a.path != detected_b.path

    def test_detect_deeply_nested_subdirectory(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test detecting from a deeply nested subdirectory."""
        workspace = workspace_manager.create_workspace("detect-deep")
        deep_dir = workspace.path / "a" / "b" / "c" / "d"
        deep_dir.mkdir(parents=True)

        detected = workspace_manager.detect_workspace(deep_dir)

        assert detected is not None
        assert detected.name == "detect-deep"

    def test_detect_workspace_state_is_active(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test that detected workspace has ACTIVE state."""
        workspace = workspace_manager.create_workspace("detect-state")

        detected = workspace_manager.detect_workspace(workspace.path)

        assert detected is not None
        assert detected.state.value == "active"

    def test_detect_workspace_layout_is_set(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test that detected workspace has a layout type."""
        workspace = workspace_manager.create_workspace("detect-layout")

        detected = workspace_manager.detect_workspace(workspace.path)

        assert detected is not None
        assert detected.layout is not None

    def test_detect_workspace_repo_root_matches(
        self,
        workspace_manager: WorkspaceManager,
        git_repo: Path,
    ) -> None:
        """Test that detected workspace repo_root matches the actual repo."""
        workspace = workspace_manager.create_workspace("detect-reporoot")

        detected = workspace_manager.detect_workspace(workspace.path)

        assert detected is not None
        assert detected.repo_root == git_repo
