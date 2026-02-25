"""Rule entity for event-action association."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.ports.event_ports import Action, ISpecification


@dataclass(frozen=True)
class Rule:
    """Immutable association between a Specification and an Action.

    When an event satisfies the specification, the action should be executed.
    Used by EventDispatcher to match events to actions.

    Attributes:
        spec: The specification that determines if this rule applies.
        action: The action to execute when the specification is satisfied.
    """

    spec: ISpecification
    action: Action

    def __post_init__(self) -> None:
        if self.spec is None:
            raise ValueError("spec cannot be None")
        if self.action is None:
            raise ValueError("action cannot be None")
