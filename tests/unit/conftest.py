"""Speed up tests that use time.sleep for long durations.

Patches time.sleep and time.time with a fake clock:
- time.sleep(n) where n > 50ms: advances the clock, no real sleep
- time.sleep(n) where n <= 50ms: real sleep (needed for threading barriers)
- time.time(): returns real time + accumulated fake offset
"""

import time as _time_module
from unittest.mock import patch

import pytest

# Grab the real functions BEFORE any patching
_REAL_SLEEP = _time_module.sleep
_REAL_TIME = _time_module.time
_THRESHOLD = 0.05


class _FakeClock:
    __slots__ = ("_offset",)

    def __init__(self) -> None:
        self._offset = 0.0

    def time(self) -> float:
        return _REAL_TIME() + self._offset

    def sleep(self, seconds: float) -> None:
        if seconds > _THRESHOLD:
            self._offset += seconds
        else:
            _REAL_SLEEP(seconds)


@pytest.fixture(autouse=True)
def _fast_clock():
    """Replace time.sleep and time.time with a fake clock."""
    clock = _FakeClock()
    with (
        patch("time.sleep", side_effect=clock.sleep),
        patch("time.time", side_effect=clock.time),
    ):
        yield
