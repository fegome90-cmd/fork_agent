# Fix report: command injection (fork_terminal.py)

- Change: Imported `shlex` and created `safe_command = shlex.quote(command)` to sanitize user input.
- Change: Applied `safe_command` to all platform execution paths (macOS osascript, Windows cmd, Linux terminals/tmux/zellij).
- Change: Escaped double quotes for AppleScript to preserve execution with `osascript`.

Why
- Prevent shell/AppleScript injection when user-supplied `command` contains metacharacters.
- Reduce risk of arbitrary code execution while keeping expected command behavior.

How to verify
- Run `python /Users/felipe_gonzalez/Developer/fork_agent-main/.claude/skills/fork_terminal/tools/fork_terminal.py "echo ok"`.
- Try special characters: `"echo ok; rm -rf /"`, `"echo $(whoami)"` and confirm they are treated as literal input.
- Verify each platform path still opens a terminal window and keeps it open as before.

Risks/considerations
- Quoted commands now pass through as a single shell token; complex shell pipelines should still work because the quoted string is parsed by `bash -c`.
- AppleScript string escaping is limited to double quotes; other edge cases should be monitored.
