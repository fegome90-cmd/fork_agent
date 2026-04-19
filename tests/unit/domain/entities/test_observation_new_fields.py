"""Unit tests for Observation entity — new fields and validation.

TDD Red Phase: 30 tests for project, type, topic_key, revision_count, session_id.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from src.domain.entities.observation import Observation


class TestNewFieldDefaults:
    """Test default values for all 5 new fields."""

    def test_project_defaults_to_none(self) -> None:
        obs = Observation(id="t1", timestamp=1000, content="test")
        assert obs.project is None

    def test_type_defaults_to_none(self) -> None:
        obs = Observation(id="t2", timestamp=1000, content="test")
        assert obs.type is None

    def test_topic_key_defaults_to_none(self) -> None:
        obs = Observation(id="t3", timestamp=1000, content="test")
        assert obs.topic_key is None

    def test_revision_count_defaults_to_one(self) -> None:
        obs = Observation(id="t4", timestamp=1000, content="test")
        assert obs.revision_count == 1

    def test_session_id_defaults_to_none(self) -> None:
        obs = Observation(id="t5", timestamp=1000, content="test")
        assert obs.session_id is None


class TestNewFieldAssignment:
    """Test that new fields can be set on construction."""

    def test_project_assigned(self) -> None:
        obs = Observation(id="t6", timestamp=1000, content="test", project="fork_agent")
        assert obs.project == "fork_agent"

    def test_type_assigned(self) -> None:
        obs = Observation(id="t7", timestamp=1000, content="test", type="decision")
        assert obs.type == "decision"

    def test_topic_key_assigned(self) -> None:
        obs = Observation(id="t8", timestamp=1000, content="test", topic_key="arch/auth")
        assert obs.topic_key == "arch/auth"

    def test_revision_count_assigned(self) -> None:
        obs = Observation(id="t9", timestamp=1000, content="test", revision_count=5)
        assert obs.revision_count == 5

    def test_session_id_assigned(self) -> None:
        obs = Observation(id="t10", timestamp=1000, content="test", session_id="ses_abc")
        assert obs.session_id == "ses_abc"


class TestTopicKeyValidation:
    """Validation rules for topic_key field."""

    def test_topic_key_rejects_spaces(self) -> None:
        with pytest.raises(ValueError, match="topic_key"):
            Observation(id="t11", timestamp=1000, content="test", topic_key="has space")

    def test_topic_key_accepts_slashes(self) -> None:
        obs = Observation(id="t12", timestamp=1000, content="test", topic_key="arch/auth/model")
        assert obs.topic_key == "arch/auth/model"

    def test_topic_key_accepts_dashes(self) -> None:
        obs = Observation(id="t13", timestamp=1000, content="test", topic_key="my-topic-key")
        assert obs.topic_key == "my-topic-key"

    def test_topic_key_accepts_none(self) -> None:
        obs = Observation(id="t14", timestamp=1000, content="test", topic_key=None)
        assert obs.topic_key is None


class TestRevisionCountValidation:
    """Validation rules for revision_count field."""

    def test_revision_count_rejects_zero(self) -> None:
        with pytest.raises(ValueError, match="revision_count"):
            Observation(id="t15", timestamp=1000, content="test", revision_count=0)

    def test_revision_count_rejects_negative(self) -> None:
        with pytest.raises(ValueError, match="revision_count"):
            Observation(id="t16", timestamp=1000, content="test", revision_count=-1)

    def test_revision_count_accepts_one(self) -> None:
        obs = Observation(id="t17", timestamp=1000, content="test", revision_count=1)
        assert obs.revision_count == 1

    def test_revision_count_accepts_large_value(self) -> None:
        obs = Observation(id="t18", timestamp=1000, content="test", revision_count=999)
        assert obs.revision_count == 999


class TestTypeValidation:
    """Validation rules for type field."""

    @pytest.mark.parametrize(
        "valid_type",
        [
            "decision",
            "architecture",
            "bugfix",
            "pattern",
            "config",
            "discovery",
            "learning",
            "manual",
            "tool_use",
            "file_change",
            "command",
            "file_read",
            "search",
        ],
    )
    def test_type_accepts_valid_values(self, valid_type: str) -> None:
        obs = Observation(id="t-valid", timestamp=1000, content="test", type=valid_type)
        assert obs.type == valid_type

    def test_type_rejects_invalid_value(self) -> None:
        with pytest.raises(ValueError, match="type"):
            Observation(id="t19", timestamp=1000, content="test", type="invalid_type")

    def test_type_accepts_none(self) -> None:
        obs = Observation(id="t20", timestamp=1000, content="test", type=None)
        assert obs.type is None


class TestProjectValidation:
    """Validation rules for project field."""

    def test_project_rejects_empty_string(self) -> None:
        with pytest.raises(ValueError, match="project"):
            Observation(id="t21", timestamp=1000, content="test", project="")

    def test_project_rejects_whitespace_only(self) -> None:
        with pytest.raises(ValueError, match="project"):
            Observation(id="t22", timestamp=1000, content="test", project="   ")

    def test_project_accepts_valid_string(self) -> None:
        obs = Observation(id="t23", timestamp=1000, content="test", project="fork_agent")
        assert obs.project == "fork_agent"

    def test_project_accepts_none(self) -> None:
        obs = Observation(id="t24", timestamp=1000, content="test", project=None)
        assert obs.project is None


class TestFrozenImmutability:
    """Verify frozen=True still holds with new fields."""

    def test_cannot_mutate_project(self) -> None:
        obs = Observation(id="t25", timestamp=1000, content="test", project="orig")
        with pytest.raises(FrozenInstanceError):
            obs.project = "new"  # type: ignore[misc]

    def test_cannot_mutate_type(self) -> None:
        obs = Observation(id="t26", timestamp=1000, content="test", type="decision")
        with pytest.raises(FrozenInstanceError):
            obs.type = "bugfix"  # type: ignore[misc]

    def test_cannot_mutate_topic_key(self) -> None:
        obs = Observation(id="t27", timestamp=1000, content="test", topic_key="a/b")
        with pytest.raises(FrozenInstanceError):
            obs.topic_key = "c/d"  # type: ignore[misc]

    def test_cannot_mutate_revision_count(self) -> None:
        obs = Observation(id="t28", timestamp=1000, content="test", revision_count=1)
        with pytest.raises(FrozenInstanceError):
            obs.revision_count = 2  # type: ignore[misc]

    def test_cannot_mutate_session_id(self) -> None:
        obs = Observation(id="t29", timestamp=1000, content="test", session_id="ses_1")
        with pytest.raises(FrozenInstanceError):
            obs.session_id = "ses_2"  # type: ignore[misc]


class TestBackwardCompatibility:
    """Entity still works with only original 5 fields."""

    def test_original_fields_only(self) -> None:
        obs = Observation(
            id="t30",
            timestamp=1700000000000,
            content="backward compat",
            metadata={"key": "val"},
            idempotency_key="dedup-1",
        )
        assert obs.id == "t30"
        assert obs.timestamp == 1700000000000
        assert obs.content == "backward compat"
        assert obs.metadata == {"key": "val"}
        assert obs.idempotency_key == "dedup-1"
        assert obs.project is None
        assert obs.type is None
        assert obs.topic_key is None
        assert obs.revision_count == 1
        assert obs.session_id is None
