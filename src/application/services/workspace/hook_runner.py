"""HookRunner for executing workspace hooks with security features."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING

from src.application.services.workspace.entities import HookResult
from src.application.services.workspace.exceptions import HookExecutionError, SecurityError

if TYPE_CHECKING:
    pass

# Dangerous environment variables that should never be passed to hooks
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

# Safe default environment variables
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
        "_",
    }
)


class HookRunner:
    """Executes workspace hooks with security features.

    Implements C-02 (path sanitization) and M-01 (configurable timeout)
    requirements for secure hook execution.
    """

    def __init__(
        self,
        hooks_dir: Path,
        timeout: int = 30,
        allowed_env_vars: set[str] | None = None,
    ) -> None:
        """Initialize HookRunner.

        Args:
            hooks_dir: Directory containing hook scripts.
            timeout: Timeout in seconds for hook execution (default: 30).
            allowed_env_vars: Additional environment variables to allow.
                             If None, uses safe defaults.
        """
        self._hooks_dir = hooks_dir
        self._timeout = timeout
        self._allowed_env_vars: frozenset[str] = SAFE_DEFAULT_ENV_VARS | (
            frozenset(allowed_env_vars) if allowed_env_vars else frozenset()
        )

    def _sanitize_path(self, path: Path, expect_file: bool = True) -> Path:
        """Sanitize and validate path.

        Implements C-02 path sanitization:
        - Resolves to absolute path
        - Blocks path traversal attempts
        - Verifies path exists and is a file or directory
        - Verifies executable permissions (for files only)

        Args:
            path: Path to sanitize.
            expect_file: If True, validates path is a file. If False, validates path is a directory.

        Returns:
            Sanitized absolute path.

        Raises:
            SecurityError: If path is invalid or unsafe.
        """
        # Convert to string for traversal check
        path_str = str(path)

        # Check for path traversal attempts (both Unix and Windows style)
        if ".." in path_str or path_str.startswith("\\"):
            raise SecurityError(f"Path traversal attempt detected: {path}")

        # Resolve to absolute path
        try:
            resolved_path = path.resolve()
        except (OSError, ValueError) as e:
            raise SecurityError(f"Failed to resolve path: {path}", e) from None

        # Verify path exists
        if not resolved_path.exists():
            raise SecurityError(f"Path does not exist: {resolved_path}")

        # Verify path is a file or directory based on expect_file flag
        if expect_file:
            if not resolved_path.is_file():
                raise SecurityError(f"Path is not a file: {resolved_path}")
            # Verify executable permissions (check read and execute for scripts)
            if not os.access(resolved_path, os.R_OK | os.X_OK):
                raise SecurityError(f"Path is not executable: {resolved_path}")
        else:
            if not resolved_path.is_dir():
                raise SecurityError(f"Path is not a directory: {resolved_path}")

        return resolved_path

    def _get_safe_env(self) -> dict[str, str]:
        """Return sanitized environment variables.

        Filters out dangerous environment variables to prevent
        security vulnerabilities (C-02).

        Returns:
            Dictionary of safe environment variables.
        """
        safe_env: dict[str, str] = {}

        for key, value in os.environ.items():
            # Skip dangerous variables
            if key in DANGEROUS_ENV_VARS:
                continue

            # Skip variables with dangerous patterns
            if any(
                key.startswith(pattern.rstrip("*"))
                for pattern in DANGEROUS_ENV_VARS
                if "*" in pattern
            ):
                continue

            # Only include allowed variables
            if key in self._allowed_env_vars:
                safe_env[key] = value

        return safe_env

    def run_setup(self, workspace_path: Path) -> HookResult:
        """Run setup hook for workspace.

        Args:
            workspace_path: Path to the workspace.

        Returns:
            HookResult containing execution results.
        """
        return self.run_hook("setup", workspace_path)

    def run_teardown(self, workspace_path: Path) -> HookResult:
        """Run teardown hook for workspace.

        Args:
            workspace_path: Path to the workspace.

        Returns:
            HookResult containing execution results.
        """
        return self.run_hook("teardown", workspace_path)

    def run_hook(self, hook_name: str, workspace_path: Path) -> HookResult:
        """Run a named hook with security checks.

        Implements M-01 (configurable timeout) and C-02 (path sanitization).

        Args:
            hook_name: Name of the hook to execute (e.g., 'setup', 'teardown').
            workspace_path: Path to the workspace.

        Returns:
            HookResult containing execution results.

        Raises:
            SecurityError: If paths are invalid.
            HookExecutionError: If hook execution fails or times out.
        """
        # Sanitize workspace path (directory)
        sanitized_workspace = self._sanitize_path(workspace_path, expect_file=False)

        # Construct hook path
        hook_path = self._hooks_dir / f"{hook_name}.sh"

        # Sanitize hook path
        try:
            sanitized_hook = self._sanitize_path(hook_path)
        except SecurityError:
            # Hook doesn't exist - return empty success result
            return HookResult(
                success=True,
                exit_code=0,
                stdout="",
                stderr="",
                duration_ms=0,
            )

        # Prepare environment
        safe_env = self._get_safe_env()

        # Add workspace path to environment
        safe_env["WORKSPACE_PATH"] = str(sanitized_workspace)

        # Execute hook with timeout
        start_time = time.monotonic()

        try:
            result = subprocess.run(
                [str(sanitized_hook), str(sanitized_workspace)],
                env=safe_env,
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
        except subprocess.TimeoutExpired as e:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            raise HookExecutionError(
                f"Hook '{hook_name}' timed out after {self._timeout} seconds",
                e,
            ) from None
        except OSError as e:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            raise HookExecutionError(
                f"Failed to execute hook '{hook_name}': {e}",
                e,
            ) from None

        duration_ms = int((time.monotonic() - start_time) * 1000)

        return HookResult(
            success=result.returncode == 0,
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            duration_ms=duration_ms,
        )
