"""Unit tests for terminal spawner service."""

from unittest.mock import MagicMock, patch

import pytest

from src.application.services.terminal.terminal_spawner import (
    LINUX_TERMINALS,
    TerminalSpawner,
    TerminalSpawnerImpl,
)
from src.domain.entities.terminal import (
    PlatformType,
    TerminalConfig,
    TerminalResult,
)
from src.domain.exceptions.terminal import TerminalNotFoundError


class TestTerminalSpawnerImpl:
    def test_spawn_macos(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Terminal opened",
                strip=lambda: "Terminal opened",
            )

            config = TerminalConfig(terminal=None, platform=PlatformType.DARWIN)
            spawner = TerminalSpawnerImpl()

            result = spawner.spawn("echo hello", config)

            assert result.success is True
            assert result.exit_code == 0
            mock_run.assert_called_once()

    def test_spawn_windows(self) -> None:
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock()

            config = TerminalConfig(terminal=None, platform=PlatformType.WINDOWS)
            spawner = TerminalSpawnerImpl()

            result = spawner.spawn("dir", config)

            assert result.success is True
            assert result.exit_code == 0
            assert "Windows" in result.output
            mock_popen.assert_called_once()

    @patch("shutil.which")
    def test_spawn_linux_with_gnome_terminal(self, mock_which: MagicMock) -> None:
        def get_terminal(term: str) -> str | None:
            return "gnome-terminal" if term == "gnome-terminal" else None

        mock_which.side_effect = get_terminal

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock()

            config = TerminalConfig(terminal=None, platform=PlatformType.LINUX)
            spawner = TerminalSpawnerImpl()

            result = spawner.spawn("ls", config)

            assert result.success is True
            assert "gnome-terminal" in result.output
            mock_popen.assert_called_once()

    @patch("shutil.which")
    def test_spawn_linux_with_xterm(self, mock_which: MagicMock) -> None:
        def get_terminal(term: str) -> str | None:
            return "xterm" if term == "xterm" else None

        mock_which.side_effect = get_terminal

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock()

            config = TerminalConfig(terminal=None, platform=PlatformType.LINUX)
            spawner = TerminalSpawnerImpl()

            result = spawner.spawn("echo test", config)

            assert result.success is True
            assert "xterm" in result.output

    @patch("shutil.which")
    @patch("uuid.uuid4")
    def test_spawn_linux_fallback_to_tmux(
        self, mock_uuid: MagicMock, mock_which: MagicMock
    ) -> None:
        def which_side_effect(cmd: str) -> str | None:
            if cmd in LINUX_TERMINALS:
                return None
            if cmd == "tmux":
                return "/usr/bin/tmux"
            return None

        mock_which.side_effect = which_side_effect
        mock_uuid.return_value = MagicMock(__str__=lambda _: "test-uuid-1234")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            config = TerminalConfig(terminal=None, platform=PlatformType.LINUX)
            spawner = TerminalSpawnerImpl()

            result = spawner.spawn("ls", config)

            assert result.success is True
            assert "tmux" in result.output
            mock_run.assert_called_once()

    @patch("shutil.which")
    def test_spawn_linux_no_terminal_raises_error(self, mock_which: MagicMock) -> None:
        mock_which.return_value = None

        config = TerminalConfig(terminal=None, platform=PlatformType.LINUX)
        spawner = TerminalSpawnerImpl()

        with pytest.raises(TerminalNotFoundError):
            spawner.spawn("echo test", config)

    @patch("shutil.which")
    @patch("uuid.uuid4")
    def test_spawn_with_tmux_creates_session(
        self, mock_uuid: MagicMock, mock_which: MagicMock
    ) -> None:
        mock_which.return_value = "/usr/bin/tmux"
        mock_uuid.return_value = MagicMock(__str__=lambda _: "abc12345")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            spawner = TerminalSpawnerImpl()
            result = spawner._spawn_with_tmux("echo test")

            assert result.success is True
            assert "tmux" in result.output
            assert "abc12345" in result.output
            mock_run.assert_called_once()


class TestSanitization:
    def test_sanitize_windows_command_removes_dangerous_chars(self) -> None:
        spawner = TerminalSpawnerImpl()

        dangerous_command = "echo hello & dir & echo"
        sanitized = spawner._sanitize_windows_command(dangerous_command)

        assert "&" not in sanitized
        assert "|" not in sanitized
        assert ";" not in sanitized
        assert "hello" in sanitized
        assert "dir" in sanitized

    def test_sanitize_windows_command_preserves_safe_chars(self) -> None:
        spawner = TerminalSpawnerImpl()

        safe_command = "echo hello world"
        sanitized = spawner._sanitize_windows_command(safe_command)

        assert sanitized == safe_command


class TestTerminalSpawnerInterface:
    def test_spawn_returns_terminal_result(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="test",
                strip=lambda: "test",
            )

            config = TerminalConfig(terminal=None, platform=PlatformType.DARWIN)
            spawner = TerminalSpawnerImpl()

            result = spawner.spawn("echo test", config)

            assert isinstance(result, TerminalResult)
            assert hasattr(result, "success")
            assert hasattr(result, "output")
            assert hasattr(result, "exit_code")

    def test_spawner_is_abstract(self) -> None:
        assert hasattr(TerminalSpawner, "__abstractmethods__")


class TestLinuxTerminals:
    def test_linux_terminals_is_list(self) -> None:
        assert isinstance(LINUX_TERMINALS, list)
        assert all(isinstance(t, str) for t in LINUX_TERMINALS)
        assert len(LINUX_TERMINALS) > 0
