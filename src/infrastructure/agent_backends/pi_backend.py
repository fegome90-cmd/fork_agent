"""pi.dev coding agent backend implementation."""

from __future__ import annotations

import shlex
import shutil


class PiBackend:
    """Backend for pi.dev coding agent.

    Reference: https://mariozechner.at/posts/2025-11-30-pi-coding-agent/

    pi is a coding agent that focuses on deep code understanding
    and iterative development. It runs tasks via: pi '{task}'
    """

    name: str = "pi"
    display_name: str = "pi.dev Agent"

    def is_available(self) -> bool:
        """Check if pi CLI is installed."""
        return shutil.which("pi") is not None

    def get_launch_command(self, task: str, _model: str) -> str:
        """Build pi launch command.

        Note: pi.dev doesn't use a model parameter in its CLI.
        The model parameter is accepted for API compatibility but ignored.

        Args:
            task: The task/prompt for the agent.
            model: Model identifier (ignored by pi, uses its own default).

        Returns:
            Shell command string with proper escaping.
        """
        return f"pi {shlex.quote(task)}"

    def get_default_model(self) -> str:
        """Get default model (pi uses its own model selection)."""
        return "pi/default"
