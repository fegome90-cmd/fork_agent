"""iTerm2 multiplexer adapter.

Concrete implementation of MultiplexerAdapter for iTerm2 on macOS.
Uses AppleScript via subprocess.run for all iTerm2 interactions.
"""

from __future__ import annotations

import logging
import os
import platform
import shlex
import subprocess

from src.domain.ports.multiplexer_adapter import MultiplexerAdapter, PaneInfo, SpawnOptions

logger = logging.getLogger(__name__)

_ITERM_TIMEOUT = 15


def _escape_applescript(s: str) -> str:
    """Escape a string for safe interpolation into AppleScript."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _run_applescript(
    script: str, timeout: int = _ITERM_TIMEOUT
) -> subprocess.CompletedProcess[str]:
    """Execute an AppleScript string via osascript."""
    return subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


class Iterm2Adapter(MultiplexerAdapter):
    """Adapter for iTerm2 terminal on macOS.

    Uses AppleScript to control iTerm2 sessions. Only available on macOS
    with TERM_PROGRAM=iTerm.app.
    """

    name = "iterm2"

    def detect(self) -> bool:
        """Detect iTerm2 on macOS via TERM_PROGRAM env var."""
        return platform.system() == "Darwin" and os.environ.get("TERM_PROGRAM") == "iTerm.app"

    def spawn(self, options: SpawnOptions) -> PaneInfo:
        """Spawn a new iTerm2 session running the given command.

        Uses AppleScript to tell iTerm2 to create a new session
        in the current window and write the command.
        """
        escaped_name = _escape_applescript(options.name) if options.name else ""
        escaped_command = _escape_applescript(options.command)

        env_setup = ""
        if options.env:
            exports = "; ".join(f"export {k}={shlex.quote(v)}" for k, v in options.env.items())
            env_setup = f' write text "{_escape_applescript(exports)}"'

        if options.workdir:
            env_setup += f'; cd "{_escape_applescript(options.workdir)}"'

        name_clause = ""
        if options.name:
            name_clause = f' set name of session to "{escaped_name}"'

        script = f'''
tell application "iTerm2"
    tell current window
        set newTab to (create tab with default profile)
        set session to current session of newTab
        {name_clause}
        write text "{escaped_command}"{env_setup}
    end tell
end tell
'''

        try:
            result = _run_applescript(script.strip())
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"Timeout spawning iTerm2 session: {options.name}") from e

        if result.returncode != 0:
            raise RuntimeError(f"Failed to spawn iTerm2 session: {result.stderr.strip()}")

        # Get the session ID of the newly created session
        session_id = self._get_current_session_id()
        if not session_id:
            session_id = options.name or "iterm2-unknown"

        return PaneInfo(pane_id=session_id, is_alive=True, title=options.name)

    def kill(self, pane_id: str) -> None:
        """Kill an iTerm2 session by closing its tab."""
        escaped_id = _escape_applescript(pane_id)
        script = f'''
tell application "iTerm2"
    try
        set targetSession to session id "{escaped_id}"
        tell targetSession to close
    on error
        -- Fallback: iterate sessions to find by name
        repeat with aWindow in windows
            repeat with aTab in tabs of aWindow
                repeat with aSession in sessions of aTab
                    if name of aSession is "{escaped_id}" then
                        close aTab
                        return
                    end if
                end repeat
            end repeat
        end repeat
    end try
end tell
'''
        try:
            result = _run_applescript(script.strip())
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"Timeout killing iTerm2 session {pane_id}") from e

        if result.returncode != 0:
            raise RuntimeError(f"Failed to kill iTerm2 session {pane_id}: {result.stderr.strip()}")

    def is_alive(self, pane_id: str) -> bool:
        """Check if an iTerm2 session still exists."""
        escaped_id = _escape_applescript(pane_id)
        script = f'''
tell application "iTerm2"
    try
        set targetSession to session id "{escaped_id}"
        return true
    on error
        return false
    end try
end tell
'''
        try:
            result = _run_applescript(script.strip())
        except subprocess.TimeoutExpired:
            logger.warning("Timeout checking iTerm2 session %s", pane_id)
            return False

        return result.returncode == 0 and "true" in result.stdout.strip().lower()

    def set_title(self, pane_id: str, title: str) -> None:
        """Set the name of an iTerm2 session."""
        escaped_id = _escape_applescript(pane_id)
        escaped_title = _escape_applescript(title)
        script = f'''
tell application "iTerm2"
    try
        set targetSession to session id "{escaped_id}"
        set name of targetSession to "{escaped_title}"
    on error
        -- Fallback: try by session name
        repeat with aWindow in windows
            repeat with aTab in tabs of aWindow
                repeat with aSession in sessions of aTab
                    if name of aSession is "{escaped_id}" then
                        set name of aSession to "{escaped_title}"
                        return
                    end if
                end repeat
            end repeat
        end repeat
    end try
end tell
'''
        try:
            result = _run_applescript(script.strip())
        except subprocess.TimeoutExpired:
            logger.warning("Timeout setting title on iTerm2 session %s", pane_id)
            return

        if result.returncode != 0:
            logger.warning(
                "Failed to set title on iTerm2 session %s: %s",
                pane_id,
                result.stderr.strip(),
            )

    def configure_pane(self, pane_id: str, remain_on_exit: bool = True) -> None:
        """Configure iTerm2 session behavior on exit.

        iTerm2 manages session exit behavior via its profile settings.
        This is a best-effort no-op with a debug log.
        """
        logger.debug(
            "iTerm2 session %s configure_pane(remain_on_exit=%s) — "
            "iTerm2 manages exit behavior via profile settings",
            pane_id,
            remain_on_exit,
        )

    def _get_current_session_id(self) -> str | None:
        """Get the ID of the current (most recently created) iTerm2 session."""
        script = """
tell application "iTerm2"
    tell current window
        return id of current session of current tab
    end tell
end tell
"""
        try:
            result = _run_applescript(script.strip())
        except subprocess.TimeoutExpired:
            return None

        if result.returncode == 0:
            return result.stdout.strip()
        return None
