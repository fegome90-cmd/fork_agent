"""Unit tests for platform detector service."""

from unittest.mock import MagicMock, patch

from src.application.services.terminal.platform_detector import (
    PlatformDetector,
    PlatformDetectorImpl,
)
from src.domain.entities.terminal import PlatformType


class TestPlatformDetectorImpl:
    """Tests for PlatformDetectorImpl class."""

    @patch("platform.system")
    def test_detect_darwin(self, mock_system: MagicMock) -> None:
        """Test detecting macOS (Darwin) platform."""
        mock_system.return_value = "Darwin"

        detector = PlatformDetectorImpl()
        result = detector.detect()

        assert result == PlatformType.DARWIN
        mock_system.assert_called_once()

    @patch("platform.system")
    def test_detect_linux(self, mock_system: MagicMock) -> None:
        """Test detecting Linux platform."""
        mock_system.return_value = "Linux"

        detector = PlatformDetectorImpl()
        result = detector.detect()

        assert result == PlatformType.LINUX
        mock_system.assert_called_once()

    @patch("platform.system")
    def test_detect_windows(self, mock_system: MagicMock) -> None:
        """Test detecting Windows platform."""
        mock_system.return_value = "Windows"

        detector = PlatformDetectorImpl()
        result = detector.detect()

        assert result == PlatformType.WINDOWS
        mock_system.assert_called_once()

    def test_platform_detector_is_abstract(self) -> None:
        """Test that PlatformDetector is an abstract base class."""
        # PlatformDetector is abstract and cannot be instantiated
        # This test verifies the abstract class is properly defined
        assert hasattr(PlatformDetector, "__abstractmethods__")


class TestPlatformDetectorInterface:
    """Tests for PlatformDetector interface compliance."""

    def test_detect_returns_platform_type(self) -> None:
        """Test that detect method returns a PlatformType."""
        detector = PlatformDetectorImpl()
        result = detector.detect()
        assert isinstance(result, PlatformType)

    @patch("platform.system")
    def test_detect_returns_valid_platform_name(self, mock_system: MagicMock) -> None:
        """Test that detect returns valid platform type."""
        valid_platforms = [PlatformType.DARWIN, PlatformType.LINUX, PlatformType.WINDOWS]
        mock_system.return_value = "Linux"

        detector = PlatformDetectorImpl()
        result = detector.detect()

        assert result in valid_platforms
