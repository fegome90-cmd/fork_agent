"""Tests for UserDecision entity."""

from __future__ import annotations

import pytest

from src.domain.entities.user_decision import DecisionStatus, UserDecision


class TestUserDecision:
    """Tests for UserDecision entity."""

    def test_create_decision(self) -> None:
        """Test creating a UserDecision."""
        decision = UserDecision(
            key="test-key",
            value="test-value",
            status=DecisionStatus.LOCKED,
        )
        assert decision.key == "test-key"
        assert decision.value == "test-value"
        assert decision.status == DecisionStatus.LOCKED
        assert decision.rationale is None

    def test_create_decision_with_rationale(self) -> None:
        """Test creating a UserDecision with rationale."""
        decision = UserDecision(
            key="test-key",
            value="test-value",
            status=DecisionStatus.DEFERRED,
            rationale="Some rationale",
        )
        assert decision.rationale == "Some rationale"

    def test_key_must_be_string(self) -> None:
        """Test that key must be a string."""
        with pytest.raises(TypeError):
            UserDecision(key=123, value="test", status=DecisionStatus.LOCKED)

    def test_key_cannot_be_empty(self) -> None:
        """Test that key cannot be empty."""
        with pytest.raises(ValueError):
            UserDecision(key="", value="test", status=DecisionStatus.LOCKED)

    def test_value_must_be_string(self) -> None:
        """Test that value must be a string."""
        with pytest.raises(TypeError):
            UserDecision(key="test", value=123, status=DecisionStatus.LOCKED)

    def test_status_must_be_decision_status(self) -> None:
        """Test that status must be DecisionStatus."""
        with pytest.raises(TypeError):
            UserDecision(key="test", value="test", status="locked")

    def test_rationale_can_be_none(self) -> None:
        """Test that rationale can be None."""
        decision = UserDecision(
            key="test",
            value="test",
            status=DecisionStatus.DISCRETION,
            rationale=None,
        )
        assert decision.rationale is None

    def test_rationale_must_be_string_or_none(self) -> None:
        """Test that rationale must be string or None."""
        with pytest.raises(TypeError):
            UserDecision(
                key="test",
                value="test",
                status=DecisionStatus.LOCKED,
                rationale=123,
            )

    def test_with_status(self) -> None:
        """Test creating new decision with different status."""
        decision = UserDecision(
            key="test",
            value="test",
            status=DecisionStatus.LOCKED,
        )
        new_decision = decision.with_status(DecisionStatus.DEFERRED)
        assert new_decision.status == DecisionStatus.DEFERRED
        assert new_decision.key == decision.key
        assert new_decision.value == decision.value

    def test_with_value(self) -> None:
        """Test creating new decision with different value."""
        decision = UserDecision(
            key="test",
            value="old-value",
            status=DecisionStatus.LOCKED,
        )
        new_decision = decision.with_value("new-value")
        assert new_decision.value == "new-value"
        assert new_decision.key == decision.key
        assert new_decision.status == decision.status


class TestDecisionStatus:
    """Tests for DecisionStatus enum."""

    def test_decision_status_values(self) -> None:
        """Test DecisionStatus enum values."""
        assert DecisionStatus.LOCKED.value == "locked"
        assert DecisionStatus.DEFERRED.value == "deferred"
        assert DecisionStatus.DISCRETION.value == "discretion"

    def test_decision_status_can_be_compared_with_string(self) -> None:
        """Test that DecisionStatus can be compared with string values."""
        assert DecisionStatus.LOCKED == "locked"
        assert DecisionStatus.DEFERRED == "deferred"
        assert DecisionStatus.DISCRETION == "discretion"
