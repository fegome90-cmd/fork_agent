#!/bin/bash
# tmux-session-per-agent.sh - SubagentStart hook
# Creates isolated tmux session for each agent with validation
#
# Env vars expected:
#   AGENT_NAME - Name of the agent (e.g., "babyclaude-1")
#   CLAUDE_PROJECT_DIR - Project directory
#   WORKTREE_PATH - Path for worktree (optional)
#
# Output: JSON with TMUX_SESSION info for the orchestrator

set -euo pipefail

# Config
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
WORKTREE_PATH="${WORKTREE_PATH:-$PROJECT_DIR}"
AGENT_NAME="${AGENT_NAME:-unknown}"
TIMESTAMP="$(date +%s)"
SESSION_NAME="fork-${AGENT_NAME}-${TIMESTAMP}"
MAX_WAIT_SECONDS=5

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" >&2
}

# Validate tmux is available
if ! command -v tmux &> /dev/null; then
    log "ERROR: tmux not found"
    echo '{"error": "tmux not found", "allowed": false}' >&2
    exit 1  # FAIL - critical
fi

# Validate working directory exists
if [ ! -d "$WORKTREE_PATH" ]; then
    log "ERROR: Working directory does not exist: $WORKTREE_PATH"
    echo '{"error": "Working directory not found", "allowed": false}' >&2
    exit 1  # FAIL - critical
fi

# Create tmux session (detached)
log "Creating tmux session: $SESSION_NAME in $WORKTREE_PATH"
if ! tmux new-session -d -s "$SESSION_NAME" -c "$WORKTREE_PATH" 2>/dev/null; then
    log "ERROR: Failed to create tmux session: $SESSION_NAME"
    echo "{\"error\": \"Failed to create tmux session\", \"allowed\": false}" >&2
    exit 1  # FAIL - critical
fi

# Validate session was created and is ready
log "Validating session: $SESSION_NAME"
WAIT_COUNT=0
while [ $WAIT_COUNT -lt $MAX_WAIT_SECONDS ]; do
    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        log "Session ready: $SESSION_NAME"
        break
    fi
    WAIT_COUNT=$((WAIT_COUNT + 1))
    sleep 1
done

# Final validation
if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    log "ERROR: Session not ready after validation: $SESSION_NAME"
    tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true
    echo '{"error": "Session validation failed", "allowed": false}' >&2
    exit 1  # FAIL - critical
fi

# Get session info
SESSION_PID=$(tmux list-panes -t "$SESSION_NAME" -F '#{pane_pid}' 2>/dev/null | head -1 || echo "unknown")

log "SUCCESS: Agent $AGENT_NAME spawned in session $SESSION_NAME (PID: $SESSION_PID)"

# Output JSON for the orchestrator
cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SubagentStart",
    "sessionName": "$SESSION_NAME",
    "attachCommand": "tmux attach -t $SESSION_NAME",
    "sendCommand": "tmux send-keys -t $SESSION_NAME",
    "sessionPid": "$SESSION_PID",
    "status": "ready",
    "additionalContext": "TMUX_SESSION: $SESSION_NAME\\nPID: $SESSION_PID\\nAttach: tmux attach -t $SESSION_NAME"
  }
}
EOF

exit 0
