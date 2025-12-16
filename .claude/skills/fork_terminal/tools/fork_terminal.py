#!/usr/bin/env -S uv run
"""Fork a new terminal window with a command."""

import subprocess
import platform

def fork_terminal(command: str) -> str:
    """Open a new Terminal window and run the specified command."""
    system = platform.system()

    if system == "Darwin":  # macOS
        result = subprocess.run(
            ["osascript", "-e", f'tell application "Terminal" to do script "{command}"'],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip

    elif system == "Windows":
        subprocess.Popen(["cmd", "/c", "start", "cmd", "/k", command], shell=True)
        return "New terminal window opened on Windows."
    
    else: # Linux and others
        raise NotImplementedError("This function is only implemented for macOS and Windows.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        output = fork_terminal(" ".join(sys.argv[1:]))
        print(output)
