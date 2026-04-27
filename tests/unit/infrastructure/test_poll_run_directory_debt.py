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


class TestReadEvents:
    """Debt fix: run directories must support reading spawn metadata back."""

    def test_read_events_returns_appended_events(self, tmp_path: Path) -> None:
        directory = PollRunDirectory(tmp_path / "polls")
        directory.create_run_dir("r1")
        directory.append_event("r1", {"type": "agent_spawned", "pid": 1234})
        directory.append_event("r1", {"type": "completed"})

        events = directory.read_events("r1")

        assert events == [
            {"type": "agent_spawned", "pid": 1234},
            {"type": "completed"},
        ]

    def test_read_events_ignores_malformed_lines(self, tmp_path: Path) -> None:
        directory = PollRunDirectory(tmp_path / "polls")
        run_dir = directory.create_run_dir("r1")
        (run_dir / "events.jsonl").write_text('{"type":"ok"}\nnot-json\n', encoding="utf-8")

        events = directory.read_events("r1")

        assert events == [{"type": "ok"}]
