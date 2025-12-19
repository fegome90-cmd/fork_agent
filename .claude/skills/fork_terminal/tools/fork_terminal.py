#!/usr/bin/env -S uv run
"""Fork a new terminal window with a command."""

import platform
import shlex
import subprocess


def fork_terminal(command: str) -> str:
    """Open a new Terminal window and run the specified command."""
    system = platform.system()
    safe_command = shlex.quote(command)

    if system == "Darwin":  # macOS
        applescript_command = safe_command.replace('"', '\\"')
        result = subprocess.run(
            [
                "osascript",
                "-e",
                f'tell application "Terminal" to do script "{applescript_command}"',
            ],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    elif system == "Windows":
        subprocess.Popen(["cmd", "/c", "start", "cmd", "/k", safe_command], shell=True)
        return "New terminal window opened on Windows."

    elif system == "Linux":
        import shutil

        # Check for common terminal emulators
        terminals = [
            "gnome-terminal",
            "x-terminal-emulator",
            "xterm",
            "konsole",
            "xfce4-terminal",
        ]
        found_terminal = None
        for term in terminals:
            if shutil.which(term):
                found_terminal = term
                break

        if found_terminal:
            if found_terminal == "gnome-terminal":
                # gnome-terminal needs specific handling to keep window open
                subprocess.Popen(
                    [found_terminal, "--", "bash", "-c", f"{safe_command}; exec bash"]
                )
            else:
                # Standard -e flag for xterm, x-terminal-emulator, etc.
                subprocess.Popen(
                    [found_terminal, "-e", f"bash -c {safe_command}; exec bash"]
                )
            return f"New terminal window opened on Linux using {found_terminal}."

        # Fallback to tmux if no GUI terminal is found
        if shutil.which("tmux"):
            import uuid

            session_name = f"fork_term_{str(uuid.uuid4())[:8]}"
            # Create a detached session
            subprocess.run(
                [
                    "tmux",
                    "new-session",
                    "-d",
                    "-s",
                    session_name,
                    f"{safe_command}; read -p 'Press enter to close...'",
                ]
            )
            return f"New terminal session opened in tmux (session: {session_name}). Attach with: tmux attach -t {session_name}"

        # Fallback to zellij if no GUI terminal or tmux is found
        if shutil.which("zellij"):
            import uuid

            session_name = f"fork_term_{str(uuid.uuid4())[:8]}"
            # Create a detached session and run the command in a new pane.
            subprocess.run(
                [
                    "zellij",
                    "attach",
                    "--create-background",
                    session_name,
                ]
            )
            subprocess.run(
                [
                    "zellij",
                    "--session",
                    session_name,
                    "action",
                    "new-pane",
                    "--",
                    "bash",
                    "-c",
                    safe_command,
                ]
            )
            return f"New terminal session opened in zellij (session: {session_name}). Attach with: zellij attach {session_name}"

        raise NotImplementedError("No supported terminal emulator found on Linux.")

    else:  # Other systems
        raise NotImplementedError(
            "This function is only implemented for macOS, Windows, and Linux."
        )


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        output = fork_terminal(" ".join(sys.argv[1:]))
        print(output)
