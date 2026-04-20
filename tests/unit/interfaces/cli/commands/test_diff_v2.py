"""Tests for CLI diff command — full feature set."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from src.application.services.diff_service import DiffEntry, DiffResult
from src.application.services.diff_formatter import DiffFormatter

runner = CliRunner()


def _make_diff_result(
    ref: str = "ref",
    target: str = "target",
    entries: tuple[DiffEntry, ...] = (),
    summary: dict[str, int] | None = None,
) -> DiffResult:
    return DiffResult(
        reference_label=ref,
        target_label=target,
        entries=entries,
        summary=summary or {"added": 0, "removed": 0, "modified": 0, "unchanged": 0},
    )


def _make_mock_memory_service() -> MagicMock:
    """Create a mock MemoryService with a _repository attribute."""
    mock_repo = MagicMock()
    mock_service = MagicMock()
    mock_service._repository = mock_repo
    return mock_service


def _mock_repo_for_id(obs_a, obs_b) -> MagicMock:
    """Create a mock repo that returns specific observations by ID."""
    mock_repo = MagicMock()
    mock_repo.get_by_id.side_effect = [obs_a, obs_b]
    return mock_repo


def _mock_repo_for_session(s1_obs: list, s2_obs: list) -> MagicMock:
    """Create a mock repo that returns observations by session."""
    mock_repo = MagicMock()
    mock_repo.get_by_session_id.side_effect = [s1_obs, s2_obs]
    return mock_repo


def _mock_repo_for_timestamp(before_obs: list, after_obs: list) -> MagicMock:
    """Create a mock repo that returns observations by timestamp range."""
    mock_repo = MagicMock()
    mock_repo.get_by_timestamp_range.side_effect = [before_obs, after_obs]
    return mock_repo


class TestDiffById:
    """Tests for diff by observation ID."""

    def test_diff_by_two_ids(self) -> None:
        from src.domain.entities.observation import Observation
        from src.interfaces.cli.commands.diff import app

        obs_a = Observation(id="o1", timestamp=1000, content="v1", topic_key="t")
        obs_b = Observation(id="o2", timestamp=2000, content="v2", topic_key="t")

        mock_repo = _mock_repo_for_id(obs_a, obs_b)
        mock_service = MagicMock()
        mock_service._repository = mock_repo

        result = runner.invoke(app, ["o1", "o2", "--project", ""], obj=mock_service)
        assert result.exit_code == 0
        assert "modified" in result.output.lower() or "[~]" in result.output

    def test_diff_by_id_json(self) -> None:
        from src.domain.entities.observation import Observation
        from src.interfaces.cli.commands.diff import app

        obs_a = Observation(id="o1", timestamp=1000, content="v1", topic_key="t")
        obs_b = Observation(id="o2", timestamp=2000, content="v2", topic_key="t")

        mock_repo = _mock_repo_for_id(obs_a, obs_b)
        mock_service = MagicMock()
        mock_service._repository = mock_repo

        result = runner.invoke(app, ["o1", "o2", "--format", "json", "--project", ""], obj=mock_service)
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["diffs"][0]["status"] == "modified"

    def test_diff_by_id_not_found(self) -> None:
        from src.application.exceptions import ObservationNotFoundError
        from src.interfaces.cli.commands.diff import app

        mock_repo = MagicMock()
        mock_repo.get_by_id.side_effect = ObservationNotFoundError("not found")
        mock_service = MagicMock()
        mock_service._repository = mock_repo

        result = runner.invoke(app, ["nonexistent", "o2", "--project", ""], obj=mock_service)
        assert result.exit_code == 1
        assert "Error" in result.output

    def test_diff_by_id_unchanged(self) -> None:
        from src.domain.entities.observation import Observation
        from src.interfaces.cli.commands.diff import app

        obs = Observation(id="o1", timestamp=1000, content="same", topic_key="t")

        mock_repo = _mock_repo_for_id(obs, obs)
        mock_service = MagicMock()
        mock_service._repository = mock_repo

        result = runner.invoke(app, ["o1", "o2", "--format", "json", "--project", ""], obj=mock_service)
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["diffs"][0]["status"] == "unchanged"


class TestDiffBySession:
    """Tests for diff by session ID."""

    def test_diff_by_session(self) -> None:
        from src.domain.entities.observation import Observation
        from src.interfaces.cli.commands.diff import app

        s1_obs = [Observation(id="o1", timestamp=1000, content="v1", topic_key="t1", session_id="s1")]
        s2_obs = [Observation(id="o2", timestamp=2000, content="v2", topic_key="t1", session_id="s2")]

        mock_repo = _mock_repo_for_session(s1_obs, s2_obs)
        mock_service = MagicMock()
        mock_service._repository = mock_repo

        result = runner.invoke(app, ["--session", "s1", "--session", "s2", "--project", ""], obj=mock_service)
        assert result.exit_code == 0
        assert "[~]" in result.output or "modified" in result.output.lower()

    def test_diff_by_session_with_project(self) -> None:
        from src.domain.entities.observation import Observation
        from src.interfaces.cli.commands.diff import app

        s1_obs = [
            Observation(id="o1", timestamp=1000, content="a", topic_key="t1", project="alpha", session_id="s1"),
            Observation(id="o2", timestamp=1001, content="b", topic_key="t2", project="beta", session_id="s1"),
        ]
        s2_obs = [
            Observation(id="o3", timestamp=2000, content="c", topic_key="t1", project="alpha", session_id="s2"),
        ]

        mock_repo = _mock_repo_for_session(s1_obs, s2_obs)
        mock_service = MagicMock()
        mock_service._repository = mock_repo

        result = runner.invoke(app, ["--session", "s1", "--session", "s2", "--project", "alpha"], obj=mock_service)
        assert result.exit_code == 0
        # Only t1 (alpha) should appear, not t2 (beta)
        assert "t2" not in result.output

    def test_diff_by_session_empty_raises(self) -> None:
        from src.interfaces.cli.commands.diff import app

        mock_repo = _mock_repo_for_session([], [])
        mock_service = MagicMock()
        mock_service._repository = mock_repo

        result = runner.invoke(app, ["--session", "empty", "--session", "s2", "--project", ""], obj=mock_service)
        assert result.exit_code == 1
        assert "Error" in result.output

    def test_diff_by_session_json(self) -> None:
        from src.domain.entities.observation import Observation
        from src.interfaces.cli.commands.diff import app

        s1_obs = [Observation(id="o1", timestamp=1000, content="a", topic_key="t1", session_id="s1")]
        s2_obs = [Observation(id="o2", timestamp=2000, content="b", topic_key="t2", session_id="s2")]

        mock_repo = _mock_repo_for_session(s1_obs, s2_obs)
        mock_service = MagicMock()
        mock_service._repository = mock_repo

        result = runner.invoke(app, ["--session", "s1", "--session", "s2", "--format", "json", "--project", ""], obj=mock_service)
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert "diffs" in parsed

    def test_diff_by_session_one_session_only_raises(self) -> None:
        from src.interfaces.cli.commands.diff import app

        mock_service = MagicMock()
        mock_service._repository = MagicMock()

        result = runner.invoke(app, ["--session", "s1", "--project", ""], obj=mock_service)
        assert result.exit_code == 1
        assert "2" in result.output or "required" in result.output.lower()


class TestDiffByTimestamp:
    """Tests for diff by timestamp."""

    def test_diff_by_timestamp(self) -> None:
        from src.domain.entities.observation import Observation
        from src.interfaces.cli.commands.diff import app

        before_obs = [Observation(id="o1", timestamp=500, content="v1", topic_key="t")]
        after_obs = [Observation(id="o2", timestamp=1500, content="v2", topic_key="t")]

        mock_repo = _mock_repo_for_timestamp(before_obs, after_obs)
        mock_service = MagicMock()
        mock_service._repository = mock_repo

        result = runner.invoke(app, ["--before", "1000", "--after", "2000", "--project", ""], obj=mock_service)
        assert result.exit_code == 0
        assert "[~]" in result.output or "modified" in result.output.lower()

    def test_diff_by_timestamp_with_type(self) -> None:
        from src.domain.entities.observation import Observation
        from src.interfaces.cli.commands.diff import app

        before_obs = [
            Observation(id="o1", timestamp=500, content="a", topic_key="t1", type="decision"),
            Observation(id="o2", timestamp=600, content="b", topic_key="t2", type="bugfix"),
        ]
        after_obs = []

        mock_repo = _mock_repo_for_timestamp(before_obs, after_obs)
        mock_service = MagicMock()
        mock_service._repository = mock_repo

        result = runner.invoke(app, ["--before", "1000", "--after", "2000", "--type", "decision", "--project", ""], obj=mock_service)
        assert result.exit_code == 0
        # Only decision type should appear
        assert "t1" in result.output

    def test_diff_invalid_timestamp(self) -> None:
        from src.interfaces.cli.commands.diff import app

        mock_service = _make_mock_memory_service()

        result = runner.invoke(app, ["--before", "not-a-number", "--after", "2000"], obj=mock_service)
        assert result.exit_code == 1
        assert "Error" in result.output

    def test_diff_before_ge_after(self) -> None:
        from src.interfaces.cli.commands.diff import app

        mock_service = _make_mock_memory_service()

        result = runner.invoke(app, ["--before", "2000", "--after", "1000"], obj=mock_service)
        assert result.exit_code == 1

    def test_diff_unknown_format(self) -> None:
        from src.interfaces.cli.commands.diff import app

        mock_service = _make_mock_memory_service()

        result = runner.invoke(app, ["--before", "1000", "--after", "2000", "--format", "yaml"], obj=mock_service)
        assert result.exit_code == 1
        assert "format" in result.output.lower()

    def test_no_changes(self) -> None:
        from src.domain.entities.observation import Observation
        from src.interfaces.cli.commands.diff import app

        obs = Observation(id="o1", timestamp=500, content="same", topic_key="t")
        mock_repo = _mock_repo_for_timestamp([obs], [obs])
        mock_service = MagicMock()
        mock_service._repository = mock_repo

        result = runner.invoke(app, ["--before", "1000", "--after", "2000", "--project", ""], obj=mock_service)
        assert result.exit_code == 0
        assert "No differences found" in result.output


class TestDiffMutualExclusivity:
    """Tests for argument validation."""

    def test_no_arguments_shows_error(self) -> None:
        from src.interfaces.cli.commands.diff import app

        mock_service = _make_mock_memory_service()

        result = runner.invoke(app, [], obj=mock_service)
        assert result.exit_code != 0

    def test_cannot_mix_ids_and_session(self) -> None:
        from src.interfaces.cli.commands.diff import app

        mock_service = _make_mock_memory_service()

        result = runner.invoke(app, ["id1", "id2", "--session", "s1"], obj=mock_service)
        assert result.exit_code == 1

    def test_cannot_mix_ids_and_timestamps(self) -> None:
        from src.interfaces.cli.commands.diff import app

        mock_service = _make_mock_memory_service()

        result = runner.invoke(app, ["id1", "id2", "--before", "1000"], obj=mock_service)
        assert result.exit_code == 1

    def test_cannot_mix_session_and_timestamps(self) -> None:
        from src.interfaces.cli.commands.diff import app

        mock_service = _make_mock_memory_service()

        result = runner.invoke(app, ["--session", "s1", "--session", "s2", "--before", "1000"], obj=mock_service)
        assert result.exit_code == 1
