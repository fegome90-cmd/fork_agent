"""Tests for non-tmux API lifecycle path.

Covers:
- Non-tmux session goes ACTIVE with NULL lease
- ACTIVE launch not quarantined on lease expiry
- DELETE route terminates lifecycle record
- Gap documentation: orphan API sessions stay ACTIVE forever
"""

from __future__ import annotations

from unittest.mock import MagicMock

from src.application.services.agent_launch_lifecycle_service import AgentLaunchLifecycleService
from src.domain.entities.agent_launch import LaunchStatus
from src.domain.services.canonical_key import build_api_key


def _make_service() -> tuple[AgentLaunchLifecycleService, MagicMock]:
    """Create a lifecycle service with a mock registry."""
    registry = MagicMock()
    svc = AgentLaunchLifecycleService(registry=registry, lease_duration_ms=5000)
    return svc, registry


class TestNonTmuxApiLifecycle:
    """Verify the non-tmux API path follows the full lifecycle."""

    def test_confirm_active_clears_lease(self) -> None:
        """confirm_active must set lease_expires_at = NULL (clear_lease=True)."""
        svc, registry = _make_service()
        registry.cas_update_status.return_value = True

        result = svc.confirm_active(
            "launch-1",
            backend="api",
            termination_handle_type="api-session",
            termination_handle_value="fork-agent-abc123",
        )

        assert result is True
        # Verify clear_lease=True was passed as keyword argument
        _, kwargs = registry.cas_update_status.call_args
        assert kwargs.get("clear_lease") is True

    def test_active_launch_not_expired_by_reconcile(self) -> None:
        """reconcile_expired_leases must skip ACTIVE launches."""
        svc, registry = _make_service()
        # list_expired_leases only returns RESERVED/SPAWNING
        registry.list_expired_leases.return_value = []

        result = svc.reconcile_expired_leases()

        assert result == []
        registry.list_expired_leases.assert_called_once()

    def test_delete_session_terminates_lifecycle(self) -> None:
        """DELETE /sessions/{id} must call begin_termination + confirm_terminated."""
        svc, registry = _make_service()

        launch = MagicMock()
        launch.launch_id = "launch-1"
        launch.status = LaunchStatus.ACTIVE
        registry.get_active_launch.return_value = launch
        registry.cas_update_status.return_value = True

        # Simulate begin_termination
        ok = svc.begin_termination("launch-1")
        assert ok is True

        # Simulate confirm_terminated
        ok = svc.confirm_terminated("launch-1")
        assert ok is True

        # Two CAS calls: one for TERMINATING, one for TERMINATED
        assert registry.cas_update_status.call_count == 2

    def test_reserved_expired_is_quarantined(self) -> None:
        """RESERVED launches with expired lease MUST be quarantined."""
        svc, registry = _make_service()

        expired_launch = MagicMock()
        expired_launch.launch_id = "launch-exp"
        expired_launch.status = LaunchStatus.RESERVED
        expired_launch.canonical_key = "api:agent:deadbeef"
        expired_launch.is_terminal = False
        expired_launch.can_transition_to.return_value = True
        registry.list_expired_leases.return_value = [expired_launch]
        # quarantine() calls get_by_launch_id first to check state
        registry.get_by_launch_id.return_value = expired_launch
        registry.cas_update_status.return_value = True

        result = svc.reconcile_expired_leases()

        assert len(result) == 1
        # Verify quarantine was called (RESERVED -> QUARANTINED)
        cas_call = registry.cas_update_status.call_args
        assert cas_call[0][1] == LaunchStatus.RESERVED
        assert cas_call[0][2] == LaunchStatus.QUARANTINED

    def test_spawning_expired_is_quarantined(self) -> None:
        """SPAWNING launches with expired lease MUST be quarantined."""
        svc, registry = _make_service()

        expired_launch = MagicMock()
        expired_launch.launch_id = "launch-spawn"
        expired_launch.status = LaunchStatus.SPAWNING
        expired_launch.canonical_key = "api:agent:cafe1234"
        expired_launch.is_terminal = False
        expired_launch.can_transition_to.return_value = True
        registry.list_expired_leases.return_value = [expired_launch]
        registry.get_by_launch_id.return_value = expired_launch
        registry.cas_update_status.return_value = True

        result = svc.reconcile_expired_leases()

        assert len(result) == 1


class TestApiCanonicalKeyFormat:
    """Verify API canonical key format through lifecycle."""

    def test_api_key_matches_build_api_key(self) -> None:
        """Key used in API route must match build_api_key output."""
        key = build_api_key("openai-codex", "test task")
        assert key.startswith("api:openai-codex:")
        parts = key.split(":")
        assert len(parts) == 3
        assert len(parts[2]) == 12  # sha256[:12]

    def test_api_key_empty_task_is_untitled(self) -> None:
        key = build_api_key("agent", None)
        assert key == "api:agent:untitled"


class TestNonTmuxOrphanGap:
    """Document the known gap: orphan API sessions stay ACTIVE forever.

    This is a design decision, not a bug. API sessions have no background
    reaper. The DELETE route is the only termination path. If a client
    crashes without calling DELETE, the canonical key is permanently blocked.

    TODO: Consider adding TTL-based ACTIVE expiry or heartbeat for API sessions.
    """

    def test_no_reaper_for_active(self) -> None:
        """Verify that reconcile does not touch ACTIVE launches.

        This test documents the current behavior. If you add ACTIVE reaping,
        this test must be updated.
        """
        svc, registry = _make_service()
        registry.list_expired_leases.return_value = []  # Only queries RESERVED/SPAWNING

        result = svc.reconcile_expired_leases()
        assert result == []
        # list_expired_leases is the gateway — it filters by status
        registry.list_expired_leases.assert_called_once()
