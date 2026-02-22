"""Tests for CLI search command."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from src.domain.entities.observation import Observation


runner = CliRunner()


class TestSearchCommand:
    """Tests for search command."""

    def test_search_returns_results(self) -> None:
        from src.interfaces.cli.commands.search import app

        mock_memory = MagicMock()
        mock_memory.search.return_value = [
            Observation(id="test-id-1", timestamp=1000, content="test content"),
            Observation(id="test-id-2", timestamp=1001, content="another test"),
        ]

        result = runner.invoke(app, ["test"], obj=mock_memory)

        assert result.exit_code == 0
        assert "test-id" in result.stdout
        mock_memory.search.assert_called_once_with(query="test", limit=None)

    def test_search_no_results(self) -> None:
        from src.interfaces.cli.commands.search import app

        mock_memory = MagicMock()
        mock_memory.search.return_value = []

        result = runner.invoke(app, ["nonexistent"], obj=mock_memory)

        assert result.exit_code == 0
        assert "No results" in result.stdout

    def test_search_with_limit(self) -> None:
        from src.interfaces.cli.commands.search import app

        mock_memory = MagicMock()
        mock_memory.search.return_value = []

        result = runner.invoke(app, ["test", "--limit", "5"], obj=mock_memory)

        assert result.exit_code == 0
        mock_memory.search.assert_called_once_with(query="test", limit=5)
