"""Configuration for Memory Hook - FASE 3.

Defines gates and policies for selective message capture.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field


class HookPolicy(StrEnum):
    """Policy levels for message capture."""

    OFF = "off"  # No capture (default)
    IMPORTANT_ONLY = "important_only"  # Only important=true messages
    ALL = "all"  # Capture everything (not recommended)


class MemoryHookConfig(BaseModel):
    """Configuration for Memory Hook.

    Gates desde día 1:
    - toggle OFF por defecto
    - policy estricta
    - rate-limit
    - truncation
    """

    # Toggle
    enabled: bool = Field(default=False, description="Hook enabled (OFF by default)")

    # Policy
    policy: HookPolicy = Field(
        default=HookPolicy.IMPORTANT_ONLY,
        description="Capture policy level"
    )
    allowed_message_types: set[str] = Field(
        default={"COMMAND", "REPLY", "HANDOFF"},
        description="Message types to capture"
    )

    # Rate-limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_per_minute: int = Field(
        default=30,
        description="Max messages per minute per (run_id, task_id, agent_id, message_type)"
    )

    # Truncation
    max_content_bytes: int = Field(
        default=4096,  # 4KB
        description="Max content size in bytes before truncation"
    )
    truncation_enabled: bool = Field(default=True, description="Enable payload truncation")

    # Storage
    payload_storage_path: Path | None = Field(
        default=None,
        description="Path to store truncated payloads (None = no storage)"
    )

    model_config = {"frozen": True}


# Default configuration (singleton)
DEFAULT_HOOK_CONFIG = MemoryHookConfig()
