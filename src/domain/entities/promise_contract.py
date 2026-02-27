"""PromiseContract entity for work orchestration SSOT."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class PromiseState(Enum):
    """States in the promise contract lifecycle."""

    CREATED = "created"
    RUNNING = "running"
    VERIFY_PASSED = "verify_passed"
    VERIFY_FAILED = "verify_failed"
    SHIPPED = "shipped"
    FAILED = "failed"


@dataclass(frozen=True)
class VerifyEvidence:
    """Evidence from verification step."""

    artifact_path: str
    passed: bool
    exit_code: int
    timestamp: str

    def __post_init__(self) -> None:
        """Validate evidence fields."""
        if not self.artifact_path:
            raise ValueError("artifact_path must be non-empty")
        if not self.timestamp:
            raise ValueError("timestamp must be non-empty")
        if not isinstance(self.exit_code, int) or self.exit_code < 0:
            raise ValueError("exit_code must be a non-negative integer")


@dataclass(frozen=True)
class PromiseContract:
    """Immutable promise contract entity representing user promise state.

    Serves as the Single Source of Truth for work orchestration between CLI and API.

    Attributes:
        id: Unique identifier for the promise contract.
        session_id: Associated session identifier.
        plan_id: Associated plan identifier.
        task: The task description.
        state: Current state in the lifecycle.
        verify_evidence: Evidence from verification step (optional).
        created_at: Timestamp when the contract was created.
        updated_at: Timestamp when the contract was last updated.
        metadata: Additional metadata dictionary.
    """

    id: str
    session_id: str
    plan_id: str
    task: str
    state: PromiseState
    verify_evidence: VerifyEvidence | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, str):
            raise TypeError("id must be a string")
        if not self.id:
            raise ValueError("id cannot be empty")
        if not isinstance(self.session_id, str):
            raise TypeError("session_id must be a string")
        if not self.session_id:
            raise ValueError("session_id cannot be empty")
        if not isinstance(self.plan_id, str):
            raise TypeError("plan_id must be a string")
        if not self.plan_id:
            raise ValueError("plan_id cannot be empty")
        if not isinstance(self.task, str):
            raise TypeError("task must be a string")
        if not self.task:
            raise ValueError("task cannot be empty")
        if not isinstance(self.state, PromiseState):
            raise TypeError("state must be a PromiseState enum")
        if self.verify_evidence is not None and not isinstance(
            self.verify_evidence, VerifyEvidence
        ):
            raise TypeError("verify_evidence must be a VerifyEvidence or None")
        if self.created_at is not None and not isinstance(self.created_at, datetime):
            raise TypeError("created_at must be a datetime or None")
        if self.updated_at is not None and not isinstance(self.updated_at, datetime):
            raise TypeError("updated_at must be a datetime or None")
        if self.metadata is not None and not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dictionary or None")

    def can_transition_to(self, new_state: PromiseState) -> bool:
        """Validate state transition is allowed.

        Args:
            new_state: The desired new state.

        Returns:
            True if the transition is valid, False otherwise.
        """
        valid_transitions: dict[PromiseState, list[PromiseState]] = {
            PromiseState.CREATED: [PromiseState.RUNNING, PromiseState.FAILED],
            PromiseState.RUNNING: [
                PromiseState.VERIFY_PASSED,
                PromiseState.VERIFY_FAILED,
                PromiseState.FAILED,
            ],
            PromiseState.VERIFY_PASSED: [PromiseState.SHIPPED, PromiseState.FAILED],
            PromiseState.VERIFY_FAILED: [PromiseState.RUNNING, PromiseState.FAILED],
            PromiseState.SHIPPED: [],
            PromiseState.FAILED: [PromiseState.RUNNING],
        }
        return new_state in valid_transitions.get(self.state, [])

    def transition_to(
        self,
        new_state: PromiseState,
        verify_evidence: VerifyEvidence | None = None,
    ) -> PromiseContract:
        """Create a new PromiseContract with updated state.

        Args:
            new_state: The new state to transition to.
            verify_evidence: Optional evidence from verification.

        Returns:
            A new PromiseContract instance with the updated state.

        Raises:
            ValueError: If the transition is not allowed or evidence is missing for verification states.
        """
        if not self.can_transition_to(new_state):
            raise ValueError(f"Cannot transition from {self.state.value} to {new_state.value}")

        # Define verification states that require evidence
        verification_states = {PromiseState.VERIFY_PASSED, PromiseState.VERIFY_FAILED}

        # Require evidence for verification states
        if new_state in verification_states and verify_evidence is None:
            raise ValueError(f"Evidence required for transition to {new_state.value}")

        # Don't carry stale evidence to non-verification states
        final_evidence = verify_evidence if new_state in verification_states else None

        now = datetime.now()
        return PromiseContract(
            id=self.id,
            session_id=self.session_id,
            plan_id=self.plan_id,
            task=self.task,
            state=new_state,
            verify_evidence=final_evidence,
            created_at=self.created_at,
            updated_at=now,
            metadata=self.metadata,
        )
