"""Integration tests for HookRunner security features.

These tests verify:
- C-02: Path traversal is blocked
- M-01: Timeout works correctly
- Dangerous environment variables are blocked
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
from pathlib import Path

import pytest

from src.application.services.workspace.hook_runner import HookRunner
from src.application.services.workspace.exceptions import SecurityError, HookExecutionError


class TestHookRunnerSecurity:
    """Tests for HookRunner security features."""

    @pytest.fixture
    def temp_hooks_dir(self, tmp_path: Path) -> Path:
        """Create a temporary hooks directory."""
        hooks_dir = tmp_path / "hooks"
        hooks_dir.mkdir()
        return hooks_dir

    @pytest.fixture
    def temp_workspace_dir(self, tmp_path: Path) -> Path:
        """Create a temporary workspace directory."""
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()
        return workspace_dir


class TestPathTraversalBlocked(TestHookRunnerSecurity):
    """Tests for C-02: Path traversal blocking."""

    def test_path_traversal_with_dotdot(self, temp_hooks_dir: Path) -> None:
        """Test that path traversal with '..' is blocked (C-02)."""
        runner = HookRunner(hooks_dir=temp_hooks_dir, timeout=30)

        # Try to use path traversal
        malicious_path = Path("/etc/passwd/../../../etc/shadow")

        with pytest.raises(SecurityError) as exc_info:
            runner._sanitize_path(malicious_path)

        assert "traversal" in str(exc_info.value).lower()

    def test_path_traversal_windows_style(self, temp_hooks_dir: Path) -> None:
        """Test that Windows-style path traversal is blocked (C-02)."""
        runner = HookRunner(hooks_dir=temp_hooks_dir, timeout=30)

        # Try to use Windows-style path traversal
        malicious_path = Path("C:\\..\\..\\Windows\\System32")

        with pytest.raises(SecurityError) as exc_info:
            runner._sanitize_path(malicious_path)

        assert "traversal" in str(exc_info.value).lower()

    def test_nonexistent_path_raises_error(self, temp_hooks_dir: Path) -> None:
        """Test that non-existent paths raise SecurityError."""
        runner = HookRunner(hooks_dir=temp_hooks_dir, timeout=30)

        nonexistent_path = Path("/nonexistent/path/that/does/not/exist")

        with pytest.raises(SecurityError) as exc_info:
            runner._sanitize_path(nonexistent_path)

        assert "does not exist" in str(exc_info.value).lower()

    def test_valid_path_resolves_correctly(
        self, temp_hooks_dir: Path, temp_workspace_dir: Path
    ) -> None:
        """Test that valid paths resolve correctly."""
        # Create a valid executable file
        test_file = temp_workspace_dir / "test.sh"
        test_file.write_text("#!/bin/bash\necho 'test'")
        test_file.chmod(0o755)  # Make executable

        runner = HookRunner(hooks_dir=temp_hooks_dir, timeout=30)

        # This should not raise
        resolved = runner._sanitize_path(test_file)

        assert resolved.resolve() == test_file.resolve()


class TestTimeoutWorks(TestHookRunnerSecurity):
    """Tests for M-01: Timeout functionality."""

    def test_hook_timeout_expires(
        self, tmp_path: Path, temp_workspace_dir: Path
    ) -> None:
        """Test that hook execution times out (M-01)."""
        # Create a hook that sleeps too long
        hooks_dir = tmp_path / "hooks"
        hooks_dir.mkdir()

        setup_hook = hooks_dir / "setup.sh"
        setup_hook.write_text("#!/bin/bash\nsleep 10\necho 'done'\n")
        setup_hook.chmod(0o755)

        runner = HookRunner(hooks_dir=hooks_dir, timeout=1)  # 1 second timeout

        with pytest.raises(HookExecutionError) as exc_info:
            runner.run_setup(temp_workspace_dir)

        assert "timed out" in str(exc_info.value).lower()
        assert "1" in str(exc_info.value)  # Should mention the timeout value

    def test_hook_executes_successfully_within_timeout(
        self, tmp_path: Path, temp_workspace_dir: Path
    ) -> None:
        """Test that hooks execute successfully when they complete in time."""
        hooks_dir = tmp_path / "hooks"
        hooks_dir.mkdir()

        setup_hook = hooks_dir / "setup.sh"
        setup_hook.write_text("#!/bin/bash\necho 'setup complete'\nexit 0\n")
        setup_hook.chmod(0o755)

        runner = HookRunner(hooks_dir=hooks_dir, timeout=30)

        result = runner.run_setup(temp_workspace_dir)

        assert result.success is True
        assert result.exit_code == 0
        assert "setup complete" in result.stdout


class TestDangerousEnvVarsBlocked(TestHookRunnerSecurity):
    """Tests for dangerous environment variable blocking."""

    def test_ld_preload_blocked(self, temp_hooks_dir: Path) -> None:
        """Test that LD_PRELOAD is blocked."""
        runner = HookRunner(hooks_dir=temp_hooks_dir, timeout=30)

        # Set dangerous env var
        os.environ["LD_PRELOAD"] = "/malicious.so"

        safe_env = runner._get_safe_env()

        assert "LD_PRELOAD" not in safe_env

    def test_ld_library_path_blocked(self, temp_hooks_dir: Path) -> None:
        """Test that LD_LIBRARY_PATH is blocked."""
        runner = HookRunner(hooks_dir=temp_hooks_dir, timeout=30)

        os.environ["LD_LIBRARY_PATH"] = "/malicious/lib"

        safe_env = runner._get_safe_env()

        assert "LD_LIBRARY_PATH" not in safe_env

    def test_bash_func_wildcard_blocked(self, temp_hooks_dir: Path) -> None:
        """Test that BASH_FUNC_* patterns are blocked."""
        runner = HookRunner(hooks_dir=temp_hooks_dir, timeout=30)

        os.environ["BASH_FUNC_MALICIOUS%%"] = "malicious function"

        safe_env = runner._get_safe_env()

        assert "BASH_FUNC_MALICIOUS%%" not in safe_env

    def test_safe_vars_allowed(self, temp_hooks_dir: Path) -> None:
        """Test that safe environment variables are allowed."""
        runner = HookRunner(hooks_dir=temp_hooks_dir, timeout=30)

        # Ensure HOME is set for the test
        if "HOME" not in os.environ:
            os.environ["HOME"] = "/home/test"

        safe_env = runner._get_safe_env()

        # Safe vars should be present
        assert "HOME" in safe_env or "PATH" in safe_env or "USER" in safe_env

    def test_custom_allowed_vars_passed_through(self, temp_hooks_dir: Path) -> None:
        """Test that custom allowed variables pass through."""
        runner = HookRunner(
            hooks_dir=temp_hooks_dir,
            timeout=30,
            allowed_env_vars={"CUSTOM_VAR"},
        )

        os.environ["CUSTOM_VAR"] = "custom_value"

        safe_env = runner._get_safe_env()

        assert "CUSTOM_VAR" in safe_env
        assert safe_env["CUSTOM_VAR"] == "custom_value"
