from src.infrastructure.tmux_orchestrator.retry import (
    ExponentialBackoff,
    RetryConfig,
    RetryResult,
    retry_sync,
)


def successful_func():
    return "success"


def failing_func():
    raise ValueError("test error")


class_call_count = 0


def counting_func():
    global class_call_count
    class_call_count += 1
    if class_call_count < 3:
        raise ValueError("temporary failure")
    return "success after retries"


class TestExponentialBackoff:
    def test_default_delays(self):
        backoff = ExponentialBackoff()
        assert backoff.get_delay(0) == 1.0
        assert backoff.get_delay(1) == 2.0
        assert backoff.get_delay(2) == 4.0
        assert backoff.get_delay(3) == 8.0
        assert backoff.get_delay(10) == 10.0

    def test_custom_base_delay(self):
        backoff = ExponentialBackoff(base_delay=2.0)
        assert backoff.get_delay(0) == 2.0
        assert backoff.get_delay(1) == 4.0
        assert backoff.get_delay(2) == 8.0

    def test_max_delay_cap(self):
        backoff = ExponentialBackoff(base_delay=1.0, max_delay=5.0)
        assert backoff.get_delay(0) == 1.0
        assert backoff.get_delay(1) == 2.0
        assert backoff.get_delay(2) == 4.0
        assert backoff.get_delay(3) == 5.0
        assert backoff.get_delay(10) == 5.0


class TestRetrySync:
    def test_success_first_try(self):
        result = retry_sync(successful_func)
        assert result.success is True
        assert result.result == "success"
        assert result.attempts == 1
        assert result.error is None

    def test_failure_after_max_retries(self):
        global class_call_count
        class_call_count = 0
        config = RetryConfig(max_retries=2)
        result = retry_sync(failing_func, config)
        assert result.success is False
        assert result.error == "test error"
        assert result.attempts == 3

    def test_retry_until_success(self):
        global class_call_count
        class_call_count = 0
        config = RetryConfig(max_retries=5, base_delay=0.1)
        result = retry_sync(counting_func, config)
        assert result.success is True
        assert result.result == "success after retries"
        assert result.attempts == 3

    def test_custom_config(self):
        config = RetryConfig(max_retries=1, base_delay=0.01)
        result = retry_sync(failing_func, config)
        assert result.success is False
        assert result.attempts == 2

    def test_retry_result_str(self):
        result = RetryResult(success=True, result="test", error=None, attempts=1)
        assert result.success is True
        assert result.result == "test"
