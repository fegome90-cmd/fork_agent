"""FPEL authorization port — thin interface for sealed-PASS gate checks.

Consumers (TaskBoardService, workflow CLI) depend on this port,
not on the concrete FPELAuthorizationService.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.domain.entities.fpel import AuthorizationDecision


@runtime_checkable
class FPELAuthorizationPort(Protocol):
    """Thin port interface: check whether a target has sealed FPEL authorization."""

    def check_sealed(
        self,
        target_id: str,
        current_hash: str | None = None,
    ) -> AuthorizationDecision:
        """Check if target_id has a valid sealed PASS for its current frozen hash.

        Args:
            target_id: Task or workflow identifier.
            current_hash: Optional SHA-256 content hash provided by the caller.
                When provided, used directly for post-seal drift comparison
                instead of querying the repository (avoids self-referential read).
                When None, falls back to repository query.

        Returns:
            AuthorizationDecision with allowed=True if sealed PASS exists,
            denied otherwise with the blocking reason.
        """
        ...
