"""Agent polling service — orchestrates autonomous task execution."""

from __future__ import annotations

import contextlib
import logging
import os
import signal
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from src.application.exceptions import TaskTransitionError
from src.domain.entities.orchestration_task import OrchestrationTaskStatus
from src.domain.entities.poll_run import PollRun, PollRunStatus
from src.domain.ports.poll_run_repository import PollRunRepository

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from src.application.services.agent_launch_lifecycle_service import AgentLaunchLifecycleService
    from src.application.services.task_board_service import TaskBoardService
    from src.infrastructure.polling.poll_run_directory import PollRunDirectory

DEFAULT_CONCURRENCY: int = 4
DEFAULT_POLL_INTERVAL: int = 10
POLL_AGENT_OWNER: str = "poll-agent"
ALLOW_SUBPROCESS_FALLBACK_ENV: str = "POLL_ALLOW_SUBPROCESS_FALLBACK"


@dataclass(frozen=True)
class LaunchHandle:
    """Durable launch metadata required for later authoritative termination."""

    method: str
    pane_id: str | None = None
    pid: int | None = None
    pgid: int | None = None


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
        "_allow_subprocess_fallback",
        "_lifecycle_service",
    )

    def __init__(
        self,
        task_service: TaskBoardService,
        poll_run_repo: PollRunRepository,
        run_dir: PollRunDirectory,
        max_concurrent: int = DEFAULT_CONCURRENCY,
        poll_interval: int = DEFAULT_POLL_INTERVAL,
        allow_subprocess_fallback: bool | None = None,
        lifecycle_service: AgentLaunchLifecycleService | None = None,
    ) -> None:
        self._task_service = task_service
        self._poll_run_repo = poll_run_repo
        self._run_dir = run_dir
        self._max_concurrent = max_concurrent
        self._poll_interval = poll_interval
        self._allow_subprocess_fallback = (
            allow_subprocess_fallback
            if allow_subprocess_fallback is not None
            else os.environ.get(ALLOW_SUBPROCESS_FALLBACK_ENV, "").lower() in {"1", "true", "yes"}
        )
        self._lifecycle_service = lifecycle_service

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
        # Run lease reconciliation if lifecycle service is wired
        if self._lifecycle_service is not None:
            self._lifecycle_service.reconcile_expired_leases()

        launch_blocking_runs = self._poll_run_repo.list_launch_blocking()
        available = self._max_concurrent - len(launch_blocking_runs)
        if available <= 0:
            return []

        approved_tasks = self._task_service.list(status=OrchestrationTaskStatus.APPROVED)
        blocking_task_ids = {r.task_id for r in launch_blocking_runs}
        candidates = []
        for task in approved_tasks:
            if task.id in blocking_task_ids:
                logger.info(
                    "Suppressing polling launch for task %s: launch already in-flight or unresolved",
                    task.id,
                )
                continue
            # Check canonical lifecycle registry if available
            if self._lifecycle_service is not None:
                from src.domain.services.canonical_key import build_task_key

                canonical_key = build_task_key(task.id)
                active = self._lifecycle_service.get_active_launch(canonical_key)
                if active is not None:
                    logger.info(
                        "Lifecycle registry blocks launch for task %s: launch %s in status %s",
                        task.id,
                        active.launch_id,
                        active.status.value,
                    )
                    continue
            candidates.append(task)

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
                if run.status in (PollRunStatus.QUEUED, PollRunStatus.SPAWNING):
                    # Keep unresolved spawn attempts protected instead of immediate relaunch.
                    started_ms = run.started_at or 0
                    elapsed_s = (int(time.time() * 1000) - started_ms) / 1000
                    if elapsed_s > self.QUEUED_TIMEOUT_S:
                        self._poll_run_repo.update_status(
                            run.id,
                            PollRunStatus.QUARANTINED,
                            f"Spawn unresolved timeout after {elapsed_s:.0f}s",
                        )
                        self._run_dir.append_event(
                            run.id,
                            {
                                "type": "launch_quarantined",
                                "timestamp": int(time.time() * 1000),
                                "reason": "queued_timeout",
                            },
                        )
                    else:
                        logger.info(
                            "Run %s still unresolved (%s); keeping launch protected",
                            run.id,
                            run.status.value,
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
                if run.status in (PollRunStatus.QUEUED, PollRunStatus.SPAWNING):
                    started_ms = run.started_at or 0
                    elapsed_s = (int(time.time() * 1000) - started_ms) / 1000
                    if elapsed_s > self.QUEUED_TIMEOUT_S:
                        self._poll_run_repo.update_status(
                            run.id,
                            PollRunStatus.QUARANTINED,
                            f"Spawn unresolved timeout after {elapsed_s:.0f}s",
                        )
                        self._run_dir.append_event(
                            run.id,
                            {
                                "type": "launch_quarantined",
                                "timestamp": int(time.time() * 1000),
                                "reason": "status_timeout",
                            },
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
        self._terminate_spawned_agent(run_id)
        # Reset task to APPROVED so it can be re-picked
        if run.task_id:
            with contextlib.suppress(ValueError, TaskTransitionError):
                self._task_service.retry(run.task_id)
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
        from src.domain.services.canonical_key import build_task_key

        now_ms = int(time.time() * 1000)
        run_id = uuid.uuid4().hex
        lifecycle_launch_id: str | None = None

        # Claim canonical launch slot via lifecycle service (if wired)
        if self._lifecycle_service is not None:
            _task_key = build_task_key(task_id)
            attempt = self._lifecycle_service.request_launch(
                canonical_key=_task_key,
                surface="polling",
                owner_type="task",
                owner_id=task_id,
            )
            if attempt.decision != "claimed":
                logger.info(
                    "Lifecycle service denied launch for task %s: %s",
                    task_id,
                    attempt.reason or attempt.decision,
                )
                run = PollRun(
                    id=run_id,
                    task_id=task_id,
                    agent_name=POLL_AGENT_OWNER,
                    status=PollRunStatus.CANCELLED,
                    error_message=f"Launch suppressed by lifecycle service: {attempt.reason or attempt.decision}",
                )
                self._poll_run_repo.save(run)
                return run
            if attempt.launch is not None:
                lifecycle_launch_id = attempt.launch.launch_id

        # Create directory
        run_dir = self._run_dir.create_run_dir(run_id)

        _canonical_key = build_task_key(task_id)

        # Create entity
        run = PollRun(
            id=run_id,
            task_id=task_id,
            agent_name=POLL_AGENT_OWNER,
            status=PollRunStatus.QUEUED,
            poll_run_dir=str(run_dir),
            canonical_key=_canonical_key,
            launch_id=lifecycle_launch_id,
        )
        self._poll_run_repo.save(run)

        # Start the task on the Task Board
        try:
            self._task_service.start(task_id, owner=POLL_AGENT_OWNER)
        except TaskTransitionError as exc:
            error_msg = str(exc)
            self._poll_run_repo.update_status(run_id, PollRunStatus.FAILED, error_msg)
            if lifecycle_launch_id is not None and self._lifecycle_service is not None:
                self._lifecycle_service.mark_failed(lifecycle_launch_id, error_msg)
            result = self._poll_run_repo.get_by_id(run_id)
            if result is None:
                raise ValueError(f"Poll run '{run_id}' disappeared") from None
            return result

        self._poll_run_repo.update_status(run_id, PollRunStatus.SPAWNING)

        # Notify lifecycle service that spawn is starting
        if lifecycle_launch_id is not None and self._lifecycle_service is not None:
            self._lifecycle_service.confirm_spawning(lifecycle_launch_id)

        # Actually spawn the agent and capture authoritative termination handles
        current = self._poll_run_repo.get_by_id(run_id)
        handle: LaunchHandle | None = None
        if current is not None:
            handle = self._spawn_agent(run=current, task_subject=task_subject, run_dir=str(run_dir))

        if handle is None:
            self._poll_run_repo.update_status(
                run_id,
                PollRunStatus.QUARANTINED,
                "Spawn unresolved: launch confirmation missing; blocking relaunch",
            )
            if lifecycle_launch_id is not None and self._lifecycle_service is not None:
                self._lifecycle_service.quarantine(lifecycle_launch_id, "spawn unresolved")
            self._run_dir.append_event(
                run_id,
                {
                    "type": "launch_quarantined",
                    "task_id": task_id,
                    "timestamp": int(time.time() * 1000),
                    "reason": "spawn_unresolved",
                },
            )
            logger.warning(
                "Run %s quarantined for task %s due to ambiguous spawn outcome",
                run_id,
                task_id,
            )
            result = self._poll_run_repo.get_by_id(run_id)
            if result is None:
                raise ValueError(f"Poll run '{run_id}' disappeared") from None
            return result

        metadata_saved = self._poll_run_repo.record_launch_metadata(
            run_id,
            launch_method=handle.method,
            pane_id=handle.pane_id,
            pid=handle.pid,
            pgid=handle.pgid,
            launch_id=lifecycle_launch_id,
        )
        if not metadata_saved:
            self._terminate_launch_handle(handle, run_id)
            self._poll_run_repo.update_status(
                run_id,
                PollRunStatus.QUARANTINED,
                "Spawn unresolved: failed to persist launch metadata",
            )
            if lifecycle_launch_id is not None and self._lifecycle_service is not None:
                self._lifecycle_service.quarantine(lifecycle_launch_id, "metadata persist failed")
            self._run_dir.append_event(
                run_id,
                {
                    "type": "launch_quarantined",
                    "task_id": task_id,
                    "timestamp": int(time.time() * 1000),
                    "reason": "metadata_persist_failed",
                },
            )
            result = self._poll_run_repo.get_by_id(run_id)
            if result is None:
                raise ValueError(f"Poll run '{run_id}' disappeared") from None
            return result

        spawned_event: dict[str, object] = {"type": "agent_spawned", "method": handle.method}
        if handle.pane_id:
            spawned_event["pane_id"] = handle.pane_id
        if handle.pid is not None:
            spawned_event["pid"] = handle.pid
        if handle.pgid is not None:
            spawned_event["pgid"] = handle.pgid
        self._run_dir.append_event(run_id, spawned_event)

        # Confirm active in lifecycle registry with termination metadata
        if lifecycle_launch_id is not None and self._lifecycle_service is not None:
            self._lifecycle_service.confirm_active(
                lifecycle_launch_id,
                backend=handle.method,
                termination_handle_type="tmux-pane" if handle.method == "tmux" else "pgid",
                termination_handle_value=handle.pane_id or str(handle.pgid or handle.pid or ""),
                tmux_pane_id=handle.pane_id,
                process_pid=handle.pid,
                process_pgid=handle.pgid,
            )

        # Launch is considered safe only after metadata is persisted.
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

        # Append start event
        self._run_dir.append_event(
            run_id,
            {
                "type": "started",
                "task_id": task_id,
                "timestamp": now_ms,
                "launch_method": handle.method,
            },
        )

        result = self._poll_run_repo.get_by_id(run_id)
        if result is None:
            raise ValueError(f"Poll run '{run_id}' disappeared after spawn")
        return result

    def _spawn_agent(self, run: PollRun, task_subject: str, run_dir: str) -> LaunchHandle | None:
        """Spawn a pi agent subprocess for this poll run.

        Uses tmux split-window if in a tmux session, otherwise falls back
        to a background subprocess (only if POLL_ALLOW_SUBPROCESS_FALLBACK is set).
        """
        run_path = Path(run_dir)
        if not run_path.exists():
            logger.warning("Run directory %s does not exist, skipping agent spawn", run_dir)
            return None

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
                    logger.info("Spawned agent in tmux pane %s for run %s", pane_id, run.id)
                    return LaunchHandle(method="tmux", pane_id=pane_id)
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
                logger.warning("tmux spawn failed for run %s", run.id)

        if not self._allow_subprocess_fallback:
            logger.warning(
                "Subprocess fallback disabled; keeping run %s protected after unresolved spawn",
                run.id,
            )
            return None

        # Fallback: background subprocess
        log_path = Path(run_dir) / "agent.log"
        try:
            with log_path.open("w") as log_file:
                proc = subprocess.Popen(
                    ["pi", "--mode", "json", "-p", f"@{prompt_file}"],
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
        except OSError:
            logger.warning("Subprocess fallback spawn failed for run %s", run.id)
            return None

        try:
            pgid = os.getpgid(proc.pid)
        except ProcessLookupError:
            logger.warning("Unable to resolve process group for spawned PID %d", proc.pid)
            with contextlib.suppress(ProcessLookupError):
                proc.kill()  # Clean up the orphan
            return None

        logger.info("Spawned agent subprocess PID %d (PGID %d) for run %s", proc.pid, pgid, run.id)
        return LaunchHandle(method="subprocess", pid=proc.pid, pgid=pgid)

    def _complete_run(self, run_id: str, task_id: str) -> None:
        """Mark a run as completed and complete the task."""
        self._terminate_spawned_agent(run_id)
        with contextlib.suppress(ValueError, TaskTransitionError):
            self._task_service.complete(task_id)
        self._poll_run_repo.update_status(run_id, PollRunStatus.COMPLETED)
        run = self._poll_run_repo.get_by_id(run_id)
        if run is not None:
            self._finalize_launch(run)
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
        self._terminate_spawned_agent(run_id)
        self._poll_run_repo.update_status(run_id, PollRunStatus.FAILED, error_message=error)
        self._finalize_launch(run, failed=True, error=error) if run is not None else None
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
            with contextlib.suppress(ValueError, TaskTransitionError):
                self._task_service.retry(run.task_id)

    def _finalize_launch(
        self, run: PollRun, *, failed: bool = False, error: str | None = None
    ) -> None:
        """Best-effort finalization of the AgentLaunch for a completed/failed run.

        Resolves the authoritative launch via ``run.launch_id`` first (if present),
        falling back to ``canonical_key`` lookup for legacy runs without the FK.
        """
        if self._lifecycle_service is None:
            return
        try:
            # Prefer the direct FK link (RC-4+)
            launch = None
            if run.launch_id is not None:
                launch = self._lifecycle_service.get_launch(run.launch_id)
            # Legacy fallback: resolve by canonical_key
            if launch is None and run.canonical_key is not None:
                launch = self._lifecycle_service.get_active_launch(run.canonical_key)
            if launch is None:
                return
            if failed:
                self._lifecycle_service.mark_failed(launch.launch_id, error=error or "run failed")
            else:
                self._lifecycle_service.begin_termination(launch.launch_id)
                self._lifecycle_service.confirm_terminated(launch.launch_id)
        except Exception:
            logger.warning("Failed to finalize launch for run %s", run.id, exc_info=True)

    def _terminate_spawned_agent(self, run_id: str) -> None:
        """Best-effort cleanup for tmux panes and detached subprocesses."""
        run = self._poll_run_repo.get_by_id(run_id)
        if run is not None:
            if run.status in (
                PollRunStatus.RUNNING,
                PollRunStatus.SPAWNING,
            ):
                self._poll_run_repo.update_status(run_id, PollRunStatus.TERMINATING)
            elif run.status in (PollRunStatus.QUEUED, PollRunStatus.QUARANTINED):
                self._poll_run_repo.update_status(run_id, PollRunStatus.CANCELLED)

            handle_from_repo = self._launch_handle_from_run(run)
            if handle_from_repo is not None:
                self._terminate_launch_handle(handle_from_repo, run_id)
                return

        # Backward-compatible fallback for legacy runs with event-only metadata.
        for event in reversed(self._run_dir.read_events(run_id)):
            if event.get("type") != "agent_spawned":
                continue

            pane_id = event.get("pane_id")
            if isinstance(pane_id, str) and pane_id:
                self._terminate_launch_handle(LaunchHandle(method="tmux", pane_id=pane_id), run_id)
                return

            pid = event.get("pid")
            if isinstance(pid, int):
                pgid = event.get("pgid")
                pgid_val = pgid if isinstance(pgid, int) else None
                self._terminate_launch_handle(
                    LaunchHandle(method="subprocess", pid=pid, pgid=pgid_val),
                    run_id,
                )
            elif isinstance(pid, str) and pid.isdigit():
                pgid = event.get("pgid")
                pgid_val = int(pgid) if isinstance(pgid, str) and pgid.isdigit() else None
                self._terminate_launch_handle(
                    LaunchHandle(method="subprocess", pid=int(pid), pgid=pgid_val),
                    run_id,
                )
            return

    @staticmethod
    def _launch_handle_from_run(run: PollRun) -> LaunchHandle | None:
        """Build a launch handle from persisted poll_run metadata."""
        if run.launch_method == "tmux" and run.launch_pane_id:
            return LaunchHandle(method="tmux", pane_id=run.launch_pane_id)
        if run.launch_method == "subprocess" and run.launch_pid is not None:
            return LaunchHandle(
                method="subprocess",
                pid=run.launch_pid,
                pgid=run.launch_pgid,
            )
        return None

    def _terminate_launch_handle(self, handle: LaunchHandle, run_id: str) -> None:
        """Terminate a launch by its authoritative metadata."""
        if handle.method == "tmux" and handle.pane_id:
            try:
                subprocess.run(
                    ["tmux", "kill-pane", "-t", handle.pane_id],
                    capture_output=True,
                    timeout=5,
                )
            except (subprocess.TimeoutExpired, FileNotFoundError):
                logger.debug("Failed to kill tmux pane %s for run %s", handle.pane_id, run_id)
            return

        if handle.method == "subprocess":
            if handle.pgid is not None:
                self._terminate_process_group(handle.pgid)
                return
            if handle.pid is not None:
                self._terminate_pid(handle.pid)
                return

    def _terminate_pid(self, pid: int) -> None:
        """Terminate a detached subprocess without raising if it already exited."""
        with contextlib.suppress(ProcessLookupError):
            os.kill(pid, signal.SIGTERM)

        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            if not self._pid_exists(pid):
                return
            time.sleep(0.05)

        with contextlib.suppress(ProcessLookupError):
            os.kill(pid, signal.SIGKILL)

    def _terminate_process_group(self, pgid: int) -> None:
        """Terminate a detached subprocess process group."""
        with contextlib.suppress(ProcessLookupError):
            os.killpg(pgid, signal.SIGTERM)

        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            if not self._pid_exists(-pgid):
                return
            time.sleep(0.05)

        with contextlib.suppress(ProcessLookupError):
            os.killpg(pgid, signal.SIGKILL)

    @staticmethod
    def _pid_exists(pid: int) -> bool:
        """Return True when the process still exists."""
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True
