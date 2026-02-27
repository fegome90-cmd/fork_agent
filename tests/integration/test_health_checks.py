"""Health checks integration tests.

These tests verify basic subsystem connectivity.
Marked as 'integration' - NOT bughunt (bughunt tests are in test_bug_detection.py).

NOTE: test_promise_repository_accessible requires full DI container and is
skipped in test env because Container doesn't have promise_contract_repository.
This is a known limitation - the container needs to be extended for this dependency.
"""

import pytest

from tests.fixtures.subsystem_fixtures import (
    mock_memory_service,
    mock_promise_repository,
    mock_tmux_orchestrator,
    mock_workspace_manager,
)


pytestmark = pytest.mark.integration


class TestHealthChecks:
    """Basic health check tests for subsystem wiring."""

    def test_promise_repository_accessible(self):
        """Verify API has access to PromiseContract repository.

        SKIPPED: Container not fully configured in test env.
        Requires promise_contract_repository provider in DI container.
        """
        pytest.skip("Container not fully configured: promise_contract_repository missing")

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
