"""Git command executor with version check and worktree support."""

from __future__ import annotations

import subprocess
from pathlib import Path

from src.infrastructure.platform.git.exceptions import (
    GitError,
    GitNotFoundError,
    GitVersionError,
)

# Minimum required git version (C-03)
MIN_GIT_VERSION = (2, 20, 0)


class GitCommandExecutor:
    """Git command executor with C-03 compliance (git >= 2.20) and M-02 support.

    This class provides a high-level interface for git operations,
    specifically focused on worktree management with version verification.
    """

    def __init__(self, repo_path: Path | None = None) -> None:
        """Initialize GitCommandExecutor and verify git version >= 2.20.

        Args:
            repo_path: Optional path to the git repository.
                       If provided, all operations will be performed in this repository.

        Raises:
            GitNotFoundError: If git is not installed.
            GitVersionError: If git version is less than 2.20.
        """
        self._version: tuple[int, int, int] | None = None
        self._repo_path = repo_path
        self._verify_git_available()
        self._verify_git_version()

    def _verify_git_available(self) -> None:
        """Verify git is available on the system."""
        try:
            subprocess.run(
                ["git", "--version"],
                capture_output=True,
                check=True,
            )
        except FileNotFoundError:
            raise GitNotFoundError("Git is not installed or not in PATH.") from None
        except subprocess.CalledProcessError as e:
            raise GitNotFoundError("Git command failed.", e) from e

    def _verify_git_version(self) -> None:
        """Verify git version is >= 2.20 (C-03 requirement).

        Raises:
            GitVersionError: If git version is less than 2.20.
        """
        version = self.get_git_version()
        if version < MIN_GIT_VERSION:
            raise GitVersionError(
                f"Git version must be >= 2.20. Found: {'.'.join(map(str, version))}"
            )

    def get_git_version(self) -> tuple[int, int, int]:
        """Get the installed git version.

        Returns:
            Tuple of (major, minor, patch) version numbers.

        Raises:
            GitError: If unable to parse git version.
        """
        if self._version is not None:
            return self._version

        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            # Output format: "git version 2.43.0"
            version_str = result.stdout.strip().split()[-1]
            parts = version_str.split(".")

            major = int(parts[0])
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0

            self._version = (major, minor, patch)
            return self._version

        except (subprocess.CalledProcessError, ValueError, IndexError) as e:
            raise GitError(f"Failed to parse git version: {e}", e) from e

    def _run_git_command(
        self,
        args: list[str],
        cwd: Path | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """Run a git command with the given arguments.

        Args:
            args: List of git command arguments.
            cwd: Working directory for the command.
            check: Whether to check return code.

        Returns:
            CompletedProcess instance.

        Raises:
            GitError: If the command fails.
        """
        try:
            return subprocess.run(
                ["git"] + args,
                cwd=str(cwd) if cwd else None,
                capture_output=True,
                text=True,
                check=check,
            )
        except subprocess.CalledProcessError as e:
            raise GitError(
                f"Git command failed: git {' '.join(args)}",
                e,
            ) from e

    def get_repo_root(self, path: Path | None = None) -> Path:
        """Get the root of the git repository.

        Args:
            path: Optional path within the repository. Defaults to repo_path or current directory.

        Returns:
            Path to the repository root.

        Raises:
            GitError: If not in a git repository.
        """
        repo_path = path if path is not None else getattr(self, "_repo_path", None)

        # Use --git-common-dir to find the main repo from any worktree
        # This returns the path to the .git directory of the main repository
        # even when called from within a worktree
        result = self._run_git_command(["rev-parse", "--git-common-dir"], cwd=repo_path)
        git_common_dir = Path(result.stdout.strip())

        # Resolve git_common_dir to absolute path relative to repo_path
        if not git_common_dir.is_absolute():
            base = repo_path if repo_path else Path.cwd()
            git_common_dir = (base / git_common_dir).resolve()

        # The repo root is the parent of the .git directory
        # If --git-common-dir returns a file (like .git file for worktrees), resolve it
        if git_common_dir.is_file():
            # It's a .git file, read the actual git dir path
            git_dir = git_common_dir.read_text().strip()
            if git_dir.startswith("./"):
                git_dir = git_dir[2:]
            # The repo root is the parent of the .git directory
            return git_common_dir.parent / git_dir

        # Otherwise, it's the .git directory itself, get parent
        return git_common_dir.parent

    def worktree_add(self, path: Path, branch: str, create_branch: bool = True) -> None:
        """Create a new git worktree.

        Args:
            path: Path where the worktree will be created.
            branch: Branch name for the worktree.
            create_branch: Whether to create the branch if it doesn't exist.

        Raises:
            GitError: If worktree creation fails.
        """
        args = ["worktree", "add"]
        if create_branch:
            args.append("-b")
            args.append(branch)
        else:
            args.append(branch)
        args.append(str(path))

        self._run_git_command(args, cwd=getattr(self, "_repo_path", None))

    def worktree_remove(self, path: Path, force: bool = False) -> None:
        """Remove a git worktree.

        Args:
            path: Path to the worktree to remove.
            force: Whether to force removal even with uncommitted changes.

        Raises:
            GitError: If worktree removal fails.
        """
        args = ["worktree", "remove"]
        if force:
            args.append("--force")
        args.append(str(path))

        self._run_git_command(args, cwd=getattr(self, "_repo_path", None))

    def worktree_list(self) -> list[dict[str, str]]:
        """List all git worktrees.

        Returns:
            List of dictionaries containing worktree information.
            Each dict contains 'path', 'branch', and optionally 'HEAD'.
        """
        result = self._run_git_command(
            ["worktree", "list", "--porcelain"], cwd=getattr(self, "_repo_path", None)
        )
        worktrees: list[dict[str, str]] = []

        current_worktree: dict[str, str] = {}
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                if current_worktree:
                    worktrees.append(current_worktree)
                    current_worktree = {}
                continue

            if line.startswith("worktree "):
                current_worktree["path"] = line.split(" ", 1)[1]
            elif line.startswith("branch "):
                current_worktree["branch"] = line.split(" ", 1)[1]
            elif line == "HEAD":
                pass  # HEAD line, not needed for basic info
            elif line.startswith("HEAD "):
                current_worktree["HEAD"] = line.split(" ", 1)[1]

        if current_worktree:
            worktrees.append(current_worktree)

        return worktrees

    def worktree_is_valid(self, path: Path) -> bool:
        """Check if a path is a valid git worktree (M-02 requirement).

        Validates:
        - Path exists
        - Path is a git worktree (checked via git worktree list)
        - Path is not the main repo

        Args:
            path: Path to check.

        Returns:
            True if the path is a valid worktree, False otherwise.
        """
        # Check path exists
        if not path.exists():
            return False

        # Get absolute path for comparison
        abs_path = path.resolve()

        # Check if path is in the worktree list
        try:
            worktrees = self.worktree_list()
            for wt in worktrees:
                wt_path = Path(wt["path"]).resolve()
                if wt_path == abs_path:
                    # Found it in worktree list - now verify it's not the main repo
                    # The main repo is typically the first entry without 'bare' attribute
                    # We'll check if it's the main working directory
                    main_repo = self.get_repo_root()
                    return abs_path != main_repo.resolve()
        except GitError:
            return False

        return False

    def branch_create(self, branch: str, start_point: str | None = None) -> None:
        """Create a new git branch.

        Args:
            branch: Name of the branch to create.
            start_point: Optional starting point (commit hash, branch, tag).

        Raises:
            GitError: If branch creation fails.
        """
        args = ["branch"]
        if start_point:
            args.extend([branch, start_point])
        else:
            args.append(branch)

        self._run_git_command(args, cwd=getattr(self, "_repo_path", None))

    def branch_delete(self, branch: str, force: bool = False) -> None:
        """Delete a git branch.

        Args:
            branch: Name of the branch to delete.
            force: Whether to force delete even if not merged.

        Raises:
            GitError: If branch deletion fails.
        """
        args = ["branch", "-d" if not force else "-D"]
        args.append(branch)

        self._run_git_command(args, cwd=getattr(self, "_repo_path", None))

    def is_clean(self, path: Path | None = None) -> bool:
        """Check if the working tree is clean (no uncommitted changes).

        Args:
            path: Optional path within the repository to check. Defaults to repo_path.

        Returns:
            True if the working tree is clean, False otherwise.

        Raises:
            GitError: If the check fails.
        """
        repo_path = path if path is not None else getattr(self, "_repo_path", None)
        result = self._run_git_command(["status", "--porcelain"], cwd=repo_path)
        # If output is empty, the working tree is clean
        return result.stdout.strip() == ""
