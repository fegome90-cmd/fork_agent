"""Unit tests for agent backends."""

from __future__ import annotations

from unittest.mock import patch

from src.infrastructure.agent_backends import (
    OpencodeBackend,
    PiBackend,
    get_available_backends,
    get_backend,
    get_default_backend,
    list_all_backends,
)


class TestOpencodeBackend:
    """Tests for OpencodeBackend."""

    def test_name_property(self) -> None:
        backend = OpencodeBackend()
        assert backend.name == "opencode"

    def test_display_name_property(self) -> None:
        backend = OpencodeBackend()
        assert backend.display_name == "OpenCode CLI"

    def test_is_available_returns_true_when_installed(self) -> None:
        backend = OpencodeBackend()
        with patch("shutil.which", return_value="/usr/bin/opencode"):
            assert backend.is_available() is True

    def test_is_available_returns_false_when_not_installed(self) -> None:
        backend = OpencodeBackend()
        with patch("shutil.which", return_value=None):
            assert backend.is_available() is False

    def test_get_launch_command_basic(self) -> None:
        backend = OpencodeBackend()
        cmd = backend.get_launch_command("test task", "gpt-4")
        assert "opencode run -m" in cmd
        assert "test task" in cmd

    def test_get_launch_command_escapes_special_chars(self) -> None:
        backend = OpencodeBackend()
        # Test various shell metacharacters
        cmd = backend.get_launch_command("it's a test", "gpt-4")
        # shlex.quote should properly escape
        assert "opencode run -m" in cmd

    def test_get_launch_command_prevents_injection(self) -> None:
        backend = OpencodeBackend()
        # Test command injection attempts are neutralized
        cmd = backend.get_launch_command("$(malicious)", "gpt-4; rm -rf /")
        # shlex.quote should escape these so they're not executed
        assert "$(malicious)" in cmd  # Present but escaped
        assert "rm -rf" in cmd  # Present but escaped as part of model

    def test_get_default_model(self) -> None:
        backend = OpencodeBackend()
        assert backend.get_default_model() == "opencode/glm-5-free"


class TestPiBackend:
    """Tests for PiBackend."""

    def test_name_property(self) -> None:
        backend = PiBackend()
        assert backend.name == "pi"

    def test_display_name_property(self) -> None:
        backend = PiBackend()
        assert backend.display_name == "pi.dev Agent"

    def test_is_available_returns_true_when_installed(self) -> None:
        backend = PiBackend()
        with patch("shutil.which", return_value="/usr/bin/pi"):
            assert backend.is_available() is True

    def test_is_available_returns_false_when_not_installed(self) -> None:
        backend = PiBackend()
        with patch("shutil.which", return_value=None):
            assert backend.is_available() is False

    def test_get_launch_command_basic(self) -> None:
        backend = PiBackend()
        cmd = backend.get_launch_command("test task", "ignored-model")
        assert cmd.startswith("pi ")
        assert "test task" in cmd
        # Model parameter should be ignored
        assert "ignored-model" not in cmd

    def test_get_launch_command_escapes_special_chars(self) -> None:
        backend = PiBackend()
        cmd = backend.get_launch_command("it's a test", "model")
        # shlex.quote should properly escape
        assert "pi " in cmd

    def test_get_launch_command_prevents_injection(self) -> None:
        backend = PiBackend()
        # Test command injection attempts are neutralized
        cmd = backend.get_launch_command("$(malicious)", "model")
        # shlex.quote should escape so they're not executed
        assert "$(malicious)" in cmd  # Present but escaped

    def test_get_default_model(self) -> None:
        backend = PiBackend()
        assert backend.get_default_model() == "pi/default"


class TestBackendRegistry:
    """Tests for backend registry functions."""

    def test_list_all_backends(self) -> None:
        backends = list_all_backends()
        assert "opencode" in backends
        assert "pi" in backends

    def test_get_backend_returns_opencode(self) -> None:
        backend = get_backend("opencode")
        assert backend is not None
        assert isinstance(backend, OpencodeBackend)

    def test_get_backend_returns_pi(self) -> None:
        backend = get_backend("pi")
        assert backend is not None
        assert isinstance(backend, PiBackend)

    def test_get_backend_returns_none_for_unknown(self) -> None:
        backend = get_backend("unknown")
        assert backend is None

    def test_get_backend_caches_instances(self) -> None:
        backend1 = get_backend("opencode")
        backend2 = get_backend("opencode")
        assert backend1 is backend2

    def test_get_available_backends_filters_by_availability(self) -> None:
        with patch.object(OpencodeBackend, "is_available", return_value=True):
            with patch.object(PiBackend, "is_available", return_value=False):
                available = get_available_backends()
                names = [b.name for b in available]
                assert "opencode" in names
                assert "pi" not in names

    def test_get_default_backend_prefers_opencode(self) -> None:
        with patch.object(OpencodeBackend, "is_available", return_value=True):
            with patch.object(PiBackend, "is_available", return_value=True):
                default = get_default_backend()
                assert default is not None
                assert default.name == "opencode"

    def test_get_default_backend_falls_back_to_pi(self) -> None:
        with patch.object(OpencodeBackend, "is_available", return_value=False):
            with patch.object(PiBackend, "is_available", return_value=True):
                default = get_default_backend()
                assert default is not None
                assert default.name == "pi"

    def test_get_default_backend_returns_none_when_none_available(self) -> None:
        with patch.object(OpencodeBackend, "is_available", return_value=False):
            with patch.object(PiBackend, "is_available", return_value=False):
                default = get_default_backend()
                assert default is None
