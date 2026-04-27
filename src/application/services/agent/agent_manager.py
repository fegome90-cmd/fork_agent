from __future__ import annotations

import logging
import re
import subprocess
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from src.infrastructure.tmux_orchestrator.circuit_breaker import (
    CircuitState,
    TmuxCircuitBreaker,
)

if TYPE_CHECKING:
    from src.application.services.agent_launch_lifecycle_service import (
        AgentLaunchLifecycleService,
    )

# Alias for backward compatibility
CircuitBreaker = TmuxCircuitBreaker

# Re-export for backward compatibility
__all__ = [
    "AgentManager",
    "AgentStatus",
    "AgentConfig",
    "AgentMetrics",
    "ReconcileResult",
    "CleanupResult",
    "CircuitBreaker",
    "CircuitState",
    "get_agent_manager",
]

logger = logging.getLogger(__name__)

# Security: patterns for sanitizing tmux send-keys input (mirrors tmux_orchestrator)
_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")

# Session prefix for fork_agent managed sessions
FORK_SESSION_PREFIX = "fork-"
AGENT_SESSION_PREFIX = "agent-"


class AgentStatus(Enum):
    PENDING = "pending"
    STARTING = "starting"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    TERMINATING = "terminating"
    TERMINATED = "terminated"
    FAILED = "failed"


@dataclass
class AgentConfig:
    name: str
    agent_type: str
    working_dir: Path
    tmux_session: str | None = None
    timeout_seconds: int = 300
    max_retries: int = 3
    environment: dict[str, str] = field(default_factory=dict)
    on_exit: Callable[[int], None] | None = None
    # Resilience config
    session_timeout: int = 10  # seconds to wait for session ready


@dataclass
class AgentMetrics:
    start_time: float = 0
    end_time: float = 0
    restart_count: int = 0
    error_count: int = 0
    last_heartbeat: float = 0
    cpu_percent: float = 0
    memory_mb: float = 0


@dataclass(frozen=True)
class ReconcileResult:
    """Result of a reconcile operation."""

    registered_agents: set[str]
    runtime_sessions: set[str]
    orphaned_sessions: set[str]
    missing_sessions: set[str]
    status: str  # "ok", "warning", "error"


@dataclass
class CleanupResult:
    """Result of a cleanup operation."""

    cleaned_sessions: list[str]
    failed_sessions: list[str]
    dry_run: bool


class Agent(ABC):
    def __init__(self, config: AgentConfig) -> None:
        self._config = config
        self._status = AgentStatus.PENDING
        self._metrics = AgentMetrics()
        self._circuit_breaker = CircuitBreaker()
        self._lock = threading.RLock()

    @property
    def config(self) -> AgentConfig:
        return self._config

    @property
    def status(self) -> AgentStatus:
        return self._status

    @property
    def metrics(self) -> AgentMetrics:
        return self._metrics

    @property
    def name(self) -> str:
        return self._config.name

    def is_healthy(self) -> bool:
        return self._status == AgentStatus.HEALTHY

    def can_execute(self) -> bool:
        return self._circuit_breaker.can_execute()

    @abstractmethod
    def spawn(self) -> bool: ...

    @abstractmethod
    def terminate(self) -> bool: ...

    @abstractmethod
    def get_pid(self) -> int | None: ...

    @abstractmethod
    def send_input(self, message: str) -> bool: ...

    def _update_status(self, status: AgentStatus) -> None:
        with self._lock:
            self._status = status
            logger.info(f"Agent {self._config.name} status: {status.value}")

    def _record_failure(self) -> None:
        self._circuit_breaker.record_failure()
        self._metrics.error_count += 1

    def _record_success(self) -> None:
        self._circuit_breaker.record_success()


