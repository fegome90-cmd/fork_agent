"""Single source of truth for canonical launch key construction.

All launch key formats are defined here. Production code MUST use these
builders instead of raw f-strings to guarantee consistent format and
namespace separation.

Format: ``{namespace}:{part1}:{part2}:...``
Validation: ``^[a-zA-Z0-9._:/-]{1,256}$``
"""

from __future__ import annotations

import hashlib


def _sanitize(value: str, max_length: int = 256) -> str:
    """Sanitize a key segment: strip, truncate, replace whitespace."""
    cleaned = value.strip().replace("\n", " ").replace("\r", "")
    return cleaned[:max_length]


def build_api_key(agent_type: str, task: str | None) -> str:
    """Build canonical key for API-initiated launches.

    Format: ``api:{agent_type}:{sha256_12hex}``
    When task is empty/None: ``api:{agent_type}:untitled``
    """
    sanitized_type = _sanitize(agent_type, max_length=64)
    if task:
        task_hash = hashlib.sha256(task.encode()).hexdigest()[:12]
    else:
        task_hash = "untitled"
    return f"api:{sanitized_type}:{task_hash}"


def build_task_key(task_id: str) -> str:
    """Build canonical key for polling/task-initiated launches.

    Format: ``task:{task_id}``
    """
    return f"task:{_sanitize(task_id, max_length=128)}"


def build_manager_key(agent_name: str) -> str:
    """Build canonical key for agent manager spawns.

    Format: ``manager:{agent_name}``
    """
    return f"manager:{_sanitize(agent_name, max_length=128)}"


def build_workflow_key(task_id: str) -> str:
    """Build canonical key for workflow executor launches.

    Format: ``workflow:{task_id}``
    """
    return f"workflow:{_sanitize(task_id, max_length=128)}"
