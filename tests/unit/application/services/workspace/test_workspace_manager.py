"""Unit tests for WorkspaceManager."""

from unittest.mock import MagicMock, patch
from pathlib import Path

import pytest

from src.application.services.workspace.entities import (
    HookResult,
    LayoutType,
    WorktreeState,
    Workspace,
    WorkspaceConfig,
)
from src.application.services.workspace.exceptions import (
    GitError,
    HookExecutionError,
    WorkspaceExistsError,
    WorkspaceNotCleanError,
    WorkspaceNotFoundError,
)
from src.application.services.workspace.workspace_manager import (
    LayoutResolver,
    WorkspaceManager,
    WorkspaceManagerABC,
)


@pytest.fixture
def workspace_config() -> WorkspaceConfig:
    return WorkspaceConfig(
        default_layout=LayoutType.NESTED,
        auto_cleanup=True,
        hooks_dir=Path("/test/repo/.git/hooks"),
    )


@pytest.fixture
def mock_git_executor() -> MagicMock:
    return MagicMock()


@pytest.fixture
def workspace_manager(
    mock_git_executor: MagicMock, workspace_config: WorkspaceConfig
) -> WorkspaceManager:
    return WorkspaceManager(git_executor=mock_git_executor, config=workspace_config)


class TestLayoutResolver:
    def test_resolve_path_nested(self) -> None:
        config = WorkspaceConfig(
            default_layout=LayoutType.NESTED,
            auto_cleanup=False,
            hooks_dir=None,
        )
        resolver = LayoutResolver(config)

        path = resolver.resolve_path("feature-branch", Path("/test/repo"))

        assert path == Path("/test/repo/.worktrees/feature-branch")

    def test_resolve_path_outer_nested(self) -> None:
        config = WorkspaceConfig(
            default_layout=LayoutType.OUTER_NESTED,
            auto_cleanup=False,
            hooks_dir=None,
        )
        resolver = LayoutResolver(config)

        path = resolver.resolve_path("feature-branch", Path("/test/repo"))

        assert path == Path("/test/repo.worktrees/feature-branch")

    def test_resolve_path_sibling(self) -> None:
        config = WorkspaceConfig(
            default_layout=LayoutType.SIBLING,
            auto_cleanup=False,
            hooks_dir=None,
        )
        resolver = LayoutResolver(config)

        path = resolver.resolve_path("feature-branch", Path("/test/repo"))

        assert path == Path("/test/repo-feature-branch")

    def test_resolve_path_default_fallback(self) -> None:
        config = WorkspaceConfig(
            default_layout=LayoutType.NESTED,
            auto_cleanup=False,
            hooks_dir=None,
        )
        resolver = LayoutResolver(config)

        path = resolver.resolve_path("feature-branch", Path("/test/repo"))

        assert path == Path("/test/repo/.worktrees/feature-branch")


