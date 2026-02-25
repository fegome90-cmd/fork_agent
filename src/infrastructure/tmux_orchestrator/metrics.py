from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass
class Metrics:
    agent_spawn_total: int = 0
    agent_spawn_failures_total: int = 0
    ipc_message_latency_sum: float = 0.0
    ipc_message_latency_count: int = 0
    ipc_message_failures_total: int = 0
    tmux_session_count: int = 0


class PrometheusMetrics:
    def __init__(self) -> None:
        self._metrics = Metrics()
        self._lock = Lock()

    def inc_spawn(self, success: bool = True) -> None:
        with self._lock:
            if success:
                self._metrics.agent_spawn_total += 1
            else:
                self._metrics.agent_spawn_failures_total += 1

    def record_latency(self, latency: float) -> None:
        with self._lock:
            self._metrics.ipc_message_latency_sum += latency
            self._metrics.ipc_message_latency_count += 1

    def inc_ipc_failure(self) -> None:
        with self._lock:
            self._metrics.ipc_message_failures_total += 1

    def set_session_count(self, count: int) -> None:
        with self._lock:
            self._metrics.tmux_session_count = count

    def get_metrics(self) -> Metrics:
        with self._lock:
            return Metrics(
                agent_spawn_total=self._metrics.agent_spawn_total,
                agent_spawn_failures_total=self._metrics.agent_spawn_failures_total,
                ipc_message_latency_sum=self._metrics.ipc_message_latency_sum,
                ipc_message_latency_count=self._metrics.ipc_message_latency_count,
                ipc_message_failures_total=self._metrics.ipc_message_failures_total,
                tmux_session_count=self._metrics.tmux_session_count,
            )

    def format_prometheus(self) -> str:
        m = self.get_metrics()
        lines = [
            "# HELP agent_spawn_total Total number of agent spawn attempts",
            "# TYPE agent_spawn_total counter",
            f"agent_spawn_total {m.agent_spawn_total}",
            "# HELP agent_spawn_failures_total Total number of agent spawn failures",
            "# TYPE agent_spawn_failures_total counter",
            f"agent_spawn_failures_total {m.agent_spawn_failures_total}",
        ]

        if m.ipc_message_latency_count > 0:
            avg_latency = m.ipc_message_latency_sum / m.ipc_message_latency_count
            lines.extend(
                [
                    "# HELP ipc_message_latency_seconds Average IPC message latency",
                    "# TYPE ipc_message_latency_seconds gauge",
                    f"ipc_message_latency_seconds {avg_latency}",
                ]
            )

        lines.extend(
            [
                "# HELP ipc_message_failures_total Total number of IPC message failures",
                "# TYPE ipc_message_failures_total counter",
                f"ipc_message_failures_total {m.ipc_message_failures_total}",
                "# HELP tmux_session_count Current number of tmux sessions",
                "# TYPE tmux_session_count gauge",
                f"tmux_session_count {m.tmux_session_count}",
            ]
        )

        return "\n".join(lines)


_metrics_instance: PrometheusMetrics | None = None
_metrics_lock = Lock()


def get_prometheus_metrics() -> PrometheusMetrics:
    global _metrics_instance
    with _metrics_lock:
        if _metrics_instance is None:
            _metrics_instance = PrometheusMetrics()
        return _metrics_instance
