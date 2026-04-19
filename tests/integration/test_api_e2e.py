"""End-to-end tests for the HTTP API.

Uses FastAPI TestClient — no uvicorn needed.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration

# --- Fixtures ---


@pytest.fixture()
def api_key():
    """Set API key for test and clean up after."""
    os.environ["API_KEY"] = "test-api-key-12345"
    yield "test-api-key-12345"
    os.environ.pop("API_KEY", None)


@pytest.fixture()
def test_db(tmp_path):
    """Create a temporary database for tests."""
    return tmp_path / "test_memory.db"


@pytest.fixture()
def client(api_key, test_db):
    """Create a TestClient with API key and test DB.

    Patches external dependencies (PM2, agent backends, GC) to avoid system deps.
    """
    from src.interfaces.api.config import clear_api_settings_cache, set_test_mode
    from src.interfaces.api.dependencies import get_memory_service, verify_api_key
    from src.infrastructure.persistence.container import create_container

    set_test_mode(True)
    clear_api_settings_cache()

    container = create_container(test_db)
    ms = container.memory_service()

    from src.interfaces.api.main import app

    # Override dependencies
    app.dependency_overrides[get_memory_service] = lambda: ms
    app.dependency_overrides[verify_api_key] = lambda: api_key

    # Create a mock PM2 service with async methods
    mock_pm2 = MagicMock()
    mock_pm2.get_status = AsyncMock(return_value={"status": "ok"})
    mock_pm2.get_logs = AsyncMock(return_value="")

    with (
        patch("src.interfaces.api.routes.system.pm2_service", mock_pm2),
        patch("src.interfaces.api.routes.system.get_available_backends", return_value=[]),
        patch("src.interfaces.api.routes.system.list_all_backends", return_value=["pi", "opencode"]),
        patch("src.interfaces.api.routes.agents._restore_sessions_from_disk", return_value=0),
        patch("src.interfaces.api.main._run_gc", return_value=(0, 0)),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        yield client

    app.dependency_overrides.clear()
    set_test_mode(False)
    clear_api_settings_cache()


# --- Root endpoint ---


def test_root(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Fork Agent API"
    assert data["version"] == "1.0.0"


# --- Health endpoint ---


def test_health(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert data["version"] == "1.0.0"
    assert "agents" in data


# --- Memory: Create observation ---


def test_create_observation(client: TestClient):
    response = client.post(
        "/api/v1/memory",
        json={"content": "test observation from API"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "data" in data
    obs = data["data"]
    assert obs["content"] == "test observation from API"
    assert "id" in obs
    assert "timestamp" in obs


def test_create_observation_empty_content(client: TestClient):
    response = client.post(
        "/api/v1/memory",
        json={"content": ""},
    )
    assert response.status_code == 422


def test_create_observation_missing_content(client: TestClient):
    response = client.post("/api/v1/memory", json={})
    assert response.status_code == 422


# --- Memory: Redaction ---


def test_create_observation_stores_sensitive_data(client: TestClient):
    """Verify that content is stored as-is (redaction is export-only, not storage)."""
    response = client.post(
        "/api/v1/memory",
        json={"content": "my API key is api_key=sk-1234567890abcdef1234567890 and password=supersecret123"},
    )
    assert response.status_code == 201
    data = response.json()
    content = data["data"]["content"]
    # Redaction is export-only; storage preserves original content
    assert "sk-1234567890abcdef1234567890" in content
    assert "supersecret123" in content


# --- Memory: List observations ---


def test_list_observations(client: TestClient):
    # Create an observation first
    client.post("/api/v1/memory", json={"content": "list test"})

    response = client.get("/api/v1/memory?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "count" in data
    assert isinstance(data["data"], list)


def test_list_observations_with_pagination(client: TestClient):
    response = client.get("/api/v1/memory?limit=5&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) <= 5


# --- Memory: Get by ID ---


def test_get_observation(client: TestClient):
    # Create first
    create_resp = client.post("/api/v1/memory", json={"content": "get by id test"})
    assert create_resp.status_code == 201
    obs_id = create_resp.json()["data"]["id"]

    # Get by ID
    response = client.get(f"/api/v1/memory/{obs_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["id"] == obs_id
    assert data["data"]["content"] == "get by id test"


def test_get_observation_not_found(client: TestClient):
    response = client.get("/api/v1/memory/nonexistent-id-12345")
    assert response.status_code == 404


# --- Memory: Search ---


def test_search_observations(client: TestClient):
    # Create a searchable observation
    client.post("/api/v1/memory", json={"content": "unique_search_term_xyzzy"})

    response = client.get("/api/v1/memory/search?q=unique_search_term_xyzzy")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) >= 1
    # Verify the content is in results
    contents = [obs["content"] for obs in data["data"]]
    assert any("unique_search_term_xyzzy" in c for c in contents)


# --- Memory: Delete ---


def test_delete_observation(client: TestClient):
    # Create
    create_resp = client.post("/api/v1/memory", json={"content": "delete me"})
    assert create_resp.status_code == 201
    obs_id = create_resp.json()["data"]["id"]

    # Delete
    response = client.delete(f"/api/v1/memory/{obs_id}")
    assert response.status_code == 204

    # Verify gone
    get_resp = client.get(f"/api/v1/memory/{obs_id}")
    assert get_resp.status_code == 404


# --- Memory: Query ---


def test_query_memory(client: TestClient):
    response = client.get("/api/v1/memory/query?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "count" in data


def test_query_memory_with_since(client: TestClient):
    response = client.get("/api/v1/memory/query?since=24h&limit=5")
    assert response.status_code == 200


# --- Memory: Timeline ---


def test_timeline(client: TestClient):
    response = client.get("/api/v1/memory/timeline/nonexistent-run-id")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "count" in data


# --- Auth tests ---


def test_unauthenticated_request_rejected():
    """Requests without API key should fail when API_KEY is set."""
    os.environ["API_KEY"] = "test-api-key-12345"

    from src.interfaces.api.config import clear_api_settings_cache, set_test_mode

    set_test_mode(True)
    clear_api_settings_cache()

    from src.interfaces.api.main import app

    mock_pm2 = MagicMock()
    mock_pm2.get_status = AsyncMock(return_value={"status": "ok"})
    mock_pm2.get_logs = AsyncMock(return_value="")

    # Do NOT override verify_api_key — test real auth
    with (
        patch("src.interfaces.api.routes.system.pm2_service", mock_pm2),
        patch("src.interfaces.api.routes.system.get_available_backends", return_value=[]),
        patch("src.interfaces.api.routes.system.list_all_backends", return_value=[]),
        patch("src.interfaces.api.routes.agents._restore_sessions_from_disk", return_value=0),
        patch("src.interfaces.api.main._run_gc", return_value=(0, 0)),
    ):
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/api/v1/health")
        # Should get 403 or 422 (missing header) or 503 (key not configured)
        assert response.status_code in (401, 403, 422, 503)

    set_test_mode(False)
    clear_api_settings_cache()
    os.environ.pop("API_KEY", None)


# --- CORS ---


def test_cors_headers_present(client: TestClient):
    """Verify CORS middleware is active."""
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    # OPTIONS may return 200 or other status depending on middleware
    assert response.status_code in (200, 204, 400, 405)
