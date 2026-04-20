"""Workflow commands for CLI."""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

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
    Task,
    VerifyResults,
    VerifyState,
    WorkflowPhase,
    get_execute_state_path,
    get_plan_state_path,
    get_state_dir,
    get_verify_state_path,
)
from src.application.services.workflow.verify_runner import verify_runner
from src.domain.entities.message import AgentMessage, MessageType
from src.infrastructure.persistence.container import (
    get_agent_messenger,
    get_memory_service,
    get_workspace_manager,
)
from src.interfaces.cli.dependencies import get_hook_service as _get_shared_hook_service

logger = logging.getLogger(__name__)


class ShipPreflightError(Exception):
    """Raised when ship preflight checks fail."""

    def __init__(
        self,
        message: str,
        *,
        current_branch: str,
        target_branch: str,
        dirty_files_count: int,
        mode: str,
        reason: str,
    ) -> None:
        super().__init__(message)
        self.current_branch = current_branch
        self.target_branch = target_branch
        self.dirty_files_count = dirty_files_count
        self.mode = mode
        self.reason = reason


def _get_hook_service() -> HookService:
    """Get HookService from ctx.obj if available (for testability), else use shared singleton."""
    try:
        ctx = typer.get_current_context()  # type: ignore[attr-defined]
        if isinstance(ctx.obj, dict):
            if "hook_service" not in ctx.obj:
                ctx.obj["hook_service"] = _get_shared_hook_service()
            return cast(HookService, ctx.obj["hook_service"])
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


def _slugify_task(text: str) -> str:
    """Create a safe slug for workflow task identifiers."""
    normalized = "".join(ch.lower() if ch.isalnum() else "-" for ch in text.strip())
    collapsed = "-".join(part for part in normalized.split("-") if part)
    return collapsed[:50] or "task"


def _send_workflow_message(phase: str, status: str, **kwargs: object) -> None:
    """Send a PROGRESS message to orchestrator:0 (best-effort, never blocks).

    Args:
        phase: Workflow phase (e.g., "execute", "verify").
        status: Status string (e.g., "agents_spawned", "completed").
        **kwargs: Additional fields included in the JSON payload.
    """
    import json

    try:
        payload = json.dumps({"phase": phase, "status": status, **kwargs})
        messenger = get_agent_messenger()
        msg = AgentMessage.create(
            from_agent="workflow:0",
            to_agent="orchestrator:0",
            message_type=MessageType.PROGRESS,
            payload=payload,
        )
        messenger.send(msg)
        logger.debug("Sent workflow message: %s %s", phase, status)
    except Exception as e:
        logger.debug("Failed to send workflow message [%s:%s]: %s", phase, status, e)


def _record_ship_event(event_name: str, metadata: dict[str, object]) -> None:
    """Persist ship lifecycle metadata to memory store (best effort)."""
    try:
        memory = get_memory_service()
        memory.save(content=f"workflow:ship:{event_name}", metadata=metadata)
    except Exception as e:
        logger.debug("Failed to save ship event %s: %s", event_name, e)


def _check_plan_exists() -> PlanState:
    plan_path = get_plan_state_path()
    plan = PlanState.load(plan_path)
    if plan is None:
        typer.echo("Error: No plan found. Run 'memory workflow outline' first.", err=True)
        raise typer.Exit(1)  # noqa: B904
    return plan


def _check_execute_exists() -> ExecuteState:
    exec_path = get_execute_state_path()
    state = ExecuteState.load(exec_path)
    if state is None:
        typer.echo("Error: No execution found. Run 'memory workflow execute' first.", err=True)
        raise typer.Exit(1)  # noqa: B904
    return state


def _check_verify_exists() -> VerifyState:
    verify_path = get_verify_state_path()
    state = VerifyState.load(verify_path)
    if state is None:
        typer.echo("Error: No verification found. Run 'memory workflow verify' first.", err=True)
        raise typer.Exit(1)  # noqa: B904
    return state


def _git_output(args: list[str]) -> str | None:
    """Run a git command and return stdout, or None on failure."""
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _get_current_branch() -> str | None:
    """Return current git branch name, or None if unavailable."""
    return _git_output(["rev-parse", "--abbrev-ref", "HEAD"])


def _get_dirty_files() -> list[str]:
    """Return dirty/untracked files from git status --porcelain."""
    output = _git_output(["status", "--porcelain"])
    if not output:
        return []

    files: list[str] = []
    for line in output.splitlines():
        candidate = line[3:].strip() if len(line) >= 4 else line.strip()
        if " -> " in candidate:
            candidate = candidate.split(" -> ", 1)[1]
        if candidate:
            files.append(candidate)
    return files


