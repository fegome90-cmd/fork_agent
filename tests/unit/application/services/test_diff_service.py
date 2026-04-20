"""Tests for DiffService."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.application.services.diff_service import DiffEntry, DiffResult, DiffService
from src.domain.entities.observation import Observation


def _make_obs(
    id: str = "obs-1",
    timestamp: int = 1000,
    content: str = "content",
    topic_key: str | None = "topic-key",
    project: str | None = None,
    type: str | None = None,
    session_id: str | None = None,
) -> Observation:
    return Observation(
        id=id,
        timestamp=timestamp,
        content=content,
        topic_key=topic_key,
        project=project,
        type=type,
        session_id=session_id,
    )


class TestDiffEntry:
    """Tests for DiffEntry dataclass."""

    def test_frozen(self) -> None:
        entry = DiffEntry(status="added", topic_key="t", content="c")
        with pytest.raises(AttributeError):
            entry.status = "removed"  # type: ignore[misc]

    def test_fields(self) -> None:
        entry = DiffEntry(
            status="modified",
            topic_key="t",
            content="new",
            previous_content="old",
            observation_id="o2",
            previous_id="o1",
        )
        assert entry.status == "modified"
        assert entry.topic_key == "t"
        assert entry.content == "new"
        assert entry.previous_content == "old"


class TestDiffResult:
    """Tests for DiffResult dataclass."""

    def test_frozen(self) -> None:
        result = DiffResult(
            reference_label="a",
            target_label="b",
            entries=(),
            summary={},
        )
        with pytest.raises(AttributeError):
            result.summary = {}  # type: ignore[misc]

    def test_empty(self) -> None:
        result = DiffResult(
            reference_label="a",
            target_label="b",
            entries=(),
            summary={},
        )
        assert result.entries == ()
        assert result.summary == {}


class TestDiffServiceDiffByTimestamp:
    """Tests for DiffService.diff_by_timestamp()."""

    def _make_service(self) -> DiffService:
        repo = MagicMock()
        return DiffService(repo)

    def test_no_observations(self) -> None:
        svc = self._make_service()
        svc._repo.get_by_timestamp_range.return_value = []
        result = svc.diff_by_timestamp(before=(0, 1000), after=(1001, 2000))
        assert result.entries == ()
        assert result.summary == {"added": 0, "removed": 0, "modified": 0, "unchanged": 0}

    def test_added_observations(self) -> None:
        svc = self._make_service()
        svc._repo.get_by_timestamp_range.side_effect = [
            [],
            [_make_obs(id="new", timestamp=1500, content="new content", topic_key="new-topic")],
        ]
        result = svc.diff_by_timestamp(before=(0, 1000), after=(1001, 2000))
        assert result.summary["added"] == 1
        assert result.entries[0].status == "added"
        assert result.entries[0].content == "new content"

    def test_removed_observations(self) -> None:
        svc = self._make_service()
        svc._repo.get_by_timestamp_range.side_effect = [
            [_make_obs(id="old", timestamp=500, content="old content", topic_key="old-topic")],
            [],
        ]
        result = svc.diff_by_timestamp(before=(0, 1000), after=(1001, 2000))
        assert result.summary["removed"] == 1
        assert result.entries[0].status == "removed"

    def test_modified_observations(self) -> None:
        svc = self._make_service()
        svc._repo.get_by_timestamp_range.side_effect = [
            [_make_obs(id="o1", timestamp=500, content="v1", topic_key="my-topic")],
            [_make_obs(id="o2", timestamp=1500, content="v2", topic_key="my-topic")],
        ]
        result = svc.diff_by_timestamp(before=(0, 1000), after=(1001, 2000))
        assert result.summary["modified"] == 1
        assert result.entries[0].status == "modified"
        assert result.entries[0].previous_content == "v1"
        assert result.entries[0].content == "v2"

    def test_unchanged_not_in_entries(self) -> None:
        svc = self._make_service()
        svc._repo.get_by_timestamp_range.side_effect = [
            [_make_obs(id="o1", timestamp=500, content="same", topic_key="stable")],
            [_make_obs(id="o2", timestamp=1500, content="same", topic_key="stable")],
        ]
        result = svc.diff_by_timestamp(before=(0, 1000), after=(1001, 2000))
        assert len(result.entries) == 0
        assert result.summary["added"] == 0
        assert result.summary["modified"] == 0
        assert result.summary["removed"] == 0

    def test_project_filter(self) -> None:
        svc = self._make_service()
        svc._repo.get_by_timestamp_range.side_effect = [
            [
                _make_obs(id="o1", timestamp=500, content="a", topic_key="t1", project="alpha"),
                _make_obs(id="o2", timestamp=600, content="b", topic_key="t2", project="beta"),
            ],
            [],
        ]
        result = svc.diff_by_timestamp(before=(0, 1000), after=(1001, 2000), project="alpha")
        assert result.summary["removed"] == 1
        assert result.entries[0].topic_key == "t1"

    def test_type_filter(self) -> None:
        svc = self._make_service()
        svc._repo.get_by_timestamp_range.side_effect = [
            [
                _make_obs(id="o1", timestamp=500, content="a", topic_key="t1", type="decision"),
                _make_obs(id="o2", timestamp=600, content="b", topic_key="t2", type="bugfix"),
            ],
            [],
        ]
        result = svc.diff_by_timestamp(before=(0, 1000), after=(1001, 2000), obs_type="decision")
        assert result.summary["removed"] == 1

    def test_sort_order_added_modified_removed(self) -> None:
        svc = self._make_service()
        svc._repo.get_by_timestamp_range.side_effect = [
            [
                _make_obs(id="r1", timestamp=500, content="removed", topic_key="removed-topic"),
                _make_obs(id="r2", timestamp=600, content="v1", topic_key="modified-topic"),
            ],
            [
                _make_obs(id="a1", timestamp=1500, content="added", topic_key="added-topic"),
                _make_obs(id="a2", timestamp=1600, content="v2", topic_key="modified-topic"),
            ],
        ]
        result = svc.diff_by_timestamp(before=(0, 1000), after=(1001, 2000))
        statuses = [e.status for e in result.entries]
        assert statuses == ["added", "modified", "removed"]

    def test_no_topic_key_uses_id_prefix(self) -> None:
        svc = self._make_service()
        svc._repo.get_by_timestamp_range.side_effect = [
            [_make_obs(id="abc12345-full", timestamp=500, content="v1", topic_key=None)],
            [_make_obs(id="abc12345-other", timestamp=1500, content="v2", topic_key=None)],
        ]
        result = svc.diff_by_timestamp(before=(0, 1000), after=(1001, 2000))
        assert result.summary["modified"] == 1

    def test_labels_preserved(self) -> None:
        svc = self._make_service()
        svc._repo.get_by_timestamp_range.return_value = []
        result = svc.diff_by_timestamp(before=(0, 1000), after=(1001, 2000))
        assert result.reference_label == "timestamp:0-1000"
        assert result.target_label == "timestamp:1001-2000"


class TestDiffServiceDiffBySession:
    """Tests for DiffService.diff_by_session()."""

    def _make_service(self) -> DiffService:
        repo = MagicMock()
        return DiffService(repo)

    def test_basic_session_diff(self) -> None:
        svc = self._make_service()
        svc._repo.get_by_session_id.side_effect = [
            [_make_obs(id="o1", timestamp=1000, content="v1", topic_key="t1", session_id="s1")],
            [_make_obs(id="o2", timestamp=2000, content="v2", topic_key="t1", session_id="s2")],
        ]
        result = svc.diff_by_session("s1", "s2")
        assert result.summary["modified"] == 1
        assert result.reference_label == "session:s1"
        assert result.target_label == "session:s2"

    def test_empty_reference_session_raises(self) -> None:
        svc = self._make_service()
        svc._repo.get_by_session_id.side_effect = [[], []]
        with pytest.raises(ValueError, match="No observations found for reference session 'empty'"):
            svc.diff_by_session("empty", "s2")

    def test_empty_target_session_raises(self) -> None:
        svc = self._make_service()
        svc._repo.get_by_session_id.side_effect = [
            [_make_obs(id="o1", timestamp=1000, content="c", session_id="s1")],
            [],
        ]
        with pytest.raises(ValueError, match="No observations found for target session 'empty'"):
            svc.diff_by_session("s1", "empty")

    def test_session_diff_with_project_filter(self) -> None:
        svc = self._make_service()
        svc._repo.get_by_session_id.side_effect = [
            [
                _make_obs(
                    id="o1",
                    timestamp=1000,
                    content="a",
                    topic_key="t1",
                    project="alpha",
                    session_id="s1",
                ),
                _make_obs(
                    id="o2",
                    timestamp=1001,
                    content="b",
                    topic_key="t2",
                    project="beta",
                    session_id="s1",
                ),
            ],
            [
                _make_obs(
                    id="o3",
                    timestamp=2000,
                    content="c",
                    topic_key="t1",
                    project="alpha",
                    session_id="s2",
                ),
                _make_obs(
                    id="o4",
                    timestamp=2001,
                    content="d",
                    topic_key="t3",
                    project="beta",
                    session_id="s2",
                ),
            ],
        ]
        result = svc.diff_by_session("s1", "s2", project="alpha")
        assert result.summary["modified"] == 1
        assert result.entries[0].topic_key == "t1"

    def test_session_diff_added_removed_modified(self) -> None:
        svc = self._make_service()
        svc._repo.get_by_session_id.side_effect = [
            [
                _make_obs(
                    id="r1", timestamp=1000, content="removed", topic_key="removed", session_id="s1"
                ),
                _make_obs(
                    id="r2", timestamp=1001, content="v1", topic_key="modified", session_id="s1"
                ),
            ],
            [
                _make_obs(
                    id="a1", timestamp=2000, content="added", topic_key="added", session_id="s2"
                ),
                _make_obs(
                    id="a2", timestamp=2001, content="v2", topic_key="modified", session_id="s2"
                ),
            ],
        ]
        result = svc.diff_by_session("s1", "s2")
        assert result.summary == {"added": 1, "removed": 1, "modified": 1, "unchanged": 0}


class TestDiffServiceDiffById:
    """Tests for DiffService.diff_by_id()."""

    def _make_service(self) -> DiffService:
        repo = MagicMock()
        return DiffService(repo)

    def test_modified(self) -> None:
        svc = self._make_service()
        svc._repo.get_by_id.side_effect = [
            _make_obs(id="o1", content="v1", topic_key="t"),
            _make_obs(id="o2", content="v2", topic_key="t"),
        ]
        result = svc.diff_by_id("o1", "o2")
        assert result.summary["modified"] == 1
        assert result.entries[0].status == "modified"
        assert result.entries[0].previous_content == "v1"
        assert result.entries[0].content == "v2"

    def test_unchanged(self) -> None:
        svc = self._make_service()
        obs = _make_obs(id="o1", content="same", topic_key="t")
        svc._repo.get_by_id.side_effect = [obs, obs]
        result = svc.diff_by_id("o1", "o2")
        assert result.summary["unchanged"] == 1
        assert result.entries[0].status == "unchanged"

    def test_labels(self) -> None:
        svc = self._make_service()
        svc._repo.get_by_id.side_effect = [
            _make_obs(id="o1", content="a"),
            _make_obs(id="o2", content="b"),
        ]
        result = svc.diff_by_id("o1", "o2")
        assert result.reference_label == "id:o1"
        assert result.target_label == "id:o2"

    def test_not_found_raises(self) -> None:
        svc = self._make_service()
        from src.application.exceptions import ObservationNotFoundError

        svc._repo.get_by_id.side_effect = ObservationNotFoundError("not found")
        with pytest.raises(ObservationNotFoundError):
            svc.diff_by_id("nonexistent", "o2")
