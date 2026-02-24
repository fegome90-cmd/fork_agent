"""Concrete action implementations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class OnFailurePolicy(str, Enum):
    """Policy for handling hook failures."""

    ABORT = "abort"
    CONTINUE = "continue"
    RETRY = "retry"


@dataclass(frozen=True)
class ShellCommandAction:
    """Action that executes a shell command.

    Attributes:
        command: The shell command to execute.
        timeout: Maximum execution time in seconds.
        critical: If True, failure aborts the workflow. If False, failure is logged and execution continues.
        on_failure: Policy to apply when hook fails (abort, continue, retry).
    """

    command: str
    timeout: int = 30
    critical: bool = True
    on_failure: OnFailurePolicy = OnFailurePolicy.ABORT

    def __post_init__(self) -> None:
        """Validate timeout is positive."""
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")

    @property
    def continue_on_failure(self) -> bool:
        """Returns True if hook failure should not abort workflow."""
        return not self.critical or self.on_failure == OnFailurePolicy.CONTINUE
