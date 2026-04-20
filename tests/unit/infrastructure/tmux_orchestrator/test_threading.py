"""Tests for REQ-6: TmuxOrchestrator thread safety foundation."""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock, patch

from src.infrastructure.tmux_orchestrator import TmuxOrchestrator


class TestRLockFoundation:
    """REQ-6: TmuxOrchestrator SHALL use RLock for thread safety."""

    def test_has_lock_attribute(self) -> None:
        """TmuxOrchestrator instance has _lock attribute."""
        orch = TmuxOrchestrator()
        assert hasattr(orch, "_lock")

    def test_lock_is_rlock(self) -> None:
        """_lock SHALL be a reentrant lock (RLock)."""
        orch = TmuxOrchestrator()
        assert isinstance(orch._lock, type(threading.RLock()))

    def test_slots_include_lock(self) -> None:
        """__slots__ SHALL contain _lock."""
        assert "_lock" in TmuxOrchestrator.__slots__

    def test_slots_include_extended_keys_cache(self) -> None:
        """__slots__ SHALL contain _extended_keys_cached for REQ-7."""
        assert "_extended_keys_cached" in TmuxOrchestrator.__slots__

    def test_slots_include_marker_counter(self) -> None:
        """__slots__ SHALL contain _marker_counter for REQ-10."""
        assert "_marker_counter" in TmuxOrchestrator.__slots__

    def test_extended_keys_cache_initially_none(self) -> None:
        """_extended_keys_cached SHALL start as None (not yet queried)."""
        orch = TmuxOrchestrator()
        assert orch._extended_keys_cached is None

    def test_marker_counter_initially_zero(self) -> None:
        """_marker_counter SHALL start at 0."""
        orch = TmuxOrchestrator()
        assert orch._marker_counter == 0

    def test_rlock_is_reentrant(self) -> None:
        """RLock SHALL allow reentrant acquisition (no self-deadlock)."""
        orch = TmuxOrchestrator()
        with orch._lock, orch._lock:
            pass  # Should not deadlock
        # If we get here, reentrant lock works


class TestConcurrentAccess:
    """REQ-6: Concurrent calls SHALL be serialized."""

    @patch("src.infrastructure.tmux_orchestrator.subprocess.run")
    def test_concurrent_send_commands_serialized(self, mock_run: MagicMock) -> None:
        """Two concurrent send_commands SHALL NOT overlap."""
        call_order: list[str] = []

        def slow_run(cmd: list[str], **_kwargs: object) -> MagicMock:
            call_order.append(f"start-{cmd[-1]}")
            time.sleep(0.01)
            call_order.append(f"end-{cmd[-1]}")
            return MagicMock(returncode=0)

        mock_run.side_effect = slow_run
        orch = TmuxOrchestrator(safety_mode=False)

        threads: list[threading.Thread] = []
        for i in range(3):
            t = threading.Thread(target=orch.send_command, args=("s", 1, f"cmd{i}"))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Check no interleaving: each start-end pair should be adjacent
        for i in range(0, len(call_order) - 1, 2):
            assert call_order[i].startswith("start"), f"Expected start at {i}, got {call_order[i]}"
            assert call_order[i + 1].startswith("end"), (
                f"Expected end at {i + 1}, got {call_order[i + 1]}"
            )

    @patch("src.infrastructure.tmux_orchestrator.subprocess.run")
    def test_reentrant_no_deadlock(self, mock_run: MagicMock) -> None:
        """launch_agent -> send_command chain SHALL NOT deadlock."""
        mock_run.return_value = MagicMock(returncode=0)
        with patch.object(
            TmuxOrchestrator,
            "_get_windows",
            return_value=[type("W", (), {"window_index": 0, "active": True})()],
        ):
            orch = TmuxOrchestrator(safety_mode=False)
            backend = MagicMock()
            backend.get_default_model.return_value = "test-model"
            backend.get_launch_command.return_value = "test command"
            # This should complete without deadlock (RLock handles reentrant case)
            result = orch.launch_agent("test-session", 0, backend, "task", "model")
            assert result  # truthy (positive int marker_id)
