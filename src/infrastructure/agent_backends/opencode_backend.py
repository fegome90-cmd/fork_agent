"""OpenCode CLI backend implementation."""

from __future__ import annotations

import shlex
import shutil


class OpencodeBackend:
    """Backend for opencode CLI coding agent.

    The original agent backend for fork-agent-api.
    Executes tasks via: opencode run -m {model} '{task}'
    """

    name: str = "opencode"
    display_name: str = "OpenCode CLI"

    def is_available(self) -> bool:
        """Check if opencode CLI is installed."""
        return shutil.which("opencode") is not None

    def get_launch_command(self, task: str, model: str) -> str:
        """Build opencode launch command.

        Args:
            task: The task/prompt for the agent.
            model: Model identifier (e.g., 'opencode/glm-5-free').

        Returns:
            Shell command string with proper escaping.
        """
        return f"opencode run -m {shlex.quote(model)} {shlex.quote(task)}"

    def get_default_model(self) -> str:
        """Get default model for opencode."""
        return "opencode/glm-5-free"
