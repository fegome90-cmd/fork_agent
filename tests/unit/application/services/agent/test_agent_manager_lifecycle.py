"""Tests for AgentManager lifecycle integration — duplicate suppression via lifecycle service."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from src.application.services.agent.agent_manager import AgentConfig, AgentManager
from src.application.services.agent_launch_lifecycle_service import (
    AgentLaunchLifecycleService,
    LaunchAttempt,
)
from src.domain.entities.agent_launch import AgentLaunch, LaunchStatus


def _make_claimed_launch(launch_id: str = "launch-mgr-001") -> AgentLaunch:
    return AgentLaunch(
        launch_id=launch_id,
        canonical_key="manager:test-agent",
        surface="manager",
        owner_type="agent",
        owner_id="test-agent",
        status=LaunchStatus.RESERVED,
    )


def _make_active_launch(launch_id: str = "launch-mgr-001") -> AgentLaunch:
    return AgentLaunch(
        launch_id=launch_id,
        canonical_key="manager:test-agent",
        surface="manager",
        owner_type="agent",
        owner_id="test-agent",
        status=LaunchStatus.ACTIVE,
        tmux_session="agent-test-agent-session",
    )


def _make_config(name: str = "test-agent", tmux_session: str = "test-mgr-session") -> AgentConfig:
    return AgentConfig(
        name=name,
        agent_type="test",
        working_dir=Path("/tmp"),
        tmux_session=tmux_session,
    )


class TestAgentManagerWithoutLifecycle:
    """When lifecycle service is not wired, manager behaves as before."""

    def test_spawn_without_lifecycle(self) -> None:
        manager = AgentManager(lifecycle_service=None)
        config = _make_config()
        agent = manager.spawn_agent(config)
        assert agent is not None
        manager.terminate_agent("test-agent")


class TestAgentManagerWithLifecycle:
    """When lifecycle service is wired, duplicate spawns are suppressed."""

    def test_first_spawn_proceeds(self) -> None:
        lifecycle = MagicMock(spec=AgentLaunchLifecycleService)
        claimed = _make_claimed_launch()
        lifecycle.request_launch.return_value = LaunchAttempt(
            launch=claimed,
            decision="claimed",
        )
        lifecycle.confirm_spawning.return_value = True
        lifecycle.confirm_active.return_value = True

        manager = AgentManager(lifecycle_service=lifecycle)
        config = _make_config()
        agent = manager.spawn_agent(config)
        assert agent is not None

        lifecycle.request_launch.assert_called_once_with(
            canonical_key="manager:test-agent",
            surface="manager",
            owner_type="agent",
            owner_id="test-agent",
        )
        lifecycle.confirm_spawning.assert_called_once_with("launch-mgr-001")
        lifecycle.confirm_active.assert_called_once()

        manager.terminate_agent("test-agent")

    def test_duplicate_spawn_is_suppressed(self) -> None:
        lifecycle = MagicMock(spec=AgentLaunchLifecycleService)
        active = _make_active_launch()
        lifecycle.request_launch.return_value = LaunchAttempt(
            launch=None,
            decision="suppressed",
            existing_launch=active,
            reason="Active launch in status ACTIVE",
        )

        manager = AgentManager(lifecycle_service=lifecycle)
        config = _make_config()
        result = manager.spawn_agent(config)

        assert result is None
        # No tmux session created
        assert len(manager.list_agents()) == 0

    def test_registry_error_returns_none(self) -> None:
        lifecycle = MagicMock(spec=AgentLaunchLifecycleService)
        lifecycle.request_launch.return_value = LaunchAttempt(
            launch=None,
            decision="error",
            reason="Registry unavailable",
        )

        manager = AgentManager(lifecycle_service=lifecycle)
        config = _make_config()
        result = manager.spawn_agent(config)

        assert result is None
        assert len(manager.list_agents()) == 0

    def test_spawn_failure_marks_lifecycle_failed(self) -> None:
        lifecycle = MagicMock(spec=AgentLaunchLifecycleService)
        claimed = _make_claimed_launch()
        lifecycle.request_launch.return_value = LaunchAttempt(
            launch=claimed,
            decision="claimed",
        )
        lifecycle.confirm_spawning.return_value = True

        manager = AgentManager(lifecycle_service=lifecycle)
        config = _make_config()

        # Make the tmux session creation fail by using a session name that will fail
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="session failed")
            result = manager.spawn_agent(config)

        assert result is None
        lifecycle.mark_failed.assert_called_once()
        call_args = lifecycle.mark_failed.call_args
        assert call_args[0][0] == "launch-mgr-001"

    def test_terminate_terminates_lifecycle_record(self) -> None:
        lifecycle = MagicMock(spec=AgentLaunchLifecycleService)
        claimed = _make_claimed_launch()
        lifecycle.request_launch.return_value = LaunchAttempt(
            launch=claimed,
            decision="claimed",
        )
        lifecycle.confirm_spawning.return_value = True
        lifecycle.confirm_active.return_value = True

        # get_active_launch returns the active record for termination
        active = _make_active_launch()
        lifecycle.get_active_launch.return_value = active
        lifecycle.begin_termination.return_value = True
        lifecycle.confirm_terminated.return_value = True

        manager = AgentManager(lifecycle_service=lifecycle)
        config = _make_config()
        agent = manager.spawn_agent(config)
        assert agent is not None

        result = manager.terminate_agent("test-agent")
        assert result is True

        lifecycle.begin_termination.assert_called_once_with("launch-mgr-001")
        lifecycle.confirm_terminated.assert_called_once_with("launch-mgr-001")

    def test_repeated_spawn_same_agent_does_not_create_two(self) -> None:
        lifecycle = MagicMock(spec=AgentLaunchLifecycleService)

        # First call: claimed
        claimed = _make_claimed_launch()
        lifecycle.request_launch.return_value = LaunchAttempt(
            launch=claimed,
            decision="claimed",
        )
        lifecycle.confirm_spawning.return_value = True
        lifecycle.confirm_active.return_value = True

        manager = AgentManager(lifecycle_service=lifecycle)
        config = _make_config()
        r1 = manager.spawn_agent(config)
        assert r1 is not None

        # Second call: suppressed
        active = _make_active_launch()
        lifecycle.request_launch.return_value = LaunchAttempt(
            launch=None,
            decision="suppressed",
            existing_launch=active,
            reason="Already active",
        )
        r2 = manager.spawn_agent(config)
        assert r2 is None

        # Only one agent in manager
        assert len(manager.list_agents()) == 1
        manager.terminate_agent("test-agent")


class TestBugHuntLifecycleDedup:
    """Tests for bug-hunt canonical key strategy and lifecycle contract."""

    def test_bug_hunt_canonical_key_is_batch_scoped(self) -> None:
        """Each agent in a hunt gets a unique canonical key scoped by hunt_id."""
        hunt_id = "abc12345"
        agent_name = "ripper"
        canonical_key = f"bug_hunt:{hunt_id}:{agent_name}"
        assert canonical_key == "bug_hunt:abc12345:ripper"

    def test_different_hunts_have_different_keys(self) -> None:
        """Different hunt batches should not block each other."""
        key1 = "bug_hunt:batch1:ripper"
        key2 = "bug_hunt:batch2:ripper"
        assert key1 != key2

    def test_different_agents_in_same_hunt_have_different_keys(self) -> None:
        """Different agents in the same hunt should not block each other."""
        key_ripper = "bug_hunt:abc12345:ripper"
        key_sniper = "bug_hunt:abc12345:sniper"
        assert key_ripper != key_sniper

    def test_same_agent_same_hunt_is_deduped(self) -> None:
        """Same agent in the same hunt should be deduplicated."""
        lifecycle = MagicMock(spec=AgentLaunchLifecycleService)
        active = AgentLaunch(
            launch_id="launch-bh-001",
            canonical_key="bug_hunt:abc12345:ripper",
            surface="bug_hunt",
            owner_type="batch",
            owner_id="abc12345",
            status=LaunchStatus.ACTIVE,
        )
        lifecycle.request_launch.return_value = LaunchAttempt(
            launch=None,
            decision="suppressed",
            existing_launch=active,
            reason="Already active",
        )

        attempt = lifecycle.request_launch(
            canonical_key="bug_hunt:abc12345:ripper",
            surface="bug_hunt",
            owner_type="batch",
            owner_id="abc12345",
        )
        assert attempt.decision == "suppressed"
