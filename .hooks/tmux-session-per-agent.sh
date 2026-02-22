#!/bin/bash
# tmux-session-per-agent.sh - SubagentStart hook
# Creates isolated tmux session for each agent
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

# Validate tmux is available
if ! command -v tmux &> /dev/null; then
    echo '{"error": "tmux not found", "allowed": false}' >&2
    exit 0  # Don't block, just warn
fi

# Create tmux session (detached)
tmux new-session -d -s "$SESSION_NAME" -c "$WORKTREE_PATH" 2>/dev/null || {
    echo "{\"error\": \"Failed to create tmux session\", \"allowed\": true}" >&2
    exit 0
}

# Output JSON for the orchestrator
cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SubagentStart",
    "sessionName": "$SESSION_NAME",
    "attachCommand": "tmux attach -t $SESSION_NAME",
    "sendCommand": "tmux send-keys -t $SESSION_NAME",
    "additionalContext": "TMUX_SESSION: $SESSION_NAME\\nAttach: tmux attach -t $SESSION_NAME"
  }
}
EOF
