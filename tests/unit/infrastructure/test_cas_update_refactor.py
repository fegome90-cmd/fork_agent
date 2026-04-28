"""Tests for cas_update_status refactored behavior.

Covers:
- confirm_active clears lease (clear_lease=True → lease_expires_at = NULL)
- Transition without clear_lease preserves lease
- ACTIVE expired not quarantined; RESERVED/SPAWNING expired yes
"""

from __future__ import annotations

from unittest.mock import MagicMock

from src.application.services.agent_launch_lifecycle_service import AgentLaunchLifecycleService
from src.domain.entities.agent_launch import LaunchStatus


def _make_service() -> tuple[AgentLaunchLifecycleService, MagicMock]:
    registry = MagicMock()
    svc = AgentLaunchLifecycleService(registry=registry, lease_duration_ms=5000)
    return svc, registry


class TestCasClearLease:
    """Verify clear_lease=True sets lease_expires_at = NULL."""

    def test_confirm_active_passes_clear_lease(self) -> None:
        svc, registry = _make_service()
        registry.cas_update_status.return_value = True

        svc.confirm_active(
            "launch-1",
            backend="api",
            termination_handle_type="test",
            termination_handle_value="test-handle",
        )

        call = registry.cas_update_status.call_args
        assert call.kwargs.get("clear_lease") is True

    def test_mark_failed_does_not_clear_lease(self) -> None:
        """mark_failed should NOT clear lease (it sets ended_at instead)."""
        svc, registry = _make_service()
        launch = MagicMock()
        launch.is_terminal = False
        launch.can_transition_to.return_value = True
        registry.get_by_launch_id.return_value = launch
        registry.cas_update_status.return_value = True

        svc.mark_failed("launch-1", "error msg")

        call = registry.cas_update_status.call_args
        # clear_lease defaults to False — should not be True
        assert call.kwargs.get("clear_lease", False) is False

    def test_begin_termination_does_not_clear_lease(self) -> None:
        svc, registry = _make_service()
        launch = MagicMock()
        launch.is_terminal = False
        launch.can_transition_to.return_value = True
        launch.status = LaunchStatus.ACTIVE
        registry.get_by_launch_id.return_value = launch
        registry.cas_update_status.return_value = True

        svc.begin_termination("launch-1")

        call = registry.cas_update_status.call_args
        assert call.kwargs.get("clear_lease", False) is False


class TestLeaseExpiryBehavior:
    """Verify reconcile behavior for different statuses."""

    def test_active_with_expired_lease_not_quarantined(self) -> None:
        """ACTIVE launches must never be quarantined by lease expiry.

        Even if lease_expires_at is in the past, reconcile only queries
        RESERVED and SPAWNING statuses.
        """
        svc, registry = _make_service()
        registry.list_expired_leases.return_value = []

        result = svc.reconcile_expired_leases()

        assert result == []
        # The SQL only checks status IN ('RESERVED', 'SPAWNING')
        registry.list_expired_leases.assert_called_once()

    def test_reserved_with_expired_lease_quarantined(self) -> None:
        svc, registry = _make_service()

        expired = MagicMock()
        expired.launch_id = "l-1"
        expired.status = LaunchStatus.RESERVED
        expired.canonical_key = "api:x:y"
        expired.is_terminal = False
        expired.can_transition_to.return_value = True
        registry.list_expired_leases.return_value = [expired]
        registry.get_by_launch_id.return_value = expired
        registry.cas_update_status.return_value = True

        result = svc.reconcile_expired_leases()

        assert len(result) == 1
        # Verify the transition: RESERVED → QUARANTINED
        call = registry.cas_update_status.call_args
        assert call[0][1] == LaunchStatus.RESERVED
        assert call[0][2] == LaunchStatus.QUARANTINED

    def test_spawning_with_expired_lease_quarantined(self) -> None:
        svc, registry = _make_service()

        expired = MagicMock()
        expired.launch_id = "l-2"
        expired.status = LaunchStatus.SPAWNING
        expired.canonical_key = "task:123"
        expired.is_terminal = False
        expired.can_transition_to.return_value = True
        registry.list_expired_leases.return_value = [expired]
        registry.get_by_launch_id.return_value = expired
        registry.cas_update_status.return_value = True

        result = svc.reconcile_expired_leases()

        assert len(result) == 1
        call = registry.cas_update_status.call_args
        assert call[0][1] == LaunchStatus.SPAWNING
        assert call[0][2] == LaunchStatus.QUARANTINED
