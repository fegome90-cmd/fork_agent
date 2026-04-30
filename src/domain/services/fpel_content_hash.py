"""FPEL content hash computation — canonical hash functions for domain entities.

Provides stable SHA-256 hash functions so that freeze() and check_sealed()
use identical canonicalization for the same target type.

The hash captures the **content** of the entity (what it describes), NOT
its lifecycle state (status, timestamps). This ensures that post-freeze
drift in the actual work content is detected, while status transitions
(PLANNING → APPROVED → IN_PROGRESS) do not trigger false positives.
"""

from __future__ import annotations

import json

from src.domain.entities.fpel import compute_content_hash
from src.domain.entities.orchestration_task import OrchestrationTask


def compute_task_hash(task: OrchestrationTask) -> str:
    """Compute canonical SHA-256 hash of an OrchestrationTask's content.

    Uses `plan_text` when present (the substantive content), falling back
    to `subject` + `description` for tasks without a plan.

    Intentionally excludes: `status`, `owner`, `created_at`, `updated_at`,
    `approved_by`, `approved_at`, `requested_by` — these are lifecycle
    metadata, not content.
    """
    content = task.plan_text
    if content is None:
        parts = [task.subject]
        if task.description:
            parts.append(task.description)
        content = "\n".join(parts)
    return compute_content_hash(content)


def compute_plan_task_hash(task_id: str, slug: str, description: str) -> str:
    """Compute canonical SHA-256 hash of a single plan task's content.

    Used when workflow execute targets a specific task_id — the hash
    scope matches the task, not the entire plan.
    """
    data = {"id": task_id, "slug": slug, "description": description}
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return compute_content_hash(canonical)


def compute_plan_hash_from_tasks(tasks: list[dict[str, str]]) -> str:
    """Compute canonical SHA-256 hash of a plan's task list.

    Accepts a list of dicts with id/slug/description keys — no dependency
    on application-layer types.

    Serializes as sorted JSON to ensure deterministic hashing.
    """
    task_data = [{"id": t["id"], "slug": t["slug"], "description": t["description"]} for t in tasks]
    canonical = json.dumps(task_data, sort_keys=True, separators=(",", ":"))
    return compute_content_hash(canonical)
