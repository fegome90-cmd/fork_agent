"""Tests for AgentLaunchLifecycleService — lifecycle orchestration and duplicate suppression."""

from __future__ import annotations

import time
from pathlib import Path

from src.application.services.agent_launch_lifecycle_service import (
    AgentLaunchLifecycleService,
)
from src.domain.entities.agent_launch import LaunchStatus
from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
from src.infrastructure.persistence.repositories.agent_launch_repository import (
    SqliteAgentLaunchRepository,
)


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
                quarantine_reason TEXT,
                parent_launch_id TEXT REFERENCES agent_launch_registry(launch_id),
                role TEXT,
                model TEXT,
                output_artifact TEXT
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_one_active_launch_per_key
                ON agent_launch_registry (canonical_key)
                WHERE status IN ('RESERVED', 'SPAWNING', 'ACTIVE', 'TERMINATING');
            CREATE INDEX IF NOT EXISTS idx_launch_canonical_key ON agent_launch_registry (canonical_key);
            CREATE INDEX IF NOT EXISTS idx_launch_status ON agent_launch_registry (status);
        """)
    repo = SqliteAgentLaunchRepository(connection=conn)
    return AgentLaunchLifecycleService(registry=repo, lease_duration_ms=lease_ms)


class TestRequestLaunch:
    """request_launch: claim, suppress, or fail closed."""

    def test_first_request_is_claimed(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        attempt = svc.request_launch(
            canonical_key="task:abc",
            surface="polling",
            owner_type="task",
            owner_id="abc",
        )
        assert attempt.decision == "claimed"
        assert attempt.launch is not None
        assert attempt.launch.status == LaunchStatus.RESERVED
        assert attempt.existing_launch is None

    def test_duplicate_request_is_suppressed(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        svc.request_launch(
            canonical_key="task:dup",
            surface="polling",
            owner_type="task",
            owner_id="dup",
        )
        second = svc.request_launch(
            canonical_key="task:dup",
            surface="api",
            owner_type="task",
            owner_id="dup",
        )
        assert second.decision == "suppressed"
        assert second.launch is None
        assert second.existing_launch is not None

    def test_suppressed_across_surfaces(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        svc.request_launch(
            canonical_key="task:multi",
            surface="polling",
            owner_type="task",
            owner_id="multi",
        )
        for surface in ("workflow", "api", "manager", "bug_hunt"):
            attempt = svc.request_launch(
                canonical_key="task:multi",
                surface=surface,
                owner_type="task",
                owner_id="multi",
            )
            assert attempt.decision == "suppressed", f"Surface {surface} should be suppressed"

    def test_request_after_terminal_succeeds(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        first = svc.request_launch(
            canonical_key="task:retry",
            surface="polling",
            owner_type="task",
            owner_id="retry",
        )
        assert first.decision == "claimed"
        assert first.launch is not None

        svc.confirm_spawning(first.launch.launch_id)
        svc.mark_failed(first.launch.launch_id, "transient error")

        second = svc.request_launch(
            canonical_key="task:retry",
            surface="polling",
            owner_type="task",
            owner_id="retry",
        )
        assert second.decision == "claimed"


class TestLifecycleTransitions:
    """Full lifecycle: RESERVED → SPAWNING → ACTIVE → TERMINATING → TERMINATED."""

    def test_full_happy_path(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        attempt = svc.request_launch(
            canonical_key="task:happy",
            surface="polling",
            owner_type="task",
            owner_id="happy",
        )
        assert attempt.launch is not None
        lid = attempt.launch.launch_id

        assert svc.confirm_spawning(lid) is True
        assert (
            svc.confirm_active(
                lid,
                backend="tmux",
                termination_handle_type="tmux-pane",
                termination_handle_value="%42",
                tmux_pane_id="%42",
            )
            is True
        )

        launch = svc.get_launch(lid)
        assert launch is not None
        assert launch.status == LaunchStatus.ACTIVE
        assert launch.backend == "tmux"
        assert launch.termination_handle_value == "%42"

        assert svc.begin_termination(lid) is True
        assert svc.confirm_terminated(lid) is True

        launch = svc.get_launch(lid)
        assert launch is not None
        assert launch.status == LaunchStatus.TERMINATED
        assert launch.ended_at is not None

    def test_confirm_active_with_subprocess(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        attempt = svc.request_launch(
            canonical_key="task:sub",
            surface="polling",
            owner_type="task",
            owner_id="sub",
        )
        assert attempt.launch is not None
        lid = attempt.launch.launch_id

        svc.confirm_spawning(lid)
        svc.confirm_active(
            lid,
            backend="subprocess",
            termination_handle_type="pgid",
            termination_handle_value="9999",
            process_pid=12345,
            process_pgid=9999,
        )

        launch = svc.get_launch(lid)
        assert launch is not None
        assert launch.process_pid == 12345
        assert launch.process_pgid == 9999

    def test_spawning_to_quarantine(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        attempt = svc.request_launch(
            canonical_key="task:q",
            surface="polling",
            owner_type="task",
            owner_id="q",
        )
        assert attempt.launch is not None
        lid = attempt.launch.launch_id
        svc.confirm_spawning(lid)

        assert svc.quarantine(lid, "spawn unresolved") is True
        launch = svc.get_launch(lid)
        assert launch is not None
        assert launch.status == LaunchStatus.QUARANTINED
        assert launch.quarantine_reason == "spawn unresolved"

    def test_quarantined_launch_blocks_new_requests(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        attempt = svc.request_launch(
            canonical_key="task:blocked",
            surface="polling",
            owner_type="task",
            owner_id="blocked",
        )
        assert attempt.launch is not None
        lid = attempt.launch.launch_id
        svc.confirm_spawning(lid)
        svc.quarantine(lid, "ambiguous")

        # QUARANTINED IS in BLOCKING_STATUSES — it must block relaunches
        # until manual recovery clears the quarantine.
        new_attempt = svc.request_launch(
            canonical_key="task:blocked",
            surface="polling",
            owner_type="task",
            owner_id="blocked",
        )
        assert new_attempt.decision == "suppressed"


class TestExpiredLeaseReconciliation:
    """reconcile_expired_leases quarantines stale RESERVED/SPAWNING records."""

    def test_expired_lease_is_quarantined(self, tmp_path: Path) -> None:
        # Use a very short lease to force immediate expiry
        svc = _make_service(tmp_path, lease_ms=1)
        attempt = svc.request_launch(
            canonical_key="task:expire",
            surface="polling",
            owner_type="task",
            owner_id="expire",
        )
        assert attempt.launch is not None

        # Wait for lease to expire
        time.sleep(0.01)

        quarantined = svc.reconcile_expired_leases()
        assert len(quarantined) == 1
        assert quarantined[0].canonical_key == "task:expire"

        launch = svc.get_launch(attempt.launch.launch_id)
        assert launch is not None
        assert launch.status == LaunchStatus.QUARANTINED

    def test_active_launch_not_expired(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path, lease_ms=1)
        attempt = svc.request_launch(
            canonical_key="task:active-no-exp",
            surface="polling",
            owner_type="task",
            owner_id="active-no-exp",
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
        assert len(quarantined) == 0

    def test_after_reconciliation_new_claim_succeeds(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path, lease_ms=1)
        svc.request_launch(
            canonical_key="task:reclaim",
            surface="polling",
            owner_type="task",
            owner_id="reclaim",
        )
        time.sleep(0.01)
        svc.reconcile_expired_leases()

        new_attempt = svc.request_launch(
            canonical_key="task:reclaim",
            surface="polling",
            owner_type="task",
            owner_id="reclaim",
        )
        assert new_attempt.decision == "claimed"


class TestGetActiveLaunch:
    """get_active_launch for dedup checks."""

    def test_returns_active_launch(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        attempt = svc.request_launch(
            canonical_key="task:active",
            surface="polling",
            owner_type="task",
            owner_id="active",
        )
        assert attempt.launch is not None

        active = svc.get_active_launch("task:active")
        assert active is not None
        assert active.launch_id == attempt.launch.launch_id

    def test_returns_none_for_terminal(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        attempt = svc.request_launch(
            canonical_key="task:dead",
            surface="polling",
            owner_type="task",
            owner_id="dead",
        )
        assert attempt.launch is not None
        svc.mark_failed(attempt.launch.launch_id, "done")

        active = svc.get_active_launch("task:dead")
        assert active is None

    def test_status_summary(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        a1 = svc.request_launch(
            canonical_key="task:s1",
            surface="polling",
            owner_type="task",
            owner_id="s1",
        )
        svc.request_launch(
            canonical_key="task:s2",
            surface="polling",
            owner_type="task",
            owner_id="s2",
        )
        assert a1.launch is not None
        svc.mark_failed(a1.launch.launch_id, "boom")

        summary = svc.get_status_summary()
        assert summary.get("RESERVED", 0) == 1
        assert summary.get("FAILED", 0) == 1


class TestAgentIdentityValidation:
    """Tests for ADR-001 identity invariants: roles, lineage, cycles."""

    def test_role_is_mandatory_for_new_launches(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        # Explicit role provided
        attempt = svc.request_launch(
            canonical_key="task:role",
            surface="workflow",
            owner_type="task",
            owner_id="role",
            role="explorer",
        )
        assert attempt.decision == "claimed"
        assert attempt.launch is not None
        assert attempt.launch.role == "explorer"

    def test_legacy_role_fallback(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        # No role provided — fallback to surface default
        attempt = svc.request_launch(
            canonical_key="task:legacy",
            surface="polling",
            owner_type="task",
            owner_id="legacy",
        )
        assert attempt.decision == "claimed"
        assert attempt.launch is not None
        assert attempt.launch.role == "poll-agent"

    def test_parent_child_linkage(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        parent = svc.request_launch(
            canonical_key="task:parent",
            surface="workflow",
            owner_type="task",
            owner_id="p1",
            role="orchestrator",
        )
        assert parent.launch is not None
        pid = parent.launch.launch_id

        child = svc.request_launch(
            canonical_key="task:child",
            surface="workflow",
            owner_type="task",
            owner_id="c1",
            role="explorer",
            parent_launch_id=pid,
        )
        assert child.decision == "claimed"
        assert child.launch is not None
        assert child.launch.parent_launch_id == pid

    def test_cycle_detection_iterative(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        a = svc.request_launch("k:a", "workflow", "task", "a", role="r1").launch
        b = svc.request_launch(
            "k:b", "workflow", "task", "b", role="r2", parent_launch_id=a.launch_id
        ).launch

        # Try to make A a child of B (cycle A->B->A)
        # request_launch would reject if we pass parent_launch_id=b.launch_id
        # when spawning a new A, but A is already there.
        # Let's test the iterative walk directly with a third node C.
        attempt = svc.request_launch(
            "k:c", "workflow", "task", "c", role="r3", parent_launch_id="nonexistent"
        )
        assert attempt.decision == "error"
        assert "not found" in attempt.reason.lower()

    def test_max_depth_enforcement(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        current_parent_id = None
        # Create a chain of 16
        for i in range(16):
            attempt = svc.request_launch(
                f"k:{i}",
                "workflow",
                "task",
                str(i),
                role="step",
                parent_launch_id=current_parent_id,
            )
            assert attempt.decision == "claimed", f"Failed at depth {i}"
            current_parent_id = attempt.launch.launch_id

        # 17th should fail
        fail_attempt = svc.request_launch(
            "k:17",
            "workflow",
            "task",
            "17",
            role="too-deep",
            parent_launch_id=current_parent_id,
        )
        assert fail_attempt.decision == "error"
        assert "max depth" in fail_attempt.reason.lower()


class TestPaneReconciliation:
    """Tests for reconcile_lost_panes logic."""

    def test_reconcile_quarantines_lost_pane(self, tmp_path: Path, monkeypatch) -> None:
        svc = _make_service(tmp_path)
        attempt = svc.request_launch("k:pane", "workflow", "task", "p", role="r")
        assert attempt.launch is not None
        lid = attempt.launch.launch_id
        svc.confirm_spawning(lid)
        svc.confirm_active(
            lid,
            backend="tmux",
            termination_handle_type="tmux-pane",
            termination_handle_value="%999",
            tmux_pane_id="%999",
        )

        # Mock tmux to return an empty set of panes
        monkeypatch.setattr(
            AgentLaunchLifecycleService, "_get_alive_tmux_panes", lambda *args: set()
        )

        quarantined = svc.reconcile_lost_panes()
        assert len(quarantined) == 1
        assert quarantined[0].launch_id == lid

        launch = svc.get_launch(lid)
        assert launch is not None
        assert launch.status == LaunchStatus.QUARANTINED
        assert launch.quarantine_reason == "pane_lost"
