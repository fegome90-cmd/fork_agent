"""Tests for EventDispatcher service.

TDD Red Phase - Tests written before implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from src.domain.ports.event_ports import Action, Event

if TYPE_CHECKING:
    from src.domain.entities.rule import Rule


class MockEvent:
    """Mock event for testing."""

    pass


class MockAction:
    """Mock action for testing."""

    value: str = "test_action"


class MockSpecification:
    """Mock specification that returns configurable result."""

    def __init__(self, result: bool = True) -> None:
        self._result = result
        self.last_checked_event: Event | None = None

    def is_satisfied_by(self, event: Event) -> bool:
        self.last_checked_event = event
        return self._result


class TestEventDispatcher:
    """Tests for EventDispatcher service."""

    def test_dispatch_runs_action_when_spec_satisfied(self) -> None:
        """Dispatcher should run action when specification is satisfied."""
        from src.application.services.orchestration.dispatcher import EventDispatcher
        from src.domain.entities.rule import Rule

        mock_runner = MagicMock()
        spec = MockSpecification(result=True)
        action = MockAction()
        rule = Rule(spec=spec, action=action)
        event = MockEvent()

        dispatcher = EventDispatcher(rules=[rule], runner=mock_runner)
        dispatcher.dispatch(event)

        mock_runner.run.assert_called_once_with(action)

    def test_dispatch_skips_action_when_spec_not_satisfied(self) -> None:
        """Dispatcher should NOT run action when specification is not satisfied."""
        from src.application.services.orchestration.dispatcher import EventDispatcher
        from src.domain.entities.rule import Rule

        mock_runner = MagicMock()
        spec = MockSpecification(result=False)
        action = MockAction()
        rule = Rule(spec=spec, action=action)
        event = MockEvent()

        dispatcher = EventDispatcher(rules=[rule], runner=mock_runner)
        dispatcher.dispatch(event)

        mock_runner.run.assert_not_called()

    def test_dispatch_with_multiple_rules_some_matching(self) -> None:
        """Dispatcher should run actions only for matching rules."""
        from src.application.services.orchestration.dispatcher import EventDispatcher
        from src.domain.entities.rule import Rule

        mock_runner = MagicMock()

        spec1 = MockSpecification(result=True)
        action1 = MockAction()
        rule1 = Rule(spec=spec1, action=action1)

        spec2 = MockSpecification(result=False)
        action2 = MockAction()
        rule2 = Rule(spec=spec2, action=action2)

        spec3 = MockSpecification(result=True)
        action3 = MockAction()
        rule3 = Rule(spec=spec3, action=action3)

        event = MockEvent()

        dispatcher = EventDispatcher(rules=[rule1, rule2, rule3], runner=mock_runner)
        dispatcher.dispatch(event)

        assert mock_runner.run.call_count == 2

    def test_dispatch_with_no_rules(self) -> None:
        """Dispatcher should handle empty rules list gracefully."""
        from src.application.services.orchestration.dispatcher import EventDispatcher

        mock_runner = MagicMock()
        event = MockEvent()

        dispatcher = EventDispatcher(rules=[], runner=mock_runner)
        dispatcher.dispatch(event)

        mock_runner.run.assert_not_called()

    def test_dispatch_with_all_rules_matching_runs_all(self) -> None:
        """Dispatcher should run all actions when all specs are satisfied."""
        from src.application.services.orchestration.dispatcher import EventDispatcher
        from src.domain.entities.rule import Rule

        mock_runner = MagicMock()

        rules = []
        for _ in range(3):
            spec = MockSpecification(result=True)
            action = MockAction()
            rules.append(Rule(spec=spec, action=action))

        event = MockEvent()

        dispatcher = EventDispatcher(rules=rules, runner=mock_runner)
        dispatcher.dispatch(event)

        assert mock_runner.run.call_count == 3

    def test_dispatch_passes_event_to_specification(self) -> None:
        """Dispatcher should pass the event to specification for checking."""
        from src.application.services.orchestration.dispatcher import EventDispatcher
        from src.domain.entities.rule import Rule

        mock_runner = MagicMock()
        spec = MockSpecification(result=True)
        action = MockAction()
        rule = Rule(spec=spec, action=action)
        event = MockEvent()

        dispatcher = EventDispatcher(rules=[rule], runner=mock_runner)
        dispatcher.dispatch(event)

        assert spec.last_checked_event is event

    def test_dispatcher_stores_rules_immutably(self) -> None:
        """Dispatcher should store rules list reference."""
        from src.application.services.orchestration.dispatcher import EventDispatcher
        from src.domain.entities.rule import Rule

        mock_runner = MagicMock()
        spec = MockSpecification(result=True)
        action = MockAction()
        rule = Rule(spec=spec, action=action)
        rules = [rule]

        dispatcher = EventDispatcher(rules=rules, runner=mock_runner)

        assert dispatcher.rules is rules

    def test_dispatcher_stores_runner(self) -> None:
        """Dispatcher should store runner reference."""
        from src.application.services.orchestration.dispatcher import EventDispatcher

        mock_runner = MagicMock()

        dispatcher = EventDispatcher(rules=[], runner=mock_runner)

        assert dispatcher.runner is mock_runner
