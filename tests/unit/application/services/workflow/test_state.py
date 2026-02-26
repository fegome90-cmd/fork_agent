"""Tests for workflow state versioning and migration."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.application.services.workflow.state import (
    CURRENT_SCHEMA_VERSION,
    ExecuteState,
    InvalidStateError,
    PlanState,
    UnsupportedSchemaError,
    VerifyState,
)


class TestPlanStateVersioning:
    """Tests for PlanState schema versioning."""

    def test_new_state_has_schema_version(self) -> None:
        """Newly created state should have current schema version."""
        state = PlanState(session_id="test-session")
        assert state.schema_version == CURRENT_SCHEMA_VERSION
        assert state.migrated_from is None

    def test_to_json_includes_schema_version(self) -> None:
        """to_json() should include schema_version field."""
        state = PlanState(session_id="test-session")
        data = state.to_json()
        assert "schema_version" in data
        assert data["schema_version"] == CURRENT_SCHEMA_VERSION

    def test_from_json_v1_loads_correctly(self) -> None:
        """Loading v1 state should be migrated to v2."""
        data = {
            "session_id": "test-session",
            "status": "planning",
            "phase": "planning",
            "schema_version": 1,
            "tasks": [],
        }
        state = PlanState.from_json(data)
        assert state.schema_version == 3
        assert state.migrated_from == 1

    def test_from_json_v0_migrates_to_v3(self) -> None:
        """Legacy v0 state should be migrated to v3."""
        """Legacy v0 state should be migrated to v2."""
        data = {
            "session_id": "test-session",
            "status": "planning",
            "phase": "planning",
            # No schema_version field = v0
            "tasks": [],
        }
        state = PlanState.from_json(data)
        assert state.schema_version == 3
        assert state.migrated_from == 0

    def test_from_json_unknown_future_version_raises(self) -> None:
        """Loading state with future version should fail."""
        data = {
            "session_id": "test-session",
            "schema_version": 999,
            "tasks": [],
        }
        with pytest.raises(UnsupportedSchemaError) as exc_info:
            PlanState.from_json(data)
        assert "not supported" in str(exc_info.value)

    def test_load_corrupt_json_raises(self) -> None:
        """Loading corrupt JSON should raise InvalidStateError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json")
            f.flush()
            path = Path(f.name)

        try:
            with pytest.raises(InvalidStateError) as exc_info:
                PlanState.load(path)
            assert "invalid JSON" in str(exc_info.value)
        finally:
            path.unlink()

    def test_load_missing_session_id_raises(self) -> None:
        """Loading state without session_id should raise InvalidStateError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"status": "planning"}, f)
            f.flush()
            path = Path(f.name)

        try:
            with pytest.raises(InvalidStateError) as exc_info:
                PlanState.load(path)
            assert "missing required field" in str(exc_info.value)
        finally:
            path.unlink()

    def test_load_non_dict_raises(self) -> None:
        """Loading non-dict JSON should raise InvalidStateError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(["not", "a", "dict"], f)
            f.flush()
            path = Path(f.name)

        try:
            with pytest.raises(InvalidStateError) as exc_info:
                PlanState.load(path)
            assert "expected dict" in str(exc_info.value)
        finally:
            path.unlink()

    def test_load_nonexistent_returns_none(self) -> None:
        """Loading nonexistent file should return None."""
        result = PlanState.load(Path("/nonexistent/path.json"))
        assert result is None

    def test_save_and_load_roundtrip(self) -> None:
        """Save and load should produce equivalent state."""
        state = PlanState(
            session_id="test-session",
            status="outlined",
            tasks=[],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "plan-state.json"
            state.save(path)
            loaded = PlanState.load(path)

        assert loaded is not None
        assert loaded.session_id == state.session_id
        assert loaded.status == state.status
        assert loaded.schema_version == state.schema_version

    def test_decisions_field(self) -> None:
        """Test that decisions field works correctly."""
        from src.domain.entities.user_decision import DecisionStatus

        state = PlanState(session_id="test-session")
        # New state should have empty decisions
        assert state.decisions == {}

        # Test add_decision method
        new_state = state.add_decision(
            key="test-key",
            value="test-value",
            status=DecisionStatus.LOCKED,
            rationale="Test rationale",
        )
        assert "test-key" in new_state.decisions
        assert new_state.decisions["test-key"].value == "test-value"


class TestExecuteStateVersioning:
    """Tests for ExecuteState schema versioning."""

    def test_new_state_has_schema_version(self) -> None:
        """Newly created state should have current schema version."""
        state = ExecuteState(session_id="test-session")
        assert state.schema_version == CURRENT_SCHEMA_VERSION

    def test_from_json_v0_migrates(self) -> None:
        """Legacy v0 state should be migrated to v3."""
        """Legacy v0 state should be migrated to v2."""
        data = {"session_id": "test", "schema_version": None, "tasks": []}
        state = ExecuteState.from_json(data)
        assert state.schema_version == 3
        assert state.migrated_from == 0


class TestVerifyStateVersioning:
    """Tests for VerifyState schema versioning."""

    def test_new_state_has_schema_version(self) -> None:
        """Newly created state should have current schema version."""
        state = VerifyState(session_id="test-session")
        assert state.schema_version == CURRENT_SCHEMA_VERSION

    def test_from_json_v0_migrates(self) -> None:
        """Legacy v0 state should be migrated to v3."""
        """Legacy v0 state should be migrated to v2."""
        data = {"session_id": "test", "schema_version": None, "tasks": []}
        state = VerifyState.from_json(data)
        assert state.schema_version == 3
        assert state.migrated_from == 0
