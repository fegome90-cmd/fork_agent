"""Tests for PollRunDirectory debt fixes (S-M2: mkdir mode=0o700)."""

from __future__ import annotations

from pathlib import Path

from src.infrastructure.polling.poll_run_directory import PollRunDirectory


class TestMkdirPermissions:
    """S-M2: Run directories should use mode=0o700."""

    def test_base_dir_permissions(self, tmp_path: Path) -> None:
        base = tmp_path / "polls"
        PollRunDirectory(base)

        # The base dir is created by the constructor
        assert base.exists()
        actual_mode = base.stat().st_mode & 0o777
        assert actual_mode == 0o700, f"Expected 0o700, got {oct(actual_mode)}"

    def test_run_dir_permissions(self, tmp_path: Path) -> None:
        base = tmp_path / "polls"
        directory = PollRunDirectory(base)
        run_dir = directory.create_run_dir("r1")

        actual_mode = run_dir.stat().st_mode & 0o777
        assert actual_mode == 0o700, f"Expected 0o700, got {oct(actual_mode)}"

    def test_nested_run_dir_permissions(self, tmp_path: Path) -> None:
        """Even deeply nested run dirs should have 0o700."""
        base = tmp_path / "polls"
        directory = PollRunDirectory(base)
        # create_run_dir creates base/run_id, so we test the dir itself
        run_dir = directory.create_run_dir("nested-test-run")

        actual_mode = run_dir.stat().st_mode & 0o777
        assert actual_mode == 0o700, f"Expected 0o700, got {oct(actual_mode)}"
