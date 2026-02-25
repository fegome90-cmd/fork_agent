"""Tests for messaging CLI commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from src.interfaces.cli.messaging_commands import message, run_messaging_cli


class TestMessageGroup:
    """Tests for message command group."""

    def test_message_group_exists(self) -> None:
        """Message command group should be callable."""
        runner = CliRunner()
        result = runner.invoke(message, ["--help"])

        assert result.exit_code == 0
        assert "send" in result.output or "Commands" in result.output


class TestMessageSend:
    """Tests for message send command."""

    def test_send_message_basic(self, tmp_path: Path) -> None:  # noqa: ARG002
        """Should send a message to a specific agent."""
        runner = CliRunner()

        with patch("src.interfaces.cli.messaging_commands._create_messenger") as mock_create:
            mock_messenger = MagicMock()
            mock_messenger.send.return_value = True
            mock_create.return_value = mock_messenger

            result = runner.invoke(
                message,
                ["send", "agent1:0", "Hello from CLI"],
            )

        assert result.exit_code == 0
        assert "sent" in result.output.lower() or "success" in result.output.lower()

    def test_send_message_shows_error_on_failure(self, tmp_path: Path) -> None:  # noqa: ARG002
        """Should show error message if send fails."""
        runner = CliRunner()

        with patch("src.interfaces.cli.messaging_commands._create_messenger") as mock_create:
            mock_messenger = MagicMock()
            mock_messenger.send.return_value = False
            mock_create.return_value = mock_messenger

            result = runner.invoke(
                message,
                ["send", "agent1:0", "Hello"],
            )

        assert result.exit_code != 0 or "failed" in result.output.lower()


class TestMessageBroadcast:
    """Tests for message broadcast command."""

    def test_broadcast_message(self, tmp_path: Path) -> None:  # noqa: ARG002
        """Should broadcast message to all sessions."""
        runner = CliRunner()

        with patch("src.interfaces.cli.messaging_commands._create_messenger") as mock_create:
            mock_messenger = MagicMock()
            mock_messenger.broadcast.return_value = 3
            mock_create.return_value = mock_messenger

            result = runner.invoke(
                message,
                ["broadcast", "Status update"],
            )

        assert result.exit_code == 0
        assert "3" in result.output  # Shows count of messages sent

    def test_broadcast_shows_zero_when_no_sessions(self, tmp_path: Path) -> None:  # noqa: ARG002
        """Should show 0 when no sessions available."""
        runner = CliRunner()

        with patch("src.interfaces.cli.messaging_commands._create_messenger") as mock_create:
            mock_messenger = MagicMock()
            mock_messenger.broadcast.return_value = 0
            mock_create.return_value = mock_messenger

            result = runner.invoke(
                message,
                ["broadcast", "Alert!"],
            )

        assert result.exit_code == 0
        assert "0" in result.output


class TestMessageList:
    """Tests for message list command."""

    def test_list_messages_empty(self, tmp_path: Path) -> None:  # noqa: ARG002
        """Should show message when no messages exist."""
        runner = CliRunner()

        with patch("src.interfaces.cli.messaging_commands._create_messenger") as mock_create:
            mock_messenger = MagicMock()
            mock_messenger.store.get_for_agent.return_value = []
            mock_create.return_value = mock_messenger

            result = runner.invoke(
                message,
                ["list", "--agent", "agent1:0"],
            )

        assert result.exit_code == 0
        # Shows "(0)" when no messages
        assert "(0)" in result.output or "no messages" in result.output.lower()

    def test_list_messages_with_limit(self, tmp_path: Path) -> None:  # noqa: ARG002
        """Should pass limit option to store."""
        runner = CliRunner()

        with patch("src.interfaces.cli.messaging_commands._create_messenger") as mock_create:
            mock_messenger = MagicMock()
            mock_messenger.store.get_for_agent.return_value = []
            mock_create.return_value = mock_messenger

            result = runner.invoke(
                message,
                ["list", "--agent", "agent1:0", "--limit", "50"],
            )

        assert result.exit_code == 0


class TestMessageHistory:
    """Tests for message history command."""

    def test_history_shows_sent_and_received(self, tmp_path: Path) -> None:  # noqa: ARG002
        """Should show both sent and received messages."""
        from src.domain.entities.message import AgentMessage, MessageType

        runner = CliRunner()

        sent = AgentMessage.create(
            from_agent="agent1:0",
            to_agent="agent2:0",
            message_type=MessageType.COMMAND,
            payload="sent msg",
        )
        received = AgentMessage.create(
            from_agent="agent2:0",
            to_agent="agent1:0",
            message_type=MessageType.REPLY,
            payload="reply msg",
        )

        with patch("src.interfaces.cli.messaging_commands._create_messenger") as mock_create:
            mock_messenger = MagicMock()
            mock_messenger.get_history.return_value = [sent, received]
            mock_create.return_value = mock_messenger

            result = runner.invoke(
                message,
                ["history", "agent1:0"],
            )

        assert result.exit_code == 0
        mock_messenger.get_history.assert_called_once()

    def test_history_with_limit(self, tmp_path: Path) -> None:  # noqa: ARG002
        """Should respect limit option."""
        from src.domain.entities.message import AgentMessage, MessageType

        runner = CliRunner()

        msg = AgentMessage.create(
            from_agent="agent2:0",
            to_agent="agent1:0",
            message_type=MessageType.REPLY,
            payload="test",
        )

        with patch("src.interfaces.cli.messaging_commands._create_messenger") as mock_create:
            mock_messenger = MagicMock()
            mock_messenger.get_history.return_value = [msg]
            mock_create.return_value = mock_messenger

            result = runner.invoke(
                message,
                ["history", "agent1:0", "--limit", "20"],
            )

        assert result.exit_code == 0
        # Check that limit was passed
        call_args = mock_messenger.get_history.call_args
        assert call_args[0][0] == "agent1:0"
        assert call_args[1]["limit"] == 20

    def test_history_shows_empty_message(self, tmp_path: Path) -> None:  # noqa: ARG002
        """Should show message when no history found."""
        runner = CliRunner()

        with patch("src.interfaces.cli.messaging_commands._create_messenger") as mock_create:
            mock_messenger = MagicMock()
            mock_messenger.get_history.return_value = []
            mock_create.return_value = mock_messenger

            result = runner.invoke(
                message,
                ["history", "agent1:0"],
            )

        assert result.exit_code == 0
        assert "no history" in result.output.lower() or "0" in result.output.lower()


class TestRunMessagingCli:
    """Tests for run_messaging_cli entry point."""

    def test_run_messaging_cli_returns_int(self) -> None:
        """run_messaging_cli should return an integer."""
        with patch("src.interfaces.cli.messaging_commands.message"):
            result = run_messaging_cli()
        assert isinstance(result, int)


class TestSendErrorHandler:
    """Tests for send command exception handling."""

    def test_send_exception_exits_with_error(self) -> None:
        """Should exit 1 and show error when exception raised."""
        runner = CliRunner()

        with patch("src.interfaces.cli.messaging_commands._create_messenger") as mock_create:
            mock_create.side_effect = RuntimeError("connection failed")

            result = runner.invoke(
                message,
                ["send", "agent1:0", "Hello"],
            )

        assert result.exit_code == 1
        assert "connection failed" in result.output


class TestBroadcastErrorHandler:
    """Tests for broadcast command exception handling."""

    def test_broadcast_exception_exits_with_error(self) -> None:
        """Should exit 1 and show error when exception raised."""
        runner = CliRunner()

        with patch("src.interfaces.cli.messaging_commands._create_messenger") as mock_create:
            mock_create.side_effect = RuntimeError("tmux unavailable")

            result = runner.invoke(
                message,
                ["broadcast", "Alert!"],
            )

        assert result.exit_code == 1
        assert "tmux unavailable" in result.output


class TestListWithoutAgent:
    """Tests for list command without --agent flag."""

    def test_list_without_agent_shows_recent(self) -> None:
        """Should query store directly when no agent specified."""
        from src.domain.entities.message import AgentMessage, MessageType

        runner = CliRunner()

        msg = AgentMessage.create(
            from_agent="agent1:0",
            to_agent="agent2:0",
            message_type=MessageType.COMMAND,
            payload="test payload content",
        )

        with patch("src.interfaces.cli.messaging_commands._create_messenger") as mock_create:
            mock_messenger = MagicMock()
            mock_messenger.store.get_for_agent.return_value = [msg]
            mock_create.return_value = mock_messenger

            result = runner.invoke(
                message,
                ["list"],
            )

        assert result.exit_code == 0
        mock_messenger.store.get_for_agent.assert_called_once_with("*", limit=10)
        assert "COMMAND" in result.output
        assert "test payload content" in result.output

    def test_list_without_agent_empty(self) -> None:
        """Should show 'No recent messages' when no messages and no agent."""
        runner = CliRunner()

        with patch("src.interfaces.cli.messaging_commands._create_messenger") as mock_create:
            mock_messenger = MagicMock()
            mock_messenger.store.get_for_agent.return_value = []
            mock_create.return_value = mock_messenger

            result = runner.invoke(
                message,
                ["list"],
            )

        assert result.exit_code == 0
        assert "no recent messages" in result.output.lower()


class TestListWithAgentMessages:
    """Tests for list command displaying actual messages."""

    def test_list_with_agent_shows_messages(self) -> None:
        """Should display message details when agent has messages."""
        from src.domain.entities.message import AgentMessage, MessageType

        runner = CliRunner()

        msg = AgentMessage.create(
            from_agent="agent1:0",
            to_agent="agent2:0",
            message_type=MessageType.COMMAND,
            payload="do the thing",
        )

        with patch("src.interfaces.cli.messaging_commands._create_messenger") as mock_create:
            mock_messenger = MagicMock()
            mock_messenger.get_messages.return_value = [msg]
            mock_create.return_value = mock_messenger

            result = runner.invoke(
                message,
                ["list", "--agent", "agent2:0"],
            )

        assert result.exit_code == 0
        assert "COMMAND" in result.output
        assert "agent1:0" in result.output
        assert "do the thing" in result.output

    def test_list_truncates_long_payload(self) -> None:
        """Should truncate payload longer than 100 chars with ellipsis."""
        from src.domain.entities.message import AgentMessage, MessageType

        runner = CliRunner()

        long_payload = "x" * 150
        msg = AgentMessage.create(
            from_agent="agent1:0",
            to_agent="agent2:0",
            message_type=MessageType.COMMAND,
            payload=long_payload,
        )

        with patch("src.interfaces.cli.messaging_commands._create_messenger") as mock_create:
            mock_messenger = MagicMock()
            mock_messenger.get_messages.return_value = [msg]
            mock_create.return_value = mock_messenger

            result = runner.invoke(
                message,
                ["list", "--agent", "agent2:0"],
            )

        assert result.exit_code == 0
        assert "..." in result.output


class TestListErrorHandler:
    """Tests for list command exception handling."""

    def test_list_exception_exits_with_error(self) -> None:
        """Should exit 1 and show error when exception raised."""
        runner = CliRunner()

        with patch("src.interfaces.cli.messaging_commands._create_messenger") as mock_create:
            mock_create.side_effect = RuntimeError("db error")

            result = runner.invoke(
                message,
                ["list", "--agent", "agent1:0"],
            )

        assert result.exit_code == 1
        assert "db error" in result.output


class TestHistoryErrorHandler:
    """Tests for history command exception handling."""

    def test_history_exception_exits_with_error(self) -> None:
        """Should exit 1 and show error when exception raised."""
        runner = CliRunner()

        with patch("src.interfaces.cli.messaging_commands._create_messenger") as mock_create:
            mock_create.side_effect = RuntimeError("store unavailable")

            result = runner.invoke(
                message,
                ["history", "agent1:0"],
            )

        assert result.exit_code == 1
        assert "store unavailable" in result.output
