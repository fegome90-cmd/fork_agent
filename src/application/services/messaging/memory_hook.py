"""Memory Hook for selective message capture - FASE 3.

Captures important messages to memory with gates:
- Toggle OFF by default
- Policy: important=true + allowed types
- Rate-limit per (run_id, task_id, agent_id, message_type)
- Truncation for large payloads
- Dedup by message_id
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from src.application.services.memory.event_metadata import (
    EventType,
    ExecutionMode,
    MemoryEventMetadata,
)
from src.application.services.messaging.memory_hook_config import (
    MemoryHookConfig,
    DEFAULT_HOOK_CONFIG,
)
from src.application.services.messaging.rate_limiter import RateLimiter
from src.domain.entities.message import AgentMessage, MessageType

if TYPE_CHECKING:
    from src.application.services.memory_service import MemoryService

logger = logging.getLogger(__name__)


class MemoryHook:
    """Hook for capturing selective messages to memory.

    Gates desde día 1:
    - toggle OFF por defecto
    - policy estricta (important + types)
    - rate-limit configurable
    - truncation + payload_ref
    - dedup por message_id
    """

    def __init__(
        self,
        memory_service: MemoryService,
        config: MemoryHookConfig | None = None,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        """Initialize Memory Hook.

        Args:
            memory_service: Service for persisting observations
            config: Hook configuration (uses default if None)
            rate_limiter: Rate limiter (creates default if None)
        """
        self._memory = memory_service
        self._config = config or DEFAULT_HOOK_CONFIG
        self._rate_limiter = rate_limiter or RateLimiter(
            max_requests=self._config.rate_limit_per_minute,
            window_seconds=60,
        )

    @property
    def config(self) -> MemoryHookConfig:
        """Get current configuration."""
        return self._config

    def should_capture(self, msg: AgentMessage, context: dict[str, Any] | None = None) -> bool:
        """Determine if message should be captured.

        Applies all gates:
        1. Toggle check
        2. Policy check (important + types)
        3. Rate limit check

        Args:
            msg: Message to check
            context: Optional context (run_id, task_id, etc.)

        Returns:
            True if message should be captured
        """
        # Gate 1: Toggle
        if not self._config.enabled:
            return False

        # Gate 2: Policy - message type
        msg_type_name = msg.message_type.name
        if msg_type_name not in self._config.allowed_message_types:
            logger.debug("Message type %s not in allowed types", msg_type_name)
            return False

        # Gate 2: Policy - important check (if policy requires it)
        if self._config.policy.value == "important_only":
            if not self._is_important(msg):
                logger.debug("Message %s is not marked as important", msg.id[:8])
                return False

        # Gate 3: Rate limit
        if self._config.rate_limit_enabled:
            rate_key = self._build_rate_key(msg, context)
            if not self._rate_limiter.is_allowed(rate_key):
                logger.debug("Rate limited: %s", rate_key)
                return False

        return True

    def capture(
        self,
        msg: AgentMessage,
        context: dict[str, Any] | None = None,
    ) -> str | None:
        """Capture message to memory if it passes gates.

        Args:
            msg: Message to capture
            context: Optional context (run_id, task_id, mode, etc.)

        Returns:
            Observation ID if captured, None if skipped
        """
        if not self.should_capture(msg, context):
            return None

        # Extract context
        ctx = context or {}
        run_id = ctx.get("run_id", "unknown")
        task_id = ctx.get("task_id", "unknown")
        mode = ctx.get("mode", ExecutionMode.WORKTREE)

        # Truncate payload if necessary
        content, truncated, payload_ref = self._truncate_payload(msg.payload)

        # Build metadata
        metadata_kwargs: dict[str, Any] = {
            "extra": {
                "from_agent_id": msg.from_agent,
                "to_agent_id": msg.to_agent,
                "message_id": msg.id,
                "message_type": msg.message_type.name,
                "correlation_id": msg.correlation_id,
                "payload_truncated": truncated,
            }
        }

        if payload_ref:
            metadata_kwargs["extra"]["payload_ref"] = payload_ref

        if msg.to_agent == "*":
            metadata_kwargs["extra"]["broadcast"] = True

        # Build idempotency key with message_id for dedup
        # Format: run_id:task_id:agent_message:message_id
        idempotency_key = f"{run_id}:{task_id}:agent_message:{msg.id}"

        # Create metadata manually (not using factory to control idempotency_key)
        import time
        timestamp_ms = int(time.time() * 1000)

        metadata = MemoryEventMetadata(
            event_type=EventType.MESSAGE_SENT.value,
            run_id=run_id,
            task_id=task_id,
            agent_id=msg.from_agent,
            session_name=msg.from_agent.split(":")[0] if ":" in msg.from_agent else msg.from_agent,
            timestamp_ms=timestamp_ms,
            mode=mode.value if isinstance(mode, ExecutionMode) else mode,
            idempotency_key=idempotency_key,
            extra={
                "from_agent_id": msg.from_agent,
                "to_agent_id": msg.to_agent,
                "message_id": msg.id,
                "message_type": msg.message_type.name,
                "correlation_id": msg.correlation_id,
                "payload_truncated": truncated,
                **({"payload_ref": payload_ref} if payload_ref else {}),
                **({"broadcast": True} if msg.to_agent == "*" else {}),
            },
        )

        # Save to memory with dedup by message_id
        try:
            obs_id = self._memory.save_event(
                content=content,
                metadata=metadata.model_dump(),
                idempotency_key=idempotency_key,
            )

            logger.debug(
                "Captured message %s to memory (obs_id=%s)",
                msg.id[:8],
                obs_id,
            )
            return obs_id

        except Exception as e:
            logger.error("Failed to capture message %s: %s", msg.id[:8], e)
            return None

    def _is_important(self, msg: AgentMessage) -> bool:
        """Check if message is marked as important.

        Checks payload JSON for 'important' field.

        Args:
            msg: Message to check

        Returns:
            True if important, False otherwise
        """
        try:
            payload = json.loads(msg.payload)
            return payload.get("important", False) is True
        except (json.JSONDecodeError, TypeError):
            # If payload is not JSON, default to False
            return False

    def _truncate_payload(
        self,
        payload: str,
    ) -> tuple[str, bool, str | None]:
        """Truncate payload if necessary.

        Args:
            payload: Message payload

        Returns:
            Tuple of (content, truncated, payload_ref)
        """
        if not self._config.truncation_enabled:
            return payload, False, None

        payload_bytes = len(payload.encode("utf-8"))

        if payload_bytes <= self._config.max_content_bytes:
            return payload, False, None

        # Truncate
        max_chars = self._config.max_content_bytes // 4  # Rough estimate for UTF-8
        truncated_content = payload[:max_chars] + "...<truncated>"

        # Optionally store full payload
        payload_ref = None
        if self._config.payload_storage_path:
            # For now, just mark that truncation happened
            # Full implementation would write to file
            payload_ref = f"<truncated:{payload_bytes}bytes>"

        return truncated_content, True, payload_ref

    def _build_rate_key(
        self,
        msg: AgentMessage,
        context: dict[str, Any] | None,
    ) -> str:
        """Build rate limit key.

        Format: run_id:task_id:agent_id:message_type

        Args:
            msg: Message being checked
            context: Optional context

        Returns:
            Rate limit key
        """
        ctx = context or {}
        run_id = ctx.get("run_id", "unknown")
        task_id = ctx.get("task_id", "unknown")

        return f"{run_id}:{task_id}:{msg.from_agent}:{msg.message_type.name}"
