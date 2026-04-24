"""Minimal protocol preflight for workflow execution.

This gate is intentionally small. It does not make the full
``tmux-fork-orchestrator`` protocol authoritative; it only blocks obviously
unsafe workflow execution before agent spawn.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from src.application.services.workflow.state import PlanState, WorkflowPhase

MANAGED_SESSION_PREFIXES = ("fork-", "agent-", "opencode-")
MAX_MANAGED_SESSIONS = 5


@dataclass(frozen=True)
class ProtocolPreflightResult:
    """Structured result for the workflow protocol preflight."""

    passed: bool
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checked_items: list[str] = field(default_factory=list)
    bypass_used: bool = False


class ProtocolPreflightService:
    """Fail-closed preflight checks before workflow agent spawn."""

    def __init__(
        self,
        *,
        cwd: Path | None = None,
        plan_state_path: Path | None = None,
        max_managed_sessions: int = MAX_MANAGED_SESSIONS,
    ) -> None:
        self._cwd = cwd or Path.cwd()
        self._plan_state_path = plan_state_path
        self._max_managed_sessions = max_managed_sessions

    def run(self, *, allow_missing_init_bypass: bool = False) -> ProtocolPreflightResult:
        """Run minimal preflight checks.

        Args:
            allow_missing_init_bypass: Transitional bypass for missing
                ``.fork/init.yaml`` only. Other failures remain fail-closed.
        """
        failures: list[str] = []
        warnings: list[str] = []
        checked: list[str] = []
        bypass_used = False

        repo_root = self._resolve_repo_root(failures, checked)
        self._check_tmux_available(failures, checked)
        self._check_plan_state(failures, checked)
        if repo_root is not None:
            init_result = self._check_fork_init_yaml(repo_root, failures, warnings, checked)
            if init_result == "missing" and allow_missing_init_bypass:
                failures.remove("Missing .fork/init.yaml; run fork init before workflow execute.")
                warnings.append(
                    "Protocol gate bypass used: missing .fork/init.yaml was allowed by "
                    "--no-protocol-gate."
                )
                bypass_used = True
        self._check_managed_session_limit(failures, checked)

        return ProtocolPreflightResult(
            passed=not failures,
            failures=failures,
            warnings=warnings,
            checked_items=checked,
            bypass_used=bypass_used,
        )

    def _resolve_repo_root(self, failures: list[str], checked: list[str]) -> Path | None:
        checked.append("repo_root")
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=self._cwd,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            failures.append(f"Cannot resolve git repository root: {exc}")
            return None

        if result.returncode != 0 or not result.stdout.strip():
            stderr = result.stderr.strip() or "not a git repository"
            failures.append(f"Cannot resolve git repository root: {stderr}")
            return None
        return Path(result.stdout.strip())

    def _check_tmux_available(self, failures: list[str], checked: list[str]) -> None:
        checked.append("tmux_available")
        if shutil.which("tmux") is None:
            failures.append("tmux is not available on PATH; workflow execute cannot spawn agents.")

    def _check_plan_state(self, failures: list[str], checked: list[str]) -> None:
        checked.append("workflow_state")
        if self._plan_state_path is None:
            failures.append("Plan state path was not provided to protocol preflight.")
            return

        try:
            plan = PlanState.load(self._plan_state_path)
        except Exception as exc:
            failures.append(f"Plan state is invalid or corrupt: {exc}")
            return

        if plan is None:
            failures.append("No plan state found. Run 'memory workflow outline' first.")
            return

        if plan.phase not in (WorkflowPhase.OUTLINED, WorkflowPhase.EXECUTED):
            failures.append(
                "Plan state phase does not allow execute: "
                f"current={plan.phase.value}, allowed=outlined,executed."
            )

    def _check_fork_init_yaml(
        self,
        repo_root: Path,
        failures: list[str],
        warnings: list[str],
        checked: list[str],
    ) -> str:
        checked.append("fork_init_yaml")
        init_path = repo_root / ".fork" / "init.yaml"
        if not init_path.exists():
            failures.append("Missing .fork/init.yaml; run fork init before workflow execute.")
            return "missing"

        try:
            with init_path.open() as f:
                yaml.safe_load(f)
        except yaml.YAMLError as exc:
            failures.append(f".fork/init.yaml is invalid YAML: {exc}")
            return "invalid"
        except OSError as exc:
            failures.append(f"Cannot read .fork/init.yaml: {exc}")
            return "invalid"

        warnings.append(".fork/init.yaml detected and parsed; treated as preflight signal only.")
        return "valid"

    def _check_managed_session_limit(self, failures: list[str], checked: list[str]) -> None:
        checked.append("managed_tmux_session_limit")
        if shutil.which("tmux") is None:
            return

        try:
            result = subprocess.run(
                ["tmux", "list-sessions", "-F", "#{session_name}"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            failures.append(f"Cannot count managed tmux sessions: {exc}")
            return

        if result.returncode != 0:
            stderr = result.stderr.lower()
            if "no server running" in stderr or "failed to connect" in stderr:
                return
            failures.append(f"Cannot count managed tmux sessions: {result.stderr.strip()}")
            return

        session_names = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        managed = [s for s in session_names if s.startswith(MANAGED_SESSION_PREFIXES)]
        if len(managed) >= self._max_managed_sessions:
            failures.append(
                f"Managed tmux session limit reached: {len(managed)} active "
                f"(max {self._max_managed_sessions}). Cleanup before workflow execute."
            )
