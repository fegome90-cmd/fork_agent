"""Tests for messaging CLI commands using Typer."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from src.interfaces.cli.commands.message import app as message_app
from src.domain.entities.message import MessageType, AgentMessage


@pytest.fixture
def runner() -> CliRunner:
    """Create a Typer CLI runner."""
    return CliRunner()


class TestMessageCommands:
    """Tests for message command group."""

    def test_message_help(self, runner: CliRunner) -> None:
        """Message command should show help."""
        result = runner.invoke(message_app, ["--help"])
        assert result.exit_code == 0
        assert "Manage inter-agent messaging" in result.stdout

    @patch("src.interfaces.cli.commands.message.get_agent_messenger")
    def test_send_message_success(self, mock_get_messenger: MagicMock, runner: CliRunner) -> None:
        """Should send a message successfully."""
        mock_messenger = MagicMock()
        mock_messenger.send.return_value = True
        mock_get_messenger.return_value = mock_messenger

        result = runner.invoke(message_app, ["send", "agent1:0", "hello world"])
        
        assert result.exit_code == 0
        assert "Message sent successfully" in result.stdout
        mock_messenger.send.assert_called_once()

    @patch("src.interfaces.cli.commands.message.get_agent_messenger")
    def test_broadcast_message(self, mock_get_messenger: MagicMock, runner: CliRunner) -> None:
        """Should broadcast a message."""
        mock_messenger = MagicMock()
        mock_messenger.broadcast.return_value = 3
        mock_get_messenger.return_value = mock_messenger

        result = runner.invoke(message_app, ["broadcast", "update everyone"])
        
        assert result.exit_code == 0
        assert "Broadcast sent to 3 windows" in result.stdout
        mock_messenger.broadcast.assert_called_once()

    @patch("src.interfaces.cli.commands.message.get_agent_messenger")
    def test_show_history(self, mock_get_messenger: MagicMock, runner: CliRunner) -> None:
        """Should show message history."""
        mock_messenger = MagicMock()
        # Mock some messages
        msg = AgentMessage.create("a1", "a2", MessageType.COMMAND, "test payload")
        mock_messenger.get_history.return_value = [msg]
        mock_get_messenger.return_value = mock_messenger

        result = runner.invoke(message_app, ["history", "agent1:0"])
        
        assert result.exit_code == 0
        assert "Message History for agent1:0" in result.stdout
        assert "test payload" in result.stdout
        mock_messenger.get_history.assert_called_once_with("agent1:0", limit=20)

    @patch("src.interfaces.cli.commands.message.get_agent_messenger")
    @patch("src.application.services.messaging.message_protocol.cleanup_temp_files")
    def test_cleanup_messages(self, mock_cleanup_fs: MagicMock, mock_get_messenger: MagicMock, runner: CliRunner) -> None:
        """Should cleanup messages."""
        mock_messenger = MagicMock()
        mock_messenger.store.cleanup_expired.return_value = 5
        mock_get_messenger.return_value = mock_messenger
        mock_cleanup_fs.return_value = 10

        result = runner.invoke(message_app, ["cleanup"])
        
        assert result.exit_code == 0
        assert "Cleanup complete" in result.stdout
        assert "Database: 5" in result.stdout
        assert "Filesystem: 10" in result.stdout
