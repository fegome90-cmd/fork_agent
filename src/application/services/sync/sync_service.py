"""Sync service for export/import operations with mutation tracking."""
from __future__ import annotations

import gzip
import hashlib
import json
import logging
import time
import uuid as uuid_mod
from contextlib import closing
from pathlib import Path
from typing import Any, Protocol

from src.application.exceptions import RepositoryError
from src.domain.entities.observation import Observation
from src.domain.entities.sync import SyncChunk, SyncMutation, SyncStatus

logger = logging.getLogger(__name__)


class ObservationRepositoryProtocol(Protocol):
    """Protocol for observation repository dependencies."""

    def get_all(
        self,
        limit: int | None = None,
        offset: int | None = None,
        type: str | None = None,
    ) -> list[Observation]:
        ...

    def count(self) -> int:
        ...

    def create(self, observation: Observation) -> None:
        ...

    def get_by_id(self, observation_id: str) -> Observation:
        ...

    def delete(self, observation_id: str) -> None:
        ...

    def update(self, observation: Observation) -> None:
        ...


class SyncRepositoryProtocol(Protocol):
    """Protocol for sync repository dependencies."""

    def record_chunk(self, chunk: SyncChunk) -> None:
        ...

    def get_chunk_by_id(self, chunk_id: str) -> SyncChunk | None:
        ...

    def list_chunks(self, source: str | None = None) -> list[SyncChunk]:
        ...

    def record_mutation(
        self,
        entity: str,
        entity_key: str,
        op: str,
        payload: str,
        source: str,
        project: str,
    ) -> int:
        ...

    def get_mutations_since(self, seq: int, limit: int | None = None) -> list[SyncMutation]:
        ...

    def get_latest_seq(self) -> int:
        ...

    def get_status(self) -> SyncStatus:
        ...

    def update_status(
        self,
        last_export_at: int | None = None,
        last_import_at: int | None = None,
        last_export_seq: int | None = None,
        mutation_count: int | None = None,
    ) -> None:
        ...


