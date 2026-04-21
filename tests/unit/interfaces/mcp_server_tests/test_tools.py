"""Unit tests for MCP tool handlers."""

from __future__ import annotations

import json
import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.domain.entities.observation import Observation


def _make_observation(
    id: str = "test-uuid-1234",
    content: str = "test observation content",
    metadata: dict[str, Any] | None = None,
    type: str | None = None,
    project: str | None = None,
    topic_key: str | None = None,
    revision_count: int = 1,
) -> Observation:
    """Create a test Observation with sensible defaults."""
    return Observation(
        id=id,
        timestamp=int(time.time() * 1000),
        content=content,
        metadata=metadata,
        type=type,
        project=project,
        topic_key=topic_key,
        revision_count=revision_count,
    )


# ---------------------------------------------------------------------------
# _serialize_observation
# ---------------------------------------------------------------------------


class TestSerializeObservation:
    def test_omits_none_fields(self) -> None:
        from src.interfaces.mcp.tools import _serialize_observation

        obs = _make_observation(id="a", content="b")
        result = _serialize_observation(obs)

        assert "id" in result
        assert "content" in result
        assert "timestamp" in result
        assert "revision_count" in result
        assert "project" not in result
        assert "metadata" not in result
        assert "type" not in result
        assert "topic_key" not in result
        assert "session_id" not in result

    def test_preserves_all_non_none_fields(self) -> None:
        from src.interfaces.mcp.tools import _serialize_observation

        obs = _make_observation(
            id="a",
            content="b",
            metadata={"what": "test"},
            type="decision",
            project="myproj",
            topic_key="test_topic",
            revision_count=2,
        )
        result = _serialize_observation(obs)

        assert result["id"] == "a"
        assert result["content"] == "b"
        assert result["metadata"] == {"what": "test"}
        assert result["type"] == "decision"
        assert result["project"] == "myproj"
        assert result["topic_key"] == "test_topic"
        assert result["revision_count"] == 2

    def test_preserves_timestamp(self) -> None:
        from src.interfaces.mcp.tools import _serialize_observation

        obs = _make_observation(id="a", content="b")
        result = _serialize_observation(obs)
        assert result["timestamp"] == obs.timestamp


# ---------------------------------------------------------------------------
# memory_save
# ---------------------------------------------------------------------------


