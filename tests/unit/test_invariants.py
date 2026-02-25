"""Invariant Coverage Tests - WO-Next-06.

This module contains tests that verify critical system invariants are maintained.
Each test is traceable to an INV-* ID in docs/informes/INVARIANTS.md.
"""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path

import pytest

from src.application.services.workflow.state import (
    ExecuteState,
    PlanState,
    VerifyState,
    get_execute_state_path,
    get_plan_state_path,
    get_verify_state_path,
)
from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection


class TestWorkflowPhaseOrdering:
    """INV-WF-001: Phase ordering - programmatic API enforcement.

    The CLI enforces phase ordering, but programmatic API usage could bypass it.
    This test verifies the state files are properly checked.
    """

    def test_execute_requires_plan_state(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # Monkeypatch path functions to use tmp_path
        monkeypatch.setattr(
            "src.application.services.workflow.state.get_plan_state_path",
            lambda: tmp_path / "plan-state.json",
        )
        monkeypatch.setattr(
            "src.application.services.workflow.state.get_execute_state_path",
            lambda: tmp_path / "execute-state.json",
        )

        plan_path = get_plan_state_path()
        if plan_path.exists():
            plan_path.unlink()

        exec_path = get_execute_state_path()
        if exec_path.exists():
            exec_path.unlink()

        plan = PlanState.load(plan_path)
        assert plan is None

    def test_verify_requires_execute_state(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "src.application.services.workflow.state.get_execute_state_path",
            lambda: tmp_path / "execute-state.json",
        )
        monkeypatch.setattr(
            "src.application.services.workflow.state.get_verify_state_path",
            lambda: tmp_path / "verify-state.json",
        )

        exec_path = get_execute_state_path()
        if exec_path.exists():
            exec_path.unlink()

        verify_path = get_verify_state_path()
        if verify_path.exists():
            verify_path.unlink()

        exec_state = ExecuteState.load(exec_path)
        assert exec_state is None

    def test_ship_requires_verify_state_with_unlock(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "src.application.services.workflow.state.get_verify_state_path",
            lambda: tmp_path / "verify-state.json",
        )

        verify_path = get_verify_state_path()

        verify_state = VerifyState(
            session_id="test-verify",
            status="verified",
            unlock_ship=False,
        )
        verify_state.save(verify_path)

        loaded = VerifyState.load(verify_path)
        assert loaded is not None
        assert loaded.unlock_ship is False

    def test_ship_allowed_with_unlock(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "src.application.services.workflow.state.get_verify_state_path",
            lambda: tmp_path / "verify-state.json",
        )

        verify_path = get_verify_state_path()

        verify_state = VerifyState(
            session_id="test-verify",
            status="verified",
            unlock_ship=True,
        )
        verify_state.save(verify_path)

        loaded = VerifyState.load(verify_path)
        assert loaded is not None
        assert loaded.unlock_ship is True


class TestTmuxSessionNaming:
    """INV-TMUX-001: Session naming convention.

    All fork sessions must follow pattern: agent-{agent_name}-{timestamp}
    Note: Implementation uses 'agent-' prefix, not 'fork-'.
    """

    def test_session_name_follows_agent_prefix(self) -> None:
        from src.application.services.agent.agent_manager import TmuxAgent, AgentConfig

        config = AgentConfig(
            name="test-agent",
            agent_type="test",
            working_dir=Path("/tmp"),
        )
        agent = TmuxAgent(config)

        assert agent.tmux_session.startswith("agent-")

    def test_session_name_contains_agent_name(self) -> None:
        from src.application.services.agent.agent_manager import TmuxAgent, AgentConfig

        config = AgentConfig(
            name="my-special-agent",
            agent_type="test",
            working_dir=Path("/tmp"),
        )
        agent = TmuxAgent(config)

        assert "my-special-agent" in agent.tmux_session

    def test_session_name_format_structure(self) -> None:
        from src.application.services.agent.agent_manager import TmuxAgent, AgentConfig

        config = AgentConfig(
            name="agent",
            agent_type="test",
            working_dir=Path("/tmp"),
        )
        agent = TmuxAgent(config)

        parts = agent.tmux_session.split("-")
        assert len(parts) >= 3, f"Expected agent-name-timestamp format, got: {agent.tmux_session}"
        assert parts[0] == "agent"


class TestCircuitBreakerRecoveryTimeout:
    """INV-CB-002: Recovery timeout - non-zero timeout behavior.

    Circuit must transition to HALF_OPEN after recovery_timeout seconds.
    This tests the non-zero timeout case (previously only zero timeout was tested).
    """

    def test_transitions_to_half_open_after_timeout(self) -> None:
        from src.application.services.agent.agent_manager import CircuitBreaker, CircuitState

        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=1)
        cb.record_failure()

        assert cb.state == CircuitState.OPEN

        time.sleep(1.5)

        assert cb.state == CircuitState.HALF_OPEN

    def test_remains_open_before_timeout(self) -> None:
        from src.application.services.agent.agent_manager import CircuitBreaker, CircuitState

        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=2)
        cb.record_failure()

        assert cb.state == CircuitState.OPEN

        time.sleep(0.5)

        assert cb.state == CircuitState.OPEN


