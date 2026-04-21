"""Speed up tests that use time.sleep for long durations.

Patches time.sleep and time.time with a fake clock for the entire session.
Uses module-level patching (not per-test fixtures) to avoid 1607× setup overhead.
"""

import time as _time_module

# Grab the real functions BEFORE any patching
_REAL_SLEEP = _time_module.sleep
_REAL_TIME = _time_module.time


class _FakeClock:
    __slots__ = ("_offset",)

    def __init__(self) -> None:
        self._offset = 0.0

    def time(self) -> float:
        return _REAL_TIME() + self._offset

    def sleep(self, seconds: float) -> None:
        if seconds > 0:
            self._offset += seconds
        # else: sleep(0) is a yield point, skip it


def pytest_configure(config):
    """Patch time.sleep and time.time once for the entire session."""
    clock = _FakeClock()
    _time_module.sleep = clock.sleep
    _time_module.time = clock.time


def pytest_unconfigure(config):
    """Restore original time functions after session."""
    _time_module.sleep = _REAL_SLEEP
    _time_module.time = _REAL_TIME
