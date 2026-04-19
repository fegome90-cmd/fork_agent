"""Tests for FailurePolicy integration in EventDispatcher."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.application.services.orchestration.actions import (
    OnFailurePolicy,
    ShellCommandAction,
)
from src.application.services.orchestration.dispatcher import EventDispatcher
from src.domain.entities.rule import Rule
from src.domain.ports.event_ports import IActionRunner
from src.infrastructure.orchestration.shell_action_runner import HookExecutionError


def _make_rule(
    policy: OnFailurePolicy = OnFailurePolicy.ABORT,
    critical: bool = True,
    command: str = "echo hello",
) -> Rule:
    """Create a Rule with a ShellCommandAction using the given policy."""
    action = ShellCommandAction(
        command=command,
        on_failure=policy,
        critical=critical,
    )
    spec = MagicMock()
    spec.is_satisfied_by.return_value = True
    return Rule(spec=spec, action=action)


def _make_event() -> MagicMock:
    event = MagicMock()
    event.__class__ = type("FakeEvent", (), {})
    return event


class TestAbortPolicy:
    """ABORT policy: exception propagates, stops dispatching."""

    def test_abort_propagates_exception(self) -> None:
        """When policy is ABORT, runner exception propagates."""
        rule = _make_rule(OnFailurePolicy.ABORT)
        runner = MagicMock(spec=IActionRunner)
        runner.run.side_effect = HookExecutionError("boom")

        dispatcher = EventDispatcher(rules=[rule], runner=runner)
        with pytest.raises(HookExecutionError, match="boom"):
            dispatcher.dispatch(_make_event())

    def test_abort_stops_at_first_failure(self) -> None:
        """ABORT stops processing remaining rules."""
        rule1 = _make_rule(OnFailurePolicy.ABORT, command="fail")
        rule2 = _make_rule(OnFailurePolicy.ABORT, command="pass")
        runner = MagicMock(spec=IActionRunner)
        runner.run.side_effect = [HookExecutionError("fail"), None]

        dispatcher = EventDispatcher(rules=[rule1, rule2], runner=runner)
        with pytest.raises(HookExecutionError):
            dispatcher.dispatch(_make_event())

        # Second rule's action should NOT have been run
        assert runner.run.call_count == 1


class TestContinuePolicy:
    """CONTINUE policy: failure is logged, remaining rules still run."""

    def test_continue_does_not_propagate(self) -> None:
        """When policy is CONTINUE, exception is swallowed."""
        rule = _make_rule(OnFailurePolicy.CONTINUE, critical=False)
        runner = MagicMock(spec=IActionRunner)
        runner.run.side_effect = HookExecutionError("soft fail")

        dispatcher = EventDispatcher(rules=[rule], runner=runner)
        # Should NOT raise
        dispatcher.dispatch(_make_event())

    def test_continue_runs_remaining_rules(self) -> None:
        """CONTINUE policy allows remaining rules to execute."""
        rule1 = _make_rule(OnFailurePolicy.CONTINUE, critical=False, command="fail")
        rule2 = _make_rule(OnFailurePolicy.ABORT, command="pass")
        runner = MagicMock(spec=IActionRunner)
        runner.run.side_effect = [HookExecutionError("soft fail"), None]

        dispatcher = EventDispatcher(rules=[rule1, rule2], runner=runner)
        dispatcher.dispatch(_make_event())

        assert runner.run.call_count == 2

    def test_continue_success_runs_normally(self) -> None:
        """CONTINUE policy with successful action runs normally."""
        rule = _make_rule(OnFailurePolicy.CONTINUE)
        runner = MagicMock(spec=IActionRunner)

        dispatcher = EventDispatcher(rules=[rule], runner=runner)
        dispatcher.dispatch(_make_event())

        runner.run.assert_called_once_with(rule.action)


class TestRetryPolicy:
    """RETRY policy: retries up to default_retry_attempts before failing."""

    def test_retry_succeeds_on_second_attempt(self) -> None:
        """RETRY succeeds when second attempt works."""
        rule = _make_rule(OnFailurePolicy.RETRY)
        runner = MagicMock(spec=IActionRunner)
        runner.run.side_effect = [HookExecutionError("fail"), None]

        dispatcher = EventDispatcher(rules=[rule], runner=runner, default_retry_attempts=2)
        dispatcher.dispatch(_make_event())

        assert runner.run.call_count == 2

    def test_retry_exhausted_propagates(self) -> None:
        """RETRY propagates exception after all attempts exhausted."""
        rule = _make_rule(OnFailurePolicy.RETRY)
        runner = MagicMock(spec=IActionRunner)
        runner.run.side_effect = HookExecutionError("persistent")

        dispatcher = EventDispatcher(rules=[rule], runner=runner, default_retry_attempts=3)
        with pytest.raises(HookExecutionError, match="persistent"):
            dispatcher.dispatch(_make_event())

        assert runner.run.call_count == 3

    def test_retry_with_default_attempts(self) -> None:
        """Default retry attempts is 2."""
        rule = _make_rule(OnFailurePolicy.RETRY)
        runner = MagicMock(spec=IActionRunner)
        runner.run.side_effect = HookExecutionError("fail")

        dispatcher = EventDispatcher(rules=[rule], runner=runner)
        with pytest.raises(HookExecutionError):
            dispatcher.dispatch(_make_event())

        assert runner.run.call_count == 2


class TestNonShellCommandAction:
    """Non-ShellCommandAction defaults to ABORT policy."""

    def test_non_shell_action_defaults_to_abort(self) -> None:
        """Actions that aren't ShellCommandAction get ABORT by default."""
        spec = MagicMock()
        spec.is_satisfied_by.return_value = True
        action = MagicMock()  # Not a ShellCommandAction
        rule = Rule(spec=spec, action=action)

        runner = MagicMock(spec=IActionRunner)
        runner.run.side_effect = RuntimeError("unexpected")

        dispatcher = EventDispatcher(rules=[rule], runner=runner)
        with pytest.raises(RuntimeError, match="unexpected"):
            dispatcher.dispatch(_make_event())


