"""Tests for REQ-12: Process metrics collection."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestCollectMetricsPsutil:
    """REQ-12: collect_metrics via psutil."""

    @patch("src.infrastructure.tmux_orchestrator.process_metrics._PSUTIL_AVAILABLE", True)
    @patch("src.infrastructure.tmux_orchestrator.process_metrics.psutil")
    def test_psutil_returns_metrics(self, mock_psutil: MagicMock) -> None:
        """psutil available and PID exists returns real metrics."""
        mock_proc = MagicMock()
        mock_proc.cpu_percent.return_value = 15.5
        mock_proc.memory_info.return_value = MagicMock(rss=100 * 1024 * 1024)  # 100 MB
        mock_psutil.Process.return_value = mock_proc
        mock_psutil.NoSuchProcess = type("NoSuchProcess", (Exception,), {})

        from src.infrastructure.tmux_orchestrator.process_metrics import collect_metrics

        result = collect_metrics(1234)
        assert result["cpu_percent"] == 15.5
        assert result["memory_mb"] > 0

    @patch("src.infrastructure.tmux_orchestrator.process_metrics._PSUTIL_AVAILABLE", True)
    @patch("src.infrastructure.tmux_orchestrator.process_metrics.psutil")
    def test_invalid_pid_returns_zeroed(self, mock_psutil: MagicMock) -> None:
        """Invalid PID returns zeroed metrics."""
        mock_psutil.Process.side_effect = Exception("No such process")
        mock_psutil.NoSuchProcess = type("NoSuchProcess", (Exception,), {})

        from src.infrastructure.tmux_orchestrator.process_metrics import collect_metrics

        result = collect_metrics(99999)
        assert result["cpu_percent"] == 0.0
        assert result["memory_mb"] == 0.0

    @patch("src.infrastructure.tmux_orchestrator.process_metrics._PSUTIL_AVAILABLE", False)
    def test_no_psutil_returns_zeroed(self) -> None:
        """psutil not available returns zeroed metrics."""
        from src.infrastructure.tmux_orchestrator.process_metrics import collect_metrics

        result = collect_metrics(1234)
        assert result["cpu_percent"] == 0.0
        assert result["memory_mb"] == 0.0

    @patch("src.infrastructure.tmux_orchestrator.process_metrics._PSUTIL_AVAILABLE", True)
    @patch("src.infrastructure.tmux_orchestrator.process_metrics.psutil")
    def test_any_error_returns_zeroed(self, mock_psutil: MagicMock) -> None:
        """Any unexpected error returns zeroed metrics."""
        mock_psutil.Process.side_effect = RuntimeError("unexpected")

        from src.infrastructure.tmux_orchestrator.process_metrics import collect_metrics

        result = collect_metrics(1234)
        assert result["cpu_percent"] == 0.0
        assert result["memory_mb"] == 0.0


class TestCollectMetricsProcFs:
    """REQ-12: /proc fallback on Linux."""

    @patch("src.infrastructure.tmux_orchestrator.process_metrics._PSUTIL_AVAILABLE", False)
    @patch("src.infrastructure.tmux_orchestrator.process_metrics.platform.system", return_value="Linux")
    def test_proc_stat_failure_returns_zeroed(self, mock_platform: MagicMock) -> None:
        """CPU parsed from /proc/{pid}/stat returns zeroed when process missing."""
        from src.infrastructure.tmux_orchestrator.process_metrics import collect_metrics

        result = collect_metrics(1234)
        # On /proc failure (no real process with PID 1234), should return zeroed
        assert result["cpu_percent"] == 0.0
        assert "memory_mb" in result

    @patch("src.infrastructure.tmux_orchestrator.process_metrics._PSUTIL_AVAILABLE", False)
    @patch("src.infrastructure.tmux_orchestrator.process_metrics.platform.system", return_value="Darwin")
    def test_non_linux_skips_proc(self, mock_platform: MagicMock) -> None:
        """Non-Linux systems skip /proc fallback."""
        from src.infrastructure.tmux_orchestrator.process_metrics import collect_metrics

        result = collect_metrics(1234)
        assert result["cpu_percent"] == 0.0
        assert result["memory_mb"] == 0.0

    @patch("src.infrastructure.tmux_orchestrator.process_metrics._PSUTIL_AVAILABLE", False)
    @patch("src.infrastructure.tmux_orchestrator.process_metrics.platform.system", return_value="Linux")
    @patch(
        "src.infrastructure.tmux_orchestrator.process_metrics._collect_via_proc",
        return_value={"cpu_percent": 80.0, "memory_mb": 100.0},
    )
    def test_proc_delegates_to_collect_via_proc(
        self,
        mock_collect_via_proc: MagicMock,
        mock_platform: MagicMock,
    ) -> None:
        """collect_metrics delegates to _collect_via_proc on Linux without psutil."""
        from src.infrastructure.tmux_orchestrator.process_metrics import collect_metrics

        result = collect_metrics(1234)
        mock_collect_via_proc.assert_called_once_with(1234)
        assert result["cpu_percent"] == 80.0
        assert result["memory_mb"] == 100.0


class TestCollectViaProc:
    """Unit tests for _collect_via_proc parsing logic."""

    def test_parses_stat_and_status(self) -> None:
        """Parses /proc/{pid}/stat and /proc/{pid}/status correctly."""
        stat_content = (
            "1234 (python) S 1 1234 1234 0 -1 4194304 100 0 0 0 "
            "50 30 0 0 20 0 1 0 12345 100000000 200 18446744073709551615 "
            "94777429188608 94777429329344 140736055398080 0 0 0 0 0 0 0 "
            "0 2147483647 0 0 0 17 0 0 0 0 0 0 94777429346656 "
            "94777429347168 94777434404864 140736055405123 140736055405132 "
            "140736055405132 140736055409123 0\n"
        )
        status_lines = [
            "Name:\tpython\n",
            "State:\tS (sleeping)\n",
            "Pid:\t1234\n",
            "VmRSS:\t102400 kB\n",
        ]

        stat_file = MagicMock()
        stat_file.read.return_value = stat_content
        stat_file.__enter__ = MagicMock(return_value=stat_file)
        stat_file.__exit__ = MagicMock(return_value=False)

        status_file = MagicMock()
        status_file.__iter__ = MagicMock(return_value=iter(status_lines))
        status_file.__enter__ = MagicMock(return_value=status_file)
        status_file.__exit__ = MagicMock(return_value=False)

        with patch("builtins.open", side_effect=[stat_file, status_file]):
            from src.infrastructure.tmux_orchestrator.process_metrics import _collect_via_proc

            result = _collect_via_proc(1234)

        # utime (index 13) = 50, stime (index 14) = 30 → 80.0
        assert result["cpu_percent"] == 80.0
        # VmRSS: 102400 kB → 100.0 MB
        assert result["memory_mb"] == 100.0

    def test_missing_vmrss_returns_zero_memory(self) -> None:
        """Returns 0 memory when VmRSS line is missing."""
        stat_content = (
            "1234 (python) S 1 1234 1234 0 -1 4194304 0 "
            "10 20 0 0 20 0 1 0 12345 100000000\n"
        )
        status_lines = [
            "Name:\tpython\n",
            "State:\tS (sleeping)\n",
        ]

        stat_file = MagicMock()
        stat_file.read.return_value = stat_content
        stat_file.__enter__ = MagicMock(return_value=stat_file)
        stat_file.__exit__ = MagicMock(return_value=False)

        status_file = MagicMock()
        status_file.__iter__ = MagicMock(return_value=iter(status_lines))
        status_file.__enter__ = MagicMock(return_value=status_file)
        status_file.__exit__ = MagicMock(return_value=False)

        with patch("builtins.open", side_effect=[stat_file, status_file]):
            from src.infrastructure.tmux_orchestrator.process_metrics import _collect_via_proc

            result = _collect_via_proc(1234)

        assert result["memory_mb"] == 0.0
