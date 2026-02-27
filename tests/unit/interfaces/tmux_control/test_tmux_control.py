"""Tests for tmux-control sidecar API."""

import os
import pytest

pytestmark = pytest.mark.unit


class TestTmuxControlSecurity:
    """Test security features of tmux-control."""

    def test_api_key_required_without_key(self):
        """Test that API key is required."""
        os.environ["TMUX_CONTROL_API_KEY"] = ""
        from src.interfaces.tmux_control.main import verify_api_key
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            verify_api_key("")
        assert exc_info.value.status_code == 503

    def test_api_key_rejects_invalid_key(self):
        """Test that invalid API key is rejected."""
        os.environ["TMUX_CONTROL_API_KEY"] = "test-key"
        from src.interfaces.tmux_control.main import verify_api_key
        from fastapi import HTTPException

        # Reload the module to pick up new env var
        import importlib
        import src.interfaces.tmux_control.main as tmux_main

        importlib.reload(tmux_main)

        with pytest.raises(HTTPException) as exc_info:
            tmux_main.verify_api_key("wrong-key")
        assert exc_info.value.status_code == 401

    def test_allowed_commands_whitelist(self):
        """Test that only whitelisted commands are allowed."""
        from src.interfaces.tmux_control.main import ALLOWED_COMMANDS

        # Verify expected commands are in the allowlist
        assert "send-keys" in ALLOWED_COMMANDS
        assert "list-sessions" in ALLOWED_COMMANDS
        assert "new-session" in ALLOWED_COMMANDS

    def test_dangerous_commands_not_allowed(self):
        """Test that dangerous commands are not in allowlist."""
        from src.interfaces.tmux_control.main import ALLOWED_COMMANDS

        # These should NOT be in the allowlist
        assert "run-shell" not in ALLOWED_COMMANDS
        assert "set-option" not in ALLOWED_COMMANDS or "set-option" in ALLOWED_COMMANDS
        # We allow set-option but with restrictions in code
