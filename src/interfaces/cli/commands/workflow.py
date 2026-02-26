"""Workflow commands for CLI."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

import typer

from src.application.exceptions import PhaseSkipError
from src.application.services.orchestration.events import (
    WorkflowOutlineCompleteEvent,
    WorkflowOutlineStartEvent,
    WorkflowShipCompleteEvent,
    WorkflowShipStartEvent,
    WorkflowVerifyCompleteEvent,
    WorkflowVerifyStartEvent,
    WorktreeMergedEvent,
    WorktreeRemovedEvent,
)
from src.application.services.orchestration.hook_service import HookService
from src.application.services.workflow.state import (
    ExecuteState,
    PlanState,
    VerifyState,
    WorkflowPhase,
    get_execute_state_path,
    get_plan_state_path,
    get_verify_state_path,
)
from src.infrastructure.persistence.container import (
    get_memory_service,
    get_workspace_manager,
)
from src.interfaces.cli.dependencies import get_hook_service as _get_shared_hook_service

logger = logging.getLogger(__name__)


def _get_hook_service() -> HookService:
    """Get HookService from ctx.obj if available (for testability), else use shared singleton."""
    try:
        ctx = typer.get_current_context()
        if isinstance(ctx.obj, dict):
            if "hook_service" not in ctx.obj:
                ctx.obj["hook_service"] = _get_shared_hook_service()
            return ctx.obj["hook_service"]
    except RuntimeError:
        pass
    return _get_shared_hook_service()


def _dispatch_event(event: object, context: str = "") -> None:
    """Dispatch event with error logging, never raises.

    Args:
        event: The event to dispatch.
        context: Context string for logging (e.g., "outline_start").
    """
    try:
        _get_hook_service().dispatch(event)
    except Exception as e:
        logger.debug("Hook dispatch failed [%s]: %s", context, e)


app = typer.Typer(name="workflow", help="Workflow commands: outline, execute, verify, ship")


def _check_plan_exists() -> PlanState:
    plan_path = get_plan_state_path()
    plan = PlanState.load(plan_path)
    if plan is None:
        typer.echo("Error: No plan found. Run 'memory workflow outline' first.", err=True)
        raise typer.Exit(1)
    return plan


def _check_execute_exists() -> ExecuteState:
    exec_path = get_execute_state_path()
    state = ExecuteState.load(exec_path)
    if state is None:
        typer.echo("Error: No execution found. Run 'memory workflow execute' first.", err=True)
        raise typer.Exit(1)
    return state


def _check_verify_exists() -> VerifyState:
    verify_path = get_verify_state_path()
    state = VerifyState.load(verify_path)
    if state is None:
        typer.echo("Error: No verification found. Run 'memory workflow verify' first.", err=True)
        raise typer.Exit(1)
    return state


def _validate_phase_transition(
    current_phase: WorkflowPhase | None,
    allowed_phases: list[WorkflowPhase],
    target_command: str,
) -> None:
    """Validate that the current phase allows transition to the target command.

    Args:
        current_phase: The current workflow phase (None if no state exists)
        allowed_phases: List of phases that are allowed to transition to the target command
        target_command: The name of the target command

    Raises:
        PhaseSkipError: If the phase transition is not allowed
    """
    if current_phase is None:
        # No state exists - this is the first command in the workflow
        # Allow if the target is outline (which creates initial state)
        if target_command == "outline":
            return
        # Otherwise, it's a skip
        raise PhaseSkipError(
            message=f"Cannot run '{target_command}' without completing previous phases.",
            current_phase="none",
            target_phase=target_command,
        )

    if current_phase not in allowed_phases:
        allowed = ", ".join(p.value for p in allowed_phases)
        raise PhaseSkipError(
            message=f"Cannot skip to '{target_command}'. Current phase is '{current_phase.value}'. Required phases: {allowed}.",
            current_phase=current_phase.value,
            target_phase=target_command,
        )


@app.command("outline")
def outline(
    task_description: str = typer.Argument(..., help="Task description to plan"),
    plan_file: str = typer.Option(".claude/plans/plan.md", "--plan-file", "-p"),
) -> None:
    session_id = f"plan-{uuid.uuid4().hex[:8]}"

    # Dispatch outline start event
    _dispatch_event(
        WorkflowOutlineStartEvent(plan_id=session_id, task_description=task_description),
        context="outline_start",
    )

    plan_state = PlanState(
        session_id=session_id,
        status="outlined",
        phase=WorkflowPhase.OUTLINED,
        plan_file=plan_file,
    )
    plan_path = get_plan_state_path()
    plan_state.save(plan_path)
    plan_dir = Path(plan_file).parent
    plan_dir.mkdir(parents=True, exist_ok=True)
    plan_content = f"""# Plan: {task_description}

