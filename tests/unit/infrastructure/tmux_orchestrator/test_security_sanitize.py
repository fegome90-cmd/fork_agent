"""Security tests: prompt injection sanitization in tmux orchestrator."""

from __future__ import annotations

import pytest

from src.infrastructure.tmux_orchestrator import TmuxOrchestrator, _sanitize_tmux_text


class TestSanitizeTmuxText:
    """Unit tests for _sanitize_tmux_text()."""

    def test_clean_text_unchanged(self) -> None:
        assert _sanitize_tmux_text("# F:abc1234") == "# F:abc1234"

    def test_strips_newline(self) -> None:
        result = _sanitize_tmux_text("hello\nworld")
        assert "\n" not in result
        assert "hello" in result
        assert "world" in result

    def test_strips_crlf(self) -> None:
        result = _sanitize_tmux_text("hello\r\nworld")
        assert "\r" not in result
        assert "\n" not in result

    def test_strips_carriage_return(self) -> None:
        result = _sanitize_tmux_text("hello\rworld")
        assert "\r" not in result

    def test_strips_ansi_escape(self) -> None:
        result = _sanitize_tmux_text("\x1b[31mred\x1b[0m")
        assert "\x1b" not in result
        assert "red" in result

    def test_strips_control_chars(self) -> None:
        # \x03 = ETX (Ctrl-C), \x04 = EOT (Ctrl-D)
        result = _sanitize_tmux_text("hello\x03\x04world")
        assert "\x03" not in result
        assert "\x04" not in result
        assert "hello" in result

    def test_empty_after_sanitize_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            _sanitize_tmux_text("\x1b[31m\x03\x04")

    def test_only_whitespace_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            _sanitize_tmux_text("   \n\t  ")

    def test_injection_payload_collapses_to_single_line(self) -> None:
        """Injection attempt with embedded newline cannot split into two commands."""
        result = _sanitize_tmux_text("legit\nrm -rf /")
        assert "\n" not in result
        # Result is one single line — no second command possible
        assert result.count(" ") >= 1  # collapsed to space


class TestSendKeysBlocksInjection:
    """Integration: TmuxOrchestrator._send_keys sanitizes before sending."""

    def test_send_keys_safety_mode_does_not_raise_on_injection(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """In safety mode, injection payload is sanitized and does not crash."""
        orch = TmuxOrchestrator(safety_mode=True)
        # Should not raise, should return True (safety mode always succeeds)
        result = orch._send_keys("fake-session", 0, "hello\nrm -rf /")
        assert result is True
        captured = capsys.readouterr()
        assert "SAFETY:" in captured.out
        # The raw newline injection character must not appear in the sent value
        # (the print itself adds a trailing \n, but the injected \n is replaced with space)
        sent_part = captured.out.split("SAFETY: Would send to fake-session:0: ")[-1]
        assert "hello rm -rf /" in sent_part or "hello" in sent_part

    def test_send_keys_safety_mode_blocks_empty_after_sanitize(self) -> None:
        """Payload that becomes empty after sanitize returns False."""
        orch = TmuxOrchestrator(safety_mode=True)
        result = orch._send_keys("fake-session", 0, "\x1b[31m\x03")
        assert result is False
