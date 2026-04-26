"""Shared infrastructure for MCP tools: imports, project detection, service access, error mapping.

MCP SDK imports are deferred to error paths to avoid the 200ms+ import cost
of loading 82 submodules. Happy-path imports (project detection, service access)
complete in ~5ms.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from src.application.exceptions import (
    MemoryStoreError,
    ObservationNotFoundError,
    SessionNotFoundError,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger("memory-mcp")


# ---------------------------------------------------------------------------
# Project auto-detection (Engram model: single DB, project from CWD)
# ---------------------------------------------------------------------------


def _detect_project() -> str:
    """Auto-detect project name from the current working directory.

    Uses the directory name of CWD, matching Engram's behavior.
    This allows a single MCP server to serve multiple projects
    by scoping each tool call to the caller's project.

    WARNING: Returns the server process CWD. Works correctly for stdio
    transport (inherits caller CWD) but returns server CWD for SSE/HTTP
    clients. Pass explicit `project` parameter for non-stdio transports.
    """
    import os

    name = os.path.basename(os.getcwd())
    return name or "default"


def _resolve_project(project: str | None) -> str:
    """Resolve project name: explicit param overrides auto-detection."""
    return project or _detect_project()


# ---------------------------------------------------------------------------
# Service access — thin wrapper over container.py
# ---------------------------------------------------------------------------

# Thread-safety: Module globals are safe under MCP stdio transport's
# single-threaded execution model. SSE/HTTP transport would require
# locking (e.g., threading.Lock) or per-request instances.
_singletons: dict[str, Any] = {}
_custom_db_path: Any | None = None  # Path | None, stored as Any to avoid top-level import


def _get_singleton(key: str, factory: Any) -> Any:
    """Generic lazy singleton factory. Thread-safe for stdio."""
    if key not in _singletons:
        _singletons[key] = factory(_custom_db_path)
    return _singletons[key]


def _get_memory_service() -> Any:
    from src.infrastructure.persistence.container import get_memory_service

    return _get_singleton("memory", get_memory_service)


def _get_session_service() -> Any:
    from src.infrastructure.persistence.container import get_session_service

    return _get_singleton("session", get_session_service)


def _get_health_service() -> Any:
    from src.infrastructure.persistence.container import get_health_service

    return _get_singleton("health", get_health_service)


def _get_agent_messenger() -> Any:
    from src.infrastructure.persistence.container import get_agent_messenger

    return _get_singleton("messenger", get_agent_messenger)


def _get_enhanced_search_service() -> Any:
    if "enhanced" not in _singletons:
        from src.infrastructure.persistence.container import get_repository
        from src.infrastructure.retrieval.v2.enhanced_search import EnhancedRetrievalSearchService

        repository = get_repository(_custom_db_path)
        _singletons["enhanced"] = EnhancedRetrievalSearchService(repository)
    return _singletons["enhanced"]


def init_service(db_path: str | None = None) -> None:
    """Initialize core service singletons (memory, session, health) with an
    optional custom db_path. Agent messenger and enhanced search are lazily
    initialized on first use.
    """
    global _custom_db_path
    from pathlib import Path

    new_path = Path(db_path) if db_path else None
    if new_path != _custom_db_path:
        _singletons.clear()
    _custom_db_path = new_path
    _get_memory_service()
    _get_session_service()
    _get_health_service()


# ---------------------------------------------------------------------------
# Error mapping — mcp SDK imported lazily (~200ms deferred to error paths)
# ---------------------------------------------------------------------------


def _validate_topic_key(topic_key: str | None) -> None:
    """Reject path traversal patterns in topic_key."""
    if topic_key and ".." in topic_key.split("/"):
        raise ValueError(f"Invalid topic_key: path traversal detected in '{topic_key}'")


def _map_error(e: Exception) -> Any:
    """Map domain exceptions to MCP error codes.

    Defers `mcp` SDK import (~200ms for 82 submodules) to error paths only.
    This keeps happy-path imports fast (~5ms instead of ~200ms).
    """
    from mcp import McpError
    from mcp.types import INTERNAL_ERROR, INVALID_PARAMS, ErrorData

    if isinstance(e, ObservationNotFoundError):
        return McpError(ErrorData(code=INVALID_PARAMS, message=str(e)))
    if isinstance(e, ValueError):
        return McpError(ErrorData(code=INVALID_PARAMS, message=str(e)))
    if isinstance(e, SessionNotFoundError):
        return McpError(ErrorData(code=INVALID_PARAMS, message=str(e)))
    if isinstance(e, MemoryStoreError):
        return McpError(ErrorData(code=INTERNAL_ERROR, message=str(e)))
    return McpError(ErrorData(code=INTERNAL_ERROR, message=f"Internal error: {e}"))
