"""ShellActionRunner infrastructure implementation."""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from src.application.services.orchestration.actions import ShellCommandAction
from src.domain.ports.event_ports import Action

logger = logging.getLogger(__name__)

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


class HookExecutionError(Exception):
    """Raised when a critical hook fails."""


class ShellActionRunner:
    """Executes shell command actions with security features.

    Adapts subprocess execution to IActionRunner interface.
    Reuses security patterns from HookRunner (C-02, M-01).

    Attributes:
        hooks_dir: Directory for hook scripts (passed to executed commands).
        default_timeout: Default timeout in seconds for command execution.
        strict_mode: When True, blocks unknown commands.
    """

    _DANGEROUS_PATTERNS: frozenset[str] = frozenset(
        {
            "curl ",
            "wget ",
            "nc ",
            "ncat ",
            "bash -i",
            "sh -i",
            "/dev/tcp/",
            "/dev/udp/",
            "base64 -d",
            "xxd -r",
            "chmod 777",
            "chmod 666",
            "> /etc/",
            ">> /etc/",
            "mkfifo ",
            "nohup ",
        }
    )

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

    def _validate_command(self, command: str) -> None:
        """Validate command for dangerous patterns.

        Logs warnings for suspicious commands. Raises HookExecutionError
        if dangerous patterns are detected.

        Args:
            command: The shell command string to validate.

        Raises:
            HookExecutionError: If a dangerous pattern is found in the command.
        """
        stripped = command.strip()

        for pattern in self._DANGEROUS_PATTERNS:
            if pattern in stripped:
                raise HookExecutionError(f"Blocked dangerous command pattern: {pattern.strip()}")

    def run(self, action: Action) -> None:
        """Execute the shell command action.

        Args:
            action: The action to execute (must be ShellCommandAction).

        Raises:
            TypeError: If action is not a ShellCommandAction.
            HookExecutionError: If critical hook fails or dangerous command.
        """
        if not isinstance(action, ShellCommandAction):
            raise TypeError(
                f"ShellActionRunner only handles ShellCommandAction, got {type(action).__name__}"
            )

        self._validate_command(action.command)

        timeout = action.timeout or self._default_timeout
        safe_env = self._get_safe_env()

        try:
            result = subprocess.run(
                action.command,  # nosec B602
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=safe_env,
            )
        except subprocess.TimeoutExpired as e:
            error_msg = f"Action timed out after {timeout} seconds: {action.command}"
            if action.continue_on_failure:
                logger.warning("%s", error_msg)
                return
            raise HookExecutionError(error_msg) from e

        if result.returncode != 0:
            error_msg = result.stderr[:200] if result.stderr else "Unknown error"
            full_msg = f"Action failed (exit {result.returncode}): {error_msg}"

            if action.continue_on_failure:
                logger.warning(
                    "Hook '%s' failed (exit %d) but continuing: %s",
                    action.command,
                    result.returncode,
                    error_msg,
                )
                return

            raise HookExecutionError(full_msg)
