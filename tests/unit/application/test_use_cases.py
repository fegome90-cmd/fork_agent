"""Unit tests for application use cases."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.application.services.terminal.platform_detector import PlatformDetector
from src.application.services.terminal.terminal_spawner import TerminalSpawner
from src.application.use_cases.delete_observation import DeleteObservation
from src.application.use_cases.fork_terminal import (
    create_fork_terminal_use_case,
    fork_terminal_use_case,
)
from src.application.use_cases.get_observation import GetObservation
from src.application.use_cases.list_observations import ListObservations
from src.application.use_cases.save_observation import SaveObservation
from src.application.use_cases.search_observations import SearchObservations
from src.domain.entities.observation import Observation
from src.domain.entities.terminal import (
    PlatformType,
    TerminalConfig,
    TerminalResult,
)
from src.domain.ports.observation_repository import ObservationRepository


# =============================================================================
# Fork Terminal Use Cases Tests
# =============================================================================


class TestForkTerminalUseCase:
    """Tests for fork_terminal_use_case function."""

    def test_fork_terminal_success_macos(self) -> None:
        """Test successful terminal fork on macOS."""
        # Arrange
        mock_detector = MagicMock(spec=PlatformDetector)
        mock_detector.detect.return_value = PlatformType.DARWIN

        mock_spawner = MagicMock(spec=TerminalSpawner)
        mock_result = TerminalResult(success=True, output="Done", exit_code=0)
        mock_spawner.spawn.return_value = mock_result

        # Act
        fork_terminal = fork_terminal_use_case(mock_detector, mock_spawner)
        result = fork_terminal("echo hello")

        # Assert
        mock_detector.detect.assert_called_once()
        mock_spawner.spawn.assert_called_once()
        assert result.success is True
        assert result.output == "Done"
        assert result.exit_code == 0

    def test_fork_terminal_success_linux(self) -> None:
        """Test successful terminal fork on Linux."""
        # Arrange
        mock_detector = MagicMock(spec=PlatformDetector)
        mock_detector.detect.return_value = PlatformType.LINUX

        mock_spawner = MagicMock(spec=TerminalSpawner)
        mock_result = TerminalResult(success=True, output="Linux terminal", exit_code=0)
        mock_spawner.spawn.return_value = mock_result

        # Act
        fork_terminal = fork_terminal_use_case(mock_detector, mock_spawner)
        fork_terminal("ls -la")

        # Assert
        mock_detector.detect.assert_called_once()
        mock_spawner.spawn.assert_called_once()
        call_args = mock_spawner.spawn.call_args
        config: TerminalConfig = call_args[0][1]
        assert config.platform == PlatformType.LINUX

    def test_fork_terminal_success_windows(self) -> None:
        """Test successful terminal fork on Windows."""
        # Arrange
        mock_detector = MagicMock(spec=PlatformDetector)
        mock_detector.detect.return_value = PlatformType.WINDOWS

        mock_spawner = MagicMock(spec=TerminalSpawner)
        mock_result = TerminalResult(success=True, output="Done", exit_code=0)
        mock_spawner.spawn.return_value = mock_result

        # Act
        fork_terminal = fork_terminal_use_case(mock_detector, mock_spawner)
        fork_terminal("dir")

        # Assert
        mock_detector.detect.assert_called_once()
        mock_spawner.spawn.assert_called_once()
        call_args = mock_spawner.spawn.call_args
        config: TerminalConfig = call_args[0][1]
        assert config.platform == PlatformType.WINDOWS

    def test_fork_terminal_failure(self) -> None:
        """Test terminal fork that fails."""
        # Arrange
        mock_detector = MagicMock(spec=PlatformDetector)
        mock_detector.detect.return_value = PlatformType.DARWIN

        mock_spawner = MagicMock(spec=TerminalSpawner)
        mock_result = TerminalResult(success=False, output="Error", exit_code=1)
        mock_spawner.spawn.return_value = mock_result

        # Act
        fork_terminal = fork_terminal_use_case(mock_detector, mock_spawner)
        result = fork_terminal("invalid_command")

        # Assert
        assert result.success is False
        assert result.exit_code == 1

    def test_fork_terminal_passes_command(self) -> None:
        """Test that command is passed correctly to spawner."""
        # Arrange
        mock_detector = MagicMock(spec=PlatformDetector)
        mock_detector.detect.return_value = PlatformType.LINUX

        mock_spawner = MagicMock(spec=TerminalSpawner)
        mock_spawner.spawn.return_value = TerminalResult(success=True, output="", exit_code=0)

        # Act
        fork_terminal = fork_terminal_use_case(mock_detector, mock_spawner)
        fork_terminal("specific_command arg1 arg2")

        # Assert
        call_args = mock_spawner.spawn.call_args
        command_passed = call_args[0][0]
        assert command_passed == "specific_command arg1 arg2"


class TestCreateForkTerminalUseCase:
    """Tests for create_fork_terminal_use_case factory function."""

    def test_create_fork_terminal_use_case(self) -> None:
        """Test creating use case with pure functions."""

        # Arrange
        def mock_detect_platform() -> PlatformType:
            return PlatformType.DARWIN

        def mock_spawn_terminal(command: str) -> TerminalResult:
            return TerminalResult(success=True, output="spawned", exit_code=0)

        # Act
        execute = create_fork_terminal_use_case(mock_detect_platform, mock_spawn_terminal)
        result = execute("test command")

        # Assert
        assert result.success is True
        assert result.output == "spawned"

    def test_create_fork_terminal_with_failure(self) -> None:
        """Test use case with function that returns failure."""

        # Arrange
        def mock_detect_platform() -> PlatformType:
            return PlatformType.WINDOWS

        def mock_spawn_terminal(command: str) -> TerminalResult:
            return TerminalResult(success=False, output="failed", exit_code=127)

        # Act
        execute = create_fork_terminal_use_case(mock_detect_platform, mock_spawn_terminal)
        result = execute("exit 127")

        # Assert
        assert result.success is False
        assert result.exit_code == 127

    def test_create_fork_terminal_config_created_correctly(self) -> None:
        """Test that config is created with None terminal."""
        # Arrange
        platform_detected: PlatformType | None = None

        def mock_detect_platform() -> PlatformType:
            nonlocal platform_detected
            platform_detected = PlatformType.LINUX
            return PlatformType.LINUX

        def mock_spawn_terminal(command: str) -> TerminalResult:
            return TerminalResult(success=True, output="ok", exit_code=0)

        # Act
        execute = create_fork_terminal_use_case(mock_detect_platform, mock_spawn_terminal)
        execute("echo test")

        # Assert
        assert platform_detected == PlatformType.LINUX


# =============================================================================
# Observation Use Cases Tests - Fixtures
# =============================================================================


@pytest.fixture
def mock_repository() -> MagicMock:
    """Fixture for mocked observation repository."""
    return MagicMock(spec=ObservationRepository)


@pytest.fixture
def sample_observation() -> Observation:
    """Fixture for a sample observation."""
    return Observation(
        id="obs-123",
        timestamp=1700000000000,
        content="Sample observation content",
        metadata={"source": "test"},
    )


@pytest.fixture
def sample_observations(sample_observation: Observation) -> list[Observation]:
    """Fixture for a list of sample observations."""
    return [
        sample_observation,
        Observation(
            id="obs-456",
            timestamp=1700000001000,
            content="Second observation",
            metadata=None,
        ),
        Observation(
            id="obs-789",
            timestamp=1700000002000,
            content="Third observation",
            metadata={"type": "info"},
        ),
    ]


# =============================================================================
# DeleteObservation Tests
# =============================================================================


class TestDeleteObservation:
    """Tests for DeleteObservation use case."""

    def test_execute_calls_repository_delete(
        self,
        mock_repository: MagicMock,
    ) -> None:
        """Test that execute calls repository delete with correct id."""
        # Arrange
        use_case = DeleteObservation(mock_repository)
        observation_id = "obs-123"

        # Act
        use_case.execute(observation_id)

        # Assert
        mock_repository.delete.assert_called_once_with(observation_id)

    def test_execute_deletes_different_observation_ids(
        self,
        mock_repository: MagicMock,
    ) -> None:
        """Test deleting different observation ids."""
        # Arrange
        use_case = DeleteObservation(mock_repository)
        observation_ids = ["obs-1", "obs-2", "obs-abc"]

        # Act & Assert
        for obs_id in observation_ids:
            use_case.execute(obs_id)
            mock_repository.delete.assert_called_with(obs_id)

    def test_execute_does_not_return_value(
        self,
        mock_repository: MagicMock,
    ) -> None:
        """Test that execute returns None."""
        # Arrange
        use_case = DeleteObservation(mock_repository)

        # Act
        result = use_case.execute("obs-123")

        # Assert
        assert result is None


# =============================================================================
# GetObservation Tests
# =============================================================================


class TestGetObservation:
    """Tests for GetObservation use case."""

    def test_execute_returns_observation_from_repository(
        self,
        mock_repository: MagicMock,
        sample_observation: Observation,
    ) -> None:
        """Test that execute returns observation from repository."""
        # Arrange
        mock_repository.get_by_id.return_value = sample_observation
        use_case = GetObservation(mock_repository)

        # Act
        result = use_case.execute("obs-123")

        # Assert
        mock_repository.get_by_id.assert_called_once_with("obs-123")
        assert result == sample_observation

    def test_execute_passes_correct_observation_id(
        self,
        mock_repository: MagicMock,
    ) -> None:
        """Test that correct observation id is passed to repository."""
        # Arrange
        use_case = GetObservation(mock_repository)
        observation_id = "specific-obs-id"

        # Act
        use_case.execute(observation_id)

        # Assert
        mock_repository.get_by_id.assert_called_once_with(observation_id)

    def test_execute_returns_different_observations(
        self,
        mock_repository: MagicMock,
        sample_observations: list[Observation],
    ) -> None:
        """Test that different observations are returned correctly."""
        # Arrange
        use_case = GetObservation(mock_repository)

        # Act & Assert
        for obs in sample_observations:
            mock_repository.get_by_id.return_value = obs
            result = use_case.execute(obs.id)
            assert result == obs


# =============================================================================
# ListObservations Tests
# =============================================================================


class TestListObservations:
    """Tests for ListObservations use case."""

    def test_execute_returns_all_observations_when_under_limit(
        self,
        mock_repository: MagicMock,
        sample_observations: list[Observation],
    ) -> None:
        """Test that all observations are returned when under limit."""
        # Arrange
        mock_repository.get_all.return_value = sample_observations
        use_case = ListObservations(mock_repository)

        # Act
        result = use_case.execute(limit=10)

        # Assert
        mock_repository.get_all.assert_called_once()
        assert len(result) == 3
        assert result == sample_observations

    def test_execute_respects_limit(
        self,
        mock_repository: MagicMock,
        sample_observations: list[Observation],
    ) -> None:
        """Test that limit is respected."""
        # Arrange
        mock_repository.get_all.return_value = sample_observations
        use_case = ListObservations(mock_repository)

        # Act
        result = use_case.execute(limit=2)

        # Assert
        assert len(result) == 2
        assert result[0] == sample_observations[0]
        assert result[1] == sample_observations[1]

    def test_execute_default_limit_is_10(
        self,
        mock_repository: MagicMock,
        sample_observations: list[Observation],
    ) -> None:
        """Test that default limit is 10."""
        # Arrange
        mock_repository.get_all.return_value = sample_observations
        use_case = ListObservations(mock_repository)

        # Act
        result = use_case.execute()

        # Assert
        mock_repository.get_all.assert_called_once()
        assert len(result) == 3  # All returned since < 10

    def test_execute_limit_zero_returns_empty_list(
        self,
        mock_repository: MagicMock,
    ) -> None:
        """Test that limit zero returns empty list."""
        # Arrange
        mock_repository.get_all.return_value = []
        use_case = ListObservations(mock_repository)

        # Act
        result = use_case.execute(limit=0)

        # Assert
        assert result == []

    def test_execute_with_large_limit_returns_all(
        self,
        mock_repository: MagicMock,
        sample_observations: list[Observation],
    ) -> None:
        """Test that limit larger than available returns all."""
        # Arrange
        mock_repository.get_all.return_value = sample_observations
        use_case = ListObservations(mock_repository)

        # Act
        result = use_case.execute(limit=100)

        # Assert
        assert len(result) == 3


# =============================================================================
# SaveObservation Tests
# =============================================================================


class TestSaveObservation:
    """Tests for SaveObservation use case."""

    def test_execute_creates_and_returns_observation(
        self,
        mock_repository: MagicMock,
    ) -> None:
        """Test that execute creates and returns an observation."""
        # Arrange
        use_case = SaveObservation(mock_repository)

        # Act
        result = use_case.execute("Test content")

        # Assert
        assert result is not None
        assert isinstance(result, Observation)
        assert result.content == "Test content"
        assert result.id is not None
        assert result.timestamp is not None

    def test_execute_calls_repository_create(
        self,
        mock_repository: MagicMock,
    ) -> None:
        """Test that repository create is called."""
        # Arrange
        use_case = SaveObservation(mock_repository)

        # Act
        use_case.execute("Content here")

        # Assert
        mock_repository.create.assert_called_once()
        call_args = mock_repository.create.call_args[0][0]
        assert call_args.content == "Content here"

    def test_execute_with_metadata(
        self,
        mock_repository: MagicMock,
    ) -> None:
        """Test that metadata is properly stored."""
        # Arrange
        use_case = SaveObservation(mock_repository)
        metadata = {"source": "cli", "tags": ["important", "todo"]}

        # Act
        result = use_case.execute("Content with metadata", metadata=metadata)

        # Assert
        assert result.metadata == metadata

    def test_execute_without_metadata(
        self,
        mock_repository: MagicMock,
    ) -> None:
        """Test that observation without metadata has None."""
        # Arrange
        use_case = SaveObservation(mock_repository)

        # Act
        result = use_case.execute("Content without metadata")

        # Assert
        assert result.metadata is None

    def test_execute_generates_unique_ids(
        self,
        mock_repository: MagicMock,
    ) -> None:
        """Test that each save generates a unique id."""
        # Arrange
        use_case = SaveObservation(mock_repository)

        # Act
        result1 = use_case.execute("Content 1")
        result2 = use_case.execute("Content 2")

        # Assert
        assert result1.id != result2.id

    def test_execute_generates_timestamp(
        self,
        mock_repository: MagicMock,
    ) -> None:
        """Test that timestamp is generated."""
        import time

        # Arrange
        use_case = SaveObservation(mock_repository)

        # Act
        before = int(time.time() * 1000)
        result = use_case.execute("Test")
        after = int(time.time() * 1000)

        # Assert
        assert result.timestamp >= before
        assert result.timestamp <= after + 1


# =============================================================================
# SearchObservations Tests
# =============================================================================


class TestSearchObservations:
    """Tests for SearchObservations use case."""

    def test_execute_returns_search_results(
        self,
        mock_repository: MagicMock,
        sample_observations: list[Observation],
    ) -> None:
        """Test that search returns results from repository."""
        # Arrange
        mock_repository.search.return_value = sample_observations
        use_case = SearchObservations(mock_repository)

        # Act
        result = use_case.execute("query")

        # Assert
        mock_repository.search.assert_called_once_with("query", limit=None)
        assert result == sample_observations

    def test_execute_passes_query_to_repository(
        self,
        mock_repository: MagicMock,
    ) -> None:
        """Test that query is passed to repository."""
        # Arrange
        use_case = SearchObservations(mock_repository)

        # Act
        use_case.execute("specific query")

        # Assert
        mock_repository.search.assert_called_once_with("specific query", limit=None)

    def test_execute_with_limit(
        self,
        mock_repository: MagicMock,
        sample_observations: list[Observation],
    ) -> None:
        """Test that limit is passed to repository."""
        # Arrange
        mock_repository.search.return_value = sample_observations[:2]
        use_case = SearchObservations(mock_repository)

        # Act
        result = use_case.execute("query", limit=5)

        # Assert
        mock_repository.search.assert_called_once_with("query", limit=5)
        assert len(result) == 2

    def test_execute_default_limit_is_none(
        self,
        mock_repository: MagicMock,
    ) -> None:
        """Test that default limit is None."""
        # Arrange
        use_case = SearchObservations(mock_repository)

        # Act
        use_case.execute("test")

        # Assert
        mock_repository.search.assert_called_once_with("test", limit=None)

    def test_execute_returns_empty_list_when_no_results(
        self,
        mock_repository: MagicMock,
    ) -> None:
        """Test that empty list is returned when no results."""
        # Arrange
        mock_repository.search.return_value = []
        use_case = SearchObservations(mock_repository)

        # Act
        result = use_case.execute("nonexistent")

        # Assert
        assert result == []

    def test_execute_with_various_queries(
        self,
        mock_repository: MagicMock,
    ) -> None:
        """Test that various queries are passed correctly."""
        # Arrange
        use_case = SearchObservations(mock_repository)
        queries = ["python", "test", "  spaces  ", "special!@#chars"]

        # Act & Assert
        for query in queries:
            use_case.execute(query)
            mock_repository.search.assert_called_with(query, limit=None)
