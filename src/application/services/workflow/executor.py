"""WorkflowExecutor service for task execution orchestration.

This service encapsulates the logic for executing workflow tasks,
separating concerns from the CLI layer.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from src.application.services.memory_service import MemoryService
from src.application.services.orchestration.events import (
    WorkflowExecuteCompleteEvent,
    WorkflowExecuteStartEvent,
    WorktreeCreatedEvent,
    WorktreeMergedEvent,
    WorktreeRemovedEvent,
)
from src.application.services.orchestration.hook_service import HookService
from src.application.services.workflow.state import (
    ExecuteState,
    PlanState,
    Task,
    WorkflowPhase,
)
from src.application.services.workspace.workspace_manager import WorkspaceManager
from src.infrastructure.agent_backends import get_default_backend
from src.infrastructure.tmux_orchestrator import TmuxOrchestrator

logger = logging.getLogger(__name__)

# Status constants for tasks
TASK_STATUS_EXECUTING = "executing"
TASK_STATUS_PENDING = "pending"


@dataclass(frozen=True)
class ExecutionResult:
    """Result of executing a workflow plan."""

    exec_state: ExecuteState
    spawned_sessions: tuple[str, ...] = ()
    worktrees_created: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class TaskExecutionResult:
    """Result of executing a single task."""

    task: Task
    session_name: str | None = None
    worktree_path: str | None = None
    worktree_name: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class CleanupResult:
    """Result of cleaning up a task's worktree."""

    worktree_name: str
    merged: bool = False
    removed: bool = False
    error: str | None = None


