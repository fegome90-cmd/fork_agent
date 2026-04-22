"""Port (interface) for terminal multiplexer adapters.

Defines the abstraction layer that concrete adapters (tmux, zellij, iTerm2)
implement. Follows hexagonal architecture: domain depends on this port,
infrastructure provides the adapters.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class SpawnOptions:
    """Configuration for spawning a new pane.

    Attributes:
        command: Shell command to execute in the new pane.
        name: Human-readable name for the pane.
        env: Optional environment variables to set in the pane.
        workdir: Optional working directory for the pane.
    """

    command: str
    name: str
    env: dict[str, str] | None = None
    workdir: str | None = None


@dataclass(frozen=True)
class PaneInfo:
    """Immutable snapshot of a multiplexer pane's state.

    Attributes:
        pane_id: Native pane identifier (e.g. tmux %0, zellij pane UUID).
        is_alive: Whether the pane process is still running.
        title: Optional display title of the pane.
    """

    pane_id: str
    is_alive: bool
    title: str = ""


class MultiplexerAdapter(ABC):
    """Abstract base for terminal multiplexer adapters.

    Each adapter wraps a specific multiplexer (tmux, zellij, iTerm2)
    behind a unified interface. Adapters are auto-detected at runtime
    via the detect() method.
    """

    name: str  # "tmux", "zellij", "iterm2"

    @abstractmethod
    def detect(self) -> bool:
        """Check whether this multiplexer is available in the current environment.

        Returns:
            True if the multiplexer is detected and usable.
        """
        ...

    @abstractmethod
    def spawn(self, options: SpawnOptions) -> PaneInfo:
        """Spawn a new pane running the given command.

        Args:
            options: Spawn configuration (command, name, env, workdir).

        Returns:
            PaneInfo with the native pane identifier.

        Raises:
            RuntimeError: If the pane could not be created.
        """
        ...

    @abstractmethod
    def kill(self, pane_id: str) -> None:
        """Kill a pane by its native identifier.

        Args:
            pane_id: The native pane identifier returned by spawn().

        Raises:
            RuntimeError: If the pane could not be killed.
        """
        ...

    @abstractmethod
    def is_alive(self, pane_id: str) -> bool:
        """Check whether a pane is still alive.

        Args:
            pane_id: The native pane identifier.

        Returns:
            True if the pane process is still running.
        """
        ...

    @abstractmethod
    def set_title(self, pane_id: str, title: str) -> None:
        """Set the display title of a pane.

        Args:
            pane_id: The native pane identifier.
            title: The new title string.
        """
        ...

    @abstractmethod
    def configure_pane(self, pane_id: str, remain_on_exit: bool = True) -> None:
        """Configure pane behavior after the command exits.

        Args:
            pane_id: The native pane identifier.
            remain_on_exit: If True, keep the pane open after the command exits.
        """
        ...
