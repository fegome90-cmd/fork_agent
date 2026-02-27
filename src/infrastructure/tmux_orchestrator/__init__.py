"""Tmux Orchestrator for AI coding agents.

Enables coordination of multiple agent sessions via tmux.
Supports multiple backends: opencode, pi.dev, etc.
"""

from __future__ import annotations

import logging
import subprocess
import warnings
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.domain.ports.agent_backend import AgentBackend

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
ORCHESTRATOR_DIR = PROJECT_ROOT / ".tmux-orchestrator"


@dataclass(frozen=True)
class TmuxWindow:
    session_name: str
    window_index: int
    window_name: str
    active: bool


@dataclass(frozen=True)
class TmuxSession:
    name: str
    windows: tuple[TmuxWindow, ...]
    attached: bool


class TmuxOrchestrator:
    """Orchestrates multiple OpenCode agent sessions via tmux."""

    __slots__ = ("_safety_mode", "_max_lines_capture")

    def __init__(self, safety_mode: bool = True) -> None:
        self._safety_mode = safety_mode
        self._max_lines_capture = 1000

    def get_sessions(self) -> list[TmuxSession]:
        try:
            result = subprocess.run(
                ["tmux", "list-sessions", "-F", "#{session_name}:#{session_attached}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
        except subprocess.TimeoutExpired:
            logger.warning("Timeout getting tmux sessions")
            return []
        if result.returncode != 0:
            return []

        sessions: list[TmuxSession] = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            session_name, attached = line.split(":")
            windows = self._get_windows(session_name)
            sessions.append(
                TmuxSession(
                    name=session_name,
                    windows=tuple(windows),
                    attached=attached == "1",
                )
            )
        return sessions

    def _get_windows(self, session_name: str) -> list[TmuxWindow]:
        try:
            result = subprocess.run(
                [
                    "tmux",
                    "list-windows",
                    "-t",
                    session_name,
                    "-F",
                    "#{window_index}:#{window_name}:#{window_active}",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout getting windows for session {session_name}")
            return []
        if result.returncode != 0:
            return []

        windows: list[TmuxWindow] = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split(":")
            if len(parts) >= 3:
                windows.append(
                    TmuxWindow(
                        session_name=session_name,
                        window_index=int(parts[0]),
                        window_name=parts[1],
                        active=parts[2] == "1",
                    )
                )
        return windows

    def capture_content(self, session: str, window: int, lines: int = 50) -> str:
        if lines > self._max_lines_capture:
            lines = self._max_lines_capture
        try:
            result = subprocess.run(
                ["tmux", "capture-pane", "-t", f"{session}:{window}", "-p", "-S", f"-{lines}"],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout capturing content from {session}:{window}")
            return ""
        return result.stdout if result.returncode == 0 else ""

    def send_message(self, session: str, window: int, message: str) -> bool:
        """Send a command to tmux window.

        DEPRECATED: Use send_command() for shell commands.
        This method will be removed in v2.0.
        """
        warnings.warn(
            "send_message() is deprecated. Use send_command() for commands.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._send_keys(session, window, message)

    def send_command(self, session: str, window: int, command: str) -> bool:
        """Send a shell command to tmux window (for actual commands only)."""
        return self._send_keys(session, window, command)

    def _send_keys(self, session: str, window: int, text: str) -> bool:
        """Internal: send text via tmux send-keys."""
        if self._safety_mode:
            print(f"SAFETY: Would send to {session}:{window}: {text[:50]}...")
            return True
        try:
            result = subprocess.run(
                ["tmux", "send-keys", "-t", f"{session}:{window}", text],
                capture_output=True,
                timeout=5,
            )
            if result.returncode != 0:
                return False
            subprocess.run(["tmux", "send-keys", "-t", f"{session}:{window}", "Enter"], timeout=5)
            return True
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout sending to {session}:{window}")
            return False

    def create_session(self, name: str, working_dir: Path | None = None) -> bool:
        cmd = ["tmux", "new-session", "-d", "-s", name]
        if working_dir:
            cmd.extend(["-c", str(working_dir)])
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=10)
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout creating session {name}")
            return False

    def create_window(self, session: str, name: str) -> int | None:
        try:
            result = subprocess.run(
                ["tmux", "new-window", "-t", session, "-n", name],
                capture_output=True,
                timeout=5,
            )
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout creating window {name} in {session}")
            return None
        if result.returncode != 0:
            return None
        windows = self._get_windows(session)
        return max(w.window_index for w in windows) if windows else None

    def kill_session(self, session: str) -> bool:
        try:
            result = subprocess.run(
                ["tmux", "kill-session", "-t", session],
                capture_output=True,
                timeout=5,
            )
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout killing session {session}")
            return False
        return result.returncode == 0

    def launch_agent(
        self,
        session: str,
        window: int,
        backend: AgentBackend,
        task: str,
        model: str | None = None,
    ) -> bool:
        """Launch an agent in a tmux window using the specified backend.

        Args:
            session: Tmux session name.
            window: Window index within the session.
            backend: Agent backend implementation (opencode, pi, etc.).
            task: Task/prompt for the agent.
            model: Optional model override. Uses backend default if not specified.

        Returns:
            True if command was sent successfully.
        """
        windows = self._get_windows(session)
        if not windows:
            logger.warning("No windows found in tmux session %s", session)
            return False

        target_window = window
        existing_indexes = {w.window_index for w in windows}
        if target_window not in existing_indexes:
            active_window = next((w.window_index for w in windows if w.active), None)
            target_window = active_window if active_window is not None else windows[0].window_index
            logger.info(
                "Requested window %s not found in session %s, using window %s",
                window,
                session,
                target_window,
            )

        actual_model = model or backend.get_default_model()
        cmd = backend.get_launch_command(task, actual_model)
        return self.send_command(session, target_window, cmd)

    def get_status(self) -> dict[str, Any]:
        sessions = self.get_sessions()
        return {
            "timestamp": datetime.now().isoformat(),
            "sessions": [
                {
                    "name": s.name,
                    "attached": s.attached,
                    "windows": [
                        {"index": w.window_index, "name": w.window_name, "active": w.active}
                        for w in s.windows
                    ],
                }
                for s in sessions
            ],
        }

    def find_windows(self, pattern: str) -> list[tuple[str, int]]:
        matches: list[tuple[str, int]] = []
        for session in self.get_sessions():
            for window in session.windows:
                if pattern.lower() in window.window_name.lower():
                    matches.append((session.name, window.window_index))
        return matches


def create_agent_session(
    name: str,
    backend: AgentBackend | None = None,
    task: str = "",
    model: str | None = None,
    working_dir: Path | None = None,
) -> tuple[str, int] | None:
    """Create a new agent session in tmux.

    Args:
        name: Session name.
        backend: Agent backend to use. Falls back to default if not specified.
        task: Optional task/prompt for the agent.
        model: Optional model override.
        working_dir: Working directory for the session.

    Returns:
        Tuple of (session_name, window_index) or None on failure.
    """
    from src.infrastructure.agent_backends import get_default_backend

    orchestrator = TmuxOrchestrator(safety_mode=False)
    if not orchestrator.create_session(name, working_dir or PROJECT_ROOT):
        return None

    if task:
        actual_backend = backend or get_default_backend()
        if actual_backend is None:
            logger.warning("No agent backend available")
            return (name, 0)
        orchestrator.launch_agent(name, 0, actual_backend, task, model)

    return (name, 0)


def send_task_to_agent(session: str, window: int, task: str) -> bool:
    orchestrator = TmuxOrchestrator(safety_mode=False)
    return orchestrator.send_command(session, window, task)


def get_agent_output(session: str, window: int, lines: int = 100) -> str:
    orchestrator = TmuxOrchestrator()
    return orchestrator.capture_content(session, window, lines)