class TestMemorySave:
    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_returns_id_and_status(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_save

        obs = _make_observation(id="saved-uuid")
        mock_get.return_value.save.return_value = obs

        result = memory_save(content="test content")
        data = json.loads(result)

        assert data["id"] == "saved-uuid"
        assert data["status"] == "saved"
        # Auto-detect fills project from CWD when not provided
        called_project = mock_get.return_value.save.call_args.kwargs.get("project")
        assert called_project is not None  # auto-detected from CWD
        mock_get.return_value.save.assert_called_once_with(
            content="test content",
            title=None,
            metadata=None,
            topic_key=None,
            project=called_project,
            type=None,
        )

    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_passes_all_params(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_save

        obs = _make_observation(id="full-uuid")
        mock_get.return_value.save.return_value = obs

        result = memory_save(
            content="my content",
            type="decision",
            project="myproj",
            topic_key="my_topic",
            metadata={"what": "test"},
        )
        data = json.loads(result)

        assert data["id"] == "full-uuid"
        mock_get.return_value.save.assert_called_once_with(
            content="my content",
            title=None,
            metadata={"what": "test"},
            topic_key="my_topic",
            project="myproj",
            type="decision",
        )


# ---------------------------------------------------------------------------
# memory_search
# ---------------------------------------------------------------------------


class TestMemorySearch:
    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_returns_results(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_search

        obs1 = _make_observation(id="s1", content="python patterns")
        obs2 = _make_observation(id="s2", content="python async")
        mock_get.return_value.search.return_value = [obs1, obs2]

        result = memory_search(query="python")
        data = json.loads(result)

        assert len(data) == 2
        assert data[0]["id"] == "s1"
        assert data[1]["id"] == "s2"
        mock_get.return_value.search.assert_called_once_with(query="python", limit=None, project="tmux_fork")

    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_passes_limit(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_search

        mock_get.return_value.search.return_value = []

        memory_search(query="test", limit=5)
        mock_get.return_value.search.assert_called_once_with(query="test", limit=5, project="tmux_fork")

    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_empty_results(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_search

        mock_get.return_value.search.return_value = []

        result = memory_search(query="nonexistent")
        data = json.loads(result)

        assert data == []


# ---------------------------------------------------------------------------
# memory_get
# ---------------------------------------------------------------------------


class TestMemoryGet:
    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_returns_observation(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_get

        obs = _make_observation(id="get-uuid", content="full content here")
        mock_get.return_value.get_by_id.return_value = obs

        result = memory_get(id="get-uuid")
        data = json.loads(result)

        assert data["id"] == "get-uuid"
        assert data["content"] == "full content here"
        mock_get.return_value.get_by_id.assert_called_once_with("get-uuid")

    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_not_found_raises_mcp_error(self, mock_get: MagicMock) -> None:
        from mcp.shared.exceptions import McpError

        from src.application.exceptions import ObservationNotFoundError
        from src.interfaces.mcp.tools import memory_get

        mock_get.return_value.get_by_id.side_effect = ObservationNotFoundError(
            "Observation not found."
        )

        with pytest.raises(McpError):
            memory_get(id="missing-uuid")


# ---------------------------------------------------------------------------
# memory_list
# ---------------------------------------------------------------------------


class TestMemoryList:
    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_returns_recent(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_list

        obs1 = _make_observation(id="l1", content="recent 1")
        obs2 = _make_observation(id="l2", content="recent 2")
        mock_get.return_value.get_recent.return_value = [obs1, obs2]

        result = memory_list()
        data = json.loads(result)

        assert len(data) == 2
        assert data[0]["id"] == "l1"
        assert data[1]["id"] == "l2"

    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_passes_limit_and_offset(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_list

        mock_get.return_value.get_recent.return_value = []

        memory_list(limit=5, offset=10)
        mock_get.return_value.get_recent.assert_called_once_with(limit=5, offset=10, type=None, project="tmux_fork")

    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_passes_type_filter(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_list

        mock_get.return_value.get_recent.return_value = []

        memory_list(type="decision")
        mock_get.return_value.get_recent.assert_called_once_with(
            limit=10, offset=0, type="decision", project="tmux_fork"
        )

    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_empty_list(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_list

        mock_get.return_value.get_recent.return_value = []

        result = memory_list()
        data = json.loads(result)

        assert data == []


# ---------------------------------------------------------------------------
# memory_delete
# ---------------------------------------------------------------------------


class TestMemoryDelete:
    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_calls_service_and_returns_status(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_delete

        mock_get.return_value.delete.return_value = None

        result = memory_delete(id="del-uuid")
        data = json.loads(result)

        assert data["id"] == "del-uuid"
        assert data["status"] == "deleted"
        mock_get.return_value.delete.assert_called_once_with("del-uuid")

    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_not_found_raises_mcp_error(self, mock_get: MagicMock) -> None:
        from mcp.shared.exceptions import McpError

        from src.application.exceptions import ObservationNotFoundError
        from src.interfaces.mcp.tools import memory_delete

        mock_get.return_value.delete.side_effect = ObservationNotFoundError(
            "Observation not found."
        )

        with pytest.raises(McpError):
            memory_delete(id="missing-uuid")


# ---------------------------------------------------------------------------
# memory_context
# ---------------------------------------------------------------------------


class TestMemoryContext:
    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_returns_recent_with_session_summary_filter(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_context

        obs = _make_observation(id="ctx1", content="session summary", type="session-summary")
        mock_get.return_value.get_recent.return_value = [obs]

        result = memory_context()
        data = json.loads(result)

        assert len(data) == 1
        assert data[0]["id"] == "ctx1"
        mock_get.return_value.get_recent.assert_called_once_with(
            limit=5, offset=0, type="session-summary", project="tmux_fork"
        )

    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_fallback_to_unfiltered(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_context

        obs = _make_observation(id="ctx2", content="recent item")
        mock_get.return_value.get_recent.side_effect = [
            [],  # First call with session-summary filter
            [obs],  # Fallback call without filter
        ]

        result = memory_context()
        data = json.loads(result)

        assert len(data) == 1
        assert mock_get.return_value.get_recent.call_count == 2


# ---------------------------------------------------------------------------
# _serialize_session
# ---------------------------------------------------------------------------


def _make_session(
    id: str = "sess-1234",
    project: str = "testproj",
    directory: str = "/tmp/test",
    goal: str | None = None,
    instructions: str | None = None,
    summary: str | None = None,
) -> Any:
    from src.domain.entities.session import Session

    return Session(
        id=id,
        project=project,
        directory=directory,
        started_at=int(time.time() * 1000),
        ended_at=None,
        goal=goal,
        instructions=instructions,
        summary=summary,
    )


class TestSerializeSession:
    def test_omits_none_fields(self) -> None:
        from src.interfaces.mcp.tools import _serialize_session

        session = _make_session()
        result = _serialize_session(session)

        assert "id" in result
        assert "project" in result
        assert "directory" in result
        assert "started_at" in result
        assert "ended_at" not in result
        assert "goal" not in result
        assert "instructions" not in result
        assert "summary" not in result

    def test_preserves_all_non_none_fields(self) -> None:
        from src.interfaces.mcp.tools import _serialize_session

        session = _make_session(
            goal="build feature",
            instructions="use TDD",
            summary="done",
        )
        result = _serialize_session(session)

        assert result["goal"] == "build feature"
        assert result["instructions"] == "use TDD"
        assert result["summary"] == "done"


class TestSerializeSessions:
    def test_serializes_list(self) -> None:
        from src.interfaces.mcp.tools import _serialize_sessions

        sessions = [_make_session(id="s1"), _make_session(id="s2")]
        result = _serialize_sessions(sessions)

        assert len(result) == 2
        assert result[0]["id"] == "s1"
        assert result[1]["id"] == "s2"


# ---------------------------------------------------------------------------
# _map_error — Error mapping tests
# ---------------------------------------------------------------------------


class TestMapErrorObservationNotFound:
    def test_observation_not_found_returns_invalid_params(self) -> None:
        from mcp.shared.exceptions import McpError
        from mcp.types import INVALID_PARAMS

        from src.application.exceptions import ObservationNotFoundError
        from src.interfaces.mcp.tools import _map_error

        err = ObservationNotFoundError("obs-123")
        result = _map_error(err)

        assert isinstance(result, McpError)
        assert result.error.code == INVALID_PARAMS


class TestMapErrorValueError:
    def test_value_error_returns_invalid_params(self) -> None:
        from mcp.shared.exceptions import McpError
        from mcp.types import INVALID_PARAMS

        from src.interfaces.mcp.tools import _map_error

        err = ValueError("Invalid input")
        result = _map_error(err)

        assert isinstance(result, McpError)
        assert result.error.code == INVALID_PARAMS


class TestMapErrorSessionNotFound:
    def test_session_not_found_returns_invalid_params(self) -> None:
        from mcp.shared.exceptions import McpError
        from mcp.types import INVALID_PARAMS

        from src.application.exceptions import SessionNotFoundError
        from src.interfaces.mcp.tools import _map_error

        err = SessionNotFoundError("Session not found.")
        result = _map_error(err)

        assert isinstance(result, McpError)
        assert result.error.code == INVALID_PARAMS


class TestMapErrorMemoryError:
    def test_memory_error_returns_internal_error(self) -> None:
        from mcp.shared.exceptions import McpError
        from mcp.types import INTERNAL_ERROR

        from src.application.exceptions import MemoryError
        from src.interfaces.mcp.tools import _map_error

        err = MemoryError("DB connection failed")
        result = _map_error(err)

        assert isinstance(result, McpError)
        assert result.error.code == INTERNAL_ERROR


class TestMapErrorGeneric:
    def test_generic_exception_returns_internal_error(self) -> None:
        from mcp.shared.exceptions import McpError
        from mcp.types import INTERNAL_ERROR

        from src.interfaces.mcp.tools import _map_error

        err = RuntimeError("Unexpected error")
        result = _map_error(err)

        assert isinstance(result, McpError)
        assert result.error.code == INTERNAL_ERROR
        assert "Internal error:" in result.error.message


# ---------------------------------------------------------------------------
# memory_update
# ---------------------------------------------------------------------------


class TestMemoryUpdate:
    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_returns_updated_observation(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_update

        obs = _make_observation(id="upd-uuid", content="updated", revision_count=2)
        mock_get.return_value.update.return_value = obs

        result = memory_update(id="upd-uuid", content="updated")
        data = json.loads(result)

        assert data["id"] == "upd-uuid"
        assert data["revision_count"] == 2
        mock_get.return_value.update.assert_called_once_with(
            observation_id="upd-uuid",
            title=None,
            content="updated",
            type=None,
            project=None,
            topic_key=None,
            metadata=None,
        )

    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_passes_metadata_json(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_update

        obs = _make_observation(id="upd-uuid")
        mock_get.return_value.update.return_value = obs

        memory_update(id="upd-uuid", metadata={"key": "val"})
        mock_get.return_value.update.assert_called_once_with(
            observation_id="upd-uuid",
            title=None,
            content=None,
            type=None,
            project=None,
            topic_key=None,
            metadata={"key": "val"},
        )


# ---------------------------------------------------------------------------
# memory_stats
# ---------------------------------------------------------------------------


class TestMemoryStats:
    @patch("src.interfaces.mcp.tools._get_health_service")
    def test_returns_stats_dict(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_stats

        mock_get.return_value.get_stats.return_value = {
            "observation_count": 42,
            "fts_count": 42,
            "db_size_bytes": 1024,
            "db_size_human": "1.0 KB",
        }

        result = memory_stats()
        data = json.loads(result)

        assert data["observation_count"] == 42
        assert data["db_size_human"] == "1.0 KB"
        mock_get.return_value.get_stats.assert_called_once()

    @patch("src.interfaces.mcp.tools._get_health_service")
    def test_error_raises_mcp_error(self, mock_get: MagicMock) -> None:
        from mcp.shared.exceptions import McpError

        from src.interfaces.mcp.tools import memory_stats

        mock_get.return_value.get_stats.side_effect = RuntimeError("db fail")

        with pytest.raises(McpError):
            memory_stats()


# ---------------------------------------------------------------------------
# memory_timeline
# ---------------------------------------------------------------------------


class TestMemoryTimeline:
    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_returns_observations_in_range(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_timeline

        obs = _make_observation(id="tl1", content="in range")
        mock_get.return_value.get_by_time_range.return_value = [obs]

        result = memory_timeline(start=1000, end=2000)
        data = json.loads(result)

        assert len(data) == 1
        assert data[0]["id"] == "tl1"
        mock_get.return_value.get_by_time_range.assert_called_once_with(1000, 2000, project="tmux_fork")

    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_empty_range(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_timeline

        mock_get.return_value.get_by_time_range.return_value = []

        result = memory_timeline(start=1000, end=2000)
        data = json.loads(result)

        assert data == []


# ---------------------------------------------------------------------------
# memory_session_start
# ---------------------------------------------------------------------------


class TestMemorySessionStart:
    @patch("src.interfaces.mcp.tools._get_session_service")
    def test_returns_session(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_session_start

        session = _make_session(id="new-sess", project="myproj")
        mock_get.return_value.start_session.return_value = session

        result = memory_session_start(project="myproj", directory="/tmp")
        data = json.loads(result)

        assert data["id"] == "new-sess"
        assert data["project"] == "myproj"
        mock_get.return_value.start_session.assert_called_once_with(
            project="myproj",
            directory="/tmp",
            goal=None,
            instructions=None,
        )

    @patch("src.interfaces.mcp.tools._get_session_service")
    def test_passes_optional_params(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_session_start

        session = _make_session()
        mock_get.return_value.start_session.return_value = session

        memory_session_start(
            project="p",
            directory="/d",
            goal="build X",
            instructions="use TDD",
        )
        mock_get.return_value.start_session.assert_called_once_with(
            project="p",
            directory="/d",
            goal="build X",
            instructions="use TDD",
        )


# ---------------------------------------------------------------------------
# memory_session_end
# ---------------------------------------------------------------------------


class TestMemorySessionEnd:
    @patch("src.interfaces.mcp.tools._get_session_service")
    def test_ends_session(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_session_end

        session = _make_session(id="end-sess", summary="done")
        mock_get.return_value.end_session.return_value = session

        result = memory_session_end(session_id="end-sess", summary="done")
        data = json.loads(result)

        assert data["id"] == "end-sess"
        mock_get.return_value.end_session.assert_called_once_with("end-sess", summary="done")

    @patch("src.interfaces.mcp.tools._get_session_service")
    def test_not_found_raises_mcp_error(self, mock_get: MagicMock) -> None:
        from mcp.shared.exceptions import McpError

        from src.application.exceptions import SessionNotFoundError
        from src.interfaces.mcp.tools import memory_session_end

        mock_get.return_value.end_session.side_effect = SessionNotFoundError()

        with pytest.raises(McpError):
            memory_session_end(session_id="missing")


# ---------------------------------------------------------------------------
# memory_session_summary
# ---------------------------------------------------------------------------


class TestMemorySessionSummary:
    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_saves_with_type_session_summary(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_session_summary

        obs = _make_observation(id="sum-uuid", type="session-summary")
        mock_get.return_value.save.return_value = obs

        result = memory_session_summary(content="Session completed", project="myproj")
        data = json.loads(result)

        assert data["id"] == "sum-uuid"
        assert data["status"] == "saved"
        assert data["type"] == "session-summary"
        mock_get.return_value.save.assert_called_once_with(
            content="Session completed",
            metadata=None,
            project="myproj",
            type="session-summary",
        )

    def test_empty_content_raises_error(self) -> None:
        from mcp import McpError

        from src.interfaces.mcp.tools import memory_session_summary

        with pytest.raises(McpError):
            memory_session_summary(content="")

    def test_whitespace_content_raises_error(self) -> None:
        from mcp import McpError

        from src.interfaces.mcp.tools import memory_session_summary

        with pytest.raises(McpError):
            memory_session_summary(content="   ")

    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_includes_session_id_in_metadata(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_session_summary

        obs = _make_observation(id="sum-uuid")
        mock_get.return_value.save.return_value = obs

        memory_session_summary(
            content="Summary text",
            project="myproj",
            session_id="sess-123",
        )
        mock_get.return_value.save.assert_called_once_with(
            content="Summary text",
            metadata={"session_id": "sess-123"},
            project="myproj",
            type="session-summary",
        )

    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_no_session_id_omits_metadata(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_session_summary

        obs = _make_observation(id="sum-uuid")
        mock_get.return_value.save.return_value = obs

        memory_session_summary(content="Summary", project="myproj")
        mock_get.return_value.save.assert_called_once_with(
            content="Summary",
            metadata=None,
            project="myproj",
            type="session-summary",
        )


# ---------------------------------------------------------------------------
# memory_suggest_topic_key
# ---------------------------------------------------------------------------


class TestSuggestTopicKeyInternal:
    def test_infer_family_from_type(self) -> None:
        from src.interfaces.mcp.tools import _infer_topic_family

        assert _infer_topic_family("architecture", "", "") == "architecture"
        assert _infer_topic_family("bugfix", "", "") == "bug"
        assert _infer_topic_family("decision", "", "") == "decision"
        assert _infer_topic_family("pattern", "", "") == "pattern"
        assert _infer_topic_family("config", "", "") == "config"
        assert _infer_topic_family("discovery", "", "") == "discovery"
        assert _infer_topic_family("learning", "", "") == "learning"

    def test_infer_family_from_content_keywords(self) -> None:
        from src.interfaces.mcp.tools import _infer_topic_family

        assert _infer_topic_family(None, "", "fixed a bug in auth") == "bug"
        assert _infer_topic_family(None, "", "new architecture for payments") == "architecture"
        assert _infer_topic_family(None, "", "discovery: root cause found") == "discovery"

    def test_infer_family_fallback_to_topic(self) -> None:
        from src.interfaces.mcp.tools import _infer_topic_family

        assert _infer_topic_family(None, "random title", "random content") == "topic"

    def test_normalize_segment(self) -> None:
        from src.interfaces.mcp.tools import _normalize_topic_segment

        assert _normalize_topic_segment("JWT Auth Model") == "jwt-auth-model"
        assert _normalize_topic_segment("  FTS5 Query!@#  ") == "fts5-query"
        assert _normalize_topic_segment("") == ""

    def test_normalize_segment_max_length(self) -> None:
        from src.interfaces.mcp.tools import _normalize_topic_segment

        long_text = "a" * 200
        result = _normalize_topic_segment(long_text)
        assert len(result) == 100

    def test_suggest_key_with_title(self) -> None:
        from src.interfaces.mcp.tools import _suggest_topic_key

        key = _suggest_topic_key("architecture", "JWT Auth Model", "")
        assert key == "architecture/jwt-auth-model"

    def test_suggest_key_with_content_fallback(self) -> None:
        from src.interfaces.mcp.tools import _suggest_topic_key

        key = _suggest_topic_key("bugfix", "", "Fixed N+1 in user list query")
        assert key.startswith("bug/")
        assert len(key) > 4

    def test_suggest_key_deduplication(self) -> None:
        from src.interfaces.mcp.tools import _suggest_topic_key

        key = _suggest_topic_key("bug", "bug-fts5-sanitization", "content")
        assert not key.startswith("bug/bug-")

    def test_suggest_key_empty_becomes_general(self) -> None:
        from src.interfaces.mcp.tools import _suggest_topic_key

        key = _suggest_topic_key("learning", "", "   ")
        assert key == "learning/general"


class TestMemorySuggestTopicKey:
    def test_returns_topic_key_json(self) -> None:
        from src.interfaces.mcp.tools import memory_suggest_topic_key

        result = memory_suggest_topic_key(title="JWT Auth Model", type="architecture")
        data = json.loads(result)

        assert "topic_key" in data
        assert "family" in data
        assert "segment" in data
        assert data["family"] == "architecture"
        assert data["segment"] == "jwt-auth-model"

    def test_uses_content_when_no_title(self) -> None:
        from src.interfaces.mcp.tools import memory_suggest_topic_key

        result = memory_suggest_topic_key(content="Fixed N+1 in user list", type="bugfix")
        data = json.loads(result)

        assert data["family"] == "bug"
        assert "topic_key" in data

    def test_raises_on_empty_inputs(self) -> None:
        from mcp import McpError

        from src.interfaces.mcp.tools import memory_suggest_topic_key

        with pytest.raises(McpError):
            memory_suggest_topic_key()

    def test_raises_on_whitespace_only(self) -> None:
        from mcp import McpError

        from src.interfaces.mcp.tools import memory_suggest_topic_key

        with pytest.raises(McpError):
            memory_suggest_topic_key(title="   ", content="   ")


# ---------------------------------------------------------------------------
# memory_save_prompt
# ---------------------------------------------------------------------------


class TestMemorySavePrompt:
    def test_raises_on_empty_content(self) -> None:
        from mcp import McpError

        from src.interfaces.mcp.tools import memory_save_prompt

        with pytest.raises(McpError):
            memory_save_prompt(content="")

    def test_raises_on_whitespace_content(self) -> None:
        from mcp import McpError

        from src.interfaces.mcp.tools import memory_save_prompt

        with pytest.raises(McpError):
            memory_save_prompt(content="   ")


# ---------------------------------------------------------------------------
# memory_capture_passive
# ---------------------------------------------------------------------------


class TestExtractLearnings:
    def test_extracts_numbered_items(self) -> None:
        from src.interfaces.mcp.tools import _extract_learnings

        text = """## Key Learnings:
1. First learning about the architecture decision we made
2. Second learning about the database optimization pattern
3. Third learning about the caching strategy implementation"""
        result = _extract_learnings(text)
        assert len(result) == 3
        assert "architecture decision" in result[0]

    def test_extracts_bullet_items(self) -> None:
        from src.interfaces.mcp.tools import _extract_learnings

        text = """## Key Learnings:
- First learning about the authentication flow
- Second learning about the error handling pattern"""
        result = _extract_learnings(text)
        assert len(result) == 2

    def test_extracts_aprendizajes_clave(self) -> None:
        from src.interfaces.mcp.tools import _extract_learnings

        text = """## Aprendizajes Clave:
1. Primera leccion aprendida sobre el sistema de memoria
2. Segunda leccion importante sobre la base de datos"""
        result = _extract_learnings(text)
        assert len(result) == 2

    def test_filters_short_items(self) -> None:
        from src.interfaces.mcp.tools import _extract_learnings

        text = """## Key Learnings:
1. Too short
2. This is a valid learning item with enough words and characters"""
        result = _extract_learnings(text)
        assert len(result) == 1
        assert "valid learning" in result[0]

    def test_returns_empty_when_no_header(self) -> None:
        from src.interfaces.mcp.tools import _extract_learnings

        text = "Just some regular text without any learnings header"
        result = _extract_learnings(text)
        assert result == []

    def test_strips_markdown_formatting(self) -> None:
        from src.interfaces.mcp.tools import _extract_learnings

        text = """## Key Learnings:
1. The **bold text** should be stripped from the learning output"""
        result = _extract_learnings(text)
        assert "**" not in result[0]

    def test_uses_last_section_when_multiple(self) -> None:
        from src.interfaces.mcp.tools import _extract_learnings

        text = """## Key Learnings:
1. First section learning about something important

## Key Learnings:
1. Second section learning about another important thing"""
        result = _extract_learnings(text)
        assert len(result) == 1
        assert "Second section" in result[0]


class TestMemoryCapturePassive:
    def test_raises_on_empty_content(self) -> None:
        from mcp import McpError

        from src.interfaces.mcp.tools import memory_capture_passive

        with pytest.raises(McpError):
            memory_capture_passive(content="")

    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_returns_zero_when_no_learnings_header(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_capture_passive

        result = memory_capture_passive(content="Just regular text without headers")
        data = json.loads(result)

        assert data["extracted"] == 0
        assert data["saved"] == 0
        assert data["duplicates"] == 0
        mock_get.return_value.save.assert_not_called()

    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_saves_learnings(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_capture_passive

        mock_get.return_value.search.return_value = []

        result = memory_capture_passive(
            content="## Key Learnings:\n1. Important learning about the system architecture",
            project="test-project",
        )
        data = json.loads(result)

        assert data["extracted"] == 1
        assert data["saved"] == 1
        assert data["duplicates"] == 0
        mock_get.return_value.save.assert_called_once()

    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_skips_duplicates(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_capture_passive

        existing = _make_observation(content="Important learning about the system architecture")
        mock_get.return_value.search.return_value = [existing]

        result = memory_capture_passive(
            content="## Key Learnings:\n1. Important learning about the system architecture",
        )
        data = json.loads(result)

        assert data["extracted"] == 1
        assert data["saved"] == 0
        assert data["duplicates"] == 1

    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_includes_source_in_metadata(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_capture_passive

        mock_get.return_value.search.return_value = []

        memory_capture_passive(
            content="## Key Learnings:\n1. Important learning about the architecture pattern",
            source="subagent-stop",
        )
        call_kwargs = mock_get.return_value.save.call_args
        assert call_kwargs.kwargs.get("metadata", {}) == {"source": "subagent-stop"}


class TestMemoryMergeProjects:
    def test_raises_on_empty_from(self) -> None:
        from mcp import McpError

        from src.interfaces.mcp.tools import memory_merge_projects

        with pytest.raises(McpError):
            memory_merge_projects(from_projects="", to_project="target")

    def test_raises_on_whitespace_from(self) -> None:
        from mcp import McpError

        from src.interfaces.mcp.tools import memory_merge_projects

        with pytest.raises(McpError):
            memory_merge_projects(from_projects="   ", to_project="target")

    def test_raises_on_empty_to(self) -> None:
        from mcp import McpError

        from src.interfaces.mcp.tools import memory_merge_projects

        with pytest.raises(McpError):
            memory_merge_projects(from_projects="source", to_project="")

    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_returns_zero_when_no_sources_after_filter(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_merge_projects

        mock_get.return_value.merge_projects.return_value = {
            "canonical": "target",
            "sources_merged": [],
            "observations_updated": 0,
            "sessions_updated": 0,
        }

        result = memory_merge_projects(from_projects="target", to_project="target")
        data = json.loads(result)

        assert data["canonical"] == "target"
        assert data["sources_merged"] == []
        assert data["observations_updated"] == 0

    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_merges_single_source(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_merge_projects

        mock_get.return_value.merge_projects.return_value = {
            "canonical": "new-project",
            "sources_merged": ["old-project"],
            "observations_updated": 5,
            "sessions_updated": 5,
        }

        result = memory_merge_projects(from_projects="old-project", to_project="new-project")
        data = json.loads(result)

        assert data["canonical"] == "new-project"
        assert data["sources_merged"] == ["old-project"]
        assert data["observations_updated"] == 5
        assert data["sessions_updated"] == 5

    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_merges_multiple_sources(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_merge_projects

        mock_get.return_value.merge_projects.return_value = {
            "canonical": "canonical",
            "sources_merged": ["proj-a", "proj-b", "proj-c"],
            "observations_updated": 9,
            "sessions_updated": 9,
        }

        result = memory_merge_projects(
            from_projects="proj-a, proj-b, proj-c", to_project="canonical"
        )
        data = json.loads(result)

        assert data["canonical"] == "canonical"
        assert data["sources_merged"] == ["proj-a", "proj-b", "proj-c"]
        assert data["observations_updated"] == 9

    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_skips_source_equal_to_canonical(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_merge_projects

        mock_get.return_value.merge_projects.return_value = {
            "canonical": "canonical",
            "sources_merged": ["other-project"],
            "observations_updated": 0,
            "sessions_updated": 0,
        }

        result = memory_merge_projects(
            from_projects="Canonical, other-project", to_project="canonical"
        )
        data = json.loads(result)

        assert "canonical" not in data["sources_merged"]
        assert data["sources_merged"] == ["other-project"]


class TestAuditFixes:
    def test_memory_save_empty_content_raises(self) -> None:
        from mcp.shared.exceptions import McpError

        from src.interfaces.mcp.tools import memory_save

        with pytest.raises(McpError):
            memory_save(content="")

    def test_memory_save_whitespace_content_raises(self) -> None:
        from mcp.shared.exceptions import McpError

        from src.interfaces.mcp.tools import memory_save

        with pytest.raises(McpError):
            memory_save(content="   ")

    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_save_prompt_happy_path(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_save_prompt

        mock_get.return_value.save_prompt.return_value = 42

        result = memory_save_prompt(content="What is the best approach for caching?")
        data = json.loads(result)

        assert data["id"] == 42
        assert data["status"] == "saved"
        mock_get.return_value.save_prompt.assert_called_once_with(
            content="What is the best approach for caching?",
            project=None,
            session_id=None,
            role=None,
            model=None,
            provider=None,
        )


# register_tools smoke test


class TestMemorySavePassthrough:
    """Verify MCP layer passes data through to service (redaction is in service layer)."""

    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_content_passed_to_service_unchanged(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_save

        obs = _make_observation(id="redact-1")
        mock_get.return_value.save.return_value = obs

        raw = "Use api_key=abcdefghijklmnopqrstuvwxyz for auth"
        memory_save(content=raw)

        call_args = mock_get.return_value.save.call_args
        assert call_args.kwargs["content"] == raw

    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_metadata_passed_to_service_unchanged(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_save

        obs = _make_observation(id="redact-3")
        mock_get.return_value.save.return_value = obs

        meta = {"password": "my_s3cret_p@ss"}
        memory_save(content="config note", metadata=meta)

        call_args = mock_get.return_value.save.call_args
        assert call_args.kwargs["metadata"] == meta


class TestMemoryUpdatePassthrough:
    """Verify MCP layer passes update data through to service (redaction is in service layer)."""

    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_content_passed_to_service_unchanged(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_update

        obs = _make_observation(id="upd-redact-1", content="updated")
        mock_get.return_value.update.return_value = obs

        raw = "secret=abc12345678901234567890"
        memory_update(id="upd-redact-1", content=raw)

        call_args = mock_get.return_value.update.call_args
        assert call_args.kwargs["content"] == raw

    @patch("src.interfaces.mcp.tools._get_memory_service")
    def test_metadata_passed_to_service_unchanged(self, mock_get: MagicMock) -> None:
        from src.interfaces.mcp.tools import memory_update

        obs = _make_observation(id="upd-meta-1")
        mock_get.return_value.update.return_value = obs

        meta = {"token": "ghp_ABCDEFGHIJKLMNOPQRST"}
        memory_update(id="upd-meta-1", metadata=meta)

        call_args = mock_get.return_value.update.call_args
        assert call_args.kwargs["metadata"] == meta


class TestRegisterTools:
    def test_registers_all_21_tools(self) -> None:
        from mcp.server.fastmcp import FastMCP

        from src.interfaces.mcp.tools import register_tools

        mcp = FastMCP("test")
        register_tools(mcp)

        registered_count = len(mcp._tool_manager._tools)
        assert registered_count == 21, f"Expected 21 tools, got {registered_count}"
