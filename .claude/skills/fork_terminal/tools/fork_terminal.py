#!/usr/bin/env -S uv run
"""Fork a new terminal window with a command."""

import os
import platform
import random
import shlex
import subprocess
import time
from datetime import datetime
from pathlib import Path


def _checkout_agent(command: str, duration: float, status: str, result: str = "") -> None:
    """Log agent execution to checkout log."""
    
    # Check if checkout is disabled
    if os.getenv('FORK_TERMINAL_DISABLE_CHECKOUT') == '1':
        return
    
    # Generate agent ID
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    random_suffix = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=3))
    agent_id = f"agent_{timestamp}_{random_suffix}"
    
    # Determine agent name from command
    command_lower = command.lower()
    if 'gemini' in command_lower:
        agent_name = "Gemini CLI Agent"
    elif 'claude' in command_lower:
        agent_name = "Claude Code Agent"
    elif 'codex' in command_lower:
        agent_name = "Codex CLI Agent"
    else:
        agent_name = "CLI Command"
    
    # Prepare log directory
    try:
        log_dir = Path.cwd() / '.claude' / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / 'agent_checkout.log'
    except:
        # If can't create in cwd, try home directory
        log_dir = Path.home() / '.claude' / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / 'agent_checkout.log'
    
    # Extract summary from command (first 100 chars)
    summary = command[:100].replace('\n', ' ').replace('"', '\\"')
    
    # Write checkout entry
    checkout_entry = f"""---
timestamp: "{datetime.now().isoformat()}"
agent_id: "{agent_id}"
agent_name: "{agent_name}"
status: "{status}"
duration_seconds: {int(duration)}
files_modified: []
report_path: null
summary: "{summary}"
errors: []
"""
    
    try:
        with open(log_file, 'a') as f:
            f.write(checkout_entry)
    except Exception:
        # Silent fail - don't break fork_terminal if checkout fails
        pass


def fork_terminal(command: str) -> str:
    """Open a new Terminal window and run the specified command."""
    
    # Record start time for checkout
    start_time = time.time()
    status = "SUCCESS"
    result = ""
    
    try:
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
            result = result.stdout.strip()
            return result

        elif system == "Windows":
            subprocess.Popen(["cmd", "/c", "start", "cmd", "/k", safe_command], shell=True)
            result = "New terminal window opened on Windows."
            return result

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
                result = f"New terminal window opened on Linux using {found_terminal}."
                return result

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
                result = f"New terminal session opened in tmux (session: {session_name}). Attach with: tmux attach -t {session_name}"
                return result

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
                result = f"New terminal session opened in zellij (session: {session_name}). Attach with: zellij attach {session_name}"
                return result

            raise NotImplementedError("No supported terminal emulator found on Linux.")

        else:  # Other systems
            raise NotImplementedError(
                "This function is only implemented for macOS, Windows, and Linux."
            )
    
    except Exception as e:
        status = "FAILURE"
        result = f"Error: {str(e)}"
        raise
    
    finally:
        # Calculate duration and checkout agent
        duration = time.time() - start_time
        _checkout_agent(command, duration, status, result)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        output = fork_terminal(" ".join(sys.argv[1:]))
        print(output)
