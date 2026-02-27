"""Bug Registry - Test-only utility for tracking detected bugs.

This module provides a simple registry for bugs discovered during testing.
Only used in tests, not in production code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class BugSeverity(Enum):
    """Severity levels for bugs."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class BugStatus(Enum):
    """Status of bug tracking."""

    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    FIXED = "FIXED"
    WONT_FIX = "WONT_FIX"


@dataclass(frozen=True)
class Bug:
    """Immutable bug record."""

    id: str
    severity: BugSeverity
    status: BugStatus
    subsystem: str
    description: str
    repro_steps: str
    expected: str
    actual: str
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


class BugRegistry:
    """In-memory registry for tracking bugs discovered in tests."""

    def __init__(self) -> None:
        self._bugs: dict[str, Bug] = {}

    def register(self, bug: Bug) -> None:
        """Register a bug."""
        self._bugs[bug.id] = bug

    def get(self, bug_id: str) -> Bug | None:
        """Get bug by ID."""
        return self._bugs.get(bug_id)

    def all(self) -> list[Bug]:
        """Get all bugs."""
        return list(self._bugs.values())

    def by_subsystem(self, subsystem: str) -> list[Bug]:
        """Get bugs by subsystem."""
        return [b for b in self._bugs.values() if b.subsystem == subsystem]

    def by_severity(self, severity: BugSeverity) -> list[Bug]:
        """Get bugs by severity."""
        return [b for b in self._bugs.values() if b.severity == severity]

    def by_status(self, status: BugStatus) -> list[Bug]:
        """Get bugs by status."""
        return [b for b in self._bugs.values() if b.status == status]


# Global registry instance for tests
_global_registry: BugRegistry | None = None


def get_registry() -> BugRegistry:
    """Get global bug registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = BugRegistry()
    return _global_registry


def reset_registry() -> None:
    """Reset global registry (for test isolation)."""
    global _global_registry
    _global_registry = None
