"""Unit tests for GitCommandExecutor."""

from unittest.mock import MagicMock, patch
from pathlib import Path

import pytest
import subprocess

from src.infrastructure.platform.git.git_command_executor import (
    GitCommandExecutor,
    MIN_GIT_VERSION,
)
from src.application.services.workspace.exceptions import (
    GitError,
    GitNotFoundError,
    GitVersionError,
)


class TestGitCommandExecutorInit:
    """Tests for GitCommandExecutor initialization."""

    @patch("subprocess.run")
    def test_init_git_available_and_valid_version(self, mock_run: MagicMock) -> None:
        """Test initialization with git available and valid version."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="git version 2.43.0",
            strip=lambda: "git version 2.43.0",
        )

        executor = GitCommandExecutor()

        assert executor._version == (2, 43, 0)

    @patch("subprocess.run")
    def test_init_git_version_2_20(self, mock_run: MagicMock) -> None:
        """Test initialization with minimum required version 2.20."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="git version 2.20.0",
            strip=lambda: "git version 2.20.0",
        )

        executor = GitCommandExecutor()

        assert executor._version == (2, 20, 0)

    @patch("subprocess.run")
    def test_init_git_not_found(self, mock_run: MagicMock) -> None:
        """Test initialization raises GitNotFoundError when git is not available."""
        mock_run.side_effect = FileNotFoundError("git not found")

        with pytest.raises(GitNotFoundError, match="not installed or not in PATH"):
            GitCommandExecutor()

    @patch("subprocess.run")
    def test_init_git_command_fails(self, mock_run: MagicMock) -> None:
        """Test initialization raises GitNotFoundError when git command fails."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        with pytest.raises(GitNotFoundError, match="command failed"):
            GitCommandExecutor()

    @patch("subprocess.run")
    def test_init_git_version_too_low(self, mock_run: MagicMock) -> None:
        """Test initialization raises GitVersionError when version < 2.20."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="git version 2.19.0",
            strip=lambda: "git version 2.19.0",
        )

        with pytest.raises(GitVersionError, match="must be >= 2.20"):
            GitCommandExecutor()


class TestGitCommandExecutorVersion:
    """Tests for get_git_version method."""

    @patch("subprocess.run")
    def test_get_git_version_cached(self, mock_run: MagicMock) -> None:
        """Test that get_git_version uses cached version."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="git version 2.43.0",
            strip=lambda: "git version 2.43.0",
        )

        executor = GitCommandExecutor()
        executor._version = (2, 43, 0)  # Set cached version

        version = executor.get_git_version()

        assert version == (2, 43, 0)
        mock_run.assert_not_called()

    @patch("subprocess.run")
    def test_get_git_version_parses_correctly(self, mock_run: MagicMock) -> None:
        """Test git version parsing."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="git version 2.43.0",
            strip=lambda: "git version 2.43.0",
        )

        executor = GitCommandExecutor.__new__(GitCommandExecutor)
        executor._version = None
        executor._verify_git_available = lambda: None
        executor._verify_git_version = lambda: None

        version = executor.get_git_version()

        assert version == (2, 43, 0)

    @patch("subprocess.run")
    def test_get_git_version_two_part(self, mock_run: MagicMock) -> None:
        """Test git version parsing with only major.minor."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="git version 2.30",
            strip=lambda: "git version 2.30",
        )

        executor = GitCommandExecutor.__new__(GitCommandExecutor)
        executor._version = None
        executor._verify_git_available = lambda: None
        executor._verify_git_version = lambda: None

        version = executor.get_git_version()

        assert version == (2, 30, 0)

    @patch("subprocess.run")
    def test_get_git_version_invalid_format(self, mock_run: MagicMock) -> None:
        """Test git version parsing with invalid format."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="invalid version",
            strip=lambda: "invalid version",
        )

        executor = GitCommandExecutor.__new__(GitCommandExecutor)
        executor._version = None

        with pytest.raises(GitError, match="Failed to parse"):
            executor.get_git_version()


