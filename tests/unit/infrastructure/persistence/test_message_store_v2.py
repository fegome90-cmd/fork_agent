import pytest

from src.domain.entities.message import AgentMessage, MessageType
from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
from src.infrastructure.persistence.message_store import MessageStore


@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test_messages.db"
    config = DatabaseConfig(db_path=db_path)
    conn = DatabaseConnection(config=config)
    return conn


def test_message_store_saves_and_retrieves(temp_db):
    store = MessageStore(connection=temp_db)

    msg = AgentMessage.create(
        from_agent="s1:0", to_agent="s2:0", message_type=MessageType.COMMAND, payload="ping"
    )

    store.save(msg)
    history = store.get_history("s2:0")

    assert len(history) == 1
    assert history[0].payload == "ping"
    assert history[0].from_agent == "s1:0"


def test_mark_as_read_sets_flag(temp_db):
    store = MessageStore(connection=temp_db)

    msg = AgentMessage.create(
        from_agent="s1:0", to_agent="s2:0", message_type=MessageType.COMMAND, payload="test"
    )
    msg_id = store.save(msg)

    count = store.mark_as_read([msg_id])
    assert count == 1

    with temp_db as conn:
        row = conn.execute("SELECT is_read FROM messages WHERE id = ?", (msg_id,)).fetchone()
        assert row is not None
        assert row["is_read"] == 1


def test_mark_as_read_empty_list(temp_db):
    store = MessageStore(connection=temp_db)
    count = store.mark_as_read([])
    assert count == 0


def test_mark_as_read_multiple(temp_db):
    store = MessageStore(connection=temp_db)

    msg1 = AgentMessage.create(
        from_agent="s1:0", to_agent="s2:0", message_type=MessageType.COMMAND, payload="test"
    )
    id1 = store.save(msg1)

    msg2 = AgentMessage.create(
        from_agent="s1:0", to_agent="s2:1", message_type=MessageType.COMMAND, payload="test"
    )
    id2 = store.save(msg2)

    count = store.mark_as_read([id1, id2])
    assert count == 2


def test_cleanup_expired_purges_old_read_messages(temp_db):
    import time

    store = MessageStore(connection=temp_db)

    msg = AgentMessage.create(
        from_agent="s1:0", to_agent="s2:0", message_type=MessageType.COMMAND, payload="test"
    )
    msg_id = store.save(msg)
    store.mark_as_read([msg_id])

    # Backdate the message so it's older than 5 minutes
    six_min_ago_ms = int(time.time() * 1000) - (6 * 60 * 1000)
    with temp_db as conn:
        conn.execute(
            "UPDATE messages SET created_at = ?, expires_at = ? WHERE id = ?",
            (six_min_ago_ms, six_min_ago_ms + 86_400_000, msg_id),
        )
        conn.commit()

    store.cleanup_expired()

    with temp_db as conn:
        row = conn.execute("SELECT COUNT(*) as c FROM messages WHERE id = ?", (msg_id,)).fetchone()
        assert row["c"] == 0


def test_unread_not_purged_by_cleanup(temp_db):
    import time

    store = MessageStore(connection=temp_db)

    msg = AgentMessage.create(
        from_agent="s1:0", to_agent="s2:0", message_type=MessageType.COMMAND, payload="test"
    )
    msg_id = store.save(msg)

    # Backdate but keep expires_at far in the future so TTL doesn't expire it
    six_min_ago_ms = int(time.time() * 1000) - (6 * 60 * 1000)
    with temp_db as conn:
        conn.execute(
            "UPDATE messages SET created_at = ?, expires_at = ? WHERE id = ?",
            (six_min_ago_ms, six_min_ago_ms + 86_400_000, msg_id),
        )
        conn.commit()

    store.cleanup_expired()

    with temp_db as conn:
        row = conn.execute("SELECT COUNT(*) as c FROM messages WHERE id = ?", (msg_id,)).fetchone()
        assert row["c"] == 1
