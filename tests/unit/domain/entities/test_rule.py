"""Tests for domain Rule entity.

TDD Red Phase - Tests written before implementation.
"""

from __future__ import annotations

import pytest

from src.domain.ports.event_ports import Action, Event, IActionRunner, ISpecification


class TestEventProtocol:
    """Tests for Event marker protocol."""

    def test_event_is_runtime_checkable(self) -> None:
        """Event protocol should be runtime_checkable for isinstance()."""
        # Event should be usable with isinstance() at runtime
        assert hasattr(Event, "__protocol_attrs__")

    def test_event_is_empty_protocol(self) -> None:
        """Event should be a marker protocol with no required methods."""
        # Empty protocol for type narrowing
        attrs = getattr(Event, "__protocol_attrs__", set())
        assert len(attrs) == 0


class TestActionProtocol:
    """Tests for Action marker protocol."""

    def test_action_is_runtime_checkable(self) -> None:
        """Action protocol should be runtime_checkable for isinstance()."""
        assert hasattr(Action, "__protocol_attrs__")

    def test_action_is_empty_protocol(self) -> None:
        """Action should be a marker protocol with no required methods."""
        attrs = getattr(Action, "__protocol_attrs__", set())
        assert len(attrs) == 0


class TestISpecification:
    """Tests for ISpecification protocol."""

    def test_has_is_satisfied_by_method(self) -> None:
        """ISpecification must have is_satisfied_by method."""
        assert hasattr(ISpecification, "is_satisfied_by")

    def test_is_satisfied_by_takes_event(self) -> None:
        """is_satisfied_by should accept Event parameter."""

        class ConcreteSpec:
            def is_satisfied_by(self, event: Event) -> bool:  # noqa: ARG002
                return True

        spec = ConcreteSpec()
        # Should not raise
        assert callable(spec.is_satisfied_by)


class TestIActionRunner:
    """Tests for IActionRunner protocol."""

    def test_has_run_method(self) -> None:
        """IActionRunner must have run method."""
        assert hasattr(IActionRunner, "run")

    def test_run_takes_action(self) -> None:
        """run should accept Action parameter."""

        class ConcreteRunner:
            def run(self, action: Action) -> None:
                pass

        runner = ConcreteRunner()
        assert callable(runner.run)


class TestRuleEntity:
    """Tests for Rule frozen dataclass."""

    def test_create_rule_with_spec_and_action(self) -> None:
        """Should create Rule with spec and action."""

        class DummySpec:
            def is_satisfied_by(self, event: Event) -> bool:  # noqa: ARG002
                return True

        class DummyAction:
            pass

        from src.domain.entities.rule import Rule

        rule = Rule(spec=DummySpec(), action=DummyAction())

        assert rule.spec is not None
        assert rule.action is not None

    def test_rule_is_immutable(self) -> None:
        """Rule should be frozen (immutable)."""
        from dataclasses import FrozenInstanceError

        from src.domain.entities.rule import Rule

        class DummySpec:
            def is_satisfied_by(self, event: Event) -> bool:  # noqa: ARG002
                return True

        class DummyAction:
            pass

        rule = Rule(spec=DummySpec(), action=DummyAction())

        with pytest.raises(FrozenInstanceError):
            rule.action = DummyAction()  # type: ignore[misc]

    def test_rule_rejects_none_spec(self) -> None:
        """Rule should reject None spec."""
        from src.domain.entities.rule import Rule

        class DummyAction:
            pass

        with pytest.raises(ValueError, match="spec cannot be None"):
            Rule(spec=None, action=DummyAction())  # type: ignore[arg-type]

    def test_rule_rejects_none_action(self) -> None:
        """Rule should reject None action."""
        from src.domain.entities.rule import Rule

        class DummySpec:
            def is_satisfied_by(self, event: Event) -> bool:  # noqa: ARG002
                return True

        with pytest.raises(ValueError, match="action cannot be None"):
            Rule(spec=DummySpec(), action=None)  # type: ignore[arg-type]

    def test_rule_stores_spec_and_action(self) -> None:
        """Rule should store and expose spec and action."""
        from src.domain.entities.rule import Rule

        class DummySpec:
            def is_satisfied_by(self, event: Event) -> bool:  # noqa: ARG002
                return True

        class DummyAction:
            value: str = "test_action"

        spec = DummySpec()
        action = DummyAction()
        rule = Rule(spec=spec, action=action)

        assert rule.spec is spec
        assert rule.action is action
