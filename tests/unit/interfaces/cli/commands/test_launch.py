"""Tests for fork launch CLI commands — direct main() coverage.

Uses sys.argv mocking per cli-entry-point-coverage pattern.
Validates exit codes, JSON output, and error handling without subprocess.
"""

from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_lifecycle():
    """Patch the lifecycle service for all tests."""
    with patch("src.interfaces.cli.commands.launch._get_service") as mock_get:
        svc = MagicMock()
        mock_get.return_value = svc
        yield svc


@pytest.fixture
def mock_launch_attempt():
    """Create a mock LaunchAttempt with decision=claimed."""
    attempt = MagicMock()
    attempt.decision = "claimed"
    attempt.launch = MagicMock()
    attempt.launch.launch_id = "abc123def456"
    attempt.reason = None
    attempt.existing_launch = None
    return attempt


class TestRequest:
    """fork launch request — claim/suppress/error decisions."""

    def test_claimed_returns_exit_0(self, mock_lifecycle, mock_launch_attempt, capsys):
        mock_lifecycle.request_launch.return_value = mock_launch_attempt

        with patch.object(
            sys,
            "argv",
            [
                "launch",
                "request",
                "--canonical-key",
                "test-key",
                "--surface",
                "test",
                "--owner-type",
                "agent",
                "--owner-id",
                "test-01",
                "--json",
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                from src.interfaces.cli.commands.launch import app

                app(
                    [
                        "request",
                        "--canonical-key",
                        "test-key",
                        "--surface",
                        "test",
                        "--owner-type",
                        "agent",
                        "--owner-id",
                        "test-01",
                        "--json",
                    ]
                )
            assert exc_info.value.code == 0

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["decision"] == "claimed"
        assert data["launch_id"] == "abc123def456"

    def test_suppressed_returns_exit_1(self, mock_lifecycle, capsys):
        attempt = MagicMock()
        attempt.decision = "suppressed"
        attempt.launch = None
        attempt.reason = "Already active"
        attempt.existing_launch = MagicMock()
        mock_lifecycle.request_launch.return_value = attempt

        with pytest.raises(SystemExit) as exc_info:
            from src.interfaces.cli.commands.launch import app

            app(
                [
                    "request",
                    "--canonical-key",
                    "dup-key",
                    "--surface",
                    "test",
                    "--owner-type",
                    "agent",
                    "--owner-id",
                    "test-02",
                    "--json",
                ]
            )
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["decision"] == "suppressed"

    def test_missing_args_shows_error(self):
        with pytest.raises(SystemExit) as exc_info:
            from src.interfaces.cli.commands.launch import app

            app(["request", "--json"])
        assert exc_info.value.code != 0


class TestConfirmSpawning:
    """fork launch confirm-spawning — CAS transition."""

    def test_ok_returns_exit_0(self, mock_lifecycle, capsys):
        mock_lifecycle.confirm_spawning.return_value = True

        with pytest.raises(SystemExit) as exc_info:
            from src.interfaces.cli.commands.launch import app

            app(["confirm-spawning", "--launch-id", "abc123", "--json"])
        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["status"] == "spawning"

    def test_cas_fail_returns_exit_1(self, mock_lifecycle, capsys):
        mock_lifecycle.confirm_spawning.return_value = False

        with pytest.raises(SystemExit) as exc_info:
            from src.interfaces.cli.commands.launch import app

            app(["confirm-spawning", "--launch-id", "abc123", "--json"])
        assert exc_info.value.code == 1


class TestConfirmActive:
    """fork launch confirm-active — full args."""

    def test_ok_returns_exit_0(self, mock_lifecycle, capsys):
        mock_lifecycle.confirm_active.return_value = True

        with pytest.raises(SystemExit) as exc_info:
            from src.interfaces.cli.commands.launch import app

            app(
                [
                    "confirm-active",
                    "--launch-id",
                    "abc123",
                    "--backend",
                    "tmux",
                    "--termination-handle-type",
                    "tmux-session",
                    "--termination-handle-value",
                    "sess-1",
                    "--tmux-session",
                    "sess-1",
                    "--json",
                ]
            )
        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["status"] == "active"


class TestStatus:
    """fork launch status — found/not found."""

    def test_found_returns_exit_0(self, mock_lifecycle, capsys):
        launch = MagicMock()
        launch.launch_id = "abc123"
        launch.status.value = "active"
        mock_lifecycle.get_launch.return_value = launch

        with pytest.raises(SystemExit) as exc_info:
            from src.interfaces.cli.commands.launch import app

            app(["status", "--launch-id", "abc123", "--json"])
        assert exc_info.value.code == 0

    def test_not_found_returns_exit_1(self, mock_lifecycle, capsys):
        mock_lifecycle.get_launch.return_value = None

        with pytest.raises(SystemExit) as exc_info:
            from src.interfaces.cli.commands.launch import app

            app(["status", "--launch-id", "nonexistent", "--json"])
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["reason"] == "not_found"


class TestListActive:
    """fork launch list-active."""

    def test_empty_returns_exit_0(self, mock_lifecycle, capsys):
        mock_lifecycle.list_active_launches.return_value = []

        with pytest.raises(SystemExit) as exc_info:
            from src.interfaces.cli.commands.launch import app

            app(["list-active", "--json"])
        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data == []


class TestErrorHandling:
    """Exception chaining and error output."""

    def test_service_exception_returns_exit_1(self, mock_lifecycle, capsys):
        mock_lifecycle.request_launch.side_effect = RuntimeError("DB connection failed")

        with pytest.raises(SystemExit) as exc_info:
            from src.interfaces.cli.commands.launch import app

            app(
                [
                    "request",
                    "--canonical-key",
                    "err-key",
                    "--surface",
                    "test",
                    "--owner-type",
                    "agent",
                    "--owner-id",
                    "test",
                    "--json",
                ]
            )
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["decision"] == "error"
        assert "DB connection failed" in data["reason"]
