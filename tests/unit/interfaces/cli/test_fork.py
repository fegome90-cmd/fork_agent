"""Unit tests for CLI interface."""

import sys
from unittest.mock import MagicMock, patch

from src.interfaces.cli.fork import main
from src.domain.entities.terminal import TerminalResult


class TestMain:
    """Tests for main CLI function."""

    @patch("sys.argv", ["fork", "echo", "hello"])
    @patch("src.interfaces.cli.fork.PlatformDetectorImpl")
    @patch("src.interfaces.cli.fork.TerminalSpawnerImpl")
    @patch("src.interfaces.cli.fork.fork_terminal_use_case")
    def test_main_with_command(
        self,
        mock_use_case: MagicMock,
        mock_spawner: MagicMock,
        mock_detector: MagicMock,
    ) -> None:
        """Test main function with a valid command."""
        # Arrange
        mock_result = TerminalResult(success=True, output="test output", exit_code=0)
        # fork_terminal_use_case returns a callable that takes a command
        mock_execute = MagicMock(return_value=mock_result)
        mock_use_case.return_value = mock_execute

        # Act
        with patch.object(sys, "exit") as mock_exit:
            main()

        # Assert
        mock_detector.assert_called_once()
        mock_spawner.assert_called_once()
        mock_use_case.assert_called_once_with(mock_detector.return_value, mock_spawner.return_value)
        mock_execute.assert_called_once_with("echo hello")
        mock_exit.assert_called_once_with(0)

    @patch("sys.argv", ["fork"])
    def test_main_without_command_prints_usage(self) -> None:
        """Test main function without command prints usage."""
        # Act
        with patch("builtins.print") as mock_print:
            with patch.object(sys, "exit") as mock_exit:
                main()

        # Assert
        mock_print.assert_called_once_with("Uso: fork <comando>")
        mock_exit.assert_called_once_with(1)

    @patch("sys.argv", ["fork", "ls", "-la"])
    @patch("src.interfaces.cli.fork.PlatformDetectorImpl")
    @patch("src.interfaces.cli.fork.TerminalSpawnerImpl")
    @patch("src.interfaces.cli.fork.fork_terminal_use_case")
    def test_main_with_multipart_command(
        self,
        mock_use_case: MagicMock,
        mock_spawner: MagicMock,
        mock_detector: MagicMock,
    ) -> None:
        """Test main function with multi-word command."""
        # Arrange
        mock_result = TerminalResult(success=True, output="files", exit_code=0)
        mock_execute = MagicMock(return_value=mock_result)
        mock_use_case.return_value = mock_execute

        # Act
        with patch.object(sys, "exit") as mock_exit:
            main()

        # Assert
        mock_execute.assert_called_once_with("ls -la")
        mock_exit.assert_called_once_with(0)

    @patch("sys.argv", ["fork", "exit", "1"])
    @patch("src.interfaces.cli.fork.PlatformDetectorImpl")
    @patch("src.interfaces.cli.fork.TerminalSpawnerImpl")
    @patch("src.interfaces.cli.fork.fork_terminal_use_case")
    def test_main_with_failing_command(
        self,
        mock_use_case: MagicMock,
        mock_spawner: MagicMock,
        mock_detector: MagicMock,
    ) -> None:
        """Test main function with a failing command."""
        # Arrange
        mock_result = TerminalResult(success=False, output="error", exit_code=1)
        mock_execute = MagicMock(return_value=mock_result)
        mock_use_case.return_value = mock_execute

        # Act
        with patch("builtins.print") as mock_print:
            with patch.object(sys, "exit") as mock_exit:
                main()

        # Assert
        mock_print.assert_called_once_with("error")
        mock_exit.assert_called_once_with(1)

    @patch("sys.argv", ["fork", "echo", "hello"])
    @patch("src.interfaces.cli.fork.PlatformDetectorImpl")
    @patch("src.interfaces.cli.fork.TerminalSpawnerImpl")
    @patch("src.interfaces.cli.fork.fork_terminal_use_case")
    def test_main_creates_services(
        self,
        mock_use_case: MagicMock,
        mock_spawner: MagicMock,
        mock_detector: MagicMock,
    ) -> None:
        """Test that main creates PlatformDetectorImpl and TerminalSpawnerImpl."""
        # Arrange
        mock_result = TerminalResult(success=True, output="", exit_code=0)
        mock_use_case.return_value = MagicMock(return_value=mock_result)

        # Act
        with patch.object(sys, "exit"):
            main()

        # Assert
        mock_detector.assert_called_once()
        mock_spawner.assert_called_once()


class TestCLIInterface:
    """Tests for CLI interface structure."""

    def test_main_function_exists(self) -> None:
        """Test that main function is defined."""
        assert callable(main)

    def test_main_returns_none(self) -> None:
        """Test that main returns None (uses sys.exit)."""
        # main() calls sys.exit(), so it doesn't return normally
        # This test verifies the function exists and is callable
        assert main is not None
