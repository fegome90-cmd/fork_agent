"""CLI commands for FPEL (Frozen Proposal Evidence Loop) operations."""

from __future__ import annotations

import logging
from typing import Annotated, Literal

import typer
from rich.console import Console

from src.domain.entities.fpel import SealFailureReason

app = typer.Typer(help="FPEL: freeze, check, seal, and verify proposals.")
console = Console()
logger = logging.getLogger(__name__)

# Map SealFailureReason → unique CLI exit code
_SEAL_FAILURE_EXIT_CODES: dict[SealFailureReason, int] = {
    SealFailureReason.HASH_MISMATCH: 10,
    SealFailureReason.MISSING_REPORTS: 11,
    SealFailureReason.TERMINAL_FAIL: 12,
    SealFailureReason.POST_FREEZE_CHANGE: 13,
    SealFailureReason.NO_FROZEN_PROPOSAL: 14,
}


def seal_failure_exit_code(reason: SealFailureReason) -> int:
    """Map a SealFailureReason to a unique CLI exit code."""
    return _SEAL_FAILURE_EXIT_CODES[reason]


def _get_fpel_service():
    """Build FPELAuthorizationService via infrastructure container.

    Returns None when FPEL is disabled via FPEL_DISABLED=1 — callers must handle this.
    """
    from src.infrastructure.persistence.container import get_fpel_service

    return get_fpel_service()


def _require_fpel_service():
    """Get FPEL service or exit with error if FPEL is disabled."""
    service = _get_fpel_service()
    if service is None:
        console.print("[red]Error: FPEL is disabled via FPEL_DISABLED=1.[/red]")
        raise typer.Exit(1)
    return service


def _validate_target_id_match(
    target_id: str,
    source_id: str,
    source_type: Literal["task", "plan"],
    allow_mismatch: bool,
) -> tuple[bool, str]:
    """Validate target_id matches source entity ID.

    Returns (should_proceed, message):
      - (True, ""): IDs match, proceed silently.
      - (True, "Warning: ..."): IDs differ but allowed, proceed with warning.
      - (False, "Error: ..."): IDs differ and not allowed, abort.
    """
    if not target_id or target_id == source_id:
        return True, ""
    if allow_mismatch:
        return (
            True,
            f"Warning: --target-id ({target_id}) differs from "
            f"--from-{source_type} ({source_id}). Proceeding with --allow-target-mismatch.",
        )
    return (
        False,
        f"Error: --target-id ({target_id}) does not match "
        f"--from-{source_type} ({source_id}). Use --allow-target-mismatch to override.",
    )


@app.command("freeze")
def freeze_proposal(
    target_id: Annotated[str, typer.Option("--target-id", help="Target task or workflow ID")],
    content: Annotated[
        str | None,
        typer.Option(
            "--content", help="Raw content to freeze (low-level, not hash-authority compliant)"
        ),
    ] = None,
    from_task: Annotated[
        str | None,
        typer.Option("--from-task", help="Task ID — freeze with canonical hash from task board"),
    ] = None,
    from_plan: Annotated[
        str | None,
        typer.Option(
            "--from-plan", help="Plan session ID — freeze with canonical hash from plan state"
        ),
    ] = None,
    allow_target_mismatch: Annotated[
        bool,
        typer.Option(
            "--allow-target-mismatch",
            help="Allow target_id to differ from source ID",
        ),
    ] = False,
    allow_target_alias: Annotated[
        bool,
        typer.Option(
            "--allow-target-alias",
            hidden=True,
            help="Backward-compatible alias for --allow-target-mismatch",
        ),
    ] = False,
) -> None:
    """Create an immutable frozen snapshot of a proposal.

    Use --from-task or --from-plan for hash-authority compliant freeze
    (canonical hash matches what check_sealed() computes at runtime).
    Use --content for low-level/arbitrary content (not hash-authority compliant).
    """
    _allow_override = allow_target_mismatch or allow_target_alias
    sources = [content is not None, from_task is not None, from_plan is not None]
    if sum(sources) != 1:
        console.print(
            "[red]Error: Provide exactly one of --content, --from-task, --from-plan[/red]"
        )
        raise typer.Exit(1)

    service = _require_fpel_service()

    if from_task is not None:
        from src.infrastructure.persistence.container import get_container

        container = get_container()
        task_board = container.task_board_service()
        task = task_board.get(from_task)
        if task is None:
            console.print(f"[red]Error: Task '{from_task}' not found[/red]")
            raise typer.Exit(1)
        should_proceed, msg = _validate_target_id_match(
            target_id, from_task, "task", _allow_override
        )
        if not should_proceed:
            console.print(f"[red]{msg}[/red]")
            raise typer.Exit(1)
        if msg:
            console.print(f"[yellow]{msg}[/yellow]")
            logger.warning(
                "Target-ID mismatch override: target=%s source=%s type=%s",
                target_id,
                from_task,
                "task",
            )
        frozen = service.freeze_task(
            target_id=target_id,
            plan_text=task.plan_text,
            subject=task.subject,
            description=task.description,
        )
    elif from_plan is not None:
        from src.interfaces.cli.commands.workflow import get_plan_state_path

        plan_path = get_plan_state_path()
        if not plan_path.exists():
            console.print("[red]Error: No plan state found. Run 'workflow outline' first.[/red]")
            raise typer.Exit(1)
        from src.application.services.workflow.state import PlanState

        plan = PlanState.load(plan_path)
        if plan is None:
            console.print("[red]Error: Failed to load plan state.[/red]")
            raise typer.Exit(1)
        if plan.session_id != from_plan:
            console.print(
                f"[red]Error: Plan session_id '{plan.session_id}' does not match --from-plan '{from_plan}'[/red]"
            )
            raise typer.Exit(1)
        should_proceed, msg = _validate_target_id_match(
            target_id, from_plan, "plan", _allow_override
        )
        if not should_proceed:
            console.print(f"[red]{msg}[/red]")
            raise typer.Exit(1)
        if msg:
            console.print(f"[yellow]{msg}[/yellow]")
            logger.warning(
                "Target-ID mismatch override: target=%s source=%s type=%s",
                target_id,
                from_plan,
                "plan",
            )
        tasks_data = [
            {"id": t.id, "slug": t.slug, "description": t.description} for t in plan.tasks
        ]
        frozen = service.freeze_plan(target_id=target_id, tasks=tasks_data)
    else:
        # No guard: content route has no entity ID for comparison.
        frozen = service.freeze(target_id=target_id, content=content)

    console.print("[green]Proposal frozen.[/green]")
    console.print(f"  frozen_proposal_id: {frozen.frozen_proposal_id}")
    console.print(f"  content_hash:       {frozen.content_hash[:16]}...")
    console.print(f"  target_id:          {frozen.target_id}")


