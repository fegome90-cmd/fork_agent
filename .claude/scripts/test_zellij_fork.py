#!/usr/bin/env python3
"""Test fork_terminal with Zellij directly on macOS."""

import subprocess
import uuid

def fork_terminal_zellij(command: str) -> str:
    """Force Zellij usage even on macOS for testing."""
    
    session_name = f"fork_term_{str(uuid.uuid4())[:8]}"
    
    # Create a detached session
    subprocess.run([
        "zellij",
        "attach",
        "--create-background",
        session_name,
    ])
    
    # Run command in new pane
    subprocess.run([
        "zellij",
        "--session",
        session_name,
        "action",
        "new-pane",
        "--",
        "bash",
        "-c",
        command,
    ])
    
    return f"New terminal session opened in zellij (session: {session_name}). Attach with: zellij attach {session_name}"


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:])
        result = fork_terminal_zellij(command)
        print(result)
    else:
        print("Usage: python3 test_zellij_fork.py <command>")
