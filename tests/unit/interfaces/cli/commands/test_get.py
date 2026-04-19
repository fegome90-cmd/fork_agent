"""Tests for CLI get command."""

from __future__ import annotations

from unittest.mock import MagicMock

from typer.testing import CliRunner

from src.domain.entities.observation import Observation

runner = CliRunner()


class TestGetCommand:
    """Tests for get command."""

    def test_get_observation_success(self) -> None:
        from src.interfaces.cli.commands.get import app

        mock_memory = MagicMock()
        mock_memory.get_by_id.return_value = Observation(
            id="test-id-123",
            timestamp=1000,
            content="test content",
            metadata={"key": "value"},
        )

        result = runner.invoke(app, ["test-id-123"], obj=mock_memory)

        assert result.exit_code == 0
        assert "test-id-123" in result.stdout
        assert "test content" in result.stdout

    def test_get_by_short_id(self) -> None:
        from src.interfaces.cli.commands.get import app

        full_id = "a1b2c3d4-5678-9abc-def0-123456789abc"
        mock_memory = MagicMock()
        mock_memory.get_by_id.side_effect = __import__(
            "src.application.exceptions", fromlist=["ObservationNotFoundError"]
        ).ObservationNotFoundError("Not found")
        mock_memory._repository.get_all.return_value = [
            Observation(id=full_id, timestamp=1000, content="found by short id"),
        ]

        result = runner.invoke(app, ["a1b2c3d4"], obj=mock_memory)

        assert result.exit_code == 0
        assert full_id in result.stdout
        assert "found by short id" in result.stdout

    def test_get_observation_not_found(self) -> None:
        from src.interfaces.cli.commands.get import app
        from src.application.exceptions import ObservationNotFoundError

        mock_memory = MagicMock()
        mock_memory.get_by_id.side_effect = ObservationNotFoundError("Not found")

        result = runner.invoke(app, ["nonexistent-id"], obj=mock_memory)

        assert result.exit_code == 1
        assert "not found" in result.output.lower()
