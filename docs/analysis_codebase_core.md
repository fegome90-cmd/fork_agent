# Codebase Core Analysis: fork_terminal.py

## Ratings (1-10)
- **Code Quality:** 7/10
- **Complexity:** 4/10 (Low/Appropriate)
- **Error Handling:** 5/10
- **Multi-platform Support:** 9/10
- **Security:** 3/10 (Command Injection Risk)

## Key Findings
- **Vulnerability:** High risk of command injection as input `command` is directly interpolated into shell strings (especially in macOS `osascript` and Linux `bash -c`).
- **Inconsistent Execution:** macOS uses blocking `subprocess.run` while Windows/Linux use non-blocking `subprocess.Popen`.
- **Robust Linux Support:** Excellent fallback logic across GUI terminals (Gnome, Xterm, etc.) and CLI multiplexers (tmux, zellij).
- **Inconsistent Returns:** macOS returns command output; other platforms return status messages.

## Recommendations
- **Sanitize Input:** Use `shlex.quote` for Linux/macOS and proper escaping for Windows to prevent arbitrary command execution.
- **Unified Interface:** Standardize return values to include status, platform, and terminal type used.
- **Improve Error Handling:** Catch `subprocess.SubprocessError` and provide more descriptive feedback when terminal spawns fail.
- **Async by Default:** Standardize on non-blocking execution across all platforms for a consistent "fork" behavior.
- **Refactor Linux Logic:** Extract terminal detection into a helper function to improve readability.
