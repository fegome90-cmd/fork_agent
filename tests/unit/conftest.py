"""Optional fake clock for faster test execution.

Only activates when TMUX_FORK_FAST_TESTS=1 is set in the environment.
This allows running tests with real time by default, and fast mode on demand.

Usage:
    # Normal (real clock) — default:
    uv run pytest tests/unit/

    # Fast mode (fake clock):
    TMUX_FORK_FAST_TESTS=1 uv run pytest tests/unit/
"""

import os
import time as _time_module

_REAL_SLEEP = _time_module.sleep
_REAL_TIME = _time_module.time


class _FakeClock:
    """Advances virtual time instead of sleeping. Thread-safe for xdist workers."""

    __slots__ = ("_offset",)

    def __init__(self) -> None:
        self._offset = 0.0

    def time(self) -> float:
        return _REAL_TIME() + self._offset

    def sleep(self, seconds: float) -> None:
        if seconds > 0:
            self._offset += seconds


def pytest_configure(config):
    """Activate fake clock only when TMUX_FORK_FAST_TESTS=1."""
    if os.environ.get("TMUX_FORK_FAST_TESTS") == "1":
        clock = _FakeClock()
        _time_module.sleep = clock.sleep
        _time_module.time = clock.time


def pytest_unconfigure(config):
    """Restore real time functions after session."""
    _time_module.sleep = _REAL_SLEEP
    _time_module.time = _REAL_TIME
