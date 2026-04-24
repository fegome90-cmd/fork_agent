"""Tests for minimal workflow protocol preflight."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from src.application.services.orchestration.protocol_preflight import ProtocolPreflightService
from src.application.services.workflow.state import PlanState, WorkflowPhase


def _save_plan(path: Path, phase: WorkflowPhase = WorkflowPhase.OUTLINED) -> None:
    PlanState(session_id="plan-1", phase=phase).save(path)


def _completed(stdout: str = "", stderr: str = "", returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def _patch_runtime(
    monkeypatch: Any,
    repo_root: Path,
    *,
    tmux_path: str | None = "/usr/bin/tmux",
    sessions: list[str] | None = None,
) -> None:
    sessions = sessions or []

    def fake_which(cmd: str) -> str | None:
        if cmd == "tmux":
            return tmux_path
        return f"/usr/bin/{cmd}"

    def fake_run(cmd: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        if cmd[:3] == ["git", "rev-parse", "--show-toplevel"]:
            return _completed(stdout=str(repo_root))
        if cmd[:3] == ["tmux", "list-sessions", "-F"]:
            return _completed(stdout="\n".join(sessions))
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr("shutil.which", fake_which)
    monkeypatch.setattr("subprocess.run", fake_run)


def test_valid_init_allows_preflight(monkeypatch: Any, tmp_path: Path) -> None:
    _patch_runtime(monkeypatch, tmp_path)
    plan_path = tmp_path / "plan-state.json"
    _save_plan(plan_path)
    init_path = tmp_path / ".fork" / "init.yaml"
    init_path.parent.mkdir()
    init_path.write_text("project_name: tmux_fork\nlanguage: python\n")

    result = ProtocolPreflightService(cwd=tmp_path, plan_state_path=plan_path).run()

    assert result.passed is True
    assert "fork_init_yaml" in result.checked_items
    assert result.bypass_used is False


def test_missing_init_blocks_by_default(monkeypatch: Any, tmp_path: Path) -> None:
    _patch_runtime(monkeypatch, tmp_path)
    plan_path = tmp_path / "plan-state.json"
    _save_plan(plan_path)

    result = ProtocolPreflightService(cwd=tmp_path, plan_state_path=plan_path).run()

    assert result.passed is False
    assert any("Missing .fork/init.yaml" in failure for failure in result.failures)


def test_missing_init_can_be_bypassed_explicitly(monkeypatch: Any, tmp_path: Path) -> None:
    _patch_runtime(monkeypatch, tmp_path)
    plan_path = tmp_path / "plan-state.json"
    _save_plan(plan_path)

    result = ProtocolPreflightService(cwd=tmp_path, plan_state_path=plan_path).run(
        allow_missing_init_bypass=True
    )

    assert result.passed is True
    assert result.bypass_used is True
    assert any("bypass used" in warning for warning in result.warnings)


def test_tmux_missing_blocks(monkeypatch: Any, tmp_path: Path) -> None:
    _patch_runtime(monkeypatch, tmp_path, tmux_path=None)
    plan_path = tmp_path / "plan-state.json"
    _save_plan(plan_path)
    init_path = tmp_path / ".fork" / "init.yaml"
    init_path.parent.mkdir()
    init_path.write_text("project_name: tmux_fork\n")

    result = ProtocolPreflightService(cwd=tmp_path, plan_state_path=plan_path).run()

    assert result.passed is False
    assert any("tmux is not available" in failure for failure in result.failures)


def test_managed_session_limit_blocks(monkeypatch: Any, tmp_path: Path) -> None:
    _patch_runtime(
        monkeypatch,
        tmp_path,
        sessions=["fork-a", "agent-b", "opencode-c", "fork-d", "agent-e"],
    )
    plan_path = tmp_path / "plan-state.json"
    _save_plan(plan_path)
    init_path = tmp_path / ".fork" / "init.yaml"
    init_path.parent.mkdir()
    init_path.write_text("project_name: tmux_fork\n")

    result = ProtocolPreflightService(cwd=tmp_path, plan_state_path=plan_path).run()

    assert result.passed is False
    assert any("Managed tmux session limit reached" in failure for failure in result.failures)


def test_invalid_init_yaml_blocks(monkeypatch: Any, tmp_path: Path) -> None:
    _patch_runtime(monkeypatch, tmp_path)
    plan_path = tmp_path / "plan-state.json"
    _save_plan(plan_path)
    init_path = tmp_path / ".fork" / "init.yaml"
    init_path.parent.mkdir()
    init_path.write_text("project_name: [broken\n")

    result = ProtocolPreflightService(cwd=tmp_path, plan_state_path=plan_path).run()

    assert result.passed is False
    assert any("invalid YAML" in failure for failure in result.failures)


def test_corrupt_plan_state_blocks_with_clear_message(monkeypatch: Any, tmp_path: Path) -> None:
    _patch_runtime(monkeypatch, tmp_path)
    plan_path = tmp_path / "plan-state.json"
    plan_path.write_text("{bad json")
    init_path = tmp_path / ".fork" / "init.yaml"
    init_path.parent.mkdir()
    init_path.write_text("project_name: tmux_fork\n")

    result = ProtocolPreflightService(cwd=tmp_path, plan_state_path=plan_path).run()

    assert result.passed is False
    assert any("Plan state is invalid or corrupt" in failure for failure in result.failures)


def test_invalid_phase_blocks(monkeypatch: Any, tmp_path: Path) -> None:
    _patch_runtime(monkeypatch, tmp_path)
    plan_path = tmp_path / "plan-state.json"
    _save_plan(plan_path, phase=WorkflowPhase.PLANNING)
    init_path = tmp_path / ".fork" / "init.yaml"
    init_path.parent.mkdir()
    init_path.write_text("project_name: tmux_fork\n")

    result = ProtocolPreflightService(cwd=tmp_path, plan_state_path=plan_path).run()

    assert result.passed is False
    assert any("phase does not allow execute" in failure for failure in result.failures)
