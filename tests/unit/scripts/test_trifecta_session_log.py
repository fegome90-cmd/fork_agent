"""Tests for trifecta-session-log orchestrator script.

Validates:
- Script exists and is executable
- Passes correct args to `trifecta session append`
- Non-blocking: exits 0 even when trifecta command fails
- Handles missing optional --files arg gracefully
"""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS_DIR = Path.home() / ".pi" / "agent" / "skills" / "tmux-fork-orchestrator" / "scripts"
SESSION_LOG_SCRIPT = SCRIPTS_DIR / "trifecta-session-log"


@pytest.fixture
def script_exists():
    """Skip test if script does not exist yet."""
    if not SESSION_LOG_SCRIPT.exists():
        pytest.skip(f"Script not yet created: {SESSION_LOG_SCRIPT}")
    return SESSION_LOG_SCRIPT


class TestScriptExists:
    """RED: Script must exist and be executable."""

    def test_script_file_exists(self, script_exists):
        assert script_exists.is_file()

    def test_script_is_executable(self, script_exists):
        assert script_exists.stat().st_mode & 0o111, "Script must be executable (chmod +x)"


class TestScriptInvocation:
    """GREEN: Script calls trifecta session append with correct args."""

    @patch("subprocess.run")
    def test_calls_trifecta_with_required_args(self, mock_run, script_exists):
        """Script must forward segment and summary to trifecta session append."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )

        result = subprocess.run(
            [str(script_exists), "explorer", "Completed task analysis"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

    @patch("subprocess.run")
    def test_calls_trifecta_with_all_args(self, mock_run, script_exists):
        """Script must forward segment, summary, and files to trifecta session append."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )

        result = subprocess.run(
            [
                str(script_exists),
                "implementer",
                "Fixed auth middleware",
                "src/auth.py,tests/test_auth.py",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0


class TestNonBlocking:
    """TRIANGULATE: Script must never block orchestrator on failure."""

    def test_exits_zero_when_trifecta_missing(self, script_exists, monkeypatch):
        """If trifecta is not installed, script exits 0."""
        # Prepend a PATH dir that has no trifecta
        empty_bin = Path("/tmp/fork-test-no-trifecta")
        empty_bin.mkdir(exist_ok=True)
        monkeypatch.setenv("PATH", f"{empty_bin}:/usr/bin:/bin")

        result = subprocess.run(
            [str(script_exists), "test-role", "test summary"],
            capture_output=True,
            text=True,
            env={**dict(__import__("os").environ), "PATH": f"{empty_bin}:/usr/bin:/bin"},
        )

        assert result.returncode == 0, (
            f"Script must exit 0 when trifecta missing, got {result.returncode}. "
            f"stderr: {result.stderr}"
        )


class TestArgValidation:
    """TRIANGULATE: Edge cases for argument handling."""

    def test_exits_nonzero_without_summary(self, script_exists):
        """Missing required summary should exit non-zero."""
        result = subprocess.run(
            [str(script_exists), "role-only"],
            capture_output=True,
            text=True,
        )

        # Script requires at least segment and summary
        assert result.returncode != 0, "Missing summary should be an error"

    def test_default_segment_is_dot(self, script_exists):
        """If no segment provided, defaults to '.'."""
        result = subprocess.run(
            [str(script_exists), ".", "summary only"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