@app.command("check")
def check_proposal(
    target_id: Annotated[str, typer.Option("--target-id", help="Target to check")],
) -> None:
    """Run checks on a frozen proposal (writes evidence only, does NOT seal)."""
    service = _require_fpel_service()
    decision = service.check(target_id=target_id)
    console.print(f"  status: {decision.status.value}")
    if decision.reason:
        console.print(f"  reason: {decision.reason.value}")
    console.print(f"  frozen_proposal_id: {decision.frozen_proposal_id or 'N/A'}")


@app.command("seal")
def seal_proposal(
    target_id: Annotated[str, typer.Option("--target-id", help="Target to seal")],
) -> None:
    """Validate invariants and create sealed PASS, or report failure reason."""
    from src.domain.entities.fpel import SealedVerdict

    service = _require_fpel_service()
    result = service.seal(target_id=target_id)

    if isinstance(result, SealedVerdict):
        console.print("[green]Sealed PASS.[/green]")
        console.print(f"  frozen_proposal_id: {result.frozen_proposal_id}")
        console.print(f"  verdict:            {result.verdict}")
        console.print(f"  sealed_at:          {result.sealed_at.isoformat()}")
        console.print(f"  content_hash:       {result.content_hash[:16]}...")
    elif isinstance(result, SealFailureReason):
        exit_code = seal_failure_exit_code(result)
        console.print(f"[red]Seal denied: {result.value}[/red]")
        raise typer.Exit(exit_code)


@app.command("status")
def status_proposal(
    target_id: Annotated[str, typer.Option("--target-id", help="Target to check status")],
) -> None:
    """Report current FPEL authorization status."""
    service = _require_fpel_service()
    decision = service.check_sealed(target_id=target_id)

    console.print(f"  status:             {decision.status.value}")
    console.print(
        f"  content_hash:       {decision.content_hash[:8] + '...' if decision.content_hash else 'N/A'}"
    )
    console.print(f"  frozen_proposal_id: {decision.frozen_proposal_id or 'N/A'}")
    console.print(f"  sealed:             {decision.allowed}")
    if decision.reason:
        console.print(f"  blocking_reason:    {decision.reason.value}")
    if decision.sealed_at:
        console.print(f"  sealed_at:          {decision.sealed_at.isoformat()}")


@app.command("fail")
def fail_proposal(
    target_id: Annotated[
        str, typer.Option("--target-id", help="Target whose active proposal to fail")
    ],
    reason: Annotated[str | None, typer.Option("--reason", help="Optional failure reason")] = None,
) -> None:
    """Mark the active frozen proposal as failed (terminal state, no recovery)."""
    service = _require_fpel_service()

    try:
        frozen = service.mark_fail(target_id=target_id, reason=reason)
    except ValueError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(12) from exc

    console.print("[red]Proposal marked as FAILED.[/red]")
    console.print(f"  frozen_proposal_id: {frozen.frozen_proposal_id}")
    if reason:
        console.print(f"  reason:             {reason}")


