"""Tests for CLI search command."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from src.domain.entities.observation import Observation

runner = CliRunner()


def _mock_cwd(name: str = "test-project") -> str:
    """Return a patched getcwd that returns a Path with the given basename."""
    return name


class TestSearchCommand:
    """Tests for search command."""

    @patch("src.interfaces.cli.commands.search.os.getcwd", return_value="/tmp/test-project")
    def test_search_returns_results(self, _mock_cwd: MagicMock) -> None:
        from src.interfaces.cli.commands.search import app

        mock_memory = MagicMock()
        mock_memory.search.return_value = [
            Observation(id="test-id-1", timestamp=1000, content="test content"),
            Observation(id="test-id-2", timestamp=1001, content="another test"),
        ]

        result = runner.invoke(app, ["test"], obj=mock_memory)

        assert result.exit_code == 0
        assert "test-id" in result.stdout
        mock_memory.search.assert_called_once_with(query="test", limit=None, project="test-project")

    def test_search_no_results(self) -> None:
        from src.interfaces.cli.commands.search import app

        mock_memory = MagicMock()
        mock_memory.search.return_value = []

        result = runner.invoke(app, ["nonexistent"], obj=mock_memory)

        assert result.exit_code == 0
        assert "No results" in result.stdout

    @patch("src.interfaces.cli.commands.search.os.getcwd", return_value="/tmp/test-project")
    def test_search_with_limit(self, _mock_cwd: MagicMock) -> None:
        from src.interfaces.cli.commands.search import app

        mock_memory = MagicMock()
        mock_memory.search.return_value = []

        result = runner.invoke(app, ["test", "--limit", "5"], obj=mock_memory)

        assert result.exit_code == 0
        mock_memory.search.assert_called_once_with(query="test", limit=5, project="test-project")

    def test_search_with_project(self) -> None:
        from src.interfaces.cli.commands.search import app

        mock_memory = MagicMock()
        mock_memory.search.return_value = []

        result = runner.invoke(app, ["test", "-p", "myproj"], obj=mock_memory)

        assert result.exit_code == 0
        mock_memory.search.assert_called_once_with(query="test", limit=None, project="myproj")

    def test_search_with_limit_and_project(self) -> None:
        from src.interfaces.cli.commands.search import app

        mock_memory = MagicMock()
        mock_memory.search.return_value = []

        result = runner.invoke(
            app, ["test", "--limit", "3", "--project", "myproj"], obj=mock_memory
        )

        assert result.exit_code == 0
        mock_memory.search.assert_called_once_with(query="test", limit=3, project="myproj")
