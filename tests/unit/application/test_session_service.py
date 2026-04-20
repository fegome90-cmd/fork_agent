"""Unit tests for SessionService."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.application.exceptions import ServiceError, SessionNotFoundError
from src.domain.entities.session import Session


class TestStartSession:
    """Tests for SessionService.start_session."""

    @pytest.fixture
    def mock_repository(self) -> MagicMock:
        return MagicMock(spec=SessionRepositorySpec())

    def test_start_session_creates_and_returns(self, mock_repository: MagicMock) -> None:
        from src.application.services.session_service import SessionService

        mock_repository.get_active.return_value = None
        service = SessionService(repository=mock_repository)

        session = service.start_session(
            project="my-project",
            directory="/tmp/work",
            goal="Implement feature X",
        )

        assert session.project == "my-project"
        assert session.directory == "/tmp/work"
        assert session.goal == "Implement feature X"
        assert session.ended_at is None
        assert session.is_active() is True
        mock_repository.create.assert_called_once()

    def test_start_session_auto_ends_previous_active(self, mock_repository: MagicMock) -> None:
        from src.application.services.session_service import SessionService

        existing = Session(
            id="old-id",
            project="my-project",
            directory="/tmp/old",
            started_at=1000000,
            ended_at=None,
            goal=None,
            instructions=None,
            summary=None,
        )
        mock_repository.get_active.return_value = existing
        service = SessionService(repository=mock_repository)

        session = service.start_session(
            project="my-project",
            directory="/tmp/new",
        )

        mock_repository.end_session.assert_called_once_with(
            existing.id,
            summary="Auto-ended: new session started",
        )
        mock_repository.create.assert_called_once()
        assert session.id != "old-id"

    def test_start_session_without_goal_or_instructions(self, mock_repository: MagicMock) -> None:
        from src.application.services.session_service import SessionService

        mock_repository.get_active.return_value = None
        service = SessionService(repository=mock_repository)

        session = service.start_session(
            project="minimal-project",
            directory="/tmp/minimal",
        )

        assert session.goal is None
        assert session.instructions is None
        assert session.summary is None

    @patch("src.application.services.session_service.uuid")
    def test_start_session_uses_generated_uuid(
        self, mock_uuid: MagicMock, mock_repository: MagicMock
    ) -> None:
        from src.application.services.session_service import SessionService

        mock_uuid.uuid4.return_value = "fixed-uuid-1234"
        mock_repository.get_active.return_value = None
        service = SessionService(repository=mock_repository)

        session = service.start_session(project="proj", directory="/d")

        assert session.id == "fixed-uuid-1234"

    def test_start_session_wraps_repository_error(self, mock_repository: MagicMock) -> None:
        from src.application.services.session_service import SessionService

        mock_repository.get_active.side_effect = RuntimeError("DB down")
        service = SessionService(repository=mock_repository)

        with pytest.raises(ServiceError, match="Failed to start session"):
            service.start_session(project="proj", directory="/d")


class TestEndSession:
    """Tests for SessionService.end_session."""

    @pytest.fixture
    def mock_repository(self) -> MagicMock:
        return MagicMock()

    def test_end_session_delegates_to_repository(self, mock_repository: MagicMock) -> None:
        from src.application.services.session_service import SessionService

        ended = Session(
            id="s1",
            project="proj",
            directory="/d",
            started_at=1000,
            ended_at=2000,
            goal=None,
            instructions=None,
            summary="Done",
        )
        mock_repository.end_session.return_value = ended
        service = SessionService(repository=mock_repository)

        result = service.end_session("s1", summary="Done")

        assert result.ended_at == 2000
        assert result.summary == "Done"
        mock_repository.end_session.assert_called_once_with("s1", "Done")

    def test_end_session_raises_on_not_found(self, mock_repository: MagicMock) -> None:
        from src.application.services.session_service import SessionService

        mock_repository.end_session.side_effect = SessionNotFoundError("Session not found.")
        service = SessionService(repository=mock_repository)

        with pytest.raises(SessionNotFoundError):
            service.end_session("nonexistent")

    def test_end_session_wraps_unexpected_error(self, mock_repository: MagicMock) -> None:
        from src.application.services.session_service import SessionService

        mock_repository.end_session.side_effect = RuntimeError("connection lost")
        service = SessionService(repository=mock_repository)

        with pytest.raises(ServiceError, match="Failed to end session"):
            service.end_session("s1")


class TestListSessions:
    """Tests for SessionService.list_sessions."""

    @pytest.fixture
    def mock_repository(self) -> MagicMock:
        return MagicMock()

    def test_list_sessions_returns_recent(self, mock_repository: MagicMock) -> None:
        from src.application.services.session_service import SessionService

        s1 = Session(
            id="s1",
            project="p",
            directory="/d",
            started_at=1000,
            ended_at=2000,
            goal=None,
            instructions=None,
            summary=None,
        )
        mock_repository.get_recent.return_value = [s1]
        service = SessionService(repository=mock_repository)

        result = service.list_sessions("p", limit=10)

        assert len(result) == 1
        assert result[0].id == "s1"
        mock_repository.get_recent.assert_called_once_with("p", limit=10)

    def test_list_sessions_excludes_active_when_flagged(self, mock_repository: MagicMock) -> None:
        from src.application.services.session_service import SessionService

        active = Session(
            id="active",
            project="p",
            directory="/d",
            started_at=1000,
            ended_at=None,
            goal=None,
            instructions=None,
            summary=None,
        )
        ended = Session(
            id="ended",
            project="p",
            directory="/d",
            started_at=1000,
            ended_at=2000,
            goal=None,
            instructions=None,
            summary=None,
        )
        mock_repository.get_recent.return_value = [active, ended]
        service = SessionService(repository=mock_repository)

        result = service.list_sessions("p", include_active=False)

        assert len(result) == 1
        assert result[0].id == "ended"

    def test_list_sessions_wraps_error(self, mock_repository: MagicMock) -> None:
        from src.application.services.session_service import SessionService

        mock_repository.get_recent.side_effect = RuntimeError("fail")
        service = SessionService(repository=mock_repository)

        with pytest.raises(ServiceError, match="Failed to list sessions"):
            service.list_sessions("p")


class TestGetActive:
    """Tests for SessionService.get_active."""

    @pytest.fixture
    def mock_repository(self) -> MagicMock:
        return MagicMock()

    def test_get_active_returns_session(self, mock_repository: MagicMock) -> None:
        from src.application.services.session_service import SessionService

        active = Session(
            id="s1",
            project="p",
            directory="/d",
            started_at=1000,
            ended_at=None,
            goal=None,
            instructions=None,
            summary=None,
        )
        mock_repository.get_active.return_value = active
        service = SessionService(repository=mock_repository)

        result = service.get_active("p")

        assert result is not None
        assert result.id == "s1"

    def test_get_active_returns_none(self, mock_repository: MagicMock) -> None:
        from src.application.services.session_service import SessionService

        mock_repository.get_active.return_value = None
        service = SessionService(repository=mock_repository)

        result = service.get_active("p")

        assert result is None


class TestGetContext:
    """Tests for SessionService.get_context."""

    @pytest.fixture
    def mock_repository(self) -> MagicMock:
        return MagicMock()

    def test_get_context_delegates_with_limit(self, mock_repository: MagicMock) -> None:
        from src.application.services.session_service import SessionService

        mock_repository.get_recent.return_value = []
        service = SessionService(repository=mock_repository)

        result = service.get_context("p", limit=5)

        assert result == []
        mock_repository.get_recent.assert_called_once_with("p", limit=5)

    def test_get_context_wraps_error(self, mock_repository: MagicMock) -> None:
        from src.application.services.session_service import SessionService

        mock_repository.get_recent.side_effect = RuntimeError("fail")
        service = SessionService(repository=mock_repository)

        with pytest.raises(ServiceError, match="Failed to get session context"):
            service.get_context("p")


# Minimal spec for type hints (not used as a real mock base, just for spec)
class SessionRepositorySpec:
    """Specification for SessionRepository interface."""

    def create(self, session: Session) -> None: ...
    def end_session(self, session_id: str, summary: str | None = None) -> Session: ...
    def get_recent(self, project: str, limit: int = 10) -> list[Session]: ...
    def get_active(self, project: str) -> Session | None: ...
