"""Unit tests for OrchestrationTask entity."""

from __future__ import annotations

import time

import pytest

from src.domain.entities.orchestration_task import (
    OrchestrationTask,
    OrchestrationTaskStatus,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOW_MS = int(time.time() * 1000)


def _make_task(
    status: OrchestrationTaskStatus = OrchestrationTaskStatus.PENDING,
    blocked_by: tuple[str, ...] = (),
    **overrides: object,
) -> OrchestrationTask:
    defaults: dict[str, object] = {
        "id": "a" * 32,
        "subject": "Test task",
        "status": status,
        "blocked_by": blocked_by,
        "created_at": NOW_MS,
        "updated_at": NOW_MS,
    }
    defaults.update(overrides)
    return OrchestrationTask(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Valid transitions: {(origin, target)}
# ---------------------------------------------------------------------------

VALID_TRANSITIONS: list[tuple[OrchestrationTaskStatus, OrchestrationTaskStatus]] = [
    (OrchestrationTaskStatus.PENDING, OrchestrationTaskStatus.PLANNING),
    (OrchestrationTaskStatus.PENDING, OrchestrationTaskStatus.DELETED),
    (OrchestrationTaskStatus.PLANNING, OrchestrationTaskStatus.APPROVED),
    (OrchestrationTaskStatus.PLANNING, OrchestrationTaskStatus.PENDING),
    (OrchestrationTaskStatus.PLANNING, OrchestrationTaskStatus.DELETED),
    (OrchestrationTaskStatus.APPROVED, OrchestrationTaskStatus.IN_PROGRESS),
    (OrchestrationTaskStatus.APPROVED, OrchestrationTaskStatus.DELETED),
    (OrchestrationTaskStatus.IN_PROGRESS, OrchestrationTaskStatus.COMPLETED),
    (OrchestrationTaskStatus.IN_PROGRESS, OrchestrationTaskStatus.DELETED),
    (OrchestrationTaskStatus.COMPLETED, OrchestrationTaskStatus.DELETED),
]


class TestValidTransitions:
    """All defined valid transitions must return True."""

    @pytest.mark.parametrize("origin, target", VALID_TRANSITIONS)
    def test_valid_transition(
        self, origin: OrchestrationTaskStatus, target: OrchestrationTaskStatus
    ) -> None:
        task = _make_task(status=origin)
        assert task.can_transition_to(target) is True


class TestInvalidTransitions:
    """Every combination not in the valid set must return False."""

    @staticmethod
    def _all_combinations() -> list[tuple[OrchestrationTaskStatus, OrchestrationTaskStatus]]:
        valid = set(VALID_TRANSITIONS)
        combos: list[tuple[OrchestrationTaskStatus, OrchestrationTaskStatus]] = []
        for origin in OrchestrationTaskStatus:
            for target in OrchestrationTaskStatus:
                if (origin, target) not in valid:
                    combos.append((origin, target))
        return combos

    @pytest.mark.parametrize("origin, target", _all_combinations())
    def test_invalid_transition(
        self, origin: OrchestrationTaskStatus, target: OrchestrationTaskStatus
    ) -> None:
        task = _make_task(status=origin)
        assert task.can_transition_to(target) is False


class TestDeletedIsTerminal:
    """DELETED is a terminal state — no transitions out."""

    @pytest.mark.parametrize("target", list(OrchestrationTaskStatus))
    def test_deleted_cannot_transition_to_anything(self, target: OrchestrationTaskStatus) -> None:
        task = _make_task(status=OrchestrationTaskStatus.DELETED)
        assert task.can_transition_to(target) is False


# ---------------------------------------------------------------------------
# Entity creation
# ---------------------------------------------------------------------------


class TestEntityCreation:
    def test_create_with_required_fields(self) -> None:
        task = OrchestrationTask(
            id="a" * 32,
            subject="Build the thing",
            created_at=NOW_MS,
            updated_at=NOW_MS,
        )
        assert task.id == "a" * 32
        assert task.subject == "Build the thing"
        assert task.description is None
        assert task.status == OrchestrationTaskStatus.PENDING
        assert task.owner is None
        assert task.blocked_by == ()
        assert task.plan_text is None
        assert task.approved_by is None
        assert task.approved_at is None
        assert task.requested_by is None

    def test_create_with_all_fields(self) -> None:
        task = OrchestrationTask(
            id="b" * 32,
            subject="Full task",
            description="A detailed description",
            status=OrchestrationTaskStatus.PLANNING,
            owner="agent-1",
            blocked_by=("c" * 32, "d" * 32),
            plan_text="# Plan\n- Step 1",
            created_at=NOW_MS,
            updated_at=NOW_MS,
            approved_by="reviewer",
            approved_at=NOW_MS,
            requested_by="alice",
        )
        assert task.description == "A detailed description"
        assert task.status == OrchestrationTaskStatus.PLANNING
        assert task.owner == "agent-1"
        assert task.blocked_by == ("c" * 32, "d" * 32)
        assert task.plan_text == "# Plan\n- Step 1"
        assert task.approved_by == "reviewer"
        assert task.approved_at == NOW_MS
        assert task.requested_by == "alice"

    def test_frozen_dataclass(self) -> None:
        task = _make_task()
        with pytest.raises(AttributeError):
            task.subject = "modified"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# __post_init__ validation
# ---------------------------------------------------------------------------


class TestPostInitValidation:
    def test_empty_subject_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="subject"):
            OrchestrationTask(
                id="a" * 32,
                subject="",
                created_at=NOW_MS,
                updated_at=NOW_MS,
            )

    def test_negative_created_at_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="created_at"):
            OrchestrationTask(
                id="a" * 32,
                subject="Valid subject",
                created_at=-1,
                updated_at=NOW_MS,
            )

    def test_negative_updated_at_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="updated_at"):
            OrchestrationTask(
                id="a" * 32,
                subject="Valid subject",
                created_at=NOW_MS,
                updated_at=-1,
            )

    def test_invalid_status_type_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="status"):
            OrchestrationTask(
                id="a" * 32,
                subject="Valid subject",
                status="NOT_A_STATUS",  # type: ignore[arg-type]
                created_at=NOW_MS,
                updated_at=NOW_MS,
            )

    def test_empty_id_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="id"):
            OrchestrationTask(
                id="",
                subject="Valid subject",
                created_at=NOW_MS,
                updated_at=NOW_MS,
            )

    def test_non_string_id_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="id"):
            OrchestrationTask(
                id=123,  # type: ignore[arg-type]
                subject="Valid subject",
                created_at=NOW_MS,
                updated_at=NOW_MS,
            )

    def test_non_string_description_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="description"):
            OrchestrationTask(
                id="a" * 32,
                subject="Valid subject",
                description=42,  # type: ignore[arg-type]
                created_at=NOW_MS,
                updated_at=NOW_MS,
            )

    def test_non_tuple_blocked_by_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="blocked_by"):
            OrchestrationTask(
                id="a" * 32,
                subject="Valid subject",
                blocked_by=["not-a-tuple"],  # type: ignore[arg-type]
                created_at=NOW_MS,
                updated_at=NOW_MS,
            )

    def test_empty_string_in_blocked_by_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="blocked_by"):
            OrchestrationTask(
                id="a" * 32,
                subject="Valid subject",
                blocked_by=("valid-id", ""),
                created_at=NOW_MS,
                updated_at=NOW_MS,
            )


