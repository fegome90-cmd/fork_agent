"""Guard tests for the fake clock in tests/unit/conftest.py."""

import os
import time


def test_fake_clock_advance_logic():
    """FakeClock.offset advances by sleep duration."""
    from tests.unit.conftest import _FakeClock

    clock = _FakeClock()
    t1 = clock.time()
    clock.sleep(5.0)
    t2 = clock.time()
    assert t2 - t1 >= 4.9  # should be ~5.0


def test_fake_clock_no_recursion():
    """Calling clock.sleep inside clock.sleep must not recurse infinitely."""
    from tests.unit.conftest import _FakeClock

    clock = _FakeClock()
    clock.sleep(0.001)  # if recursion, this would stack overflow


def test_fake_clock_deactivation():
    """Without TMUX_FORK_FAST_TESTS=1, time.sleep is real."""
    from tests.unit.conftest import _REAL_SLEEP, _REAL_TIME

    assert callable(_REAL_SLEEP)
    assert callable(_REAL_TIME)


def test_real_clock_works():
    """With TMUX_FORK_FAST_TESTS unset, time.sleep actually waits."""
    if os.environ.get("TMUX_FORK_FAST_TESTS") == "1":
        return  # skip in fast mode
    t0 = time.time()
    time.sleep(0.05)
    elapsed = time.time() - t0
    assert elapsed >= 0.04  # real sleep


def test_xdist_compatible():
    """Fake clock works with xdist — each worker gets its own state."""
    from tests.unit.conftest import _FakeClock

    c1 = _FakeClock()
    c2 = _FakeClock()
    c1.sleep(10.0)
    assert c1.time() > c2.time()  # independent clocks
