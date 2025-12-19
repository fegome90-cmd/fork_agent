# Zellij Fix Implementation

## Overview
Updated the zellij fallback in `fork_terminal.py` to create a named session explicitly and run the command in a new pane within that session. Removed the blocking `read -p` usage to avoid hanging detached panes.

## Changes Made
- Replaced `zellij run -d -n <session>` with a two-step flow:
  - Create a detached session via `zellij attach --create-background <session>`.
  - Launch the command in that session via `zellij --session <session> action new-pane -- bash -c <command>`.
- Removed the `read -p 'Press enter to close...'` prompt.
- Kept return messaging consistent with the actual session name and `zellij attach <session>`.

## Before / After (Conceptual)
Before:
- `zellij run -d -n <session> -- bash -c "<command>; read -p ..."`
- Pane name was mistaken for a session name; attach often failed.

After:
- `zellij attach --create-background <session>`
- `zellij --session <session> action new-pane -- bash -c <command>`
- Session is named and attachable as advertised.

## Bugs Fixed
- Ensures the named session exists and is attachable.
- Aligns zellij usage with session semantics instead of pane naming.
- Removes blocking prompt that could hang in detached panes.

## Testing Recommendations
- Run `fork_terminal.py` on Linux without a GUI terminal and without tmux installed.
- Confirm output references the session name and `zellij attach <session>` works.
- Verify the command runs in a new pane and exits cleanly.