# ---------------------------------------------------------------------------
# is_blocked property
# ---------------------------------------------------------------------------


class TestIsBlocked:
    def test_empty_blocked_by_is_not_blocked(self) -> None:
        task = _make_task(blocked_by=())
        assert task.is_blocked is False

    def test_non_empty_blocked_by_is_blocked(self) -> None:
        task = _make_task(blocked_by=("e" * 32,))
        assert task.is_blocked is True

    def test_multiple_blockers(self) -> None:
        task = _make_task(blocked_by=("e" * 32, "f" * 32))
        assert task.is_blocked is True


# ---------------------------------------------------------------------------
# Self-blocking detection (M9)
# ---------------------------------------------------------------------------


class TestSelfBlocking:
    def test_self_in_blocked_by_raises_value_error(self) -> None:
        task_id = "a" * 32
        with pytest.raises(ValueError, match="cannot block itself"):
            OrchestrationTask(
                id=task_id,
                subject="Self-blocking",
                blocked_by=(task_id,),
                created_at=NOW_MS,
                updated_at=NOW_MS,
            )


# ---------------------------------------------------------------------------
# detect_cycle static method (M9)
# ---------------------------------------------------------------------------


class TestDetectCycle:
    def test_no_cycle(self) -> None:
        a = _make_task(id="a" * 32, blocked_by=("b" * 32,))
        b = _make_task(id="b" * 32)
        assert OrchestrationTask.detect_cycle([a, b]) is False

    def test_simple_cycle(self) -> None:
        a = _make_task(id="a" * 32, blocked_by=("b" * 32,))
        b = _make_task(id="b" * 32, blocked_by=("a" * 32,))
        assert OrchestrationTask.detect_cycle([a, b]) is True

    def test_three_node_cycle(self) -> None:
        a = _make_task(id="a" * 32, blocked_by=("b" * 32,))
        b = _make_task(id="b" * 32, blocked_by=("c" * 32,))
        c = _make_task(id="c" * 32, blocked_by=("a" * 32,))
        assert OrchestrationTask.detect_cycle([a, b, c]) is True

    def test_empty_list(self) -> None:
        assert OrchestrationTask.detect_cycle([]) is False

    def test_single_node_no_cycle(self) -> None:
        a = _make_task(id="a" * 32)
        assert OrchestrationTask.detect_cycle([a]) is False


# ---------------------------------------------------------------------------
# DELETED cannot transition to anything (M9 — explicit tests)
# ---------------------------------------------------------------------------


class TestDeletedTransitions:
    @pytest.mark.parametrize(
        "target",
        [
            OrchestrationTaskStatus.PENDING,
            OrchestrationTaskStatus.PLANNING,
            OrchestrationTaskStatus.APPROVED,
            OrchestrationTaskStatus.IN_PROGRESS,
            OrchestrationTaskStatus.COMPLETED,
            OrchestrationTaskStatus.DELETED,
        ],
    )
    def test_deleted_to_any_status_is_false(self, target: OrchestrationTaskStatus) -> None:
        task = _make_task(status=OrchestrationTaskStatus.DELETED)
        assert task.can_transition_to(target) is False
