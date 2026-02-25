from src.infrastructure.tmux_orchestrator.dead_letter_queue import (
    DeadLetterItem,
    DeadLetterQueue,
)


class TestDeadLetterQueue:
    def test_initial_state_empty(self):
        dlq = DeadLetterQueue()
        assert dlq.is_empty() is True
        assert dlq.size() == 0

    def test_add_item(self):
        dlq = DeadLetterQueue()
        dlq.add("session1", 0, {"msg": "test"}, "error", 1)
        assert dlq.size() == 1

    def test_get_item(self):
        dlq = DeadLetterQueue()
        dlq.add("session1", 0, {"msg": "test"}, "error", 1)
        item = dlq.get(timeout=1.0)
        assert item is not None
        assert item.session == "session1"
        assert item.window == 0

    def test_get_empty_returns_none(self):
        dlq = DeadLetterQueue()
        item = dlq.get(timeout=0.1)
        assert item is None

    def test_get_all(self):
        dlq = DeadLetterQueue()
        dlq.add("session1", 0, {"msg": "1"}, "error1", 1)
        dlq.add("session2", 1, {"msg": "2"}, "error2", 2)
        items = dlq.get_all()
        assert len(items) == 2

    def test_requeue(self):
        dlq = DeadLetterQueue()
        dlq.add("session1", 0, {"msg": "test"}, "error", 1)
        item = dlq.get(timeout=1.0)
        dlq.requeue(item)
        assert dlq.size() == 1

    def test_persist_and_load(self, tmp_path):
        dlq = DeadLetterQueue(persist_path=tmp_path / "dlq.json")
        dlq.add("session1", 0, {"msg": "test"}, "error", 1)
        dlq.persist()

        dlq2 = DeadLetterQueue(persist_path=tmp_path / "dlq.json")
        count = dlq2.load()
        assert count == 1

    def test_max_size(self, tmp_path):  # noqa: ARG002
        dlq = DeadLetterQueue(max_size=2)
        dlq.add("s1", 0, {}, "e1", 1)
        dlq.add("s2", 0, {}, "e2", 1)
        dlq.add("s3", 0, {}, "e3", 1)
        assert dlq.size() == 2


class TestDeadLetterItem:
    def test_create_item(self):
        item = DeadLetterItem(
            timestamp=1234567890.0,
            session="test",
            window=0,
            message={"key": "value"},
            error="test error",
            attempts=3,
        )
        assert item.session == "test"
        assert item.attempts == 3
