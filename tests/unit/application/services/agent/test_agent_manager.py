from __future__ import annotations

import time
from pathlib import Path

import pytest

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
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=1)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(1.1)
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
        time.sleep(1)
        manager.stop_health_monitoring()
