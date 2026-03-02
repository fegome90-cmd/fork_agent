"""Integration tests for Memory Hook - FASE 3.

Tests the complete flow:
- With toggle OFF: IPC flow → 0 new agent_message observations
- With toggle ON: Send 1 important COMMAND → 1 observation with complete metadata
- Retry: Re-send same message_id → still 1
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.application.services.messaging.memory_hook import MemoryHook
from src.application.services.messaging.memory_hook_config import (
    HookPolicy,
    MemoryHookConfig,
)
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


class TestMemoryHookIntegration:
    """Integration tests for Memory Hook."""

    def test_toggle_off_no_capture(
        self,
        container,
        temp_db: Path,
    ) -> None:
        """With toggle OFF, IPC flow should produce 0 agent_message observations."""
        memory = container.memory_service()

        # Hook disabled by default
        config = MemoryHookConfig(enabled=False)
        hook = MemoryHook(memory_service=memory, config=config)

        # Send important message
        msg = AgentMessage.create(
            from_agent="agent1:0",
            to_agent="agent2:0",
            message_type=MessageType.COMMAND,
            payload=json.dumps({"important": True, "command": "test"}),
        )

        obs_id = hook.capture(msg, context={"run_id": "run-1", "task_id": "task-1"})

        # Should not capture
        assert obs_id is None

        # Verify no message observations
        observations = memory.get_recent(limit=10)
        message_obs = [
            o for o in observations
            if o.metadata and o.metadata.get("event_type") == "agent_message"
        ]
        assert len(message_obs) == 0, "Toggle OFF should not capture any messages"

    def test_toggle_on_captures_important_command(
        self,
        container,
        temp_db: Path,
    ) -> None:
        """With toggle ON, send 1 important COMMAND → 1 observation with complete metadata."""
        memory = container.memory_service()

        # Hook enabled
        config = MemoryHookConfig(enabled=True, policy=HookPolicy.IMPORTANT_ONLY)
        hook = MemoryHook(memory_service=memory, config=config)

        # Send important message
        msg = AgentMessage.create(
            from_agent="agent1:0",
            to_agent="agent2:0",
            message_type=MessageType.COMMAND,
            payload=json.dumps({"important": True, "command": "execute task X"}),
        )

        context = {"run_id": "run-integration-1", "task_id": "task-integration-1"}
        obs_id = hook.capture(msg, context=context)

        # Should capture
        assert obs_id is not None

        # Verify observation
        observations = memory.get_recent(limit=10)
        message_obs = [
            o for o in observations
            if o.metadata and o.metadata.get("event_type") == "agent_message"
        ]
        assert len(message_obs) == 1, "Should capture exactly 1 message"

        obs = message_obs[0]
        # Verify complete metadata
        assert obs.metadata.get("run_id") == "run-integration-1"
        assert obs.metadata.get("task_id") == "task-integration-1"
        assert obs.metadata.get("agent_id") == "agent1:0"
        assert obs.metadata.get("session_name") == "agent1"
        assert obs.metadata.get("event_type") == "agent_message"

        # Verify message-specific metadata in extra
        extra = obs.metadata.get("extra", {})
        assert extra.get("from_agent_id") == "agent1:0"
        assert extra.get("to_agent_id") == "agent2:0"
        assert extra.get("message_type") == "COMMAND"
        assert extra.get("message_id") == msg.id
        assert "idempotency_key" in obs.metadata

    def test_retry_same_message_id_no_duplicate(
        self,
        container,
        temp_db: Path,
    ) -> None:
        """Re-send same message_id → still 1 observation (idempotency)."""
        memory = container.memory_service()

        config = MemoryHookConfig(enabled=True, policy=HookPolicy.IMPORTANT_ONLY)
        hook = MemoryHook(memory_service=memory, config=config)

        msg = AgentMessage.create(
            from_agent="agent1:0",
            to_agent="agent2:0",
            message_type=MessageType.COMMAND,
            payload=json.dumps({"important": True, "command": "retry test"}),
        )

        context = {"run_id": "run-retry-1", "task_id": "task-retry-1"}

        # Send same message twice
        obs_id_1 = hook.capture(msg, context)
        obs_id_2 = hook.capture(msg, context)

        # Should return same observation ID
        assert obs_id_1 == obs_id_2

        # Should have only 1 observation
        observations = memory.get_recent(limit=10)
        message_obs = [
            o for o in observations
            if o.metadata and o.metadata.get("event_type") == "agent_message"
        ]
        assert len(message_obs) == 1, "Retry should not create duplicate"

    def test_full_flow_with_broadcast(
        self,
        container,
        temp_db: Path,
    ) -> None:
        """Test broadcast message capture."""
        memory = container.memory_service()

        config = MemoryHookConfig(enabled=True, policy=HookPolicy.IMPORTANT_ONLY)
        hook = MemoryHook(memory_service=memory, config=config)

        # Broadcast message (to_agent="*")
        msg = AgentMessage.create(
            from_agent="coordinator:0",
            to_agent="*",  # Broadcast
            message_type=MessageType.COMMAND,
            payload=json.dumps({"important": True, "command": "shutdown all"}),
        )

        obs_id = hook.capture(msg, context={"run_id": "run-broadcast", "task_id": "task-broadcast"})

        assert obs_id is not None

        # Verify broadcast flag in metadata
        observations = memory.get_recent(limit=10)
        message_obs = [
            o for o in observations
            if o.metadata and o.metadata.get("event_type") == "agent_message"
        ]
        assert len(message_obs) == 1

        extra = message_obs[0].metadata.get("extra", {})
        assert extra.get("broadcast") is True
        assert extra.get("to_agent_id") == "*"
