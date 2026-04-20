"""Test runner for workflow verification."""

from __future__ import annotations

import contextlib
import subprocess
import sys
import time
from pathlib import Path

from src.application.services.workflow.state import VerifyResults


class VerifyRunner:
    """Runs pytest and captures test results."""

    TIMEOUT_SECONDS = 300  # 5 minutes

    def detect_project_root(self, start_path: Path | None = None) -> Path:
        """Walk up from start_path looking for pyproject.toml.

        Args:
            start_path: Directory to start from (defaults to cwd)

        Returns:
            Path to project root (directory containing pyproject.toml)

        Raises:
            FileNotFoundError: If pyproject.toml not found
        """
        if start_path is None:
            start_path = Path.cwd()

        current = start_path.resolve()

        # Walk up looking for pyproject.toml
        while True:
            pyproject = current / "pyproject.toml"
            if pyproject.exists():
                return current

            parent = current.parent
            if parent == current:
                # Reached filesystem root
                raise FileNotFoundError(
                    f"Project root not found: pyproject.toml not found from {start_path} to root"
                )
            current = parent

    def run(
        self,
        project_root: Path | None = None,
        timeout: int | None = None,
    ) -> VerifyResults:
        """Run pytest in the project directory.

        Args:
            project_root: Project root (auto-detected if None)
            timeout: Timeout in seconds (defaults to TIMEOUT_SECONDS)

        Returns:
            VerifyResults with test execution data
        """
        if timeout is None:
            timeout = self.TIMEOUT_SECONDS

        # Detect project root if not provided
        if project_root is None:
            project_root = self.detect_project_root()

        start_time = time.time()

        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "-v", "--tb=short"],
                cwd=project_root,
                capture_output=True,
                timeout=timeout,
                text=True,
            )
        except subprocess.TimeoutExpired:
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                "passed": False,
                "exit_code": -1,
                "test_count": 0,
                "fail_count": 0,
                "duration_ms": duration_ms,
                "error": f"Tests timed out after {timeout} seconds",
            }
        except FileNotFoundError:
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                "passed": False,
                "exit_code": -1,
                "test_count": 0,
                "fail_count": 0,
                "duration_ms": duration_ms,
                "error": "pytest not found - ensure pytest is installed",
            }

        duration_ms = int((time.time() - start_time) * 1000)

        # Parse test counts from output
        test_count = 0
        fail_count = 0

        # Look for pytest summary line like "5 passed" or "3 failed, 5 passed"
        for line in result.stdout.split("\n"):
            if " passed" in line or " failed" in line:
                # Extract numbers
                parts = line.split()
                for i, part in enumerate(parts):
                    clean_part = part.rstrip(",")
                    if clean_part == "passed" and i > 0:
                        with contextlib.suppress(ValueError):
                            test_count += int(parts[i - 1].rstrip(","))
                    elif clean_part == "failed" and i > 0:
                        with contextlib.suppress(ValueError):
                            fail_count += int(parts[i - 1].rstrip(","))

        # Also check stderr
        for line in result.stderr.split("\n"):
            if " passed" in line or " failed" in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    clean_part = part.rstrip(",")
                    if clean_part == "passed" and i > 0:
                        with contextlib.suppress(ValueError):
                            test_count += int(parts[i - 1].rstrip(","))
                    elif clean_part == "failed" and i > 0:
                        with contextlib.suppress(ValueError):
                            fail_count += int(parts[i - 1].rstrip(","))

        test_results: VerifyResults = {
            "passed": result.returncode == 0,
            "exit_code": result.returncode,
            "test_count": test_count,
            "fail_count": fail_count,
            "duration_ms": duration_ms,
        }

        # Include error message if tests failed
        if result.returncode != 0 and result.stderr:
            # Truncate long output
            error_msg = result.stderr[-500:] if len(result.stderr) > 500 else result.stderr
            test_results["error"] = error_msg

        return test_results


# Module-level instance for convenience
verify_runner = VerifyRunner()
