"""Workspace detector for auto-detection from current directory."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from src.application.services.workspace.entities import LayoutType, Workspace, WorktreeState
from src.application.services.workspace.workspace_manager import WorkspaceManager

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from src.infrastructure.platform.git.git_command_executor import GitCommandExecutor


class WorkspaceDetector:
    """Detects workspace from current directory or given path.

    Uses git worktree list to find all worktrees and matches
    the current path to find the corresponding workspace.
    """

    def __init__(self, workspace_manager: WorkspaceManager) -> None:
        """Initialize WorkspaceDetector.

        Args:
            workspace_manager: Workspace manager instance to use for workspace operations.
        """
        self._manager = workspace_manager

    @property
    def _git(self) -> GitCommandExecutor:
        # Access git executor through the manager's public interface
        return self._manager.git_executor

    def detect(self, path: Path | None = None) -> Workspace | None:
        """Detect workspace from current directory or given path.

        Uses git worktree list to find all worktrees and checks
        if the given path is within any of them.

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

        # Get repo root
        try:
            repo_root = self._git.get_repo_root(target_path)
        except Exception:
            logger.debug("Failed to get repo root for %s", target_path, exc_info=True)
            return None
        if target_path == repo_root.resolve():
            return None

        # Find the worktree that contains this path
        worktrees = self._git.worktree_list()

        for wt in worktrees:
            wt_path = Path(wt["path"]).resolve()

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

    def is_in_workspace(self, path: Path | None = None) -> bool:
        """Check if given path is inside a workspace.

        Args:
            path: Optional path to check. Uses cwd if not specified.

        Returns:
            True if the path is inside a workspace, False otherwise.
        """
        return self.detect(path) is not None

    def get_workspace_name(self, path: Path | None = None) -> str | None:
        """Get workspace name from current directory.

        Args:
            path: Optional path to get workspace name from. Uses cwd if not specified.

        Returns:
            Workspace name if found, None otherwise.
        """
        workspace = self.detect(path)
        return workspace.name if workspace else None

    def _detect_layout(self, worktree_path: Path, repo_root: Path) -> LayoutType:
        """Delegate layout detection to the workspace manager.

        Args:
            worktree_path: Path to the worktree.
            repo_root: Root path of the git repository.

        Returns:
            Detected LayoutType.
        """
        return self._manager.detect_layout(worktree_path, repo_root)
