"""Pytest configuration and fixtures."""

import shutil

import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "bughunt: bug detection tests for integration issues")
    config.addinivalue_line("markers", "integration: integration tests")
    config.addinivalue_line("markers", "requires_tmux: tests that require tmux runtime")


def tmux_available() -> bool:
    """Check if tmux is available and functional (TMUX env or tmux binary + can create session)."""
    import os
    import subprocess

    # If inside a tmux session, assume it works
    if "TMUX" in os.environ:
        return True

    # Check if tmux binary exists
    if shutil.which("tmux") is None:
        return False

    # Try to create a test session to verify tmux actually works
    try:
        result = subprocess.run(
            ["tmux", "new-session", "-d", "-s", "_pytest_check"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode == 0:
            # Cleanup test session
            subprocess.run(
                ["tmux", "kill-session", "-t", "_pytest_check"],
                capture_output=True,
                timeout=5,
            )
            return True
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    return False


@pytest.fixture
def skip_if_no_tmux():
    """Skip test if tmux is not available."""
    if not tmux_available():
        pytest.skip("tmux not available (TMUX env or tmux binary required)")


from src.domain.entities.terminal import PlatformType, TerminalConfig, TerminalResult  # noqa: E402


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
