"""Unit tests for verify_runner module."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.application.services.workflow.verify_runner import VerifyRunner


class TestVerifyRunner:
    def test_detect_root_finds_pyproject(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").touch()
        runner = VerifyRunner()
        result = runner.detect_project_root(tmp_path)
        assert result == tmp_path

    def test_detect_root_walks_up(self, tmp_path: Path) -> None:
        subdir = tmp_path / "src" / "module"
        subdir.mkdir(parents=True)
        (tmp_path / "pyproject.toml").touch()
        runner = VerifyRunner()
        result = runner.detect_project_root(subdir)
        assert result == tmp_path

    def test_detect_root_not_found(self, tmp_path: Path) -> None:
        runner = VerifyRunner()
        with pytest.raises(FileNotFoundError, match="Project root not found"):
            runner.detect_project_root(tmp_path)

    def test_detect_root_multiple_monorepo(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").touch()
        subdir = tmp_path / "packages" / "app"
        subdir.mkdir(parents=True)
        (subdir / "pyproject.toml").touch()
        runner = VerifyRunner()
        result = runner.detect_project_root(subdir)
        assert result == subdir

    @patch("subprocess.run")
    def test_run_success(self, mock_run: MagicMock, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").touch()
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "3 passed in 0.5s"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        runner = VerifyRunner()
        result = runner.run(tmp_path)
        assert result["passed"] is True
        assert result["exit_code"] == 0
        assert result["test_count"] == 3
        assert result["fail_count"] == 0


    @patch("subprocess.run")
    def test_run_timeout(self, mock_run: MagicMock, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").touch()
        mock_run.side_effect = subprocess.TimeoutExpired("pytest", 300)
        runner = VerifyRunner()
        result = runner.run(tmp_path, timeout=300)
        assert result["passed"] is False
        assert result["exit_code"] == -1
        assert "timed out" in result["error"]

    @patch("subprocess.run")
    def test_run_no_pytest(self, mock_run: MagicMock, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").touch()
        mock_run.side_effect = FileNotFoundError("pytest not found")
        runner = VerifyRunner()
        result = runner.run(tmp_path)
        assert result["passed"] is False
        assert "pytest not found" in result["error"]

    @patch("subprocess.run")
    def test_run_with_complex_output(self, mock_run: MagicMock, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").touch()
        mock_result = MagicMock()
        mock_result.returncode = 0
        # Multiple test patterns
        mock_result.stdout = "tests/test_a.py::test_x PASSED\ntests/test_b.py::test_y PASSED\n5 passed in 1.2s"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        runner = VerifyRunner()
        result = runner.run(tmp_path)
        assert result["passed"] is True
        assert result["test_count"] == 5

    @patch("subprocess.run")
    def test_run_with_errors_in_stderr(self, mock_run: MagicMock, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").touch()
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "ERROR: Something went wrong\n1 failed"
        mock_run.return_value = mock_result
        runner = VerifyRunner()
        result = runner.run(tmp_path)
        assert result["passed"] is False
        assert result["error"] is not None

    @patch("subprocess.run")
    def test_run_uses_python_executable(self, mock_run: MagicMock, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").touch()
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "1 passed"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        runner = VerifyRunner()
        result = runner.run(tmp_path)
        assert result["passed"] is True
        call_args = mock_run.call_args
        assert call_args is not None
