"""Pytest configuration and fixtures for E2E tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from src.application.services.workspace.entities import (
    LayoutType,
    WorkspaceConfig,
)
from src.application.services.workspace.hook_runner import HookRunner
from src.application.services.workspace.workspace_manager import WorkspaceManager
from src.infrastructure.platform.git.git_command_executor import GitCommandExecutor


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repository with initial commit."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # Initialize git repo
    subprocess.run(
        ["git", "init"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    # Configure git user
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    # Create initial commit
    (repo_path / "README.md").write_text("# Test Repository\n")
    subprocess.run(
        ["git", "add", "README.md"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    return repo_path


@pytest.fixture
def hooks_dir(git_repo: Path) -> Path:
    """Create hooks directory within the repo."""
    hooks_dir = git_repo / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    return hooks_dir


@pytest.fixture
def git_executor(git_repo: Path) -> GitCommandExecutor:
    """Create GitCommandExecutor pointing to test repo."""
    return GitCommandExecutor(repo_path=git_repo)


@pytest.fixture
def workspace_config(hooks_dir: Path) -> WorkspaceConfig:
    """Create workspace configuration."""
    return WorkspaceConfig(
        default_layout=LayoutType.NESTED,
        auto_cleanup=True,
        hooks_dir=hooks_dir,
    )


@pytest.fixture
def workspace_config_no_hooks() -> WorkspaceConfig:
    """Create workspace configuration without hooks."""
    return WorkspaceConfig(
        default_layout=LayoutType.NESTED,
        auto_cleanup=False,
        hooks_dir=None,
    )


@pytest.fixture
def hook_runner(hooks_dir: Path) -> HookRunner:
    """Create HookRunner."""
    return HookRunner(hooks_dir=hooks_dir, timeout=30)


@pytest.fixture
def workspace_manager(
    git_executor: GitCommandExecutor,
    workspace_config: WorkspaceConfig,
    hook_runner: HookRunner,
) -> WorkspaceManager:
    """Create WorkspaceManager with hooks."""
    return WorkspaceManager(
        git_executor=git_executor,
        config=workspace_config,
        hook_runner=hook_runner,
    )


@pytest.fixture
def workspace_manager_no_hooks(
    git_executor: GitCommandExecutor,
    workspace_config_no_hooks: WorkspaceConfig,
) -> WorkspaceManager:
    """Create WorkspaceManager without hooks."""
    return WorkspaceManager(
        git_executor=git_executor,
        config=workspace_config_no_hooks,
        hook_runner=None,
    )
