"""Unit tests for compact CLI commands.

Tests are isolated from the broken session.py import chain by
patching at the function level rather than importing session_app.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

runner = CliRunner()


@dataclass(frozen=True)
class FakeObservation:
    """Minimal observation stand-in for CLI tests."""
    id: str
    timestamp: int
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


def _make_memory_service(
    save_return: FakeObservation | None = None,
    recent_return: list[FakeObservation] | None = None,
    search_return: list[FakeObservation] | None = None,
) -> MagicMock:
    """Build a mock MemoryService with sensible defaults."""
    mock = MagicMock()
    mock.save.return_value = save_return or FakeObservation(
        id="obs-123", timestamp=1000000, content="saved"
    )
    mock.get_recent.return_value = recent_return or []
    mock.search.return_value = search_return if search_return is not None else []
    return mock


class TestSaveSummary:
    """Tests for compact save-summary command."""

    def test_save_summary_basic(self) -> None:
        from src.interfaces.cli.commands.compact import app

        mock_memory = _make_memory_service()
        result = runner.invoke(
            app,
            ["save-summary", "--goal", "Build feature"],
            obj=mock_memory,
        )

        assert result.exit_code == 0
        assert "Session summary saved" in result.stdout
        mock_memory.save.assert_called_once()
        call_kwargs = mock_memory.save.call_args
        meta = call_kwargs.kwargs.get("metadata") or call_kwargs[1].get("metadata")
        assert meta["type"] == "session-summary"
        assert meta["topic_key"] == "compact/session-summary"
        assert meta["structured"]["goal"] == "Build feature"

    def test_save_summary_with_all_options(self) -> None:
        from src.interfaces.cli.commands.compact import app

        mock_memory = _make_memory_service()
        result = runner.invoke(
            app,
            [
                "save-summary",
                "--goal", "Refactor DB",
                "--instructions", "Use clean architecture",
                "--discoveries", "bug in repo, slow query",
                "--accomplished", "Migrated schema",
                "--next-steps", "Add indexes,Run benchmarks",
                "--files", "repo.py,models.py",
                "--project", "myapp",
            ],
            obj=mock_memory,
        )

        assert result.exit_code == 0
        call_kwargs = mock_memory.save.call_args
        meta = call_kwargs.kwargs.get("metadata") or call_kwargs[1].get("metadata")
        structured = meta["structured"]
        assert structured["discoveries"] == ["bug in repo", "slow query"]
        assert structured["next_steps"] == ["Add indexes", "Run benchmarks"]
        assert structured["files"] == ["repo.py", "models.py"]
        assert meta["project"] == "myapp"

    def test_save_summary_project_auto_detected(self) -> None:
        from src.interfaces.cli.commands.compact import app

        mock_memory = _make_memory_service()
        with patch("src.interfaces.cli.commands.compact.Path") as mock_path_cls:
            mock_cwd = MagicMock()
            mock_cwd.name = "auto-project"
            mock_path_cls.return_value = mock_cwd

            result = runner.invoke(
                app,
                ["save-summary", "--goal", "Auto detect"],
                obj=mock_memory,
            )

        assert result.exit_code == 0
        call_kwargs = mock_memory.save.call_args
        meta = call_kwargs.kwargs.get("metadata") or call_kwargs[1].get("metadata")
        assert meta["project"] == "auto-project"


class TestRecover:
    """Tests for compact recover command."""

    def test_recover_no_summaries(self) -> None:
        from src.interfaces.cli.commands.compact import app

        mock_memory = _make_memory_service(recent_return=[], search_return=[])
        result = runner.invoke(
            app,
            ["recover"],
            obj=mock_memory,
        )

        assert result.exit_code == 0
        assert "No session summaries" in result.stdout

    def test_recover_finds_summaries_via_search(self) -> None:
        from src.interfaces.cli.commands.compact import app

        summary_obs = FakeObservation(
            id="sum-001",
            timestamp=1000000,
            content="Session Summary",
            metadata={
                "type": "session-summary",
                "topic_key": "compact/session-summary",
                "structured": {
                    "goal": "Fix auth",
                    "accomplished": "Fixed login flow",
                    "next_steps": ["Write tests"],
                },
            },
        )
        regular_obs = FakeObservation(
            id="obs-001",
            timestamp=1001000,
            content="Found a bug in the token refresh logic",
        )
        mock_memory = _make_memory_service(
            recent_return=[regular_obs],
            search_return=[summary_obs],
        )

        result = runner.invoke(
            app,
            ["recover", "--summary-limit", "3", "--obs-limit", "10"],
            obj=mock_memory,
        )

        assert result.exit_code == 0
        assert "Session Summaries" in result.stdout
        assert "Fix auth" in result.stdout
        assert "Observations" in result.stdout
        assert "token refresh" in result.stdout
        # Verify search was called for summaries
        mock_memory.search.assert_called()

    def test_recover_shows_artifacts_index(self) -> None:
        from src.interfaces.cli.commands.compact import app

        artifact_obs = FakeObservation(
            id="art-001",
            timestamp=1002000,
            content="Artifacts: plan.md, impl.md",
            metadata={
                "type": "artifacts-index",
                "structured": {"files": ["plan.md", "impl.md", "test_plan.md"]},
            },
        )
        # search is called twice: once for summaries, once for artifacts
        mock_memory = MagicMock()
        mock_memory.search.side_effect = [[], [artifact_obs]]
        mock_memory.get_recent.return_value = []

        result = runner.invoke(
            app,
            ["recover"],
            obj=mock_memory,
        )

        assert result.exit_code == 0
        assert "Artifacts Index" in result.stdout
        assert "plan.md" in result.stdout

    def test_recover_empty_no_crash(self) -> None:
        from src.interfaces.cli.commands.compact import app

        mock_memory = _make_memory_service(recent_return=[], search_return=[])
        result = runner.invoke(
            app,
            ["recover"],
            obj=mock_memory,
        )

        assert result.exit_code == 0
        assert "No session summaries" in result.stdout
        assert "No observations" in result.stdout

    def test_recover_with_project_filter(self) -> None:
        from src.interfaces.cli.commands.compact import app

        mock_memory = _make_memory_service(recent_return=[], search_return=[])
        result = runner.invoke(
            app,
            ["recover", "--project", "specific-proj"],
            obj=mock_memory,
        )

        assert result.exit_code == 0


class TestFileOps:
    """Tests for compact file-ops command."""

    def test_file_ops_saves_manifest(self) -> None:
        from src.interfaces.cli.commands.compact import app

        mock_memory = _make_memory_service()
        result = runner.invoke(
            app,
            [
                "file-ops",
                "--read", "a.py,b.py",
                "--written", "c.py",
                "--edited", "d.py",
            ],
            obj=mock_memory,
        )

        assert result.exit_code == 0
        assert "File operations saved" in result.stdout
        call_kwargs = mock_memory.save.call_args
        meta = call_kwargs.kwargs.get("metadata") or call_kwargs[1].get("metadata")
        assert meta["type"] == "file-ops"
        manifest = meta["structured"]["manifest"]
        assert manifest["read"] == ["a.py", "b.py"]
        assert manifest["written"] == ["c.py"]
        assert manifest["edited"] == ["d.py"]

    def test_file_ops_requires_at_least_one_flag(self) -> None:
        from src.interfaces.cli.commands.compact import app

        mock_memory = _make_memory_service()
        result = runner.invoke(
            app,
            ["file-ops"],
            obj=mock_memory,
        )

        assert result.exit_code == 1
        assert "At least one of" in result.output

    def test_file_ops_with_project(self) -> None:
        from src.interfaces.cli.commands.compact import app

        mock_memory = _make_memory_service()
        result = runner.invoke(
            app,
            ["file-ops", "--read", "x.py", "--project", "myproj"],
            obj=mock_memory,
        )

        assert result.exit_code == 0
        call_kwargs = mock_memory.save.call_args
        meta = call_kwargs.kwargs.get("metadata") or call_kwargs[1].get("metadata")
        assert meta["project"] == "myproj"
