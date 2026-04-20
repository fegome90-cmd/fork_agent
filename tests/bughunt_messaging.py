"""Bug Hunt: Messaging Protocol Reliability.

Targets potential truncation issues in Tmux messaging and validates side-channel signaling.
"""

from unittest.mock import patch

import pytest

from src.application.services.messaging.agent_messenger import AgentMessenger
from src.application.services.messaging.message_protocol import decode_message
from src.domain.entities.message import AgentMessage, MessageType
from src.infrastructure.persistence.database import DatabaseConnection
from src.infrastructure.persistence.message_store import MessageStore
from src.infrastructure.tmux_orchestrator import TmuxOrchestrator

pytestmark = pytest.mark.bughunt


@pytest.fixture
def messenger(tmp_path):
    conn = DatabaseConnection.from_path(tmp_path / "test.db")
    store = MessageStore(connection=conn)
    orchestrator = TmuxOrchestrator(safety_mode=False)
    return AgentMessenger(orchestrator=orchestrator, store=store)


def test_large_message_payload_preservation(messenger, tmp_path):
    """
    BUG HUNT: Tmux display-message has a limit (usually ~200-500 chars).
    If we send a message larger than that, it should still be retrievable
    via the filesystem-backed protocol v2 and Tmux Option side-channel.
    """
    # Create a payload larger than Tmux typical limit
    large_payload = "A" * 2000

    msg = AgentMessage.create(
        from_agent="leader:0",
        to_agent="fork-target:0",
        message_type=MessageType.COMMAND,
        payload=large_payload,
    )

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0

        # We also need to patch FORK_MSG_TEMP_DIR inside message_protocol
        with patch(
            "src.application.services.messaging.message_protocol.FORK_MSG_TEMP_DIR", tmp_path
        ):
            messenger.send(msg)

            # Find the set-option call (new side-channel)
            set_opt_call = None
            for call in mock_run.call_args_list:
                args = call[0][0]
                if "set-option" in args:
                    set_opt_call = args
                    break

            assert set_opt_call is not None, "set-option call not found"

            # The encoded message is the last argument
            encoded_msg = set_opt_call[-1]
            assert encoded_msg.startswith("# F:")

            # Now decode it using protocol v2 logic (it should read from tmp_path)
            decoded = decode_message(encoded_msg)

            assert decoded is not None
            assert len(decoded.payload) == 2000
            assert decoded.payload == large_payload
            assert decoded.id == msg.id


def test_expired_temp_files_cleanup_leak(_messenger, tmp_path):
    """
    BUG HUNT: Do we leak temp files if they are not cleaned up?
    """
    from src.application.services.messaging.message_protocol import (
        cleanup_temp_files,
        encode_message,
    )

    with patch("src.application.services.messaging.message_protocol.FORK_MSG_TEMP_DIR", tmp_path):
        # Create 5 messages
        for i in range(5):
            msg = AgentMessage.create("a", "b", MessageType.COMMAND, f"payload {i}")
            encode_message(msg)

        assert len(list(tmp_path.glob("fork_msg_*.json"))) == 5

        # Run cleanup with -1 age (all should be removed as they are "older" than now + 1s)
        # Use a large time jump
        future_time = 9999999999.0
        with patch("time.time", return_value=future_time):
            removed = cleanup_temp_files(max_age_seconds=-1)
            assert removed == 5

        assert len(list(tmp_path.glob("fork_msg_*.json"))) == 0
