"""Unit tests for HookRunner."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.application.services.workspace.entities import HookResult
from src.application.services.workspace.hook_runner import HookRunner
from src.application.services.workspace.exceptions import HookExecutionError, SecurityError


@pytest.fixture
def temp_hooks_dir(tmp_path: Path) -> Path:
    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir()
    return hooks_dir


@pytest.fixture
def hook_runner(temp_hooks_dir: Path) -> HookRunner:
    return HookRunner(hooks_dir=temp_hooks_dir)


class TestHookRunnerSanitizePath:
    def test_sanitize_path_with_file_not_exists(
        self, hook_runner: HookRunner, temp_hooks_dir: Path
    ) -> None:
        with pytest.raises(SecurityError, match="Path does not exist"):
            hook_runner._sanitize_path(temp_hooks_dir / "nonexistent.sh")

    def test_sanitize_path_traversal_dotdot(self, hook_runner: HookRunner) -> None:
        with pytest.raises(SecurityError, match="Path traversal attempt detected"):
            hook_runner._sanitize_path(Path("/some/path/../../../etc/passwd"))

    def test_sanitize_path_traversal_windows(self, hook_runner: HookRunner) -> None:
        with pytest.raises(SecurityError, match="Path traversal attempt detected"):
            hook_runner._sanitize_path(Path("\\windows\\system32"))

    def test_sanitize_path_resolve_error(
        self, hook_runner: HookRunner, temp_hooks_dir: Path
    ) -> None:
        with patch.object(Path, "resolve", side_effect=OSError("Cannot resolve")):
            with pytest.raises(SecurityError, match="Failed to resolve path"):
                hook_runner._sanitize_path(temp_hooks_dir / "test.sh")


class TestHookRunnerGetSafeEnv:
    def test_get_safe_env_filters_dangerous_vars(self, hook_runner: HookRunner) -> None:
        with patch.dict(
            "os.environ",
            {
                "HOME": "/home/user",
                "PATH": "/usr/bin",
                "LD_PRELOAD": "/malicious.so",
                "LD_LIBRARY_PATH": "/malicious",
            },
            clear=False,
        ):
            safe_env = hook_runner._get_safe_env()
            assert "HOME" in safe_env
            assert "PATH" in safe_env
            assert "LD_PRELOAD" not in safe_env
            assert "LD_LIBRARY_PATH" not in safe_env


class TestHookRunnerRunHook:
    def test_run_hook_oserror(self, hook_runner: HookRunner, temp_hooks_dir: Path) -> None:
        hook_script = temp_hooks_dir / "bad.sh"
        hook_script.write_text("#!/bin/bash\nexit 1")
        hook_script.chmod(0o755)

        with patch("subprocess.run", side_effect=OSError("Exec failed")):
            with pytest.raises(HookExecutionError, match="Failed to execute hook"):
                hook_runner.run_hook("bad", temp_hooks_dir)


class TestHookRunnerRunSetup:
    def test_run_setup_success(self, hook_runner: HookRunner, temp_hooks_dir: Path) -> None:
        hook_script = temp_hooks_dir / "setup.sh"
        hook_script.write_text("#!/bin/bash\necho 'Setup done'")
        hook_script.chmod(0o755)

        result = hook_runner.run_setup(temp_hooks_dir)

        assert result.success is True
        assert result.exit_code == 0


class TestHookRunnerRunTeardown:
    def test_run_teardown_success(self, hook_runner: HookRunner, temp_hooks_dir: Path) -> None:
        hook_script = temp_hooks_dir / "teardown.sh"
        hook_script.write_text("#!/bin/bash\necho 'Teardown done'")
        hook_script.chmod(0o755)

        result = hook_runner.run_teardown(temp_hooks_dir)

        assert result.success is True
        assert result.exit_code == 0