class WorkflowExecutor:
    """Encapsulates workflow execution logic.

    This service coordinates:
    - TmuxOrchestrator for session management
    - WorkspaceManager for worktree creation/cleanup
    - MemoryService for history persistence
    - HookService for event dispatching
    """

    def __init__(
        self,
        tmux_orchestrator: TmuxOrchestrator,
        memory_service: MemoryService,
        workspace_manager: WorkspaceManager,
        hook_service: HookService,
    ) -> None:
        """Initialize WorkflowExecutor with dependencies.

        Args:
            tmux_orchestrator: Service for tmux session management.
            memory_service: Service for observation persistence.
            workspace_manager: Service for worktree management.
            hook_service: Service for event dispatching.
        """
        self._tmux = tmux_orchestrator
        self._memory = memory_service
        self._workspace = workspace_manager
        self._hooks = hook_service

    def execute_task(
        self,
        task: Task,
        model: str,
        session_name: str | None = None,
    ) -> TaskExecutionResult:
        """Execute a single task: create tmux session and worktree.

        Args:
            task: The task to execute.
            model: The agent model to use.
            session_name: Optional session name (auto-generated if None).

        Returns:
            TaskExecutionResult with execution details.

        Note:
            If worktree creation succeeds but session creation fails,
            the worktree will remain. Caller is responsible for cleanup
            via cleanup_worktree() if needed.
        """
        errors: list[str] = []
        result_session: str | None = None
        result_worktree_path: str | None = None
        result_worktree_name: str | None = None

        # Generate session name if not provided
        if session_name is None:
            session_name = f"fork-{task.slug[:20]}-{uuid.uuid4().hex[:8]}"

        # Step 1: Create tmux session
        try:
            success = self._tmux.create_session(session_name)
            if success:
                logger.info("Created tmux session: %s", session_name)
                result_session = session_name

                # Launch agent in the session
                backend = get_default_backend()
                if backend is None:
                    errors.append("No available agent backend found (opencode/pi)")
                    logger.warning("No available backend to launch task %s", task.id)
                else:
                    prompt = f"Execute task: {task.description}"
                    launched = self._tmux.launch_agent(
                        session_name,
                        0,
                        backend,
                        prompt,
                        model,
                    )
                    if not launched:
                        errors.append(f"Failed to launch agent in tmux session: {session_name}")
                        logger.warning("Failed to launch agent in tmux session: %s", session_name)
            else:
                errors.append(f"Failed to create tmux session: {session_name}")
                logger.warning("Failed to create tmux session: %s", session_name)
        except Exception as e:
            errors.append(f"Error creating tmux session: {e}")
            logger.error("Error creating tmux session for task %s: %s", task.id, e)

        # Step 2: Create worktree
        base_worktree_name = f"task-{task.slug[:30]}"
        worktree_name = base_worktree_name
        try:
            try:
                workspace = self._workspace.create_workspace(worktree_name)
            except Exception as first_error:
                if "already exists" not in str(first_error).lower():
                    raise
                worktree_name = f"{base_worktree_name[:24]}-{uuid.uuid4().hex[:6]}"
                workspace = self._workspace.create_workspace(worktree_name)

            result_worktree_path = str(workspace.path)
            result_worktree_name = worktree_name
            logger.info("Created worktree: %s at %s", worktree_name, result_worktree_path)

            # Dispatch worktree created event
            self._dispatch_event(
                WorktreeCreatedEvent(
                    workspace_name=worktree_name,
                    worktree_path=result_worktree_path,
                ),
            )
        except Exception as e:
            errors.append(f"Failed to create worktree: {e}")
            logger.warning("Failed to create worktree for task %s: %s", task.id, e)

        return TaskExecutionResult(
            task=task,
            session_name=result_session,
            worktree_path=result_worktree_path,
            worktree_name=result_worktree_name,
            error="; ".join(errors) if errors else None,
        )

    def execute_plan(
        self,
        plan: PlanState,
        parallel: bool = False,
        model: str = "opencode/glm-5-free",
        task_id: str | None = None,
    ) -> ExecutionResult:
        """Execute all tasks in a plan.

        Args:
            plan: The plan to execute.
            parallel: Whether to execute tasks in parallel.
            model: The agent model to use.
            task_id: Optional specific task ID to execute.

        Returns:
            ExecutionResult with execution details.
        """
        # Dispatch execute start event
        self._dispatch_event(
            WorkflowExecuteStartEvent(
                plan_id=plan.session_id,
                task_count=len(plan.tasks),
            ),
        )

        # Filter tasks if task_id specified
        tasks_to_execute = plan.tasks
        if task_id:
            tasks_to_execute = [t for t in plan.tasks if t.id == task_id]

        # Execute tasks
        spawned_sessions: list[str] = []
        worktrees_created: list[str] = []
        errors: list[str] = []
        updated_tasks: list[Task] = []

        if parallel:
            # Create all sessions first, then launch agents
            task_results: list[TaskExecutionResult] = []
            for task in tasks_to_execute:
                result = self.execute_task(task, model)
                task_results.append(result)

            # Process results (DRY: extracted to helper method)
            for result in task_results:
                self._collect_result_data(
                    result,
                    spawned_sessions,
                    worktrees_created,
                    errors,
                )
                updated_tasks.append(self._create_updated_task(result))
        else:
            # Sequential execution
            for task in tasks_to_execute:
                result = self.execute_task(task, model)

                # Process results (DRY: extracted to helper method)
                self._collect_result_data(
                    result,
                    spawned_sessions,
                    worktrees_created,
                    errors,
                )
                updated_tasks.append(self._create_updated_task(result))

        # Create execution state
        exec_state = ExecuteState(
            session_id=f"exec-{uuid.uuid4().hex[:8]}",
            status=TASK_STATUS_EXECUTING,
            phase=WorkflowPhase.EXECUTED,
            tasks=updated_tasks,
        )

        # Dispatch execute complete event
        self._dispatch_event(
            WorkflowExecuteCompleteEvent(
                plan_id=plan.session_id,
                tasks_completed=len(updated_tasks),
            ),
        )

        # Save to memory for history
        try:
            self._memory.save(
                content=f"workflow:execute:{plan.session_id}:started",
                metadata={
                    "phase": "execute",
                    "plan_id": plan.session_id,
                    "task_count": len(updated_tasks),
                    "sessions_spawned": len(spawned_sessions),
                },
            )
        except Exception as e:
            logger.debug("Failed to save execute to memory: %s", e)

        return ExecutionResult(
            exec_state=exec_state,
            spawned_sessions=tuple(spawned_sessions),
            worktrees_created=tuple(worktrees_created),
            errors=tuple(errors),
        )

    def cleanup_worktree(
        self,
        task: Task,
        merge: bool = True,
        target_branch: str = "main",
    ) -> CleanupResult:
        """Clean up a task's worktree.

        Args:
            task: The task whose worktree to clean up.
            merge: Whether to merge the worktree branch first.
            target_branch: The target branch for merge.

        Returns:
            CleanupResult with cleanup details.
        """
        worktree_name = task.branch or f"task-{task.slug[:30]}"

        if not task.worktree_path:
            return CleanupResult(
                worktree_name=worktree_name,
                merged=False,
                removed=False,
                error="No worktree path found",
            )

        merged = False
        removed = False
        errors: list[str] = []

        # Merge if requested
        if merge:
            try:
                self._workspace.merge_workspace(
                    worktree_name,
                    target_branch=target_branch,
                    delete_branch=False,
                )
                logger.info("Merged worktree: %s into %s", worktree_name, target_branch)
                merged = True

                # Dispatch merge event
                self._dispatch_event(
                    WorktreeMergedEvent(
                        workspace_name=worktree_name,
                        target_branch=target_branch,
                    ),
                )
            except Exception as e:
                logger.warning("Failed to merge worktree %s: %s", worktree_name, e)
                errors.append(f"Merge failed: {e}")

        # Remove worktree
        try:
            self._workspace.remove_workspace(worktree_name, force=True)
            logger.info("Removed worktree: %s", worktree_name)
            removed = True

            # Dispatch removed event
            self._dispatch_event(
                WorktreeRemovedEvent(workspace_name=worktree_name),
            )
        except Exception as e:
            logger.warning("Failed to remove worktree %s: %s", worktree_name, e)
            errors.append(f"Remove failed: {e}")

        return CleanupResult(
            worktree_name=worktree_name,
            merged=merged,
            removed=removed,
            error="; ".join(errors) if errors else None,
        )

    def cleanup_all_worktrees(
        self,
        tasks: tuple[Task, ...],
        merge: bool = True,
        target_branch: str = "main",
    ) -> tuple[CleanupResult, ...]:
        """Clean up worktrees for multiple tasks.

        Args:
            tasks: Tasks whose worktrees to clean up.
            merge: Whether to merge branches first.
            target_branch: The target branch for merge.

        Returns:
            Tuple of CleanupResult for each task.
        """
        results: list[CleanupResult] = []
        for task in tasks:
            if task.worktree_path:
                result = self.cleanup_worktree(task, merge, target_branch)
                results.append(result)
        return tuple(results)

    def _dispatch_event(self, event: object) -> None:
        """Dispatch an event via HookService.

        Args:
            event: The event to dispatch.
        """
        try:
            self._hooks.dispatch(event)
        except Exception as e:
            logger.error("Error dispatching %s event: %s", type(event).__name__, e)

    def _collect_result_data(
        self,
        result: TaskExecutionResult,
        sessions: list[str],
        worktrees: list[str],
        errors: list[str],
    ) -> None:
        """Collect result data into aggregate lists.

        Args:
            result: The task execution result.
            sessions: List to append session names to.
            worktrees: List to append worktree names to.
            errors: List to append errors to.
        """
        if result.session_name:
            sessions.append(result.session_name)
        if result.worktree_name:
            worktrees.append(result.worktree_name)
        if result.error:
            errors.append(result.error)

    def _create_updated_task(self, result: TaskExecutionResult) -> Task:
        """Create an updated Task from execution result.

        Args:
            result: The task execution result.

        Returns:
            Updated Task with execution details.
        """
        return Task(
            id=result.task.id,
            slug=result.task.slug,
            description=result.task.description,
            status=TASK_STATUS_EXECUTING if result.session_name else result.task.status,
            branch=result.worktree_name or result.task.branch,
            worktree_path=result.worktree_path or result.task.worktree_path,
            session_name=result.session_name,
            agent_pid=result.task.agent_pid,
        )
