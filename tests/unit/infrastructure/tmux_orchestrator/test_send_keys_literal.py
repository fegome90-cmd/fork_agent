"""Tests for REQ-8: -l flag on send-keys."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.infrastructure.tmux_orchestrator import TmuxOrchestrator


class TestSendKeysLiteral:
    """REQ-8: Command text SHALL be sent with -l (literal) flag."""

    @patch("src.infrastructure.tmux_orchestrator.subprocess.run")
    def test_command_sent_with_literal_flag(self, mock_run: MagicMock) -> None:
        """Text send SHALL include -l flag."""
        mock_run.return_value = MagicMock(returncode=0)
        orch = TmuxOrchestrator(safety_mode=False)
        orch._send_keys("session", 0, "echo hello")
        # Find the command send call — the one that contains the text payload
        for call in mock_run.call_args_list:
            cmd = call[0][0]
            if "echo hello" in cmd:
                assert "-l" in cmd, f"Expected -l flag in command text send, got: {cmd}"
                break
        else:
            pytest.fail("No call found with command text payload")

    @patch("src.infrastructure.tmux_orchestrator.subprocess.run")
    def test_special_chars_not_interpreted(self, mock_run: MagicMock) -> None:
        """Special chars like C-c SHALL NOT be interpreted as key bindings."""
        mock_run.return_value = MagicMock(returncode=0)
        orch = TmuxOrchestrator(safety_mode=False)
        orch._send_keys("session", 0, "echo 'C-c M-x'")
        # Find the literal text send call — the one with -l flag and the payload
        for call in mock_run.call_args_list:
            cmd = call[0][0]
            if "echo 'C-c M-x'" in cmd:
                assert "-l" in cmd, f"Expected -l flag for literal text send, got: {cmd}"
                break
        else:
            pytest.fail("No call found with command text payload")

    def test_safety_mode_returns_positive(self) -> None:
        """Safety mode still returns positive int without subprocess."""
        orch = TmuxOrchestrator(safety_mode=True)
        result = orch._send_keys("session", 0, "echo test")
        assert result > 0


# Pytest is imported lazily to avoid top-level dependency in test helpers
import pytest  # noqa: E402
