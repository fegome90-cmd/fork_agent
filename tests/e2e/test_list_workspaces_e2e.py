"""End-to-end tests for listing workspaces.

Tests:
- Create multiple workspaces
- Verify list command returns correct workspaces
- Verify list includes all expected details
"""

from __future__ import annotations

from src.application.services.workspace.workspace_manager import WorkspaceManager


class TestListWorkspacesE2E:
    """E2E tests for listing workspaces."""

    def test_list_workspaces_empty_initially(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test that listing workspaces returns empty list initially."""
        workspaces = workspace_manager.list_workspaces()
        assert workspaces == []

    def test_list_workspaces_after_single_creation(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test listing workspaces after creating one."""
        # Create workspace
        workspace_manager.create_workspace("list-test-1")

        # List should contain the workspace
        workspaces = workspace_manager.list_workspaces()
        assert len(workspaces) == 1
        assert workspaces[0].name == "list-test-1"

    def test_list_workspaces_after_multiple_creations(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test listing workspaces after creating multiple."""
        # Create multiple workspaces
        workspace_manager.create_workspace("multi-1")
        workspace_manager.create_workspace("multi-2")
        workspace_manager.create_workspace("multi-3")

        # List should contain all workspaces
        workspaces = workspace_manager.list_workspaces()
        assert len(workspaces) == 3

        names = {ws.name for ws in workspaces}
        assert names == {"multi-1", "multi-2", "multi-3"}

    def test_list_workspaces_includes_path(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test that list includes workspace path."""
        workspace_manager.create_workspace("path-test")

        workspaces = workspace_manager.list_workspaces()
        found = next(ws for ws in workspaces if ws.name == "path-test")

        assert found.path.exists()
        assert found.path.is_dir()

    def test_list_workspaces_includes_layout(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test that list includes layout type."""
        workspace_manager.create_workspace("layout-test")

        workspaces = workspace_manager.list_workspaces()
        found = next(ws for ws in workspaces if ws.name == "layout-test")

        assert found.layout is not None

    def test_list_workspaces_after_removal(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test that list reflects workspace removal."""
        # Create workspaces
        workspace_manager.create_workspace("remove-list-1")
        workspace_manager.create_workspace("remove-list-2")

        # Verify both exist
        workspaces = workspace_manager.list_workspaces()
        assert len(workspaces) == 2

        # Remove one
        workspace_manager.remove_workspace("remove-list-1", force=True)

        # Verify only one remains
        workspaces = workspace_manager.list_workspaces()
        assert len(workspaces) == 1
        assert workspaces[0].name == "remove-list-2"

    def test_list_workspaces_persists_across_manager_instances(
        self,
        git_executor,
        workspace_config,
    ) -> None:
        """Test that list works across different manager instances."""
        from src.application.services.workspace.workspace_manager import WorkspaceManager

        # Create first manager and workspace
        manager1 = WorkspaceManager(
            git_executor=git_executor,
            config=workspace_config,
            hook_runner=None,
        )
        manager1.create_workspace("persist-list")

        # Create new manager instance
        manager2 = WorkspaceManager(
            git_executor=git_executor,
            config=workspace_config,
            hook_runner=None,
        )

        # Should still be able to list the workspace
        workspaces = manager2.list_workspaces()
        assert any(ws.name == "persist-list" for ws in workspaces)
