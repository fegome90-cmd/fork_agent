"""Bug test fixtures for bug-hunt testing."""

from __future__ import annotations

import pytest

from tests.support.bug_registry import (
    Bug,
    BugRegistry,
    BugSeverity,
    BugStatus,
    get_registry,
    reset_registry,
)


@pytest.fixture
def bug_registry() -> BugRegistry:
    """Fresh bug registry for each test."""
    reset_registry()
    return get_registry()


@pytest.fixture
def critical_bug() -> Bug:
    """Sample critical bug for testing."""
    return Bug(
        id="BUG-001",
        severity=BugSeverity.CRITICAL,
        status=BugStatus.OPEN,
        subsystem="workflow",
        description="Verify endpoint silently swallows exceptions",
        repro_steps="1. Call POST /api/v1/workflow/{plan_id}/verify\n2. Force repo.save() to throw",
        expected="HTTP 500 returned with error detail",
        actual="HTTP 200 returned, exception silently swallowed",
        metadata={"endpoint": "/api/v1/workflow/verify"},
    )


@pytest.fixture
def high_bug() -> Bug:
    """Sample high severity bug."""
    return Bug(
        id="BUG-002",
        severity=BugSeverity.HIGH,
        status=BugStatus.OPEN,
        subsystem="memory",
        description="Memory isolation not enforced between worktrees",
        repro_steps="1. Create worktree A\n2. Save observation in A\n3. Query from worktree B",
        expected="No results (isolated)",
        actual="Observations visible across worktrees",
    )


@pytest.fixture
def medium_bug() -> Bug:
    """Sample medium severity bug."""
    return Bug(
        id="BUG-003",
        severity=BugSeverity.MEDIUM,
        status=BugStatus.OPEN,
        subsystem="tmux",
        description="Tmux session cleanup not implemented",
        repro_steps="1. Run workflow execute\n2. Kill parent process",
        expected="Sessions cleaned up",
        actual="Sessions remain orphaned",
    )


@pytest.fixture
def registered_bugs(bug_registry, critical_bug, high_bug, medium_bug) -> BugRegistry:
    """Registry with multiple bugs registered."""
    bug_registry.register(critical_bug)
    bug_registry.register(high_bug)
    bug_registry.register(medium_bug)
    return bug_registry
