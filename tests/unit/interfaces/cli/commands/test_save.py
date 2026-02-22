"""Tests for CLI save command."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from src.domain.entities.observation import Observation


runner = CliRunner()


class TestSaveCommand:
    """Tests for save command."""

    def test_save_content_success(self) -> None:
        """Test saving content returns observation ID."""
        from src.interfaces.cli.commands.save import app

        mock_repo = MagicMock()
        mock_repo.create.return_value = None

        result = runner.invoke(app, ["test content"], obj=mock_repo)

        assert result.exit_code == 0
        assert "Saved:" in result.stdout
        mock_repo.create.assert_called_once()

    def test_save_with_metadata_json(self) -> None:
        """Test saving content with valid JSON metadata."""
        from src.interfaces.cli.commands.save import app

        mock_repo = MagicMock()
        mock_repo.create.return_value = None

        result = runner.invoke(
            app,
            ["test content", "--metadata", '{"key": "value"}'],
            obj=mock_repo,
        )

        assert result.exit_code == 0
        mock_repo.create.assert_called_once()

    def test_save_invalid_metadata_json(self) -> None:
        """Test saving with invalid JSON metadata fails."""
        from src.interfaces.cli.commands.save import app

        mock_repo = MagicMock()

        result = runner.invoke(
            app,
            ["test content", "--metadata", "not json"],
            obj=mock_repo,
        )

        assert result.exit_code == 1
        assert "Invalid JSON" in result.output

    def test_save_empty_content_fails(self) -> None:
        """Test saving empty content fails."""
        from src.interfaces.cli.commands.save import app

        mock_repo = MagicMock()

        result = runner.invoke(app, [""], obj=mock_repo)

        assert result.exit_code == 1
