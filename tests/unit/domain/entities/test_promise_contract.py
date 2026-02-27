"""Tests for PromiseContract entity."""

from __future__ import annotations

from datetime import datetime

import pytest

from src.domain.entities.promise_contract import PromiseContract, PromiseState, VerifyEvidence


class TestVerifyEvidence:
    def test_verify_evidence_creation(self) -> None:
        evidence = VerifyEvidence(
            artifact_path="/path/to/artifact.json",
            passed=True,
            exit_code=0,
            timestamp="2026-02-26T10:00:00",
        )
        assert evidence.artifact_path == "/path/to/artifact.json"
        assert evidence.passed is True
        assert evidence.exit_code == 0
        assert evidence.timestamp == "2026-02-26T10:00:00"

    def test_verify_evidence_immutable(self) -> None:
        evidence = VerifyEvidence(
            artifact_path="/path/to/artifact.json",
            passed=True,
            exit_code=0,
            timestamp="2026-02-26T10:00:00",
        )
        with pytest.raises(AttributeError):
            evidence.passed = False

    def test_verify_evidence_empty_artifact_path_raises(self) -> None:
        with pytest.raises(ValueError, match="artifact_path must be non-empty"):
            VerifyEvidence(
                artifact_path="",
                passed=True,
                exit_code=0,
                timestamp="2026-02-26T10:00:00",
            )

    def test_verify_evidence_empty_timestamp_raises(self) -> None:
        with pytest.raises(ValueError, match="timestamp must be non-empty"):
            VerifyEvidence(
                artifact_path="/path/to/artifact.json",
                passed=True,
                exit_code=0,
                timestamp="",
            )

    def test_verify_evidence_negative_exit_code_raises(self) -> None:
        with pytest.raises(ValueError, match="exit_code must be a non-negative integer"):
            VerifyEvidence(
                artifact_path="/path/to/artifact.json",
                passed=True,
                exit_code=-1,
                timestamp="2026-02-26T10:00:00",
            )

    def test_verify_evidence_non_int_exit_code_raises(self) -> None:
        with pytest.raises(ValueError, match="exit_code must be a non-negative integer"):
            VerifyEvidence(
                artifact_path="/path/to/artifact.json",
                passed=True,
                exit_code=1.5,  # type: ignore[arg-type]
                timestamp="2026-02-26T10:00:00",
            )


