from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DecisionStatus(StrEnum):
    """Decision status enum with string values for database persistence."""

    LOCKED = "locked"
    DEFERRED = "deferred"
    DISCRETION = "discretion"


@dataclass(frozen=True)
class UserDecision:
    """Immutable user decision entity.

    Represents a decision made by the user during workflow execution,
    preserving context between interactions.

    Attributes:
        key: Unique identifier for the decision.
        value: The decision value/answer.
        status: Current status (locked, deferred, or discretion).
        rationale: Optional explanation of the decision.
    """

    key: str
    value: str
    status: DecisionStatus
    rationale: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.key, str):
            raise TypeError("key debe ser un string")
        if not self.key:
            raise ValueError("key no puede estar vacío")
        if not isinstance(self.value, str):
            raise TypeError("value debe ser un string")
        if not isinstance(self.status, DecisionStatus):
            raise TypeError("status debe ser un DecisionStatus")
        if self.rationale is not None and not isinstance(self.rationale, str):
            raise TypeError("rationale debe ser un string o None")

    def with_status(self, new_status: DecisionStatus) -> UserDecision:
        """Create a new UserDecision with a different status."""
        return UserDecision(
            key=self.key,
            value=self.value,
            status=new_status,
            rationale=self.rationale,
        )

    def with_value(self, new_value: str) -> UserDecision:
        """Create a new UserDecision with a different value."""
        return UserDecision(
            key=self.key,
            value=new_value,
            status=self.status,
            rationale=self.rationale,
        )