def _is_branch_checked_out_in_worktree(target_branch: str) -> bool:
    """Return True when target branch is already checked out in any worktree."""
    output = _git_output(["worktree", "list", "--porcelain"])
    if not output:
        return False

    target_ref = f"refs/heads/{target_branch}"
    for line in output.splitlines():
        if line.startswith("branch ") and line.split(" ", 1)[1] == target_ref:
            return True
    return False


def _enforce_ship_checkout_preflight(target_branch: str, use_worktree: bool) -> None:
    """Fail fast when cross-branch shipping prerequisites are not met."""
    current_branch = _get_current_branch()
    if current_branch is None or current_branch == target_branch:
        return

    dirty_files = _get_dirty_files()
    dirty_count = len(dirty_files)

    if dirty_count > 0 and not use_worktree:
        typer.echo(
            f"Error: Cannot ship to '{target_branch}' from '{current_branch}' with local changes.",
            err=True,
        )
        typer.echo(
            "Git would block checkout because files may be overwritten.",
            err=True,
        )
        typer.echo("Dirty files (showing up to 10):", err=True)
        for file_path in dirty_files[:10]:
            typer.echo(f"  - {file_path}", err=True)
        if dirty_count > 10:
            typer.echo(f"  ... and {dirty_count - 10} more", err=True)
        typer.echo("Options:", err=True)
        typer.echo("  1) Commit/stash your changes", err=True)
        typer.echo(f"  2) Re-run with --target {current_branch} (or --inplace)", err=True)
        typer.echo("  3) Re-run with --use-worktree", err=True)
        raise ShipPreflightError(
            "dirty_worktree_cross_branch",
            current_branch=current_branch,
            target_branch=target_branch,
            dirty_files_count=dirty_count,
            mode="no-worktree",
            reason="dirty_worktree_cross_branch",
        )

    if use_worktree and _is_branch_checked_out_in_worktree(target_branch):
        typer.echo(
            f"Error: Target branch '{target_branch}' is already checked out in another worktree.",
            err=True,
        )
        typer.echo("Close that worktree or re-run with --no-worktree and a clean tree.", err=True)
        raise ShipPreflightError(
            "target_branch_checked_out",
            current_branch=current_branch,
            target_branch=target_branch,
            dirty_files_count=dirty_count,
            mode="worktree",
            reason="target_branch_checked_out",
        )


