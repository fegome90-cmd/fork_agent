"""CLI interfaces."""

from typing import Any

# Lazy imports via PEP 562 to avoid loading fork.py (82ms) at module import time.
# fork.py pulls in agent_manager, terminal entities, message commands, etc.
_LAZY_IMPORTS = {
    "ForkTerminalFn": "src.interfaces.cli.fork",
    "create_fork_cli": "src.interfaces.cli.fork",
    "run_cli": "src.interfaces.cli.fork",
}

__all__ = [
    "create_fork_cli",
    "run_cli",
    "ForkTerminalFn",
]


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        mod = __import__(_LAZY_IMPORTS[name], fromlist=[name])
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return list(globals()) + list(_LAZY_IMPORTS)
