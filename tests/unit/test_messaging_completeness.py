"""Verify 0 message loss under concurrent delivery.

Pattern: 10 senders × 10 messages each = 100 total to 1 receiver.
All 100 must arrive in history. MessageStore uses the same WAL-mode
SQLite connection pool as ObservationRepository.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from src.domain.entities.message import AgentMessage, MessageType
from src.infrastructure.persistence.database import (
    DatabaseConnection,
)
from src.infrastructure.persistence.message_store import MessageStore


@pytest.fixture()
def store(tmp_path):
    """Create a MessageStore backed by a fresh file-based DB."""
    db_path = tmp_path / "msg_race.db"
    conn = DatabaseConnection.from_path(db_path)
    ms = MessageStore(connection=conn)
    yield ms
    conn.close_all()


class TestMessagingCompleteness:
    """Zero message loss under concurrent delivery."""

    def test_100_concurrent_messages_zero_loss(self, store):
        """100 concurrent messages from 10 senders must produce 0 loss."""
        SENDERS = 10
        MSGS_PER_SENDER = 10
        TOTAL = SENDERS * MSGS_PER_SENDER

        barrier = threading.Barrier(SENDERS)

        def send_batch(sender_id: int) -> None:
            barrier.wait(timeout=30)
            for j in range(MSGS_PER_SENDER):
                msg = AgentMessage.create(
                    from_agent=f"sender-{sender_id}:0",
                    to_agent="receiver:0",
                    message_type=MessageType.COMMAND,
                    payload=f"msg-{sender_id}-{j}",
                )
                store.save(msg)

        with ThreadPoolExecutor(max_workers=SENDERS) as pool:
            futures = [pool.submit(send_batch, i) for i in range(SENDERS)]
            for f in futures:
                f.result()

        history = store.get_history("receiver:0")
        assert len(history) == TOTAL, (
            f"Lost {TOTAL - len(history)} messages! Expected {TOTAL}, got {len(history)}"
        )

    def test_concurrent_send_and_receive(self, store):
        """Interleaved send/receive must not crash or lose messages."""
        SENDERS = 5
        RECEIVERS = 5
        MSGS_PER_SENDER = 10
        TOTAL_MSGS = SENDERS * MSGS_PER_SENDER
        PARTICIPANTS = SENDERS + RECEIVERS

        barrier = threading.Barrier(PARTICIPANTS)
        read_errors: list[Exception] = []

        def sender(sid: int) -> None:
            barrier.wait(timeout=30)
            for j in range(MSGS_PER_SENDER):
                msg = AgentMessage.create(
                    from_agent=f"sender-{sid}:0",
                    to_agent=f"receiver-{sid % RECEIVERS}:0",
                    message_type=MessageType.COMMAND,
                    payload=f"interleaved-{sid}-{j}",
                )
                store.save(msg)

        def receiver(rid: int) -> None:
            barrier.wait(timeout=30)
            for _ in range(10):
                try:
                    msgs = store.get_for_agent(f"receiver-{rid}:0")
                    assert isinstance(msgs, list)
                except Exception as exc:
                    read_errors.append(exc)

        with ThreadPoolExecutor(max_workers=PARTICIPANTS) as pool:
            futures = [pool.submit(sender, i) for i in range(SENDERS)] + [
                pool.submit(receiver, i) for i in range(RECEIVERS)
            ]
            for f in futures:
                f.result()

        assert not read_errors, f"Receiver errors: {read_errors}"

        # Count total messages in DB for all receivers
        total = 0
        for rid in range(RECEIVERS):
            history = store.get_history(f"receiver-{rid}:0")
            total += len(history)
        assert total == TOTAL_MSGS, (
            f"Lost {TOTAL_MSGS - total} messages! Expected {TOTAL_MSGS}, got {total}"
        )

    def test_concurrent_broadcast_no_duplication(self, store):
        """Broadcast to_agent='*' must not duplicate messages in history."""
        SENDERS = 10
        MSGS_PER_SENDER = 5

        barrier = threading.Barrier(SENDERS)

        def send_broadcast(sid: int) -> None:
            barrier.wait(timeout=30)
            for j in range(MSGS_PER_SENDER):
                msg = AgentMessage.create(
                    from_agent=f"bcast-sender-{sid}:0",
                    to_agent="*",
                    message_type=MessageType.OBSERVATION,
                    payload=f"broadcast-{sid}-{j}",
                )
                store.save(msg)

        with ThreadPoolExecutor(max_workers=SENDERS) as pool:
            futures = [pool.submit(send_broadcast, i) for i in range(SENDERS)]
            for f in futures:
                f.result()

        # Check that each sender's history has exactly MSGS_PER_SENDER
        for sid in range(SENDERS):
            history = store.get_history(f"bcast-sender-{sid}:0", limit=100)
            sent = [m for m in history if m.from_agent == f"bcast-sender-{sid}:0"]
            assert len(sent) == MSGS_PER_SENDER, (
                f"Sender {sid}: expected {MSGS_PER_SENDER} sent, got {len(sent)}"
            )

        # Verify no duplicates by ID
        all_msgs = store.get_history("bcast-sender-0:0", limit=200)
        all_ids = [m.id for m in all_msgs if m.to_agent == "*"]
        assert len(all_ids) == len(set(all_ids)), "Duplicate message IDs detected!"
