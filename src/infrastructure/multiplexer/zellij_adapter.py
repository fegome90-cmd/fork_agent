"""Zellij multiplexer adapter.

Concrete implementation of MultiplexerAdapter for zellij.
Uses subprocess.run for all zellij interactions (synchronous).
"""

from __future__ import annotations

import logging
import os
import shlex
import subprocess

from src.domain.ports.multiplexer_adapter import MultiplexerAdapter, PaneInfo, SpawnOptions

logger = logging.getLogger(__name__)

_ZELLIJ_TIMEOUT = 10


class ZellijAdapter(MultiplexerAdapter):
    """Adapter for zellij terminal multiplexer."""

    name = "zellij"

    def detect(self) -> bool:
        """Detect zellij by checking the ZELLIJ environment variable."""
        return "ZELLIJ" in os.environ

    def spawn(self, options: SpawnOptions) -> PaneInfo:
        """Spawn a new zellij pane running the given command.

        Uses zellij run with direction right. Derives pane ID from
        the current session context.
        """
        cmd: list[str] = ["zellij", "run"]

        if options.workdir:
            cmd.extend(["-c", options.workdir])

        cmd.extend(["--direction", "right"])

        if options.name:
            cmd.extend(["--name", options.name])

        # Build actual command with env vars prepended
        actual_command = options.command
        if options.env:
            exports = " ".join(f"{shlex.quote(k)}={shlex.quote(v)}" for k, v in options.env.items())
            actual_command = f"export {exports} && {actual_command}"

        cmd.extend(["--", actual_command])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=_ZELLIJ_TIMEOUT,
            )
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"Timeout spawning zellij pane: {options.name}") from e

        if result.returncode != 0:
            raise RuntimeError(f"Failed to spawn zellij pane: {result.stderr.strip()}")

        # Derive pane ID from zellij list-panes output
        pane_id = self._get_latest_pane_id()
        if not pane_id:
            # Fallback: use the name as identifier
            pane_id = options.name or "zellij-unknown"

        return PaneInfo(pane_id=pane_id, is_alive=True, title=options.name or "")

    def kill(self, pane_id: str) -> None:
        """Kill a zellij pane by its ID."""
        try:
            result = subprocess.run(
                ["zellij", "action", "kill-pane", "--pane-id", pane_id],
                capture_output=True,
                text=True,
                timeout=_ZELLIJ_TIMEOUT,
            )
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"Timeout killing zellij pane {pane_id}") from e

        if result.returncode != 0:
            raise RuntimeError(f"Failed to kill zellij pane {pane_id}: {result.stderr.strip()}")

    def is_alive(self, pane_id: str) -> bool:
        """Check if a zellij pane is alive via list-panes output."""
        try:
            result = subprocess.run(
                ["zellij", "list-panes"],
                capture_output=True,
                text=True,
                timeout=_ZELLIJ_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            logger.warning("Timeout checking zellij panes")
            return False

        if result.returncode != 0:
            return False

        return pane_id in result.stdout

    def set_title(self, pane_id: str, title: str) -> None:
        """Zellij does not support setting pane titles directly.

        Logs a warning since this operation is not supported.
        """
        logger.warning(
            "Zellij does not support setting pane titles. "
            "Requested title '%s' for pane %s ignored.",
            title,
            pane_id,
        )

    def configure_pane(self, pane_id: str, remain_on_exit: bool = True) -> None:
        """Configure zellij pane behavior on exit.

        Zellij has its own exit behavior config; this is a best-effort no-op
        with a debug log.
        """
        logger.debug(
            "Zellij pane %s configure_pane(remain_on_exit=%s) — "
            "zellij manages exit behavior via its own config",
            pane_id,
            remain_on_exit,
        )

    def _get_latest_pane_id(self) -> str | None:
        """Get the most recently created pane ID from zellij list-panes."""
        try:
            result = subprocess.run(
                ["zellij", "list-panes"],
                capture_output=True,
                text=True,
                timeout=_ZELLIJ_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            return None

        if result.returncode != 0:
            return None

        lines = result.stdout.strip().splitlines()
        if not lines:
            return None

        # Return the last line's identifier (most recent pane)
        last_line = lines[-1].strip()
        return last_line.split()[0] if last_line else None
