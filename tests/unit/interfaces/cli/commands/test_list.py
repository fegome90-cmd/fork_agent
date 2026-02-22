"""Tests for CLI list command."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from src.domain.entities.observation import Observation


runner = CliRunner()


class TestListCommand:
    """Tests for list command."""

    def test_list_returns_observations(self) -> None:
        """Test list returns recent observations."""
        from src.interfaces.cli.commands.list import app

        mock_repo = MagicMock()
        mock_repo.get_all.return_value = [
            Observation(id="test-id-1", timestamp=1000, content="first"),
            Observation(id="test-id-2", timestamp=1001, content="second"),
        ]

        result = runner.invoke(app, obj=mock_repo)

        assert result.exit_code == 0
        assert "test-id" in result.stdout

    def test_list_empty(self) -> None:
        """Test list with no observations."""
        from src.interfaces.cli.commands.list import app

        mock_repo = MagicMock()
        mock_repo.get_all.return_value = []

        result = runner.invoke(app, obj=mock_repo)

        assert result.exit_code == 0
        assert "No observations" in result.stdout

    def test_list_with_limit(self) -> None:
        """Test list with limit parameter."""
        from src.interfaces.cli.commands.list import app

        mock_repo = MagicMock()
        mock_repo.get_all.return_value = []

        result = runner.invoke(app, ["--limit", "5"], obj=mock_repo)

        assert result.exit_code == 0
