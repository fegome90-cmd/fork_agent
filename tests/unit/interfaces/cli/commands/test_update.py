"""Tests for CLI update command."""

from __future__ import annotations

from unittest.mock import MagicMock

from typer.testing import CliRunner

from src.domain.entities.observation import Observation

runner = CliRunner()


class TestUpdateCommand:
    """Tests for update command."""

    def test_update_content(self) -> None:
        from src.interfaces.cli.commands.update import app

        mock_memory = MagicMock()
        mock_memory.get_by_id.return_value = MagicMock(id="test-id-123")
        mock_memory.update.return_value = Observation(
            id="test-id-123",
            timestamp=1000,
            content="updated content",
            revision_count=2,
        )

        result = runner.invoke(
            app, ["test-id-123", "--content", "updated content"], obj=mock_memory
        )

        assert result.exit_code == 0
        assert "Updated:" in result.stdout
        mock_memory.update.assert_called_once_with(
            observation_id="test-id-123",
            content="updated content",
            metadata=None,
            type=None,
            topic_key=None,
            project=None,
        )

    def test_update_type(self) -> None:
        from src.interfaces.cli.commands.update import app

        mock_memory = MagicMock()
        mock_memory.get_by_id.return_value = MagicMock(id="test-id-123")
        mock_memory.update.return_value = Observation(
            id="test-id-123",
            timestamp=1000,
            content="original",
            type="bugfix",
            revision_count=2,
        )

        result = runner.invoke(app, ["test-id-123", "--type", "bugfix"], obj=mock_memory)

        assert result.exit_code == 0
        call_kwargs = mock_memory.update.call_args
        assert call_kwargs.kwargs["type"] == "bugfix"

    def test_update_topic_key(self) -> None:
        from src.interfaces.cli.commands.update import app

        mock_memory = MagicMock()
        mock_memory.get_by_id.return_value = MagicMock(id="test-id-123")
        mock_memory.update.return_value = Observation(
            id="test-id-123",
            timestamp=1000,
            content="original",
            topic_key="my-topic",
            revision_count=2,
        )

        result = runner.invoke(app, ["test-id-123", "--topic-key", "my-topic"], obj=mock_memory)

        assert result.exit_code == 0
        call_kwargs = mock_memory.update.call_args
        assert call_kwargs.kwargs["topic_key"] == "my-topic"

    def test_update_project(self) -> None:
        from src.interfaces.cli.commands.update import app

        mock_memory = MagicMock()
        mock_memory.get_by_id.return_value = MagicMock(id="test-id-123")
        mock_memory.update.return_value = Observation(
            id="test-id-123",
            timestamp=1000,
            content="original",
            project="my-project",
            revision_count=2,
        )

        result = runner.invoke(app, ["test-id-123", "--project", "my-project"], obj=mock_memory)

        assert result.exit_code == 0
        call_kwargs = mock_memory.update.call_args
        assert call_kwargs.kwargs["project"] == "my-project"

    def test_update_no_fields_exits(self) -> None:
        from src.interfaces.cli.commands.update import app

        mock_memory = MagicMock()

        result = runner.invoke(app, ["test-id-123"], obj=mock_memory)

        assert result.exit_code == 1
        assert "At least one" in result.output
        mock_memory.update.assert_not_called()
