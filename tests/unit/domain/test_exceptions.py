"""Unit tests for domain exceptions."""

import pytest

from src.domain.exceptions.terminal import (
    TerminalError,
    PlatformNotSupportedError,
    TerminalNotFoundError,
    CommandExecutionError,
)


class TestTerminalError:
    """Tests for TerminalError base exception."""

    def test_create_terminal_error_with_message(self) -> None:
        """Test creating a terminal error with just a message."""
        error = TerminalError("Test error message")
        assert error.message == "Test error message"
        assert error.details == {}
        assert str(error) == "Test error message"

    def test_create_terminal_error_with_message_and_details(self) -> None:
        """Test creating a terminal error with message and details."""
        details = {"key": "value", "extra": 123}
        error = TerminalError("Test error", details=details)
        assert error.message == "Test error"
        assert error.details == details

    def test_terminal_error_inheritance(self) -> None:
        """Test that TerminalError inherits from Exception."""
        error = TerminalError("Base error")
        assert isinstance(error, Exception)

    def test_terminal_error_details_default_empty(self) -> None:
        """Test that details default to empty dict when not provided."""
        error = TerminalError("Test")
        assert error.details == {}


class TestPlatformNotSupportedError:
    """Tests for PlatformNotSupportedError exception."""

    def test_create_platform_error(self) -> None:
        """Test creating a platform not supported error."""
        error = PlatformNotSupportedError("UnknownOS")
        assert error.message == "Plataforma 'UnknownOS' no está soportada"
        assert error.details["platform"] == "UnknownOS"
        assert isinstance(error, TerminalError)

    def test_platform_error_inheritance(self) -> None:
        """Test that PlatformNotSupportedError inherits from TerminalError."""
        error = PlatformNotSupportedError("TestOS")
        assert isinstance(error, TerminalError)
        assert isinstance(error, Exception)


class TestTerminalNotFoundError:
    """Tests for TerminalNotFoundError exception."""

    def test_create_terminal_not_found_error(self) -> None:
        """Test creating a terminal not found error."""
        terminals = ["gnome-terminal", "xterm", "konsole"]
        error = TerminalNotFoundError("Linux", terminals)
        assert error.message == "No se encontró emulador de terminal en Linux"
        assert error.details["platform"] == "Linux"
        assert error.details["terminals_tried"] == terminals

    def test_terminal_not_found_error_inheritance(self) -> None:
        """Test that TerminalNotFoundError inherits from TerminalError."""
        error = TerminalNotFoundError("Windows", ["cmd", "powershell"])
        assert isinstance(error, TerminalError)
        assert isinstance(error, Exception)

    def test_terminal_not_found_error_empty_terminals(self) -> None:
        """Test creating error with empty terminals list."""
        error = TerminalNotFoundError("Unknown", [])
        assert error.details["terminals_tried"] == []


class TestCommandExecutionError:
    """Tests for CommandExecutionError exception."""

    def test_create_command_execution_error(self) -> None:
        """Test creating a command execution error."""
        error = CommandExecutionError(
            command="rm -rf /",
            exit_code=1,
            output="Permission denied",
        )
        assert error.message == "Comando 'rm -rf /' falló con código 1"
        assert error.details["command"] == "rm -rf /"
        assert error.details["exit_code"] == 1
        assert error.details["output"] == "Permission denied"

    def test_command_execution_error_inheritance(self) -> None:
        """Test that CommandExecutionError inherits from TerminalError."""
        error = CommandExecutionError("ls", 2, "No such file")
        assert isinstance(error, TerminalError)
        assert isinstance(error, Exception)

    def test_command_execution_error_with_zero_exit_code(self) -> None:
        """Test creating error with exit code 0 (edge case)."""
        error = CommandExecutionError("echo test", 0, "test output")
        assert error.details["exit_code"] == 0
