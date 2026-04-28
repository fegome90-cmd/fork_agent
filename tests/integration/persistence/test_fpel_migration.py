"""Integration tests for FPEL migration and schema integrity.

Task 2.4: Verifies:
- Schema compatibility (tables exist with correct columns)
- Seal idempotency UNIQUE constraint at DB level
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
from src.infrastructure.persistence.migrations import run_migrations


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FPEL_MIGRATION_NAME = "033_create_fpel_tables"


@pytest.fixture
def fpel_db(tmp_path: Path) -> DatabaseConnection:
    """Create a fresh DB with all migrations applied, including FPEL tables."""
    db_path = tmp_path / "fpel_test.db"
    config = DatabaseConfig(db_path=db_path)
    migrations_dir = Path(__file__).parent.parent.parent.parent / "src" / "infrastructure" / "persistence" / "migrations"
    run_migrations(config, migrations_dir)
    return DatabaseConnection(config=config)


# ---------------------------------------------------------------------------
# Schema compatibility — tables exist
# ---------------------------------------------------------------------------


class TestSchemaCompatibility:
    """Verify FPEL tables are created with correct columns."""

    def test_frozen_proposals_table_exists(self, fpel_db: DatabaseConnection) -> None:
        """frozen_proposals table must exist after migration."""
        with fpel_db as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='frozen_proposals'"
            )
            result = cursor.fetchone()
        assert result is not None, "frozen_proposals table must exist"

    def test_frozen_proposals_has_required_columns(self, fpel_db: DatabaseConnection) -> None:
        """frozen_proposals must have: frozen_proposal_id, target_id, content_hash, content, lifecycle."""
        required = {"frozen_proposal_id", "target_id", "content_hash", "content", "lifecycle"}
        with fpel_db as conn:
            cursor = conn.execute("PRAGMA table_info(frozen_proposals)")
            columns = {row["name"] for row in cursor.fetchall()}
        assert required.issubset(columns), f"Missing columns: {required - columns}"

    def test_sealed_verdicts_table_exists(self, fpel_db: DatabaseConnection) -> None:
        """sealed_verdicts table must exist after migration."""
        with fpel_db as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='sealed_verdicts'"
            )
            result = cursor.fetchone()
        assert result is not None, "sealed_verdicts table must exist"

    def test_sealed_verdicts_has_required_columns(self, fpel_db: DatabaseConnection) -> None:
        """sealed_verdicts must have: frozen_proposal_id, verdict, sealed_at, content_hash."""
        required = {"frozen_proposal_id", "verdict", "sealed_at", "content_hash"}
        with fpel_db as conn:
            cursor = conn.execute("PRAGMA table_info(sealed_verdicts)")
            columns = {row["name"] for row in cursor.fetchall()}
        assert required.issubset(columns), f"Missing columns: {required - columns}"

    def test_fpel_status_table_exists(self, fpel_db: DatabaseConnection) -> None:
        """fpel_status table must exist for tracking FPEL state per target."""
        with fpel_db as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='fpel_status'"
            )
            result = cursor.fetchone()
        assert result is not None, "fpel_status table must exist"

    def test_fpel_checker_reports_table_exists(self, fpel_db: DatabaseConnection) -> None:
        """fpel_checker_reports table must exist for storing checker evidence."""
        with fpel_db as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='fpel_checker_reports'"
            )
            result = cursor.fetchone()
        assert result is not None, "fpel_checker_reports table must exist"


# ---------------------------------------------------------------------------
# Seal idempotency — DB-level UNIQUE constraint
# ---------------------------------------------------------------------------


def _insert_frozen_proposal(conn, fp_id: str, target_id: str = "task-test") -> None:
    """Insert a frozen proposal row to satisfy FK constraints."""
    conn.execute(
        "INSERT INTO frozen_proposals (frozen_proposal_id, target_id, content_hash, content) "
        "VALUES (?, ?, 'abc123hash', 'test content')",
        (fp_id, target_id),
    )


class TestSealIdempotencyDBLevel:
    """Verify UNIQUE constraint on sealed_verdicts prevents duplicate seals at DB level."""

    def test_unique_constraint_rejects_duplicate_sealed_verdict(self, fpel_db: DatabaseConnection) -> None:
        """Inserting a second sealed verdict with same frozen_proposal_id MUST fail."""
        fp_id = "fp-test123abc"
        now = "2026-04-28T00:00:00Z"
        content_hash = "abc123hash"

        with fpel_db as conn:
            _insert_frozen_proposal(conn, fp_id)
            # First insert succeeds
            conn.execute(
                "INSERT INTO sealed_verdicts (frozen_proposal_id, verdict, sealed_at, content_hash) "
                "VALUES (?, 'SEALED_PASS', ?, ?)",
                (fp_id, now, content_hash),
            )
            conn.commit()

            # Second insert with same frozen_proposal_id MUST fail
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO sealed_verdicts (frozen_proposal_id, verdict, sealed_at, content_hash) "
                    "VALUES (?, 'SEALED_PASS', ?, ?)",
                    (fp_id, "2026-04-29T00:00:00Z", content_hash),
                )
                conn.commit()

    def test_different_frozen_ids_both_succeed(self, fpel_db: DatabaseConnection) -> None:
        """Different frozen_proposal_ids can each have one sealed verdict."""
        now = "2026-04-28T00:00:00Z"
        content_hash = "abc123hash"

        with fpel_db as conn:
            _insert_frozen_proposal(conn, "fp-aaa")
            _insert_frozen_proposal(conn, "fp-bbb")
            conn.execute(
                "INSERT INTO sealed_verdicts (frozen_proposal_id, verdict, sealed_at, content_hash) "
                "VALUES ('fp-aaa', 'SEALED_PASS', ?, ?)",
                (now, content_hash),
            )
            conn.execute(
                "INSERT INTO sealed_verdicts (frozen_proposal_id, verdict, sealed_at, content_hash) "
                "VALUES ('fp-bbb', 'SEALED_PASS', ?, ?)",
                (now, content_hash),
            )
            conn.commit()

            cursor = conn.execute("SELECT COUNT(*) FROM sealed_verdicts")
            count = cursor.fetchone()[0]
        assert count == 2
