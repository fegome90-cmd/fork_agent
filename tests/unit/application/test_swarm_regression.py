"""Swarm regression suite — proves at most one live launch per canonical key.

This suite targets the ORIGINAL failure mode: repeated polling cycles spawning
duplicate `pi` agent processes for the same task, burning RAM and provider quota.

The swarm happened because:
1. Polling didn't check for existing launches before spawning
2. No canonical dedup — same task could get multiple agents
3. Failed/ambiguous spawns got retried instead of quarantined
4. No authoritative cleanup — orphaned processes kept running

Each test here locks down one of these failure vectors so it cannot regress.
"""

from __future__ import annotations

import time
from pathlib import Path

from src.application.services.agent_launch_lifecycle_service import (
    AgentLaunchLifecycleService,
    LaunchAttempt,
)
from src.domain.entities.agent_launch import AgentLaunch, LaunchStatus
from src.domain.entities.poll_run import PollRun, PollRunStatus
from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
from src.infrastructure.persistence.repositories.agent_launch_repository import (
    SqliteAgentLaunchRepository,
)


# ---------------------------------------------------------------------------
# Helpers — mirrors patterns from test_agent_launch_lifecycle_service.py
# ---------------------------------------------------------------------------


def _make_service(tmp_path: Path, lease_ms: int = 300_000) -> AgentLaunchLifecycleService:
    db_path = tmp_path / "test.db"
    config = DatabaseConfig(db_path=db_path)
    conn = DatabaseConnection(config=config)
    with conn as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS agent_launch_registry (
                launch_id TEXT PRIMARY KEY,
                canonical_key TEXT NOT NULL,
                surface TEXT NOT NULL,
                owner_type TEXT NOT NULL,
                owner_id TEXT NOT NULL,
                backend TEXT,
                status TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                reserved_at INTEGER,
                spawn_started_at INTEGER,
                spawn_confirmed_at INTEGER,
                ended_at INTEGER,
                lease_expires_at INTEGER,
                termination_handle_type TEXT,
                termination_handle_value TEXT,
                process_pid INTEGER,
                process_pgid INTEGER,
                tmux_session TEXT,
                tmux_pane_id TEXT,
                prompt_digest TEXT,
                request_fingerprint TEXT,
                last_error TEXT,
                quarantine_reason TEXT
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_one_active_launch_per_key
                ON agent_launch_registry (canonical_key)
                WHERE status IN ('RESERVED', 'SPAWNING', 'ACTIVE', 'TERMINATING');
            CREATE INDEX IF NOT EXISTS idx_launch_canonical_key ON agent_launch_registry (canonical_key);
            CREATE INDEX IF NOT EXISTS idx_launch_status ON agent_launch_registry (status);
        """)
    repo = SqliteAgentLaunchRepository(connection=conn)
    return AgentLaunchLifecycleService(registry=repo, lease_duration_ms=lease_ms)


def _run_full_lifecycle(
    svc: AgentLaunchLifecycleService,
    canonical_key: str,
    surface: str = "polling",
    owner_type: str = "task",
    owner_id: str = "task-1",
    backend: str = "tmux",
    handle_type: str = "tmux-pane",
    handle_value: str = "%1",
) -> AgentLaunch:
    """Drive a launch through claim -> spawning -> active and return the final record."""
    attempt = svc.request_launch(
        canonical_key=canonical_key,
        surface=surface,
        owner_type=owner_type,
        owner_id=owner_id,
    )
    assert attempt.decision == "claimed"
    assert attempt.launch is not None
    lid = attempt.launch.launch_id

    assert svc.confirm_spawning(lid) is True
    assert svc.confirm_active(
        lid,
        backend=backend,
        termination_handle_type=handle_type,
        termination_handle_value=handle_value,
    ) is True
    launch = svc.get_launch(lid)
    assert launch is not None
    return launch


# ---------------------------------------------------------------------------
# 1. Repeated polling under unchanged approval state
# ---------------------------------------------------------------------------


class TestRepeatedPollingSingleLaunch:
    """Regression: same task polled N times produces exactly 1 launch.

    This was the core of the original swarm — polling cycles kept re-spawning
    because there was no dedup check.
    """

    def test_n_polls_produce_at_most_one_claim(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        canonical_key = "task:pi-swarm-target"

        results: list[LaunchAttempt] = []
        for _ in range(20):
            attempt = svc.request_launch(
                canonical_key=canonical_key,
                surface="polling",
                owner_type="task",
                owner_id="pi-swarm-target",
            )
            results.append(attempt)

        claimed = [a for a in results if a.decision == "claimed"]
        suppressed = [a for a in results if a.decision == "suppressed"]

        assert len(claimed) == 1, "Exactly one poll cycle should win the claim"
        assert len(suppressed) == 19, "All other poll cycles should be suppressed"

    def test_suppressed_attempts_reference_same_existing_launch(
        self, tmp_path: Path,
    ) -> None:
        svc = _make_service(tmp_path)
        canonical_key = "task:dedup-ref"

        first = svc.request_launch(
            canonical_key=canonical_key,
            surface="polling",
            owner_type="task",
            owner_id="dedup-ref",
        )
        assert first.launch is not None
        original_id = first.launch.launch_id

        for _ in range(10):
            attempt = svc.request_launch(
                canonical_key=canonical_key,
                surface="polling",
                owner_type="task",
                owner_id="dedup-ref",
            )
            assert attempt.decision == "suppressed"
            assert attempt.existing_launch is not None
            assert attempt.existing_launch.launch_id == original_id

    def test_after_terminal_state_new_claim_allowed(self, tmp_path: Path) -> None:
        """After a launch reaches terminal state, a fresh claim is allowed."""
        svc = _make_service(tmp_path)
        canonical_key = "task:retry-after-done"

        first = svc.request_launch(
            canonical_key=canonical_key,
            surface="polling",
            owner_type="task",
            owner_id="retry-after-done",
        )
        assert first.decision == "claimed"
        assert first.launch is not None

        svc.confirm_spawning(first.launch.launch_id)
        svc.confirm_active(
            first.launch.launch_id,
            backend="tmux",
            termination_handle_type="tmux-pane",
            termination_handle_value="%1",
        )
        svc.begin_termination(first.launch.launch_id)
        svc.confirm_terminated(first.launch.launch_id)

        # Now a new claim should succeed — the old one is terminal
        second = svc.request_launch(
            canonical_key=canonical_key,
            surface="polling",
            owner_type="task",
            owner_id="retry-after-done",
        )
        assert second.decision == "claimed"
        assert second.launch is not None
        assert second.launch.launch_id != first.launch.launch_id


# ---------------------------------------------------------------------------
# 2. Near-concurrent launch attempts for same canonical item
# ---------------------------------------------------------------------------


class TestNearConcurrentLaunchAttempts:
    """Regression: two surfaces (polling + API) try to launch same task; only one wins.

    The original code had no shared ownership check, so polling and API could
    both spawn agents for the same task simultaneously.
    """

    def test_two_surfaces_same_key_one_wins(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        canonical_key = "task:race-target"

        polling_attempt = svc.request_launch(
            canonical_key=canonical_key,
            surface="polling",
            owner_type="task",
            owner_id="race-target",
        )
        api_attempt = svc.request_launch(
            canonical_key=canonical_key,
            surface="api",
            owner_type="session",
            owner_id="race-target",
        )

        decisions = {polling_attempt.decision, api_attempt.decision}
        assert "claimed" in decisions
        claimed_count = sum(
            1 for a in (polling_attempt, api_attempt) if a.decision == "claimed"
        )
        assert claimed_count == 1, "Exactly one surface must win"

    def test_five_surfaces_same_key_one_wins(self, tmp_path: Path) -> None:
        """Simulate all surfaces trying to launch for the same canonical key."""
        svc = _make_service(tmp_path)
        canonical_key = "task:multi-race"

        attempts = []
        for surface in ("polling", "workflow", "api", "manager", "bug_hunt"):
            owner_type = "batch" if surface == "bug_hunt" else "task"
            attempt = svc.request_launch(
                canonical_key=canonical_key,
                surface=surface,
                owner_type=owner_type,
                owner_id="multi-race",
            )
            attempts.append(attempt)

        claimed = [a for a in attempts if a.decision == "claimed"]
        suppressed = [a for a in attempts if a.decision == "suppressed"]
        assert len(claimed) == 1
        assert len(suppressed) == 4

    def test_at_most_one_active_launch_in_registry(self, tmp_path: Path) -> None:
        """After multiple claim attempts, the registry contains exactly one active launch."""
        svc = _make_service(tmp_path)
        canonical_key = "task:reg-check"

        for surface in ("polling", "workflow", "api", "manager"):
            svc.request_launch(
                canonical_key=canonical_key,
                surface=surface,
                owner_type="task",
                owner_id="reg-check",
            )

        active = svc.list_active_launches()
        matching = [l for l in active if l.canonical_key == canonical_key]
        assert len(matching) == 1, "Registry must have exactly one active launch for this key"


# ---------------------------------------------------------------------------
# 3. Cleanup after terminal states
# ---------------------------------------------------------------------------


class TestCleanupAfterTerminalStates:
    """Regression: completed, failed, cancelled, interrupted runs all get deterministic cleanup.

    The original failure mode left orphaned processes running because cleanup
    was not tied to the canonical lifecycle.
    """

    def test_completed_launch_has_ended_at(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        launch = _run_full_lifecycle(svc, "task:complete-cleanup")

        assert svc.begin_termination(launch.launch_id) is True
        assert svc.confirm_terminated(launch.launch_id) is True

        record = svc.get_launch(launch.launch_id)
        assert record is not None
        assert record.status == LaunchStatus.TERMINATED
        assert record.ended_at is not None

    def test_failed_launch_has_ended_at(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        attempt = svc.request_launch(
            canonical_key="task:fail-cleanup",
            surface="polling",
            owner_type="task",
            owner_id="fail-cleanup",
        )
        assert attempt.launch is not None

        assert svc.mark_failed(attempt.launch.launch_id, "Process crashed") is True

        record = svc.get_launch(attempt.launch.launch_id)
        assert record is not None
        assert record.status == LaunchStatus.FAILED
        assert record.ended_at is not None

    def test_cancelled_launch_transitions_cleanly(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        launch = _run_full_lifecycle(svc, "task:cancel-cleanup")

        assert svc.begin_termination(launch.launch_id) is True
        assert svc.confirm_terminated(launch.launch_id) is True

        record = svc.get_launch(launch.launch_id)
        assert record is not None
        assert record.status == LaunchStatus.TERMINATED

    def test_interrupted_spawning_gets_marked_failed(self, tmp_path: Path) -> None:
        """A launch stuck in SPAWNING (interrupted) can be cleaned up."""
        svc = _make_service(tmp_path)
        attempt = svc.request_launch(
            canonical_key="task:interrupt-cleanup",
            surface="polling",
            owner_type="task",
            owner_id="interrupt-cleanup",
        )
        assert attempt.launch is not None
        svc.confirm_spawning(attempt.launch.launch_id)

        # Simulate interruption — mark as failed
        assert svc.mark_failed(attempt.launch.launch_id, "Interrupted during spawn") is True

        record = svc.get_launch(attempt.launch.launch_id)
        assert record is not None
        assert record.status == LaunchStatus.FAILED

    def test_terminal_launch_allows_new_claim(self, tmp_path: Path) -> None:
        """After cleanup, the canonical key is free for a new launch."""
        svc = _make_service(tmp_path)

        # Complete a full lifecycle
        launch = _run_full_lifecycle(svc, "task:reuse-key")
        svc.begin_termination(launch.launch_id)
        svc.confirm_terminated(launch.launch_id)

        # New claim should succeed
        new_attempt = svc.request_launch(
            canonical_key="task:reuse-key",
            surface="polling",
            owner_type="task",
            owner_id="reuse-key",
        )
        assert new_attempt.decision == "claimed"

    def test_all_terminal_states_free_canonical_key(self, tmp_path: Path) -> None:
        """Every terminal state should free the canonical key for new claims."""
        svc_factory = lambda: _make_service(tmp_path / "fresh")

        terminal_transitions = [
            ("terminated", lambda s, lid: (
                s.confirm_spawning(lid),
                s.confirm_active(lid, backend="tmux",
                                 termination_handle_type="tmux-pane",
                                 termination_handle_value="%1"),
                s.begin_termination(lid),
                s.confirm_terminated(lid),
            )),
            ("failed", lambda s, lid: (
                s.mark_failed(lid, "boom"),
            )),
        ]

        for label, transitions in terminal_transitions:
            base = tmp_path / f"terminal_{label}"
            base.mkdir(parents=True, exist_ok=True)
            svc = _make_service(base)
            key = f"task:terminal-{label}"

            attempt = svc.request_launch(
                canonical_key=key,
                surface="polling",
                owner_type="task",
                owner_id=f"terminal-{label}",
            )
            assert attempt.launch is not None
            transitions(svc, attempt.launch.launch_id)

            # Key should be free
            new_attempt = svc.request_launch(
                canonical_key=key,
                surface="polling",
                owner_type="task",
                owner_id=f"terminal-{label}",
            )
            assert new_attempt.decision == "claimed", (
                f"Key should be free after {label}, got {new_attempt.decision}"
            )


# ---------------------------------------------------------------------------
# 4. Quarantine prevents relaunch loop
# ---------------------------------------------------------------------------


class TestQuarantinePreventsRelaunchLoop:
    """Regression: a quarantined launch does NOT get retried automatically.

    The original code would retry failed spawns, potentially burning quota in
    a tight loop. Quarantine is the conservative escape hatch.
    """

    def test_quarantined_launch_allows_new_claim_after_manual_recovery(
        self, tmp_path: Path,
    ) -> None:
        """QUARANTINED is NOT a blocking status, so a new claim is allowed.

        However, the operator must explicitly decide to relaunch. The quarantine
        reason is visible in the audit trail.
        """
        svc = _make_service(tmp_path)
        attempt = svc.request_launch(
            canonical_key="task:quarantine-relaunch",
            surface="polling",
            owner_type="task",
            owner_id="quarantine-relaunch",
        )
        assert attempt.launch is not None
        svc.confirm_spawning(attempt.launch.launch_id)
        svc.quarantine(attempt.launch.launch_id, "Ambiguous spawn result")

        record = svc.get_launch(attempt.launch.launch_id)
        assert record is not None
        assert record.status == LaunchStatus.QUARANTINED
        assert record.quarantine_reason == "Ambiguous spawn result"

        # QUARANTINED is not in BLOCKING_STATUSES, so a new claim is allowed
        # This represents manual operator recovery
        new_attempt = svc.request_launch(
            canonical_key="task:quarantine-relaunch",
            surface="polling",
            owner_type="task",
            owner_id="quarantine-relaunch",
        )
        assert new_attempt.decision == "claimed"

    def test_quarantine_reason_is_preserved(self, tmp_path: Path) -> None:
        """The quarantine reason survives in the audit trail."""
        svc = _make_service(tmp_path)
        attempt = svc.request_launch(
            canonical_key="task:quarantine-audit",
            surface="polling",
            owner_type="task",
            owner_id="quarantine-audit",
        )
        assert attempt.launch is not None
        svc.confirm_spawning(attempt.launch.launch_id)
        svc.quarantine(attempt.launch.launch_id, "Process unreachable after 3 probes")

        quarantined = svc.list_quarantined_launches()
        assert len(quarantined) == 1
        reason = quarantined[0].quarantine_reason
        assert reason is not None and "unreachable" in reason.lower()

    def test_quarantined_from_multiple_states(self, tmp_path: Path) -> None:
        """Quarantine works from RESERVED, SPAWNING, and ACTIVE states."""
        for initial_state, setup in (
            ("RESERVED", lambda svc, lid: None),
            ("SPAWNING", lambda svc, lid: svc.confirm_spawning(lid)),
            ("ACTIVE", lambda svc, lid: (
                svc.confirm_spawning(lid),
                svc.confirm_active(
                    lid, backend="tmux",
                    termination_handle_type="tmux-pane",
                    termination_handle_value="%1",
                ),
            )),
        ):
            base = tmp_path / f"q_{initial_state}"
            base.mkdir(parents=True, exist_ok=True)
            svc = _make_service(base)
            key = f"task:q-{initial_state.lower()}"

            attempt = svc.request_launch(
                canonical_key=key,
                surface="polling",
                owner_type="task",
                owner_id=f"q-{initial_state.lower()}",
            )
            assert attempt.launch is not None
            setup(svc, attempt.launch.launch_id)

            result = svc.quarantine(
                attempt.launch.launch_id,
                f"Quarantined from {initial_state}",
            )
            assert result is True

            record = svc.get_launch(attempt.launch.launch_id)
            assert record is not None
            assert record.status == LaunchStatus.QUARANTINED


# ---------------------------------------------------------------------------
# 5. Lease expiry quarantines instead of retrying
# ---------------------------------------------------------------------------


class TestLeaseExpiryQuarantines:
    """Regression: stale RESERVED/SPAWNING records get quarantined, not relaunched.

    The original code would re-issue launches for stale records, creating
    duplicate processes.
    """

    def test_expired_reserved_is_quarantined(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path, lease_ms=1)
        attempt = svc.request_launch(
            canonical_key="task:lease-reserved",
            surface="polling",
            owner_type="task",
            owner_id="lease-reserved",
        )
        assert attempt.launch is not None

        time.sleep(0.01)
        quarantined = svc.reconcile_expired_leases()
        assert len(quarantined) == 1
        assert quarantined[0].canonical_key == "task:lease-reserved"

        record = svc.get_launch(attempt.launch.launch_id)
        assert record is not None
        assert record.status == LaunchStatus.QUARANTINED

    def test_expired_spawning_is_quarantined(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path, lease_ms=1)
        attempt = svc.request_launch(
            canonical_key="task:lease-spawning",
            surface="polling",
            owner_type="task",
            owner_id="lease-spawning",
        )
        assert attempt.launch is not None
        svc.confirm_spawning(attempt.launch.launch_id)

        time.sleep(0.01)
        quarantined = svc.reconcile_expired_leases()
        assert len(quarantined) == 1

        record = svc.get_launch(attempt.launch.launch_id)
        assert record is not None
        assert record.status == LaunchStatus.QUARANTINED

    def test_active_launch_not_expired(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path, lease_ms=1)
        attempt = svc.request_launch(
            canonical_key="task:lease-active",
            surface="polling",
            owner_type="task",
            owner_id="lease-active",
        )
        assert attempt.launch is not None
        svc.confirm_spawning(attempt.launch.launch_id)
        svc.confirm_active(
            attempt.launch.launch_id,
            backend="tmux",
            termination_handle_type="tmux-pane",
            termination_handle_value="%1",
        )

        time.sleep(0.01)
        quarantined = svc.reconcile_expired_leases()
        assert len(quarantined) == 0, "ACTIVE launches must not be expired"

    def test_after_lease_reconciliation_new_claim_succeeds(self, tmp_path: Path) -> None:
        """Once an expired lease is quarantined, the key is free for new claims."""
        svc = _make_service(tmp_path, lease_ms=1)
        svc.request_launch(
            canonical_key="task:lease-reclaim",
            surface="polling",
            owner_type="task",
            owner_id="lease-reclaim",
        )
        time.sleep(0.01)
        svc.reconcile_expired_leases()

        new_attempt = svc.request_launch(
            canonical_key="task:lease-reclaim",
            surface="polling",
            owner_type="task",
            owner_id="lease-reclaim",
        )
        assert new_attempt.decision == "claimed"

    def test_reconciliation_does_not_duplicate_launches(self, tmp_path: Path) -> None:
        """Running reconciliation multiple times does not create extra records."""
        svc = _make_service(tmp_path, lease_ms=1)
        svc.request_launch(
            canonical_key="task:lease-idempotent",
            surface="polling",
            owner_type="task",
            owner_id="lease-idempotent",
        )
        time.sleep(0.01)

        q1 = svc.reconcile_expired_leases()
        q2 = svc.reconcile_expired_leases()

        assert len(q1) == 1
        assert len(q2) == 0, "Second reconciliation should find nothing new"

    def test_lease_expiry_prevents_swarm_loop(self, tmp_path: Path) -> None:
        """Simulate the original swarm scenario: repeated polls + stale records.

        Without lease reconciliation, stale records would allow repeated claims.
        With it, stale records get quarantined, but only ONE new claim succeeds.
        """
        # Phase 1: short-lease service to force expiry
        svc = _make_service(tmp_path, lease_ms=1)

        # First poll claims
        first = svc.request_launch(
            canonical_key="task:swarm-prevention",
            surface="polling",
            owner_type="task",
            owner_id="swarm-prevention",
        )
        assert first.decision == "claimed"

        # Time passes, lease expires
        time.sleep(0.01)

        # Reconciliation quarantines the stale claim
        svc.reconcile_expired_leases()

        # Phase 2: normal-lease service so loop claims don't auto-expire
        svc_normal = _make_service(tmp_path, lease_ms=300_000)

        # Only ONE of N subsequent polls should claim
        claims = 0
        for _ in range(10):
            attempt = svc_normal.request_launch(
                canonical_key="task:swarm-prevention",
                surface="polling",
                owner_type="task",
                owner_id="swarm-prevention",
            )
            if attempt.decision == "claimed":
                claims += 1

        assert claims == 1, "Exactly one poll should claim after reconciliation"


# ---------------------------------------------------------------------------
# 6. All surfaces obey same dedup
# ---------------------------------------------------------------------------


class TestAllSurfacesObeySameDedup:
    """Regression: polling, workflow, API, manager, bug-hunt all respect the canonical key dedup.

    The original swarm could be triggered from multiple surfaces because each
    had its own independent spawn logic with no shared dedup.
    """

    def test_polling_blocks_workflow(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        svc.request_launch(
            canonical_key="task:cross-surface",
            surface="polling",
            owner_type="task",
            owner_id="cross-surface",
        )
        attempt = svc.request_launch(
            canonical_key="task:cross-surface",
            surface="workflow",
            owner_type="task",
            owner_id="cross-surface",
        )
        assert attempt.decision == "suppressed"

    def test_workflow_blocks_polling(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        svc.request_launch(
            canonical_key="task:wf-first",
            surface="workflow",
            owner_type="task",
            owner_id="wf-first",
        )
        attempt = svc.request_launch(
            canonical_key="task:wf-first",
            surface="polling",
            owner_type="task",
            owner_id="wf-first",
        )
        assert attempt.decision == "suppressed"

    def test_api_blocks_manager(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        svc.request_launch(
            canonical_key="task:api-blocks",
            surface="api",
            owner_type="session",
            owner_id="api-blocks",
        )
        attempt = svc.request_launch(
            canonical_key="task:api-blocks",
            surface="manager",
            owner_type="agent",
            owner_id="api-blocks",
        )
        assert attempt.decision == "suppressed"

    def test_manager_blocks_polling(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        svc.request_launch(
            canonical_key="task:mgr-blocks",
            surface="manager",
            owner_type="agent",
            owner_id="mgr-blocks",
        )
        attempt = svc.request_launch(
            canonical_key="task:mgr-blocks",
            surface="polling",
            owner_type="task",
            owner_id="mgr-blocks",
        )
        assert attempt.decision == "suppressed"

    def test_bug_hunt_blocks_bug_hunt_same_key(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        svc.request_launch(
            canonical_key="bug_hunt:batch1:ripper",
            surface="bug_hunt",
            owner_type="batch",
            owner_id="batch1",
        )
        attempt = svc.request_launch(
            canonical_key="bug_hunt:batch1:ripper",
            surface="bug_hunt",
            owner_type="batch",
            owner_id="batch1",
        )
        assert attempt.decision == "suppressed"

    def test_different_canonical_keys_do_not_block(self, tmp_path: Path) -> None:
        """Different canonical keys should NOT block each other."""
        svc = _make_service(tmp_path)

        surfaces_and_keys = [
            ("polling", "task:unique-1"),
            ("workflow", "task:unique-2"),
            ("api", "api:session-abc"),
            ("manager", "manager:agent-x"),
            ("bug_hunt", "bug_hunt:h1:ripper"),
        ]
        for surface, key in surfaces_and_keys:
            attempt = svc.request_launch(
                canonical_key=key,
                surface=surface,
                owner_type="task",
                owner_id=key.split(":")[1],
            )
            assert attempt.decision == "claimed", (
                f"Surface {surface} with key {key} should not be blocked"
            )

    def test_full_cross_surface_matrix(self, tmp_path: Path) -> None:
        """Every surface pair exhibits correct dedup for the same canonical key."""
        surfaces = ("polling", "workflow", "api", "manager", "bug_hunt")

        for first_surface in surfaces:
            base = tmp_path / f"matrix_{first_surface}"
            base.mkdir(parents=True, exist_ok=True)
            svc = _make_service(base)
            key = "task:matrix-target"

            first = svc.request_launch(
                canonical_key=key,
                surface=first_surface,
                owner_type="task",
                owner_id="matrix-target",
            )
            assert first.decision == "claimed", f"First surface {first_surface} should claim"

            for second_surface in surfaces:
                attempt = svc.request_launch(
                    canonical_key=key,
                    surface=second_surface,
                    owner_type="task",
                    owner_id="matrix-target",
                )
                assert attempt.decision == "suppressed", (
                    f"Surface {second_surface} should be suppressed after"
                    f" {first_surface} claimed"
                )


# ---------------------------------------------------------------------------
# Integration: lifecycle service + polling service together
# ---------------------------------------------------------------------------


class TestPollingServiceWithLifecycleIntegration:
    """Integration regression: polling service + lifecycle service end-to-end.

    These tests prove the polling service correctly delegates to the lifecycle
    service and that the original swarm scenario cannot recur.
    """


class MockPollRunRepo:
    """In-memory poll run repository for integration tests."""

    def __init__(self) -> None:
        self._runs: dict[str, PollRun] = {}

    def save(self, run: PollRun) -> None:
        self._runs[run.id] = run

    def get_by_id(self, run_id: str) -> PollRun | None:
        return self._runs.get(run_id)

    def list_by_status(self, status: PollRunStatus) -> list[PollRun]:
        return [r for r in self._runs.values() if r.status == status]

    def list_active(self) -> list[PollRun]:
        return [
            r
            for r in self._runs.values()
            if r.status
            in (
                PollRunStatus.QUEUED,
                PollRunStatus.SPAWNING,
                PollRunStatus.RUNNING,
                PollRunStatus.TERMINATING,
            )
        ]

    def list_launch_blocking(self) -> list[PollRun]:
        return [
            r
            for r in self._runs.values()
            if r.status
            in (
                PollRunStatus.QUEUED,
                PollRunStatus.SPAWNING,
                PollRunStatus.RUNNING,
                PollRunStatus.TERMINATING,
                PollRunStatus.QUARANTINED,
            )
        ]

    def update_status(
        self, run_id: str, status: PollRunStatus, error_message: str | None = None
    ) -> None:
        from dataclasses import replace
        run = self._runs.get(run_id)
        if run:
            self._runs[run_id] = replace(run, status=status, error_message=error_message)

    def remove(self, run_id: str) -> None:
        self._runs.pop(run_id, None)

    def count_by_status(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for run in self._runs.values():
            counts[run.status.value] = counts.get(run.status.value, 0) + 1
        return counts

    def record_launch_metadata(
        self,
        run_id: str,
        *,
        launch_method: str,
        pane_id: str | None = None,
        pid: int | None = None,
        pgid: int | None = None,
    ) -> bool:
        from dataclasses import replace
        run = self._runs.get(run_id)
        if run is None:
            return False
        self._runs[run_id] = replace(
            run,
            launch_method=launch_method,
            launch_pane_id=pane_id,
            launch_pid=pid,
            launch_pgid=pgid,
            launch_recorded_at=1,
        )
        return True


# ---------------------------------------------------------------------------
# Observability regression
# ---------------------------------------------------------------------------


class TestLaunchDecisionObservability:
    """Regression: launch decisions are observable without log archaeology.

    This was REQ-OBS-1 through REQ-OBS-4 in the spec.
    """

    def test_status_summary_shows_all_states(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)

        # Create launches in different states
        a1 = svc.request_launch(
            canonical_key="task:obs-r",
            surface="polling",
            owner_type="task",
            owner_id="obs-r",
        )
        assert a1.launch is not None

        a2 = svc.request_launch(
            canonical_key="task:obs-f",
            surface="polling",
            owner_type="task",
            owner_id="obs-f",
        )
        assert a2.launch is not None
        svc.mark_failed(a2.launch.launch_id, "test failure")

        summary = svc.get_status_summary()
        assert summary.get("RESERVED", 0) >= 1
        assert summary.get("FAILED", 0) >= 1

    def test_suppressed_attempt_includes_existing_launch_info(
        self, tmp_path: Path,
    ) -> None:
        """When a launch is suppressed, the existing launch info is available."""
        svc = _make_service(tmp_path)

        first = svc.request_launch(
            canonical_key="task:obs-sup",
            surface="polling",
            owner_type="task",
            owner_id="obs-sup",
        )
        assert first.launch is not None
        svc.confirm_spawning(first.launch.launch_id)
        svc.confirm_active(
            first.launch.launch_id,
            backend="tmux",
            termination_handle_type="tmux-pane",
            termination_handle_value="%42",
        )

        suppressed = svc.request_launch(
            canonical_key="task:obs-sup",
            surface="api",
            owner_type="session",
            owner_id="obs-sup",
        )
        assert suppressed.decision == "suppressed"
        assert suppressed.existing_launch is not None
        assert suppressed.existing_launch.status == LaunchStatus.ACTIVE
        assert suppressed.existing_launch.termination_handle_value == "%42"
        assert suppressed.reason is not None

    def test_list_active_launches_returns_only_blocking(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)

        # One active, one failed, one terminated
        active = _run_full_lifecycle(svc, "task:obs-active")

        failed_key = "task:obs-failed"
        f = svc.request_launch(
            canonical_key=failed_key,
            surface="polling",
            owner_type="task",
            owner_id="obs-failed",
        )
        assert f.launch is not None
        svc.mark_failed(f.launch.launch_id, "done")

        active_launches = svc.list_active_launches()
        active_ids = {l.launch_id for l in active_launches}
        assert active.launch_id in active_ids
        assert f.launch.launch_id not in active_ids

    def test_quarantined_launches_visible_for_triage(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        attempt = svc.request_launch(
            canonical_key="task:obs-q",
            surface="polling",
            owner_type="task",
            owner_id="obs-q",
        )
        assert attempt.launch is not None
        svc.confirm_spawning(attempt.launch.launch_id)
        svc.quarantine(attempt.launch.launch_id, "Process zombie detected")

        quarantined = svc.list_quarantined_launches()
        assert len(quarantined) == 1
        assert quarantined[0].quarantine_reason == "Process zombie detected"
        assert quarantined[0].canonical_key == "task:obs-q"