class TestWorkspaceManagerCreate:
    def test_create_workspace_success(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_is_valid.return_value = False

        workspace = workspace_manager.create_workspace("feature-branch")

        assert workspace.name == "feature-branch"
        assert workspace.state == WorktreeState.ACTIVE
        mock_git_executor.worktree_add.assert_called_once()

    def test_create_workspace_already_exists(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_is_valid.return_value = True

        with pytest.raises(WorkspaceExistsError):
            workspace_manager.create_workspace("feature-branch")

    def test_create_workspace_with_custom_layout(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_is_valid.return_value = False

        workspace = workspace_manager.create_workspace("feature-branch", layout=LayoutType.SIBLING)

        assert workspace.layout == LayoutType.SIBLING

    def test_create_workspace_git_error(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_is_valid.return_value = False
        mock_git_executor.worktree_add.side_effect = GitError("Git error")

        with pytest.raises(GitError):
            workspace_manager.create_workspace("feature-branch")

    def test_create_workspace_with_hook_runner_success(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_is_valid.return_value = False

        mock_hook_runner = MagicMock()
        mock_hook_runner.run_setup.return_value = HookResult(
            success=True, exit_code=0, stdout="", stderr="", duration_ms=100
        )
        workspace_manager._hook_runner = mock_hook_runner

        workspace = workspace_manager.create_workspace("feature-branch")

        mock_hook_runner.run_setup.assert_called_once()
        assert workspace.last_setup_hook is not None

    def test_create_workspace_with_hook_runner_failure(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_is_valid.return_value = False

        mock_hook_runner = MagicMock()
        mock_hook_runner.run_setup.side_effect = HookExecutionError("Hook failed")
        workspace_manager._hook_runner = mock_hook_runner

        workspace = workspace_manager.create_workspace("feature-branch")

        assert workspace.last_setup_hook is None


class TestWorkspaceManagerStart:
    def test_start_workspace_found(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
            {"path": "/test/repo/.worktrees/feature", "branch": "refs/heads/feature"},
        ]

        workspace = workspace_manager.start_workspace("feature")

        assert workspace.name == "feature"
        assert workspace.state == WorktreeState.ACTIVE

    def test_start_workspace_not_found(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
        ]

        with pytest.raises(WorkspaceNotFoundError):
            workspace_manager.start_workspace("nonexistent")

    def test_start_workspace_with_refs_heads_prefix(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
            {
                "path": "/test/repo/.worktrees/feature",
                "branch": "refs/heads/feature-branch",
            },
        ]

        workspace = workspace_manager.start_workspace("feature-branch")

        assert workspace.name == "feature-branch"

    def test_start_workspace_skips_main_repo(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
        ]

        with pytest.raises(WorkspaceNotFoundError):
            workspace_manager.start_workspace("main")


class TestWorkspaceManagerList:
    def test_list_workspaces_empty(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
        ]

        workspaces = workspace_manager.list_workspaces()

        assert workspaces == []

    def test_list_workspaces_with_worktrees(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
            {"path": "/test/repo/.worktrees/feature1", "branch": "refs/heads/feature1"},
            {"path": "/test/repo/.worktrees/feature2", "branch": "refs/heads/feature2"},
        ]

        workspaces = workspace_manager.list_workspaces()

        assert len(workspaces) == 2
        assert workspaces[0].name == "feature1"
        assert workspaces[1].name == "feature2"


class TestWorkspaceManagerRemove:
    def test_remove_workspace_success(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
            {"path": "/test/repo/.worktrees/feature", "branch": "refs/heads/feature"},
        ]
        mock_git_executor.is_clean.return_value = True

        workspace_manager.remove_workspace("feature")

        mock_git_executor.worktree_remove.assert_called_once()

    def test_remove_workspace_not_clean(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
            {"path": "/test/repo/.worktrees/feature", "branch": "refs/heads/feature"},
        ]
        mock_git_executor.is_clean.return_value = False

        with pytest.raises(WorkspaceNotCleanError):
            workspace_manager.remove_workspace("feature")

    def test_remove_workspace_force(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
            {"path": "/test/repo/.worktrees/feature", "branch": "refs/heads/feature"},
        ]
        mock_git_executor.is_clean.return_value = False

        workspace_manager.remove_workspace("feature", force=True)

        mock_git_executor.worktree_remove.assert_called_once()
        call_args = mock_git_executor.worktree_remove.call_args
        assert call_args[1]["force"] is True

    def test_remove_workspace_with_teardown_hook_success(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
            {"path": "/test/repo/.worktrees/feature", "branch": "refs/heads/feature"},
        ]
        mock_git_executor.is_clean.return_value = True

        mock_hook_runner = MagicMock()
        mock_hook_runner.run_teardown.return_value = HookResult(
            success=True, exit_code=0, stdout="", stderr="", duration_ms=100
        )
        workspace_manager._hook_runner = mock_hook_runner

        workspace_manager.remove_workspace("feature")

        mock_hook_runner.run_teardown.assert_called_once()

    def test_remove_workspace_with_teardown_hook_failure(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
            {"path": "/test/repo/.worktrees/feature", "branch": "refs/heads/feature"},
        ]
        mock_git_executor.is_clean.return_value = True

        mock_hook_runner = MagicMock()
        mock_hook_runner.run_teardown.side_effect = HookExecutionError("Hook failed")
        workspace_manager._hook_runner = mock_hook_runner

        workspace_manager.remove_workspace("feature")

        mock_git_executor.worktree_remove.assert_called_once()


class TestWorkspaceManagerMerge:
    def test_merge_workspace_success(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
            {"path": "/test/repo/.worktrees/feature", "branch": "refs/heads/feature"},
        ]

        workspace_manager.merge_workspace("feature")

        mock_git_executor._run_git_command.assert_called_once()
        mock_git_executor.branch_delete.assert_called_once()

    def test_merge_workspace_no_delete_branch(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
            {"path": "/test/repo/.worktrees/feature", "branch": "refs/heads/feature"},
        ]

        workspace_manager.merge_workspace("feature", delete_branch=False)

        mock_git_executor.branch_delete.assert_not_called()

    def test_merge_workspace_git_error(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
            {"path": "/test/repo/.worktrees/feature", "branch": "refs/heads/feature"},
        ]
        mock_git_executor._run_git_command.side_effect = GitError("Merge failed")

        with pytest.raises(GitError):
            workspace_manager.merge_workspace("feature")

    def test_merge_workspace_branch_delete_error(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
            {"path": "/test/repo/.worktrees/feature", "branch": "refs/heads/feature"},
        ]
        mock_git_executor.branch_delete.side_effect = GitError("Delete failed")

        with pytest.raises(GitError):
            workspace_manager.merge_workspace("feature")


class TestWorkspaceManagerDetect:
    def test_detect_workspace_from_path(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
            {"path": "/test/repo/.worktrees/feature", "branch": "refs/heads/feature"},
        ]

        def mock_exists(self: Path) -> bool:
            return True

        def mock_resolve(self: Path, strict: bool = False) -> Path:
            return self

        with (
            patch.object(Path, "exists", mock_exists),
            patch.object(Path, "resolve", mock_resolve),
        ):
            workspace = workspace_manager.detect_workspace(Path("/test/repo/.worktrees/feature"))

        assert workspace is not None
        assert workspace.name == "feature"

    def test_detect_workspace_main_repo_returns_none(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
        ]

        workspace = workspace_manager.detect_workspace(Path("/test/repo"))

        assert workspace is None

    def test_detect_workspace_not_a_worktree(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
        ]

        workspace = workspace_manager.detect_workspace(Path("/some/other/path"))

        assert workspace is None

    def test_detect_workspace_none_path_uses_cwd(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
            {"path": "/test/repo/.worktrees/feature", "branch": "refs/heads/feature"},
        ]

        def mock_exists(self: Path) -> bool:
            return True

        def mock_resolve(self: Path, strict: bool = False) -> Path:
            return self

        with (
            patch.object(Path, "exists", mock_exists),
            patch.object(Path, "resolve", mock_resolve),
            patch("pathlib.Path.cwd", return_value=Path("/test/repo/.worktrees/feature")),
        ):
            workspace = workspace_manager.detect_workspace()

        assert workspace is not None
        assert workspace.name == "feature"

    def test_detect_workspace_path_not_exists(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")

        workspace = workspace_manager.detect_workspace(Path("/nonexistent"))

        assert workspace is None

    def test_detect_workspace_path_resolve_error(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")

        def mock_resolve_error(self: Path, strict: bool = False) -> Path:
            raise OSError("Cannot resolve")

        with patch.object(Path, "resolve", mock_resolve_error):
            workspace = workspace_manager.detect_workspace(Path("/test/repo/.worktrees/feature"))

        assert workspace is None


class TestWorkspaceManagerDetectLayout:
    def test_detect_layout_nested(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")

        layout = workspace_manager._detect_layout(
            Path("/test/repo/.worktrees/feature"), Path("/test/repo")
        )

        assert layout == LayoutType.NESTED

    def test_detect_layout_outer_nested(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")

        layout = workspace_manager._detect_layout(
            Path("/test/repo.worktrees/feature"), Path("/test/repo")
        )

        assert layout == LayoutType.OUTER_NESTED

    def test_detect_layout_sibling(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")

        layout = workspace_manager._detect_layout(Path("/test/repo-feature"), Path("/test/repo"))

        assert layout == LayoutType.SIBLING

    def test_detect_layout_fallback_to_nested(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")

        layout = workspace_manager._detect_layout(Path("/some/other/path"), Path("/test/repo"))

        assert layout == LayoutType.NESTED

    def test_detect_layout_nested_oserror(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")

        def mock_resolve_error(self: Path, strict: bool = False) -> Path:
            raise OSError("Cannot resolve")

        with patch.object(Path, "resolve", mock_resolve_error):
            layout = workspace_manager._detect_layout(
                Path("/test/repo/.worktrees/feature"), Path("/test/repo")
            )

        assert layout == LayoutType.NESTED


class TestWorkspaceManagerABC:
    def test_abc_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            WorkspaceManagerABC()

    def test_abc_methods_are_abstract(self) -> None:
        assert hasattr(WorkspaceManagerABC, "create_workspace")
        assert hasattr(WorkspaceManagerABC, "start_workspace")
        assert hasattr(WorkspaceManagerABC, "list_workspaces")
        assert hasattr(WorkspaceManagerABC, "remove_workspace")
        assert hasattr(WorkspaceManagerABC, "merge_workspace")
        assert hasattr(WorkspaceManagerABC, "detect_workspace")


class TestWorkspaceManagerIntegration:
    def test_full_workflow(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_is_valid.return_value = False
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
        ]
        mock_git_executor.is_clean.return_value = True

        workspace = workspace_manager.create_workspace("feature-branch")
        assert workspace.name == "feature-branch"

        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
            {
                "path": "/test/repo/.worktrees/feature-branch",
                "branch": "refs/heads/feature-branch",
            },
        ]
        workspaces = workspace_manager.list_workspaces()
        assert len(workspaces) == 1

        started = workspace_manager.start_workspace("feature-branch")
        assert started.name == "feature-branch"

        workspace_manager.remove_workspace("feature-branch")
        mock_git_executor.worktree_remove.assert_called_once()
