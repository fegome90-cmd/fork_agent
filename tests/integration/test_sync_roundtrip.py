"""Integration tests: full sync roundtrip using real DI wiring.

Tests create_container → export → import into a fresh container → verify data.
"""

from __future__ import annotations

from pathlib import Path

from src.domain.entities.observation import Observation
from src.infrastructure.persistence.container import create_container


def _make_obs(
    obs_id: str = "test-1",
    content: str = "hello",
    project: str | None = None,
    obs_type: str | None = None,
    topic_key: str | None = None,
) -> Observation:
    return Observation(
        id=obs_id,
        timestamp=1000,
        content=content,
        metadata=None,
        idempotency_key=f"ik-{obs_id}",
        project=project,
        type=obs_type,
        topic_key=topic_key,
        revision_count=1,
        session_id="sess-integ",
    )


class TestSyncRoundtripIntegration:
    def test_insert_update_delete_roundtrip(self, tmp_path: Path) -> None:
        """Insert+update+delete on DB-A, export, import into DB-B, verify."""
        # --- DB-A: mutate data ---
        container_a = create_container(tmp_path / "db_a.db")
        repo_a = container_a.observation_repository()
        sync_a = container_a.sync_service()
        export_dir = tmp_path / "sync"
        sync_a._export_dir = export_dir

        repo_a.create(_make_obs("rud-1", "original"))
        repo_a.create(_make_obs("rud-2", "keep"))
        repo_a.update(
            Observation(
                id="rud-1",
                timestamp=2000,
                content="updated",
                metadata=None,
                idempotency_key="ik-rud-1",
                project=None,
                type=None,
                topic_key=None,
                revision_count=2,
                session_id="sess-integ",
            )
        )
        repo_a.delete("rud-2")

        # Export from A
        chunks = sync_a.export_incremental()
        assert len(chunks) >= 1

        # --- DB-B: fresh import ---
        container_b = create_container(tmp_path / "db_b.db")
        sync_b = container_b.sync_service()
        sync_b._export_dir = export_dir

        counts = sync_b.import_mutations(chunks, source="integ-test")
        # Insert mutations for rud-1 and rud-2 are applied first,
        # then update on rud-1 and delete on rud-2.
        assert counts["inserted"] >= 2  # rud-1 + rud-2 (via insert mutations)
        assert counts["updated"] >= 1  # rud-1
        assert counts["deleted"] == 1  # rud-2

        # Verify final state: only rud-1 with "updated" content
        repo_b = container_b.observation_repository()
        all_obs = repo_b.get_all()
        assert len(all_obs) == 1
        assert all_obs[0].id == "rud-1"
        assert all_obs[0].content == "updated"

    def test_export_import_preserves_all_fields(self, tmp_path: Path) -> None:
        """All 10 observation fields survive export+import via DI."""
        container_a = create_container(tmp_path / "db_a.db")
        repo_a = container_a.observation_repository()
        sync_a = container_a.sync_service()
        export_dir = tmp_path / "sync"
        sync_a._export_dir = export_dir

        obs = Observation(
            id="fields-rt",
            timestamp=9999,
            content="all fields",
            metadata={"env": "prod", "v": 3},
            idempotency_key="ik-fields-rt",
            project="proj-x",
            type="discovery",
            topic_key="proj-x/fields-rt",
            revision_count=5,
            session_id="sess-field-rt",
        )
        repo_a.create(obs)

        chunks = sync_a.export_observations()
        assert len(chunks) == 1

        container_b = create_container(tmp_path / "db_b.db")
        sync_b = container_b.sync_service()
        sync_b._export_dir = export_dir

        imported = sync_b.import_observations(chunks, source="field-test")
        assert imported == 1

        repo_b = container_b.observation_repository()
        result = repo_b.get_by_id("fields-rt")
        assert result.id == "fields-rt"
        assert result.timestamp == 9999
        assert result.content == "all fields"
        assert result.metadata == {"env": "prod", "v": 3}
        assert result.idempotency_key == "ik-fields-rt"
        assert result.project == "proj-x"
        assert result.type == "discovery"
        assert result.topic_key == "proj-x/fields-rt"
        assert result.revision_count == 5
        assert result.session_id == "sess-field-rt"

    def test_get_status_after_roundtrip(self, tmp_path: Path) -> None:
        """Status tracking after export+import on both databases."""
        container_a = create_container(tmp_path / "db_a.db")
        repo_a = container_a.observation_repository()
        sync_a = container_a.sync_service()
        export_dir = tmp_path / "sync"
        sync_a._export_dir = export_dir

        repo_a.create(_make_obs("stat-1", "status test"))
        repo_a.create(_make_obs("stat-2", "another"))

        # Export
        chunks = sync_a.export_observations()
        assert len(chunks) == 1

        # Check status after export
        status_a = sync_a.get_status()
        assert status_a["total_observations"] == 2
        assert status_a["last_export_at"] is not None

        # Import into B
        container_b = create_container(tmp_path / "db_b.db")
        sync_b = container_b.sync_service()
        sync_b._export_dir = export_dir

        imported = sync_b.import_observations(chunks, source="status-test")
        assert imported == 2

        status_b = sync_b.get_status()
        assert status_b["total_observations"] == 2
        assert status_b["last_import_at"] is not None

    def test_multi_operation_sequence_integrity(self, tmp_path: Path) -> None:
        """3 obs, update 1, delete 1, roundtrip, verify 2 remain."""
        container_a = create_container(tmp_path / "db_a.db")
        repo_a = container_a.observation_repository()
        sync_a = container_a.sync_service()
        export_dir = tmp_path / "sync"
        sync_a._export_dir = export_dir

        # Create 3 observations
        repo_a.create(_make_obs("seq-1", "keep"))
        repo_a.create(_make_obs("seq-2", "update-me"))
        repo_a.create(_make_obs("seq-3", "delete-me"))

        # Update seq-2
        repo_a.update(
            Observation(
                id="seq-2",
                timestamp=2000,
                content="updated",
                metadata=None,
                idempotency_key="ik-seq-2",
                project=None,
                type=None,
                topic_key=None,
                revision_count=2,
                session_id="sess-integ",
            )
        )

        # Delete seq-3
        repo_a.delete("seq-3")

        # Export mutations
        chunks = sync_a.export_incremental()
        assert len(chunks) >= 1

        # Import into fresh DB
        container_b = create_container(tmp_path / "db_b.db")
        sync_b = container_b.sync_service()
        sync_b._export_dir = export_dir

        counts = sync_b.import_mutations(chunks, source="seq-test")
        # 3 inserts (all three obs), then update on seq-2, delete on seq-3
        assert counts["inserted"] == 3
        assert counts["deleted"] == 1

        repo_b = container_b.observation_repository()
        all_obs = repo_b.get_all()
        assert len(all_obs) == 2

        ids = {o.id for o in all_obs}
        assert "seq-1" in ids
        assert "seq-2" in ids
        assert "seq-3" not in ids  # Was deleted

        # Verify seq-2 content
        seq2 = [o for o in all_obs if o.id == "seq-2"][0]
        assert seq2.content == "updated"
