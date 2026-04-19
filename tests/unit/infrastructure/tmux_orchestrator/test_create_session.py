"""Tests for REQ-5 (idempotent create) and REQ-9 (history-limit)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from src.infrastructure.tmux_orchestrator import TmuxOrchestrator


class TestCreateSessionIdempotent:
    """REQ-5: create_session SHALL be idempotent using -A flag."""

    @patch("src.infrastructure.tmux_orchestrator.subprocess.run")
    def test_new_session_created(self, mock_run: MagicMock) -> None:
        """New session creation with -A flag succeeds."""
        mock_run.return_value = MagicMock(returncode=0)
        orch = TmuxOrchestrator(safety_mode=False)
        result = orch.create_session("test-session")
        assert result is True
        cmd = mock_run.call_args_list[0][0][0]
        assert "-A" in cmd
        assert "-s" in cmd
        assert "test-session" in cmd

    @patch("src.infrastructure.tmux_orchestrator.subprocess.run")
    def test_existing_session_returns_true(self, mock_run: MagicMock) -> None:
        """Existing session with -A flag returns True (attaches)."""
        mock_run.return_value = MagicMock(returncode=0)
        orch = TmuxOrchestrator(safety_mode=False)
        result = orch.create_session("existing-session")
        assert result is True

    @patch("src.infrastructure.tmux_orchestrator.subprocess.run")
    def test_timeout_returns_false(self, mock_run: MagicMock) -> None:
        """Timeout returns False."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="tmux", timeout=10)
        orch = TmuxOrchestrator(safety_mode=False)
        result = orch.create_session("timeout-session")
        assert result is False

    @patch("src.infrastructure.tmux_orchestrator.subprocess.run")
    def test_working_dir_preserved(self, mock_run: MagicMock) -> None:
        """Working directory is passed as -c flag."""
        mock_run.return_value = MagicMock(returncode=0)
        orch = TmuxOrchestrator(safety_mode=False)
        orch.create_session("test-session", working_dir=Path("/tmp/work"))
        cmd = mock_run.call_args_list[0][0][0]
        assert "-c" in cmd

    @patch("src.infrastructure.tmux_orchestrator.subprocess.run")
    def test_session_name_sanitized(self, mock_run: MagicMock) -> None:
        """Session name is sanitized before passing to tmux."""
        mock_run.return_value = MagicMock(returncode=0)
        orch = TmuxOrchestrator(safety_mode=False)
        orch.create_session("agent.type:v2")
        cmd = mock_run.call_args_list[0][0][0]
        # Should be sanitized: agent.type:v2 -> agent-type-v2
        assert "agent-type-v2" in cmd
        assert "agent.type:v2" not in cmd


class TestHistoryLimit:
    """REQ-9: history-limit SHALL be set after session creation."""

    @patch("src.infrastructure.tmux_orchestrator.subprocess.run")
    def test_history_limit_set_after_success(self, mock_run: MagicMock) -> None:
        """set-option history-limit 10000 called after successful creation."""
        mock_run.return_value = MagicMock(returncode=0)
        orch = TmuxOrchestrator(safety_mode=False)
        orch.create_session("test-session")
        # Second call should be set-option
        calls = mock_run.call_args_list
        assert len(calls) >= 2
        history_cmd = calls[1][0][0]
        assert "set-option" in history_cmd
        assert "history-limit" in history_cmd
        assert "10000" in history_cmd

    @patch("src.infrastructure.tmux_orchestrator.subprocess.run")
    def test_history_limit_failure_non_fatal(self, mock_run: MagicMock) -> None:
        """History-limit failure does not fail create_session."""
        import subprocess

        mock_run.side_effect = [
            MagicMock(returncode=0),  # create_session succeeds
            subprocess.TimeoutExpired(cmd="tmux", timeout=5),  # set-option fails
        ]
        orch = TmuxOrchestrator(safety_mode=False)
        result = orch.create_session("test-session")
        assert result is True

    @patch("src.infrastructure.tmux_orchestrator.subprocess.run")
    def test_history_limit_not_called_on_creation_failure(self, mock_run: MagicMock) -> None:
        """History-limit not attempted if session creation fails."""
        mock_run.return_value = MagicMock(returncode=1)  # creation fails
        orch = TmuxOrchestrator(safety_mode=False)
        result = orch.create_session("test-session")
        assert result is False
        # Only one call (the failed create), no set-option
        assert mock_run.call_count == 1
