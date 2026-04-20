"""PromiseContract repository for SQLite persistence."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any

from src.application.exceptions import RepositoryError
from src.domain.entities.promise_contract import PromiseContract, PromiseState, VerifyEvidence
from src.infrastructure.persistence.database import DatabaseConnection


class PromiseContractRepository:
    """Repository for persisting and retrieving PromiseContract entities."""

    __slots__ = ("_connection",)

    def __init__(self, connection: DatabaseConnection) -> None:
        self._connection = connection

    def save(self, contract: PromiseContract) -> PromiseContract:
        """Store a new promise contract in the database.

        Args:
            contract: The promise contract entity to persist.

        Raises:
            RepositoryError: If the contract ID already exists or database error occurs.
        """
        verify_evidence_json = self._serialize_verify_evidence(contract.verify_evidence)
        metadata_json = self._serialize_metadata(contract.metadata)
        created_at = contract.created_at.isoformat() if contract.created_at else None
        updated_at = contract.updated_at.isoformat() if contract.updated_at else None

        try:
            with self._connection as conn:
                conn.execute(
                    """INSERT INTO promise_contracts
                       (id, session_id, plan_id, task, state, verify_evidence, created_at, updated_at, metadata)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        contract.id,
                        contract.session_id,
                        contract.plan_id,
                        contract.task,
                        contract.state.value,
                        verify_evidence_json,
                        created_at,
                        updated_at,
                        metadata_json,
                    ),
                )
        except sqlite3.IntegrityError as e:
            raise RepositoryError(
                f"PromiseContract with id '{contract.id}' already exists",
                e,
            ) from e
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to save promise contract: {e}", e) from e

        return contract

    def get_by_id(self, contract_id: str) -> PromiseContract | None:
        """Retrieve a promise contract by its ID.

        Args:
            contract_id: The unique identifier of the contract.

        Returns:
            The promise contract if found, None otherwise.
        """
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    """SELECT id, session_id, plan_id, task, state, verify_evidence,
                          created_at, updated_at, metadata
                       FROM promise_contracts WHERE id = ?""",
                    (contract_id,),
                )
                row = cursor.fetchone()

            if row is None:
                return None

            return self._row_to_contract(row)
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to get promise contract: {e}", e) from e

    def get_by_plan_id(self, plan_id: str) -> PromiseContract | None:
        """Retrieve a promise contract by its plan ID.

        Args:
            plan_id: The plan identifier.

        Returns:
            The promise contract if found, None otherwise.
        """
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    """SELECT id, session_id, plan_id, task, state, verify_evidence,
                          created_at, updated_at, metadata
                       FROM promise_contracts WHERE plan_id = ?""",
                    (plan_id,),
                )
                row = cursor.fetchone()

            if row is None:
                return None

            return self._row_to_contract(row)
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to get promise contract by plan_id: {e}", e) from e

    def get_by_session_id(self, session_id: str) -> list[PromiseContract]:
        """Retrieve all promise contracts for a session.

        Args:
            session_id: The session identifier.

        Returns:
            List of promise contracts for the session.
        """
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    """SELECT id, session_id, plan_id, task, state, verify_evidence,
                          created_at, updated_at, metadata
                       FROM promise_contracts WHERE session_id = ?
                       ORDER BY created_at DESC""",
                    (session_id,),
                )
                rows = cursor.fetchall()

            return [self._row_to_contract(row) for row in rows]
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to get promise contracts by session_id: {e}", e) from e

    def update_state(
        self,
        contract_id: str,
        state: PromiseState,
    ) -> PromiseContract:
        """Update the state of a promise contract.

        Args:
            contract_id: The unique identifier of the contract.
            state: The new state.

        Returns:
            The updated promise contract.

        Raises:
            RepositoryError: If the contract is not found or transition is invalid.
        """
        # Load current contract and validate transition
        current = self.get_by_id(contract_id)
        if current is None:
            raise RepositoryError(f"Contract {contract_id} not found")

        # Validate transition is allowed
        if not current.can_transition_to(state):
            raise RepositoryError(f"Invalid transition from {current.state.value} to {state.value}")

        now = datetime.now().isoformat()
        try:
            with self._connection as conn:
                cursor = conn.execute(
                    "UPDATE promise_contracts SET state = ?, updated_at = ? WHERE id = ?",
                    (state.value, now, contract_id),
                )

                if cursor.rowcount == 0:
                    raise RepositoryError(f"PromiseContract '{contract_id}' not found")
        except RepositoryError:
            raise
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to update promise contract state: {e}", e) from e

        contract = self.get_by_id(contract_id)
        if contract is None:
            raise RepositoryError(f"PromiseContract '{contract_id}' not found after update")
        return contract

    def _row_to_contract(self, row: sqlite3.Row) -> PromiseContract:
        """Convert a database row to a PromiseContract entity."""
        verify_evidence = self._deserialize_verify_evidence(row["verify_evidence"])
        metadata = self._deserialize_metadata(row["metadata"])
        created_at = self._parse_datetime(row["created_at"])
        updated_at = self._parse_datetime(row["updated_at"])

        return PromiseContract(
            id=row["id"],
            session_id=row["session_id"],
            plan_id=row["plan_id"],
            task=row["task"],
            state=PromiseState(row["state"]),
            verify_evidence=verify_evidence,
            created_at=created_at,
            updated_at=updated_at,
            metadata=metadata,
        )

    def _serialize_verify_evidence(self, evidence: VerifyEvidence | None) -> str | None:
        """Serialize VerifyEvidence to JSON string."""
        if evidence is None:
            return None
        return json.dumps(
            {
                "artifact_path": evidence.artifact_path,
                "passed": evidence.passed,
                "exit_code": evidence.exit_code,
                "timestamp": evidence.timestamp,
            }
        )

    def _deserialize_verify_evidence(self, evidence_json: str | None) -> VerifyEvidence | None:
        """Deserialize JSON string to VerifyEvidence."""
        if evidence_json is None:
            return None
        data = json.loads(evidence_json)
        return VerifyEvidence(
            artifact_path=data["artifact_path"],
            passed=data["passed"],
            exit_code=data["exit_code"],
            timestamp=data["timestamp"],
        )

    def _serialize_metadata(self, metadata: dict[str, Any] | None) -> str | None:
        """Serialize metadata dict to JSON string."""
        return json.dumps(metadata) if metadata is not None else None

    def _deserialize_metadata(self, metadata_json: str | None) -> dict[str, Any] | None:
        """Deserialize JSON string to metadata dict."""
        return json.loads(metadata_json) if metadata_json is not None else None

    def _parse_datetime(self, dt_str: str | None) -> datetime | None:
        """Parse ISO format datetime string to datetime object."""
        if dt_str is None:
            return None
        return datetime.fromisoformat(dt_str)
