"""Tests for PromiseContractRepository."""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from src.application.exceptions import RepositoryError
from src.domain.entities.promise_contract import PromiseContract, PromiseState, VerifyEvidence
from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
from src.infrastructure.persistence.repositories.promise_repository import (
    PromiseContractRepository,
)


@pytest.fixture
def db_connection() -> DatabaseConnection:
    """Create a temporary database with promise_contracts schema."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        config = DatabaseConfig(db_path=db_path)
        conn = DatabaseConnection(config)

        with conn as c:
            c.execute(
                """CREATE TABLE promise_contracts (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    plan_id TEXT NOT NULL UNIQUE,
                    task TEXT NOT NULL,
                    state TEXT NOT NULL CHECK(state IN (
                        'created', 'running', 'verify_passed', 'verify_failed', 'shipped', 'failed'
                    )),
                    verify_evidence TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    metadata TEXT
                )"""
            )

        yield conn


@pytest.fixture
def repository(db_connection: DatabaseConnection) -> PromiseContractRepository:
    """Create repository with test database."""
    return PromiseContractRepository(db_connection)


@pytest.fixture
def sample_contract() -> PromiseContract:
    now = datetime(2026, 2, 26, 10, 0, 0)
    return PromiseContract(
        id="promise-abc123",
        session_id="session-001",
        plan_id="plan-xyz",
        task="Build feature X",
        state=PromiseState.CREATED,
        created_at=now,
        updated_at=now,
        metadata={"key": "value"},
    )


class TestPromiseContractRepositorySave:
    def test_save_contract_success(
        self, repository: PromiseContractRepository, sample_contract: PromiseContract
    ) -> None:
        result = repository.save(sample_contract)
        assert result.id == sample_contract.id
        assert result.plan_id == sample_contract.plan_id

    def test_save_contract_persisted(
        self, repository: PromiseContractRepository, sample_contract: PromiseContract
    ) -> None:
        repository.save(sample_contract)
        retrieved = repository.get_by_id(sample_contract.id)
        assert retrieved is not None
        assert retrieved.id == sample_contract.id
        assert retrieved.state == PromiseState.CREATED

    def test_save_contract_with_verify_evidence(
        self, repository: PromiseContractRepository
    ) -> None:
        now = datetime(2026, 2, 26, 10, 0, 0)
        evidence = VerifyEvidence(
            artifact_path="/path/artifact.json",
            passed=True,
            exit_code=0,
            timestamp=now,
        )
        contract = PromiseContract(
            id="promise-evidence",
            session_id="session-001",
            plan_id="plan-evidence",
            task="Build feature",
            state=PromiseState.VERIFY_PASSED,
            verify_evidence=evidence,
            created_at=now,
            updated_at=now,
        )
        repository.save(contract)
        retrieved = repository.get_by_id("promise-evidence")
        assert retrieved is not None
        assert retrieved.verify_evidence is not None
        assert retrieved.verify_evidence.passed is True
        assert retrieved.verify_evidence.artifact_path == "/path/artifact.json"
        assert retrieved.verify_evidence.timestamp == now

    def test_save_duplicate_id_raises_error(
        self, repository: PromiseContractRepository, sample_contract: PromiseContract
    ) -> None:
        repository.save(sample_contract)
        with pytest.raises(RepositoryError, match="already exists"):
            repository.save(sample_contract)

    def test_save_duplicate_plan_id_raises_error(
        self, repository: PromiseContractRepository, sample_contract: PromiseContract
    ) -> None:
        repository.save(sample_contract)
        duplicate = PromiseContract(
            id="promise-different-id",
            session_id="session-001",
            plan_id=sample_contract.plan_id,
            task="Another task",
            state=PromiseState.CREATED,
        )
        with pytest.raises(RepositoryError):
            repository.save(duplicate)


class TestPromiseContractRepositoryGetById:
    def test_get_existing_contract(
        self, repository: PromiseContractRepository, sample_contract: PromiseContract
    ) -> None:
        repository.save(sample_contract)
        result = repository.get_by_id(sample_contract.id)
        assert result is not None
        assert result.id == sample_contract.id
        assert result.task == sample_contract.task

    def test_get_nonexistent_contract_returns_none(
        self, repository: PromiseContractRepository
    ) -> None:
        result = repository.get_by_id("non-existent")
        assert result is None

    def test_get_contract_preserves_metadata(
        self, repository: PromiseContractRepository, sample_contract: PromiseContract
    ) -> None:
        repository.save(sample_contract)
        result = repository.get_by_id(sample_contract.id)
        assert result is not None
        assert result.metadata == {"key": "value"}


class TestPromiseContractRepositoryGetByPlanId:
    def test_get_by_plan_id_success(
        self, repository: PromiseContractRepository, sample_contract: PromiseContract
    ) -> None:
        repository.save(sample_contract)
        result = repository.get_by_plan_id(sample_contract.plan_id)
        assert result is not None
        assert result.plan_id == sample_contract.plan_id

    def test_get_by_plan_id_not_found(self, repository: PromiseContractRepository) -> None:
        result = repository.get_by_plan_id("non-existent-plan")
        assert result is None


class TestPromiseContractRepositoryGetBySessionId:
    def test_get_by_session_id_returns_all(
        self, repository: PromiseContractRepository
    ) -> None:
        now = datetime(2026, 2, 26, 10, 0, 0)
        contract1 = PromiseContract(
            id="promise-1",
            session_id="session-A",
            plan_id="plan-1",
            task="Task 1",
            state=PromiseState.CREATED,
            created_at=now,
        )
        contract2 = PromiseContract(
            id="promise-2",
            session_id="session-A",
            plan_id="plan-2",
            task="Task 2",
            state=PromiseState.RUNNING,
            created_at=now,
        )
        contract3 = PromiseContract(
            id="promise-3",
            session_id="session-B",
            plan_id="plan-3",
            task="Task 3",
            state=PromiseState.CREATED,
            created_at=now,
        )
        repository.save(contract1)
        repository.save(contract2)
        repository.save(contract3)

        results = repository.get_by_session_id("session-A")
        assert len(results) == 2
        ids = {r.id for r in results}
        assert ids == {"promise-1", "promise-2"}

    def test_get_by_session_id_empty(self, repository: PromiseContractRepository) -> None:
        results = repository.get_by_session_id("non-existent-session")
        assert results == []


class TestPromiseContractRepositoryUpdateState:
    def test_update_state_valid_transition(
        self, repository: PromiseContractRepository, sample_contract: PromiseContract
    ) -> None:
        repository.save(sample_contract)
        updated = repository.update_state(sample_contract.id, PromiseState.RUNNING)
        assert updated.state == PromiseState.RUNNING

    def test_update_state_invalid_transition_raises(
        self, repository: PromiseContractRepository, sample_contract: PromiseContract
    ) -> None:
        repository.save(sample_contract)
        with pytest.raises(RepositoryError, match="Invalid state transition"):
            repository.update_state(sample_contract.id, PromiseState.SHIPPED)

    def test_update_state_nonexistent_raises(
        self, repository: PromiseContractRepository
    ) -> None:
        with pytest.raises(RepositoryError, match="not found"):
            repository.update_state("non-existent", PromiseState.RUNNING)

    def test_update_state_updates_timestamp(
        self, repository: PromiseContractRepository, sample_contract: PromiseContract
    ) -> None:
        repository.save(sample_contract)
        updated = repository.update_state(sample_contract.id, PromiseState.RUNNING)
        assert updated.updated_at is not None
        if sample_contract.updated_at is not None:
            assert updated.updated_at >= sample_contract.updated_at
