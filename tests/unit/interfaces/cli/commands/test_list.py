"""Tests for CLI list command."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from src.domain.entities.observation import Observation

runner = CliRunner()


class TestListCommand:
    """Tests for list command."""

    def test_list_returns_observations(self) -> None:
        from src.interfaces.cli.commands.list import app

        mock_memory = MagicMock()
        mock_memory.get_recent.return_value = [
            Observation(id="test-id-1", timestamp=1000, content="first"),
            Observation(id="test-id-2", timestamp=1001, content="second"),
        ]

        result = runner.invoke(app, obj=mock_memory)

        assert result.exit_code == 0
        assert "test-id" in result.stdout

    def test_list_empty(self) -> None:
        from src.interfaces.cli.commands.list import app

        mock_memory = MagicMock()
        mock_memory.get_recent.return_value = []

        result = runner.invoke(app, obj=mock_memory)

        assert result.exit_code == 0
        assert "No observations" in result.stdout

    @patch("src.interfaces.cli.commands.list.os.getcwd", return_value="/tmp/test-project")
    def test_list_with_limit(self, _mock_cwd: MagicMock) -> None:
        from src.interfaces.cli.commands.list import app

        mock_memory = MagicMock()
        mock_memory.get_recent.return_value = []

        result = runner.invoke(app, ["--limit", "5"], obj=mock_memory)

        assert result.exit_code == 0
        mock_memory.get_recent.assert_called_once_with(
            limit=5, offset=0, type=None, project="test-project"
        )

    def test_list_with_project(self) -> None:
        from src.interfaces.cli.commands.list import app

        mock_memory = MagicMock()
        mock_memory.get_recent.return_value = []

        result = runner.invoke(app, ["--project", "myproj"], obj=mock_memory)

        assert result.exit_code == 0
        mock_memory.get_recent.assert_called_once_with(
            limit=20, offset=0, type=None, project="myproj"
        )

    def test_list_with_project_short_flag(self) -> None:
        from src.interfaces.cli.commands.list import app

        mock_memory = MagicMock()
        mock_memory.get_recent.return_value = []

        result = runner.invoke(app, ["-p", "myproj"], obj=mock_memory)

        assert result.exit_code == 0
        mock_memory.get_recent.assert_called_once_with(
            limit=20, offset=0, type=None, project="myproj"
        )

    def test_list_with_type_and_project(self) -> None:
        from src.interfaces.cli.commands.list import app

        mock_memory = MagicMock()
        mock_memory.get_recent.return_value = []

        result = runner.invoke(app, ["--type", "decision", "-p", "myproj"], obj=mock_memory)

        assert result.exit_code == 0
        mock_memory.get_recent.assert_called_once_with(
            limit=20, offset=0, type="decision", project="myproj"
        )
