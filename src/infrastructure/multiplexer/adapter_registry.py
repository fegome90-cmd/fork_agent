"""Multiplexer adapter auto-detection registry.

Iterates through available adapters and returns the first one
that detects itself as available in the current environment.
Result is cached for the process lifetime.
"""

from __future__ import annotations

from src.domain.ports.multiplexer_adapter import MultiplexerAdapter
from src.infrastructure.multiplexer.iterm2_adapter import Iterm2Adapter
from src.infrastructure.multiplexer.tmux_adapter import TmuxAdapter
from src.infrastructure.multiplexer.zellij_adapter import ZellijAdapter

_cached_adapter: MultiplexerAdapter | None = None

# Detection priority: tmux first (most common in agent workflows),
# then zellij, then iTerm2 (macOS only).
_ADAPTER_CLASSES: list[type[MultiplexerAdapter]] = [
    TmuxAdapter,
    ZellijAdapter,
    Iterm2Adapter,
]


def get_multiplexer_adapter() -> MultiplexerAdapter | None:
    """Return the first detected multiplexer adapter, cached per process.

    Returns:
        A MultiplexerAdapter instance if any multiplexer is detected,
        or None if no supported multiplexer is available.
    """
    global _cached_adapter  # noqa: PLW0603
    if _cached_adapter is not None:
        return _cached_adapter

    for cls in _ADAPTER_CLASSES:
        adapter = cls()
        if adapter.detect():
            _cached_adapter = adapter
            return _cached_adapter

    return None


def reset_adapter_cache() -> None:
    """Clear the cached adapter. Useful for testing."""
    global _cached_adapter  # noqa: PLW0603
    _cached_adapter = None
