"""Tests for CLI delete command."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner


runner = CliRunner()


class TestDeleteCommand:
    """Tests for delete command."""

    def test_delete_with_force(self) -> None:
        """Test deleting with force flag skips confirmation."""
        from src.interfaces.cli.commands.delete import app

        mock_repo = MagicMock()
        mock_repo.delete.return_value = None

        result = runner.invoke(app, ["test-id-123", "--force"], obj=mock_repo)

        assert result.exit_code == 0
        assert "Deleted" in result.stdout
        mock_repo.delete.assert_called_once_with("test-id-123")

    def test_delete_not_found(self) -> None:
        """Test deleting non-existent observation fails."""
        from src.interfaces.cli.commands.delete import app

        mock_repo = MagicMock()
        mock_repo.delete.side_effect = Exception("Not found")

        result = runner.invoke(app, ["nonexistent-id", "--force"], obj=mock_repo)

        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_delete_cancels_without_confirmation(self) -> None:
        """Test delete cancels when user declines confirmation."""
        from src.interfaces.cli.commands.delete import app

        mock_repo = MagicMock()

        result = runner.invoke(app, ["test-id-123"], input="n\n", obj=mock_repo)

        assert result.exit_code == 0
        assert "Cancelled" in result.stdout
        mock_repo.delete.assert_not_called()
