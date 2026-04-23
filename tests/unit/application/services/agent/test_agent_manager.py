from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from src.application.services.agent.agent_manager import (
    AgentConfig,
    AgentManager,
    AgentStatus,
    CircuitBreaker,
    CircuitState,
    TmuxAgent,
)


class TestCircuitBreaker:
    def test_initial_state_closed(self) -> None:
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED

    def test_records_success(self) -> None:
        cb = CircuitBreaker()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_opens_after_threshold(self) -> None:
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_half_open_after_recovery_timeout(self) -> None:
        fake_time = [100.0]

        def clock() -> float:
            return fake_time[0]

        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=1, _clock=clock)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        fake_time[0] += 1.1  # advance past recovery_timeout
        assert cb.state == CircuitState.HALF_OPEN

    def test_can_execute_closed(self) -> None:
        cb = CircuitBreaker()
        assert cb.can_execute() is True

    def test_cannot_execute_open(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
        cb.record_failure()
        assert cb.can_execute() is False


class TestAgentConfig:
    def test_defaults(self) -> None:
        config = AgentConfig(
            name="test",
            agent_type="test",
            working_dir=Path("/tmp"),
        )
        assert config.timeout_seconds == 300
        assert config.max_retries == 3
        assert config.tmux_session is None


class TestTmuxAgent:
    def test_creates_session_name(self) -> None:
        config = AgentConfig(
            name="test-agent",
            agent_type="test",
            working_dir=Path("/tmp"),
        )
        agent = TmuxAgent(config)
        assert agent.tmux_session.startswith("agent-test-agent-")

    def test_custom_session_name(self) -> None:
        config = AgentConfig(
            name="test-agent",
            agent_type="test",
            working_dir=Path("/tmp"),
            tmux_session="custom-session",
        )
        agent = TmuxAgent(config)
        assert agent.tmux_session == "custom-session"


class TestAgentManager:
    def test_spawn_and_terminate(self) -> None:
        manager = AgentManager()
        config = AgentConfig(
            name="test-agent",
            agent_type="test",
            working_dir=Path("/tmp"),
            tmux_session="test-spawn-session",
        )
        agent = manager.spawn_agent(config)
        assert agent is not None
        assert agent.name == "test-agent"
        assert agent.status == AgentStatus.HEALTHY

        result = manager.terminate_agent("test-agent")
        assert result is True

    def test_duplicate_agent_fails(self) -> None:
        import subprocess

        subprocess.run(["tmux", "kill-session", "-t", "test-dup-session"], capture_output=True)
        manager = AgentManager()
        config = AgentConfig(
            name="test-agent-2",
            agent_type="test",
            working_dir=Path("/tmp"),
            tmux_session="test-dup-session",
        )
        agent1 = manager.spawn_agent(config)
        agent2 = manager.spawn_agent(config)
        assert agent1 is not None
        assert agent2 is None
        if agent1:
            manager.terminate_agent("test-agent-2")

    def test_list_agents(self) -> None:
        manager = AgentManager()
        config = AgentConfig(
            name="test-list-agent",
            agent_type="test",
            working_dir=Path("/tmp"),
            tmux_session="test-list-session",
        )
        manager.spawn_agent(config)
        agents = manager.list_agents()
        assert len(agents) == 1
        manager.terminate_agent("test-list-agent")

    def test_health_check(self) -> None:
        manager = AgentManager()
        manager.start_health_monitoring()
        assert manager._health_thread is not None
        assert manager._health_thread.is_alive()
        manager.stop_health_monitoring()


class TestReconcileSessions:
    @patch("subprocess.run")
    def test_reconcile_no_sessions(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        manager = AgentManager()
        result = manager.reconcile_sessions()
        assert result.status == "ok"
        assert len(result.orphaned_sessions) == 0
        assert len(result.missing_sessions) == 0

    @patch("subprocess.run")
    def test_reconcile_detects_orphans(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="fork-orphan-123\nfork-agent-456\n",
        )
        manager = AgentManager()
        result = manager.reconcile_sessions()
        assert result.status == "warning"
        assert "fork-orphan-123" in result.orphaned_sessions
        assert "fork-agent-456" in result.orphaned_sessions

    @patch("subprocess.run")
    def test_reconcile_ignores_non_fork_sessions(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="fork-valid-123\nother-session\n",
        )
        manager = AgentManager()
        result = manager.reconcile_sessions()
        assert "other-session" not in result.runtime_sessions
        assert "fork-valid-123" in result.runtime_sessions

    @patch("subprocess.run")
    def test_reconcile_detects_registered_agent(self, mock_run: MagicMock) -> None:
        # First call: reconcile returns the session we registered
        mock_run.return_value = MagicMock(returncode=0, stdout="test-reconcile-agent\n")
        import subprocess

        subprocess.run(
            ["tmux", "kill-session", "-t", "test-reconcile-agent"],
            capture_output=True,
        )
        manager = AgentManager()

        # Manually register a mock agent to test reconcile
        mock_agent = MagicMock(spec=TmuxAgent)
        mock_agent.tmux_session = "test-reconcile-agent"
        manager._agents["test-reconcile"] = mock_agent

        # Now reconcile - should find the registered session
        result = manager.reconcile_sessions()
        assert "test-reconcile-agent" in result.registered_agents


class TestCleanupOrphans:
    @patch("subprocess.run")
    def test_cleanup_dry_run_reports_orphans(self, mock_run: MagicMock) -> None:
        # First call: reconcile finds orphan
        # Second call: cleanup (dry run, doesn't kill)
        mock_run.return_value = MagicMock(returncode=0, stdout="fork-orphan-999\n")
        manager = AgentManager()
        result = manager.cleanup_orphans(dry_run=True)
        assert result.dry_run is True
        assert len(result.cleaned_sessions) == 1
        assert "fork-orphan-999" in result.cleaned_sessions

    @patch("subprocess.run")
    def test_cleanup_skips_registered_agents(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        import subprocess

        subprocess.run(
            ["tmux", "kill-session", "-t", "test-cleanup-agent"],
            capture_output=True,
        )
        manager = AgentManager()
        config = AgentConfig(
            name="test-cleanup",
            agent_type="test",
            working_dir=Path("/tmp"),
            tmux_session="test-cleanup-agent",
        )
        manager.spawn_agent(config)

        result = manager.cleanup_orphans(dry_run=True)
        # Should not report the registered agent as orphan
        assert "test-cleanup-agent" not in result.cleaned_sessions

        manager.terminate_agent("test-cleanup")


class TestGetHealthStatus:
    @patch("subprocess.run")
    def test_health_status_returns_correct_structure(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="fork-session-1\nfork-session-2\n",
        )
        manager = AgentManager()
        status = manager.get_health_status()
        assert "orphan_sessions_count" in status
        assert "reconcile_status" in status
        assert "registered_count" in status
        assert "runtime_sessions_count" in status


class TestListRuntimeSessions:
    @patch("subprocess.run")
    def test_list_runtime_sessions_filters_prefix(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="fork-agent-1\nagent-test-2\nother-session\n",
        )
        manager = AgentManager()
        sessions = manager.list_runtime_sessions()
        assert "fork-agent-1" in sessions
        assert "agent-test-2" in sessions
        assert "other-session" not in sessions

    @patch("subprocess.run")
    def test_list_runtime_sessions_handles_empty(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        manager = AgentManager()
        sessions = manager.list_runtime_sessions()
        assert sessions == set()
