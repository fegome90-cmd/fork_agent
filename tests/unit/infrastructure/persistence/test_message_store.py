"""Tests for SQLite message store."""

from __future__ import annotations

from pathlib import Path

from src.domain.entities.message import AgentMessage, MessageType
from src.infrastructure.persistence.message_store import MessageStore


class TestMessageStoreInit:
    """Tests for MessageStore initialization."""

    def test_creates_database_file(self, tmp_path: Path) -> None:
        """Should create database file on init."""
        db_path = tmp_path / "test.db"
        assert not db_path.exists()

        MessageStore(db_path=db_path)

        assert db_path.exists()

    def test_creates_messages_table(self, tmp_path: Path) -> None:
        """Should create messages table with correct schema."""
        db_path = tmp_path / "test.db"
        MessageStore(db_path=db_path)

        import sqlite3

        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='messages'"
        )
        result = cursor.fetchone()
        conn.close()

        assert result is not None

    def test_creates_indexes(self, tmp_path: Path) -> None:
        """Should create indexes for common queries."""
        db_path = tmp_path / "test.db"
        MessageStore(db_path=db_path)

        import sqlite3

        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='messages'"
        )
        indexes = [row[0] for row in cursor.fetchall()]
        conn.close()

        # Should have indexes on key columns
        assert any("to_agent" in idx for idx in indexes)
        assert any("from_agent" in idx for idx in indexes)


class TestMessageStoreSave:
    """Tests for save method."""

    def test_save_message(self, tmp_path: Path) -> None:
        """Should save message to database."""
        store = MessageStore(db_path=tmp_path / "test.db")
        msg = AgentMessage.create(
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=MessageType.COMMAND,
            payload='{"task": "run"}',
        )

        store.save(msg)

        # Should not raise, message is saved
        messages = store.get_for_agent("s2:0")
        assert len(messages) == 1
        assert messages[0].id == msg.id

    def test_save_with_correlation_id(self, tmp_path: Path) -> None:
        """Should save message with correlation_id."""
        store = MessageStore(db_path=tmp_path / "test.db")
        msg = AgentMessage.create(
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=MessageType.REPLY,
            payload='{"result": "ok"}',
            correlation_id="corr-123",
        )

        store.save(msg)

        messages = store.get_for_agent("s2:0")
        assert messages[0].correlation_id == "corr-123"

    def test_save_sets_expires_at(self, tmp_path: Path) -> None:
        """Should set expires_at to created_at + 24h default."""
        store = MessageStore(db_path=tmp_path / "test.db")
        msg = AgentMessage.create(
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=MessageType.COMMAND,
            payload="test",
        )

        store.save(msg)

        import sqlite3

        conn = sqlite3.connect(str(tmp_path / "test.db"))
        cursor = conn.execute(
            "SELECT created_at, expires_at FROM messages WHERE id = ?",
            (msg.id,),
        )
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        created_at, expires_at = row
        # 24 hours in milliseconds = 86400000
        assert expires_at == created_at + 86400000


class TestMessageStoreGetForAgent:
    """Tests for get_for_agent method."""

    def test_get_messages_for_agent(self, tmp_path: Path) -> None:
        """Should get messages addressed to specific agent."""
        store = MessageStore(db_path=tmp_path / "test.db")
        msg1 = AgentMessage.create(
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=MessageType.COMMAND,
            payload="msg1",
        )
        msg2 = AgentMessage.create(
            from_agent="s1:0",
            to_agent="s3:0",  # Different target
            message_type=MessageType.COMMAND,
            payload="msg2",
        )

        store.save(msg1)
        store.save(msg2)

        messages = store.get_for_agent("s2:0")
        assert len(messages) == 1
        assert messages[0].payload == "msg1"

    def test_get_returns_newest_first(self, tmp_path: Path) -> None:
        """Should return messages in descending order by created_at."""
        store = MessageStore(db_path=tmp_path / "test.db")

        # Create messages with slight time difference
        import time

        msg1 = AgentMessage.create(
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=MessageType.COMMAND,
            payload="first",
        )
        time.sleep(0.01)
        msg2 = AgentMessage.create(
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=MessageType.COMMAND,
            payload="second",
        )

        store.save(msg1)
        store.save(msg2)

        messages = store.get_for_agent("s2:0")
        assert len(messages) == 2
        assert messages[0].payload == "second"  # Newest first
        assert messages[1].payload == "first"

    def test_get_respects_limit(self, tmp_path: Path) -> None:
        """Should respect limit parameter."""
        store = MessageStore(db_path=tmp_path / "test.db")

        for i in range(10):
            msg = AgentMessage.create(
                from_agent="s1:0",
                to_agent="s2:0",
                message_type=MessageType.COMMAND,
                payload=f"msg{i}",
            )
            store.save(msg)

        messages = store.get_for_agent("s2:0", limit=5)
        assert len(messages) == 5

    def test_get_includes_broadcast_messages(self, tmp_path: Path) -> None:
        """Should include messages with to_agent='*'."""
        store = MessageStore(db_path=tmp_path / "test.db")
        direct_msg = AgentMessage.create(
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=MessageType.COMMAND,
            payload="direct",
        )
        broadcast_msg = AgentMessage.create(
            from_agent="s1:0",
            to_agent="*",
            message_type=MessageType.COMMAND,
            payload="broadcast",
        )

        store.save(direct_msg)
        store.save(broadcast_msg)

        messages = store.get_for_agent("s2:0")
        assert len(messages) == 2
        payloads = {m.payload for m in messages}
        assert "direct" in payloads
        assert "broadcast" in payloads


