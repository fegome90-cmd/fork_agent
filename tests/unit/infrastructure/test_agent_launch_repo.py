"""Tests for SqliteAgentLaunchRepository — atomic claim, CAS, and query operations."""

from __future__ import annotations

import time
import uuid
from pathlib import Path

from src.domain.entities.agent_launch import AgentLaunch, LaunchStatus
from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
from src.infrastructure.persistence.repositories.agent_launch_repository import (
    SqliteAgentLaunchRepository,
)


def _make_repo(tmp_path: Path) -> SqliteAgentLaunchRepository:
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
            CREATE INDEX IF NOT EXISTS idx_launch_surface ON agent_launch_registry (surface);
        """)
    return SqliteAgentLaunchRepository(connection=conn)


def _claim_id() -> str:
    return uuid.uuid4().hex


class TestAtomicClaim:
    """Atomic claim prevents duplicate active launches for the same canonical key."""

    def test_first_claim_succeeds(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        result = repo.claim(
            launch_id=_claim_id(),
            canonical_key="task:abc123",
            surface="polling",
            owner_type="task",
            owner_id="abc123",
            lease_expires_at=int(time.time() * 1000) + 60_000,
        )
        assert result is not None
        assert result.status == LaunchStatus.RESERVED
        assert result.canonical_key == "task:abc123"
        assert result.surface == "polling"
        assert result.reserved_at is not None
        assert result.lease_expires_at is not None

    def test_second_claim_for_same_key_returns_none(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        lease = int(time.time() * 1000) + 60_000
        first = repo.claim(
            launch_id=_claim_id(),
            canonical_key="task:dup",
            surface="polling",
            owner_type="task",
            owner_id="dup",
            lease_expires_at=lease,
        )
        assert first is not None

        second = repo.claim(
            launch_id=_claim_id(),
            canonical_key="task:dup",
            surface="polling",
            owner_type="task",
            owner_id="dup",
            lease_expires_at=lease,
        )
        assert second is None

    def test_claim_for_different_key_succeeds(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        lease = int(time.time() * 1000) + 60_000
        first = repo.claim(
            launch_id=_claim_id(),
            canonical_key="task:key1",
            surface="polling",
            owner_type="task",
            owner_id="key1",
            lease_expires_at=lease,
        )
        assert first is not None

        second = repo.claim(
            launch_id=_claim_id(),
            canonical_key="task:key2",
            surface="api",
            owner_type="task",
            owner_id="key2",
            lease_expires_at=lease,
        )
        assert second is not None

    def test_claim_succeeds_after_terminal_status(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        lid = _claim_id()
        lease = int(time.time() * 1000) + 60_000
        repo.claim(
            launch_id=lid,
            canonical_key="task:terminal",
            surface="polling",
            owner_type="task",
            owner_id="terminal",
            lease_expires_at=lease,
        )
        # Move to terminal
        repo.cas_update_status(lid, LaunchStatus.RESERVED, LaunchStatus.FAILED, error="boom")

        # Should be able to claim again
        new_claim = repo.claim(
            launch_id=_claim_id(),
            canonical_key="task:terminal",
            surface="polling",
            owner_type="task",
            owner_id="terminal",
            lease_expires_at=lease,
        )
        assert new_claim is not None

    def test_claim_blocked_when_active(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        lid = _claim_id()
        lease = int(time.time() * 1000) + 60_000
        repo.claim(
            launch_id=lid,
            canonical_key="task:active",
            surface="polling",
            owner_type="task",
            owner_id="active",
            lease_expires_at=lease,
        )
        repo.cas_update_status(lid, LaunchStatus.RESERVED, LaunchStatus.SPAWNING)
        repo.cas_update_status(lid, LaunchStatus.SPAWNING, LaunchStatus.ACTIVE)

        duplicate = repo.claim(
            launch_id=_claim_id(),
            canonical_key="task:active",
            surface="api",
            owner_type="task",
            owner_id="active",
            lease_expires_at=lease,
        )
        assert duplicate is None


class TestCasUpdateStatus:
    """CAS status transitions with metadata capture."""

    def test_cas_succeeds_when_status_matches(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        lid = _claim_id()
        lease = int(time.time() * 1000) + 60_000
        repo.claim(
            launch_id=lid,
            canonical_key="task:cas1",
            surface="polling",
            owner_type="task",
            owner_id="cas1",
            lease_expires_at=lease,
        )
        ok = repo.cas_update_status(lid, LaunchStatus.RESERVED, LaunchStatus.SPAWNING)
        assert ok is True

        launch = repo.get_by_launch_id(lid)
        assert launch is not None
        assert launch.status == LaunchStatus.SPAWNING

    def test_cas_fails_when_status_mismatched(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        lid = _claim_id()
        lease = int(time.time() * 1000) + 60_000
        repo.claim(
            launch_id=lid,
            canonical_key="task:cas2",
            surface="polling",
            owner_type="task",
            owner_id="cas2",
            lease_expires_at=lease,
        )
        # Try to transition from ACTIVE (wrong — it's RESERVED)
        ok = repo.cas_update_status(lid, LaunchStatus.ACTIVE, LaunchStatus.TERMINATING)
        assert ok is False

    def test_terminal_transition_sets_ended_at(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        lid = _claim_id()
        lease = int(time.time() * 1000) + 60_000
        repo.claim(
            launch_id=lid,
            canonical_key="task:term",
            surface="polling",
            owner_type="task",
            owner_id="term",
            lease_expires_at=lease,
        )
        repo.cas_update_status(lid, LaunchStatus.RESERVED, LaunchStatus.SPAWNING)
        repo.cas_update_status(lid, LaunchStatus.SPAWNING, LaunchStatus.ACTIVE)
        repo.cas_update_status(
            lid,
            LaunchStatus.ACTIVE,
            LaunchStatus.TERMINATED,
        )
        launch = repo.get_by_launch_id(lid)
        assert launch is not None
        assert launch.status == LaunchStatus.TERMINATED
        assert launch.ended_at is not None

    def test_cas_captures_termination_metadata(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        lid = _claim_id()
        lease = int(time.time() * 1000) + 60_000
        repo.claim(
            launch_id=lid,
            canonical_key="task:meta",
            surface="polling",
            owner_type="task",
            owner_id="meta",
            lease_expires_at=lease,
        )
        repo.cas_update_status(
            lid,
            LaunchStatus.RESERVED,
            LaunchStatus.SPAWNING,
            backend="tmux",
            tmux_pane_id="%42",
            termination_handle_type="tmux-pane",
            termination_handle_value="%42",
        )
        launch = repo.get_by_launch_id(lid)
        assert launch is not None
        assert launch.backend == "tmux"
        assert launch.tmux_pane_id == "%42"
        assert launch.termination_handle_type == "tmux-pane"

    def test_cas_captures_subprocess_metadata(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        lid = _claim_id()
        lease = int(time.time() * 1000) + 60_000
        repo.claim(
            launch_id=lid,
            canonical_key="task:sub",
            surface="polling",
            owner_type="task",
            owner_id="sub",
            lease_expires_at=lease,
        )
        repo.cas_update_status(
            lid,
            LaunchStatus.RESERVED,
            LaunchStatus.SPAWNING,
            backend="subprocess",
            process_pid=12345,
            process_pgid=12340,
            termination_handle_type="pgid",
            termination_handle_value="12340",
        )
        launch = repo.get_by_launch_id(lid)
        assert launch is not None
        assert launch.process_pid == 12345
        assert launch.process_pgid == 12340

    def test_quarantine_sets_reason(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        lid = _claim_id()
        lease = int(time.time() * 1000) + 60_000
        repo.claim(
            launch_id=lid,
            canonical_key="task:q",
            surface="polling",
            owner_type="task",
            owner_id="q",
            lease_expires_at=lease,
        )
        repo.cas_update_status(
            lid,
            LaunchStatus.RESERVED,
            LaunchStatus.QUARANTINED,
            quarantine_reason="spawn unresolved",
        )
        launch = repo.get_by_launch_id(lid)
        assert launch is not None
        assert launch.status == LaunchStatus.QUARANTINED
        assert launch.quarantine_reason == "spawn unresolved"


class TestQueryOperations:
    """find_active, list_by_status, list_expired_leases, count_by_status."""

    def test_find_active_by_canonical_key(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        lid = _claim_id()
        lease = int(time.time() * 1000) + 60_000
        repo.claim(
            launch_id=lid,
            canonical_key="task:find",
            surface="polling",
            owner_type="task",
            owner_id="find",
            lease_expires_at=lease,
        )
        found = repo.find_active_by_canonical_key("task:find")
        assert found is not None
        assert found.launch_id == lid

    def test_find_active_returns_none_for_terminal(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        lid = _claim_id()
        lease = int(time.time() * 1000) + 60_000
        repo.claim(
            launch_id=lid,
            canonical_key="task:gone",
            surface="polling",
            owner_type="task",
            owner_id="gone",
            lease_expires_at=lease,
        )
        repo.cas_update_status(lid, LaunchStatus.RESERVED, LaunchStatus.FAILED, error="nope")
        found = repo.find_active_by_canonical_key("task:gone")
        assert found is None

    def test_list_by_status(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        lease = int(time.time() * 1000) + 60_000
        for i in range(3):
            repo.claim(
                launch_id=_claim_id(),
                canonical_key=f"task:list{i}",
                surface="polling",
                owner_type="task",
                owner_id=f"list{i}",
                lease_expires_at=lease,
            )
        reserved = repo.list_by_status(LaunchStatus.RESERVED)
        assert len(reserved) == 3

    def test_list_expired_leases(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        # Create a claim that already expired
        past_lease = int(time.time() * 1000) - 10_000
        repo.claim(
            launch_id=_claim_id(),
            canonical_key="task:expired",
            surface="polling",
            owner_type="task",
            owner_id="expired",
            lease_expires_at=past_lease,
        )
        now_ms = int(time.time() * 1000)
        expired = repo.list_expired_leases(now_ms)
        assert len(expired) == 1
        assert expired[0].canonical_key == "task:expired"

    def test_list_expired_leases_excludes_active(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        # Active launches should NOT appear in expired leases even if lease is old
        past_lease = int(time.time() * 1000) - 10_000
        lid = _claim_id()
        repo.claim(
            launch_id=lid,
            canonical_key="task:active-exp",
            surface="polling",
            owner_type="task",
            owner_id="active-exp",
            lease_expires_at=past_lease,
        )
        repo.cas_update_status(lid, LaunchStatus.RESERVED, LaunchStatus.SPAWNING)
        repo.cas_update_status(lid, LaunchStatus.SPAWNING, LaunchStatus.ACTIVE)

        now_ms = int(time.time() * 1000)
        expired = repo.list_expired_leases(now_ms)
        assert len(expired) == 0

    def test_count_by_status(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        lease = int(time.time() * 1000) + 60_000
        lid1 = _claim_id()
        repo.claim(
            launch_id=lid1,
            canonical_key="task:c1",
            surface="polling",
            owner_type="task",
            owner_id="c1",
            lease_expires_at=lease,
        )
        repo.cas_update_status(lid1, LaunchStatus.RESERVED, LaunchStatus.FAILED, error="x")

        repo.claim(
            launch_id=_claim_id(),
            canonical_key="task:c2",
            surface="polling",
            owner_type="task",
            owner_id="c2",
            lease_expires_at=lease,
        )
        counts = repo.count_by_status()
        assert counts.get("RESERVED", 0) == 1
        assert counts.get("FAILED", 0) == 1


class TestAgentLaunchEntity:
    """AgentLaunch domain entity validation and helpers."""

    def test_blocking_property(self) -> None:
        launch = AgentLaunch(
            launch_id="abc",
            canonical_key="task:1",
            surface="polling",
            owner_type="task",
            owner_id="1",
            status=LaunchStatus.RESERVED,
        )
        assert launch.is_blocking is True

        terminal = AgentLaunch(
            launch_id="abc",
            canonical_key="task:1",
            surface="polling",
            owner_type="task",
            owner_id="1",
            status=LaunchStatus.TERMINATED,
        )
        assert terminal.is_blocking is False

    def test_terminal_property(self) -> None:
        for status in (LaunchStatus.TERMINATED, LaunchStatus.FAILED, LaunchStatus.SUPPRESSED_DUPLICATE):
            launch = AgentLaunch(
                launch_id="x",
                canonical_key="task:1",
                surface="polling",
                owner_type="task",
                owner_id="1",
                status=status,
            )
            assert launch.is_terminal is True

    def test_valid_transitions(self) -> None:
        launch = AgentLaunch(
            launch_id="x",
            canonical_key="task:1",
            surface="polling",
            owner_type="task",
            owner_id="1",
            status=LaunchStatus.RESERVED,
        )
        assert launch.can_transition_to(LaunchStatus.SPAWNING) is True
        assert launch.can_transition_to(LaunchStatus.ACTIVE) is False
        assert launch.can_transition_to(LaunchStatus.FAILED) is True

    def test_termination_handle(self) -> None:
        launch = AgentLaunch(
            launch_id="x",
            canonical_key="task:1",
            surface="polling",
            owner_type="task",
            owner_id="1",
            status=LaunchStatus.ACTIVE,
            termination_handle_type="tmux-pane",
            termination_handle_value="%42",
        )
        handle = launch.termination_handle
        assert handle == {"type": "tmux-pane", "value": "%42"}
