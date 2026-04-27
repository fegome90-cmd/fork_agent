"""Concrete event implementations."""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal

WorkflowPhaseLiteral = Literal["outline", "execute", "verify", "ship"]
SubagentStatusLiteral = Literal["completed", "failed", "cancelled", "timeout"]


@dataclass(frozen=True)
class UserCommandEvent:
    """Event fired when user invokes a CLI command.

    Attributes:
        command_name: The name of the command invoked.
        args: Tuple of command arguments.
    """

    command_name: str
    args: tuple[str, ...] = ()


@dataclass(frozen=True)
class FileWrittenEvent:
    """Event fired when a file is written or modified.

    Attributes:
        path: The absolute path to the file that was written.
    """

    path: str


@dataclass(frozen=True)
class ToolPreExecutionEvent:
    """Event fired before a tool executes.

    Used for PreToolUse hooks to gate or modify tool execution.

    Attributes:
        tool_name: The name of the tool about to execute.
    """

    tool_name: str


@dataclass(frozen=True)
class SessionStartEvent:
    """Event fired when a new session starts."""

    session_id: str = ""


@dataclass(frozen=True)
class SubagentStartEvent:
    """Event fired when a subagent starts.

    Attributes:
        agent_name: Name of the agent starting.
    """

    agent_name: str


@dataclass(frozen=True)
class SubagentStopEvent:
    """Event fired when a subagent stops.

    Attributes:
        agent_name: Name of the agent that stopped.
        duration_ms: Duration in milliseconds.
        status: Status of the subagent execution.
    """

    agent_name: str
    duration_ms: int = 0
    status: SubagentStatusLiteral = "completed"


# =============================================================================
# Workflow Events (Wave 1 - Hooks Foundation)
# =============================================================================


@dataclass(frozen=True)
class WorkflowPhaseChangeEvent:
    """Event fired when workflow phase changes.

    Attributes:
        plan_id: The unique identifier of the plan.
        phase: The current phase (outline, execute, verify, ship).
        timestamp: Unix timestamp of the phase change.
    """

    plan_id: str
    phase: WorkflowPhaseLiteral
    timestamp: int = field(default_factory=lambda: int(time.time()))


@dataclass(frozen=True)
class WorkflowOutlineStartEvent:
    """Event fired when workflow outline phase starts.

    Attributes:
        plan_id: The unique identifier of the plan.
        task_description: The task being planned.
    """

    plan_id: str
    task_description: str = ""


@dataclass(frozen=True)
class WorkflowOutlineCompleteEvent:
    """Event fired when workflow outline phase completes.

    Attributes:
        plan_id: The unique identifier of the plan.
        plan_file: Path to the generated plan file.
    """

    plan_id: str
    plan_file: str = ""


@dataclass(frozen=True)
class WorkflowExecuteStartEvent:
    """Event fired when workflow execute phase starts.

    Attributes:
        plan_id: The unique identifier of the plan.
        task_count: Number of tasks to execute.
    """

    plan_id: str
    task_count: int = 0


@dataclass(frozen=True)
class WorkflowExecuteCompleteEvent:
    """Event fired when workflow execute phase completes.

    Attributes:
        plan_id: The unique identifier of the plan.
        tasks_completed: Number of tasks completed.
    """

    plan_id: str
    tasks_completed: int = 0


@dataclass(frozen=True)
class WorkflowVerifyStartEvent:
    """Event fired when workflow verify phase starts.

    Attributes:
        plan_id: The unique identifier of the plan.
        run_tests: Whether tests will be run.
    """

    plan_id: str
    run_tests: bool = True


@dataclass(frozen=True)
class WorkflowVerifyCompleteEvent:
    """Event fired when workflow verify phase completes.

    Attributes:
        plan_id: The unique identifier of the plan.
        test_results: Read-only results of the verification (test name -> passed).
    """

    plan_id: str
    test_results: Mapping[str, bool] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.test_results, dict):
            object.__setattr__(self, "test_results", MappingProxyType(self.test_results))


@dataclass(frozen=True)
class WorkflowShipStartEvent:
    """Event fired when workflow ship phase starts.

    Attributes:
        plan_id: The unique identifier of the plan.
        target_branch: The branch to ship to.
    """

    plan_id: str
    target_branch: str = "main"


@dataclass(frozen=True)
class WorkflowShipCompleteEvent:
    """Event fired when workflow ship phase completes.

    Attributes:
        plan_id: The unique identifier of the plan.
        target_branch: The branch shipped to.
    """

    plan_id: str
    target_branch: str = "main"


# =============================================================================
# Worktree Events (Wave 3 - Memory + Worktree Integration)
# =============================================================================


@dataclass(frozen=True)
class WorktreeCreatedEvent:
    """Event fired when a worktree is created for a task.

    Attributes:
        workspace_name: The name of the workspace/worktree.
        worktree_path: The path to the worktree.
    """

    workspace_name: str
    worktree_path: str


@dataclass(frozen=True)
class WorktreeMergedEvent:
    """Event fired when a worktree branch is merged.

    Attributes:
        workspace_name: The name of the workspace/worktree.
        target_branch: The branch merged into.
    """

    workspace_name: str
    target_branch: str = "main"


@dataclass(frozen=True)
class WorktreeRemovedEvent:
    """Event fired when a worktree is removed.

    Attributes:
        workspace_name: The name of the workspace/worktree.
    """

    workspace_name: str


@dataclass(frozen=True)
class TrifectaIndexEvent:
    """Event fired when Trifecta graph index completes.

    Attributes:
        repo_path: Absolute path to the repository.
        duration_ms: Time taken to index in milliseconds.
        node_count: Number of nodes in the graph.
        edge_count: Number of edges in the graph.
    """

    repo_path: str
    duration_ms: int
    node_count: int = 0
    edge_count: int = 0
