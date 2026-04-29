"""Port for poll run persistence."""

from __future__ import annotations

from typing import Protocol

from src.domain.entities.poll_run import PollRun, PollRunStatus


class PollRunRepository(Protocol):
    """Protocol for poll run persistence."""

    def save(self, run: PollRun) -> None: ...

    def get_by_id(self, run_id: str) -> PollRun | None: ...

    def list_by_status(self, status: PollRunStatus) -> list[PollRun]: ...

    def list_active(self) -> list[PollRun]: ...

    def list_launch_blocking(self) -> list[PollRun]: ...

    def update_status(
        self, run_id: str, status: PollRunStatus, error_message: str | None = None
    ) -> None: ...

    def count_by_status(self) -> dict[str, int]: ...

    def record_launch_metadata(
        self,
        run_id: str,
        *,
        launch_method: str,
        pane_id: str | None = None,
        pid: int | None = None,
        pgid: int | None = None,
        launch_id: str | None = None,
    ) -> bool: ...

    def remove(self, run_id: str) -> None: ...
