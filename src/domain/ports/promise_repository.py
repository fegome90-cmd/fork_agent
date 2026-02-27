"""PromiseRepository protocol for IO operations."""

from __future__ import annotations

from typing import Protocol

from src.domain.entities.promise_contract import PromiseContract, PromiseState


class PromiseRepository(Protocol):
    """Protocol for promise contract persistence."""

    def save(self, contract: PromiseContract) -> PromiseContract:
        """Save a promise contract to the repository.

        Args:
            contract: The promise contract to save.

        Returns:
            The saved promise contract.
        """
        ...

    def get_by_id(self, contract_id: str) -> PromiseContract | None:
        """Retrieve a promise contract by its ID.

        Args:
            contract_id: The unique identifier of the contract.

        Returns:
            The promise contract if found, None otherwise.
        """
        ...

    def get_by_plan_id(self, plan_id: str) -> PromiseContract | None:
        """Retrieve a promise contract by its plan ID.

        Args:
            plan_id: The plan identifier.

        Returns:
            The promise contract if found, None otherwise.
        """
        ...

    def get_by_session_id(self, session_id: str) -> list[PromiseContract]:
        """Retrieve all promise contracts for a session.

        Args:
            session_id: The session identifier.

        Returns:
            List of promise contracts for the session.
        """
        ...

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
            RepositoryError: If the contract is not found.
        """
        ...
