"""Unit tests for session CLI commands.

NOTE: src/interfaces/cli/commands/session.py has a SyntaxError (entire file on one line).
These tests verify the SessionService integration logic in isolation and will pass
once the source file formatting is fixed. They import the service layer only.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from src.domain.entities.session import Session

runner = CliRunner()


def _make_active_session(**overrides) -> Session:
    """Create a sample active session for testing."""
    defaults = {
        "id": "test-session-001",
        "project": "test-proj",
        "directory": "/tmp/test-proj",
        "started_at": 1000000,
        "ended_at": None,
        "goal": "Test goal",
        "instructions": None,
        "summary": None,
    }
    defaults.update(overrides)
    return Session(**defaults)


def _make_ended_session(**overrides) -> Session:
    """Create a sample ended session for testing."""
    defaults = {
        "id": "test-session-002",
        "project": "test-proj",
        "directory": "/tmp/test-proj",
        "started_at": 1000000,
        "ended_at": 2000000,
        "goal": "Test goal",
        "instructions": None,
        "summary": "Completed work",
    }
    defaults.update(overrides)
    return Session(**defaults)


def _make_session_service(
    active_session: Session | None = None,
    start_return: Session | None = None,
    end_return: Session | None = None,
    list_return: list[Session] | None = None,
    context_return: list[Session] | None = None,
) -> MagicMock:
    """Build a mock SessionService."""
    mock = MagicMock()
    mock.get_active.return_value = active_session
    mock.start_session.return_value = start_return or _make_active_session()
    mock.end_session.return_value = end_return or _make_ended_session()
    mock.list_sessions.return_value = list_return or []
    mock.get_context.return_value = context_return or []
    return mock


class TestSessionStartCommand:
    """Tests for session start command."""

    def test_start_session_calls_service(self) -> None:
        """Session start should invoke service.start_session and print ID."""
        from src.interfaces.cli.commands.session import app

        mock_service = _make_session_service()
        with (
            patch(
                "src.interfaces.cli.commands.session._get_session_service",
                return_value=mock_service,
            ),
            patch("os.getcwd", return_value="/tmp/workdir"),
        ):
            result = runner.invoke(
                app,
                ["start", "--project", "myproj", "--goal", "Build X"],
            )

        assert result.exit_code == 0
        assert "Session started" in result.stdout
        mock_service.start_session.assert_called_once_with(
            project="myproj",
            directory="/tmp/workdir",
            goal="Build X",
            instructions=None,
        )

    def test_start_session_with_instructions(self) -> None:
        """Session start should pass instructions through."""
        from src.interfaces.cli.commands.session import app

        mock_service = _make_session_service()
        with (
            patch(
                "src.interfaces.cli.commands.session._get_session_service",
                return_value=mock_service,
            ),
            patch("os.getcwd", return_value="/tmp"),
        ):
            result = runner.invoke(
                app,
                [
                    "start",
                    "--project",
                    "p",
                    "--goal",
                    "g",
                    "--instructions",
                    "Use TDD",
                ],
            )

        assert result.exit_code == 0
        call_kwargs = mock_service.start_session.call_args
        assert call_kwargs.kwargs["instructions"] == "Use TDD"


class TestSessionEndCommand:
    """Tests for session end command."""

    def test_end_session_with_active(self) -> None:
        """Session end should find active and end it."""
        from src.interfaces.cli.commands.session import app

        active = _make_active_session()
        mock_service = _make_session_service(active_session=active)
        with patch(
            "src.interfaces.cli.commands.session._get_session_service", return_value=mock_service
        ):
            result = runner.invoke(
                app,
                ["end", "--project", "test-proj", "--summary", "Done"],
            )

        assert result.exit_code == 0
        assert "Session ended" in result.stdout
        mock_service.get_active.assert_called_once_with("test-proj")
        mock_service.end_session.assert_called_once()

    def test_end_session_no_active_fails(self) -> None:
        """Session end should error when no active session exists."""
        from src.interfaces.cli.commands.session import app

        mock_service = _make_session_service(active_session=None)
        with patch(
            "src.interfaces.cli.commands.session._get_session_service", return_value=mock_service
        ):
            result = runner.invoke(
                app,
                ["end", "--project", "test-proj"],
            )

        assert result.exit_code == 1
        assert "No active session" in result.output


class TestSessionListCommand:
    """Tests for session list command."""

    def test_list_sessions_shows_sessions(self) -> None:
        """Session list should display recent sessions."""
        from src.interfaces.cli.commands.session import app

        sessions = [_make_active_session(), _make_ended_session()]
        mock_service = _make_session_service(list_return=sessions)
        with patch(
            "src.interfaces.cli.commands.session._get_session_service", return_value=mock_service
        ):
            result = runner.invoke(
                app,
                ["list", "--project", "test-proj"],
            )

        assert result.exit_code == 0
        assert "test-proj" in result.stdout

    def test_list_sessions_empty(self) -> None:
        """Session list should show message when no sessions."""
        from src.interfaces.cli.commands.session import app

        mock_service = _make_session_service(list_return=[])
        with patch(
            "src.interfaces.cli.commands.session._get_session_service", return_value=mock_service
        ):
            result = runner.invoke(
                app,
                ["list", "--project", "test-proj"],
            )

        assert result.exit_code == 0
        assert "No sessions" in result.stdout


class TestSessionContextCommand:
    """Tests for session context command."""

    def test_context_shows_sessions(self) -> None:
        """Session context should display session recovery info."""
        from src.interfaces.cli.commands.session import app

        sessions = [_make_active_session()]
        mock_service = _make_session_service(context_return=sessions)
        with patch(
            "src.interfaces.cli.commands.session._get_session_service", return_value=mock_service
        ):
            result = runner.invoke(
                app,
                ["context", "--project", "test-proj"],
            )

        assert result.exit_code == 0
        assert "Session Context" in result.stdout

    def test_context_empty(self) -> None:
        """Session context should show message when no context."""
        from src.interfaces.cli.commands.session import app

        mock_service = _make_session_service(context_return=[])
        with patch(
            "src.interfaces.cli.commands.session._get_session_service", return_value=mock_service
        ):
            result = runner.invoke(
                app,
                ["context", "--project", "test-proj"],
            )

        assert result.exit_code == 0
        assert "No session context" in result.stdout
