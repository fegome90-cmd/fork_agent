"""Dependencies para la API."""

import hmac
import logging
from threading import Lock
from typing import Any

from fastapi import Header, HTTPException, status

logger = logging.getLogger(__name__)

_memory_service: Any = None
_memory_lock = Lock()

_hook_service: Any = None
_hook_lock = Lock()

_promise_repository: Any = None
_promise_repo_lock = Lock()


async def verify_api_key(x_api_key: str = Header(...)) -> str:
    from src.interfaces.api.config import api_settings

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


def get_memory_service(db_path: str | None = None) -> Any:
    global _memory_service

    if _memory_service is not None:
        return _memory_service

    with _memory_lock:
        if _memory_service is None:
            try:
                from pathlib import Path

                from src.infrastructure.persistence.container import create_container

                path = Path(db_path) if db_path else None
                container = create_container(path)
                _memory_service = container.memory_service()
                logger.info("Initialized MemoryService singleton")
            except Exception as e:
                logger.exception(f"Failed to initialize MemoryService: {e}")
                raise

    return _memory_service


def get_hook_service() -> Any:
    global _hook_service

    if _hook_service is not None:
        return _hook_service

    with _hook_lock:
        if _hook_service is None:
            try:
                from src.application.services.orchestration.hook_service import HookService

                _hook_service = HookService()
                logger.info("Initialized HookService singleton")
            except Exception as e:
                logger.exception(f"Failed to initialize HookService: {e}")
                raise

    return _hook_service


def get_promise_repository() -> Any:
    global _promise_repository

    if _promise_repository is not None:
        return _promise_repository

    with _promise_repo_lock:
        if _promise_repository is None:
            try:
                from src.infrastructure.persistence.container import create_container

                container = create_container()
                _promise_repository = container.promise_contract_repository()
                logger.info("Initialized PromiseContractRepository singleton")
            except Exception as e:
                logger.exception(f"Failed to initialize PromiseContractRepository: {e}")
                raise

    return _promise_repository
