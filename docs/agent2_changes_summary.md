Updated Zellij fallback in fork_terminal.py to explicitly create named background sessions and launch commands in new panes.
Replaced zellij run with a two-step attach and new-pane flow for reliable session management and attachability.
Removed blocking prompts to prevent detached panes from hanging, ensuring consistent and clean command execution.
