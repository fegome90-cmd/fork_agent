"""Unit tests for CLI interface."""

import sys
from unittest.mock import MagicMock, patch

from src.domain.entities.terminal import TerminalResult
from src.interfaces.cli.fork import create_fork_cli


class TestForkCLI:
    """Tests for fork CLI with Dependency Injection."""

    def test_cli_with_valid_command(self) -> None:
        """Test CLI with a valid command."""
        # Arrange
        mock_result = TerminalResult(success=True, output="test output", exit_code=0)
        mock_fork = MagicMock(return_value=mock_result)
        cli = create_fork_cli(mock_fork)

        # Act
        with patch.object(sys, "argv", ["fork", "echo", "hello"]):
            exit_code = cli()

        # Assert
        mock_fork.assert_called_once_with("echo hello")
        assert exit_code == 0

    def test_cli_without_command(self) -> None:
        """Test CLI without command prints usage."""
        # Arrange
        mock_fork = MagicMock()
        cli = create_fork_cli(mock_fork)

        # Act
        with patch.object(sys, "argv", ["fork"]), patch("builtins.print") as mock_print:
            exit_code = cli()

        # Assert
        mock_print.assert_called_once_with("Uso: fork <comando>")
        assert exit_code == 1
        mock_fork.assert_not_called()

    def test_cli_with_failing_command(self) -> None:
        """Test CLI with a failing command."""
        # Arrange
        mock_result = TerminalResult(success=False, output="error", exit_code=1)
        mock_fork = MagicMock(return_value=mock_result)
        cli = create_fork_cli(mock_fork)

        # Act
        with (
            patch.object(sys, "argv", ["fork", "invalid"]),
            patch("builtins.print") as mock_print,
        ):
            exit_code = cli()

        # Assert
        mock_print.assert_called_once_with("error")
        assert exit_code == 1

    def test_cli_with_exception(self) -> None:
        """Test CLI handles exceptions gracefully."""
        # Arrange
        mock_fork = MagicMock(side_effect=Exception("Test error"))
        cli = create_fork_cli(mock_fork)

        # Act
        with (
            patch.object(sys, "argv", ["fork", "test"]),
            patch("builtins.print") as mock_print,
        ):
            exit_code = cli()

        # Assert
        mock_print.assert_called_once()
        assert exit_code == 1

    def test_cli_with_multipart_command(self) -> None:
        """Test CLI with multi-word command."""
        # Arrange
        mock_result = TerminalResult(success=True, output="files", exit_code=0)
        mock_fork = MagicMock(return_value=mock_result)
        cli = create_fork_cli(mock_fork)

        # Act
        with patch.object(sys, "argv", ["fork", "ls", "-la"]):
            exit_code = cli()

        # Assert
        mock_fork.assert_called_once_with("ls -la")
        assert exit_code == 0


class TestCreateForkCLI:
    """Tests for create_fork_cli factory function."""

    def test_returns_callable(self) -> None:
        """Test that create_fork_cli returns a callable."""
        mock_fork = MagicMock()
        result = create_fork_cli(mock_fork)
        assert callable(result)
