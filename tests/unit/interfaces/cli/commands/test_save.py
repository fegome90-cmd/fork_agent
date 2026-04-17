"""Tests for CLI save command."""

from __future__ import annotations

from unittest.mock import MagicMock

from typer.testing import CliRunner

from src.domain.entities.observation import Observation

runner = CliRunner()


class TestSaveCommand:
    """Tests for save command."""

    def test_save_content_success(self) -> None:
        from src.interfaces.cli.commands.save import app

        mock_memory = MagicMock()
        mock_memory.save.return_value = Observation(
            id="test-id-123",
            timestamp=1000,
            content="test content",
        )

        result = runner.invoke(app, ["test content"], obj=mock_memory)

        assert result.exit_code == 0
        assert "Saved:" in result.stdout
        mock_memory.save.assert_called_once_with(content="test content", metadata=None, topic_key=None, project=None, type=None)

    def test_save_with_metadata_json(self) -> None:
        from src.interfaces.cli.commands.save import app

        mock_memory = MagicMock()
        mock_memory.save.return_value = Observation(
            id="test-id-123",
            timestamp=1000,
            content="test content",
        )

        result = runner.invoke(
            app,
            ["test content", "--metadata", '{"key": "value"}'],
            obj=mock_memory,
        )

        assert result.exit_code == 0
        mock_memory.save.assert_called_once_with(content="test content", metadata={"key": "value"}, topic_key=None, project=None, type=None)

    def test_save_invalid_metadata_json(self) -> None:
        from src.interfaces.cli.commands.save import app

        mock_memory = MagicMock()

        result = runner.invoke(
            app,
            ["test content", "--metadata", "not json"],
            obj=mock_memory,
        )

        assert result.exit_code == 1
        assert "Invalid JSON" in result.output

    def test_save_empty_content_fails(self) -> None:
        from src.interfaces.cli.commands.save import app

        mock_memory = MagicMock()

        result = runner.invoke(app, [""], obj=mock_memory)

        assert result.exit_code == 1
