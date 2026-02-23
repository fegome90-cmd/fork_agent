from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class HealthResponse:
    status: str
    agents: dict[str, dict[str, Any]]
    circuit_breakers: dict[str, str]


def build_health_response(
    agents: dict[str, Any],
    circuit_breakers: dict[str, str],
) -> HealthResponse:
    agent_statuses = {}
    for name, agent in agents.items():
        agent_statuses[name] = {
            "status": agent.get("status", "unknown"),
            "pid": agent.get("pid"),
            "can_execute": agent.get("can_execute", True),
        }

    overall_status = "healthy" if agent_statuses else "degraded"

    return HealthResponse(
        status=overall_status,
        agents=agent_statuses,
        circuit_breakers=circuit_breakers,
    )


def to_dict(response: HealthResponse) -> dict[str, Any]:
    return {
        "status": response.status,
        "agents": response.agents,
        "circuit_breakers": response.circuit_breakers,
    }
