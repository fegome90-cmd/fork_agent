from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResiliencePolicy:
    """Single Source of Truth for resilience configuration.

    This policy defines the canonical configuration for all circuit breakers
    in the fork_agent system. Using a frozen dataclass ensures immutability.
    """

    failure_threshold: int
    recovery_timeout_seconds: int
    half_open_max_calls: int

    def to_dict(self) -> dict[str, int]:
        return {
            "failure_threshold": self.failure_threshold,
            "recovery_timeout_seconds": self.recovery_timeout_seconds,
            "half_open_max_calls": self.half_open_max_calls,
        }


DEFAULT_POLICY = ResiliencePolicy(
    failure_threshold=3,
    recovery_timeout_seconds=30,
    half_open_max_calls=2,
)


def get_default_policy() -> ResiliencePolicy:
    return DEFAULT_POLICY


def create_policy(
    failure_threshold: int | None = None,
    recovery_timeout_seconds: int | None = None,
    half_open_max_calls: int | None = None,
) -> ResiliencePolicy:
    return ResiliencePolicy(
        failure_threshold=failure_threshold if failure_threshold is not None else DEFAULT_POLICY.failure_threshold,
        recovery_timeout_seconds=recovery_timeout_seconds if recovery_timeout_seconds is not None else DEFAULT_POLICY.recovery_timeout_seconds,
        half_open_max_calls=half_open_max_calls if half_open_max_calls is not None else DEFAULT_POLICY.half_open_max_calls,
    )
