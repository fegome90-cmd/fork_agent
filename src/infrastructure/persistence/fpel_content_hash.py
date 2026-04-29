"""FPEL content hash computation for call sites.

Provides canonical hash functions for domain entities (OrchestrationTask,
PlanState) so that call sites can pass `current_hash` to `check_sealed()`.

The hash captures the **content** of the entity (what it describes), NOT
its lifecycle state (status, timestamps). This ensures that post-freeze
drift in the actual work content is detected, while status transitions
(PLANNING → APPROVED → IN_PROGRESS) do not trigger false positives.
"""

from __future__ import annotations

import json

from src.application.services.workflow.state import PlanState
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
        # Fallback: canonicalize subject + description
        parts = [task.subject]
        if task.description:
            parts.append(task.description)
        content = "\n".join(parts)
    return compute_content_hash(content)


def compute_plan_hash(plan: PlanState) -> str:
    """Compute canonical SHA-256 hash of a PlanState's content.

    Serializes the task list (id + slug + description) as canonical JSON.
    Intentionally excludes: `session_id`, `phase`, `status`, `started_at`,
    `decisions` — these are lifecycle metadata, not the work content.
    """
    task_data = [
        {
            "id": t.id,
            "slug": t.slug,
            "description": t.description,
        }
        for t in plan.tasks
    ]
    canonical = json.dumps(task_data, sort_keys=True, separators=(",", ":"))
    return compute_content_hash(canonical)
