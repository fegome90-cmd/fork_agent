#!/bin/bash
# memory-trace-writer.sh - SubagentStop hook
# Writes agent trace to MessageStore

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
AGENT_NAME="${AGENT_NAME:-unknown}"
DURATION_MS="${DURATION_MS:-0}"
STATUS="${STATUS:-completed}"

# Format timestamp
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Try to use memory CLI if available, otherwise write to trace file
TRACE_DIR=".claude/traces"
mkdir -p "$TRACE_DIR"

TRACE_FILE="${TRACE_DIR}/current-trace.json"

# Update or create trace
if [ -f "$TRACE_FILE" ]; then
    # Update existing trace with completed span
    python3 -c "
import json
import sys
with open('$TRACE_FILE', 'r') as f:
    data = json.load(f)
for span in data.get('spans', []):
    if span.get('agent_id') == '$AGENT_NAME' and span.get('status') == 'running':
        span['status'] = '$STATUS'
        span['duration_ms'] = $DURATION_MS
        span['end'] = '$TIMESTAMP'
        break
with open('$TRACE_FILE', 'w') as f:
    json.dump(data, f, indent=2)
" 2>/dev/null || echo "Failed to update trace"
else
    # Create new trace
    python3 -c "
import json
data = {
    'session_id': 'trace-$(date +%Y%m%d-%H%M%S)',
    'spans': [{
        'name': '$AGENT_NAME',
        'agent_id': '$AGENT_NAME',
        'start': '$TIMESTAMP',
        'end': '$TIMESTAMP',
        'duration_ms': $DURATION_MS,
        'status': '$STATUS'
    }]
}
with open('$TRACE_FILE', 'w') as f:
    json.dump(data, f, indent=2)
"
fi

cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SubagentStop",
    "agentName": "$AGENT_NAME",
    "durationMs": $DURATION_MS,
    "status": "$STATUS",
    "traceFile": "$TRACE_FILE"
  }
}
EOF
