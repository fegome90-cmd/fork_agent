#!/usr/bin/env bash
# Helper to launch optimized tmux for Fork Agent
# Usage: ./ide_tmux.sh [session_name]

SESSION_NAME=${1:-"fork_ide"}
CONFIG_FILE="$(pwd)/.claude/config/tmux.conf"

echo "🚀 Launching IDE Optimized Tmux..."
echo "   Session: $SESSION_NAME"
echo "   Config:  $CONFIG_FILE"

# Check if session exists
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "⚠️  Session '$SESSION_NAME' already exists."
    
    # Reload config just in case
    tmux source-file "$CONFIG_FILE"
    
    # Check if we are already inside a tmux session
    if [ -n "$TMUX" ]; then
        echo "🔄 Switching to session..."
        tmux switch-client -t "$SESSION_NAME"
    else
        echo "🔗 Attaching..."
        tmux attach -t "$SESSION_NAME"
    fi
else
    # Create new session with our config
    tmux -f "$CONFIG_FILE" new-session -s "$SESSION_NAME"
fi