class TestGitCommandExecutorRun:
    """Tests for _run_git_command method."""

    @patch("subprocess.run")
    def test_run_git_command_success(self, mock_run: MagicMock) -> None:
        """Test running git command successfully."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="output",
            stderr="",
        )

        executor = GitCommandExecutor.__new__(GitCommandExecutor)
        executor._version = (2, 43, 0)

        result = executor._run_git_command(["status"])

        assert result.returncode == 0
        assert result.stdout == "output"
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_run_git_command_failure(self, mock_run: MagicMock) -> None:
        """Test running git command that fails."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git", output="error")

        executor = GitCommandExecutor.__new__(GitCommandExecutor)
        executor._version = (2, 43, 0)

        with pytest.raises(GitError, match="Git command failed"):
            executor._run_git_command(["invalid-command"])

    @patch("subprocess.run")
    def test_run_git_command_with_cwd(self, mock_run: MagicMock) -> None:
        """Test running git command with cwd."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="output",
            stderr="",
        )

        executor = GitCommandExecutor.__new__(GitCommandExecutor)
        executor._version = (2, 43, 0)

        cwd = Path("/test/repo")
        executor._run_git_command(["status"], cwd=cwd)

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[1]["cwd"] == str(cwd)


class TestGitCommandExecutorRepoOperations:
    """Tests for repository operations."""

    @patch("subprocess.run")
    def test_get_repo_root(self, mock_run: MagicMock) -> None:
        """Test getting repository root."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="/test/repo\n",
            strip=lambda: "/test/repo",
        )

        executor = GitCommandExecutor.__new__(GitCommandExecutor)
        executor._version = (2, 43, 0)

        root = executor.get_repo_root()

        assert root == Path("/test/repo")
        mock_run.assert_called_once()


class TestGitCommandExecutorWorktreeOperations:
    """Tests for worktree operations."""

    @patch("subprocess.run")
    def test_worktree_add(self, mock_run: MagicMock) -> None:
        """Test adding a worktree."""
        mock_run.return_value = MagicMock(returncode=0)

        executor = GitCommandExecutor.__new__(GitCommandExecutor)
        executor._version = (2, 43, 0)

        path = Path("/test/repo/.worktrees/feature")
        executor.worktree_add(path, "feature", create_branch=True)

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "worktree" in call_args
        assert "add" in call_args
        assert "-b" in call_args
        assert "feature" in call_args

    @patch("subprocess.run")
    def test_worktree_add_without_branch_creation(self, mock_run: MagicMock) -> None:
        """Test adding a worktree without creating a branch."""
        mock_run.return_value = MagicMock(returncode=0)

        executor = GitCommandExecutor.__new__(GitCommandExecutor)
        executor._version = (2, 43, 0)

        path = Path("/test/repo/.worktrees/feature")
        executor.worktree_add(path, "feature", create_branch=False)

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "-b" not in call_args

    @patch("subprocess.run")
    def test_worktree_remove(self, mock_run: MagicMock) -> None:
        """Test removing a worktree."""
        mock_run.return_value = MagicMock(returncode=0)

        executor = GitCommandExecutor.__new__(GitCommandExecutor)
        executor._version = (2, 43, 0)

        path = Path("/test/repo/.worktrees/feature")
        executor.worktree_remove(path)

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "worktree" in call_args
        assert "remove" in call_args

    @patch("subprocess.run")
    def test_worktree_remove_force(self, mock_run: MagicMock) -> None:
        """Test removing a worktree with force."""
        mock_run.return_value = MagicMock(returncode=0)

        executor = GitCommandExecutor.__new__(GitCommandExecutor)
        executor._version = (2, 43, 0)

        path = Path("/test/repo/.worktrees/feature")
        executor.worktree_remove(path, force=True)

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "--force" in call_args

    @patch("subprocess.run")
    def test_worktree_list(self, mock_run: MagicMock) -> None:
        """Test listing worktrees."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="""worktree /test/repo
branch refs/heads/main

worktree /test/repo/.worktrees/feature
branch refs/heads/feature
""",
            strip=lambda x: x,
        )

        executor = GitCommandExecutor.__new__(GitCommandExecutor)
        executor._version = (2, 43, 0)

        worktrees = executor.worktree_list()

        assert len(worktrees) == 2
        assert worktrees[0]["path"] == "/test/repo"
        assert worktrees[0]["branch"] == "refs/heads/main"
        assert worktrees[1]["path"] == "/test/repo/.worktrees/feature"
        assert worktrees[1]["branch"] == "refs/heads/feature"

    @patch("subprocess.run")
    def test_worktree_list_empty(self, mock_run: MagicMock) -> None:
        """Test listing worktrees when there are none."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            strip=lambda x: x,
        )

        executor = GitCommandExecutor.__new__(GitCommandExecutor)
        executor._version = (2, 43, 0)

        worktrees = executor.worktree_list()

        assert worktrees == []


