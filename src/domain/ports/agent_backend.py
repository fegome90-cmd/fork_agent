"""Port (Protocol) for agent execution backends."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class AgentBackend(Protocol):
    """Abstract interface for agent execution backends.

    Defines the contract for launching AI coding agents via tmux.
    Concrete implementations handle specific agent CLIs (opencode, pi, etc.).
    """

    @property
    def name(self) -> str:
        """Backend identifier used in API requests.

        Returns:
            Short identifier like 'opencode' or 'pi'.
        """
        ...

    @property
    def display_name(self) -> str:
        """Human-readable name for the backend.

        Returns:
            Full name like 'OpenCode CLI' or 'pi.dev Agent'.
        """
        ...

    def is_available(self) -> bool:
        """Check if this backend is installed and ready to use.

        Returns:
            True if the agent CLI binary exists and is executable.
        """
        ...

    def get_launch_command(self, task: str, model: str) -> str:
        """Build the shell command to launch the agent.

        Args:
            task: The task/prompt for the agent to execute.
            model: The model identifier to use.

        Returns:
            Shell command string to execute via tmux send-keys.
        """
        ...

    def get_default_model(self) -> str:
        """Get the default model for this backend.

        Returns:
            Default model identifier.
        """
        ...
