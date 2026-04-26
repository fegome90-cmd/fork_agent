"""Canonical agent launch lifecycle service — single owner for all spawn decisions.

This is the ONLY component allowed to answer:
1. May this canonical work item launch right now?
2. If yes, what exact launch record should be created?
3. Is the launch active, suppressed, quarantined, or terminal?

All launch surfaces (polling, workflow, API, manager, bug-hunt) MUST delegate
to this service before spawning any process.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from src.domain.entities.agent_launch import AgentLaunch, LaunchStatus

LaunchDecision = Literal["claimed", "suppressed", "error"]

if TYPE_CHECKING:
    from src.domain.ports.agent_launch_repository import AgentLaunchRepository

logger = logging.getLogger(__name__)

DEFAULT_LEASE_DURATION_MS: int = 300_000  # 5 minutes


@dataclass(frozen=True)
class LaunchAttempt:
    """Result of requesting a launch through the lifecycle service."""

    launch: AgentLaunch | None
    decision: LaunchDecision  # "claimed" | "suppressed" | "error"
    existing_launch: AgentLaunch | None = None
    reason: str | None = None


class AgentLaunchLifecycleService:
    """Application service owning claim → spawn → confirm → finalize → cleanup.

    This service is the canonical lifecycle owner. No other component should
    directly interact with the launch registry for spawn decisions.
    """

    __slots__ = ("_registry", "_lease_duration_ms")

    def __init__(
        self,
        registry: AgentLaunchRepository,
        lease_duration_ms: int = DEFAULT_LEASE_DURATION_MS,
    ) -> None:
        self._registry = registry
        self._lease_duration_ms = lease_duration_ms

    def request_launch(
        self,
        canonical_key: str,
        surface: str,
        owner_type: str,
        owner_id: str,
    ) -> LaunchAttempt:
        """Request permission to launch an agent for a canonical work item.

        Returns a LaunchAttempt indicating whether the caller may proceed.
        - decision="claimed": launch_id is claimed in RESERVED state, proceed with spawn.
        - decision="suppressed": an active launch already exists, do NOT spawn.
        - decision="error": unexpected registry failure, fail closed.
        """
        try:
            # Check for existing active launch first (fast path, avoids claim attempt)
            existing = self._registry.find_active_by_canonical_key(canonical_key)
            if existing is not None:
                if existing.lease_is_valid:
                    logger.info(
                        "LAUNCH_DECISION decision=suppressed canonical_key=%s"
                        " existing_launch=%s existing_status=%s surface=%s",
                        canonical_key,
                        existing.launch_id,
                        existing.status.value,
                        surface,
                    )
                    return LaunchAttempt(
                        launch=None,
                        decision="suppressed",
                        existing_launch=existing,
                        reason=f"Active launch {existing.launch_id} in status {existing.status.value}",
                    )
                # Lease expired but still blocking — quarantine it
                self._quarantine_expired(existing)

            # Attempt atomic claim
            launch_id = uuid.uuid4().hex
            now_ms = int(time.time() * 1000)
            lease_expires_at = now_ms + self._lease_duration_ms

            claimed = self._registry.claim(
                launch_id=launch_id,
                canonical_key=canonical_key,
                surface=surface,
                owner_type=owner_type,
                owner_id=owner_id,
                lease_expires_at=lease_expires_at,
            )

            if claimed is None:
                # Race condition: someone else claimed between our check and claim
                logger.info(
                    "LAUNCH_DECISION decision=suppressed canonical_key=%s"
                    " reason=claim_race surface=%s",
                    canonical_key,
                    surface,
                )
                winner = self._registry.find_active_by_canonical_key(canonical_key)
                return LaunchAttempt(
                    launch=None,
                    decision="suppressed",
                    existing_launch=winner,
                    reason="Concurrent claim won by another request",
                )

            logger.info(
                "LAUNCH_DECISION decision=claimed launch_id=%s canonical_key=%s"
                " surface=%s owner_type=%s owner_id=%s",
                claimed.launch_id,
                canonical_key,
                surface,
                owner_type,
                owner_id,
            )
            return LaunchAttempt(launch=claimed, decision="claimed")

        except Exception as e:
            # Registry unavailable — fail closed (spec REQ-FAIL-5)
            logger.error(
                "Registry error for canonical_key=%s: %s; failing closed",
                canonical_key,
                e,
            )
            return LaunchAttempt(
                launch=None,
                decision="error",
                reason=f"Registry error: {e}",
            )

    def confirm_spawning(self, launch_id: str) -> bool:
        """Transition from RESERVED to SPAWNING. Call when starting the actual spawn."""
        return self._registry.cas_update_status(
            launch_id,
            LaunchStatus.RESERVED,
            LaunchStatus.SPAWNING,
        )

    def confirm_active(
        self,
        launch_id: str,
        *,
        backend: str,
        termination_handle_type: str,
        termination_handle_value: str,
        tmux_pane_id: str | None = None,
        tmux_session: str | None = None,
        process_pid: int | None = None,
        process_pgid: int | None = None,
    ) -> bool:
        """Transition from SPAWNING to ACTIVE with termination metadata.

        This is the point where the launch is considered confirmed and safe.
        """
        result = self._registry.cas_update_status(
            launch_id,
            LaunchStatus.SPAWNING,
            LaunchStatus.ACTIVE,
            backend=backend,
            termination_handle_type=termination_handle_type,
            termination_handle_value=termination_handle_value,
            tmux_pane_id=tmux_pane_id,
            tmux_session=tmux_session,
            process_pid=process_pid,
            process_pgid=process_pgid,
        )
        if result:
            logger.info(
                "LAUNCH_DECISION decision=active launch_id=%s backend=%s"
                " handle_type=%s handle=%s tmux_session=%s",
                launch_id,
                backend,
                termination_handle_type,
                termination_handle_value,
                tmux_session,
            )
        return result

    def mark_failed(self, launch_id: str, error: str) -> bool:
        """Mark a launch as FAILED. Works from any non-terminal status."""
        launch = self._registry.get_by_launch_id(launch_id)
        if launch is None or launch.is_terminal:
            return False
        if not launch.can_transition_to(LaunchStatus.FAILED):
            return False
        result = self._registry.cas_update_status(
            launch_id,
            launch.status,
            LaunchStatus.FAILED,
            error=error,
        )
        if result:
            logger.info(
                "LAUNCH_DECISION decision=failed launch_id=%s canonical_key=%s error=%s",
                launch_id,
                launch.canonical_key,
                error[:200],
            )
        return result

    def begin_termination(self, launch_id: str) -> bool:
        """Transition to TERMINATING. Call before attempting cleanup.

        Only valid from ACTIVE state (also works from SPAWNING/RESERVED
        via the transition map). Call confirm_terminated after cleanup.
        """
        launch = self._registry.get_by_launch_id(launch_id)
        if launch is None:
            return False
        if not launch.can_transition_to(LaunchStatus.TERMINATING):
            return False
        return self._registry.cas_update_status(
            launch_id,
            launch.status,
            LaunchStatus.TERMINATING,
        )

    def confirm_terminated(self, launch_id: str) -> bool:
        """Transition from TERMINATING to TERMINATED after cleanup verification."""
        result = self._registry.cas_update_status(
            launch_id,
            LaunchStatus.TERMINATING,
            LaunchStatus.TERMINATED,
        )
        if result:
            logger.info(
                "LAUNCH_DECISION decision=terminated launch_id=%s",
                launch_id,
            )
        return result

    def quarantine(self, launch_id: str, reason: str) -> bool:
        """Quarantine a launch — blocks relaunch until manual recovery."""
        launch = self._registry.get_by_launch_id(launch_id)
        if launch is None or launch.is_terminal:
            return False
        if not launch.can_transition_to(LaunchStatus.QUARANTINED):
            return False
        return self._registry.cas_update_status(
            launch_id,
            launch.status,
            LaunchStatus.QUARANTINED,
            quarantine_reason=reason,
        )

    def get_launch(self, launch_id: str) -> AgentLaunch | None:
        """Retrieve a launch record by ID."""
        return self._registry.get_by_launch_id(launch_id)

    def get_active_launch(self, canonical_key: str) -> AgentLaunch | None:
        """Check if a canonical key has an active launch."""
        return self._registry.find_active_by_canonical_key(canonical_key)

    def reconcile_expired_leases(self) -> list[AgentLaunch]:
        """Find and quarantine all launches with expired leases.

        This should be called periodically (e.g., by a background task or
        during polling cycles) to prevent stale RESERVED/SPAWNING records
        from blocking legitimate launches forever.
        """
        now_ms = int(time.time() * 1000)
        expired = self._registry.list_expired_leases(now_ms)
        quarantined: list[AgentLaunch] = []
        for launch in expired:
            ok = self.quarantine(
                launch.launch_id,
                reason=f"Lease expired at {launch.lease_expires_at}",
            )
            if ok:
                quarantined.append(launch)
                logger.warning(
                    "Quarantined expired launch %s for canonical_key=%s",
                    launch.launch_id,
                    launch.canonical_key,
                )
            else:
                logger.warning(
                    "CAS failed quarantining expired launch %s for canonical_key=%s — race with another reconciler?",
                    launch.launch_id,
                    launch.canonical_key,
                )
        return quarantined

    def get_status_summary(self) -> dict[str, int]:
        """Return counts by status for operator visibility."""
        return self._registry.count_by_status()

    def list_active_launches(self) -> list[AgentLaunch]:
        """List all launches in blocking (active/in-flight) states."""
        result: list[AgentLaunch] = []
        for status in (
            LaunchStatus.RESERVED,
            LaunchStatus.SPAWNING,
            LaunchStatus.ACTIVE,
            LaunchStatus.TERMINATING,
        ):
            result.extend(self._registry.list_by_status(status))
        return sorted(result, key=lambda launch: launch.created_at or 0, reverse=True)

    def list_quarantined_launches(self) -> list[AgentLaunch]:
        """List all quarantined launches for operator triage."""
        return self._registry.list_by_status(LaunchStatus.QUARANTINED)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _quarantine_expired(self, launch: AgentLaunch) -> bool:
        """Move an expired-lease launch to QUARANTINED."""
        ok = self.quarantine(
            launch.launch_id,
            reason=f"Lease expired at {launch.lease_expires_at}",
        )
        if not ok:
            logger.warning(
                "CAS failed quarantining expired launch %s — already transitioned by another path?",
                launch.launch_id,
            )
        return ok
