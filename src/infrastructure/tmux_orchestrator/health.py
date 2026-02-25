from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.infrastructure.tmux_orchestrator.resilience_policy import DEFAULT_POLICY


@dataclass
class HealthResponse:
    status: str
    agents: dict[str, dict[str, Any]]
    circuit_breakers: dict[str, dict[str, Any]]


def build_health_response(
    agents: dict[str, Any],
    circuit_breakers: dict[str, Any],
) -> HealthResponse:
    agent_statuses = {}
    for name, agent in agents.items():
        agent_statuses[name] = {
            "status": agent.get("status", "unknown"),
            "pid": agent.get("pid"),
            "can_execute": agent.get("can_execute", True),
        }

    cb_statuses = {}
    for name, cb_info in circuit_breakers.items():
        cb_statuses[name] = {
            "state": cb_info.get("state", "unknown"),
            "policy": DEFAULT_POLICY.to_dict(),
        }

    overall_status = "healthy" if agent_statuses else "degraded"

    return HealthResponse(
        status=overall_status,
        agents=agent_statuses,
        circuit_breakers=cb_statuses,
    )


def to_dict(response: HealthResponse) -> dict[str, Any]:
    return {
        "status": response.status,
        "agents": response.agents,
        "circuit_breakers": response.circuit_breakers,
    }