@app.command("snapshot-legacy")
def snapshot_legacy(
    target_id: Annotated[str, typer.Option("--target-id", help="Target ID for legacy snapshot")],
    content: Annotated[
        str | None,
        typer.Option(
            "--content",
            help="Raw content (low-level, NOT hash-authority compliant)",
        ),
    ] = None,
    from_task: Annotated[
        str | None,
        typer.Option("--from-task", help="Task ID — snapshot with canonical task hash authority"),
    ] = None,
    from_plan: Annotated[
        str | None,
        typer.Option(
            "--from-plan", help="Plan session ID — snapshot with canonical plan hash authority"
        ),
    ] = None,
    allow_target_mismatch: Annotated[
        bool,
        typer.Option(
            "--allow-target-mismatch",
            help="Allow target_id to differ from source ID",
        ),
    ] = False,
    allow_target_alias: Annotated[
        bool,
        typer.Option(
            "--allow-target-alias",
            hidden=True,
            help="Backward-compatible alias for --allow-target-mismatch",
        ),
    ] = False,
) -> None:
    """Create a legacy-approved snapshot (freeze + seal with source=LEGACY_APPROVED).

    Use --from-task or --from-plan for hash-authority compliant snapshot
    (canonical hash matches what check_sealed() computes at runtime).
    Use --content for low-level/arbitrary content (NOT hash-authority compliant).
    """
    _allow_override = allow_target_mismatch or allow_target_alias
    sources = [content is not None, from_task is not None, from_plan is not None]
    if sum(sources) != 1:
        console.print(
            "[red]Error: Provide exactly one of --content, --from-task, --from-plan[/red]"
        )
        raise typer.Exit(1)

    service = _require_fpel_service()

    try:
        if content is not None:
            # No guard: content route has no entity ID for comparison.
            console.print(
                "[yellow]Warning: --content is NOT hash-authority compliant. "
                "Post-snapshot runtime checks may produce HASH_MISMATCH. "
                "Use --from-task or --from-plan for authority.[/yellow]"
            )
            frozen, sealed = service.snapshot_legacy(target_id=target_id, content=content)
        elif from_task is not None:
            from src.infrastructure.persistence.container import get_container

            container = get_container()
            task_board = container.task_board_service()
            task = task_board.get(from_task)
            if task is None:
                console.print(f"[red]Error: Task '{from_task}' not found[/red]")
                raise typer.Exit(1)
            should_proceed, msg = _validate_target_id_match(
                target_id, from_task, "task", _allow_override
            )
            if not should_proceed:
                console.print(f"[red]{msg}[/red]")
                raise typer.Exit(1)
            if msg:
                console.print(f"[yellow]{msg}[/yellow]")
                logger.warning(
                    "Target-ID mismatch override: target=%s source=%s type=%s",
                    target_id,
                    from_task,
                    "task",
                )
            frozen, sealed = service.snapshot_legacy_task(
                target_id=target_id,
                plan_text=task.plan_text,
                subject=task.subject,
                description=task.description,
            )
        else:
            from src.interfaces.cli.commands.workflow import get_plan_state_path

            plan_path = get_plan_state_path()
            if not plan_path.exists():
                console.print(
                    "[red]Error: No plan state found. Run 'workflow outline' first.[/red]"
                )
                raise typer.Exit(1)
            from src.application.services.workflow.state import PlanState

            plan = PlanState.load(plan_path)
            if plan is None:
                console.print("[red]Error: Failed to load plan state.[/red]")
                raise typer.Exit(1)
            if plan.session_id != from_plan:
                console.print(
                    f"[red]Error: Plan session_id '{plan.session_id}' does not match --from-plan '{from_plan}'[/red]"
                )
                raise typer.Exit(1)
            should_proceed, msg = _validate_target_id_match(
                target_id, from_plan, "plan", _allow_override
            )
            if not should_proceed:
                console.print(f"[red]{msg}[/red]")
                raise typer.Exit(1)
            if msg:
                console.print(f"[yellow]{msg}[/yellow]")
                logger.warning(
                    "Target-ID mismatch override: target=%s source=%s type=%s",
                    target_id,
                    from_plan,
                    "plan",
                )
            tasks_data = [
                {"id": t.id, "slug": t.slug, "description": t.description} for t in plan.tasks
            ]
            frozen, sealed = service.snapshot_legacy_plan(target_id=target_id, tasks=tasks_data)
    except ValueError as exc:
        msg = str(exc)
        console.print(f"[red]Error: {exc}[/red]")
        if "active unsealed" in msg:
            raise typer.Exit(13) from exc
        raise typer.Exit(12) from exc

    console.print("[green]Legacy snapshot created.[/green]")
    console.print(f"  frozen_proposal_id: {frozen.frozen_proposal_id}")
    console.print(f"  verdict:            {sealed.verdict}")
    console.print(f"  source:             {sealed.source}")
    console.print(f"  content_hash:       {sealed.content_hash[:16]}...")
