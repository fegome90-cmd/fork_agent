"""Event dispatcher for matching events to actions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.domain.ports.event_ports import Event, IActionRunner

if TYPE_CHECKING:
    from src.domain.entities.rule import Rule

from src.application.services.orchestration.actions import (
    OnFailurePolicy,
    ShellCommandAction,
)

logger = logging.getLogger(__name__)


class EventDispatcher:
    """Stateless event dispatcher.

    Matches events against rules and runs corresponding actions.
    Supports failure policies: ABORT (default), CONTINUE, RETRY.

    Attributes:
        rules: List of rules to evaluate against incoming events.
        runner: The action runner responsible for executing matched actions.
        default_retry_attempts: How many times to retry on RETRY policy.
    """

    __slots__ = ("_rules", "_runner", "_default_retry_attempts")

    def __init__(
        self,
        rules: list[Rule],
        runner: IActionRunner,
        default_retry_attempts: int = 2,
    ) -> None:
        self._rules = rules
        self._runner = runner
        self._default_retry_attempts = default_retry_attempts

    @property
    def rules(self) -> list[Rule]:
        return self._rules

    @property
    def runner(self) -> IActionRunner:
        return self._runner

    def _get_policy(self, rule: Rule) -> OnFailurePolicy:
        """Get the failure policy for a rule's action."""
        action = rule.action
        if isinstance(action, ShellCommandAction):
            return action.on_failure
        return OnFailurePolicy.ABORT

    def dispatch(self, event: Event) -> None:
        """Dispatch event to all matching rules.

        Iterates through all rules and executes actions for those
        whose specifications are satisfied by the event.
        Respects each action's on_failure policy.

        Args:
            event: The event to dispatch.
        """
        for rule in self._rules:
            if rule.spec.is_satisfied_by(event):
                policy = self._get_policy(rule)
                self._run_with_policy(rule, policy)

    def _run_with_policy(self, rule: Rule, policy: OnFailurePolicy) -> None:
        """Run a rule's action respecting its failure policy."""
        if policy == OnFailurePolicy.CONTINUE:
            try:
                self._runner.run(rule.action)
            except Exception as exc:
                logger.warning(
                    "CONTINUE policy: swallowed error for rule '%s': %s",
                    getattr(rule.action, 'command', rule.action),
                    exc,
                )
        elif policy == OnFailurePolicy.RETRY:
            attempts = self._default_retry_attempts
            for attempt in range(attempts):
                try:
                    self._runner.run(rule.action)
                    return
                except Exception:
                    if attempt == attempts - 1:
                        raise
                    logger.debug(
                        "RETRY policy: attempt %d/%d failed",
                        attempt + 1,
                        attempts,
                    )
        else:
            # ABORT: let exception propagate
            self._runner.run(rule.action)
