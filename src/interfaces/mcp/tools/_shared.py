"""Shared infrastructure for MCP tools: imports, project detection, service access, error mapping."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from mcp import McpError
from mcp.types import INTERNAL_ERROR, INVALID_PARAMS, ErrorData

from src.application.exceptions import (
    MemoryError,
    ObservationNotFoundError,
    SessionNotFoundError,
)

if TYPE_CHECKING:
    pass

# MCP has no dedicated NOT_FOUND code — use INVALID_PARAMS for client errors
# and INTERNAL_ERROR for server errors.
_NOT_FOUND_FALLBACK = INVALID_PARAMS

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

    return os.path.basename(os.getcwd())


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
        _singletons["enhanced"] = EnhancedRetrievalSearchService(repository)  # type: ignore[arg-type]
    return _singletons["enhanced"]


def init_service(db_path: str | None = None) -> None:
    """Initialize core service singletons (memory, session, health) with an
    optional custom db_path. Agent messenger and enhanced search are lazily
    initialized on first use.
    """
    global _custom_db_path
    from pathlib import Path

    _custom_db_path = Path(db_path) if db_path else None
    _get_memory_service()
    _get_session_service()
    _get_health_service()


# ---------------------------------------------------------------------------
# Error mapping
# ---------------------------------------------------------------------------


def _map_error(e: Exception) -> McpError:
    """Map domain exceptions to MCP error codes."""
    if isinstance(e, ObservationNotFoundError):
        return McpError(ErrorData(code=_NOT_FOUND_FALLBACK, message=str(e)))
    if isinstance(e, ValueError):
        return McpError(ErrorData(code=INVALID_PARAMS, message=str(e)))
    if isinstance(e, SessionNotFoundError):
        return McpError(ErrorData(code=_NOT_FOUND_FALLBACK, message=str(e)))
    if isinstance(e, MemoryError):
        return McpError(ErrorData(code=INTERNAL_ERROR, message=str(e)))
    return McpError(ErrorData(code=INTERNAL_ERROR, message=f"Internal error: {e}"))
