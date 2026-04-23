"""Agent polling service — orchestrates autonomous task execution."""

from __future__ import annotations

import logging
import os
import subprocess
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from src.application.exceptions import TaskTransitionError
from src.domain.entities.orchestration_task import OrchestrationTaskStatus
from src.domain.entities.poll_run import PollRun, PollRunStatus
from src.domain.ports.poll_run_repository import PollRunRepository

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from src.application.services.task_board_service import TaskBoardService
    from src.infrastructure.polling.poll_run_directory import PollRunDirectory

DEFAULT_CONCURRENCY: int = 4
DEFAULT_POLL_INTERVAL: int = 10
POLL_AGENT_OWNER: str = "poll-agent"


class AgentPollingService:
    """Application service coordinating autonomous agent polling.

    Polls the Task Board for APPROVED tasks, spawns poll runs,
    and tracks execution status via filesystem artifacts.
    """

    QUEUED_TIMEOUT_S: int = 300

    __slots__ = (
        "_task_service",
        "_poll_run_repo",
        "_run_dir",
        "_max_concurrent",
        "_poll_interval",
    )

    def __init__(
        self,
        task_service: TaskBoardService,
        poll_run_repo: PollRunRepository,
        run_dir: PollRunDirectory,
        max_concurrent: int = DEFAULT_CONCURRENCY,
        poll_interval: int = DEFAULT_POLL_INTERVAL,
    ) -> None:
        self._task_service = task_service
        self._poll_run_repo = poll_run_repo
        self._run_dir = run_dir
        self._max_concurrent = max_concurrent
        self._poll_interval = poll_interval

    @property
    def max_concurrent(self) -> int:
        return self._max_concurrent

    @max_concurrent.setter
    def max_concurrent(self, value: int) -> None:
        if value < 1:
            raise ValueError("max_concurrent must be >= 1")
        self._max_concurrent = value

    @property
    def poll_interval(self) -> int:
        return self._poll_interval

    @poll_interval.setter
    def poll_interval(self, value: int) -> None:
        if value < 0.1:
            raise ValueError("poll_interval must be >= 0.1 seconds")
        self._poll_interval = value

    def poll_once(self) -> list[PollRun]:
        """Execute a single poll cycle.

        1. Check active runs and available slots.
        2. Fetch APPROVED tasks from the Task Board.
        3. Skip tasks already assigned to active runs.
        4. Spawn new poll runs up to the concurrency cap.
        """
        active = self._poll_run_repo.list_active()
        available = self._max_concurrent - len(active)
        if available <= 0:
            return []

        approved_tasks = self._task_service.list(status=OrchestrationTaskStatus.APPROVED)
        # Skip tasks already being handled by an active run
        active_task_ids = {r.task_id for r in active}
        candidates = [t for t in approved_tasks if t.id not in active_task_ids]

        new_runs: list[PollRun] = []
        for task in candidates[:available]:
            run = self._spawn_run(task.id, task.subject)
            new_runs.append(run)

        return new_runs

    def check_runs(self) -> list[PollRun]:
        """Check all active runs and update their status.

        Reads status.json from each run directory to detect
        completion, failure, or missing status (agent crash).
        """
        active = self._poll_run_repo.list_active()
        updated: list[PollRun] = []

        for run in active:
            status_data = self._run_dir.read_status(run.id)

            if status_data is None:
                if run.status == PollRunStatus.QUEUED:
                    # Check if QUEUED for too long (stuck in spawn)
                    started_ms = run.started_at or 0
                    elapsed_s = (int(time.time() * 1000) - started_ms) / 1000
                    if elapsed_s > self.QUEUED_TIMEOUT_S:
                        self._fail_run(
                            run.id,
                            f"QUEUED timeout after {elapsed_s:.0f}s",
                        )
                    else:
                        self._fail_run(
                            run.id,
                            "Spawn incomplete: run never reached RUNNING state",
                        )
                else:
                    # RUNNING with no status file — agent crashed
                    self._fail_run(run.id, "Agent crashed: no status file written")
                updated.append(self._poll_run_repo.get_by_id(run.id))  # type: ignore[arg-type]
                continue

            run_status = status_data.get("status", "")

            if run_status == "COMPLETED":
                self._complete_run(run.id, run.task_id)
            elif run_status == "FAILED":
                error = str(status_data.get("error", "Unknown error"))
                self._fail_run(run.id, error)
            else:
                # Still running — check QUEUED timeout for safety
                if run.status == PollRunStatus.QUEUED:
                    started_ms = run.started_at or 0
                    elapsed_s = (int(time.time() * 1000) - started_ms) / 1000
                    if elapsed_s > self.QUEUED_TIMEOUT_S:
                        self._fail_run(
                            run.id,
                            f"QUEUED timeout after {elapsed_s:.0f}s",
                        )
                        updated.append(
                            self._poll_run_repo.get_by_id(run.id)  # type: ignore[arg-type]
                        )
                        continue

            current = self._poll_run_repo.get_by_id(run.id)
            if current is not None:
                updated.append(current)

        return updated

    def cancel_run(self, run_id: str) -> PollRun:
        """Cancel an active poll run."""
        run = self._poll_run_repo.get_by_id(run_id)
        if run is None:
            raise ValueError(f"Poll run '{run_id}' not found")
        if not run.can_transition_to(PollRunStatus.CANCELLED):
            raise ValueError(f"Cannot cancel run '{run_id}' in status {run.status.value}")
        self._poll_run_repo.update_status(run_id, PollRunStatus.CANCELLED)
        self._run_dir.append_event(
            run_id,
            {
                "type": "cancelled",
                "timestamp": int(time.time() * 1000),
            },
        )
        # Kill the tmux session if running
        session_name = f"poll-{run_id[:8]}"
        try:
            subprocess.run(
                ["tmux", "kill-session", "-t", session_name],
                capture_output=True,
                timeout=5,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        # Reset task to APPROVED so it can be re-picked
        if run.task_id:
            try:
                self._task_service.retry(run.task_id)
            except (ValueError, TaskTransitionError):
                pass
        result = self._poll_run_repo.get_by_id(run_id)
        if result is None:
            raise ValueError(f"Poll run '{run_id}' disappeared after update")
        return result

    def get_active_runs(self) -> list[PollRun]:
        """Return all active (QUEUED or RUNNING) runs."""
        return self._poll_run_repo.list_active()

    def get_run_status(self, run_id: str) -> dict[str, object] | None:
        """Read status.json from filesystem for a specific run."""
        result = self._run_dir.read_status(run_id)
        return dict(result) if result is not None else None

    def get_status_summary(self) -> dict[str, int]:
        """Return counts by status — single GROUP BY query."""
        return self._poll_run_repo.count_by_status()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _spawn_run(self, task_id: str, task_subject: str) -> PollRun:
        """Create, persist, and start a new poll run for a task."""
        now_ms = int(time.time() * 1000)
        run_id = uuid.uuid4().hex

        # Create directory
        run_dir = self._run_dir.create_run_dir(run_id)

        # Create entity
        run = PollRun(
            id=run_id,
            task_id=task_id,
            agent_name=POLL_AGENT_OWNER,
            status=PollRunStatus.QUEUED,
            poll_run_dir=str(run_dir),
        )
        self._poll_run_repo.save(run)

        # Start the task on the Task Board
        try:
            self._task_service.start(task_id, owner=POLL_AGENT_OWNER)
        except TaskTransitionError:
            # Task was concurrently claimed by another poll cycle
            self._poll_run_repo.update_status(run_id, PollRunStatus.FAILED, "Task already started")
            result = self._poll_run_repo.get_by_id(run_id)
            if result is None:
                raise ValueError(f"Poll run '{run_id}' disappeared") from None
            return result

        # Transition to RUNNING
        current = self._poll_run_repo.get_by_id(run_id)
        if current is None or not current.can_transition_to(PollRunStatus.RUNNING):
            self._poll_run_repo.update_status(
                run_id, PollRunStatus.FAILED, "Invalid transition to RUNNING"
            )
            result = self._poll_run_repo.get_by_id(run_id)
            if result is None:
                raise ValueError(f"Poll run '{run_id}' disappeared") from None
            return result
        self._poll_run_repo.update_status(run_id, PollRunStatus.RUNNING)

        # Write status.json
        self._run_dir.write_status(
            run_id,
            {
                "run_id": run_id,
                "task_id": task_id,
                "task_subject": task_subject,
                "agent_name": POLL_AGENT_OWNER,
                "status": "RUNNING",
                "started_at": now_ms,
            },
        )

        # Actually spawn the agent
        current = self._poll_run_repo.get_by_id(run_id)
        if current is not None:
            self._spawn_agent(run=current, task_subject=task_subject, run_dir=str(run_dir))

        # Append start event
        self._run_dir.append_event(
            run_id,
            {
                "type": "started",
                "task_id": task_id,
                "timestamp": now_ms,
            },
        )

        result = self._poll_run_repo.get_by_id(run_id)
        if result is None:
            raise ValueError(f"Poll run '{run_id}' disappeared after spawn")
        return result

    def _spawn_agent(self, run: PollRun, task_subject: str, run_dir: str) -> None:
        """Spawn a pi agent subprocess for this poll run.

        Uses tmux split-window if in a tmux session, otherwise falls back
        to a background subprocess.
        """
        run_path = Path(run_dir)
        if not run_path.exists():
            logger.warning("Run directory %s does not exist, skipping agent spawn", run_dir)
            return

        prompt_file = run_path / "agent_prompt.txt"
        prompt_file.parent.mkdir(parents=True, exist_ok=True)
        prompt_file.write_text(
            f"You are an autonomous agent executing task: {task_subject}\n"
            f"Run ID: {run.id}\n"
            f"Write your results to {run_dir}/status.json when done.\n"
            f"Set status to COMPLETED or FAILED.\n"
        )

        # Try tmux split-window first (if in tmux)
        if os.environ.get("TMUX"):
            cmd = [
                "tmux",
                "split-window",
                "-P",
                "-F",
                "#{pane_id}",
                "--",
                f"pi --mode json -p @{prompt_file} 2>&1 | tee {run_dir}/agent_output.jsonl; echo $?",
            ]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                pane_id = result.stdout.strip()
                if pane_id:
                    self._run_dir.append_event(
                        run.id,
                        {"type": "agent_spawned", "pane_id": pane_id, "method": "tmux"},
                    )
                    logger.info("Spawned agent in tmux pane %s for run %s", pane_id, run.id)
                    return
            except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                logger.warning("tmux spawn failed, falling back to subprocess")

        # Fallback: background subprocess
        log_path = Path(run_dir) / "agent.log"
        with log_path.open("w") as log_file:
            proc = subprocess.Popen(
                ["pi", "--mode", "json", "-p", f"@{prompt_file}"],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        self._run_dir.append_event(
            run.id,
            {"type": "agent_spawned", "pid": proc.pid, "method": "subprocess"},
        )
        logger.info("Spawned agent subprocess PID %d for run %s", proc.pid, run.id)

    def _complete_run(self, run_id: str, task_id: str) -> None:
        """Mark a run as completed and complete the task."""
        try:
            self._task_service.complete(task_id)
        except (ValueError, TaskTransitionError):
            pass  # Task might already be completed — acceptable for polling
        self._poll_run_repo.update_status(run_id, PollRunStatus.COMPLETED)
        self._run_dir.append_event(
            run_id,
            {
                "type": "completed",
                "task_id": task_id,
                "timestamp": int(time.time() * 1000),
            },
        )

    def _fail_run(self, run_id: str, error: str) -> None:
        """Mark a run as failed and reset the task for re-processing."""
        run = self._poll_run_repo.get_by_id(run_id)
        self._poll_run_repo.update_status(run_id, PollRunStatus.FAILED, error_message=error)
        self._run_dir.append_event(
            run_id,
            {
                "type": "failed",
                "error": error,
                "timestamp": int(time.time() * 1000),
            },
        )
        # Reset task to APPROVED so it can be re-picked
        if run is not None and run.task_id:
            try:
                self._task_service.retry(run.task_id)
            except (ValueError, TaskTransitionError):
                pass  # Task might be deleted or already reset
