"""Unit tests for Memory Hook - FASE 3.

Tests all gates:
- Toggle OFF by default
- Policy: important=false → no capture
- Policy: type not in allowed → no capture
- Rate-limit: N+1 in window → drop
- Truncation: payload > limit → truncated + metadata
- Dedup: same message_id → no duplicate
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.application.services.messaging.memory_hook import MemoryHook
from src.application.services.messaging.memory_hook_config import (
    MemoryHookConfig,
    HookPolicy,
)
from src.application.services.messaging.rate_limiter import RateLimiter
from src.application.services.memory_service import MemoryService
from src.domain.entities.message import AgentMessage, MessageType
from src.infrastructure.persistence.container import create_container


@pytest.fixture
def temp_db() -> Path:
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        yield Path(f.name)


@pytest.fixture
def container(temp_db: Path):
    """Create a container for testing."""
    return create_container(temp_db)


@pytest.fixture
def memory_service(container) -> MemoryService:
    """Get MemoryService."""
    return container.memory_service()


@pytest.fixture
def enabled_config() -> MemoryHookConfig:
    """Config with hook enabled."""
    return MemoryHookConfig(
        enabled=True,
        policy=HookPolicy.IMPORTANT_ONLY,
        rate_limit_per_minute=30,
        max_content_bytes=4096,
    )


@pytest.fixture
def disabled_config() -> MemoryHookConfig:
    """Config with hook disabled (default)."""
    return MemoryHookConfig(enabled=False)


@pytest.fixture
def hook_enabled(memory_service: MemoryService, enabled_config: MemoryHookConfig) -> MemoryHook:
    """Create MemoryHook with enabled config."""
    return MemoryHook(
        memory_service=memory_service,
        config=enabled_config,
    )


@pytest.fixture
def hook_disabled(memory_service: MemoryService, disabled_config: MemoryHookConfig) -> MemoryHook:
    """Create MemoryHook with disabled config."""
    return MemoryHook(
        memory_service=memory_service,
        config=disabled_config,
    )


class TestToggleOffByDefault:
    """Test that hook is OFF by default."""

    def test_disabled_hook_does_not_capture(
        self,
        hook_disabled: MemoryHook,
    ) -> None:
        """Disabled hook should not capture any messages."""
        msg = AgentMessage.create(
            from_agent="agent1:0",
            to_agent="agent2:0",
            message_type=MessageType.COMMAND,
            payload=json.dumps({"important": True, "data": "test"}),
        )

        result = hook_disabled.capture(msg, context={"run_id": "run-1", "task_id": "task-1"})

        assert result is None, "Disabled hook should not capture"

    def test_should_capture_returns_false_when_disabled(
        self,
        hook_disabled: MemoryHook,
    ) -> None:
        """should_capture should return False when disabled."""
        msg = AgentMessage.create(
            from_agent="agent1:0",
            to_agent="agent2:0",
            message_type=MessageType.COMMAND,
            payload=json.dumps({"important": True}),
        )

        assert hook_disabled.should_capture(msg) is False


class TestPolicyImportantOnly:
    """Test policy: only important=true messages."""

    def test_important_false_not_captured(
        self,
        hook_enabled: MemoryHook,
    ) -> None:
        """Messages with important=false should not be captured."""
        msg = AgentMessage.create(
            from_agent="agent1:0",
            to_agent="agent2:0",
            message_type=MessageType.COMMAND,
            payload=json.dumps({"important": False, "data": "test"}),
        )

        result = hook_enabled.should_capture(msg)
        assert result is False, "important=false should not be captured"

    def test_important_true_captured(
        self,
        hook_enabled: MemoryHook,
    ) -> None:
        """Messages with important=true should be captured."""
        msg = AgentMessage.create(
            from_agent="agent1:0",
            to_agent="agent2:0",
            message_type=MessageType.COMMAND,
            payload=json.dumps({"important": True, "data": "test"}),
        )

        result = hook_enabled.should_capture(msg)
        assert result is True, "important=true should be captured"

    def test_no_important_field_not_captured(
        self,
        hook_enabled: MemoryHook,
    ) -> None:
        """Messages without important field should not be captured."""
        msg = AgentMessage.create(
            from_agent="agent1:0",
            to_agent="agent2:0",
            message_type=MessageType.COMMAND,
            payload=json.dumps({"data": "test"}),
        )

        result = hook_enabled.should_capture(msg)
        assert result is False, "missing important field should not be captured"


class TestPolicyMessageTypes:
    """Test policy: only allowed message types."""

    def test_command_type_allowed(
        self,
        hook_enabled: MemoryHook,
    ) -> None:
        """COMMAND type should be allowed."""
        msg = AgentMessage.create(
            from_agent="agent1:0",
            to_agent="agent2:0",
            message_type=MessageType.COMMAND,
            payload=json.dumps({"important": True}),
        )

        assert hook_enabled.should_capture(msg) is True

    def test_reply_type_allowed(
        self,
        hook_enabled: MemoryHook,
    ) -> None:
        """REPLY type should be allowed."""
        msg = AgentMessage.create(
            from_agent="agent1:0",
            to_agent="agent2:0",
            message_type=MessageType.REPLY,
            payload=json.dumps({"important": True}),
        )

        assert hook_enabled.should_capture(msg) is True

    def test_type_not_in_allowed_set_rejected(
        self,
        memory_service: MemoryService,
    ) -> None:
        """Types not in allowed_message_types should be rejected."""
        config = MemoryHookConfig(
            enabled=True,
            policy=HookPolicy.IMPORTANT_ONLY,
            allowed_message_types={"COMMAND"},  # Only COMMAND allowed
        )
        hook = MemoryHook(memory_service=memory_service, config=config)

        msg = AgentMessage.create(
            from_agent="agent1:0",
            to_agent="agent2:0",
            message_type=MessageType.REPLY,  # REPLY not in allowed set
            payload=json.dumps({"important": True}),
        )

        assert hook.should_capture(msg) is False


class TestRateLimit:
    """Test rate limiting."""

    def test_rate_limit_exceeded_drops_message(
        self,
        memory_service: MemoryService,
    ) -> None:
        """Messages exceeding rate limit should be dropped."""
        config = MemoryHookConfig(
            enabled=True,
            policy=HookPolicy.ALL,  # Accept all for this test
            rate_limit_per_minute=2,  # Very low limit
        )
        rate_limiter = RateLimiter(max_requests=2, window_seconds=60)
        hook = MemoryHook(
            memory_service=memory_service,
            config=config,
            rate_limiter=rate_limiter,
        )

        context = {"run_id": "run-1", "task_id": "task-1"}

        # First 2 should succeed
        for i in range(2):
            msg = AgentMessage.create(
                from_agent="agent1:0",
                to_agent="agent2:0",
                message_type=MessageType.COMMAND,
                payload=json.dumps({"data": f"msg-{i}"}),
            )
            assert hook.should_capture(msg, context) is True

        # Third should be rate limited
        msg = AgentMessage.create(
            from_agent="agent1:0",
            to_agent="agent2:0",
            message_type=MessageType.COMMAND,
            payload=json.dumps({"data": "msg-3"}),
        )
        assert hook.should_capture(msg, context) is False

    def test_rate_limit_independent_per_agent(
        self,
        memory_service: MemoryService,
    ) -> None:
        """Rate limit should be independent per agent."""
        config = MemoryHookConfig(
            enabled=True,
            policy=HookPolicy.ALL,
            rate_limit_per_minute=1,
        )
        rate_limiter = RateLimiter(max_requests=1, window_seconds=60)
        hook = MemoryHook(
            memory_service=memory_service,
            config=config,
            rate_limiter=rate_limiter,
        )

        context = {"run_id": "run-1", "task_id": "task-1"}

        # Agent1: first message OK
        msg1 = AgentMessage.create(
            from_agent="agent1:0",
            to_agent="agent2:0",
            message_type=MessageType.COMMAND,
            payload=json.dumps({"data": "msg1"}),
        )
        assert hook.should_capture(msg1, context) is True

        # Agent1: second message rate limited
        msg2 = AgentMessage.create(
            from_agent="agent1:0",
            to_agent="agent2:0",
            message_type=MessageType.COMMAND,
            payload=json.dumps({"data": "msg2"}),
        )
        assert hook.should_capture(msg2, context) is False

        # Agent2: first message OK (different agent)
        msg3 = AgentMessage.create(
            from_agent="agent2:0",
            to_agent="agent1:0",
            message_type=MessageType.COMMAND,
            payload=json.dumps({"data": "msg3"}),
        )
        assert hook.should_capture(msg3, context) is True


class TestTruncation:
    """Test payload truncation."""

    def test_large_payload_truncated(
        self,
        memory_service: MemoryService,
    ) -> None:
        """Payloads exceeding max_content_bytes should be truncated."""
        config = MemoryHookConfig(
            enabled=True,
            policy=HookPolicy.ALL,
            max_content_bytes=100,  # Very small limit
            truncation_enabled=True,
        )
        hook = MemoryHook(memory_service=memory_service, config=config)

        # Create large payload
        large_data = "x" * 1000
        msg = AgentMessage.create(
            from_agent="agent1:0",
            to_agent="agent2:0",
            message_type=MessageType.COMMAND,
            payload=json.dumps({"important": True, "data": large_data}),
        )

        obs_id = hook.capture(msg, context={"run_id": "run-1", "task_id": "task-1"})

        assert obs_id is not None, "Should capture even if truncated"

        # Verify truncation metadata
        observations = memory_service.get_recent(limit=10)
        assert len(observations) >= 1

        obs = observations[0]
        assert obs.metadata.get("extra", {}).get("payload_truncated") is True

    def test_small_payload_not_truncated(
        self,
        hook_enabled: MemoryHook,
        memory_service: MemoryService,
    ) -> None:
        """Small payloads should not be truncated."""
        msg = AgentMessage.create(
            from_agent="agent1:0",
            to_agent="agent2:0",
            message_type=MessageType.COMMAND,
            payload=json.dumps({"important": True, "data": "small"}),
        )

        obs_id = hook_enabled.capture(msg, context={"run_id": "run-1", "task_id": "task-1"})

        assert obs_id is not None

        observations = memory_service.get_recent(limit=10)
        obs = observations[0]
        assert obs.metadata.get("extra", {}).get("payload_truncated") is not True


class TestDedup:
    """Test deduplication by message_id."""

    def test_same_message_id_no_duplicate(
        self,
        hook_enabled: MemoryHook,
        memory_service: MemoryService,
    ) -> None:
        """Same message_id should not create duplicate observations."""
        msg = AgentMessage.create(
            from_agent="agent1:0",
            to_agent="agent2:0",
            message_type=MessageType.COMMAND,
            payload=json.dumps({"important": True, "data": "test"}),
        )

        context = {"run_id": "run-1", "task_id": "task-1"}

        # Capture same message twice
        obs_id_1 = hook_enabled.capture(msg, context)
        obs_id_2 = hook_enabled.capture(msg, context)

        # Should return same observation ID (idempotency)
        assert obs_id_1 == obs_id_2

        # Should have only 1 observation
        observations = memory_service.get_recent(limit=10)
        message_observations = [
            o for o in observations
            if o.metadata and o.metadata.get("event_type") == "message_sent"
        ]
        assert len(message_observations) == 1, f"Expected 1 observation, got {len(message_observations)}"

    def test_different_message_id_creates_separate_observations(
        self,
        hook_enabled: MemoryHook,
        memory_service: MemoryService,
    ) -> None:
        """Different message_id should create separate observations."""
        context = {"run_id": "run-1", "task_id": "task-1"}

        # Two different messages
        msg1 = AgentMessage.create(
            from_agent="agent1:0",
            to_agent="agent2:0",
            message_type=MessageType.COMMAND,
            payload=json.dumps({"important": True, "data": "msg1"}),
        )

        msg2 = AgentMessage.create(
            from_agent="agent1:0",
            to_agent="agent2:0",
            message_type=MessageType.COMMAND,
            payload=json.dumps({"important": True, "data": "msg2"}),
        )

        obs_id_1 = hook_enabled.capture(msg1, context)
        obs_id_2 = hook_enabled.capture(msg2, context)

        # Should be different observation IDs
        assert obs_id_1 != obs_id_2

        # Should have 2 observations
        observations = memory_service.get_recent(limit=10)
        message_observations = [
            o for o in observations
            if o.metadata and o.metadata.get("event_type") == "message_sent"
        ]
        assert len(message_observations) == 2
