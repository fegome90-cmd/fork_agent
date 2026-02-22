"""Tests for CLI get command."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from src.domain.entities.observation import Observation


runner = CliRunner()


class TestGetCommand:
    """Tests for get command."""

    def test_get_observation_success(self) -> None:
        """Test getting an observation by ID."""
        from src.interfaces.cli.commands.get import app

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = Observation(
            id="test-id-123",
            timestamp=1000,
            content="test content",
            metadata={"key": "value"},
        )

        result = runner.invoke(app, ["test-id-123"], obj=mock_repo)

        assert result.exit_code == 0
        assert "test-id-123" in result.stdout
        assert "test content" in result.stdout

    def test_get_observation_not_found(self) -> None:
        """Test getting non-existent observation fails."""
        from src.interfaces.cli.commands.get import app

        mock_repo = MagicMock()
        mock_repo.get_by_id.side_effect = Exception("Not found")

        result = runner.invoke(app, ["nonexistent-id"], obj=mock_repo)

        assert result.exit_code == 1
        assert "not found" in result.output.lower()
