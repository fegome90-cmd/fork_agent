"""CLI commands for FPEL (Frozen Proposal Evidence Loop) operations."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console

from src.domain.entities.fpel import SealFailureReason

app = typer.Typer(help="FPEL: freeze, check, seal, and verify proposals.")
console = Console()

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

    Returns None when FPEL_ENABLED is not set — callers must handle this.
    """
    from src.infrastructure.persistence.container import get_fpel_service

    return get_fpel_service()


def _require_fpel_service():
    """Get FPEL service or exit with error if FPEL is disabled."""
    service = _get_fpel_service()
    if service is None:
        console.print("[red]Error: FPEL is disabled. Set FPEL_ENABLED=1 to enable.[/red]")
        raise typer.Exit(1)
    return service


@app.command("freeze")
def freeze_proposal(
    target_id: Annotated[str, typer.Option("--target-id", help="Target task or workflow ID")],
    content: Annotated[str, typer.Option("--content", help="Proposal content to freeze")],
) -> None:
    """Create an immutable frozen snapshot of a proposal."""

    service = _require_fpel_service()
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