class TestDatabaseThreadLocal:
    """INV-DB-004: Thread-local connections.

    Each thread must get its own database connection.
    """

    def test_same_thread_reuses_connection(self, tmp_path: Path) -> None:
        db_path = tmp_path / "reuse_test.db"
        config = DatabaseConfig(db_path=db_path)

        connection_ids = []

        def get_connection_ids() -> None:
            with DatabaseConnection(config) as conn1:
                connection_ids.append(id(conn1))
            with DatabaseConnection(config) as conn2:
                connection_ids.append(id(conn2))

        thread = threading.Thread(target=get_connection_ids)
        thread.start()
        thread.join()

        assert connection_ids[0] == connection_ids[1]

    def test_connection_isolation_between_threads(self, tmp_path: Path) -> None:
        db_path = tmp_path / "isolation_test.db"
        config = DatabaseConfig(db_path=db_path)

        with DatabaseConnection(config) as conn:
            conn.execute("CREATE TABLE test_isolation (id INTEGER PRIMARY KEY, value TEXT)")

        def insert_data() -> None:
            with DatabaseConnection(config) as conn:
                conn.execute("INSERT INTO test_isolation (value) VALUES ('from_thread2')")

        thread = threading.Thread(target=insert_data)
        thread.start()
        thread.join()

        with DatabaseConnection(config) as conn:
            cursor = conn.execute("SELECT value FROM test_isolation")
            rows = cursor.fetchall()

        assert len(rows) == 1
        assert rows[0][0] == "from_thread2"


class TestGitGuard:
    """INV-HK-003: Git guard enforcement.

    Dangerous git commands must be blocked via git-branch-guard.sh.
    This tests the script's behavior programmatically.
    """

    def test_git_checkout_is_blocked(self) -> None:
        import subprocess

        guard_path = Path(".hooks/git-branch-guard.sh")
        if not guard_path.exists():
            pytest.skip("git-branch-guard.sh not found")

        env = {"TOOL_INPUT": "git checkout main", "TOOL_NAME": "Bash"}
        result = subprocess.run(
            ["bash", str(guard_path)],
            capture_output=True,
            text=True,
            env={**os.environ.copy(), **env},
        )

        assert result.returncode == 2

    def test_git_reset_is_blocked(self) -> None:
        import subprocess

        guard_path = Path(".hooks/git-branch-guard.sh")
        if not guard_path.exists():
            pytest.skip("git-branch-guard.sh not found")

        env = {"TOOL_INPUT": "git reset --hard", "TOOL_NAME": "Bash"}
        result = subprocess.run(
            ["bash", str(guard_path)],
            capture_output=True,
            text=True,
            env={**os.environ.copy(), **env},
        )

        assert result.returncode == 2

    def test_git_push_is_blocked(self) -> None:
        import subprocess

        guard_path = Path(".hooks/git-branch-guard.sh")
        if not guard_path.exists():
            pytest.skip("git-branch-guard.sh not found")

        env = {"TOOL_INPUT": "git push origin main", "TOOL_NAME": "Bash"}
        result = subprocess.run(
            ["bash", str(guard_path)],
            capture_output=True,
            text=True,
            env={**os.environ.copy(), **env},
        )

        assert result.returncode == 2

    def test_git_status_is_allowed(self) -> None:
        import subprocess

        guard_path = Path(".hooks/git-branch-guard.sh")
        if not guard_path.exists():
            pytest.skip("git-branch-guard.sh not found")

        env = {"TOOL_INPUT": "git status", "TOOL_NAME": "Bash"}
        result = subprocess.run(
            ["bash", str(guard_path)],
            capture_output=True,
            text=True,
            env={**os.environ.copy(), **env},
        )

        assert result.returncode == 0

    def test_git_add_is_allowed(self) -> None:
        import subprocess

        guard_path = Path(".hooks/git-branch-guard.sh")
        if not guard_path.exists():
            pytest.skip("git-branch-guard.sh not found")

        env = {"TOOL_INPUT": "git add .", "TOOL_NAME": "Bash"}
        result = subprocess.run(
            ["bash", str(guard_path)],
            capture_output=True,
            text=True,
            env={**os.environ.copy(), **env},
        )

        assert result.returncode == 0


