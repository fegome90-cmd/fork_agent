"""Tests for topic_key field on Observation entity."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from src.domain.entities.observation import Observation


class TestObservationTopicKey:
    """Tests for topic_key field on Observation."""

    def test_create_observation_with_topic_key(self) -> None:
        observation = Observation(
            id="test-tk-001",
            timestamp=1700000000000,
            content="Test with topic_key",
            topic_key="fork/my-change/proposal",
        )

        assert observation.topic_key == "fork/my-change/proposal"

    def test_observation_topic_key_defaults_to_none(self) -> None:
        observation = Observation(
            id="test-tk-002",
            timestamp=1700000000000,
            content="No topic_key",
        )

        assert observation.topic_key is None

    def test_observation_validates_topic_key_type(self) -> None:
        with pytest.raises(TypeError, match="topic_key must be a string or None"):
            Observation(
                id="test-tk-003",
                timestamp=1700000000000,
                content="test",
                topic_key=123,  # type: ignore[arg-type]
            )

    def test_observation_validates_topic_key_not_empty(self) -> None:
        with pytest.raises(ValueError, match="topic_key must not be empty"):
            Observation(
                id="test-tk-004",
                timestamp=1700000000000,
                content="test",
                topic_key="",
            )

    def test_observation_accepts_none_topic_key(self) -> None:
        observation = Observation(
            id="test-tk-005",
            timestamp=1700000000000,
            content="Explicit None",
            topic_key=None,
        )

        assert observation.topic_key is None

    def test_topic_key_is_immutable(self) -> None:
        observation = Observation(
            id="test-tk-006",
            timestamp=1700000000000,
            content="Immutable topic_key",
            topic_key="fork/test/key",
        )

        with pytest.raises(FrozenInstanceError):
            observation.topic_key = "fork/other/key"  # type: ignore[misc]

    def test_observation_validates_topic_key_max_length(self) -> None:
        with pytest.raises(ValueError, match="topic_key must not exceed 128 characters"):
            Observation(
                id="test-tk-007",
                timestamp=1700000000000,
                content="test",
                topic_key="a" * 129,
            )

    def test_observation_accepts_topic_key_at_max_length(self) -> None:
        observation = Observation(
            id="test-tk-008",
            timestamp=1700000000000,
            content="test",
            topic_key="a" * 128,
        )
        assert len(observation.topic_key) == 128
