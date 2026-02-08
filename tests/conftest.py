"""Pytest configuration and fixtures."""

import pytest
from src.domain.entities.terminal import TerminalConfig, TerminalResult, PlatformType


@pytest.fixture
def terminal_config_linux() -> TerminalConfig:
    """Fixture para configuración de terminal en Linux."""
    return TerminalConfig(terminal="xterm", platform=PlatformType.LINUX)


@pytest.fixture
def terminal_config_macos() -> TerminalConfig:
    """Fixture para configuración de terminal en macOS."""
    return TerminalConfig(terminal="Terminal", platform=PlatformType.DARWIN)


@pytest.fixture
def terminal_config_windows() -> TerminalConfig:
    """Fixture para configuración de terminal en Windows."""
    return TerminalConfig(terminal="cmd", platform=PlatformType.WINDOWS)


@pytest.fixture
def successful_result() -> TerminalResult:
    """Fixture para resultado exitoso."""
    return TerminalResult(success=True, output="Test output", exit_code=0)


@pytest.fixture
def failed_result() -> TerminalResult:
    """Fixture para resultado fallido."""
    return TerminalResult(success=False, output="Error occurred", exit_code=1)
