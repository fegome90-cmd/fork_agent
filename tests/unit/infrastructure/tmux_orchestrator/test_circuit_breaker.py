import pytest
from src.infrastructure.tmux_orchestrator.circuit_breaker import (
    CircuitState,
    TmuxCircuitBreaker,
)


class TestTmuxCircuitBreaker:
    def test_initial_state_is_closed(self):
        cb = TmuxCircuitBreaker()
        assert cb.state == CircuitState.CLOSED

    def test_can_execute_initially_true(self):
        cb = TmuxCircuitBreaker()
        assert cb.can_execute() is True

    def test_opens_after_threshold_failures(self):
        cb = TmuxCircuitBreaker(failure_threshold=3)

        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_cannot_execute_when_open(self):
        cb = TmuxCircuitBreaker(failure_threshold=2)

        cb.record_failure()
        cb.record_failure()
        assert cb.can_execute() is False

    def test_success_resets_circuit(self):
        cb = TmuxCircuitBreaker(failure_threshold=2)

        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_opens_immediately_with_zero_timeout(self):
        cb = TmuxCircuitBreaker(failure_threshold=1, recovery_timeout=0)
        cb.record_failure()
        assert cb.state == CircuitState.HALF_OPEN

    def test_failure_count_tracks_correctly(self):
        cb = TmuxCircuitBreaker(failure_threshold=5)

        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 2

        cb.record_success()
        assert cb.failure_count == 0

    def test_reset_clears_state(self):
        cb = TmuxCircuitBreaker(failure_threshold=2)

        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True
