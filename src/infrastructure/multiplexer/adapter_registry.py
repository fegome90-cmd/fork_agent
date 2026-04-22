"""Multiplexer adapter auto-detection registry.

Iterates through available adapters and returns the first one
that detects itself as available in the current environment.
Result is cached for the process lifetime.
"""

from __future__ import annotations

import threading

from src.domain.ports.multiplexer_adapter import MultiplexerAdapter
from src.infrastructure.multiplexer.iterm2_adapter import Iterm2Adapter
from src.infrastructure.multiplexer.tmux_adapter import TmuxAdapter
from src.infrastructure.multiplexer.zellij_adapter import ZellijAdapter

_cached_adapter: MultiplexerAdapter | None = None
_cache_lock = threading.Lock()

# Detection priority: tmux first (most common in agent workflows),
# then zellij, then iTerm2 (macOS only).
_ADAPTER_CLASSES: list[type[MultiplexerAdapter]] = [
    TmuxAdapter,
    ZellijAdapter,
    Iterm2Adapter,
]


def get_multiplexer_adapter() -> MultiplexerAdapter | None:
    """Auto-detect and return the appropriate multiplexer adapter.

    Uses a cached singleton with thread-safe double-check locking.
    Returns None if no multiplexer is detected.
    """
    global _cached_adapter  # noqa: PLW0603
    if _cached_adapter is not None:
        return _cached_adapter
    with _cache_lock:
        if _cached_adapter is not None:  # double-check after acquiring lock
            return _cached_adapter
        for cls in _ADAPTER_CLASSES:
            adapter = cls()
            if adapter.detect():
                _cached_adapter = adapter
                return _cached_adapter
    return None


def reset_adapter_cache() -> None:
    """Clear the cached adapter. For testing only."""
    global _cached_adapter  # noqa: PLW0603
    with _cache_lock:
        _cached_adapter = None
