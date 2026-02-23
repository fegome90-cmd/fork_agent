"""ShellActionRunner infrastructure implementation."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from src.application.services.orchestration.actions import ShellCommandAction
from src.domain.ports.event_ports import Action

DANGEROUS_ENV_VARS: frozenset[str] = frozenset(
    {
        "LD_PRELOAD",
        "LD_LIBRARY_PATH",
        "LD_AUDIT",
        "LD_DEBUG",
        "BASH_ENV",
        "ENV",
        "CDPATH",
        "GLOBIGNORE",
        "BASH_FUNC_*",
        "IFS",
        "MAIL",
        "MAILPATH",
        "OPTIND",
        "PS1",
        "PS2",
        "FIGNORE",
    }
)

SAFE_DEFAULT_ENV_VARS: frozenset[str] = frozenset(
    {
        "HOME",
        "USER",
        "LOGNAME",
        "PATH",
        "SHELL",
        "TERM",
        "LANG",
        "LC_ALL",
        "PWD",
        "SHLVL",
    }
)


class ShellActionRunner:
    """Executes shell command actions with security features.

    Adapts subprocess execution to IActionRunner interface.
    Reuses security patterns from HookRunner (C-02, M-01).

    Attributes:
        hooks_dir: Directory for hook scripts (passed to executed commands).
        default_timeout: Default timeout in seconds for command execution.
    """

    __slots__ = ("_default_timeout", "_hooks_dir")

    def __init__(self, hooks_dir: Path, default_timeout: int = 30) -> None:
        self._hooks_dir = hooks_dir
        self._default_timeout = default_timeout

    def _get_safe_env(self) -> dict[str, str]:
        """Return sanitized environment variables.

        Filters out dangerous environment variables to prevent
        security vulnerabilities.

        Returns:
            Dictionary of safe environment variables.
        """
        safe_env: dict[str, str] = {}

        for key, value in os.environ.items():
            if key in DANGEROUS_ENV_VARS:
                continue

            if any(
                key.startswith(pattern.rstrip("*"))
                for pattern in DANGEROUS_ENV_VARS
                if "*" in pattern
            ):
                continue

            if key in SAFE_DEFAULT_ENV_VARS:
                safe_env[key] = value

        safe_env["HOOKS_DIR"] = str(self._hooks_dir)

        return safe_env

    def run(self, action: Action) -> None:
        """Execute the shell command action.

        Args:
            action: The action to execute (must be ShellCommandAction).

        Raises:
            TypeError: If action is not a ShellCommandAction.
            RuntimeError: If command execution fails or times out.
        """
        if not isinstance(action, ShellCommandAction):
            raise TypeError(
                f"ShellActionRunner only handles ShellCommandAction, got {type(action).__name__}"
            )

        timeout = action.timeout or self._default_timeout
        safe_env = self._get_safe_env()

        try:
            result = subprocess.run(
                action.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=safe_env,
            )
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"Action timed out after {timeout} seconds: {action.command}") from e

        if result.returncode != 0:
            error_msg = result.stderr[:200] if result.stderr else "Unknown error"
            raise RuntimeError(f"Action failed (exit {result.returncode}): {error_msg}")
