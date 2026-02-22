"""End-to-end tests for workspace auto-detection.

Tests:
- Create workspace and change to its directory
- Verify detect returns correct workspace
- Test detection from subdirectories
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from src.application.services.workspace.workspace_manager import WorkspaceManager


class TestAutoDetectE2E:
    """E2E tests for workspace auto-detection."""

    def test_detect_workspace_from_workspace_directory(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test detecting workspace when in its directory."""
        # Create workspace
        workspace = workspace_manager.create_workspace("detect-test")

        # Detect from workspace path
        detected = workspace_manager.detect_workspace(workspace.path)

        assert detected is not None
        assert detected.name == "detect-test"
        assert detected.path == workspace.path

    def test_detect_workspace_from_subdirectory(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test detecting workspace from a subdirectory within it."""
        # Create workspace
        workspace = workspace_manager.create_workspace("subdir-test")

        # Create a subdirectory
        subdir = workspace.path / "src" / "components"
        subdir.mkdir(parents=True)

        # Detect from subdirectory
        detected = workspace_manager.detect_workspace(subdir)

        assert detected is not None
        assert detected.name == "subdir-test"

    def test_detect_workspace_returns_none_for_main_repo(
        self,
        workspace_manager: WorkspaceManager,
        git_repo: Path,
    ) -> None:
        """Test that detect returns None for main repository."""
        # Detect from main repo
        detected = workspace_manager.detect_workspace(git_repo)

        assert detected is None

    def test_detect_workspace_returns_none_for_unrelated_path(
        self,
        workspace_manager: WorkspaceManager,
        tmp_path: Path,
    ) -> None:
        """Test that detect returns None for unrelated path."""
        # Create unrelated directory
        unrelated = tmp_path / "unrelated"
        unrelated.mkdir()

        # Detect from unrelated path
        detected = workspace_manager.detect_workspace(unrelated)

        assert detected is None

    def test_detect_workspace_with_path_argument(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test detect with explicit path argument."""
        # Create workspace
        workspace = workspace_manager.create_workspace("explicit-path")

        # Detect with explicit path
        detected = workspace_manager.detect_workspace(path=workspace.path)

        assert detected is not None
        assert detected.name == "explicit-path"

    def test_detect_workspace_none_when_no_workspaces(
        self,
        workspace_manager: WorkspaceManager,
        git_repo: Path,
    ) -> None:
        """Test detect returns None when no workspaces exist."""
        detected = workspace_manager.detect_workspace(git_repo)
        assert detected is None

    def test_detect_workspace_multiple_workspaces(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test detection when multiple workspaces exist."""
        # Create multiple workspaces
        workspace1 = workspace_manager.create_workspace("detect-multi-1")
        workspace2 = workspace_manager.create_workspace("detect-multi-2")

        # Detect each workspace
        detected1 = workspace_manager.detect_workspace(workspace1.path)
        detected2 = workspace_manager.detect_workspace(workspace2.path)

        assert detected1 is not None
        assert detected1.name == "detect-multi-1"

        assert detected2 is not None
        assert detected2.name == "detect-multi-2"

    def test_detect_workspace_after_changing_to_directory(
        self,
        workspace_manager: WorkspaceManager,
        git_repo: Path,
    ) -> None:
        """Test detection after changing to workspace directory (simulating cd)."""
        # Create workspace
        workspace = workspace_manager.create_workspace("cd-test")

        # Simulate "cd" by detecting from workspace path
        detected = workspace_manager.detect_workspace(workspace.path)

        assert detected is not None
        assert detected.name == "cd-test"
        assert detected.path == workspace.path

    def test_detect_workspace_includes_layout(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test that detected workspace includes layout information."""
        workspace = workspace_manager.create_workspace("layout-detect")

        detected = workspace_manager.detect_workspace(workspace.path)

        assert detected is not None
        assert detected.layout is not None
