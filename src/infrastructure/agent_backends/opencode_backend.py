"""OpenCode CLI backend implementation."""

from __future__ import annotations

import logging
import os
import shlex
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


class OpencodeBackend:
    """Backend for opencode CLI coding agent.

    Default strategy requested by user:
    - Primary model: opencode/minimax-m2.5-free
    - Fallback model: opencode/minimax-m2.5

    A fallback retry is executed in a POSIX shell (`bash -lc`) so behavior is
    deterministic even when the tmux session default shell is fish.

    Binary resolution order is explicit and suitable for non-interactive
    processes such as pm2-managed services:
    1. `OPENCODE_BIN` env override
    2. `PATH` lookup via `shutil.which("opencode")`
    3. Known user-local install path: `~/.opencode/bin/opencode`
    """

    name: str = "opencode"
    display_name: str = "OpenCode CLI"

    @staticmethod
    def _is_executable(path: str) -> bool:
        """Return whether a path exists and is executable."""
        return Path(path).is_file() and os.access(path, os.X_OK)

    def resolve_executable(self) -> str | None:
        """Resolve the OpenCode executable path.

        Returns:
            Absolute executable path when found, otherwise None.
        """
        candidates: list[str] = []

        env_override = os.getenv("OPENCODE_BIN", "").strip()
        if env_override:
            candidates.append(env_override)

        which_result = shutil.which("opencode")
        if which_result:
            candidates.append(which_result)

        candidates.append(str(Path.home() / ".opencode" / "bin" / "opencode"))

        seen: set[str] = set()
        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)
            if self._is_executable(candidate):
                return candidate

        return None

    def is_available(self) -> bool:
        """Check if opencode CLI is installed."""
        return self.resolve_executable() is not None

    def get_launch_command(self, task: str, model: str) -> str:
        """Build opencode launch command with model fallback.

        Args:
            task: The task/prompt for the agent.
            model: Primary model identifier.

        Returns:
            Shell command string with proper escaping.
        """
        executable = self.resolve_executable()
        if executable is None:
            logger.warning(
                "opencode executable not resolved; falling back to PATH lookup for launch command"
            )
            executable = "opencode"

        quoted_executable = shlex.quote(executable)
        primary_model = model
        fallback_model = os.getenv("OPENCODE_FALLBACK_MODEL", "opencode/minimax-m2.5")
        fallback_message = shlex.quote(
            f"[fork-agent] primary model failed, retrying fallback model: {fallback_model}"
        )

        primary_cmd = (
            f"{quoted_executable} run -m {shlex.quote(primary_model)} {shlex.quote(task)}"
        )

        if fallback_model == primary_model:
            return primary_cmd

        fallback_cmd = (
            f"{quoted_executable} run -m {shlex.quote(fallback_model)} {shlex.quote(task)}"
        )
        script = (
            f"{primary_cmd}; rc=$?; "
            f"if [ $rc -ne 0 ]; then "
            f"echo {fallback_message} >&2; "
            f"{fallback_cmd}; "
            "fi"
        )
        return f"bash -lc {shlex.quote(script)}"

    def get_default_model(self) -> str:
        """Get default model for opencode (override with env if needed)."""
        return os.getenv("OPENCODE_DEFAULT_MODEL", "opencode/minimax-m2.5-free")