class TestMixedPolicies:
    """Mixed policies in a single dispatch."""

    def test_mixed_abort_stops_at_failure(self) -> None:
        """CONTINUE -> ABORT sequence: ABORT stops further rules."""
        rule1 = _make_rule(OnFailurePolicy.CONTINUE, critical=False, command="soft")
        rule2 = _make_rule(OnFailurePolicy.ABORT, command="hard")
        rule3 = _make_rule(OnFailurePolicy.ABORT, command="never")

        runner = MagicMock(spec=IActionRunner)
        runner.run.side_effect = [
            HookExecutionError("soft fail"),
            HookExecutionError("hard fail"),
            None,
        ]

        dispatcher = EventDispatcher(rules=[rule1, rule2, rule3], runner=runner)
        with pytest.raises(HookExecutionError, match="hard fail"):
            dispatcher.dispatch(_make_event())

        # rule1 (CONTINUE) ran and failed, rule2 (ABORT) ran and raised,
        # rule3 never ran
        assert runner.run.call_count == 2

    def test_all_continue_all_run(self) -> None:
        """All CONTINUE policies: all rules run despite failures."""
        rules = [
            _make_rule(OnFailurePolicy.CONTINUE, critical=False, command=f"cmd{i}")
            for i in range(3)
        ]
        runner = MagicMock(spec=IActionRunner)
        runner.run.side_effect = [
            HookExecutionError("fail1"),
            HookExecutionError("fail2"),
            None,
        ]

        dispatcher = EventDispatcher(rules=rules, runner=runner)
        dispatcher.dispatch(_make_event())

        assert runner.run.call_count == 3
