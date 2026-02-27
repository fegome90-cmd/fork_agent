"""Agent backend implementations and registry."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

from .opencode_backend import OpencodeBackend
from .pi_backend import PiBackend

if TYPE_CHECKING:
    from src.domain.ports.agent_backend import AgentBackend

logger = logging.getLogger(__name__)

# Available backend implementations (ordered by preference)
_BACKENDS: dict[str, type[Any]] = {
    "opencode": OpencodeBackend,
    "pi": PiBackend,
}

# Cache for backend instances
_backend_instances: dict[str, AgentBackend] = {}


def get_backend(name: str) -> AgentBackend | None:
    """Get a backend instance by name.

    Args:
        name: Backend identifier ('opencode' or 'pi').

    Returns:
        Backend instance or None if not found.
    """
    if name in _backend_instances:
        return _backend_instances[name]

    backend_class = _BACKENDS.get(name)
    if backend_class is None:
        logger.warning(f"Unknown backend: {name}")
        return None

    instance = cast("AgentBackend", backend_class())
    _backend_instances[name] = instance
    return instance


def get_available_backends() -> list[AgentBackend]:
    """Get list of all available (installed) backends.

    Returns:
        List of backend instances that are installed and ready.
    """
    return [
        backend
        for name in _BACKENDS
        if (backend := get_backend(name)) and backend.is_available()
    ]


def get_default_backend() -> AgentBackend | None:
    """Get the default available backend.

    Iterates through backends in definition order (opencode first).

    Returns:
        Default backend instance or None if none available.
    """
    for name in _BACKENDS:
        backend = get_backend(name)
        if backend and backend.is_available():
            return backend
    return None


def list_all_backends() -> list[str]:
    """List all registered backend names.

    Returns:
        List of backend identifiers.
    """
    return list(_BACKENDS.keys())


__all__ = [
    "OpencodeBackend",
    "PiBackend",
    "get_backend",
    "get_available_backends",
    "get_default_backend",
    "list_all_backends",
]
