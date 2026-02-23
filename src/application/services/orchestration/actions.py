"""Concrete action implementations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ShellCommandAction:
    """Action that executes a shell command.

    Attributes:
        command: The shell command to execute.
        timeout: Maximum execution time in seconds.
    """

    command: str
    timeout: int = 30

    def __post_init__(self) -> None:
        """Validate timeout is positive."""
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
