"""Workflow state management."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path


class WorkflowPhase(str, Enum):
    PLANNING = "planning"
    OUTLINED = "outlined"
    EXECUTING = "executing"
    EXECUTED = "executed"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    SHIPPING = "shipping"
    SHIPPED = "shipped"


@dataclass(frozen=True)
class Task:
    id: str
    slug: str
    description: str
    status: str = "pending"
    branch: str | None = None
    worktree_path: str | None = None


@dataclass
class PlanState:
    session_id: str
    status: str = "planning"
    phase: WorkflowPhase = WorkflowPhase.PLANNING
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    plan_file: str = ".claude/plans/plan.md"
    tasks: list[Task] = field(default_factory=list)

    def to_json(self) -> dict:
        return {
            "session_id": self.session_id,
            "status": self.status,
            "phase": self.phase.value,
            "started_at": self.started_at,
            "plan_file": self.plan_file,
            "tasks": [
                {
                    "id": t.id,
                    "slug": t.slug,
                    "description": t.description,
                    "status": t.status,
                    "branch": t.branch,
                    "worktree_path": t.worktree_path,
                }
                for t in self.tasks
            ],
        }

    @classmethod
    def from_json(cls, data: dict) -> PlanState:
        tasks = [
            Task(
                id=t["id"],
                slug=t["slug"],
                description=t["description"],
                status=t.get("status", "pending"),
                branch=t.get("branch"),
                worktree_path=t.get("worktree_path"),
            )
            for t in data.get("tasks", [])
        ]
        return cls(
            session_id=data["session_id"],
            status=data.get("status", "planning"),
            phase=WorkflowPhase(data.get("phase", "planning")),
            started_at=data.get("started_at", datetime.utcnow().isoformat() + "Z"),
            plan_file=data.get("plan_file", ".claude/plans/plan.md"),
            tasks=tasks,
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_json(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> PlanState | None:
        if not path.exists():
            return None
        with open(path) as f:
            return cls.from_json(json.load(f))


@dataclass
class ExecuteState:
    session_id: str
    status: str = "idle"
    phase: WorkflowPhase = WorkflowPhase.PLANNING
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    tasks: list[Task] = field(default_factory=list)
    current_task_index: int = 0

    def to_json(self) -> dict:
        return {
            "session_id": self.session_id,
            "status": self.status,
            "phase": self.phase.value,
            "started_at": self.started_at,
            "tasks": [
                {
                    "id": t.id,
                    "slug": t.slug,
                    "description": t.description,
                    "status": t.status,
                    "branch": t.branch,
                    "worktree_path": t.worktree_path,
                }
                for t in self.tasks
            ],
            "current_task_index": self.current_task_index,
        }

    @classmethod
    def from_json(cls, data: dict) -> ExecuteState:
        tasks = [
            Task(
                id=t["id"],
                slug=t["slug"],
                description=t["description"],
                status=t.get("status", "pending"),
                branch=t.get("branch"),
                worktree_path=t.get("worktree_path"),
            )
            for t in data.get("tasks", [])
        ]
        return cls(
            session_id=data["session_id"],
            status=data.get("status", "idle"),
            phase=WorkflowPhase(data.get("phase", "planning")),
            started_at=data.get("started_at", datetime.utcnow().isoformat() + "Z"),
            tasks=tasks,
            current_task_index=data.get("current_task_index", 0),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_json(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> ExecuteState | None:
        if not path.exists():
            return None
        with open(path) as f:
            return cls.from_json(json.load(f))


@dataclass
class VerifyState:
    session_id: str
    status: str = "pending"
    phase: WorkflowPhase = WorkflowPhase.PLANNING
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    unlock_ship: bool = False
    file_hashes: dict[str, str] = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)
    test_results: dict[str, bool] = field(default_factory=dict)

    def to_json(self) -> dict:
        return {
            "session_id": self.session_id,
            "status": self.status,
            "phase": self.phase.value,
            "started_at": self.started_at,
            "unlock_ship": self.unlock_ship,
            "file_hashes": self.file_hashes,
            "evidence": self.evidence,
            "test_results": self.test_results,
        }

    @classmethod
    def from_json(cls, data: dict) -> VerifyState:
        return cls(
            session_id=data["session_id"],
            status=data.get("status", "pending"),
            phase=WorkflowPhase(data.get("phase", "planning")),
            started_at=data.get("started_at", datetime.utcnow().isoformat() + "Z"),
            unlock_ship=data.get("unlock_ship", False),
            file_hashes=data.get("file_hashes", {}),
            evidence=data.get("evidence", []),
            test_results=data.get("test_results", {}),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_json(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> VerifyState | None:
        if not path.exists():
            return None
        with open(path) as f:
            return cls.from_json(json.load(f))


def get_state_dir() -> Path:
    return Path(".claude")


def get_plan_state_path() -> Path:
    return get_state_dir() / "plan-state.json"


def get_execute_state_path() -> Path:
    return get_state_dir() / "execute-state.json"


def get_verify_state_path() -> Path:
    return get_state_dir() / "verify-state.json"
