"""Launch lifecycle CLI commands — boundary contract for skill/repo integration.

Wraps AgentLaunchLifecycleService with a CLI interface that tmux-live can
call via subprocess. No Python imports required from the skill side.

Exit codes: 0=success, 1=failure/suppressed, 2=usage error
"""

from __future__ import annotations

import functools
import json
import logging
import signal
import sys
from collections.abc import Callable
from typing import Any

import typer

# Configure logging to send all library warnings/errors to stderr
logging.basicConfig(level=logging.WARNING, stream=sys.stderr, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

_VERSION = "1.0.0"

app = typer.Typer(
    name="launch",
    help="Agent launch lifecycle management.",
    no_args_is_help=True,
)


@app.callback(invoke_without_command=True)
def launch_main(
    version: bool = typer.Option(False, "--version", help="Show version"),
) -> None:
    """Agent launch lifecycle management."""
    if version:
        print(f"fork launch {_VERSION}")
        raise typer.Exit(0)


signal.signal(signal.SIGINT, lambda _s, _f: (_ for _ in ()).throw(typer.Exit(130)))


# ── Helpers ───────────────────────────────────────────────────


def _get_service():
    """Lazy import to avoid cold-start overhead."""
    from src.infrastructure.persistence.container import get_lifecycle_service

    return get_lifecycle_service()


def _output(data: dict, json_mode: bool) -> None:
    """Print result in JSON or human-readable format."""
    if json_mode:
        print(json.dumps(data, indent=2))
    else:
        parts = [f"decision={data.get('decision', 'n/a')}"]
        if data.get("launch_id"):
            parts.append(f"launch_id={data['launch_id']}")
        if data.get("status"):
            parts.append(f"status={data['status']}")
        if data.get("reason"):
            parts.append(f"reason={data['reason']}")
        print(" | ".join(parts))


def _output_error(msg: str, json_mode: bool) -> None:
    """Print error to stderr in human mode, stdout in JSON mode."""
    if json_mode:
        print(json.dumps({"decision": "error", "launch_id": None, "reason": msg}))
    else:
        print(f"Error: {msg}", file=sys.stderr)


def _lifecycle_command(fn: Callable[..., None]) -> Callable[..., None]:
    """Decorator: wraps command with error handling, stderr routing, and exit codes."""

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> None:
        try:
            fn(*args, **kwargs)
        except typer.Exit:
            raise
        except Exception as e:
            json_output = kwargs.get("json_output", False)
            _output_error(str(e), json_output)
            raise typer.Exit(1) from e

    return wrapper


# ── Commands ──────────────────────────────────────────────────


@app.command()
@_lifecycle_command
def request(
    canonical_key: str = typer.Option(..., "--canonical-key", help="Unique key for dedup"),
    surface: str = typer.Option(..., "--surface", help="Caller surface (skill, api, workflow)"),
    owner_type: str = typer.Option(..., "--owner-type", help="Owner type (agent, session)"),
    owner_id: str = typer.Option(..., "--owner-id", help="Owner identifier"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Request permission to launch an agent."""
    svc = _get_service()
    attempt = svc.request_launch(
        canonical_key=canonical_key,
        surface=surface,
        owner_type=owner_type,
        owner_id=owner_id,
    )
    data = {
        "decision": attempt.decision,
        "launch_id": attempt.launch.launch_id if attempt.launch else None,
        "reason": attempt.reason,
    }
    _output(data, json_output)
    raise typer.Exit(0 if attempt.decision == "claimed" else 1)


@app.command()
@_lifecycle_command
def confirm_spawning(
    launch_id: str = typer.Option(..., "--launch-id", help="Launch ID to confirm"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Confirm that spawn has started (RESERVED → SPAWNING)."""
    svc = _get_service()
    ok = svc.confirm_spawning(launch_id)
    _output(
        {
            "decision": None,
            "launch_id": launch_id,
            "status": "spawning" if ok else "cas_failed",
            "reason": None,
        },
        json_output,
    )
    raise typer.Exit(0 if ok else 1)


@app.command()
@_lifecycle_command
def confirm_active(
    launch_id: str = typer.Option(..., "--launch-id", help="Launch ID"),
    backend: str = typer.Option(..., "--backend", help="Backend type (tmux, process)"),
    termination_handle_type: str = typer.Option(
        ..., "--termination-handle-type", help="Handle type"
    ),
    termination_handle_value: str = typer.Option(
        ..., "--termination-handle-value", help="Handle value"
    ),
    tmux_session: str | None = typer.Option(None, "--tmux-session", help="tmux session name"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Confirm agent is running (SPAWNING → ACTIVE)."""
    svc = _get_service()
    ok = svc.confirm_active(
        launch_id,
        backend=backend,
        termination_handle_type=termination_handle_type,
        termination_handle_value=termination_handle_value,
        tmux_session=tmux_session,
    )
    _output(
        {
            "decision": None,
            "launch_id": launch_id,
            "status": "active" if ok else "cas_failed",
            "reason": None,
        },
        json_output,
    )
    raise typer.Exit(0 if ok else 1)


@app.command()
@_lifecycle_command
def mark_failed(
    launch_id: str = typer.Option(..., "--launch-id", help="Launch ID"),
    error: str = typer.Option(..., "--error", help="Error description"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Mark a launch as failed."""
    svc = _get_service()
    ok = svc.mark_failed(launch_id, error)
    _output(
        {
            "decision": None,
            "launch_id": launch_id,
            "status": "failed" if ok else "already_terminal",
            "reason": None,
        },
        json_output,
    )
    raise typer.Exit(0 if ok else 1)


@app.command()
@_lifecycle_command
def begin_termination(
    launch_id: str = typer.Option(..., "--launch-id", help="Launch ID"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Begin termination (ACTIVE → TERMINATING)."""
    svc = _get_service()
    ok = svc.begin_termination(launch_id)
    _output(
        {
            "decision": None,
            "launch_id": launch_id,
            "status": "terminating" if ok else "invalid_transition",
            "reason": None,
        },
        json_output,
    )
    raise typer.Exit(0 if ok else 1)


@app.command()
@_lifecycle_command
def confirm_terminated(
    launch_id: str = typer.Option(..., "--launch-id", help="Launch ID"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Confirm termination complete (TERMINATING → TERMINATED)."""
    svc = _get_service()
    ok = svc.confirm_terminated(launch_id)
    _output(
        {
            "decision": None,
            "launch_id": launch_id,
            "status": "terminated" if ok else "cas_failed",
            "reason": None,
        },
        json_output,
    )
    raise typer.Exit(0 if ok else 1)


@app.command()
@_lifecycle_command
def status(
    launch_id: str = typer.Option(..., "--launch-id", help="Launch ID"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Query launch status."""
    svc = _get_service()
    launch = svc.get_launch(launch_id)
    if launch is None:
        _output(
            {"decision": None, "launch_id": launch_id, "status": None, "reason": "not_found"},
            json_output,
        )
        raise typer.Exit(1)
    _output(
        {
            "decision": None,
            "launch_id": launch.launch_id,
            "status": launch.status.value,
            "reason": None,
            "error": launch.last_error,
        },
        json_output,
    )
    raise typer.Exit(0)


@app.command("list-active")
@_lifecycle_command
def list_active(
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """List all active (in-flight) launches."""
    svc = _get_service()
    launches = svc.list_active_launches()
    items = []
    for launch in launches:
        try:
            items.append(
                {
                    "launch_id": launch.launch_id,
                    "canonical_key": launch.canonical_key,
                    "surface": launch.surface,
                    "status": launch.status.value,
                    "tmux_session": launch.tmux_session,
                }
            )
        except Exception as e:
            if not json_output:
                print(f"Skipping malformed launch {launch.launch_id}: {e}", file=sys.stderr)
            continue

    if json_output:
        print(json.dumps(items, indent=2))
    else:
        if not items:
            print("No active launches.")
        for item in items:
            print(f"  {item['launch_id'][:12]}... {item['status']} {item['canonical_key']}")
    raise typer.Exit(0)


@app.command()
@_lifecycle_command
def summary(
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Show launch counts by status (operator dashboard)."""
    svc = _get_service()
    counts = svc.get_status_summary()
    if json_output:
        print(json.dumps(counts, indent=2))
    else:
        if not counts:
            print("No launches recorded.")
        for status_val, count in sorted(counts.items()):
            print(f"  {status_val:<24} {count}")
    raise typer.Exit(0)


@app.command("list-quarantined")
@_lifecycle_command
def list_quarantined(
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """List quarantined launches (operator triage)."""
    svc = _get_service()
    launches = svc.list_quarantined_launches()
    items = []
    for launch in launches:
        try:
            items.append(
                {
                    "launch_id": launch.launch_id,
                    "canonical_key": launch.canonical_key,
                    "surface": launch.surface,
                    "status": launch.status.value,
                    "quarantine_reason": launch.quarantine_reason,
                    "created_at": launch.created_at,
                }
            )
        except Exception as e:
            if not json_output:
                print(f"Skipping malformed launch {launch.launch_id}: {e}", file=sys.stderr)
            continue

    if json_output:
        print(json.dumps(items, indent=2))
    else:
        if not items:
            print("No quarantined launches.")
        for item in items:
            reason = item.get("quarantine_reason") or "unknown"
            print(f"  {item['launch_id'][:12]}... {item['canonical_key']} ({reason})")
    raise typer.Exit(0)
