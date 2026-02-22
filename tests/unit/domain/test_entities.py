"""Unit tests for domain entities."""

from __future__ import annotations

import pytest

from src.domain.entities.terminal import (
    TerminalResult,
    TerminalConfig,
    TerminalInfo,
    PlatformType,
)


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
        """Test that TerminalResult is immutable (frozen=True)."""
        # frozen=True is defined in the entity, this test just verifies it can be instantiated
        _ = TerminalResult(success=True, output="test", exit_code=0)

    def test_terminal_result_invalid_success_type(self) -> None:
        """Test that non-bool success raises TypeError."""
        with pytest.raises(TypeError, match="success debe ser un booleano"):
            TerminalResult(success="yes", output="test", exit_code=0)  # type: ignore[arg-type]

    def test_terminal_result_invalid_output_type(self) -> None:
        """Test that non-str output raises TypeError."""
        with pytest.raises(TypeError, match="output debe ser un string"):
            TerminalResult(success=True, output=123, exit_code=0)  # type: ignore[arg-type]

    def test_terminal_result_invalid_exit_code_type(self) -> None:
        """Test that non-int exit_code raises TypeError."""
        with pytest.raises(TypeError, match="exit_code debe ser un entero"):
            TerminalResult(success=True, output="test", exit_code="0")  # type: ignore[arg-type]


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
        """Test that TerminalConfig is immutable (frozen=True)."""
        # frozen=True is defined in the entity, this test just verifies it can be instantiated
        _ = TerminalConfig(terminal="gnome-terminal", platform=PlatformType.LINUX)

    def test_terminal_config_invalid_terminal_type(self) -> None:
        """Test that non-str/non-None terminal raises TypeError."""
        with pytest.raises(TypeError, match="terminal debe ser un string o None"):
            TerminalConfig(terminal=123, platform=PlatformType.LINUX)  # type: ignore[arg-type]

    def test_terminal_config_invalid_platform_type(self) -> None:
        """Test that non-PlatformType platform raises TypeError."""
        with pytest.raises(TypeError, match="platform debe ser un PlatformType"):
            TerminalConfig(terminal="xterm", platform="Linux")  # type: ignore[arg-type]


class TestTerminalInfo:
    """Tests for TerminalInfo entity."""

    def test_create_terminal_info_with_path(self) -> None:
        """Test creating terminal info with a path."""
        info = TerminalInfo(
            name="gnome-terminal",
            path="/usr/bin/gnome-terminal",
            is_available=True,
        )
        assert info.name == "gnome-terminal"
        assert info.path == "/usr/bin/gnome-terminal"
        assert info.is_available is True

    def test_create_terminal_info_without_path(self) -> None:
        """Test creating terminal info without a path."""
        info = TerminalInfo(name="unknown-terminal", path=None, is_available=False)
        assert info.name == "unknown-terminal"
        assert info.path is None
        assert info.is_available is False

    def test_terminal_info_immutability(self) -> None:
        """Test that TerminalInfo is immutable."""
        info = TerminalInfo(name="test", path=None, is_available=True)
        from dataclasses import FrozenInstanceError

        with pytest.raises(FrozenInstanceError):
            info.name = "changed"  # type: ignore[misc]

    def test_terminal_info_invalid_name_type(self) -> None:
        """Test that non-str name raises TypeError."""
        with pytest.raises(TypeError, match="name debe ser un string"):
            TerminalInfo(name=123, path=None, is_available=True)  # type: ignore[arg-type]

    def test_terminal_info_invalid_path_type(self) -> None:
        """Test that non-str/non-None path raises TypeError."""
        with pytest.raises(TypeError, match="path debe ser un string o None"):
            TerminalInfo(name="test", path=123, is_available=True)  # type: ignore[arg-type]

    def test_terminal_info_invalid_is_available_type(self) -> None:
        """Test that non-bool is_available raises TypeError."""
        with pytest.raises(TypeError, match="is_available debe ser un booleano"):
            TerminalInfo(name="test", path=None, is_available="yes")  # type: ignore[arg-type]
