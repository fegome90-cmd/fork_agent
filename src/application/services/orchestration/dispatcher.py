"""Event dispatcher for matching events to actions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.domain.ports.event_ports import Event, IActionRunner

if TYPE_CHECKING:
    from src.domain.entities.rule import Rule


class EventDispatcher:
    """Stateless event dispatcher.

    Matches events against rules and runs corresponding actions.
    Each event is checked against all rules; matching rules trigger their actions.

    Attributes:
        rules: List of rules to evaluate against incoming events.
        runner: The action runner responsible for executing matched actions.
    """

    __slots__ = ("_rules", "_runner")

    def __init__(self, rules: list[Rule], runner: IActionRunner) -> None:
        self._rules = rules
        self._runner = runner

    @property
    def rules(self) -> list[Rule]:
        """Return the list of rules."""
        return self._rules

    @property
    def runner(self) -> IActionRunner:
        """Return the action runner."""
        return self._runner

    def dispatch(self, event: Event) -> None:
        """Dispatch event to all matching rules.

        Iterates through all rules and executes actions for those
        whose specifications are satisfied by the event.

        Args:
            event: The event to dispatch.
        """
        for rule in self._rules:
            if rule.spec.is_satisfied_by(event):
                self._runner.run(rule.action)
