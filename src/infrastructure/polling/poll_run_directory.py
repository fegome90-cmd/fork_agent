"""Filesystem manager for poll run directories.

Each autonomous run gets a directory under the platform-specific
data directory containing status.json, events.jsonl, and output.log.
"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import TypedDict


class RunStatus(TypedDict, total=False):
    """Structure of status.json files."""

    status: str
    task_id: str
    started_at: int
    error: str | None


class PollRunDirectory:
    """Manages per-run filesystem artifacts for autonomous agent polling."""

    def __init__(self, base_dir: Path | None = None) -> None:
        if base_dir is None:
            xdg = os.environ.get("XDG_DATA_HOME")
            root = Path(xdg) if xdg else Path.home() / ".local" / "share"
            self._base_dir = root / "fork" / "poll-runs"
        else:
            self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

    @property
    def base_dir(self) -> Path:
        """The base directory for all poll runs."""
        return self._base_dir

    def create_run_dir(self, run_id: str) -> Path:
        """Create a directory for a specific run. Returns the path."""
        run_dir = self._base_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        return run_dir

    def write_status(self, run_id: str, data: dict[str, object]) -> None:
        """Atomically write status.json for a run."""
        run_dir = self._base_dir / run_id
        status_path = run_dir / "status.json"
        # Atomic write: temp file then rename
        fd, tmp = tempfile.mkstemp(dir=run_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2, default=str)
            os.replace(tmp, status_path)
        except BaseException:
            # Clean up temp file on any error
            with contextlib.suppress(OSError):
                os.unlink(tmp)
            raise

    def read_status(self, run_id: str) -> RunStatus | None:
        """Read status.json for a run. Returns None if not found."""
        status_path = self._base_dir / run_id / "status.json"
        if not status_path.exists():
            return None
        try:
            return json.loads(status_path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]
        except (json.JSONDecodeError, ValueError):
            return None

    def append_event(self, run_id: str, event: dict[str, object]) -> None:
        """Append a JSONL event line to events.jsonl."""
        events_path = self._base_dir / run_id / "events.jsonl"
        line = json.dumps(event, default=str) + "\n"
        with events_path.open("a", encoding="utf-8") as f:
            f.write(line)

    def read_events(self, run_id: str) -> list[dict[str, object]]:
        """Read events.jsonl for a run.

        Returns an empty list when the file does not exist or contains
        malformed JSON lines.
        """
        events_path = self._base_dir / run_id / "events.jsonl"
        if not events_path.exists():
            return []

        events: list[dict[str, object]] = []
        for line in events_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                data = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if isinstance(data, dict):
                events.append(data)
        return events

    def write_output(self, run_id: str, content: str) -> None:
        """Append content to output.log."""
        output_path = self._base_dir / run_id / "output.log"
        with output_path.open("a", encoding="utf-8", errors="replace") as f:
            f.write(content)
            if not content.endswith("\n"):
                f.write("\n")

    def cleanup_run(self, run_id: str) -> None:
        """Remove a run directory entirely."""
        run_dir = self._base_dir / run_id
        if run_dir.exists():
            shutil.rmtree(run_dir, ignore_errors=True)

    def list_active_runs(self) -> list[Path]:
        """Scan for runs with RUNNING status in their status.json."""
        active: list[Path] = []
        if not self._base_dir.exists():
            return active
        for entry in self._base_dir.iterdir():
            if not entry.is_dir():
                continue
            status_path = entry / "status.json"
            if not status_path.exists():
                continue
            try:
                data = json.loads(status_path.read_text(encoding="utf-8"))
                if data.get("status") == "RUNNING":
                    active.append(entry)
            except (json.JSONDecodeError, ValueError):
                continue
        return active
