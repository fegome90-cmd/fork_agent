"""Agent launch entity — canonical lifecycle ownership for agent spawns."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

# Canonical key must be alphanumeric, dots, hyphens, underscores, colons, slashes.
# Max 256 chars. Rejects control chars, null bytes, newlines.
_CANONICAL_KEY_RE: Final[re.Pattern[str]] = re.compile(r"^[a-zA-Z0-9._:/-]{1,256}$")
_MAX_OWNER_ID_LENGTH: Final[int] = 1024
_VALID_OWNER_TYPES: Final[frozenset[str]] = frozenset({"agent", "session", "task", "run", "batch"})


class LaunchStatus(StrEnum):
    """Canonical lifecycle states for agent launch ownership."""

    RESERVED = "RESERVED"
    SPAWNING = "SPAWNING"
    ACTIVE = "ACTIVE"
    TERMINATING = "TERMINATING"
    TERMINATED = "TERMINATED"
    FAILED = "FAILED"
    SUPPRESSED_DUPLICATE = (
        "SUPPRESSED_DUPLICATE"  # Reserved for internal dedup — not set via public API
    )
    QUARANTINED = "QUARANTINED"


# States that block duplicate launches for the same canonical key.
BLOCKING_STATUSES: frozenset[LaunchStatus] = frozenset(
    {
        LaunchStatus.RESERVED,
        LaunchStatus.SPAWNING,
        LaunchStatus.ACTIVE,
        LaunchStatus.TERMINATING,
        LaunchStatus.QUARANTINED,
    }
)

# States that are terminal — no further transitions allowed.
TERMINAL_STATUSES: frozenset[LaunchStatus] = frozenset(
    {
        LaunchStatus.TERMINATED,
        LaunchStatus.FAILED,
        LaunchStatus.SUPPRESSED_DUPLICATE,
    }
)

_VALID_TRANSITIONS: dict[LaunchStatus, set[LaunchStatus]] = {
    LaunchStatus.RESERVED: {
        LaunchStatus.SPAWNING,
        LaunchStatus.FAILED,
        LaunchStatus.QUARANTINED,
    },
    LaunchStatus.SPAWNING: {
        LaunchStatus.ACTIVE,
        LaunchStatus.FAILED,
        LaunchStatus.QUARANTINED,
    },
    LaunchStatus.ACTIVE: {
        LaunchStatus.TERMINATING,
        LaunchStatus.FAILED,
        LaunchStatus.QUARANTINED,
    },
    LaunchStatus.TERMINATING: {
        LaunchStatus.TERMINATED,
        LaunchStatus.FAILED,
    },
    LaunchStatus.QUARANTINED: {
        LaunchStatus.FAILED,
        LaunchStatus.TERMINATED,
    },
    LaunchStatus.TERMINATED: set(),
    LaunchStatus.FAILED: set(),
    LaunchStatus.SUPPRESSED_DUPLICATE: set(),
}


@dataclass(frozen=True)
class AgentLaunch:
    """Immutable agent launch record — canonical ownership for one spawn attempt.

    Attributes:
        launch_id: Stable UUID4 identifier.
        canonical_key: Deduplication key derived from the logical work item.
        surface: Source surface (polling, workflow, api, manager, bug_hunt).
        owner_type: Kind of canonical work item (task, run, session, batch).
        owner_id: Domain identifier for the canonical item.
        status: Current lifecycle status.
        backend: Launch backend (tmux, subprocess).
        created_at: Unix epoch ms when the launch was requested.
        reserved_at: Unix epoch ms when ownership was claimed.
        spawn_started_at: Unix epoch ms when process creation started.
        spawn_confirmed_at: Unix epoch ms when the backend was confirmed alive.
        ended_at: Unix epoch ms when cleanup or terminal completion finished.
        lease_expires_at: Safety cutoff for in-flight work.
        termination_handle_type: Type of termination handle.
        termination_handle_value: Actual handle value for cleanup.
        process_pid: Detached subprocess PID, when applicable.
        process_pgid: Process group ID, when applicable.
        tmux_session: Tmux session name, when applicable.
        tmux_pane_id: Tmux pane id, when applicable.
        prompt_digest: Hash of the effective launch prompt.
        request_fingerprint: Fingerprint for spotting identical repeated requests.
        last_error: Last failure detail.
        quarantine_reason: Why a record was blocked from relaunch.
        parent_launch_id: Optional UUID of the parent launch (delegation lineage).
        role: Orchestrator role (e.g., explorer, architect, implementer).
        model: Assigned LLM model identifier.
        output_artifact: Path to the written output artifact file.
    """

    launch_id: str
    canonical_key: str
    surface: str
    owner_type: str
    owner_id: str
    status: LaunchStatus
    backend: str | None = None
    created_at: int | None = None
    reserved_at: int | None = None
    spawn_started_at: int | None = None
    spawn_confirmed_at: int | None = None
    ended_at: int | None = None
    lease_expires_at: int | None = None
    termination_handle_type: str | None = None
    termination_handle_value: str | None = None
    process_pid: int | None = None
    process_pgid: int | None = None
    tmux_session: str | None = None
    tmux_pane_id: str | None = None
    prompt_digest: str | None = None
    request_fingerprint: str | None = None
    last_error: str | None = None
    quarantine_reason: str | None = None
    parent_launch_id: str | None = None
    role: str | None = None
    model: str | None = None
    output_artifact: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.launch_id, str) or not self.launch_id:
            raise ValueError("launch_id must be a non-empty string")
        if not isinstance(self.canonical_key, str) or not self.canonical_key:
            raise ValueError("canonical_key must be a non-empty string")
        if not _CANONICAL_KEY_RE.match(self.canonical_key):
            raise ValueError(
                f"canonical_key must match {_CANONICAL_KEY_RE.pattern} (got {self.canonical_key!r})"
            )
        if not isinstance(self.status, LaunchStatus):
            raise TypeError("status must be a LaunchStatus")
        if not isinstance(self.owner_id, str) or not self.owner_id:
            raise ValueError("owner_id must be a non-empty string")
        if len(self.owner_id) > _MAX_OWNER_ID_LENGTH:
            raise ValueError(
                f"owner_id must be <= {_MAX_OWNER_ID_LENGTH} chars (got {len(self.owner_id)})"
            )
        if self.owner_type not in _VALID_OWNER_TYPES:
            raise ValueError(
                f"owner_type must be one of {sorted(_VALID_OWNER_TYPES)} (got {self.owner_type!r})"
            )
        if self.parent_launch_id is not None:
            if not self.parent_launch_id.strip():
                raise ValueError("parent_launch_id must be non-empty when provided")
            if self.parent_launch_id == self.launch_id:
                raise ValueError("parent_launch_id cannot equal launch_id (self-cycle)")
        for _fname, _fval in {
            "role": self.role,
            "model": self.model,
            "output_artifact": self.output_artifact,
        }.items():
            if _fval is not None and not _fval.strip():
                raise ValueError(f"{_fname} must be non-empty when provided")

    @property
    def display_name(self) -> str:
        """Human-readable label — NOT an authority.

        Format: {role}:{launch_id[:8]}
        """
        role_part = self.role or "unknown"
        return f"{role_part}:{self.launch_id[:8]}"

    def can_transition_to(self, target: LaunchStatus) -> bool:
        """Check if transitioning to target status is allowed."""
        return target in _VALID_TRANSITIONS.get(self.status, set())

    @property
    def is_blocking(self) -> bool:
        """Whether this launch blocks duplicate launches for the same canonical key."""
        return self.status in BLOCKING_STATUSES

    @property
    def is_terminal(self) -> bool:
        """Whether this launch is in a terminal state."""
        return self.status in TERMINAL_STATUSES

    @property
    def lease_is_valid(self) -> bool:
        """Whether the lease has not expired. Returns True if no lease is set."""
        if self.lease_expires_at is None:
            return True
        return int(time.time() * 1000) < self.lease_expires_at

    @property
    def termination_handle(self) -> dict[str, str | None]:
        """Extract termination handle as a typed dict for cleanup consumers."""
        return {
            "type": self.termination_handle_type,
            "value": self.termination_handle_value,
        }
