from __future__ import annotations

import json
import logging
import queue
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DeadLetterItem:
    timestamp: float
    session: str
    window: int
    message: dict[str, Any]
    error: str
    attempts: int


class DeadLetterQueue:
    """Queue for storing failed messages that could not be delivered.

    Messages are persisted to disk and can be retried later.
    """

    def __init__(self, max_size: int = 1000, persist_path: Path | None = None) -> None:
        self._queue: queue.Queue[DeadLetterItem] = queue.Queue(maxsize=max_size)
        self._persist_path = persist_path
        self._lock = threading.Lock()
        self._processed_count = 0

    def add(
        self,
        session: str,
        window: int,
        message: dict[str, Any],
        error: str,
        attempts: int = 1,
    ) -> None:
        item = DeadLetterItem(
            timestamp=datetime.now().timestamp(),
            session=session,
            window=window,
            message=message,
            error=error,
            attempts=attempts,
        )
        try:
            self._queue.put_nowait(item)
            logger.info(f"Added to DLQ: session={session}, window={window}, error={error}")
        except queue.Full:
            logger.error("Dead letter queue is full, dropping message")

    def get(self, timeout: float = 1.0) -> DeadLetterItem | None:
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def size(self) -> int:
        return self._queue.qsize()

    def is_empty(self) -> bool:
        return self._queue.empty()

    def get_all(self) -> list[DeadLetterItem]:
        items = []
        while not self._queue.empty():
            try:
                items.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return items

    def requeue(self, item: DeadLetterItem) -> None:
        try:
            self._queue.put_nowait(item)
        except queue.Full:
            logger.error("Failed to requeue item, queue is full")

    def persist(self, path: Path | None = None) -> None:
        p = path or self._persist_path
        if p is None:
            logger.warning("No persist path set, skipping")
            return

        items = self.get_all()
        data = [
            {
                "timestamp": item.timestamp,
                "session": item.session,
                "window": item.window,
                "message": item.message,
                "error": item.error,
                "attempts": item.attempts,
            }
            for item in items
        ]

        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Persisted {len(items)} items to {p}")

    def load(self, path: Path | None = None) -> int:
        p = path or self._persist_path
        if p is None or not p.exists():
            return 0

        with open(p) as f:
            data = json.load(f)

        count = 0
        for item in data:
            dlq_item = DeadLetterItem(
                timestamp=item["timestamp"],
                session=item["session"],
                window=item["window"],
                message=item["message"],
                error=item["error"],
                attempts=item["attempts"],
            )
            try:
                self._queue.put_nowait(dlq_item)
                count += 1
            except queue.Full:
                break

        logger.info(f"Loaded {count} items from {p}")
        return count


_dlq_instance: DeadLetterQueue | None = None
_dlq_lock = threading.Lock()


def get_dead_letter_queue() -> DeadLetterQueue:
    global _dlq_instance
    with _dlq_lock:
        if _dlq_instance is None:
            _dlq_instance = DeadLetterQueue()
        return _dlq_instance