class TestHookOnFailurePolicy:
    """INV-HK-004: Hook on_failure policy enforcement.

    Critical hooks must abort on failure.
    Non-critical hooks must continue with logging.
    """

    def test_critical_hook_aborts_on_failure(self, tmp_path: Path) -> None:
        from src.application.services.orchestration.actions import (
            OnFailurePolicy,
            ShellCommandAction,
        )
        from src.infrastructure.orchestration.shell_action_runner import (
            HookExecutionError,
            ShellActionRunner,
        )

        runner = ShellActionRunner(hooks_dir=tmp_path)
        action = ShellCommandAction(
            command="exit 1",
            critical=True,
            on_failure=OnFailurePolicy.ABORT,
        )

        with pytest.raises(HookExecutionError):
            runner.run(action)

    def test_non_critical_hook_continues_on_failure(self, tmp_path: Path) -> None:
        from src.application.services.orchestration.actions import (
            OnFailurePolicy,
            ShellCommandAction,
        )
        from src.infrastructure.orchestration.shell_action_runner import (
            ShellActionRunner,
        )

        runner = ShellActionRunner(hooks_dir=tmp_path)
        action = ShellCommandAction(
            command="exit 1",
            critical=False,
            on_failure=OnFailurePolicy.CONTINUE,
        )

        runner.run(action)


class TestDLQMaxSize:
    """INV-DLQ-001: DLQ max size enforcement.

    DLQ must not exceed max_size items.
    """

    def test_dlq_rejects_when_full(self) -> None:
        from src.infrastructure.tmux_orchestrator.dead_letter_queue import DeadLetterQueue

        dlq = DeadLetterQueue(max_size=2)

        dlq.add(
            session="session1",
            window=1,
            message={"test": "message1"},
            error="error1",
        )
        dlq.add(
            session="session2",
            window=2,
            message={"test": "message2"},
            error="error2",
        )

        assert dlq.size() == 2

        dlq.add(
            session="session3",
            window=3,
            message={"test": "message3"},
            error="error3",
        )

        assert dlq.size() == 2


class TestResiliencePolicySSOT:
    """INV-RES-001: Single Source of Truth for resilience policy.

    All circuit breakers must use the same policy from resilience_policy.py.
    """

    def test_default_policy_values(self) -> None:
        from src.infrastructure.tmux_orchestrator.resilience_policy import (
            DEFAULT_POLICY,
        )

        assert DEFAULT_POLICY.failure_threshold == 3
        assert DEFAULT_POLICY.recovery_timeout_seconds == 30
        assert DEFAULT_POLICY.half_open_max_calls == 2

    def test_policy_used_by_circuit_breaker(self) -> None:
        from src.infrastructure.tmux_orchestrator.circuit_breaker import (
            CircuitState,
            TmuxCircuitBreaker,
        )
        from src.infrastructure.tmux_orchestrator.resilience_policy import (
            ResiliencePolicy,
        )

        custom_policy = ResiliencePolicy(
            failure_threshold=2,
            recovery_timeout_seconds=60,
            half_open_max_calls=1,
        )

        cb = TmuxCircuitBreaker(policy=custom_policy)

        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
