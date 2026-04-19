"""Tests for HIGH issues #5 (idempotent spawn) and #6 (Agent RLock)."""
from __future__ import annotations

import subprocess
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.application.services.agent.agent_manager import (
    Agent,
    AgentConfig,
    AgentManager,
    TmuxAgent,
)


class TestTmuxAgentIdempotentSpawn:
    """HIGH #5: TmuxAgent.spawn() SHALL use -A flag for idempotent creation."""

    @patch("subprocess.run")
    def test_spawn_uses_a_flag(self, mock_run: MagicMock) -> None:
        """spawn() SHALL include -A in tmux new-session command."""
        mock_run.return_value = MagicMock(returncode=0)
        config = AgentConfig(
            name="idem-agent",
            agent_type="test",
            working_dir=Path("/tmp"),
            tmux_session="idem-session",
        )
        agent = TmuxAgent(config)
        agent.spawn()

        cmd = mock_run.call_args_list[0][0][0]
        assert "-A" in cmd, f"Expected -A flag in tmux new-session, got: {cmd}"
        assert "new-session" in cmd
        assert "idem-session" in cmd

    @patch("subprocess.run")
    def test_spawn_idempotent_on_existing_session(self, mock_run: MagicMock) -> None:
        """With -A flag, spawn succeeds even if session already exists."""
        mock_run.return_value = MagicMock(returncode=0)
        config = AgentConfig(
            name="idem-agent-2",
            agent_type="test",
            working_dir=Path("/tmp"),
            tmux_session="existing-session",
        )
        agent = TmuxAgent(config)
        result = agent.spawn()
        assert result is True

    @patch("subprocess.run")
    def test_a_flag_before_d_flag(self, mock_run: MagicMock) -> None:
        """-A flag SHALL appear before -d flag in the command."""
        mock_run.return_value = MagicMock(returncode=0)
        config = AgentConfig(
            name="flag-order",
            agent_type="test",
            working_dir=Path("/tmp"),
            tmux_session="flag-session",
        )
        agent = TmuxAgent(config)
        agent.spawn()

        cmd = mock_run.call_args_list[0][0][0]
        a_idx = cmd.index("-A")
        d_idx = cmd.index("-d")
        assert a_idx < d_idx, f"-A (idx={a_idx}) should come before -d (idx={d_idx})"


class TestAgentRLock:
    """HIGH #6: Agent SHALL use RLock for thread safety."""

    def test_agent_lock_is_rlock(self) -> None:
        """Agent._lock SHALL be RLock, not Lock."""
        config = AgentConfig(
            name="rlock-test",
            agent_type="test",
            working_dir=Path("/tmp"),
        )
        agent = TmuxAgent(config)
        assert isinstance(agent._lock, type(threading.RLock()))

    def test_agent_rlock_is_reentrant(self) -> None:
        """RLock SHALL allow reentrant acquisition without deadlock."""
        config = AgentConfig(
            name="reentrant-test",
            agent_type="test",
            working_dir=Path("/tmp"),
        )
        agent = TmuxAgent(config)
        with agent._lock:
            with agent._lock:
                pass  # Should not deadlock


class TestAgentManagerThreadSafeReads:
    """HIGH #6: AgentManager read methods SHALL hold lock."""

    def test_get_agent_holds_lock(self) -> None:
        """get_agent() SHALL acquire _lock."""
        manager = AgentManager()
        # Verify it doesn't raise and returns None
        assert manager.get_agent("nonexistent") is None

    def test_list_agents_holds_lock(self) -> None:
        """list_agents() SHALL acquire _lock."""
        manager = AgentManager()
        agents = manager.list_agents()
        assert isinstance(agents, list)

    def test_get_healthy_agents_holds_lock(self) -> None:
        """get_healthy_agents() SHALL acquire _lock."""
        manager = AgentManager()
        healthy = manager.get_healthy_agents()
        assert isinstance(healthy, list)

    @patch("subprocess.run")
    def test_concurrent_reads_no_error(self, mock_run: MagicMock) -> None:
        """Concurrent reads on AgentManager SHALL not raise."""
        import concurrent.futures

        mock_run.return_value = MagicMock(returncode=0)
        manager = AgentManager()
        config = AgentConfig(
            name="concurrent-test",
            agent_type="test",
            working_dir=Path("/tmp"),
            tmux_session="concurrent-session",
        )
        # We need to mock spawn since tmux might not be available
        with patch.object(TmuxAgent, "spawn", return_value=True):
            manager.spawn_agent(config)

        errors: list[Exception] = []

        def read_list() -> None:
            try:
                for _ in range(50):
                    manager.list_agents()
                    manager.get_agent("concurrent-test")
                    manager.get_healthy_agents()
            except Exception as e:
                errors.append(e)

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(read_list) for _ in range(4)]
            concurrent.futures.wait(futures)

        assert errors == [], f"Concurrent read errors: {errors}"
        manager.terminate_agent("concurrent-test")
