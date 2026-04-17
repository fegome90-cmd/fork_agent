"""Tests for CLI context command."""

from __future__ import annotations

from unittest.mock import MagicMock

from typer.testing import CliRunner

from src.domain.entities.observation import Observation

runner = CliRunner()


class TestContextCommand:
    """Tests for context command."""

    def test_context_shows_observations(self) -> None:
        from src.interfaces.cli.commands.context import app

        mock_memory = MagicMock()
        mock_memory.get_recent.return_value = [
            Observation(id="test-id-1", timestamp=1000, content="first observation text"),
            Observation(id="test-id-2", timestamp=1001, content="second observation text"),
        ]

        result = runner.invoke(app, obj=mock_memory)

        assert result.exit_code == 0
        assert "test-id" in result.stdout
        assert "first observation" in result.stdout
        mock_memory.get_recent.assert_called_once_with(limit=5, type=None)

    def test_context_with_type_filter(self) -> None:
        from src.interfaces.cli.commands.context import app

        mock_memory = MagicMock()
        mock_memory.get_recent.return_value = [
            Observation(
                id="test-id-1",
                timestamp=1000,
                content="decision observation",
                type="decision",
            ),
        ]

        result = runner.invoke(app, ["--type", "decision"], obj=mock_memory)

        assert result.exit_code == 0
        assert "decision" in result.stdout
        mock_memory.get_recent.assert_called_once_with(limit=5, type="decision")

    def test_context_empty(self) -> None:
        from src.interfaces.cli.commands.context import app

        mock_memory = MagicMock()
        mock_memory.get_recent.return_value = []

        result = runner.invoke(app, obj=mock_memory)

        assert result.exit_code == 0
        assert "No context found" in result.stdout
