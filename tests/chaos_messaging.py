"""Chaos Lab: Messaging Stress & Torture Tests.

Designed to force failures, race conditions, and disk/memory exhaustion.
"""

import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from src.application.services.messaging.agent_messenger import AgentMessenger
from src.domain.entities.message import AgentMessage, MessageType
from src.infrastructure.persistence.database import DatabaseConnection
from src.infrastructure.persistence.message_store import MAX_TOTAL_MESSAGES, MessageStore
from src.infrastructure.tmux_orchestrator import TmuxOrchestrator

pytestmark = pytest.mark.bughunt


@pytest.fixture
def messenger(tmp_path):
    # Use a real file-based DB for stress testing WAL mode
    db_path = tmp_path / "chaos.db"
    conn = DatabaseConnection.from_path(db_path)
    store = MessageStore(connection=conn)
    orchestrator = TmuxOrchestrator(safety_mode=False)
    return AgentMessenger(orchestrator=orchestrator, store=store)


def test_flood_and_prune_enforcement(messenger):
    """
    STRESS: Send double the MAX_TOTAL_MESSAGES.
    EXPECT: DB size stays constant at ~5000, no crash.
    """
    flood_count = MAX_TOTAL_MESSAGES * 2
    print(f"\n[FLOOD] Sending {flood_count} messages...")

    start_time = time.time()
    for i in range(flood_count):
        msg = AgentMessage.create("leader:0", "fork-target:0", MessageType.COMMAND, f"payload {i}")
        # We bypass tmux call for raw DB stress
        messenger.store.save(msg)

    end_time = time.time()

    # Verify count
    count = 0
    with messenger.store._connection as conn:
        count = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]

    print(f"[FLOOD] Completed in {end_time - start_time:.2f}s")
    assert count <= MAX_TOTAL_MESSAGES
    print(f"[FLOOD] Hygiene verified: {count} messages in DB (Limit is {MAX_TOTAL_MESSAGES})")


def test_concurrent_write_torture(messenger):
    """
    STRESS: 20 threads writing and cleaning up simultaneously.
    EXPECT: No 'Database is locked' errors due to WAL mode and retries.
    """
    num_threads = 20
    msgs_per_thread = 200
    print(f"\n[CONCURRENCY] Starting {num_threads} attackers...")

    def attack():
        for i in range(msgs_per_thread):
            msg = AgentMessage.create("attacker:0", "victim:0", MessageType.COMMAND, f"burn {i}")
            messenger.store.save(msg)

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(attack) for _ in range(num_threads)]
        for f in futures:
            f.result()  # Should not raise SQLite error

    print("[CONCURRENCY] System survived concurrent writes.")


def test_large_payload_fs_exhaustion(messenger, tmp_path):
    """
    STRESS: Send 100 messages of 1MB each.
    EXPECT: Auto-cleanup triggers and keeps /tmp/fork-messages manageable.
    """
    from unittest.mock import patch

    from src.application.services.messaging.message_protocol import cleanup_temp_files

    # Mocking the temp dir to the test tmp_path
    with patch("src.application.services.messaging.message_protocol.FORK_MSG_TEMP_DIR", tmp_path):
        large_data = "X" * (1024 * 1024)  # 1MB

        print("\n[FS_STRESS] Starting 100MB burst...")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            for i in range(100):
                msg = AgentMessage.create("heavy:0", "receiver:0", MessageType.COMMAND, large_data)
                messenger.send(msg)
                # Force small delay to simulate real-world but fast enough to stress
                if i % 10 == 0:
                    print(f"[FS_STRESS] {i}% done...")

        files = list(tmp_path.glob("fork_msg_*.json"))
        total_size_mb = sum(f.stat().st_size for f in files) / (1024 * 1024)

        print(f"[FS_STRESS] Current /tmp usage: {total_size_mb:.2f} MB ({len(files)} files)")

        # Now we simulate time passing to 71 seconds
        future_time = time.time() + 71
        with patch("time.time", return_value=future_time):
            removed = cleanup_temp_files(max_age_seconds=60)
            print(f"[FS_STRESS] Cleanup removed {removed} expired blobs.")

        assert len(list(tmp_path.glob("fork_msg_*.json"))) == 0
        print("[FS_STRESS] Disk hygiene verified.")
