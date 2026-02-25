"""Workflow state management.

State Schema Versioning:
- v3 (current): Includes goal and derived_requirements in PlanState
- v2 (legacy): Includes decisions field in PlanState
- v1 (legacy): No decisions field - auto-migrated on load
- v0 (legacy): No schema_version field - auto-migrated on load
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

from src.domain.entities.derived_requirement import (
    DerivedRequirement,
    RequirementPriority,
    RequirementSource,
)
from src.domain.entities.goal import Goal
from src.domain.entities.user_decision import DecisionStatus, UserDecision

import json

CURRENT_SCHEMA_VERSION = 3


class StateError(Exception):
    """Base exception for state loading errors."""


class InvalidStateError(StateError):
    """Raised when state is invalid or corrupt."""


class UnsupportedSchemaError(StateError):
    """Raised when schema version is not supported."""


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
    session_name: str | None = None
    agent_pid: int | None = None
    depends_on: tuple[str, ...] = ()
    requirement_ids: tuple[str, ...] = ()


@dataclass
class PlanState:
    session_id: str
    status: str = "planning"
    phase: WorkflowPhase = WorkflowPhase.PLANNING
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    plan_file: str = ".claude/plans/plan.md"
    tasks: list[Task] = field(default_factory=list)
    decisions: dict[str, UserDecision] = field(default_factory=dict)
    goal: Goal | None = None
    derived_requirements: tuple[DerivedRequirement, ...] = ()
    schema_version: int = CURRENT_SCHEMA_VERSION
    migrated_from: int | None = None

    def to_json(self) -> dict:
        return {
            "session_id": self.session_id,
            "status": self.status,
            "phase": self.phase.value,
            "started_at": self.started_at,
            "plan_file": self.plan_file,
            "schema_version": self.schema_version,
            "migrated_from": self.migrated_from,
            "tasks": [
                {
                    "id": t.id,
                    "slug": t.slug,
                    "description": t.description,
                    "status": t.status,
                    "branch": t.branch,
                    "worktree_path": t.worktree_path,
                    "session_name": t.session_name,
                    "agent_pid": t.agent_pid,
                    "depends_on": list(t.depends_on),
                    "requirement_ids": list(t.requirement_ids),
                }
                for t in self.tasks
            ],
            "decisions": {
                k: {
                    "key": d.key,
                    "value": d.value,
                    "status": d.status.value,
                    "rationale": d.rationale,
                }
                for k, d in self.decisions.items()
            },
            "goal": {
                "objective": self.goal.objective,
                "must_haves": list(self.goal.must_haves),
                "nice_to_haves": list(self.goal.nice_to_haves),
                "scope_in": list(self.goal.scope_in),
                "scope_out": list(self.goal.scope_out),
            }
            if self.goal
            else None,
            "derived_requirements": [
                {
                    "id": r.id,
                    "description": r.description,
                    "source": r.source.value,
                    "priority": r.priority.value,
                }
                for r in self.derived_requirements
            ],
        }

    @classmethod
    def from_json(cls, data: dict) -> PlanState:
        # Detect legacy state (v0) - no schema_version field
        schema_version = data.get("schema_version")
        if schema_version is None:
            schema_version = 0  # Legacy state

        # Fail-closed for unknown future versions
        if schema_version > CURRENT_SCHEMA_VERSION:
            raise UnsupportedSchemaError(
                f"PlanState schema version {schema_version} is not supported. "
                f"Maximum supported version is {CURRENT_SCHEMA_VERSION}."
            )

        # Migration tracking
        migrated_from: int | None = None

        # Migration: v0 -> v1
        if schema_version == 0:
            migrated_from = 0

        # Migration: v1 -> v2 (add decisions field)
        if schema_version == 1:
            migrated_from = 1

        # Migration: v2 -> v3 (add goal and derived_requirements)
        if schema_version == 2:
            migrated_from = 2

        schema_version = 3  # Always use current version

        # Parse tasks with new fields
        tasks = [
            Task(
                id=t["id"],
                slug=t["slug"],
                description=t["description"],
                status=t.get("status", "pending"),
                branch=t.get("branch"),
                worktree_path=t.get("worktree_path"),
                session_name=t.get("session_name"),
                agent_pid=t.get("agent_pid"),
                depends_on=tuple(t.get("depends_on", [])),
                requirement_ids=tuple(t.get("requirement_ids", [])),
            )
            for t in data.get("tasks", [])
        ]

        # Parse decisions (new in v2)
        decisions: dict[str, UserDecision] = {}
        decisions_data = data.get("decisions", {})
        for k, d in decisions_data.items():
            decisions[k] = UserDecision(
                key=d["key"],
                value=d["value"],
                status=DecisionStatus(d["status"]),
                rationale=d.get("rationale"),
            )

        # Parse goal (new in v3)
        goal: Goal | None = None
        goal_data = data.get("goal")
        if goal_data:
            goal = Goal(
                objective=goal_data["objective"],
                must_haves=tuple(goal_data.get("must_haves", [])),
                nice_to_haves=tuple(goal_data.get("nice_to_haves", [])),
                scope_in=tuple(goal_data.get("scope_in", [])),
                scope_out=tuple(goal_data.get("scope_out", [])),
            )

        # Parse derived_requirements (new in v3)
        derived_requirements: tuple[DerivedRequirement, ...] = ()
        req_data = data.get("derived_requirements", [])
        if req_data:
            derived_requirements = tuple(
                DerivedRequirement(
                    id=r["id"],
                    description=r["description"],
                    source=RequirementSource(r["source"]),
                    priority=RequirementPriority(r["priority"]),
                )
                for r in req_data
            )

        return cls(
            session_id=data["session_id"],
            status=data.get("status", "planning"),
            phase=WorkflowPhase(data.get("phase", "planning")),
            started_at=data.get("started_at", datetime.utcnow().isoformat() + "Z"),
            plan_file=data.get("plan_file", ".claude/plans/plan.md"),
            tasks=tasks,
            decisions=decisions,
            goal=goal,
            derived_requirements=derived_requirements,
            schema_version=schema_version,
            migrated_from=migrated_from,
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_json(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> PlanState | None:
        if not path.exists():
            return None
        try:
            with open(path) as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise InvalidStateError(f"PlanState: expected dict, got {type(data).__name__}")
            if "session_id" not in data:
                raise InvalidStateError("PlanState: missing required field 'session_id'")
            return cls.from_json(data)
        except json.JSONDecodeError as e:
            raise InvalidStateError(f"PlanState: invalid JSON - {e}") from e

    def add_decision(
        self, key: str, value: str, status: DecisionStatus, rationale: str | None = None
    ) -> PlanState:
        """Create a new PlanState with an added decision."""
        new_decisions = dict(self.decisions)
        new_decisions[key] = UserDecision(key=key, value=value, status=status, rationale=rationale)
        return PlanState(
            session_id=self.session_id,
            status=self.status,
            phase=self.phase,
            started_at=self.started_at,
            plan_file=self.plan_file,
            tasks=self.tasks,
            decisions=new_decisions,
            goal=self.goal,
            derived_requirements=self.derived_requirements,
            schema_version=self.schema_version,
            migrated_from=self.migrated_from,
        )

    def get_decision(self, key: str) -> UserDecision | None:
        """Get a decision by key."""
        return self.decisions.get(key)


@dataclass
class ExecuteState:
    session_id: str
    status: str = "idle"
    phase: WorkflowPhase = WorkflowPhase.PLANNING
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    tasks: list[Task] = field(default_factory=list)
    current_task_index: int = 0
    schema_version: int = CURRENT_SCHEMA_VERSION
    migrated_from: int | None = None

    def to_json(self) -> dict:
        return {
            "session_id": self.session_id,
            "status": self.status,
            "phase": self.phase.value,
            "started_at": self.started_at,
            "schema_version": self.schema_version,
            "migrated_from": self.migrated_from,
            "tasks": [
                {
                    "id": t.id,
                    "slug": t.slug,
                    "description": t.description,
                    "status": t.status,
                    "branch": t.branch,
                    "worktree_path": t.worktree_path,
                    "session_name": t.session_name,
                    "agent_pid": t.agent_pid,
                    "depends_on": list(t.depends_on),
                    "requirement_ids": list(t.requirement_ids),
                }
                for t in self.tasks
            ],
            "current_task_index": self.current_task_index,
        }

    @classmethod
    def from_json(cls, data: dict) -> ExecuteState:
        schema_version = data.get("schema_version")
        if schema_version is None:
            schema_version = 0

        if schema_version > CURRENT_SCHEMA_VERSION:
            raise UnsupportedSchemaError(
                f"ExecuteState schema version {schema_version} is not supported. "
                f"Maximum supported version is {CURRENT_SCHEMA_VERSION}."
            )

        migrated_from: int | None = None
        if schema_version == 0:
            migrated_from = 0
            schema_version = 3

        tasks = [
            Task(
                id=t["id"],
                slug=t["slug"],
                description=t["description"],
                status=t.get("status", "pending"),
                branch=t.get("branch"),
                worktree_path=t.get("worktree_path"),
                session_name=t.get("session_name"),
                agent_pid=t.get("agent_pid"),
                depends_on=tuple(t.get("depends_on", [])),
                requirement_ids=tuple(t.get("requirement_ids", [])),
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
            schema_version=schema_version,
            migrated_from=migrated_from,
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_json(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> ExecuteState | None:
        if not path.exists():
            return None
        try:
            with open(path) as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise InvalidStateError(f"ExecuteState: expected dict, got {type(data).__name__}")
            if "session_id" not in data:
                raise InvalidStateError("ExecuteState: missing required field 'session_id'")
            return cls.from_json(data)
        except json.JSONDecodeError as e:
            raise InvalidStateError(f"ExecuteState: invalid JSON - {e}") from e


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
    schema_version: int = CURRENT_SCHEMA_VERSION
    migrated_from: int | None = None

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
            "schema_version": self.schema_version,
            "migrated_from": self.migrated_from,
        }

    @classmethod
    def from_json(cls, data: dict) -> VerifyState:
        schema_version = data.get("schema_version")
        if schema_version is None:
            schema_version = 0

        if schema_version > CURRENT_SCHEMA_VERSION:
            raise UnsupportedSchemaError(
                f"VerifyState schema version {schema_version} is not supported. "
                f"Maximum supported version is {CURRENT_SCHEMA_VERSION}."
            )

        migrated_from: int | None = None
        if schema_version == 0:
            migrated_from = 0
            schema_version = 3

        return cls(
            session_id=data["session_id"],
            status=data.get("status", "pending"),
            phase=WorkflowPhase(data.get("phase", "planning")),
            started_at=data.get("started_at", datetime.utcnow().isoformat() + "Z"),
            unlock_ship=data.get("unlock_ship", False),
            file_hashes=data.get("file_hashes", {}),
            evidence=data.get("evidence", []),
            test_results=data.get("test_results", {}),
            schema_version=schema_version,
            migrated_from=migrated_from,
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_json(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> VerifyState | None:
        if not path.exists():
            return None
        try:
            with open(path) as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise InvalidStateError(f"VerifyState: expected dict, got {type(data).__name__}")
            if "session_id" not in data:
                raise InvalidStateError("VerifyState: missing required field 'session_id'")
            return cls.from_json(data)
        except json.JSONDecodeError as e:
            raise InvalidStateError(f"VerifyState: invalid JSON - {e}") from e


def get_state_dir() -> Path:
    return Path(".claude")


def get_plan_state_path() -> Path:
    return get_state_dir() / "plan-state.json"


def get_execute_state_path() -> Path:
    return get_state_dir() / "execute-state.json"


def get_verify_state_path() -> Path:
    return get_state_dir() / "verify-state.json"
