"""Tests for the diff service method."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.application.services.diff_result import DiffItem, DiffResult
from src.application.services.memory_service import MemoryService
from src.domain.entities.observation import Observation


def _make_obs(
    id: str = "obs-1",
    timestamp: int = 1000,
    content: str = "content",
    topic_key: str | None = "topic-key",
    project: str | None = None,
    type: str | None = None,
) -> Observation:
    return Observation(
        id=id, timestamp=timestamp, content=content,
        topic_key=topic_key, project=project, type=type,
    )


class TestMemoryServiceDiff:
    """Tests for MemoryService.diff()."""

    def _make_service(self) -> MemoryService:
        repo = MagicMock()
        return MemoryService(repository=repo)

    def test_from_greater_than_to_raises(self) -> None:
        svc = self._make_service()
        with pytest.raises(ValueError, match="from must be before to"):
            svc.diff(from_ts=2000, to_ts=1000)

    def test_from_equals_to_raises(self) -> None:
        svc = self._make_service()
        with pytest.raises(ValueError, match="from must be before to"):
            svc.diff(from_ts=1000, to_ts=1000)

    def test_no_observations_returns_empty(self) -> None:
        svc = self._make_service()
        svc._repository.get_by_timestamp_range.return_value = []
        result = svc.diff(from_ts=1000, to_ts=2000)
        assert result.added == 0
        assert result.modified == 0
        assert result.removed == 0
        assert result.items == ()

    def test_added_observations(self) -> None:
        svc = self._make_service()
        svc._repository.get_by_timestamp_range.side_effect = [
            [],  # from window: nothing
            [_make_obs(id="obs-new", timestamp=1500, content="new content", topic_key="new-topic")],
        ]
        result = svc.diff(from_ts=1000, to_ts=2000)
        assert result.added == 1
        assert result.modified == 0
        assert result.removed == 0
        assert result.items[0].change_type == "added"
        assert result.items[0].to_content == "new content"

    def test_removed_observations(self) -> None:
        svc = self._make_service()
        svc._repository.get_by_timestamp_range.side_effect = [
            [_make_obs(id="obs-old", timestamp=500, content="old content", topic_key="old-topic")],
            [],  # to window: nothing
        ]
        result = svc.diff(from_ts=1000, to_ts=2000)
        assert result.added == 0
        assert result.modified == 0
        assert result.removed == 1
        assert result.items[0].change_type == "removed"
        assert result.items[0].from_content == "old content"

    def test_modified_observations(self) -> None:
        svc = self._make_service()
        svc._repository.get_by_timestamp_range.side_effect = [
            [_make_obs(id="obs-1", timestamp=500, content="v1", topic_key="my-topic")],
            [_make_obs(id="obs-2", timestamp=1500, content="v2", topic_key="my-topic")],
        ]
        result = svc.diff(from_ts=1000, to_ts=2000)
        assert result.added == 0
        assert result.removed == 0
        assert result.modified == 1
        assert result.items[0].change_type == "modified"
        assert result.items[0].from_content == "v1"
        assert result.items[0].to_content == "v2"

    def test_unchanged_observations_not_in_diff(self) -> None:
        svc = self._make_service()
        svc._repository.get_by_timestamp_range.side_effect = [
            [_make_obs(id="obs-1", timestamp=500, content="same", topic_key="stable")],
            [_make_obs(id="obs-2", timestamp=1500, content="same", topic_key="stable")],
        ]
        result = svc.diff(from_ts=1000, to_ts=2000)
        assert result.added == 0
        assert result.modified == 0
        assert result.removed == 0

    def test_project_filter(self) -> None:
        svc = self._make_service()
        svc._repository.get_by_timestamp_range.side_effect = [
            [
                _make_obs(id="o1", timestamp=500, content="a", topic_key="t1", project="proj-a"),
                _make_obs(id="o2", timestamp=600, content="b", topic_key="t2", project="proj-b"),
            ],
            [],
        ]
        result = svc.diff(from_ts=1000, to_ts=2000, project="proj-a")
        assert result.removed == 1
        assert result.items[0].topic_key == "t1"

    def test_type_filter(self) -> None:
        svc = self._make_service()
        svc._repository.get_by_timestamp_range.side_effect = [
            [
                _make_obs(id="o1", timestamp=500, content="a", topic_key="t1", type="decision"),
                _make_obs(id="o2", timestamp=600, content="b", topic_key="t2", type="bugfix"),
            ],
            [],
        ]
        result = svc.diff(from_ts=1000, to_ts=2000, obs_type="decision")
        assert result.removed == 1
        assert result.items[0].topic_key == "t1"

    def test_no_topic_key_matches_by_id_prefix(self) -> None:
        svc = self._make_service()
        svc._repository.get_by_timestamp_range.side_effect = [
            [_make_obs(id="abc12345-full", timestamp=500, content="v1", topic_key=None)],
            [_make_obs(id="abc12345-full", timestamp=1500, content="v2", topic_key=None)],
        ]
        result = svc.diff(from_ts=1000, to_ts=2000)
        # Both have same ID prefix "abc12345", content differs → modified
        assert result.modified == 1

    def test_latest_observation_wins_in_from_window(self) -> None:
        """When multiple observations have same topic_key, latest wins."""
        svc = self._make_service()
        svc._repository.get_by_timestamp_range.side_effect = [
            [
                _make_obs(id="o1", timestamp=300, content="old", topic_key="my-topic"),
                _make_obs(id="o2", timestamp=800, content="newer", topic_key="my-topic"),
            ],
            [_make_obs(id="o3", timestamp=1500, content="newest", topic_key="my-topic")],
        ]
        result = svc.diff(from_ts=1000, to_ts=2000)
        assert result.modified == 1
        assert result.items[0].from_content == "newer"
        assert result.items[0].to_content == "newest"

    def test_result_timestamps_preserved(self) -> None:
        svc = self._make_service()
        svc._repository.get_by_timestamp_range.return_value = []
        result = svc.diff(from_ts=1000, to_ts=2000)
        assert result.from_timestamp == 1000
        assert result.to_timestamp == 2000

    def test_result_to_json(self) -> None:
        svc = self._make_service()
        svc._repository.get_by_timestamp_range.side_effect = [
            [],
            [_make_obs(id="obs-new", timestamp=1500, content="new", topic_key="t")],
        ]
        result = svc.diff(from_ts=1000, to_ts=2000)
        j = result.to_json()
        assert j["summary"]["added"] == 1
        assert j["items"][0]["change_type"] == "added"
        assert j["from_timestamp"] == 1000
        assert j["to_timestamp"] == 2000

    def test_mixed_changes(self) -> None:
        """Test scenario with added, modified, and removed."""
        svc = self._make_service()
        svc._repository.get_by_timestamp_range.side_effect = [
            [
                _make_obs(id="o1", timestamp=500, content="removed-content", topic_key="removed"),
                _make_obs(id="o2", timestamp=700, content="v1", topic_key="modified"),
            ],
            [
                _make_obs(id="o3", timestamp=1500, content="v2", topic_key="modified"),
                _make_obs(id="o4", timestamp=1600, content="added-content", topic_key="added"),
            ],
        ]
        result = svc.diff(from_ts=1000, to_ts=2000)
        assert result.added == 1
        assert result.modified == 1
        assert result.removed == 1