class TmuxAgent(Agent):
    def __init__(self, config: AgentConfig) -> None:
        super().__init__(config)
        self._process: subprocess.Popen[str] | None = None
        self._tmux_session = config.tmux_session or f"agent-{config.name}-{int(time.time())}"

    @property
    def tmux_session(self) -> str:
        return self._tmux_session

    def spawn(self, validate: bool = True) -> bool:
        """Spawn the agent in a tmux session.

        Args:
            validate: If True, wait for session to be ready after creation.

        Returns:
            True if spawn succeeded, False otherwise.
        """
        try:
            self._update_status(AgentStatus.STARTING)
            self._metrics.start_time = time.time()

            result = subprocess.run(
                [
                    "tmux",
                    "new-session",
                    "-A",
                    "-d",
                    "-s",
                    self._tmux_session,
                    "-c",
                    str(self._config.working_dir),
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                logger.error(f"Failed to create tmux session: {result.stderr}")
                self._update_status(AgentStatus.FAILED)
                self._record_failure()
                return False

            # Validate session is ready
            if validate and not self._wait_for_session(timeout=self._config.session_timeout):
                logger.error(
                    f"Session {self._tmux_session} not ready after {self._config.session_timeout}s"
                )
                self._safe_kill(self._tmux_session)
                self._update_status(AgentStatus.FAILED)
                self._record_failure()
                return False

            self._update_status(AgentStatus.HEALTHY)
            self._metrics.last_heartbeat = time.time()
            self._record_success()
            logger.info(f"Agent {self._config.name} spawned in tmux session {self._tmux_session}")
            return True

        except Exception:
            logger.exception(f"Failed to spawn agent {self._config.name}")
            self._update_status(AgentStatus.FAILED)
            self._record_failure()
            return False

    def _wait_for_session(self, timeout: int = 10) -> bool:
        """Wait for tmux session to be fully ready."""
        start = time.time()
        while time.time() - start < timeout:
            result = subprocess.run(
                ["tmux", "has-session", "-t", self._tmux_session],
                capture_output=True,
                timeout=2,
            )
            if result.returncode == 0:
                return True
            time.sleep(0.5)
        return False

    def _safe_kill(self, session_name: str) -> None:
        """Safely kill a session, ignoring errors."""
        try:
            subprocess.run(
                ["tmux", "kill-session", "-t", session_name],
                capture_output=True,
                timeout=5,
            )
        except Exception as e:
            logger.warning(f"Failed to kill session {session_name}: {e}")

    def terminate(self) -> bool:
        try:
            self._update_status(AgentStatus.TERMINATING)

            subprocess.run(
                ["tmux", "kill-session", "-t", self._tmux_session],
                capture_output=True,
                timeout=10,
            )

            self._metrics.end_time = time.time()
            self._update_status(AgentStatus.TERMINATED)
            logger.info(f"Agent {self._config.name} terminated")
            return True

        except Exception:
            logger.exception(f"Failed to terminate agent {self._config.name}")
            self._update_status(AgentStatus.FAILED)
            return False

    def get_pid(self) -> int | None:
        try:
            result = subprocess.run(
                ["tmux", "list-panes", "-t", self._tmux_session, "-F", "#{pane_pid}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return int(result.stdout.strip().split("\n")[0])
        except Exception as e:
            logger.warning(f"Failed to get PID for {self._tmux_session}: {e}")
        return None

    def send_input(self, message: str) -> bool:
        try:
            # Sanitize to prevent prompt injection via newlines or control chars
            sanitized = _ANSI_ESCAPE.sub("", message)
            sanitized = _CONTROL_CHARS.sub("", sanitized)
            sanitized = sanitized.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
            sanitized = sanitized.strip()
            if not sanitized:
                logger.warning(
                    "send_input blocked: empty after sanitization",
                    extra={"agent": self._config.name, "reason": "empty_after_sanitize"},
                )
                return False
            result = subprocess.run(
                ["tmux", "send-keys", "-t", self._tmux_session, f"{sanitized}", "Enter"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to send input to agent {self._config.name}: {e}")
            return False


class AgentManager:
    def __init__(
        self,
        lifecycle_service: AgentLaunchLifecycleService | None = None,
    ) -> None:
        self._agents: dict[str, Agent] = {}
        self._lock = threading.RLock()
        self._health_check_interval = 30
        self._running = False
        self._health_thread: threading.Thread | None = None
        self._lifecycle = lifecycle_service

    def spawn_agent(self, config: AgentConfig) -> Agent | None:
        with self._lock:
            if config.name in self._agents:
                logger.warning(f"Agent {config.name} already exists")
                return None

            # Claim canonical launch slot via lifecycle service (if wired)
            from src.domain.services.canonical_key import build_manager_key

            canonical_key = build_manager_key(config.name)
            lifecycle_launch_id: str | None = None
            if self._lifecycle is not None:
                attempt = self._lifecycle.request_launch(
                    canonical_key=canonical_key,
                    surface="manager",
                    owner_type="agent",
                    owner_id=config.name,
                )
                if attempt.decision == "suppressed":
                    logger.info(
                        "Manager spawn suppressed for agent %s: %s",
                        config.name,
                        attempt.reason or "already active",
                    )
                    return None
                if attempt.decision == "error":
                    logger.error(
                        "Lifecycle registry error for agent %s: %s",
                        config.name,
                        attempt.reason,
                    )
                    return None
                if attempt.launch is not None:
                    lifecycle_launch_id = attempt.launch.launch_id

            # Currently only TmuxAgent is supported
            agent = TmuxAgent(config)

            # Notify lifecycle that spawn is starting
            if lifecycle_launch_id is not None and self._lifecycle is not None:
                ok = self._lifecycle.confirm_spawning(lifecycle_launch_id)
                if not ok:
                    logger.warning(
                        "CAS failed for launch %s during spawning — split-brain risk",
                        lifecycle_launch_id,
                    )

            if agent.spawn():
                self._agents[config.name] = agent

                # Confirm active in lifecycle registry
                if lifecycle_launch_id is not None and self._lifecycle is not None:
                    ok = self._lifecycle.confirm_active(
                        lifecycle_launch_id,
                        backend="tmux",
                        termination_handle_type="tmux-session",
                        termination_handle_value=agent.tmux_session,
                        tmux_session=agent.tmux_session,
                    )
                    if not ok:
                        logger.warning(
                            "CAS failed for launch %s during confirm_active — split-brain risk",
                            lifecycle_launch_id,
                        )
                return agent

            # Spawn failed — mark lifecycle record as failed
            if lifecycle_launch_id is not None and self._lifecycle is not None:
                self._lifecycle.mark_failed(lifecycle_launch_id, "tmux spawn failed")
            return None

    def get_agent(self, name: str) -> Agent | None:
        return self._agents.get(name)

    def terminate_agent(self, name: str) -> bool:
        with self._lock:
            agent = self._agents.get(name)
            if agent is None:
                return False

            # Begin lifecycle termination
            if self._lifecycle is not None:
                from src.domain.services.canonical_key import build_manager_key

                canonical_key = build_manager_key(name)
                active = self._lifecycle.get_active_launch(canonical_key)
                if active is not None:
                    self._lifecycle.begin_termination(active.launch_id)

            success = agent.terminate()

            if success:
                # Confirm lifecycle termination
                if self._lifecycle is not None:
                    from src.domain.services.canonical_key import build_manager_key as _bmk

                    canonical_key = _bmk(name)
                    active = self._lifecycle.get_active_launch(canonical_key)
                    if active is not None:
                        self._lifecycle.confirm_terminated(active.launch_id)
                del self._agents[name]
            return success

    def list_agents(self) -> list[Agent]:
        return list(self._agents.values())

    def get_healthy_agents(self) -> list[Agent]:
        return [a for a in self._agents.values() if a.is_healthy()]

    def start_health_monitoring(self) -> None:
        self._running = True
        self._health_thread = threading.Thread(target=self._health_monitor_loop, daemon=True)
        self._health_thread.start()

    def stop_health_monitoring(self) -> None:
        self._running = False
        if self._health_thread:
            self._health_thread.join(timeout=5)

    def _health_monitor_loop(self) -> None:
        while self._running:
            try:
                self._check_agent_health()
            except Exception:
                logger.exception("Error in health monitor loop")
            time.sleep(self._health_check_interval)

    def _check_agent_health(self) -> None:
        with self._lock:
            for name, agent in list(self._agents.items()):
                if not agent.can_execute():
                    logger.warning(f"Agent {name} circuit breaker OPEN")
                    continue

                pid = agent.get_pid()
                if pid is None and agent.status == AgentStatus.HEALTHY:
                    logger.warning(f"Agent {name} process not found, marking unhealthy")
                    agent._update_status(AgentStatus.UNHEALTHY)

    def list_runtime_sessions(self) -> set[str]:
        """List all tmux sessions matching fork_agent prefixes.

        Returns:
            Set of session names matching fork- or agent- prefix.
        """
        sessions: set[str] = set()
        try:
            result = subprocess.run(
                ["tmux", "list-sessions", "-F", "#{session_name}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                # No sessions or error - return empty set
                return sessions

            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                # Only include sessions with our prefixes
                if line.startswith(FORK_SESSION_PREFIX) or line.startswith(AGENT_SESSION_PREFIX):
                    sessions.add(line)

        except subprocess.TimeoutExpired:
            logger.warning("Timeout listing tmux sessions")
        except Exception as e:
            logger.error(f"Error listing tmux sessions: {e}")

        return sessions

    def reconcile_sessions(self) -> ReconcileResult:
        """Reconcile runtime tmux sessions with registered agents.

        Compares:
        - Runtime sessions (from tmux) vs registered agents
        - Identifies orphaned sessions (in tmux but not registered)
        - Identifies missing sessions (registered but not in tmux)

        Returns:
            ReconcileResult with orphan and missing session info.
        """
        with self._lock:
            # Get runtime sessions
            runtime_sessions = self.list_runtime_sessions()

            # Get registered agent sessions
            registered_sessions: set[str] = set()
            for agent in self._agents.values():
                if isinstance(agent, TmuxAgent):
                    registered_sessions.add(agent.tmux_session)

            # Find orphaned sessions (in tmux but not registered)
            orphaned = runtime_sessions - registered_sessions

            # Find missing sessions (registered but not in tmux)
            missing = registered_sessions - runtime_sessions

            # Determine status
            if not orphaned and not missing:
                status = "ok"
            elif orphaned or missing:
                status = "warning"
            else:
                status = "error"

            return ReconcileResult(
                registered_agents=registered_sessions,
                runtime_sessions=runtime_sessions,
                orphaned_sessions=orphaned,
                missing_sessions=missing,
                status=status,
            )

    def cleanup_orphans(self, dry_run: bool = False, min_age_seconds: int = 0) -> CleanupResult:
        """Clean up orphaned tmux sessions.

        Args:
            dry_run: If True, only report what would be cleaned without actually cleaning.
            min_age_seconds: Only clean sessions older than this many seconds.

        Returns:
            CleanupResult with cleaned and failed session lists.
        """
        result = self.reconcile_sessions()
        cleaned: list[str] = []
        failed: list[str] = []

        for session in result.orphaned_sessions:
            # Optional age check - skip sessions younger than min_age_seconds
            if min_age_seconds > 0:
                session_age = self._get_session_age(session)
                if session_age < min_age_seconds:
                    logger.info(
                        f"Skipping young session {session} (age: {session_age}s < {min_age_seconds}s)"
                    )
                    continue

            if dry_run:
                logger.info(f"[DRY RUN] Would clean orphan session: {session}")
                cleaned.append(session)
            else:
                logger.info(f"Cleaning orphan session: {session}")
                if self._kill_session(session):
                    cleaned.append(session)
                else:
                    failed.append(session)
                    logger.error(f"Failed to clean orphan session: {session}")

        return CleanupResult(
            cleaned_sessions=cleaned,
            failed_sessions=failed,
            dry_run=dry_run,
        )

    def _get_session_age(self, session_name: str) -> float:
        """Get the age of a tmux session in seconds."""
        try:
            result = subprocess.run(
                ["tmux", "list-sessions", "-F", "#{session_created}", "-t", session_name],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                created_ts = int(result.stdout.strip())
                return time.time() - created_ts
        except Exception as e:
            logger.warning(f"Could not get age for session {session_name}: {e}")
        return 0.0

    def _kill_session(self, session_name: str) -> bool:
        """Kill a tmux session."""
        try:
            result = subprocess.run(
                ["tmux", "kill-session", "-t", session_name],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error killing session {session_name}: {e}")
            return False

    def get_health_status(self) -> dict[str, object]:
        """Get health status including orphan session info."""
        reconcile = self.reconcile_sessions()
        return {
            "orphan_sessions_count": len(reconcile.orphaned_sessions),
            "orphan_sessions": list(reconcile.orphaned_sessions),
            "reconcile_status": reconcile.status,
            "registered_count": len(self._agents),
            "runtime_sessions_count": len(reconcile.runtime_sessions),
        }


_agent_manager: AgentManager | None = None


def get_agent_manager(
    lifecycle_service: AgentLaunchLifecycleService | None = None,
) -> AgentManager:
    global _agent_manager
    if _agent_manager is None:
        _agent_manager = AgentManager(lifecycle_service=lifecycle_service)
    return _agent_manager
