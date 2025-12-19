1. `zellij run` names panes instead of sessions, breaking `zellij attach`.
2. Incorrect return messages promise non-existent sessions.
3. `read -p` in detached panes causes hanging processes.