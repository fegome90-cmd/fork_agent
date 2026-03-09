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

    def get_launch_command(self, task: str, model: str) -> str:
        """Build pi launch command.

        Supports provider-qualified model IDs like:
        `nvidia-nim/minimaxai/minimax-m2.5`.

        For reliability, pass both `--provider` and `--model` when provider
        prefix is present.
        """
        base = "pi"
        if model and model != "pi/default":
            if "/" in model:
                provider, model_id = model.split("/", 1)
                base += (
                    f" --provider {shlex.quote(provider)}"
                    f" --model {shlex.quote(model_id)}"
                )
            else:
                base += f" --model {shlex.quote(model)}"
        return f"{base} {shlex.quote(task)}"

    def get_default_model(self) -> str:
        """Get deterministic default model for pi backend sessions."""
        return "nvidia-nim/minimaxai/minimax-m2.5"
