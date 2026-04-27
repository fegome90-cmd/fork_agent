"""API dependencies — FastAPI-specific DI and auth.

Service singletons are re-exported from the canonical container.
This module only contains FastAPI-specific logic (auth, Depends wrappers).
"""

from __future__ import annotations

import hmac
import logging
from pathlib import Path

from fastapi import Header, HTTPException, status

from src.application.services.memory_service import MemoryService
from src.application.services.orchestration.hook_service import HookService
from src.infrastructure.persistence.container import (
    get_hook_service as _get_hook_service,
)
from src.infrastructure.persistence.container import (
    get_memory_service as _get_memory_service,
)
from src.infrastructure.persistence.container import (
    get_promise_repository as _get_promise_repository,
)
from src.infrastructure.persistence.repositories.promise_repository import (
    PromiseContractRepository,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# FastAPI Authentication (API-specific — stays here)
# ---------------------------------------------------------------------------


async def verify_api_key(x_api_key: str = Header(...)) -> str:
    """Verify the API key from request headers."""
    from src.interfaces.api.config import get_api_settings

    api_settings = get_api_settings()

    if not api_settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API key not configured",
        )

    if not hmac.compare_digest(x_api_key, api_settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return x_api_key


# ---------------------------------------------------------------------------
# Re-exports with proper typing (replaces Any-typed singletons)
# ---------------------------------------------------------------------------


def get_memory_service(db_path: str = "") -> MemoryService:
    """Get MemoryService singleton — delegates to canonical container.

    Maintains str-based db_path API for backward compatibility with routes.
    """
    if not db_path:
        from src.infrastructure.persistence.container import get_default_db_path

        db_path = str(get_default_db_path())
    path = Path(db_path) if db_path else None
    return _get_memory_service(path)  # type: ignore[no-any-return]


def get_hook_service() -> HookService:
    """Get HookService singleton — delegates to canonical container."""
    return _get_hook_service()  # type: ignore[no-any-return]


def get_promise_repository() -> PromiseContractRepository:
    """Get PromiseContractRepository singleton — delegates to canonical container."""
    return _get_promise_repository()  # type: ignore[no-any-return]
