"""Unit tests for project CLI commands."""

from __future__ import annotations

from unittest.mock import MagicMock

from typer.testing import CliRunner

runner = CliRunner()


def _make_memory_service() -> MagicMock:
    """Build a mock MemoryService with sensible defaults."""
    mock = MagicMock()
    mock.merge_projects.return_value = {
        "canonical": "proj-a",
        "sources_merged": ["proj-b"],
        "observations_updated": 3,
        "sessions_updated": 0,
    }
    return mock


class TestProjectMerge:
    """Tests for project merge command."""

    def test_merge_projects_success(self) -> None:
        from src.interfaces.cli.commands.project import app

        mock_memory = _make_memory_service()
        # When a Typer has a single command, invoke without the command name
        result = runner.invoke(
            app,
            ["--from", "proj-b", "--to", "proj-a", "--force"],
            obj=mock_memory,
        )

        assert result.exit_code == 0
        assert "Merged 3 observations" in result.stdout
        assert "proj-a" in result.stdout
        mock_memory.merge_projects.assert_called_once_with("proj-b", "proj-a")

    def test_merge_dry_run(self) -> None:
        from src.interfaces.cli.commands.project import app

        mock_memory = _make_memory_service()
        result = runner.invoke(
            app,
            ["--from", "proj-b", "--to", "proj-a", "--dry-run"],
            obj=mock_memory,
        )

        assert result.exit_code == 0
        assert "DRY RUN" in result.stdout
        assert "proj-a" in result.stdout
        assert "Source projects" in result.stdout
        mock_memory.merge_projects.assert_not_called()

    def test_merge_requires_confirmation(self) -> None:
        from src.interfaces.cli.commands.project import app

        mock_memory = _make_memory_service()
        result = runner.invoke(
            app,
            ["--from", "proj-b", "--to", "proj-a"],
            input="n\n",
            obj=mock_memory,
        )

        assert result.exit_code == 1  # typer.Abort
        assert "Aborted" in result.stdout
        mock_memory.merge_projects.assert_not_called()

    def test_merge_confirmed_without_force(self) -> None:
        from src.interfaces.cli.commands.project import app

        mock_memory = _make_memory_service()
        result = runner.invoke(
            app,
            ["--from", "proj-b", "--to", "proj-a"],
            input="y\n",
            obj=mock_memory,
        )

        assert result.exit_code == 0
        assert "Merged" in result.stdout
        mock_memory.merge_projects.assert_called_once_with("proj-b", "proj-a")

    def test_merge_with_sessions_updated(self) -> None:
        from src.interfaces.cli.commands.project import app

        mock_memory = MagicMock()
        mock_memory.merge_projects.return_value = {
            "canonical": "proj-a",
            "sources_merged": ["proj-b", "proj-c"],
            "observations_updated": 5,
            "sessions_updated": 2,
        }

        result = runner.invoke(
            app,
            ["--from", "proj-b,proj-c", "--to", "proj-a", "--force"],
            obj=mock_memory,
        )

        assert result.exit_code == 0
        assert "Merged 5 observations" in result.stdout
        assert "Updated 2 sessions" in result.stdout
        assert "proj-b" in result.stdout