class TestPromiseContract:
    def test_promise_contract_creation_minimal(self) -> None:
        contract = PromiseContract(
            id="promise-123",
            session_id="session-456",
            plan_id="plan-789",
            task="Build an API",
            state=PromiseState.CREATED,
        )
        assert contract.id == "promise-123"
        assert contract.session_id == "session-456"
        assert contract.plan_id == "plan-789"
        assert contract.task == "Build an API"
        assert contract.state == PromiseState.CREATED
        assert contract.verify_evidence is None

    def test_promise_contract_creation_full(self) -> None:
        now = datetime.now()
        evidence = VerifyEvidence(
            artifact_path="/path/to/artifact.json",
            passed=True,
            exit_code=0,
            timestamp=now.isoformat(),
        )
        contract = PromiseContract(
            id="promise-123",
            session_id="session-456",
            plan_id="plan-789",
            task="Build an API",
            state=PromiseState.VERIFY_PASSED,
            verify_evidence=evidence,
            created_at=now,
            updated_at=now,
            metadata={"key": "value"},
        )
        assert contract.verify_evidence is not None
        assert contract.verify_evidence.passed is True
        assert contract.metadata == {"key": "value"}

    def test_promise_contract_immutable(self) -> None:
        contract = PromiseContract(
            id="promise-123",
            session_id="session-456",
            plan_id="plan-789",
            task="Build an API",
            state=PromiseState.CREATED,
        )
        with pytest.raises(AttributeError):
            contract.task = "New task"

    def test_promise_contract_empty_id_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            PromiseContract(
                id="",
                session_id="session-456",
                plan_id="plan-789",
                task="Build an API",
                state=PromiseState.CREATED,
            )

    def test_promise_contract_empty_session_id_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            PromiseContract(
                id="promise-123",
                session_id="",
                plan_id="plan-789",
                task="Build an API",
                state=PromiseState.CREATED,
            )

    def test_promise_contract_empty_plan_id_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            PromiseContract(
                id="promise-123",
                session_id="session-456",
                plan_id="",
                task="Build an API",
                state=PromiseState.CREATED,
            )

    def test_promise_contract_empty_task_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            PromiseContract(
                id="promise-123",
                session_id="session-456",
                plan_id="plan-789",
                task="",
                state=PromiseState.CREATED,
            )

    def test_promise_contract_invalid_id_type_raises(self) -> None:
        with pytest.raises(TypeError, match="id must be a string"):
            PromiseContract(
                id=123,  # type: ignore[arg-type]
                session_id="session-456",
                plan_id="plan-789",
                task="Build an API",
                state=PromiseState.CREATED,
            )

    def test_promise_contract_invalid_session_id_type_raises(self) -> None:
        with pytest.raises(TypeError, match="session_id must be a string"):
            PromiseContract(
                id="promise-123",
                session_id=456,  # type: ignore[arg-type]
                plan_id="plan-789",
                task="Build an API",
                state=PromiseState.CREATED,
            )

    def test_promise_contract_invalid_plan_id_type_raises(self) -> None:
        with pytest.raises(TypeError, match="plan_id must be a string"):
            PromiseContract(
                id="promise-123",
                session_id="session-456",
                plan_id=789,  # type: ignore[arg-type]
                task="Build an API",
                state=PromiseState.CREATED,
            )

    def test_promise_contract_invalid_task_type_raises(self) -> None:
        with pytest.raises(TypeError, match="task must be a string"):
            PromiseContract(
                id="promise-123",
                session_id="session-456",
                plan_id="plan-789",
                task=123,  # type: ignore[arg-type]
                state=PromiseState.CREATED,
            )

    def test_promise_contract_invalid_state_type_raises(self) -> None:
        with pytest.raises(TypeError, match="state must be a PromiseState enum"):
            PromiseContract(
                id="promise-123",
                session_id="session-456",
                plan_id="plan-789",
                task="Build an API",
                state="created",  # type: ignore[arg-type]
            )

    def test_promise_contract_invalid_verify_evidence_type_raises(self) -> None:
        with pytest.raises(TypeError, match="verify_evidence must be a VerifyEvidence"):
            PromiseContract(
                id="promise-123",
                session_id="session-456",
                plan_id="plan-789",
                task="Build an API",
                state=PromiseState.CREATED,
                verify_evidence="invalid",  # type: ignore[arg-type]
            )

    def test_promise_contract_invalid_created_at_type_raises(self) -> None:
        with pytest.raises(TypeError, match="created_at must be a datetime"):
            PromiseContract(
                id="promise-123",
                session_id="session-456",
                plan_id="plan-789",
                task="Build an API",
                state=PromiseState.CREATED,
                created_at="invalid",  # type: ignore[arg-type]
            )

    def test_promise_contract_invalid_updated_at_type_raises(self) -> None:
        with pytest.raises(TypeError, match="updated_at must be a datetime"):
            PromiseContract(
                id="promise-123",
                session_id="session-456",
                plan_id="plan-789",
                task="Build an API",
                state=PromiseState.CREATED,
                updated_at="invalid",  # type: ignore[arg-type]
            )

    def test_promise_contract_invalid_metadata_type_raises(self) -> None:
        with pytest.raises(TypeError, match="metadata must be a dictionary"):
            PromiseContract(
                id="promise-123",
                session_id="session-456",
                plan_id="plan-789",
                task="Build an API",
                state=PromiseState.CREATED,
                metadata="invalid",  # type: ignore[arg-type]
            )


