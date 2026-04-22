"""Tmux multiplexer adapter.

Concrete implementation of MultiplexerAdapter for tmux.
Uses subprocess.run for all tmux interactions (synchronous).
"""

from __future__ import annotations

import logging
import os
import shlex
import subprocess

from src.domain.ports.multiplexer_adapter import MultiplexerAdapter, PaneInfo, SpawnOptions
from src.infrastructure.tmux_orchestrator import _sanitize_tmux_text

logger = logging.getLogger(__name__)

_TMUX_TIMEOUT = 10


class TmuxAdapter(MultiplexerAdapter):
    """Adapter for tmux terminal multiplexer."""

    name = "tmux"

    def detect(self) -> bool:
        """Detect tmux by checking the TMUX environment variable."""
        return "TMUX" in os.environ

    def spawn(self, options: SpawnOptions) -> PaneInfo:
        """Spawn a new tmux pane running the given command.

        Uses tmux split-window with format output to capture the pane ID.
        """
        cmd: list[str] = ["tmux", "split-window", "-P", "-F", "#{pane_id}"]

        if options.workdir:
            cmd.extend(["-c", options.workdir])

        # Build the actual command with env vars prepended
        actual_command = options.command
        if options.command:
            actual_command = _sanitize_tmux_text(options.command)
        if options.env:
            exports = " && ".join(
                f"export {shlex.quote(k)}={shlex.quote(v)}" for k, v in options.env.items()
            )
            actual_command = f"{exports} && {actual_command}"

        # Command comes last after --
        cmd.extend(["--", actual_command])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=_TMUX_TIMEOUT,
            )
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"Timeout spawning tmux pane: {options.name}") from e

        if result.returncode != 0:
            raise RuntimeError(f"Failed to spawn tmux pane: {result.stderr.strip()}")

        pane_id = result.stdout.strip()
        if not pane_id:
            raise RuntimeError("tmux split-window returned empty pane ID")

        # Set pane title if name provided (split-window has no -n flag)
        if options.name:
            self.set_title(pane_id, options.name)

        info = PaneInfo(pane_id=pane_id, is_alive=True, title=options.name or "")
        return info

    def kill(self, pane_id: str) -> None:
        """Kill a tmux pane by its ID."""
        try:
            result = subprocess.run(
                ["tmux", "kill-pane", "-t", pane_id],
                capture_output=True,
                text=True,
                timeout=_TMUX_TIMEOUT,
            )
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"Timeout killing tmux pane {pane_id}") from e

        if result.returncode != 0:
            raise RuntimeError(f"Failed to kill tmux pane {pane_id}: {result.stderr.strip()}")

    def is_alive(self, pane_id: str) -> bool:
        """Check if a tmux pane is alive via display-message."""
        try:
            result = subprocess.run(
                ["tmux", "display-message", "-t", pane_id, "-p", "#{pane_id}"],
                capture_output=True,
                text=True,
                timeout=_TMUX_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            logger.warning("Timeout checking liveness of pane %s", pane_id)
            return False

        return result.returncode == 0

    def set_title(self, pane_id: str, title: str) -> None:
        """Set the title of a tmux pane."""
        try:
            result = subprocess.run(
                ["tmux", "select-pane", "-t", pane_id, "-T", title],
                capture_output=True,
                text=True,
                timeout=_TMUX_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            logger.warning("Timeout setting title on pane %s", pane_id)
            return

        if result.returncode != 0:
            logger.warning("Failed to set title on pane %s: %s", pane_id, result.stderr.strip())

    def configure_pane(self, pane_id: str, remain_on_exit: bool = True) -> None:
        """Configure tmux pane remain-on-exit option."""
        value = "on" if remain_on_exit else "off"
        try:
            result = subprocess.run(
                ["tmux", "set-option", "-t", pane_id, "remain-on-exit", value],
                capture_output=True,
                text=True,
                timeout=_TMUX_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            logger.warning("Timeout configuring pane %s", pane_id)
            return

        if result.returncode != 0:
            logger.warning("Failed to configure pane %s: %s", pane_id, result.stderr.strip())
