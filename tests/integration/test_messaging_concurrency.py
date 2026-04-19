import pytest
from pathlib import Path
from src.infrastructure.persistence.container import get_container, get_memory_service, get_agent_messenger
from src.domain.entities.message import AgentMessage, MessageType

def test_concurrency_shared_db(tmp_path):
    db_path = tmp_path / "concurrent.db"
    container = get_container(db_path)
    
    memory_service = get_memory_service(db_path)
    messenger = get_agent_messenger(db_path)
    
    # 1. Save observation
    obs = memory_service.save("Observation 1")
    assert obs.id is not None
    
    # 2. Send message (same DB, same connection pool)
    msg = AgentMessage.create(
        from_agent="s1:0",
        to_agent="s2:0",
        message_type=MessageType.COMMAND,
        payload="Message 1"
    )
    assert messenger.store.save(msg) is None # save returns None
    
    # 3. Verify both exist
    assert len(memory_service.search("Observation")) >= 1
    assert len(messenger.get_history("s2:0")) == 1
