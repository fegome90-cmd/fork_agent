"""Tests for REQ-4: Agent idle detection."""
from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

from src.infrastructure.tmux_orchestrator import TmuxOrchestrator


class TestIsIdle:
    """REQ-4: is_idle SHALL detect idle shell via pane_current_command."""

    @patch("src.infrastructure.tmux_orchestrator.subprocess.run")
    def test_idle_shell_bash(self, mock_run: MagicMock) -> None:
        """Bash shell detected as idle."""
        mock_run.return_value = MagicMock(returncode=0, stdout="bash\n")
        orch = TmuxOrchestrator(safety_mode=False)
        assert orch.is_idle("session", 1) is True

    @patch("src.infrastructure.tmux_orchestrator.subprocess.run")
    def test_idle_shell_zsh(self, mock_run: MagicMock) -> None:
        """Zsh shell detected as idle."""
        mock_run.return_value = MagicMock(returncode=0, stdout="zsh\n")
        orch = TmuxOrchestrator(safety_mode=False)
        assert orch.is_idle("session", 1) is True

    @patch("src.infrastructure.tmux_orchestrator.subprocess.run")
    def test_idle_shell_fish(self, mock_run: MagicMock) -> None:
        """Fish shell detected as idle."""
        mock_run.return_value = MagicMock(returncode=0, stdout="fish\n")
        orch = TmuxOrchestrator(safety_mode=False)
        assert orch.is_idle("session", 1) is True

    @patch("src.infrastructure.tmux_orchestrator.subprocess.run")
    def test_idle_shell_sh(self, mock_run: MagicMock) -> None:
        """Plain sh detected as idle."""
        mock_run.return_value = MagicMock(returncode=0, stdout="sh\n")
        orch = TmuxOrchestrator(safety_mode=False)
        assert orch.is_idle("session", 1) is True

    @patch("src.infrastructure.tmux_orchestrator.subprocess.run")
    def test_active_process_returns_false(self, mock_run: MagicMock) -> None:
        """Running process (python, vim, etc) is NOT idle."""
        mock_run.return_value = MagicMock(returncode=0, stdout="python3\n")
        orch = TmuxOrchestrator(safety_mode=False)
        assert orch.is_idle("session", 1) is False

    @patch("src.infrastructure.tmux_orchestrator.subprocess.run")
    def test_tmux_error_returns_false(self, mock_run: MagicMock) -> None:
        """Tmux error (non-zero returncode) returns False (fail-closed)."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        orch = TmuxOrchestrator(safety_mode=False)
        assert orch.is_idle("session", 1) is False

    @patch("src.infrastructure.tmux_orchestrator.subprocess.run")
    def test_timeout_returns_false(self, mock_run: MagicMock) -> None:
        """Timeout returns False (fail-closed)."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="tmux", timeout=5)
        orch = TmuxOrchestrator(safety_mode=False)
        assert orch.is_idle("session", 1) is False

    @patch("src.infrastructure.tmux_orchestrator.subprocess.run")
    def test_empty_output_returns_false(self, mock_run: MagicMock) -> None:
        """Empty output returns False (can't determine)."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        orch = TmuxOrchestrator(safety_mode=False)
        assert orch.is_idle("session", 1) is False
