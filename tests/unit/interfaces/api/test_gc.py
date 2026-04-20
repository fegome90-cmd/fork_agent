"""Unit tests for zombie session garbage collection."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.application.services.agent.agent_manager import CleanupResult
from src.interfaces.api.main import _run_gc, app, get_gc_state
from src.interfaces.api.routes.agents import SessionStore, _restore_sessions_from_disk


@pytest.fixture
def client():
    from src.interfaces.api.dependencies import verify_api_key

    app.dependency_overrides[verify_api_key] = lambda: "test-key"
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestRestoreSessionsFromDisk:
    """Tests for _restore_sessions_from_disk()."""

    def test_restore_populates_store(self, tmp_path: Path):
        # Setup mock sessions directory
        sessions_dir = tmp_path / "api-sessions"
        sessions_dir.mkdir()

        session_data = {
            "session_id": "test-session",
            "agent_type": "opencode",
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "tmux_session": "fork-test",
            "hooks": []
        }
        (sessions_dir / "test-session.json").write_text(json.dumps(session_data))

        with patch("src.interfaces.api.routes.agents._sessions_dir", sessions_dir):
            # Clear memory only, don't use SessionStore.delete() as it hits disk
            with patch("src.interfaces.api.routes.agents._sessions", {}):
                count = _restore_sessions_from_disk()

                assert count == 1
                assert SessionStore.exists("test-session")
            session = SessionStore.get("test-session")
            assert session.session_id == "test-session"

    def test_restore_skips_invalid_json(self, tmp_path: Path):
        sessions_dir = tmp_path / "api-sessions"
        sessions_dir.mkdir()
        (sessions_dir / "invalid.json").write_text("not json")

        with patch("src.interfaces.api.routes.agents._sessions_dir", sessions_dir):
            count = _restore_sessions_from_disk()
            assert count == 0


class TestRunGc:
    """Tests for _run_gc()."""

    @patch("src.application.services.agent.agent_manager.AgentManager.cleanup_orphans")
    def test_run_gc_updates_state(self, mock_cleanup):
        mock_cleanup.return_value = CleanupResult(
            cleaned_sessions=["s1", "s2"],
            failed_sessions=["f1"],
            dry_run=False
        )

        cleaned, failed = _run_gc(min_age_seconds=0)

        assert cleaned == 2
        assert failed == 1

        state = get_gc_state()
        assert state.cleaned_count == 2
        assert state.failed_count == 1
        assert state.last_run_at is not None


class TestGcStatusEndpoint:
    """Tests for GET /sessions/gc/status."""

    def test_gc_status_never_run(self, client):
        with patch("src.interfaces.api.main._gc_state_lock"):  # noqa: SIM117
            with patch("src.interfaces.api.main._gc_state") as mock_state:
                mock_state.last_run_at = None

                response = client.get("/api/v1/agents/sessions/gc/status")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "never_run"
                assert data["last_run_at"] is None

    def test_gc_status_ok(self, client):
        with patch("src.interfaces.api.main._gc_state_lock"):  # noqa: SIM117
            with patch("src.interfaces.api.main._gc_state") as mock_state:
                mock_state.last_run_at = datetime.now()
                mock_state.cleaned_count = 5
                mock_state.failed_count = 0

                response = client.get("/api/v1/agents/sessions/gc/status")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "ok"
                assert data["cleaned_count"] == 5
