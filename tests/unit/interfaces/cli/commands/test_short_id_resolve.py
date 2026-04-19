"""Tests for BUG-19: CLI update/delete short ID resolution."""

from __future__ import annotations

from unittest.mock import MagicMock

from typer.testing import CliRunner

from src.application.exceptions import ObservationNotFoundError
from src.domain.entities.observation import Observation

runner = CliRunner()


class TestBug19UpdateShortId:
    """BUG-19: update command should resolve short ID prefixes."""

    def test_update_with_short_id(self) -> None:
        from src.interfaces.cli.commands.update import app

        full_id = "abc12345-def6-7890-abcd-ef1234567890"
        mock_memory = MagicMock()
        mock_memory.get_by_id.side_effect = ObservationNotFoundError("not found")
        mock_memory.get_by_id_prefix.return_value = [
            Observation(id=full_id, timestamp=1000, content="original")
        ]
        mock_memory.update.return_value = Observation(
            id=full_id,
            timestamp=1000,
            content="updated via short ID",
            revision_count=2,
        )

        result = runner.invoke(
            app,
            [full_id[:8], "--content", "updated via short ID"],
            obj=mock_memory,
        )

        assert result.exit_code == 0
        assert "Updated:" in result.stdout
        mock_memory.update.assert_called_once()

    def test_update_ambiguous_short_id(self) -> None:
        from src.interfaces.cli.commands.update import app

        mock_memory = MagicMock()
        mock_memory.get_by_id.side_effect = ObservationNotFoundError("not found")
        mock_memory.get_by_id_prefix.return_value = [
            Observation(id="abc12345-def6-7890-abcd-ef1234567890", timestamp=1000, content="a"),
            Observation(id="abc12345-aaaa-7890-abcd-ef1234567890", timestamp=1000, content="b"),
        ]

        result = runner.invoke(
            app,
            ["abc12345", "--content", "updated"],
            obj=mock_memory,
        )

        assert result.exit_code == 1
        assert "Ambiguous" in result.output

    def test_update_not_found_short_id(self) -> None:
        from src.interfaces.cli.commands.update import app

        mock_memory = MagicMock()
        mock_memory.get_by_id.side_effect = ObservationNotFoundError("not found")
        mock_memory.get_by_id_prefix.return_value = []

        result = runner.invoke(
            app,
            ["nonexist", "--content", "updated"],
            obj=mock_memory,
        )

        assert result.exit_code == 1
        assert "not found" in result.output


class TestBug19DeleteShortId:
    """BUG-19: delete command should resolve short ID prefixes."""

    def test_delete_with_short_id(self) -> None:
        from src.interfaces.cli.commands.delete import app

        full_id = "abc12345-def6-7890-abcd-ef1234567890"
        mock_memory = MagicMock()
        mock_memory.get_by_id.side_effect = ObservationNotFoundError("not found")
        mock_memory.get_by_id_prefix.return_value = [
            Observation(id=full_id, timestamp=1000, content="to delete")
        ]
        mock_memory.delete.return_value = None

        result = runner.invoke(
            app,
            [full_id[:8], "--force"],
            obj=mock_memory,
        )

        assert result.exit_code == 0
        assert "Deleted:" in result.stdout
        mock_memory.delete.assert_called_once_with(full_id)

    def test_delete_ambiguous_short_id(self) -> None:
        from src.interfaces.cli.commands.delete import app

        mock_memory = MagicMock()
        mock_memory.get_by_id.side_effect = ObservationNotFoundError("not found")
        mock_memory.get_by_id_prefix.return_value = [
            Observation(id="abc12345-def6-7890-abcd-ef1234567890", timestamp=1000, content="a"),
            Observation(id="abc12345-aaaa-7890-abcd-ef1234567890", timestamp=1000, content="b"),
        ]

        result = runner.invoke(
            app,
            ["abc12345", "--force"],
            obj=mock_memory,
        )

        assert result.exit_code == 1
        assert "Ambiguous" in result.output
