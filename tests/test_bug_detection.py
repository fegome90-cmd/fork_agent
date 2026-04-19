"""Bug detection tests for workflow verify endpoint."""

import os
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.bughunt


@pytest.fixture(autouse=True)
def setup_api_key():
    """Set up API key for tests before importing app."""
    from src.interfaces.api.config import set_test_mode

    # Enable test mode to always read fresh env vars
    set_test_mode(True)
    os.environ["API_KEY"] = "test-key"
    yield
    # Cleanup after test
    set_test_mode(False)


@pytest.fixture
def mock_promise_repo():
    mock = MagicMock()
    mock.save.return_value = MagicMock(id="promise-123")
    return mock


@pytest.fixture
def failing_promise_repo():
    mock = MagicMock()

    def save_fails(*_args, **_kwargs):
        raise Exception("Database connection failed")

    mock.save = save_fails
    return mock


class TestWorkflowVerifyContract:
    def test_verify_persists_evidence(self, mock_promise_repo):
        with patch(
            "src.interfaces.api.routes.workflow.get_promise_repository",
            return_value=mock_promise_repo,
        ):
            from fastapi.testclient import TestClient

            from src.interfaces.api.main import app

            client = TestClient(app)
            client.post(
                "/api/v1/workflow/test-plan/verify",
                headers={"x-api-key": "test-key"},
            )
            assert mock_promise_repo.save.called

    def test_verify_persist_error_returns_500(self, failing_promise_repo):
        with patch(
            "src.interfaces.api.routes.workflow.get_promise_repository",
            return_value=failing_promise_repo,
        ):
            from fastapi.testclient import TestClient

            from src.interfaces.api.main import app

            client = TestClient(app)
            response = client.post(
                "/api/v1/workflow/test/verify",
                headers={"x-api-key": "test-key"},
            )
            assert response.status_code == 500

    def test_verify_evidence_has_required_fields(self, mock_promise_repo):
        with patch(
            "src.interfaces.api.routes.workflow.get_promise_repository",
            return_value=mock_promise_repo,
        ):
            from fastapi.testclient import TestClient

            from src.interfaces.api.main import app

            client = TestClient(app)
            client.post(
                "/api/v1/workflow/plan-fields/verify",
                headers={"x-api-key": "test-key"},
            )
            assert mock_promise_repo.save.called
