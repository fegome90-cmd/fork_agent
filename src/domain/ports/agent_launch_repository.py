"""Port for agent launch registry persistence."""

from __future__ import annotations

from typing import Protocol

from src.domain.entities.agent_launch import AgentLaunch, LaunchStatus


class AgentLaunchRepository(Protocol):
    """Protocol for the canonical agent launch registry.

    This is the ONLY store that determines whether a launch may proceed.
    All launch surfaces MUST consult this registry before spawning any process.
    """

    def claim(
        self,
        launch_id: str,
        canonical_key: str,
        surface: str,
        owner_type: str,
        owner_id: str,
        lease_expires_at: int,
        *,
        role: str | None = None,
        parent_launch_id: str | None = None,
        model: str | None = None,
    ) -> AgentLaunch | None:
        """Atomically claim a RESERVED launch slot for a canonical key.

        Returns the new AgentLaunch if the claim succeeded (no active launch
        exists for the same canonical key), or None if a blocking launch already
        exists.

        The claim is atomic via the unique partial index on (canonical_key)
        WHERE status IN blocking states. If the INSERT violates the constraint,
        None is returned — no retry, no exception.
        """
        ...

    def get_by_launch_id(self, launch_id: str) -> AgentLaunch | None:
        """Retrieve a launch record by its stable launch_id."""
        ...

    def find_active_by_canonical_key(self, canonical_key: str) -> AgentLaunch | None:
        """Find the active (blocking) launch for a canonical key, if any."""
        ...

    def cas_update_status(
        self,
        launch_id: str,
        expected_status: LaunchStatus,
        new_status: LaunchStatus,
        *,
        error: str | None = None,
        quarantine_reason: str | None = None,
        backend: str | None = None,
        termination_handle_type: str | None = None,
        termination_handle_value: str | None = None,
        process_pid: int | None = None,
        process_pgid: int | None = None,
        tmux_session: str | None = None,
        tmux_pane_id: str | None = None,
        output_artifact: str | None = None,
        clear_lease: bool = False,
    ) -> bool:
        """CAS update — only succeeds if current status matches expected_status.

        Returns True if the row was updated, False if the CAS guard failed.
        Atomically updates status and any provided metadata fields.

        When clear_lease is True, lease_expires_at is set to NULL (no lease).
        This is used when transitioning to ACTIVE — managed launches should
        never auto-expire.
        """
        ...

    def list_by_status(self, status: LaunchStatus) -> list[AgentLaunch]:
        """List all launches in a given status."""
        ...

    def list_expired_leases(self, now_ms: int) -> list[AgentLaunch]:
        """Find launches with lease_expires_at <= now_ms that are still in blocking states."""
        ...

    def count_by_status(self) -> dict[str, int]:
        """Return counts grouped by status."""
        ...