class TestMessageStoreGetHistory:
    """Tests for get_history method."""

    def test_get_history_includes_sent_and_received(self, tmp_path: Path) -> None:
        """Should include both sent and received messages."""
        store = MessageStore(db_path=tmp_path / "test.db")
        sent = AgentMessage.create(
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=MessageType.COMMAND,
            payload="sent",
        )
        received = AgentMessage.create(
            from_agent="s3:0",
            to_agent="s1:0",
            message_type=MessageType.REPLY,
            payload="received",
        )

        store.save(sent)
        store.save(received)

        history = store.get_history("s1:0")
        assert len(history) == 2
        payloads = {m.payload for m in history}
        assert "sent" in payloads
        assert "received" in payloads

    def test_get_history_respects_limit(self, tmp_path: Path) -> None:
        """Should respect limit parameter."""
        store = MessageStore(db_path=tmp_path / "test.db")

        for i in range(20):
            msg = AgentMessage.create(
                from_agent="s1:0",
                to_agent=f"s{i:02d}:0",
                message_type=MessageType.COMMAND,
                payload=f"msg{i}",
            )
            store.save(msg)

        history = store.get_history("s1:0", limit=10)
        assert len(history) == 10


class TestMessageStoreGetByCorrelation:
    """Tests for get_by_correlation method."""

    def test_get_by_correlation(self, tmp_path: Path) -> None:
        """Should get messages by correlation_id."""
        store = MessageStore(db_path=tmp_path / "test.db")
        correlation_id = "req-123"

        command = AgentMessage.create(
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=MessageType.COMMAND,
            payload="request",
        )
        reply = AgentMessage.create(
            from_agent="s2:0",
            to_agent="s1:0",
            message_type=MessageType.REPLY,
            payload="response",
            correlation_id=correlation_id,
        )

        store.save(command)
        store.save(reply)

        messages = store.get_by_correlation(correlation_id)
        assert len(messages) == 1
        assert messages[0].correlation_id == correlation_id

    def test_get_by_correlation_returns_empty_if_none(self, tmp_path: Path) -> None:
        """Should return empty list if no messages match."""
        store = MessageStore(db_path=tmp_path / "test.db")
        msg = AgentMessage.create(
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=MessageType.COMMAND,
            payload="test",
        )
        store.save(msg)

        messages = store.get_by_correlation("nonexistent")
        assert messages == []


class TestMessageStoreCleanupExpired:
    """Tests for cleanup_expired method."""

    def test_cleanup_removes_expired_messages(self, tmp_path: Path) -> None:
        """Should remove messages past expires_at."""
        store = MessageStore(db_path=tmp_path / "test.db")

        # Create message and manually set expired
        msg = AgentMessage.create(
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=MessageType.COMMAND,
            payload="test",
        )
        store.save(msg)

        # Manually update expires_at to past
        import sqlite3

        conn = sqlite3.connect(str(tmp_path / "test.db"))
        conn.execute("UPDATE messages SET expires_at = 0 WHERE id = ?", (msg.id,))
        conn.commit()
        conn.close()

        removed = store.cleanup_expired()
        assert removed == 1

        messages = store.get_for_agent("s2:0")
        assert len(messages) == 0

    def test_cleanup_keeps_valid_messages(self, tmp_path: Path) -> None:
        """Should not remove messages that haven't expired."""
        store = MessageStore(db_path=tmp_path / "test.db")
        msg = AgentMessage.create(
            from_agent="s1:0",
            to_agent="s2:0",
            message_type=MessageType.COMMAND,
            payload="test",
        )
        store.save(msg)

        removed = store.cleanup_expired()
        assert removed == 0

        messages = store.get_for_agent("s2:0")
        assert len(messages) == 1


class TestMessageStoreGetDbPath:
    """Tests for get_db_path method."""

    def test_get_db_path_returns_path(self, tmp_path: Path) -> None:
        """Should return the database path."""
        db_path = tmp_path / "test.db"
        store = MessageStore(db_path=db_path)

        result = store.get_db_path()

        assert result == db_path

    def test_default_db_path(self) -> None:
        """Should use default path if not specified."""
        store = MessageStore()

        result = store.get_db_path()

        # Should end with .tmux-orchestrator/messages.db
        assert str(result).endswith(".tmux-orchestrator/messages.db")

        # Cleanup - only remove the db file, not the directory (may have other files)
        if result.exists():
            result.unlink()
        store.close()
