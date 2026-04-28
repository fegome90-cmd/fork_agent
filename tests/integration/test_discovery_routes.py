"""Integration tests for discovery routes."""

from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.interfaces.api.dependencies import verify_api_key
from src.interfaces.api.routes.discovery import router


async def mock_verify_api_key() -> str:
    """Mock API key verification that always succeeds."""
    return "test-api-key"


@pytest.fixture
def test_app() -> FastAPI:
    """Create test app with discovery router and mocked auth."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    # Override the dependency
    app.dependency_overrides[verify_api_key] = mock_verify_api_key
    return app


@pytest.fixture
def client(test_app: FastAPI) -> Generator[TestClient, None, None]:
    """Create test client with mocked API key verification."""
    with TestClient(test_app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.mark.integration
class TestDiscoveryOverviewEndpoint:
    """Tests for GET /api/v1/discovery endpoint."""

    def test_discovery_returns_overview_card(self, client: TestClient) -> None:
        """Discovery endpoint should return overview card."""
        response = client.get("/api/v1/discovery")

        assert response.status_code == 200
        data = response.json()
        assert data["card_type"] == "overview"
        assert "data" in data
        assert data["data"]["api_name"] == "Fork Agent API"

    def test_discovery_includes_auth_info(self, client: TestClient) -> None:
        """Discovery card should include authentication info."""
        response = client.get("/api/v1/discovery")

        assert response.status_code == 200
        data = response.json()
        auth = data["data"]["auth"]
        assert auth["type"] == "api_key"
        assert auth["header"] == "X-API-Key"

    def test_discovery_includes_endpoints(self, client: TestClient) -> None:
        """Discovery card should list available endpoints."""
        response = client.get("/api/v1/discovery")

        assert response.status_code == 200
        data = response.json()
        endpoints = data["data"]["endpoints"]
        assert len(endpoints) > 0

        # Should include health endpoint (no auth required)
        health_endpoints = [e for e in endpoints if "/health" in e["path"]]
        assert len(health_endpoints) > 0
        assert health_endpoints[0]["auth_required"] is False

    def test_discovery_includes_quick_actions(self, client: TestClient) -> None:
        """Discovery card should include quick actions."""
        response = client.get("/api/v1/discovery")

        assert response.status_code == 200
        data = response.json()
        assert "quick_actions" in data
        assert len(data["quick_actions"]) > 0

    def test_discovery_includes_cache_ttl(self, client: TestClient) -> None:
        """Discovery card should include cache TTL."""
        response = client.get("/api/v1/discovery")

        assert response.status_code == 200
        data = response.json()
        assert "cache_ttl" in data
        assert data["cache_ttl"] > 0


@pytest.mark.integration
class TestDiscoveryWorkflowsEndpoint:
    """Tests for GET /api/v1/discovery/workflows endpoint."""

    def test_workflows_returns_list(self, client: TestClient) -> None:
        """Workflows endpoint should return list of workflows."""
        response = client.get("/api/v1/discovery/workflows")

        assert response.status_code == 200
        data = response.json()
        assert "workflows" in data
        assert len(data["workflows"]) > 0

    def test_workflows_include_full_development_cycle(self, client: TestClient) -> None:
        """Workflows should include full-development-cycle workflow."""
        response = client.get("/api/v1/discovery/workflows")

        assert response.status_code == 200
        data = response.json()
        workflow_ids = [w["workflow_id"] for w in data["workflows"]]
        assert "full-development-cycle" in workflow_ids

    def test_workflow_has_steps(self, client: TestClient) -> None:
        """Each workflow should have steps."""
        response = client.get("/api/v1/discovery/workflows")

        assert response.status_code == 200
        data = response.json()
        for workflow in data["workflows"]:
            assert "steps" in workflow
            assert len(workflow["steps"]) > 0

    def test_workflow_quick_agent_session_exists(self, client: TestClient) -> None:
        """Should include quick-agent-session workflow."""
        response = client.get("/api/v1/discovery/workflows")

        assert response.status_code == 200
        data = response.json()
        workflow_ids = [w["workflow_id"] for w in data["workflows"]]
        assert "quick-agent-session" in workflow_ids


@pytest.mark.integration
class TestDiscoveryErrorGuidanceEndpoint:
    """Tests for GET /api/v1/discovery/errors/{status_code} endpoint."""

    def test_error_guidance_401(self, client: TestClient) -> None:
        """Should return guidance for 401 errors."""
        response = client.get("/api/v1/discovery/errors/401")

        assert response.status_code == 200
        data = response.json()
        assert data["card_type"] == "error"
        assert data["data"]["status_code"] == 401
        assert "recovery_steps" in data["data"]

    def test_error_guidance_404(self, client: TestClient) -> None:
        """Should return guidance for 404 errors."""
        response = client.get("/api/v1/discovery/errors/404")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status_code"] == 404

    def test_error_guidance_429(self, client: TestClient) -> None:
        """Should return guidance for 429 rate limit errors."""
        response = client.get("/api/v1/discovery/errors/429")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status_code"] == 429

    def test_error_guidance_503(self, client: TestClient) -> None:
        """Should return guidance for 503 service unavailable errors."""
        response = client.get("/api/v1/discovery/errors/503")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status_code"] == 503

    def test_error_guidance_unknown_code_returns_generic(self, client: TestClient) -> None:
        """Unknown error codes should return generic guidance."""
        response = client.get("/api/v1/discovery/errors/999")

        # Should still return 200 with generic guidance
        assert response.status_code == 200
        data = response.json()
        assert "recovery_steps" in data["data"]
        assert data["data"]["status_code"] == 999

    def test_error_guidance_400(self, client: TestClient) -> None:
        """Should return guidance for 400 bad request errors."""
        response = client.get("/api/v1/discovery/errors/400")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status_code"] == 400
        assert data["data"]["title"] == "Bad Request"


@pytest.mark.integration
class TestDiscoveryAgentBackends:
    """Tests for agent backend info in discovery."""

    def test_discovery_includes_available_agents(self, client: TestClient) -> None:
        """Discovery should list available agent backends."""
        response = client.get("/api/v1/discovery")

        assert response.status_code == 200
        data = response.json()
        agents = data["data"]["available_agents"]
        # Should have at least the registered backends (even if not installed)
        assert isinstance(agents, list)

    def test_discovery_agents_have_required_fields(self, client: TestClient) -> None:
        """Agent backend info should have required fields."""
        response = client.get("/api/v1/discovery")

        assert response.status_code == 200
        data = response.json()
        agents = data["data"]["available_agents"]

        for agent in agents:
            assert "name" in agent
            assert "display_name" in agent
            assert "available" in agent
            assert isinstance(agent["available"], bool)


@pytest.mark.integration
class TestDiscoveryCommonErrors:
    """Tests for common errors list in discovery."""

    def test_discovery_includes_common_errors(self, client: TestClient) -> None:
        """Discovery should list common error codes."""
        response = client.get("/api/v1/discovery")

        assert response.status_code == 200
        data = response.json()
        common_errors = data["data"]["common_errors"]
        assert isinstance(common_errors, list)
        assert 401 in common_errors
        assert 404 in common_errors
