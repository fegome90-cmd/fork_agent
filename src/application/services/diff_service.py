"""Service for comparing observations between references."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol


class _ObservationReader(Protocol):
    """Minimal protocol for repo methods used by DiffService."""

    def get_by_timestamp_range(self, start: int, end: int) -> list: ...
    def get_by_session_id(self, session_id: str, project: str | None = None) -> list: ...
    def get_by_id(self, observation_id: str): ...  # noqa: ANN001


@dataclass(frozen=True)
class DiffEntry:
    """A single diff entry between two observations."""

    status: Literal["added", "removed", "modified", "unchanged"]
    topic_key: str
    content: str
    previous_content: str | None = None
    observation_id: str | None = None
    previous_id: str | None = None


@dataclass(frozen=True)
class DiffResult:
    """Result of diffing observations between two references."""

    reference_label: str
    target_label: str
    entries: tuple[DiffEntry, ...]
    summary: dict[str, int]


class DiffService:
    """Compare observations between two references (timestamps, sessions, IDs)."""

    def __init__(self, repo: _ObservationReader) -> None:
        self._repo = repo

    def diff_by_timestamp(
        self,
        before: tuple[int, int],
        after: tuple[int, int],
        project: str | None = None,
        obs_type: str | None = None,
    ) -> DiffResult:
        """Diff observations between two timestamp windows.

        Args:
            before: (start, end) for reference window.
            after: (start, end) for target window.
            project: Optional project filter.
            obs_type: Optional observation type filter.

        Returns:
            DiffResult with comparison entries and summary.
        """
        ref_obs = self._repo.get_by_timestamp_range(before[0], before[1])
        target_obs = self._repo.get_by_timestamp_range(after[0], after[1])
        return self._compare(
            ref_obs, target_obs,
            f"timestamp:{before[0]}-{before[1]}",
            f"timestamp:{after[0]}-{after[1]}",
            project, obs_type,
        )

    def diff_by_session(
        self,
        session_a: str,
        session_b: str,
        project: str | None = None,
        obs_type: str | None = None,
    ) -> DiffResult:
        """Diff observations between two sessions.

        Args:
            session_a: Reference session ID.
            session_b: Target session ID.
            project: Optional project filter.
            obs_type: Optional observation type filter.

        Returns:
            DiffResult with comparison entries and summary.

        Raises:
            ValueError: If no observations found for either session.
        """
        ref_obs = self._repo.get_by_session_id(session_a)
        target_obs = self._repo.get_by_session_id(session_b)

        if not ref_obs:
            raise ValueError(f"No observations found for reference session '{session_a}'")
        if not target_obs:
            raise ValueError(f"No observations found for target session '{session_b}'")

        return self._compare(
            ref_obs, target_obs,
            f"session:{session_a}",
            f"session:{session_b}",
            project, obs_type,
        )

    def diff_by_id(self, id_a: str, id_b: str) -> DiffResult:
        """Diff two individual observations by ID.

        Args:
            id_a: First observation ID.
            id_b: Second observation ID.

        Returns:
            DiffResult with field-level comparison.

        Raises:
            ValueError: If either observation is not found.
        """
        obs_a = self._repo.get_by_id(id_a)
        obs_b = self._repo.get_by_id(id_b)

        key_a = obs_a.topic_key if obs_a.topic_key else obs_a.id[:8]
        key_b = obs_b.topic_key if obs_b.topic_key else obs_b.id[:8]

        if obs_a.content != obs_b.content:
            status: Literal["added", "removed", "modified", "unchanged"] = "modified"
        else:
            status = "unchanged"

        entry = DiffEntry(
            status=status,
            topic_key=f"{key_a} vs {key_b}",
            content=obs_b.content,
            previous_content=obs_a.content,
            observation_id=obs_b.id,
            previous_id=obs_a.id,
        )

        return DiffResult(
            reference_label=f"id:{id_a}",
            target_label=f"id:{id_b}",
            entries=(entry,),
            summary={"modified": 1 if status == "modified" else 0, "unchanged": 1 if status == "unchanged" else 0, "added": 0, "removed": 0},
        )

    def _compare(
        self,
        ref_obs: list,
        target_obs: list,
        ref_label: str,
        target_label: str,
        project: str | None,
        obs_type: str | None,
    ) -> DiffResult:
        """Compare two observation lists by topic_key/index key."""
        if project:
            ref_obs = [o for o in ref_obs if getattr(o, "project", None) == project]
            target_obs = [o for o in target_obs if getattr(o, "project", None) == project]
        if obs_type:
            ref_obs = [o for o in ref_obs if getattr(o, "type", None) == obs_type]
            target_obs = [o for o in target_obs if getattr(o, "type", None) == obs_type]

        def _key(o: object) -> str:
            tk = getattr(o, "topic_key", None)
            if tk:
                return tk
            return getattr(o, "id", "")[:8]

        def _build_map(obs_list: list) -> dict[str, object]:
            mapping: dict[str, object] = {}
            for obs in obs_list:
                k = _key(obs)
                existing = mapping.get(k)
                if existing is None or getattr(obs, "timestamp", 0) > getattr(existing, "timestamp", 0):
                    mapping[k] = obs
            return mapping

        ref_map = _build_map(ref_obs)
        target_map = _build_map(target_obs)

        all_keys = sorted(set(ref_map) | set(target_map))
        entries: list[DiffEntry] = []
        counts = {"added": 0, "removed": 0, "modified": 0, "unchanged": 0}

        for key in all_keys:
            r = ref_map.get(key)
            t = target_map.get(key)

            if r is not None and t is None:
                entries.append(DiffEntry(
                    status="removed",
                    topic_key=key,
                    content=getattr(r, "content", ""),
                    observation_id=getattr(r, "id", None),
                ))
                counts["removed"] += 1
            elif r is None and t is not None:
                entries.append(DiffEntry(
                    status="added",
                    topic_key=key,
                    content=getattr(t, "content", ""),
                    observation_id=getattr(t, "id", None),
                ))
                counts["added"] += 1
            else:
                r_content = getattr(r, "content", "")
                t_content = getattr(t, "content", "")
                if r_content != t_content:
                    entries.append(DiffEntry(
                        status="modified",
                        topic_key=key,
                        content=t_content,
                        previous_content=r_content,
                        observation_id=getattr(t, "id", None),
                        previous_id=getattr(r, "id", None),
                    ))
                    counts["modified"] += 1
                # unchanged entries are tracked but not included in entries list

        # Sort: added first, modified, removed
        order = {"added": 0, "modified": 1, "removed": 2}
        entries.sort(key=lambda e: (order.get(e.status, 99), e.topic_key))

        return DiffResult(
            reference_label=ref_label,
            target_label=target_label,
            entries=tuple(entries),
            summary=counts,
        )
