"""Tests for BUG-16: API POST /memory should persist all fields."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


@pytest.fixture()
def api_key():
    os.environ["API_KEY"] = "test-api-key-12345"
    yield "test-api-key-12345"
    os.environ.pop("API_KEY", None)


@pytest.fixture()
def client(api_key, tmp_path):
    from src.interfaces.api.config import clear_api_settings_cache, set_test_mode
    from src.interfaces.api.dependencies import get_memory_service, verify_api_key
    from src.infrastructure.persistence.container import create_container

    set_test_mode(True)
    clear_api_settings_cache()

    test_db = tmp_path / "test_memory.db"
    container = create_container(test_db)
    ms = container.memory_service()

    from src.interfaces.api.main import app

    app.dependency_overrides[get_memory_service] = lambda: ms
    app.dependency_overrides[verify_api_key] = lambda: api_key

    mock_pm2 = MagicMock()
    mock_pm2.get_status = AsyncMock(return_value={"status": "ok"})
    mock_pm2.get_logs = AsyncMock(return_value="")

    with (
        patch("src.interfaces.api.routes.system.pm2_service", mock_pm2),
        patch("src.interfaces.api.routes.system.get_available_backends", return_value=[]),
        patch("src.interfaces.api.routes.system.list_all_backends", return_value=[]),
        patch("src.interfaces.api.routes.agents._restore_sessions_from_disk", return_value=0),
        patch("src.interfaces.api.main._run_gc", return_value=(0, 0)),
    ):
        yield TestClient(app, raise_server_exceptions=False)

    app.dependency_overrides.clear()
    set_test_mode(False)
    clear_api_settings_cache()


class TestBug16ApiFields:
    """BUG-16: POST /memory with type/project/topic_key/metadata/title."""

    def test_create_with_all_fields(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/memory",
            json={
                "content": "api field test",
                "type": "decision",
                "project": "api-proj",
                "topic_key": "test/api",
                "metadata": {"what": "testing", "why": "bugfix"},
                "title": "API Fields Test",
            },
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["content"] == "api field test"
        assert data["type"] == "decision"
        assert data["project"] == "api-proj"
        assert data["topic_key"] == "test/api"
        assert data["metadata"]["what"] == "testing"

    def test_create_with_partial_fields(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/memory",
            json={
                "content": "partial test",
                "type": "discovery",
                "project": "my-project",
            },
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["type"] == "discovery"
        assert data["project"] == "my-project"
        assert data["topic_key"] is None

    def test_fields_persisted_in_db(self, client: TestClient) -> None:
        client.post(
            "/api/v1/memory",
            json={
                "content": "persist test",
                "type": "bugfix",
                "project": "persist-proj",
                "topic_key": "test/persist",
            },
        )
        # Search to verify
        response = client.get("/api/v1/memory/search?q=persist+test")
        assert response.status_code == 200
        results = response.json()["data"]
        assert len(results) >= 1
        obs = results[0]
        assert obs["type"] == "bugfix"
        assert obs["project"] == "persist-proj"
        assert obs["topic_key"] == "test/persist"


class TestBug17PutEndpoint:
    """BUG-17: PUT /memory/{id} endpoint."""

    def test_put_update_content(self, client: TestClient) -> None:
        create_resp = client.post("/api/v1/memory", json={"content": "original content"})
        obs_id = create_resp.json()["data"]["id"]

        response = client.put(
            f"/api/v1/memory/{obs_id}",
            json={"content": "updated content"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["content"] == "updated content"
        assert data["revision_count"] == 2

    def test_put_update_type(self, client: TestClient) -> None:
        create_resp = client.post("/api/v1/memory", json={"content": "type test"})
        obs_id = create_resp.json()["data"]["id"]

        response = client.put(
            f"/api/v1/memory/{obs_id}",
            json={"type": "pattern"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["type"] == "pattern"

    def test_put_not_found(self, client: TestClient) -> None:
        response = client.put(
            "/api/v1/memory/nonexistent-id",
            json={"content": "nope"},
        )
        assert response.status_code == 404

    def test_put_updates_all_fields(self, client: TestClient) -> None:
        create_resp = client.post(
            "/api/v1/memory",
            json={"content": "multi field test"},
        )
        obs_id = create_resp.json()["data"]["id"]

        response = client.put(
            f"/api/v1/memory/{obs_id}",
            json={
                "content": "updated all",
                "type": "decision",
                "project": "new-proj",
                "topic_key": "test/updated",
                "metadata": {"updated": True},
                "title": "Updated Title",
            },
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["content"] == "updated all"
        assert data["type"] == "decision"
        assert data["project"] == "new-proj"
        assert data["topic_key"] == "test/updated"
        assert data["metadata"]["updated"] is True
