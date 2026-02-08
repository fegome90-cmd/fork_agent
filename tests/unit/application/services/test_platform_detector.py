"""Unit tests for platform detector service."""

from unittest.mock import MagicMock, patch

from src.application.services.terminal.platform_detector import (
    PlatformDetector,
    PlatformDetectorImpl,
)


class TestPlatformDetectorImpl:
    """Tests for PlatformDetectorImpl class."""

    @patch("platform.system")
    def test_detect_darwin(self, mock_system: MagicMock) -> None:
        """Test detecting macOS (Darwin) platform."""
        mock_system.return_value = "Darwin"

        detector = PlatformDetectorImpl()
        result = detector.detect()

        assert result == "Darwin"
        mock_system.assert_called_once()

    @patch("platform.system")
    def test_detect_linux(self, mock_system: MagicMock) -> None:
        """Test detecting Linux platform."""
        mock_system.return_value = "Linux"

        detector = PlatformDetectorImpl()
        result = detector.detect()

        assert result == "Linux"
        mock_system.assert_called_once()

    @patch("platform.system")
    def test_detect_windows(self, mock_system: MagicMock) -> None:
        """Test detecting Windows platform."""
        mock_system.return_value = "Windows"

        detector = PlatformDetectorImpl()
        result = detector.detect()

        assert result == "Windows"
        mock_system.assert_called_once()

    def test_platform_detector_is_abstract(self) -> None:
        """Test that PlatformDetector is an abstract base class."""
        # PlatformDetector is abstract and cannot be instantiated
        # This test verifies the abstract class is properly defined
        assert hasattr(PlatformDetector, "__abstractmethods__")


class TestPlatformDetectorInterface:
    """Tests for PlatformDetector interface compliance."""

    def test_detect_returns_string(self) -> None:
        """Test that detect method returns a string."""
        detector = PlatformDetectorImpl()
        result = detector.detect()
        assert isinstance(result, str)

    @patch("platform.system")
    def test_detect_returns_valid_platform_name(
        self, mock_system: MagicMock
    ) -> None:
        """Test that detect returns valid platform name."""
        valid_platforms = ["Darwin", "Linux", "Windows"]
        mock_system.return_value = "Linux"

        detector = PlatformDetectorImpl()
        result = detector.detect()

        assert result in valid_platforms
