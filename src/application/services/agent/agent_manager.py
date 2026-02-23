from __future__ import annotations

import logging
import subprocess
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    PENDING = "pending"
    STARTING = "starting"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    TERMINATING = "terminating"
    TERMINATED = "terminated"
    FAILED = "failed"


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


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


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 3,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._half_open_max_calls = half_open_max_calls
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._half_open_calls = 0
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if time.time() - self._last_failure_time >= self._recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
            return self._state

    def record_success(self) -> None:
        with self._lock:
            self._failure_count = 0
            self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._failure_count >= self._failure_threshold:
                self._state = CircuitState.OPEN

    def can_execute(self) -> bool:
        state = self.state
        if state == CircuitState.CLOSED:
            return True
        if state == CircuitState.HALF_OPEN:
            with self._lock:
                if self._half_open_calls < self._half_open_max_calls:
                    self._half_open_calls += 1
                    return True
        return False


class Agent(ABC):
    def __init__(self, config: AgentConfig) -> None:
        self._config = config
        self._status = AgentStatus.PENDING
        self._metrics = AgentMetrics()
        self._circuit_breaker = CircuitBreaker()
        self._lock = threading.Lock()

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
                logger.error(f"Session {self._tmux_session} not ready after {self._config.session_timeout}s")
                self._safe_kill(self._tmux_session)
                self._update_status(AgentStatus.FAILED)
                self._record_failure()
                return False

            self._update_status(AgentStatus.HEALTHY)
            self._metrics.last_heartbeat = time.time()
            self._record_success()
            logger.info(f"Agent {self._config.name} spawned in tmux session {self._tmux_session}")
            return True

        except Exception as e:
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
        except Exception:
            pass

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

        except Exception as e:
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
        except Exception:
            pass
        return None

    def send_input(self, message: str) -> bool:
        try:
            escaped = message.replace("'", "'\\''")
            result = subprocess.run(
                ["tmux", "send-keys", "-t", self._tmux_session, f"{escaped}", "Enter"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to send input to agent {self._config.name}: {e}")
            return False


class AgentManager:
    def __init__(self) -> None:
        self._agents: dict[str, Agent] = {}
        self._lock = threading.RLock()
        self._health_check_interval = 30
        self._running = False
        self._health_thread: threading.Thread | None = None

    def spawn_agent(self, config: AgentConfig) -> Agent | None:
        with self._lock:
            if config.name in self._agents:
                logger.warning(f"Agent {config.name} already exists")
                return None

            agent: Agent
            if config.tmux_session is not None or True:
                agent = TmuxAgent(config)
            else:
                raise ValueError("Unknown agent type")

            if agent.spawn():
                self._agents[config.name] = agent
                return agent

            return None

    def get_agent(self, name: str) -> Agent | None:
        return self._agents.get(name)

    def terminate_agent(self, name: str) -> bool:
        with self._lock:
            agent = self._agents.get(name)
            if agent is None:
                return False

            success = agent.terminate()
            if success:
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
            except Exception as e:
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


_agent_manager: AgentManager | None = None


def get_agent_manager() -> AgentManager:
    global _agent_manager
    if _agent_manager is None:
        _agent_manager = AgentManager()
    return _agent_manager
