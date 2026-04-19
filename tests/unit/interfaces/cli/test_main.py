"""Tests for CLI main.py - entry point and command registration."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from src.interfaces.cli import main
from src.infrastructure.persistence.container import get_default_db_path

runner = CliRunner()


class TestMainApp:
    def test_app_exists(self) -> None:
        assert main.app is not None

    def test_app_name(self) -> None:
        assert main.app.info.name == "memory"

    def test_app_help(self) -> None:
        help_text = main.app.info.help or ""
        assert "Manage agent memory observations" in help_text

    def test_commands_registered(self) -> None:
        commands = list(main.app.registered_commands)
        command_names = [cmd.name for cmd in commands]
        assert "save" in command_names
        assert "search" in command_names
        assert "list" in command_names
        assert "get" in command_names
        assert "delete" in command_names


class TestMainCallback:
    def test_callback_sets_memory_service(self) -> None:
        with patch("src.interfaces.cli.main.get_memory_service") as mock_get_service:
            mock_service = MagicMock()
            mock_get_service.return_value = mock_service

            @main.app.command()
            def test_cmd(ctx: main.typer.Context) -> None:
                assert ctx.obj is mock_service

            runner.invoke(main.app, ["test-cmd"])

    def test_callback_with_custom_db_path(self) -> None:
        with patch("src.interfaces.cli.main.get_memory_service") as mock_get_service:
            mock_service = MagicMock()
            mock_get_service.return_value = mock_service

            @main.app.command()
            def test_cmd(ctx: main.typer.Context) -> None:
                pass

            runner.invoke(main.app, ["--db", "custom/path.db", "test-cmd"])

            mock_get_service.assert_called_once_with(Path("custom/path.db"))

    def test_callback_with_db_option_short(self) -> None:
        with patch("src.interfaces.cli.main.get_memory_service") as mock_get_service:
            mock_service = MagicMock()
            mock_get_service.return_value = mock_service

            @main.app.command()
            def test_cmd(ctx: main.typer.Context) -> None:
                pass

            runner.invoke(main.app, ["-d", "another/path.db", "test-cmd"])

            mock_get_service.assert_called_once_with(Path("another/path.db"))

    def test_callback_default_db_path(self) -> None:
        with patch("src.interfaces.cli.main.get_memory_service") as mock_get_service:
            mock_service = MagicMock()
            mock_get_service.return_value = mock_service

            @main.app.command()
            def test_cmd(ctx: main.typer.Context) -> None:
                pass

            runner.invoke(main.app, ["test-cmd"])

            mock_get_service.assert_called_once_with(get_default_db_path())


class TestMainHelp:
    def test_help_command(self) -> None:
        result = runner.invoke(main.app, ["--help"])
        assert result.exit_code == 0
        assert "memory" in result.output.lower()

    def test_help_shows_db_option(self) -> None:
        result = runner.invoke(main.app, ["--help"])
        assert result.exit_code == 0
        assert "--db" in result.output or "-d" in result.output


class TestMainDirectExecution:
    def test_main_can_be_imported(self) -> None:
        assert main.app is not None

    def test_app_info_not_none(self) -> None:
        assert main.app.info is not None
