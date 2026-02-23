#!/bin/bash
# workspace-init.sh - SessionStart hook

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
WORKSPACE_NAME="$(basename "$PROJECT_DIR")"

# Create traces directory
mkdir -p "$PROJECT_DIR/.claude/traces"

# Check if workspace tracking exists
if [ -f "$PROJECT_DIR/.claude/context-memory-id" ]; then
    WORKSPACE_ID=$(cat "$PROJECT_DIR/.claude/context-memory-id")
else
    WORKSPACE_ID="ws-$(date +%s)"
    echo "$WORKSPACE_ID" > "$PROJECT_DIR/.claude/context-memory-id"
fi

cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "workspaceName": "$WORKSPACE_NAME",
    "workspaceId": "$WORKSPACE_ID",
    "projectDir": "$PROJECT_DIR"
  }
}
EOF
