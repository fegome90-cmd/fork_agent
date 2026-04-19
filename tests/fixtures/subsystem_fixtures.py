"""Subsystem fixtures for mocking external dependencies in bug detection tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_promise_repository():
    """Mock PromiseContractRepository for testing."""
    mock = MagicMock()
    mock.save.return_value = MagicMock(id="promise-123")
    mock.get_by_plan_id.return_value = None
    return mock


@pytest.fixture
def mock_tmux_orchestrator():
    """Mock TmuxOrchestrator for testing."""
    mock = MagicMock()
    mock.create_session.return_value = True
    mock.list_sessions.return_value = []
    mock.kill_session.return_value = True
    return mock


@pytest.fixture
def mock_memory_service():
    """Mock MemoryService for testing."""
    mock = MagicMock()
    mock.save.return_value = MagicMock(id="obs-123")
    mock.search.return_value = []
    return mock


@pytest.fixture
def mock_workspace_manager():
    """Mock WorkspaceManager for testing."""
    mock = MagicMock()
    mock.create_workspace.return_value = MagicMock(path="/tmp/test-workspace")
    mock.list_workspaces.return_value = []
    return mock


@pytest.fixture
def failing_promise_repository():
    """Mock PromiseContractRepository that always fails on save."""
    mock = MagicMock()

    def save_fails(*_args, **_kwargs):
        raise Exception("Database connection failed")

    mock.save = save_fails
    return mock