def _merge_branch_via_temp_worktree(branch_name: str, target_branch: str) -> None:
    """Merge branch into target using temporary git worktree."""
    repo_root = _git_output(["rev-parse", "--show-toplevel"])
    if repo_root is None:
        raise RuntimeError("Unable to detect git repository root") from None
    temp_dir = Path(tempfile.mkdtemp(prefix="workflow-ship-"))
    try:
        add_result = subprocess.run(
            ["git", "-C", repo_root, "worktree", "add", str(temp_dir), target_branch],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if add_result.returncode != 0:
            raise RuntimeError(add_result.stderr.strip() or "git worktree add failed")

        merge_result = subprocess.run(
            ["git", "-C", str(temp_dir), "merge", branch_name, "--no-edit"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if merge_result.returncode != 0:
            subprocess.run(
                ["git", "-C", str(temp_dir), "merge", "--abort"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            raise RuntimeError(merge_result.stderr.strip() or "git merge failed")
    finally:
        subprocess.run(
            ["git", "-C", repo_root, "worktree", "remove", str(temp_dir), "--force"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        shutil.rmtree(temp_dir, ignore_errors=True)


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

    plan_task = Task(
        id=f"task-{uuid.uuid4().hex[:8]}",
        slug=_slugify_task(task_description),
        description=task_description,
    )
    plan_state = PlanState(
        session_id=session_id,
        status="outlined",
        phase=WorkflowPhase.OUTLINED,
        plan_file=plan_file,
        tasks=[plan_task],
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


# ZK


@app.command("execute")
def execute(
    task_id: str | None = typer.Argument(None, help="Specific task ID to execute"),
    parallel: bool = typer.Option(False, "--parallel", help="Run tasks in parallel"),
    model: str = typer.Option("opencode/glm-5-free", "--model", "-m", help="Agent model to use"),
    messaging: bool = typer.Option(
        False, "--messaging", help="Enable inter-agent messaging for coordination"
    ),
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

    # Send messaging notification if enabled
    if messaging:
        _send_workflow_message(
            "execute",
            "agents_spawned",
            count=len(result.spawned_sessions),
        )

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
    messaging: bool = typer.Option(
        False, "--messaging", help="Enable inter-agent messaging for coordination"
    ),
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
    test_results: VerifyResults = {}
    if run_tests:
        try:
            test_results = verify_runner.run()
            output_path = get_state_dir() / "verify-output.txt"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            # Run again to capture output (or we could modify run() to return stdout)
            # For now, just note that output would be captured in a full implementation
        except Exception as e:
            logger.warning("Verify runner failed: %s", e)
            test_results = {"passed": False, "error": str(e)}
    verify_state = VerifyState(
        session_id=session_id,
        status="verified",
        phase=WorkflowPhase.VERIFIED,
        unlock_ship=True,
        test_results=test_results,
    )
    verify_state.save(verify_path)
    # Send messaging notification if enabled
    if messaging:
        passed = test_results.get("passed", True) if test_results else True
        _send_workflow_message("verify", "completed", passed=passed)

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
    target_branch: str = typer.Option(
        "main",
        "--target",
        "-t",
        "--branch",
        "-b",
        help="Target branch (deprecated alias: --branch)",
    ),
    inplace: bool = typer.Option(False, "--inplace", help="Use current branch as target"),
    cleanup: bool = typer.Option(True, "--cleanup/--no-cleanup", help="Cleanup worktrees"),
    use_worktree: bool = typer.Option(
        True,
        "--use-worktree/--no-worktree",
        help="Use temporary worktree for cross-branch merges",
    ),
    force: bool = typer.Option(False, "--force", help="Force ship without verification"),
    reason: str = typer.Option(
        "", "--reason", help="Reason for forced ship (required with --force)"
    ),
) -> None:
    argv = sys.argv
    used_target_flag = any(flag in argv for flag in ("--target", "-t", "--branch", "-b"))
    used_legacy_branch = any(flag in argv for flag in ("--branch", "-b"))

    if inplace and used_target_flag:
        typer.echo("Error: --inplace cannot be used with --target/--branch", err=True)
        raise typer.Exit(1)  # noqa: B904
    if used_legacy_branch:
        typer.echo("Warning: --branch is deprecated, use --target", err=True)

    if inplace:
        current = _get_current_branch()
        if current is None:
            typer.echo("Error: Cannot resolve current branch for --inplace", err=True)
            raise typer.Exit(1)  # noqa: B904
        target_branch = current

    # Handle --force: skip verification gate
    if force:
        if not reason.strip():
            typer.echo("Error: --force requires --reason", err=True)
            raise typer.Exit(1)  # noqa: B904
        # Create minimal verify_state for forced ship
        verify_state = VerifyState(
            session_id=f"forced-{uuid.uuid4().hex[:8]}",
            phase=WorkflowPhase.VERIFIED,
            unlock_ship=True,
        )
    else:
        verify_state = _check_verify_exists()

        # ExitGate: Validate verification passed
        test_results = verify_state.test_results
        # Empty test_results means --no-tests was used (user opted out)
        # This is allowed - treat as passed
        if not test_results:
            passed = True
            exit_code = 0
        else:
            passed = test_results.get("passed", False)
            exit_code = test_results.get("exit_code", -1)

        if not passed and exit_code != 0:
            typer.echo("Error: Tests failed, cannot ship", err=True)
            raise typer.Exit(1)  # noqa: B904
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
        raise typer.Exit(1)  # noqa: B904
    # Safety preflight: block cross-branch shipping when local changes are dirty
    try:
        _enforce_ship_checkout_preflight(target_branch, use_worktree)
    except ShipPreflightError as e:
        _record_ship_event(
            "preflight_failed",
            {
                "session_id": verify_state.session_id,
                "target_branch": e.target_branch,
                "current_branch": e.current_branch,
                "is_dirty": e.dirty_files_count > 0,
                "dirty_files_count": e.dirty_files_count,
                "mode": e.mode,
                "reason": e.reason,
                "forced": force,
            },
        )
        raise typer.Exit(1)  # noqa: B904
    current_branch = _get_current_branch() or "unknown"
    dirty_files_count = len(_get_dirty_files())
    cross_branch = current_branch != target_branch
    ship_mode = "worktree" if use_worktree and cross_branch else "inplace"

    if force:
        _record_ship_event(
            "forced",
            {
                "session_id": verify_state.session_id,
                "reason": reason,
                "timestamp": datetime.now(UTC).isoformat(),
                "forced_by": "cli",
                "current_branch": current_branch,
                "target_branch": target_branch,
                "is_dirty": dirty_files_count > 0,
                "dirty_files_count": dirty_files_count,
                "mode": ship_mode,
            },
        )
        typer.echo("Warning: Forced ship executed (audit event logged)")

    _record_ship_event(
        "started",
        {
            "session_id": verify_state.session_id,
            "target_branch": target_branch,
            "current_branch": current_branch,
            "is_dirty": dirty_files_count > 0,
            "dirty_files_count": dirty_files_count,
            "mode": ship_mode,
            "forced": force,
        },
    )

    # Note: plan check not needed here, verify already validated the workflow

    # Dispatch ship start event
    _dispatch_event(
        WorkflowShipStartEvent(plan_id=verify_state.session_id, target_branch=target_branch),
        context="ship_start",
    )

    exec_path = get_execute_state_path()
    exec_state = ExecuteState.load(exec_path)

    # Cleanup worktrees if requested
    runtime_errors: list[str] = []
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
                            current_branch = _get_current_branch() or "unknown"
                            cross_branch = current_branch != target_branch
                            if use_worktree and cross_branch:
                                _merge_branch_via_temp_worktree(worktree_name, target_branch)
                            else:
                                workspace_manager.merge_workspace(
                                    worktree_name,
                                    target_branch=target_branch,
                                    delete_branch=False,
                                )
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
                            runtime_errors.append(f"merge:{worktree_name}")

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
                            runtime_errors.append(f"remove:{worktree_name}")

                    except Exception as e:
                        logger.error("Error cleaning up worktree for task %s: %s", task.id, e)
                        runtime_errors.append(f"cleanup:{task.id}")

            if cleaned_worktrees:
                typer.echo(f"  Cleaned up worktrees: {', '.join(cleaned_worktrees)}")

        except Exception as e:
            logger.error("Error initializing WorkspaceManager for cleanup: %s", e)
            runtime_errors.append("cleanup:init")

    if runtime_errors:
        _record_ship_event(
            "failed_runtime",
            {
                "session_id": verify_state.session_id,
                "target_branch": target_branch,
                "current_branch": current_branch,
                "is_dirty": dirty_files_count > 0,
                "dirty_files_count": dirty_files_count,
                "mode": ship_mode,
                "error_count": len(runtime_errors),
                "forced": force,
            },
        )
        typer.echo("Error: Ship failed during runtime operations", err=True)
        raise typer.Exit(1)  # noqa: B904
    typer.echo(f"✓ Shipping to {target_branch}")
    typer.echo(f"  Session: {verify_state.session_id}")
    typer.echo("Workflow complete!")

    # Dispatch ship complete event
    _dispatch_event(
        WorkflowShipCompleteEvent(plan_id=verify_state.session_id, target_branch=target_branch),
        context="ship_complete",
    )

    _record_ship_event(
        "completed",
        {
            "phase": "ship",
            "plan_id": verify_state.session_id,
            "target_branch": target_branch,
            "current_branch": current_branch,
            "is_dirty": dirty_files_count > 0,
            "dirty_files_count": dirty_files_count,
            "mode": ship_mode,
            "forced": force,
        },
    )


@app.command("bug-hunt")
def bug_hunt(
    agents: str = typer.Option(
        "all", "--agents", "-a", help="Agent roles: ripper, walker, sniper, or all"
    ),
    intensity: str = typer.Option("standard", "--intensity", "-i", help="quick, standard, or deep"),
    subsystems: str = typer.Option(
        "", "--subsystems", "-s", help="Comma-separated subsystems to test"
    ),
    auto: bool = typer.Option(False, "--auto", help="Run without confirmation prompts"),
) -> None:
    """Launch parallel bug-hunt agents against the project.

    Spawns 3 adversarial agents (ripper, walker, sniper) via tmux-live
    that execute real CLI commands to find bugs that unit tests miss.
    Requires: tmux-live on PATH, memory CLI available.

    Agents:
      ripper  — adversarial inputs, PII, injection, encoding attacks
      walker  — multi-step workflows, roundtrips, real-world usage
      sniper  — cross-project isolation, boundaries, edge cases

    Intensity levels:
      quick    — 1 agent (ripper only), focused scenarios
      standard — 3 agents, full scenario catalog
      deep     — 3 agents, extended scenarios + follow-up rounds
    """

    # Pre-flight checks
    if not shutil.which("tmux-live"):
        typer.echo("Error: tmux-live not found on PATH. Install tmux-fork-orchestrator.", err=True)
        raise typer.Exit(1)

    if not shutil.which("memory"):
        typer.echo("Error: memory CLI not found. Run 'uv tool install .'", err=True)
        raise typer.Exit(1)

    # Resolve agent roles
    valid_agents = {"ripper", "walker", "sniper"}
    if agents == "all":
        selected_agents = valid_agents
    else:
        selected_agents = {a.strip() for a in agents.split(",") if a.strip() in valid_agents}
        if not selected_agents:
            typer.echo(f"Error: No valid agents. Use: {', '.join(valid_agents)} or 'all'", err=True)
            raise typer.Exit(1)

    # Quick mode: single agent only
    if intensity == "quick":
        selected_agents = {"ripper"}

    # Record hunt session
    hunt_id = uuid.uuid4().hex[:8]
    hunt_date = datetime.now(UTC).strftime("%Y-%m-%d")
    topic_key = f"bug-hunt/{hunt_date}/{hunt_id}"

    typer.echo(f"""
=== Bug Hunt: {hunt_id} ===
  Agents: {", ".join(sorted(selected_agents))}
  Intensity: {intensity}
  Subsystems: {subsystems or "all"}
  Topic key: {topic_key}
""")

    if not auto:
        confirm = input("Launch agents? [y/N] ")
        if confirm.lower() != "y":
            typer.echo("Aborted.")
            raise typer.Exit(0)

    # Initialize tmux-live orchestrator
    try:
        result = subprocess.run(
            ["tmux-live", "init", str(len(selected_agents) + 1)],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            pass  # tmux-live initialized successfully
        else:
            typer.echo(f"Warning: tmux-live not available ({result.stderr.strip()})", err=True)
            typer.echo(
                "Hint: Run inside tmux for agent spawning. Use 'memory workflow bug-hunt --help'",
                err=True,
            )
            typer.echo("       to see what would run.", err=True)
            raise typer.Exit(1)
    except FileNotFoundError:
        typer.echo("Error: tmux-live not found on PATH. Install from tmux_fork skills.", err=True)
        raise typer.Exit(1) from None

    # Agent role → tmux-live role mapping
    role_map = {
        "ripper": "explorer",
        "walker": "implementer",
        "sniper": "verifier",
    }

    # Agent-specific instructions — loaded from real-world-bug-hunter skill resources
    skill_root = Path.home() / ".pi" / "agent" / "skills" / "real-world-bug-hunter"
    agent_resource_map = {
        "ripper": skill_root / "resources" / "agent-ripper.md",
        "walker": skill_root / "resources" / "agent-walker.md",
        "sniper": skill_root / "resources" / "agent-sniper.md",
    }
    test_catalog_path = skill_root / "resources" / "test-catalog.md"

    agent_instructions: dict[str, str] = {}
    for agent_name in selected_agents:
        resource_path = agent_resource_map[agent_name]
        if resource_path.exists():
            agent_instructions[agent_name] = resource_path.read_text()
        else:
            # Fallback: minimal instructions
            logger.warning("Skill resource not found: %s", resource_path)
            agent_instructions[agent_name] = (
                f"You are the {agent_name.upper()} agent. Find bugs in memory CLI."
            )

    # Load test catalog (shared across all agents)
    test_catalog = ""
    if test_catalog_path.exists():
        test_catalog = test_catalog_path.read_text()

    # Spawn agents
    spawned = []
    for agent_name in sorted(selected_agents):
        tmux_role = role_map[agent_name]
        prompt_path = f"/tmp/hunt-prompt-{agent_name}-{hunt_id}.txt"

        # Build agent prompt from skill resource + catalog + project context
        subsystem_filter = f"\nFocus on subsystems: {subsystems}" if subsystems else ""
        prompt = f"""{agent_instructions[agent_name]}

# Test Catalog
{test_catalog}

# Project Context
Project directory: {Path.cwd()}
Hunt ID: {hunt_id}
Intensity: {intensity}{subsystem_filter}

## Output
Write findings to /tmp/hunt-findings-{agent_name}-{hunt_id}.md
When done, write ## HUNT_COMPLETE ## as last line.
"""

        with open(prompt_path, "w") as f:
            f.write(prompt)

        full_name = f"hunt-{agent_name}-{hunt_id}"
        result = subprocess.run(
            ["tmux-live", "launch", tmux_role, full_name, f"@{prompt_path}"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            typer.echo(f"  ✅ Spawned {agent_name} ({full_name})")
            spawned.append(full_name)
        else:
            typer.echo(f"  ❌ Failed to spawn {agent_name}: {result.stderr.strip()}", err=True)

    if not spawned:
        typer.echo("Error: No agents spawned. Aborting.", err=True)
        raise typer.Exit(1)

    typer.echo(f"\n{len(spawned)} agents running. Monitoring...")

    # Wait for all agents
    for name in spawned:
        typer.echo(f"  Waiting for {name}...")
        subprocess.run(["tmux-live", "wait", name, "600"], capture_output=True)

    # Consolidate findings
    typer.echo("\n=== Consolidating Findings ===")
    findings_dir = f"/tmp/hunt-findings-{hunt_id}"
    Path(findings_dir).mkdir(exist_ok=True)

    all_findings: list[dict[str, str | int]] = []
    for agent_name in sorted(selected_agents):
        src = f"/tmp/hunt-findings-{agent_name}-{hunt_id}.md"
        dst = f"{findings_dir}/hunt-findings-{agent_name}.md"
        if Path(src).exists():
            shutil.copy2(src, dst)
            content = Path(src).read_text()
            bugs = content.count("## Bug #")
            typer.echo(f"  {agent_name}: {bugs} bugs found")
            all_findings.append({"agent": agent_name, "bugs": bugs, "file": dst})
        else:
            typer.echo(f"  {agent_name}: no findings file")

    # Run hunt-consolidate if available
    report_path = f"/tmp/hunt-report-{hunt_id}.md"
    consolidate_script = skill_root / "scripts" / "hunt-consolidate"
    if consolidate_script.exists() and all_findings:
        result = subprocess.run(
            [str(consolidate_script), findings_dir, report_path],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and Path(report_path).exists():
            typer.echo(f"  Consolidated report: {report_path}")
        else:
            typer.echo(f"  Consolidation warning: {result.stderr[:200]}", err=True)

    # Count severity from structured headers [AGENT-NNN] SEVERITY
    critical_count = 0
    high_count = 0
    for finding in all_findings:
        finding_file = cast(str, finding["file"])
        if Path(finding_file).exists():
            text = Path(finding_file).read_text()
            critical_count += len(re.findall(r"^\[[A-Z]+-[0-9]+\] +CRITICAL\b", text, re.MULTILINE))
            high_count += len(re.findall(r"^\[[A-Z]+-[0-9]+\] +HIGH\b", text, re.MULTILINE))

    # Save consolidated report
    total_bugs = sum(cast(int, finding["bugs"]) for finding in all_findings)
    report = f"Bug hunt {hunt_id}: {total_bugs} bugs found by {len(spawned)} agents."

    # Include consolidated report if available
    report_content = report
    if Path(report_path).exists():
        report_content = Path(report_path).read_text()

    try:
        svc = get_memory_service()
        svc.save(
            content=report_content,
            type="session-summary",
            project=Path.cwd().name,
            topic_key=topic_key,
            metadata={
                "hunt_id": hunt_id,
                "agents": list(selected_agents),
                "total_bugs": total_bugs,
                "critical": critical_count,
                "high": high_count,
            },
        )
        typer.echo(f"\nReport saved: {topic_key}")
    except Exception as e:
        typer.echo(f"\nWarning: Could not save to memory: {e}", err=True)

    # Cleanup
    subprocess.run(["tmux-live", "kill-all"], capture_output=True)

    # Print verdict (using structured severity counts)
    if total_bugs == 0:
        typer.echo("\nVerdict: PASS — no bugs found.")
    elif critical_count > 0:
        typer.echo(
            f"\nVerdict: FAIL — {critical_count} CRITICAL bug(s) found. Fix before shipping."
        )
    elif high_count > 0:
        typer.echo(f"\nVerdict: PASS WITH WARNINGS — {high_count} HIGH-severity bug(s) found.")
    else:
        typer.echo(f"\nVerdict: PASS — {total_bugs} non-critical bugs found.")

    # Print summary of all findings
    for finding in all_findings:
        finding_file = cast(str, finding["file"])
        if Path(finding_file).exists():
            typer.echo(f"\n--- {finding['agent']} findings: {finding['file']} ---")


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
