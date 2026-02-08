"""Unit tests for application use cases."""

from unittest.mock import MagicMock

from src.application.use_cases.fork_terminal import (
    fork_terminal_use_case,
    create_fork_terminal_use_case,
)
from src.domain.entities.terminal import (
    TerminalConfig,
    TerminalResult,
    PlatformType,
)
from src.application.services.terminal.platform_detector import PlatformDetector
from src.application.services.terminal.terminal_spawner import TerminalSpawner


class TestForkTerminalUseCase:
    """Tests for fork_terminal_use_case function."""

    def test_fork_terminal_success_macos(self) -> None:
        """Test successful terminal fork on macOS."""
        # Arrange
        mock_detector = MagicMock(spec=PlatformDetector)
        mock_detector.detect.return_value = PlatformType.DARWIN

        mock_spawner = MagicMock(spec=TerminalSpawner)
        mock_result = TerminalResult(success=True, output="Done", exit_code=0)
        mock_spawner.spawn.return_value = mock_result

        # Act
        fork_terminal = fork_terminal_use_case(mock_detector, mock_spawner)
        result = fork_terminal("echo hello")

        # Assert
        mock_detector.detect.assert_called_once()
        mock_spawner.spawn.assert_called_once()
        assert result.success is True
        assert result.output == "Done"
        assert result.exit_code == 0

    def test_fork_terminal_success_linux(self) -> None:
        """Test successful terminal fork on Linux."""
        # Arrange
        mock_detector = MagicMock(spec=PlatformDetector)
        mock_detector.detect.return_value = PlatformType.LINUX

        mock_spawner = MagicMock(spec=TerminalSpawner)
        mock_result = TerminalResult(success=True, output="Linux terminal", exit_code=0)
        mock_spawner.spawn.return_value = mock_result

        # Act
        fork_terminal = fork_terminal_use_case(mock_detector, mock_spawner)
        result = fork_terminal("ls -la")

        # Assert
        mock_detector.detect.assert_called_once()
        mock_spawner.spawn.assert_called_once()
        call_args = mock_spawner.spawn.call_args
        config: TerminalConfig = call_args[0][1]
        assert config.platform == PlatformType.LINUX

    def test_fork_terminal_success_windows(self) -> None:
        """Test successful terminal fork on Windows."""
        # Arrange
        mock_detector = MagicMock(spec=PlatformDetector)
        mock_detector.detect.return_value = PlatformType.WINDOWS

        mock_spawner = MagicMock(spec=TerminalSpawner)
        mock_result = TerminalResult(success=True, output="Done", exit_code=0)
        mock_spawner.spawn.return_value = mock_result

        # Act
        fork_terminal = fork_terminal_use_case(mock_detector, mock_spawner)
        result = fork_terminal("dir")

        # Assert
        mock_detector.detect.assert_called_once()
        mock_spawner.spawn.assert_called_once()
        call_args = mock_spawner.spawn.call_args
        config: TerminalConfig = call_args[0][1]
        assert config.platform == PlatformType.WINDOWS

    def test_fork_terminal_failure(self) -> None:
        """Test terminal fork that fails."""
        # Arrange
        mock_detector = MagicMock(spec=PlatformDetector)
        mock_detector.detect.return_value = PlatformType.DARWIN

        mock_spawner = MagicMock(spec=TerminalSpawner)
        mock_result = TerminalResult(success=False, output="Error", exit_code=1)
        mock_spawner.spawn.return_value = mock_result

        # Act
        fork_terminal = fork_terminal_use_case(mock_detector, mock_spawner)
        result = fork_terminal("invalid_command")

        # Assert
        assert result.success is False
        assert result.exit_code == 1

    def test_fork_terminal_passes_command(self) -> None:
        """Test that command is passed correctly to spawner."""
        # Arrange
        mock_detector = MagicMock(spec=PlatformDetector)
        mock_detector.detect.return_value = PlatformType.LINUX

        mock_spawner = MagicMock(spec=TerminalSpawner)
        mock_spawner.spawn.return_value = TerminalResult(
            success=True, output="", exit_code=0
        )

        # Act
        fork_terminal = fork_terminal_use_case(mock_detector, mock_spawner)
        fork_terminal("specific_command arg1 arg2")

        # Assert
        call_args = mock_spawner.spawn.call_args
        command_passed = call_args[0][0]
        assert command_passed == "specific_command arg1 arg2"


class TestCreateForkTerminalUseCase:
    """Tests for create_fork_terminal_use_case factory function."""

    def test_create_fork_terminal_use_case(self) -> None:
        """Test creating use case with pure functions."""
        # Arrange
        def mock_detect_platform() -> PlatformType:
            return PlatformType.DARWIN

        def mock_spawn_terminal(command: str) -> TerminalResult:
            return TerminalResult(success=True, output="spawned", exit_code=0)

        # Act
        execute = create_fork_terminal_use_case(mock_detect_platform, mock_spawn_terminal)
        result = execute("test command")

        # Assert
        assert result.success is True
        assert result.output == "spawned"

    def test_create_fork_terminal_with_failure(self) -> None:
        """Test use case with function that returns failure."""
        # Arrange
        def mock_detect_platform() -> PlatformType:
            return PlatformType.WINDOWS

        def mock_spawn_terminal(command: str) -> TerminalResult:
            return TerminalResult(success=False, output="failed", exit_code=127)

        # Act
        execute = create_fork_terminal_use_case(mock_detect_platform, mock_spawn_terminal)
        result = execute("exit 127")

        # Assert
        assert result.success is False
        assert result.exit_code == 127

    def test_create_fork_terminal_config_created_correctly(self) -> None:
        """Test that config is created with None terminal."""
        # Arrange
        platform_detected: PlatformType | None = None

        def mock_detect_platform() -> PlatformType:
            nonlocal platform_detected
            platform_detected = PlatformType.LINUX
            return PlatformType.LINUX

        def mock_spawn_terminal(command: str) -> TerminalResult:
            return TerminalResult(success=True, output="ok", exit_code=0)

        # Act
        execute = create_fork_terminal_use_case(mock_detect_platform, mock_spawn_terminal)
        execute("echo test")

        # Assert
        assert platform_detected == PlatformType.LINUX