class TestWorktreeIsValid:
    """Tests for worktree_is_valid method (M-02 requirement)."""

    @patch.object(GitCommandExecutor, "worktree_list")
    @patch.object(GitCommandExecutor, "get_repo_root")
    def test_worktree_is_valid_true(self, mock_get_root: MagicMock, mock_list: MagicMock) -> None:
        """Test worktree_is_valid returns True for valid worktree."""
        worktree_path = Path("/test/repo/.worktrees/feature")
        
        mock_get_root.return_value = Path("/test/repo")
        mock_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
            {"path": "/test/repo/.worktrees/feature", "branch": "refs/heads/feature"},
        ]

        executor = GitCommandExecutor.__new__(GitCommandExecutor)
        executor._version = (2, 43, 0)

        # Need to mock path.exists() too
        with patch("pathlib.Path.exists", return_value=True):
            result = executor.worktree_is_valid(worktree_path)

        assert result is True

    @patch.object(GitCommandExecutor, "worktree_list")
    @patch.object(GitCommandExecutor, "get_repo_root")
    def test_worktree_is_valid_false_not_in_list(self, mock_get_root: MagicMock, mock_list: MagicMock) -> None:
        """Test worktree_is_valid returns False when not in worktree list."""
        worktree_path = Path("/test/repo/.worktrees/nonexistent")
        
        mock_get_root.return_value = Path("/test/repo")
        mock_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
        ]

        executor = GitCommandExecutor.__new__(GitCommandExecutor)
        executor._version = (2, 43, 0)

        with patch("pathlib.Path.exists", return_value=True):
            result = executor.worktree_is_valid(worktree_path)

        assert result is False

    @patch.object(GitCommandExecutor, "worktree_list")
    @patch.object(GitCommandExecutor, "get_repo_root")
    def test_worktree_is_valid_false_main_repo(self, mock_get_root: MagicMock, mock_list: MagicMock) -> None:
        """Test worktree_is_valid returns False for main repo."""
        worktree_path = Path("/test/repo")
        
        mock_get_root.return_value = Path("/test/repo")
        mock_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
        ]

        executor = GitCommandExecutor.__new__(GitCommandExecutor)
        executor._version = (2, 43, 0)

        with patch("pathlib.Path.exists", return_value=True):
            result = executor.worktree_is_valid(worktree_path)

        assert result is False

    @patch("pathlib.Path.exists")
    def test_worktree_is_valid_false_path_not_exists(self, mock_exists: MagicMock) -> None:
        """Test worktree_is_valid returns False when path doesn't exist."""
        mock_exists.return_value = False

        executor = GitCommandExecutor.__new__(GitCommandExecutor)
        executor._version = (2, 43, 0)

        result = executor.worktree_is_valid(Path("/nonexistent"))

        assert result is False


class TestGitCommandExecutorBranchOperations:
    """Tests for branch operations."""

    @patch("subprocess.run")
    def test_branch_create(self, mock_run: MagicMock) -> None:
        """Test creating a branch."""
        mock_run.return_value = MagicMock(returncode=0)

        executor = GitCommandExecutor.__new__(GitCommandExecutor)
        executor._version = (2, 43, 0)

        executor.branch_create("feature-branch")

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "branch" in call_args
        assert "feature-branch" in call_args

    @patch("subprocess.run")
    def test_branch_create_with_start_point(self, mock_run: MagicMock) -> None:
        """Test creating a branch with start point."""
        mock_run.return_value = MagicMock(returncode=0)

        executor = GitCommandExecutor.__new__(GitCommandExecutor)
        executor._version = (2, 43, 0)

        executor.branch_create("feature-branch", "v1.0.0")

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "feature-branch" in call_args
        assert "v1.0.0" in call_args

    @patch("subprocess.run")
    def test_branch_delete(self, mock_run: MagicMock) -> None:
        """Test deleting a branch."""
        mock_run.return_value = MagicMock(returncode=0)

        executor = GitCommandExecutor.__new__(GitCommandExecutor)
        executor._version = (2, 43, 0)

        executor.branch_delete("feature-branch")

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "-d" in call_args

    @patch("subprocess.run")
    def test_branch_delete_force(self, mock_run: MagicMock) -> None:
        """Test force deleting a branch."""
        mock_run.return_value = MagicMock(returncode=0)

        executor = GitCommandExecutor.__new__(GitCommandExecutor)
        executor._version = (2, 43, 0)

        executor.branch_delete("feature-branch", force=True)

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "-D" in call_args


class TestIsClean:
    """Tests for is_clean method."""

    @patch("subprocess.run")
    def test_is_clean_true(self, mock_run: MagicMock) -> None:
        """Test is_clean returns True when working tree is clean."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            strip=lambda x: x,
        )

        executor = GitCommandExecutor.__new__(GitCommandExecutor)
        executor._version = (2, 43, 0)

        result = executor.is_clean(Path("/test/repo"))

        assert result is True

    @patch("subprocess.run")
    def test_is_clean_false(self, mock_run: MagicMock) -> None:
        """Test is_clean returns False when working tree has changes."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="M modified.txt",
            strip=lambda x: x,
        )

        executor = GitCommandExecutor.__new__(GitCommandExecutor)
        executor._version = (2, 43, 0)

        result = executor.is_clean(Path("/test/repo"))

        assert result is False
