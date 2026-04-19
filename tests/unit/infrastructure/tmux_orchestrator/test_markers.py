"""Tests for REQ-10: FORK_START/END markers and capture_between_markers."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.infrastructure.tmux_orchestrator import TmuxOrchestrator


class TestMarkers:
    """REQ-10: Commands SHALL be wrapped with FORK_START/END markers."""

    @patch("src.infrastructure.tmux_orchestrator.subprocess.run")
    def test_command_wrapped_with_markers(self, mock_run: MagicMock) -> None:
        """send_command wraps text between FORK_START and FORK_END."""
        mock_run.return_value = MagicMock(returncode=0)
        orch = TmuxOrchestrator(safety_mode=False)
        orch.send_command("session", 0, "echo hello")
        all_cmds = [str(c[0][0]) for c in mock_run.call_args_list]
        full_text = " ".join(all_cmds)
        assert "FORK_START" in full_text
        assert "FORK_END" in full_text

    @patch("src.infrastructure.tmux_orchestrator.subprocess.run")
    def test_marker_ids_unique_and_monotonic(self, mock_run: MagicMock) -> None:
        """Each successful send returns a unique, incrementing marker_id."""
        mock_run.return_value = MagicMock(returncode=0)
        orch = TmuxOrchestrator(safety_mode=False)
        id1 = orch.send_command("session", 0, "cmd1")
        id2 = orch.send_command("session", 0, "cmd2")
        id3 = orch.send_command("session", 0, "cmd3")
        assert id1 > 0 and id2 > 0 and id3 > 0
        assert id1 < id2 < id3

    @patch("src.infrastructure.tmux_orchestrator.subprocess.run")
    def test_capture_between_markers_extracts_text(self, mock_run: MagicMock) -> None:
        """capture_between_markers extracts text between markers."""
        orch = TmuxOrchestrator(safety_mode=False)
        marker_id = orch.send_command("session", 0, "echo hello")
        # Subsequent calls to capture_content will hit subprocess.run
        # We set up the mock to return marker content for capture-pane calls
        marker_content = MagicMock()
        marker_content.returncode = 0
        marker_content.stdout = (
            "before\nFORK_START:{mid}\necho hello output\nFORK_END:{mid}\nafter".format(
                mid=marker_id
            )
        )
        mock_run.return_value = marker_content
        result = orch.capture_between_markers("session", 0, marker_id)
        assert "echo hello output" in result
        assert "FORK_START" not in result
        assert "FORK_END" not in result

    @patch("src.infrastructure.tmux_orchestrator.subprocess.run")
    def test_capture_missing_markers_returns_empty(self, mock_run: MagicMock) -> None:
        """capture_between_markers returns empty string if markers not found."""
        no_marker_content = MagicMock()
        no_marker_content.returncode = 0
        no_marker_content.stdout = "no markers here"
        mock_run.return_value = no_marker_content
        orch = TmuxOrchestrator(safety_mode=False)
        result = orch.capture_between_markers("session", 0, 999)
        assert result == ""

    def test_safety_mode_does_not_send_markers_to_tmux(self) -> None:
        """Safety mode returns marker_id but does not call subprocess."""
        with patch("src.infrastructure.tmux_orchestrator.subprocess.run") as mock_run:
            orch = TmuxOrchestrator(safety_mode=True)
            result = orch.send_command("session", 0, "echo test")
            assert result > 0
            mock_run.assert_not_called()