class TestPromiseStateTransitions:
    def test_can_transition_created_to_running(self) -> None:
        contract = PromiseContract(
            id="promise-123",
            session_id="session-456",
            plan_id="plan-789",
            task="Build an API",
            state=PromiseState.CREATED,
        )
        assert contract.can_transition_to(PromiseState.RUNNING) is True

    def test_can_transition_created_to_failed(self) -> None:
        contract = PromiseContract(
            id="promise-123",
            session_id="session-456",
            plan_id="plan-789",
            task="Build an API",
            state=PromiseState.CREATED,
        )
        assert contract.can_transition_to(PromiseState.FAILED) is True

    def test_cannot_transition_created_to_shipped(self) -> None:
        contract = PromiseContract(
            id="promise-123",
            session_id="session-456",
            plan_id="plan-789",
            task="Build an API",
            state=PromiseState.CREATED,
        )
        assert contract.can_transition_to(PromiseState.SHIPPED) is False

    def test_can_transition_running_to_verify_passed(self) -> None:
        contract = PromiseContract(
            id="promise-123",
            session_id="session-456",
            plan_id="plan-789",
            task="Build an API",
            state=PromiseState.RUNNING,
        )
        assert contract.can_transition_to(PromiseState.VERIFY_PASSED) is True

    def test_can_transition_running_to_verify_failed(self) -> None:
        contract = PromiseContract(
            id="promise-123",
            session_id="session-456",
            plan_id="plan-789",
            task="Build an API",
            state=PromiseState.RUNNING,
        )
        assert contract.can_transition_to(PromiseState.VERIFY_FAILED) is True

    def test_can_transition_verify_passed_to_shipped(self) -> None:
        contract = PromiseContract(
            id="promise-123",
            session_id="session-456",
            plan_id="plan-789",
            task="Build an API",
            state=PromiseState.VERIFY_PASSED,
        )
        assert contract.can_transition_to(PromiseState.SHIPPED) is True

    def test_cannot_transition_shipped_to_any(self) -> None:
        contract = PromiseContract(
            id="promise-123",
            session_id="session-456",
            plan_id="plan-789",
            task="Build an API",
            state=PromiseState.SHIPPED,
        )
        assert contract.can_transition_to(PromiseState.RUNNING) is False
        assert contract.can_transition_to(PromiseState.FAILED) is False

    def test_transition_to_valid(self) -> None:
        contract = PromiseContract(
            id="promise-123",
            session_id="session-456",
            plan_id="plan-789",
            task="Build an API",
            state=PromiseState.CREATED,
        )
        # Evidence is only kept for verification states, not RUNNING
        new_contract = contract.transition_to(PromiseState.RUNNING)
        assert new_contract.state == PromiseState.RUNNING
        assert new_contract.verify_evidence is None  # No evidence for non-verification states
        assert new_contract.id == contract.id
        assert new_contract.plan_id == contract.plan_id

    def test_transition_to_invalid_raises(self) -> None:
        contract = PromiseContract(
            id="promise-123",
            session_id="session-456",
            plan_id="plan-789",
            task="Build an API",
            state=PromiseState.CREATED,
        )
        with pytest.raises(ValueError, match="Cannot transition"):
            contract.transition_to(PromiseState.SHIPPED)

    def test_transition_to_verify_passed_requires_evidence(self) -> None:
        contract = PromiseContract(
            id="promise-123",
            session_id="session-456",
            plan_id="plan-789",
            task="Build an API",
            state=PromiseState.RUNNING,
        )
        with pytest.raises(ValueError, match="Evidence required for transition to verify_passed"):
            contract.transition_to(PromiseState.VERIFY_PASSED)

    def test_transition_to_verify_failed_requires_evidence(self) -> None:
        contract = PromiseContract(
            id="promise-123",
            session_id="session-456",
            plan_id="plan-789",
            task="Build an API",
            state=PromiseState.RUNNING,
        )
        with pytest.raises(ValueError, match="Evidence required for transition to verify_failed"):
            contract.transition_to(PromiseState.VERIFY_FAILED)

    def test_transition_to_verify_passed_with_evidence(self) -> None:
        contract = PromiseContract(
            id="promise-123",
            session_id="session-456",
            plan_id="plan-789",
            task="Build an API",
            state=PromiseState.RUNNING,
        )
        evidence = VerifyEvidence(
            artifact_path="/path/to/artifact.json",
            passed=True,
            exit_code=0,
            timestamp="2026-02-26T10:00:00",
        )
        new_contract = contract.transition_to(PromiseState.VERIFY_PASSED, evidence)
        assert new_contract.state == PromiseState.VERIFY_PASSED
        assert new_contract.verify_evidence == evidence

    def test_transition_to_shipped_clears_evidence(self) -> None:
        evidence = VerifyEvidence(
            artifact_path="/path/to/artifact.json",
            passed=True,
            exit_code=0,
            timestamp="2026-02-26T10:00:00",
        )
        contract = PromiseContract(
            id="promise-123",
            session_id="session-456",
            plan_id="plan-789",
            task="Build an API",
            state=PromiseState.VERIFY_PASSED,
            verify_evidence=evidence,
        )
        new_contract = contract.transition_to(PromiseState.SHIPPED)
        assert new_contract.state == PromiseState.SHIPPED
        assert new_contract.verify_evidence is None  # Evidence cleared for non-verification states