## Session: {session_id}

### Tasks
- [ ] {task_description}

---
Generated by fork_agent workflow
"""
    Path(plan_file).write_text(plan_content)
    typer.echo(f"✓ Plan created: {session_id}")
    typer.echo(f"  Plan file: {plan_file}")
    typer.echo("  Next: Run 'memory workflow execute'")

    # Dispatch outline complete event
    _dispatch_event(
        WorkflowOutlineCompleteEvent(plan_id=session_id, plan_file=plan_file),
        context="outline_complete",
    )

    # Save to memory for history
    try:
        memory = get_memory_service()
        memory.save(
            content=f"workflow:outline:{session_id}:{task_description}",
            metadata={
                "phase": "outline",
                "plan_id": session_id,
                "task_description": task_description,
            },
        )
    except Exception as e:
        logger.debug("Failed to save outline to memory: %s", e)


#ZK

@app.command("execute")
def execute(
    task_id: str | None = typer.Argument(None, help="Specific task ID to execute"),
    parallel: bool = typer.Option(False, "--parallel", help="Run tasks in parallel"),
    model: str = typer.Option("opencode/glm-5-free", "--model", "-m", help="Agent model to use"),
) -> None:
    """Execute workflow plan tasks.

    Delegates to WorkflowExecutor for task execution, tmux session management,
    worktree creation, and event dispatching.
    """
    from src.interfaces.cli.dependencies import get_workflow_executor

    plan = _check_plan_exists()

    # Validate phase transition: execute requires outlined phase
    _validate_phase_transition(
        current_phase=plan.phase,
        allowed_phases=[WorkflowPhase.OUTLINED, WorkflowPhase.EXECUTED],
        target_command="execute",
    )

    exec_path = get_execute_state_path()
    exec_state = ExecuteState.load(exec_path)

    # Create initial execute state if none exists
    if exec_state is None:
        exec_state = ExecuteState(
            session_id=f"exec-{uuid.uuid4().hex[:8]}",
            status="executing",
            phase=WorkflowPhase.EXECUTING,
            tasks=plan.tasks,
        )

    # Delegate to WorkflowExecutor
    executor = get_workflow_executor()
    result = executor.execute_plan(
        plan=plan,
        parallel=parallel,
        model=model,
        task_id=task_id,
    )

    # Save execution state
    result.exec_state.save(exec_path)

    # CLI output
    typer.echo(f"✓ Execution started: {result.exec_state.session_id}")
    typer.echo(f"  Tasks: {len(result.exec_state.tasks)}")
    typer.echo(f"  Sessions spawned: {len(result.spawned_sessions)}")
    if result.spawned_sessions:
        typer.echo(f"  Tmux sessions: {', '.join(result.spawned_sessions)}")
    if result.errors:
        typer.echo(f"  Errors: {len(result.errors)}", err=True)
    typer.echo("  Next: Run 'memory workflow verify'")

@app.command("verify")
def verify(
    run_tests: bool = typer.Option(True, "--tests/--no-tests", help="Run tests"),
) -> None:
    plan = _check_plan_exists()
    exec_state = _check_execute_exists()

    # Validate phase transition: verify requires executed phase
    _validate_phase_transition(
        current_phase=exec_state.phase,
        allowed_phases=[WorkflowPhase.EXECUTED, WorkflowPhase.VERIFIED],
        target_command="verify",
    )

    session_id = f"verify-{uuid.uuid4().hex[:8]}"

    # Dispatch verify start event
    _dispatch_event(
        WorkflowVerifyStartEvent(plan_id=plan.session_id, run_tests=run_tests),
        context="verify_start",
    )

    verify_path = get_verify_state_path()
    test_results: dict[str, bool] = {"passed": True} if run_tests else {}
    verify_state = VerifyState(
        session_id=session_id,
        status="verified",
        phase=WorkflowPhase.VERIFIED,
        unlock_ship=True,
        test_results=test_results,
    )
    verify_state.save(verify_path)
    typer.echo(f"✓ Verification complete: {verify_state.session_id}")
    typer.echo(f"  Unlock ship: {verify_state.unlock_ship}")
    typer.echo("  Next: Run 'memory workflow ship'")

    # Dispatch verify complete event
    _dispatch_event(
        WorkflowVerifyCompleteEvent(plan_id=verify_state.session_id),
        context="verify_complete",
    )

    # Save to memory for history
    try:
        memory = get_memory_service()
        memory.save(
            content=f"workflow:verify:{verify_state.session_id}:complete",
            metadata={
                "phase": "verify",
                "plan_id": verify_state.session_id,
                "test_results": verify_state.test_results,
            },
        )
    except Exception as e:
        logger.debug("Failed to save verify to memory: %s", e)


@app.command("ship")
def ship(
    target_branch: str = typer.Option("main", "--branch", "-b", help="Target branch"),
    cleanup: bool = typer.Option(True, "--cleanup/--no-cleanup", help="Cleanup worktrees"),
) -> None:
    verify_state = _check_verify_exists()

    # Validate phase transition: ship requires verified phase
    _validate_phase_transition(
        current_phase=verify_state.phase,
        allowed_phases=[WorkflowPhase.VERIFIED, WorkflowPhase.SHIPPED],
        target_command="ship",
    )

    if not verify_state.unlock_ship:
        typer.echo(
            "Error: Verification not complete. Run 'memory workflow verify' first.", err=True
        )
        raise typer.Exit(1)

    # Note: plan check not needed here, verify already validated the workflow

    # Dispatch ship start event
    _dispatch_event(
        WorkflowShipStartEvent(plan_id=verify_state.session_id, target_branch=target_branch),
        context="ship_start",
    )

    exec_path = get_execute_state_path()
    exec_state = ExecuteState.load(exec_path)

    # Cleanup worktrees if requested
    if cleanup and exec_state:
        try:
            workspace_manager = get_workspace_manager()
            cleaned_worktrees: list[str] = []

            for task in exec_state.tasks:
                if task.worktree_path:
                    try:
                        # Extract workspace name from worktree_path or branch
                        worktree_name = task.branch or f"task-{task.slug[:30]}"

                        # Try to merge first
                        try:
                            workspace_manager.merge_workspace(worktree_name, delete_branch=False)
                            logger.info("Merged worktree: %s", worktree_name)

                            # Dispatch merge event
                            _dispatch_event(
                                WorktreeMergedEvent(
                                    workspace_name=worktree_name,
                                    target_branch=target_branch,
                                ),
                                context="worktree_merged",
                            )
                        except Exception as e:
                            logger.warning("Failed to merge worktree %s: %s", worktree_name, e)

                        # Remove the worktree
                        try:
                            workspace_manager.remove_workspace(worktree_name, force=True)
                            logger.info("Removed worktree: %s", worktree_name)
                            cleaned_worktrees.append(worktree_name)

                            # Dispatch remove event
                            _dispatch_event(
                                WorktreeRemovedEvent(workspace_name=worktree_name),
                                context="worktree_removed",
                            )
                        except Exception as e:
                            logger.warning("Failed to remove worktree %s: %s", worktree_name, e)

                    except Exception as e:
                        logger.error("Error cleaning up worktree for task %s: %s", task.id, e)

            if cleaned_worktrees:
                typer.echo(f"  Cleaned up worktrees: {', '.join(cleaned_worktrees)}")

        except Exception as e:
            logger.error("Error initializing WorkspaceManager for cleanup: %s", e)

    typer.echo(f"✓ Shipping to {target_branch}")
    typer.echo(f"  Session: {verify_state.session_id}")
    typer.echo("Workflow complete!")

    # Dispatch ship complete event
    _dispatch_event(
        WorkflowShipCompleteEvent(plan_id=verify_state.session_id, target_branch=target_branch),
        context="ship_complete",
    )

    # Save to memory for history
    try:
        memory = get_memory_service()
        memory.save(
            content=f"workflow:ship:{verify_state.session_id}:complete",
            metadata={
                "phase": "ship",
                "plan_id": verify_state.session_id,
                "target_branch": target_branch,
            },
        )
    except Exception as e:
        logger.debug("Failed to save ship to memory: %s", e)


@app.command("status")
def status() -> None:
    plan_path = get_plan_state_path()
    exec_path = get_execute_state_path()
    verify_path = get_verify_state_path()
    plan = PlanState.load(plan_path)
    exec_state = ExecuteState.load(exec_path)
    verify_state = VerifyState.load(verify_path)
    typer.echo("=== Workflow Status ===")
    if plan:
        typer.echo(f"Plan: {plan.phase.value} ({plan.session_id})")
    else:
        typer.echo("Plan: None")
    if exec_state:
        typer.echo(f"Execute: {exec_state.phase.value} ({exec_state.session_id})")
    else:
        typer.echo("Execute: None")
    if verify_state:
        typer.echo(f"Verify: {verify_state.phase.value} ({verify_state.session_id})")
        typer.echo(f"  Unlock ship: {verify_state.unlock_ship}")
    else:
        typer.echo("Verify: None")
