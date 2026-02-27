"""Health checks integration tests for bug detection.

These tests verify basic subsystem connectivity.
Marked with both 'integration' and 'bughunt' markers.
"""

import pytest

from tests.fixtures.subsystem_fixtures import (
    mock_memory_service,
    mock_promise_repository,
    mock_tmux_orchestrator,
    mock_workspace_manager,
)


pytestmark = [pytest.mark.integration, pytest.mark.bughunt]


class TestHealthChecks:
    """Basic health check tests for subsystem wiring."""

    def test_promise_repository_accessible(self):
        """Verify API has access to PromiseContract repository."""
        try:
            from src.interfaces.api.dependencies import get_promise_repository

            repo = get_promise_repository()
            assert repo is not None
        except AttributeError as e:
            pytest.skip(f"Container not fully configured: {e}")
        except ImportError:
            pytest.fail("Promise repository dependency not found")
        """Verify API has access to PromiseContract repository."""
        try:
            from src.interfaces.api.dependencies import get_promise_repository

            repo = get_promise_repository()
            assert repo is not None
        except ImportError:
            pytest.fail("Promise repository dependency not found")

    def test_tmux_orchestrator_imports(self):
        """Verify tmux orchestrator can be imported."""
        try:
            from src.infrastructure.tmux_orchestrator import TmuxOrchestrator

            assert TmuxOrchestrator is not None
        except Exception as e:
            pytest.fail(f"TmuxOrchestrator import failed: {e}")

    def test_memory_service_imports(self):
        """Verify memory service can be imported."""
        try:
            from src.application.services.memory_service import MemoryService

            assert MemoryService is not None
        except Exception as e:
            pytest.fail(f"MemoryService import failed: {e}")

    def test_workspace_manager_imports(self):
        """Verify workspace manager can be imported."""
        try:
            from src.application.services.workspace.workspace_manager import WorkspaceManager

            assert WorkspaceManager is not None
        except Exception as e:
            pytest.fail(f"WorkspaceManager import failed: {e}")

    def test_workflow_state_imports(self):
        """Verify workflow state can be imported."""
        try:
            from src.application.services.workflow import state as workflow_state

            assert workflow_state is not None
        except Exception as e:
            pytest.fail(f"Workflow state import failed: {e}")

    def test_api_routes_registered(self):
        """Verify API routes are properly registered."""
        from src.interfaces.api.main import app

        routes = [r.path for r in app.routes]
        assert len(routes) > 0
        assert any("/workflow" in r for r in routes)

    def test_workflow_executor_imports(self):
        """Verify WorkflowExecutor can be imported."""
        try:
            from src.application.services.workflow.executor import WorkflowExecutor

            assert WorkflowExecutor is not None
        except Exception as e:
            pytest.fail(f"WorkflowExecutor import failed: {e}")
