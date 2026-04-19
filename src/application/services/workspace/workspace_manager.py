"""WorkspaceManager implementation for git worktree-based workspaces."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

from src.application.services.workspace.entities import (
    HookResult,
    LayoutType,
    Workspace,
    WorkspaceConfig,
    WorktreeState,
)
from src.application.services.workspace.exceptions import (
    GitError,
    HookExecutionError,
    WorkspaceExistsError,
    WorkspaceNotCleanError,
    WorkspaceNotFoundError,
)
from src.infrastructure.platform.git.git_command_executor import GitCommandExecutor

from .hook_runner import HookRunner

logger = logging.getLogger(__name__)


class LayoutResolver:
    """Resolves workspace paths based on layout type.

    This is a simple implementation for Task 1.5. A full implementation
    will be done in Task 2.2.
    """

    def __init__(self, config: WorkspaceConfig) -> None:
        """Initialize LayoutResolver with configuration.

        Args:
            config: Workspace configuration.
        """
        self._config = config

    def resolve_path(self, name: str, repo_root: Path) -> Path:
        """Resolve the path for a workspace based on layout.

        Args:
            name: Workspace/branch name.
            repo_root: Root path of the git repository.

        Returns:
            Resolved path for the workspace.
        """
        layout = self._config.default_layout

        if layout == LayoutType.NESTED:
            return repo_root / ".worktrees" / name
        elif layout == LayoutType.OUTER_NESTED:
            parent = repo_root.parent
            repo_name = repo_root.name
            return parent / f"{repo_name}.worktrees" / name
        elif layout == LayoutType.SIBLING:
            parent = repo_root.parent
            repo_name = repo_root.name
            return parent / f"{repo_name}-{name}"

        # Default to nested
        return repo_root / ".worktrees" / name


class WorkspaceManagerABC(ABC):
    """Abstract base class for WorkspaceManager.

    Defines the interface for workspace management operations
    using git worktrees.
    """

    @abstractmethod
    def create_workspace(self, name: str, layout: LayoutType | None = None) -> Workspace:
        """Create a new workspace.

        Args:
            name: Name of the workspace (and branch).
            layout: Optional layout type. Uses default if not specified.

        Returns:
            Created Workspace entity.

        Raises:
            WorkspaceExistsError: If workspace already exists.
            GitError: If git operation fails.
        """
        ...

    @abstractmethod
    def start_workspace(self, name: str) -> Workspace:
        """Start (find) an existing workspace.

        Args:
            name: Name of the workspace to find.

        Returns:
            Workspace entity.

        Raises:
            WorkspaceNotFoundError: If workspace doesn't exist.
        """
        ...

    @abstractmethod
    def list_workspaces(self) -> list[Workspace]:
        """List all workspaces.

        Returns:
            List of Workspace entities.
        """
        ...

    @abstractmethod
    def remove_workspace(self, name: str, force: bool = False) -> None:
        """Remove a workspace.

        Args:
            name: Name of the workspace to remove.
            force: Whether to force removal even with uncommitted changes.

        Raises:
            WorkspaceNotFoundError: If workspace doesn't exist.
            WorkspaceNotCleanError: If workspace has uncommitted changes (without force).
            GitError: If git operation fails.
        """
        ...

    @abstractmethod
    def merge_workspace(
        self,
        name: str,
        target_branch: str = "main",
        delete_branch: bool = True,
    ) -> None:
        """Merge a workspace branch to target branch.

        Args:
            name: Name of the workspace to merge.
            target_branch: The target branch to merge into (default: "main").
            delete_branch: Whether to delete the branch after merging.

        Raises:
            WorkspaceNotFoundError: If workspace doesn't exist.
            GitError: If git operation fails.
        """
        ...

    @abstractmethod
    def detect_workspace(self, path: Path | None = None) -> Workspace | None:
        """Detect workspace from current directory or given path.

        Args:
            path: Optional path to detect workspace from. Uses cwd if not specified.

        Returns:
            Workspace entity if found, None otherwise.
        """
        ...


class WorkspaceManager(WorkspaceManagerABC):
    """Concrete implementation of WorkspaceManager using git worktrees.

    Manages workspaces using git worktree operations with configurable layouts.
    """

    def __init__(
        self,
        git_executor: GitCommandExecutor,
        config: WorkspaceConfig,
        hook_runner: HookRunner | None = None,
    ) -> None:
        """Initialize WorkspaceManager.

        Args:
            git_executor: Git command executor.
            config: Workspace configuration.
            hook_runner: Optional hook runner for setup/teardown hooks.
        """
        self._git = git_executor
        self._config = config
        self._layout_resolver = LayoutResolver(config)
        self._hook_runner = hook_runner

    @property
    def git_executor(self) -> GitCommandExecutor:
        """Public accessor for the git command executor."""
        return self._git

    def create_workspace(self, name: str, layout: LayoutType | None = None) -> Workspace:
        """Create a new workspace.

        Args:
            name: Name of the workspace (and branch).
            layout: Optional layout type. Uses default if not specified.

        Returns:
            Created Workspace entity.

        Raises:
            WorkspaceExistsError: If workspace already exists.
            GitError: If git operation fails.
        """
        # Get repo root
        repo_root = self._git.get_repo_root()

        # Resolve path based on layout
        if layout:
            # Create temporary config with custom layout
            temp_config = WorkspaceConfig(
                default_layout=layout,
                auto_cleanup=self._config.auto_cleanup,
                hooks_dir=self._config.hooks_dir,
            )
            temp_resolver = LayoutResolver(temp_config)
            worktree_path = temp_resolver.resolve_path(name, repo_root)
        else:
            worktree_path = self._layout_resolver.resolve_path(name, repo_root)

        # Check if workspace already exists
        if self._git.worktree_is_valid(worktree_path):
            raise WorkspaceExistsError(f"Workspace '{name}' already exists at {worktree_path}")

        # Create the worktree (this also creates the branch)
        self._git.worktree_add(worktree_path, name, create_branch=True)

        # Run setup hook if hook_runner is available
        setup_hook_result: HookResult | None = None
        if self._hook_runner is not None:
            try:
                setup_hook_result = self._hook_runner.run_setup(worktree_path)
                if not setup_hook_result.success:
                    logger.warning(
                        f"Setup hook failed for workspace '{name}': "
                        f"exit_code={setup_hook_result.exit_code}, "
                        f"stderr={setup_hook_result.stderr}"
                    )
            except HookExecutionError as e:
                logger.warning(f"Setup hook execution failed for workspace '{name}': {e}")

        # Return the workspace entity
        return Workspace(
            name=name,
            path=worktree_path,
            layout=layout or self._config.default_layout,
            state=WorktreeState.ACTIVE,
            repo_root=repo_root,
            last_setup_hook=setup_hook_result,
        )

    def start_workspace(self, name: str) -> Workspace:
        """Start (find) an existing workspace.

        Args:
            name: Name of the workspace to find.

        Returns:
            Workspace entity.

        Raises:
            WorkspaceNotFoundError: If workspace doesn't exist.
        """
        # Find the workspace in the worktree list
        worktrees = self._git.worktree_list()

        repo_root = self._git.get_repo_root()

        for wt in worktrees:
            wt_path = Path(wt["path"])
            wt_branch = wt.get("branch", "")

            # Check if this is the workspace we're looking for
            # The branch name might be prefixed with 'refs/heads/'
            branch_name = wt_branch.replace("refs/heads/", "")

            if branch_name == name:
                # Verify it's not the main repo
                if wt_path.resolve() == repo_root.resolve():
                    continue

                # Determine layout type
                layout = self._detect_layout(wt_path, repo_root)

                return Workspace(
                    name=name,
                    path=wt_path,
                    layout=layout,
                    state=WorktreeState.ACTIVE,
                    repo_root=repo_root,
                )

        raise WorkspaceNotFoundError(f"Workspace '{name}' not found")

    def list_workspaces(self) -> list[Workspace]:
        """List all workspaces.

        Returns:
            List of Workspace entities.
        """
        worktrees = self._git.worktree_list()
        repo_root = self._git.get_repo_root()

        workspaces: list[Workspace] = []

        for wt in worktrees:
            wt_path = Path(wt["path"])

            # Skip the main repo
            if wt_path.resolve() == repo_root.resolve():
                continue

            # Get branch name
            wt_branch = wt.get("branch", "")
            name = wt_branch.replace("refs/heads/", "")

            # Determine layout type
            layout = self._detect_layout(wt_path, repo_root)

            workspaces.append(
                Workspace(
                    name=name,
                    path=wt_path,
                    layout=layout,
                    state=WorktreeState.ACTIVE,
                    repo_root=repo_root,
                )
            )

        return workspaces

    def remove_workspace(self, name: str, force: bool = False) -> None:
        """Remove a workspace.

        Args:
            name: Name of the workspace to remove.
            force: Whether to force removal even with uncommitted changes.

        Raises:
            WorkspaceNotFoundError: If workspace doesn't exist.
            WorkspaceNotCleanError: If workspace has uncommitted changes (without force).
            GitError: If git operation fails.
        """
        # Find the workspace
        workspace = self.start_workspace(name)

        # Run teardown hook if hook_runner is available
        if self._hook_runner is not None:
            try:
                teardown_result = self._hook_runner.run_teardown(workspace.path)
                if not teardown_result.success:
                    logger.warning(
                        f"Teardown hook failed for workspace '{name}': "
                        f"exit_code={teardown_result.exit_code}, "
                        f"stderr={teardown_result.stderr}"
                    )
            except HookExecutionError as e:
                logger.warning(f"Teardown hook execution failed for workspace '{name}': {e}")

        # Check if clean (unless force)
        if not force and not self._git.is_clean(workspace.path):
            raise WorkspaceNotCleanError(
                f"Workspace '{name}' has uncommitted changes. Use force=True to remove anyway."
            )

        # Remove the worktree
        self._git.worktree_remove(workspace.path, force=force)

        # Delete the branch
        self._git.branch_delete(name, force=force)

    def merge_workspace(
        self,
        name: str,
        target_branch: str = "main",
        delete_branch: bool = True,
    ) -> None:
        """Merge a workspace branch to target branch.

        Args:
            name: Name of the workspace to merge.
            target_branch: The target branch to merge into (default: "main").
            delete_branch: Whether to delete the branch after merging.

        Raises:
            WorkspaceNotFoundError: If workspace doesn't exist.
            GitError: If git operation fails.
        """
        # Find the workspace to get its path
        workspace = self.start_workspace(name)

        # Get the repo root for running merge commands
        repo_root = workspace.repo_root

        # First checkout the target branch
        try:
            self._git._run_git_command(
                ["checkout", target_branch],
                cwd=repo_root,
            )
        except GitError as e:
            raise GitError(f"Failed to checkout target branch '{target_branch}': {e}", e) from e

        # Merge the branch (we need to be in the main worktree for this)
        # Run: git merge <branch_name> --no-edit
        try:
            self._git._run_git_command(
                ["merge", name, "--no-edit"],
                cwd=repo_root,
            )
        except GitError as e:
            raise GitError(f"Failed to merge branch '{name}': {e}", e) from e

        # Delete the branch if requested
        if delete_branch:
            try:
                self._git.branch_delete(name, force=False)
            except GitError as e:
                raise GitError(f"Failed to delete branch '{name}': {e}", e) from e

    def detect_workspace(self, path: Path | None = None) -> Workspace | None:
        """Detect workspace from current directory or given path.

        Args:
            path: Optional path to detect workspace from. Uses cwd if not specified.

        Returns:
            Workspace entity if found, None otherwise.
        """
        if path is None:
            path = Path.cwd()

        # Resolve the path
        try:
            target_path = path.resolve()
        except (OSError, ValueError):
            return None

        # Check if path exists
        if not target_path.exists():
            return None

        # Get repo root
        try:
            repo_root = self._git.get_repo_root(target_path)
        except (GitError, FileNotFoundError, OSError):
            # FileNotFoundError: path doesn't exist (worktree was removed)
            # OSError: other filesystem issues
            return None

        # Check if we're in the main repo (not a worktree)
        if target_path == repo_root.resolve():
            return None

        # Find the worktree that contains this path
        worktrees = self._git.worktree_list()
        repo_root_resolved = repo_root.resolve()

        for wt in worktrees:
            wt_path = Path(wt["path"]).resolve()

            # Skip the main repo - we only want worktrees
            if wt_path == repo_root_resolved:
                continue

            # Check if target path is this worktree or inside it
            try:
                if wt_path == target_path or target_path.is_relative_to(wt_path):
                    # Get branch name
                    wt_branch = wt.get("branch", "")
                    name = wt_branch.replace("refs/heads/", "")

                    # Determine layout type
                    layout = self._detect_layout(wt_path, repo_root)

                    return Workspace(
                        name=name,
                        path=wt_path,
                        layout=layout,
                        state=WorktreeState.ACTIVE,
                        repo_root=repo_root,
                    )
            except (OSError, ValueError):
                continue

        return None

    def detect_layout(self, worktree_path: Path, repo_root: Path) -> LayoutType:
        """Detect the layout type based on worktree path.

        Args:
            worktree_path: Path to the worktree.
            repo_root: Root path of the git repository.

        Returns:
            Detected LayoutType.
        """
        return self._detect_layout(worktree_path, repo_root)

    def _detect_layout(self, worktree_path: Path, repo_root: Path) -> LayoutType:
        """Internal layout detection logic.

        Args:
            worktree_path: Path to the worktree.
            repo_root: Root path of the git repository.

        Returns:
            Detected LayoutType.
        """
        # Check nested layout: .worktrees/<name>/
        expected_nested = repo_root / ".worktrees"
        try:
            if worktree_path.resolve().is_relative_to(expected_nested.resolve()):
                return LayoutType.NESTED
        except (OSError, ValueError):
            pass

        # Check outer nested: ../<repo>.worktrees/<name>/
        repo_name = repo_root.name
        expected_outer = repo_root.parent / f"{repo_name}.worktrees"
        try:
            if worktree_path.resolve().is_relative_to(expected_outer.resolve()):
                return LayoutType.OUTER_NESTED
        except (OSError, ValueError):
            pass

        # Check sibling: ../<repo>-<name>/
        expected_sibling_prefix = repo_root.parent / f"{repo_name}-"
        try:
            resolved = worktree_path.resolve()
            if str(resolved).startswith(str(expected_sibling_prefix.resolve())):
                return LayoutType.SIBLING
        except (OSError, ValueError):
            pass

        # Default to nested
        return LayoutType.NESTED
