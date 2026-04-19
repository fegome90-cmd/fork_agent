"""Tests for project and type fields on Observation entity (scoping)."""
from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from src.domain.entities.observation import Observation


class TestObservationScoping:
    """Tests for project and type fields on Observation."""

    def test_create_observation_with_project(self) -> None:
        observation = Observation(
            id="test-scp-001",
            timestamp=1700000000000,
            content="Test with project",
            project="fork_agent",
        )
        assert observation.project == "fork_agent"

    def test_create_observation_with_type(self) -> None:
        observation = Observation(
            id="test-scp-002",
            timestamp=1700000000000,
            content="Test with type",
            type="decision",
        )
        assert observation.type == "decision"

    def test_create_observation_with_both_project_and_type(self) -> None:
        observation = Observation(
            id="test-scp-003",
            timestamp=1700000000000,
            content="Test with both",
            project="fork_agent",
            type="decision",
        )
        assert observation.project == "fork_agent"
        assert observation.type == "decision"

    def test_observation_project_defaults_to_none(self) -> None:
        observation = Observation(
            id="test-scp-004",
            timestamp=1700000000000,
            content="No project",
        )
        assert observation.project is None

    def test_observation_type_defaults_to_none(self) -> None:
        observation = Observation(
            id="test-scp-005",
            timestamp=1700000000000,
            content="No type",
        )
        assert observation.type is None

    def test_observation_validates_project_type(self) -> None:
        with pytest.raises(TypeError, match="project must be a string or None"):
            Observation(
                id="test-scp-006",
                timestamp=1700000000000,
                content="test",
                project=123,  # type: ignore[arg-type]
            )

    def test_observation_validates_type_type(self) -> None:
        with pytest.raises(TypeError, match="type must be a string or None"):
            Observation(
                id="test-scp-007",
                timestamp=1700000000000,
                content="test",
                type=456,  # type: ignore[arg-type]
            )

    def test_observation_validates_project_not_empty(self) -> None:
        with pytest.raises(ValueError, match="project must not be empty"):
            Observation(
                id="test-scp-008",
                timestamp=1700000000000,
                content="test",
                project="",
            )

    def test_observation_validates_type_not_empty(self) -> None:
        with pytest.raises(ValueError, match="type must be one of"):
            Observation(
                id="test-scp-009",
                timestamp=1700000000000,
                content="test",
                type="",
            )

    def test_observation_accepts_none_project(self) -> None:
        observation = Observation(
            id="test-scp-010",
            timestamp=1700000000000,
            content="Explicit None project",
            project=None,
        )
        assert observation.project is None

    def test_observation_accepts_none_type(self) -> None:
        observation = Observation(
            id="test-scp-011",
            timestamp=1700000000000,
            content="Explicit None type",
            type=None,
        )
        assert observation.type is None

    def test_project_is_immutable(self) -> None:
        observation = Observation(
            id="test-scp-012",
            timestamp=1700000000000,
            content="Immutable project",
            project="fork_agent",
        )
        with pytest.raises(FrozenInstanceError):
            observation.project = "other_project"  # type: ignore[misc]

    def test_type_is_immutable(self) -> None:
        observation = Observation(
            id="test-scp-013",
            timestamp=1700000000000,
            content="Immutable type",
            type="decision",
        )
        with pytest.raises(FrozenInstanceError):
            observation.type = "milestone"  # type: ignore[misc]

    def test_project_with_underscores_allowed(self) -> None:
        observation = Observation(
            id="test-scp-014",
            timestamp=1700000000000,
            content="Test project with underscore",
            project="fork_agent_migration",
        )
        assert observation.project == "fork_agent_migration"

    def test_type_with_special_chars_allowed(self) -> None:
        observation = Observation(
            id="test-scp-015",
            timestamp=1700000000000,
            content="Test type with dash",
            type="session-summary",
        )
        assert observation.type == "session-summary"
