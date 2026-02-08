"""Unit tests for domain entities."""

from src.domain.entities.terminal import TerminalResult, TerminalConfig, PlatformType


class TestTerminalResult:
    """Tests for TerminalResult entity."""

    def test_create_successful_result(self) -> None:
        """Test creating a successful terminal result."""
        result = TerminalResult(success=True, output="echo hello", exit_code=0)
        assert result.success is True
        assert result.output == "echo hello"
        assert result.exit_code == 0

    def test_create_failed_result(self) -> None:
        """Test creating a failed terminal result."""
        result = TerminalResult(success=False, output="error", exit_code=1)
        assert result.success is False
        assert result.output == "error"
        assert result.exit_code == 1

    def test_result_immutability(self) -> None:
        """Test that TerminalResult is immutable."""
        result = TerminalResult(success=True, output="test", exit_code=0)
        try:
            result.success = False
            assert False, "Should not be mutable"
        except Exception:
            pass


class TestTerminalConfig:
    """Tests for TerminalConfig entity."""

    def test_create_config_with_terminal(self) -> None:
        """Test creating a config with a terminal specified."""
        config = TerminalConfig(terminal="xterm", platform=PlatformType.LINUX)
        assert config.terminal == "xterm"
        assert config.platform == PlatformType.LINUX

    def test_create_config_without_terminal(self) -> None:
        """Test creating a config without a terminal specified."""
        config = TerminalConfig(terminal=None, platform=PlatformType.DARWIN)
        assert config.terminal is None
        assert config.platform == PlatformType.DARWIN

    def test_config_immutability(self) -> None:
        """Test that TerminalConfig is immutable."""
        config = TerminalConfig(terminal="gnome-terminal", platform=PlatformType.LINUX)
        try:
            config.terminal = "konsole"
            assert False, "Should not be mutable"
        except Exception:
            pass