class SyncService:
    """Service for sync operations: export, import, and mutation tracking."""

    def __init__(
        self,
        observation_repo: ObservationRepositoryProtocol,
        sync_repo: SyncRepositoryProtocol,
        export_dir: Path = Path("~/.local/share/fork/sync").expanduser(),
        export_version: int = 1,
    ) -> None:
        """Initialize the sync service.

        Args:
            observation_repo: Repository for observation operations
            sync_repo: Repository for sync tracking
            export_dir: Directory for export files
            export_version: Export format version
        """
        self._observation_repo = observation_repo
        self._sync_repo = sync_repo
        self._export_dir = export_dir
        self._export_version = export_version

    def export_observations(
        self,
        project: str | None = None,
        chunk_size: int = 100,
    ) -> list[Path]:
        """Export observations to chunked JSONL files.

        When a watermark exists (last_export_seq > 0), exports only
        observations changed since the last export by reconstructing
        from the mutation journal.  Otherwise performs a full dump.

        Args:
            project: Optional project filter
            chunk_size: Number of observations per chunk

        Returns:
            List of chunk file paths created
        """
        self._export_dir.mkdir(parents=True, exist_ok=True)

        status = self._sync_repo.get_status()
        last_export_seq = status.last_export_seq or 0

        if last_export_seq > 0:
            # Incremental: reconstruct observations from mutations
            observations, export_max_seq = self._reconstruct_from_mutations(
                last_export_seq, project
            )
        else:
            # Full dump
            observations = self._observation_repo.get_all()
            if project:
                observations = [o for o in observations if o.project == project]
            export_max_seq = None

        if not observations:
            logger.info("No observations to export")
            return []

        observations.sort(key=lambda o: o.timestamp)

        chunk_paths: list[Path] = []
        total_observations = len(observations)
        chunk_count = (total_observations + chunk_size - 1) // chunk_size
        timestamp = int(time.time() * 1000)

        for i in range(chunk_count):
            start_idx = i * chunk_size
            end_idx = min((i + 1) * chunk_size, total_observations)
            chunk_obs = observations[start_idx:end_idx]

            chunk_path = self._write_chunk(chunk_obs, i, timestamp)
            chunk_paths.append(chunk_path)

        self._write_manifest(chunk_paths, total_observations, timestamp)

        # Advance watermark — use export_max_seq for incremental,
        # global latest_seq for full dump.
        watermark_seq = export_max_seq if export_max_seq is not None else self._sync_repo.get_latest_seq()
        self._sync_repo.update_status(
            last_export_at=timestamp,
            last_export_seq=watermark_seq,
        )

        logger.info(
            "Exported %d observations in %d chunks to %s",
            total_observations,
            len(chunk_paths),
            self._export_dir,
        )

        return chunk_paths

    def _reconstruct_from_mutations(
        self,
        since_seq: int,
        project: str | None = None,
    ) -> tuple[list[Observation], int]:
        """Reconstruct current observation state from mutations.

        Walks the mutation journal from *since_seq* (exclusive) to build
        the latest snapshot of each observation.  Delete mutations remove
        entries; the last insert/update wins per entity_key.

        Args:
            since_seq: Sequence number to start from (exclusive).
            project: Optional project filter applied to mutations.

        Returns:
            Tuple of (observations, max_seq) where *max_seq* is the
            highest sequence number of the **processed** mutations.
        """
        mutations = self._sync_repo.get_mutations_since(since_seq)

        obs_data: dict[str, dict[str, Any]] = {}
        deleted_ids: set[str] = set()
        max_seq = since_seq

        for m in mutations:
            max_seq = max(max_seq, m.seq)

            # Apply project filter after tracking watermark
            if project and m.project != project:
                continue

            if m.op == "delete":
                deleted_ids.add(m.entity_key)
                obs_data.pop(m.entity_key, None)
            elif m.op in ("insert", "update"):
                try:
                    payload = (
                        json.loads(m.payload)
                        if isinstance(m.payload, str)
                        else m.payload
                    )
                    obs_data[m.entity_key] = payload
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(
                        "Failed to parse mutation payload for seq %d: %s",
                        m.seq,
                        e,
                    )

        # Reconstruct Observation objects
        # Note: obs_data only contains keys that were inserted/updated AFTER
        # their last deletion (or never deleted). Keys removed by delete mutations
        # are popped from obs_data, so no deleted_ids check is needed here.
        observations: list[Observation] = []
        for obs_id, payload in obs_data.items():
            try:
                obs_type = payload.get("type")
                if obs_type is not None:
                    from src.domain.entities.observation import Observation as _Obs

                    if obs_type not in _Obs._ALLOWED_TYPES:
                        logger.warning(
                            "Skipping obs %s with invalid type: %s", obs_id, obs_type
                        )
                        obs_type = None
                obs = Observation(
                    id=payload.get("id", obs_id),
                    timestamp=payload.get("timestamp", 0),
                    content=payload.get("content", ""),
                    metadata=payload.get("metadata"),
                    idempotency_key=payload.get("idempotency_key"),
                    project=payload.get("project"),
                    type=obs_type,
                    topic_key=payload.get("topic_key"),
                    revision_count=payload.get("revision_count", 1),
                    session_id=payload.get("session_id"),
                )
                observations.append(obs)
            except (KeyError, TypeError) as e:
                logger.warning("Failed to reconstruct observation %s: %s", obs_id, e)

        return observations, max_seq

    def _write_chunk(self, observations: list[Observation], index: int, timestamp: int) -> Path:
        """Write a single chunk to a gzipped JSONL file."""
        chunk_id = f"sync_{timestamp}_{index:03d}"
        chunk_path = self._export_dir / f"{chunk_id}.jsonl.gz"

        lines: list[str] = []
        for obs in observations:
            obs_dict: dict[str, Any] = {
                "id": obs.id,
                "timestamp": obs.timestamp,
                "content": obs.content,
                "metadata": obs.metadata,
                "idempotency_key": obs.idempotency_key,
                "project": obs.project,
                "type": obs.type,
                "topic_key": obs.topic_key,
                "revision_count": obs.revision_count,
                "session_id": obs.session_id,
            }
            lines.append(json.dumps(obs_dict, separators=(",", ":")))

        content = "\n".join(lines).encode("utf-8")

        with gzip.open(chunk_path, "wb") as f:
            f.write(content)

        return chunk_path

    def _write_manifest(
        self,
        chunk_paths: list[Path],
        total_observations: int,
        timestamp: int,
    ) -> None:
        """Write the export manifest file."""
        hasher = hashlib.sha256()
        for chunk_path in chunk_paths:
            with open(chunk_path, "rb") as f:
                hasher.update(f.read())
        checksum = f"sha256:{hasher.hexdigest()}"

        manifest: dict[str, Any] = {
            "chunk_count": len(chunk_paths),
            "total_observations": total_observations,
            "checksum": checksum,
            "created_at": timestamp,
            "export_version": self._export_version,
        }

        manifest_path = self._export_dir / f"manifest_{timestamp}.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

    def _validate_manifest(
        self,
        chunk_paths: list[Path],
        manifest_path: Path | None = None,
    ) -> bool:
        """Verify SHA256 checksum of chunks matches manifest.

        Args:
            chunk_paths: List of chunk files to verify.
            manifest_path: Optional manifest file. If None, skips validation.

        Returns:
            True if valid or no manifest to check.

        Raises:
            ValueError: If checksum mismatch detected.
        """
        if manifest_path is None or not manifest_path.exists():
            return True

        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            raise ValueError(f"Invalid manifest file: {e}") from e

        expected = manifest.get("checksum", "")
        if not expected or not expected.startswith("sha256:"):
            return True  # Legacy manifest without checksum

        hasher = hashlib.sha256()
        for chunk_path in sorted(chunk_paths):
            if chunk_path.exists():
                with open(chunk_path, "rb") as f:
                    hasher.update(f.read())

        actual = f"sha256:{hasher.hexdigest()}"
        if actual != expected:
            raise ValueError(
                f"Manifest checksum mismatch: expected {expected}, got {actual}"
            )
        return True

    def import_observations(
        self,
        chunk_paths: list[Path],
        source: str = "import",
        manifest_path: Path | None = None,
    ) -> int:
        """Import observations from JSONL chunks.

        Args:
            chunk_paths: List of chunk file paths to import
            source: Source identifier for the import
            manifest_path: Optional manifest file for checksum validation.

        Returns:
            Number of observations imported
        """
        self._validate_manifest(chunk_paths, manifest_path)

        imported_count = 0
        timestamp = int(time.time() * 1000)

        # Suppress mutation recording during import to avoid ghost mutations
        self._disable_obs_mutation_recording()
        try:
            for chunk_path in chunk_paths:
                if not chunk_path.exists():
                    logger.warning("Chunk file not found: %s", chunk_path)
                    continue

                chunk_id = chunk_path.stem.replace(".jsonl", "")
                if self._sync_repo.get_chunk_by_id(chunk_id):
                    logger.info("Chunk %s already imported, skipping", chunk_id)
                    continue

                obs_count = self._import_single_chunk(chunk_path, source)
                imported_count += obs_count

                # Record chunk
                checksum = self._calculate_checksum(chunk_path)
                chunk = SyncChunk(
                    chunk_id=chunk_id,
                    source=source,
                    imported_at=timestamp,
                    observation_count=obs_count,
                    checksum=checksum,
                )
                self._sync_repo.record_chunk(chunk)
        finally:
            self._enable_obs_mutation_recording()

        if imported_count > 0:
            self._sync_repo.update_status(last_import_at=timestamp)

        logger.info(
            "Imported %d observations from %s chunks",
            imported_count,
            len(chunk_paths),
        )

        return imported_count

    def _import_single_chunk(self, chunk_path: Path, _source: str) -> int:
        """Import observations from a single chunk file.

        Args:
            chunk_path: Path to the chunk file
            source: Source identifier

        Returns:
            Number of observations imported from this chunk
        """
        imported = 0

        try:
            gz = gzip.open(chunk_path, "rt", encoding="utf-8")  # noqa: SIM115
        except OSError as e:
            logger.warning("Skipping corrupt/invalid chunk %s: %s", chunk_path, e)
            return 0

        with closing(gz):
            for line in gz:
                line = line.strip()
                if not line:
                    continue

                try:
                    obs_dict = json.loads(line)

                    # Validate UUID format at import boundary (RIPPER-009)
                    obs_id = obs_dict.get("id", "")
                    try:
                        uuid_mod.UUID(obs_id)
                    except (ValueError, AttributeError):
                        # Log warning but allow legacy/interop non-UUID IDs through
                        logger.debug(
                            "Non-UUID id on import: %s — allowing for compatibility",
                            str(obs_id)[:50],
                        )

                    # Validate type against allowed values
                    obs_type = obs_dict.get("type")
                    if obs_type is not None:
                        from src.domain.entities.observation import Observation as _Obs
                        if obs_type not in _Obs._ALLOWED_TYPES:
                            logger.warning("Skipping obs %s with invalid type: %s", obs_id, obs_type)
                            obs_type = None
                    observation = Observation(
                        id=obs_id,
                        timestamp=obs_dict["timestamp"],
                        content=obs_dict["content"],
                        metadata=obs_dict.get("metadata"),
                        idempotency_key=obs_dict.get("idempotency_key"),
                        project=obs_dict.get("project"),
                        type=obs_type,
                        topic_key=obs_dict.get("topic_key"),
                        revision_count=obs_dict.get("revision_count", 1),
                        session_id=obs_dict.get("session_id"),
                    )

                    # Try to create; if duplicate ID, skip silently
                    try:
                        self._observation_repo.create(observation)
                        imported += 1
                    except RepositoryError as e:
                        if "already exists" in str(e).lower():
                            logger.debug("Skipping duplicate observation: %s", observation.id)
                        else:
                            raise
                    except Exception:
                        raise

                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning("Failed to parse observation: %s", e)
                    continue

        return imported

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            hasher.update(f.read())
        return f"sha256:{hasher.hexdigest()}"

    def get_status(self) -> dict[str, Any]:
        """Get sync status: total obs, last sync, mutation count.

        Returns:
            Dictionary with sync status information
        """
        status = self._sync_repo.get_status()
        latest_seq = self._sync_repo.get_latest_seq()

        # Count total observations
        total_obs = self._observation_repo.count()

        return {
            "total_observations": total_obs,
            "last_export_at": status.last_export_at,
            "last_import_at": status.last_import_at,
            "last_export_seq": status.last_export_seq,
            "latest_seq": latest_seq,
            "mutation_count": status.mutation_count,
        }

    def get_mutations_since(self, seq: int) -> list[SyncMutation]:
        """Get mutations since given sequence number.

        Args:
            seq: The sequence number to start from (exclusive)

        Returns:
            List of mutations ordered by sequence number
        """
        return self._sync_repo.get_mutations_since(seq)

    def _disable_obs_mutation_recording(self) -> None:
        """Disable mutation recording on the observation repo (for imports)."""
        repo = self._observation_repo
        if hasattr(repo, "disable_mutation_recording"):
            repo.disable_mutation_recording()

    def _enable_obs_mutation_recording(self) -> None:
        """Re-enable mutation recording on the observation repo."""
        repo = self._observation_repo
        if hasattr(repo, "enable_mutation_recording"):
            repo.enable_mutation_recording()

    def record_mutation(
        self,
        entity: str,
        entity_key: str,
        op: str,
        payload: str,
        source: str = "local",
        project: str = "",
    ) -> None:
        """Record a mutation in the journal.

        Note: This method is not called externally. Mutation recording is
        handled automatically by ObservationRepository when sync_repo is
        configured. Prefer relying on repository-level mutation tracking
        rather than calling this method directly.

        Args:
            entity: Entity type (e.g., "observation")
            entity_key: Unique key for the entity
            op: Operation type (insert, update, delete)
            payload: JSON string containing mutation data
            source: Source of the mutation
            project: Project scope
        """
        self._sync_repo.record_mutation(
            entity=entity,
            entity_key=entity_key,
            op=op,
            payload=payload,
            source=source,
            project=project,
        )

    # ------------------------------------------------------------------
    # Incremental sync (mutations-based)
    # ------------------------------------------------------------------

    def export_incremental(
        self,
        _project: str | None = None,
        chunk_size: int = 100,
        commit_watermark: bool = True,
    ) -> list[Path]:
        """Export only mutations since last export.

        Writes mutations as JSONL.gz chunks. Each line is a mutation with
        its payload (full observation data for insert/update, id-only for delete).

        Args:
            _project: Reserved for future per-project incremental export.
            chunk_size: Mutations per chunk.
            commit_watermark: If True (default), advance the export watermark
                immediately.  Set to False when the caller needs to defer
                watermark advancement (e.g. until after a git push succeeds).
                Use ``commit_export_watermark()`` to advance later.

        Returns:
            List of chunk file paths.
        """
        status = self._sync_repo.get_status()
        last_seq = status.last_export_seq or 0
        mutations = self._sync_repo.get_mutations_since(last_seq)

        if not mutations:
            self._last_export_max_seq = 0
            return []

        self._export_dir.mkdir(parents=True, exist_ok=True)
        timestamp = int(time.time() * 1000)
        paths: list[Path] = []

        max_seq = last_seq
        for i in range(0, len(mutations), chunk_size):
            batch = mutations[i : i + chunk_size]
            chunk_path = self._write_mutation_chunk(batch, i // chunk_size, timestamp)
            paths.append(chunk_path)
            max_seq = max(m.seq for m in batch)

        # Write manifest
        self._write_manifest(paths, len(mutations), timestamp)

        # Store max_seq so the caller can commit later if needed
        self._last_export_max_seq = max_seq
        self._last_export_timestamp = timestamp

        if commit_watermark:
            self._sync_repo.update_status(
                last_export_at=timestamp,
                last_export_seq=max_seq,
            )

        logger.info(
            "Exported %d mutations (seq %d-%d) to %d chunks",
            len(mutations),
            last_seq + 1,
            max_seq,
            len(paths),
        )
        return paths

    def commit_export_watermark(self) -> None:
        """Advance the export watermark to the last exported seq.

        Call this only after the exported chunks have been successfully
        delivered (e.g. after a successful git push).  If no export has
        been performed, this is a no-op.
        """
        max_seq = getattr(self, "_last_export_max_seq", 0)
        if max_seq <= 0:
            return
        timestamp = getattr(self, "_last_export_timestamp", 0) or int(time.time() * 1000)
        self._sync_repo.update_status(
            last_export_at=timestamp,
            last_export_seq=max_seq,
        )
        logger.info("Committed export watermark to seq %d", max_seq)

    def _write_mutation_chunk(
        self,
        mutations: list[SyncMutation],
        index: int,
        timestamp: int,
    ) -> Path:
        """Write a list of mutations to a gzipped JSONL chunk."""
        chunk_id = f"mutation_{timestamp}_{index:03d}"
        chunk_path = self._export_dir / f"{chunk_id}.jsonl.gz"

        with gzip.open(chunk_path, "wt", encoding="utf-8") as f:
            for m in mutations:
                line = json.dumps(
                    {
                        "seq": m.seq,
                        "entity": m.entity,
                        "entity_key": m.entity_key,
                        "op": m.op,
                        "payload": m.payload,
                        "source": m.source,
                        "project": m.project,
                        "created_at": m.created_at,
                    },
                    ensure_ascii=False,
                )
                f.write(line + "\n")

        return chunk_path

    def import_mutations(
        self,
        chunk_paths: list[Path],
        source: str = "pull",
        manifest_path: Path | None = None,
    ) -> dict[str, int]:
        """Import mutations from incremental chunks.

        Applies each mutation in order:
        - insert: INSERT OR IGNORE
        - update: upsert (insert if missing, update if exists)
        - delete: DELETE if exists

        Returns:
            Dictionary with counts: {"inserted": N, "updated": N, "deleted": N, "skipped": N}
        """
        self._validate_manifest(chunk_paths, manifest_path)

        counts: dict[str, int] = {"inserted": 0, "updated": 0, "deleted": 0, "skipped": 0}
        timestamp = int(time.time() * 1000)

        # Suppress mutation recording during import to avoid ghost mutations
        self._disable_obs_mutation_recording()
        try:
            for chunk_path in chunk_paths:
                chunk_id = chunk_path.stem.replace(".jsonl", "")
                if self._sync_repo.get_chunk_by_id(chunk_id) is not None:
                    logger.debug("Skipping already-imported chunk: %s", chunk_id)
                    continue

                obs_count = 0
                try:
                    gz = gzip.open(chunk_path, "rt", encoding="utf-8")  # noqa: SIM115
                except OSError as e:
                    logger.warning("Skipping corrupt/invalid mutation chunk %s: %s", chunk_path, e)
                    continue

                with closing(gz):
                    for line in gz:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            mutation = json.loads(line)
                            applied = self._apply_mutation(mutation)
                            counts[applied] += 1
                            if applied != "skipped":
                                obs_count += 1
                        except (json.JSONDecodeError, KeyError) as e:
                            logger.warning("Failed to parse mutation: %s", e)
                            counts["skipped"] += 1

                checksum = self._calculate_checksum(chunk_path)
                self._sync_repo.record_chunk(
                    SyncChunk(
                        chunk_id=chunk_id,
                        source=source,
                        imported_at=timestamp,
                        observation_count=obs_count,
                        checksum=checksum,
                    )
                )
        finally:
            self._enable_obs_mutation_recording()

        self._sync_repo.update_status(last_import_at=timestamp)
        return counts

    def _apply_mutation(self, mutation: dict[str, Any]) -> str:
        """Apply a single mutation. Returns the count key."""
        op = mutation["op"]
        payload = json.loads(mutation["payload"]) if isinstance(mutation["payload"], str) else mutation["payload"]

        if op == "delete":
            try:
                self._observation_repo.delete(payload["id"])
                return "deleted"
            except Exception:
                logger.debug("Sync delete failed for %s", payload.get("id"), exc_info=True)
                return "skipped"

        if op in ("insert", "update"):
            observation = Observation(
                id=payload.get("id", mutation["entity_key"]),
                timestamp=payload.get("timestamp", mutation.get("created_at", 0)),
                content=payload.get("content", ""),
                metadata=payload.get("metadata"),
                idempotency_key=payload.get("idempotency_key"),
                project=payload.get("project"),
                type=payload.get("type"),
                topic_key=payload.get("topic_key"),
                revision_count=payload.get("revision_count", 1),
                session_id=payload.get("session_id"),
            )
            if op == "insert":
                try:
                    self._observation_repo.create(observation)
                    return "inserted"
                except Exception:
                    logger.debug("Sync insert failed (duplicate?)", exc_info=True)
                    return "skipped"  # duplicate
            else:
                try:
                    self._observation_repo.update(observation)
                    return "updated"
                except Exception as update_err:
                    # Only fall back to insert if observation not found
                    err_str = str(update_err).lower()
                    if "not found" in err_str:
                        logger.debug("Sync update not found, trying insert", exc_info=True)
                        try:
                            self._observation_repo.create(observation)
                            return "inserted"
                        except Exception:
                            logger.debug("Sync fallback insert failed", exc_info=True)
                    else:
                        logger.warning("Sync update failed: %s", update_err)
                    return "skipped"

        return "skipped"
