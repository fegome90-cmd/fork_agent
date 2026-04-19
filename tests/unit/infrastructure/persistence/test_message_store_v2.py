import pytest
from pathlib import Path
from src.domain.entities.message import AgentMessage, MessageType
from src.infrastructure.persistence.message_store import MessageStore
from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection

@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test_messages.db"
    config = DatabaseConfig(db_path=db_path)
    conn = DatabaseConnection(config=config)
    return conn

def test_message_store_saves_and_retrieves(temp_db):
    store = MessageStore(connection=temp_db)
    
    msg = AgentMessage.create(
        from_agent="s1:0",
        to_agent="s2:0",
        message_type=MessageType.COMMAND,
        payload="ping"
    )
    
    store.save(msg)
    history = store.get_history("s2:0")
    
    assert len(history) == 1
    assert history[0].payload == "ping"
    assert history[0].from_agent == "s1:0"
