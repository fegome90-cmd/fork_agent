"""Tests for send_command return type change (bool -> int)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.infrastructure.tmux_orchestrator import TmuxOrchestrator


class TestSendCommandReturnType:
    """send_command SHALL return int (0=fail, >0=success)."""

    @patch("src.infrastructure.tmux_orchestrator.subprocess.run")
    def test_success_returns_positive_int(self, mock_run: MagicMock) -> None:
        """Successful send returns positive int."""
        mock_run.return_value = MagicMock(returncode=0)
        orch = TmuxOrchestrator(safety_mode=False)
        result = orch.send_command("session", 0, "echo hello")
        assert isinstance(result, int)
        assert result > 0

    @patch("src.infrastructure.tmux_orchestrator.subprocess.run")
    def test_failure_returns_zero(self, mock_run: MagicMock) -> None:
        """Failed send returns 0."""
        mock_run.return_value = MagicMock(returncode=1)
        orch = TmuxOrchestrator(safety_mode=False)
        result = orch.send_command("session", 0, "echo hello")
        assert result == 0

    @patch("src.infrastructure.tmux_orchestrator.subprocess.run")
    def test_timeout_returns_zero(self, mock_run: MagicMock) -> None:
        """Timeout returns 0."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="tmux", timeout=5)
        orch = TmuxOrchestrator(safety_mode=False)
        result = orch.send_command("session", 0, "echo hello")
        assert result == 0

    def test_safety_mode_returns_positive(self) -> None:
        """Safety mode returns positive int (no subprocess call)."""
        orch = TmuxOrchestrator(safety_mode=True)
        result = orch.send_command("session", 0, "echo hello")
        assert isinstance(result, int)
        assert result > 0

    def test_empty_after_sanitize_returns_zero(self) -> None:
        """Empty text after sanitization returns 0."""
        orch = TmuxOrchestrator(safety_mode=False)
        result = orch.send_command("session", 0, "\x01\x02\x03")
        assert result == 0

    @patch("src.infrastructure.tmux_orchestrator.subprocess.run")
    def test_marker_counter_increments_on_success(self, mock_run: MagicMock) -> None:
        """Each successful call increments _marker_counter."""
        mock_run.return_value = MagicMock(returncode=0)
        orch = TmuxOrchestrator(safety_mode=False)
        r1 = orch.send_command("session", 0, "cmd1")
        r2 = orch.send_command("session", 0, "cmd2")
        assert r1 > 0
        assert r2 > 0
        assert r2 > r1  # counter increases

    def test_send_message_deprecated_returns_bool(self) -> None:
        """send_message (deprecated) still returns bool, wrapping _send_keys int."""
        import warnings

        orch = TmuxOrchestrator(safety_mode=True)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = orch.send_message("session", 0, "echo hello")
        assert isinstance(result, bool)
        assert result is True
