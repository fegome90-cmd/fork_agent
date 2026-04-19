"""Tests for REQ-7: Extended-keys detection and Enter behavior."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.infrastructure.tmux_orchestrator import TmuxOrchestrator


class TestExtendedKeys:
    """REQ-7: Enter key behavior SHALL adapt to extended-keys setting."""

    @patch("src.infrastructure.tmux_orchestrator.subprocess.run")
    def test_extended_keys_on_sends_enter_key_name(self, mock_run: MagicMock) -> None:
        """When extended-keys is ON, Enter sent as key name."""
        mock_run.return_value = MagicMock(returncode=0, stdout="on\n")
        orch = TmuxOrchestrator(safety_mode=False)
        orch._send_enter("session:0")
        # Find the Enter send call (last call)
        enter_call = mock_run.call_args_list[-1]
        cmd = enter_call[0][0]
        assert "Enter" in cmd
        assert "-l" not in cmd or "\\r" not in str(cmd)

    @patch("src.infrastructure.tmux_orchestrator.subprocess.run")
    def test_extended_keys_off_sends_literal_cr(self, mock_run: MagicMock) -> None:
        """When extended-keys is OFF, Enter sent as literal \\r."""
        mock_run.return_value = MagicMock(returncode=0, stdout="off\n")
        orch = TmuxOrchestrator(safety_mode=False)
        orch._send_enter("session:0")
        # Find the Enter send call
        enter_call = mock_run.call_args_list[-1]
        cmd = enter_call[0][0]
        assert "-l" in cmd
        assert "\r" in cmd

    @patch("src.infrastructure.tmux_orchestrator.subprocess.run")
    def test_query_failure_caches_false(self, mock_run: MagicMock) -> None:
        """Query failure caches False (use literal \\r)."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        orch = TmuxOrchestrator(safety_mode=False)
        orch._send_enter("session:0")
        # Should have used literal \r (cached False)
        assert orch._extended_keys_cached is False
        # Reset and call again - should NOT re-query
        mock_run.reset_mock()
        mock_run.return_value = MagicMock(returncode=0)
        orch._send_enter("session:0")
        # Should NOT have called show-options again
        for call_args in mock_run.call_args_list:
            cmd = call_args[0][0]
            assert "show-options" not in str(cmd)

    @patch("src.infrastructure.tmux_orchestrator.subprocess.run")
    def test_cache_avoids_repeated_queries(self, mock_run: MagicMock) -> None:
        """Second call uses cache, doesn't re-query tmux."""
        mock_run.return_value = MagicMock(returncode=0, stdout="on\n")
        orch = TmuxOrchestrator(safety_mode=False)
        orch._send_enter("session:0")
        orch._send_enter("session:0")
        # Should only have queried once (first call)
        show_calls = [c for c in mock_run.call_args_list if "show-options" in str(c)]
        assert len(show_calls) <= 1
