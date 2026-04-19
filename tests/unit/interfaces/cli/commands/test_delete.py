"""Tests for CLI delete command."""

from __future__ import annotations

from unittest.mock import MagicMock

from typer.testing import CliRunner

from src.application.exceptions import ObservationNotFoundError

runner = CliRunner()


class TestDeleteCommand:
    """Tests for delete command."""

    def test_delete_with_force(self) -> None:
        from src.interfaces.cli.commands.delete import app

        mock_memory = MagicMock()
        mock_memory.get_by_id.return_value = MagicMock(id="test-id-123")
        mock_memory.delete.return_value = None

        result = runner.invoke(app, ["test-id-123", "--force"], obj=mock_memory)

        assert result.exit_code == 0
        assert "Deleted" in result.stdout
        mock_memory.delete.assert_called_once_with("test-id-123")

    def test_delete_not_found(self) -> None:
        from src.interfaces.cli.commands.delete import app

        mock_memory = MagicMock()
        mock_memory.get_by_id.side_effect = ObservationNotFoundError("Not found")
        mock_memory._repository.get_all.return_value = []

        result = runner.invoke(app, ["nonexistent-id", "--force"], obj=mock_memory)

        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_delete_cancels_without_confirmation(self) -> None:
        from src.interfaces.cli.commands.delete import app

        mock_memory = MagicMock()

        result = runner.invoke(app, ["test-id-123"], input="n\n", obj=mock_memory)

        assert result.exit_code == 0
        assert "Cancelled" in result.stdout
        mock_memory.delete.assert_not_called()
