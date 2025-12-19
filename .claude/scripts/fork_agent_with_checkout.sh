#!/bin/bash
# Agent Checkout Wrapper - Wraps any agent command with automatic checkout logging
#
# Usage: ./fork_agent_with_checkout.sh <AGENT_ID> <AGENT_NAME> <REPORT_PATH> <COMMAND>
#
# Example:
#   ./fork_agent_with_checkout.sh "C1" "Security Fix" "docs/fix_security.md" \
#     "gemini -y -m gemini-3-flash-preview 'Fix security issue'"

AGENT_ID="$1"
AGENT_NAME="$2"
REPORT_PATH="$3"
shift 3
COMMAND="$@"

# Configuration
LOG_FILE=".claude/logs/agent_checkout.log"
START_TIME=$(date +%s)

echo "🚀 Starting Agent ${AGENT_ID}: ${AGENT_NAME}"
echo "   Command: ${COMMAND}"
echo ""

# Execute agent command
eval "$COMMAND" 2>&1 | tee "/tmp/agent_${AGENT_ID}.log"
AGENT_STATUS=${PIPESTATUS[0]}

# Calculate duration
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# Determine status
if [ $AGENT_STATUS -eq 0 ] && [ -f "${REPORT_PATH}" ]; then
  STATUS="SUCCESS"
  SUMMARY=$(tail -1 "${REPORT_PATH}" 2>/dev/null | head -c 100 || echo "Task completed")
else
  STATUS="FAILURE"
  SUMMARY="Agent failed with exit code ${AGENT_STATUS}"
fi

# Get modified files (if git repo)
if git rev-parse --git-dir > /dev/null 2>&1; then
  FILES_MODIFIED=$(git diff --name-only HEAD 2>/dev/null | sed 's/^/  - "/' | sed 's/$/"/')
  if [ -z "$FILES_MODIFIED" ]; then
    FILES_MODIFIED="  []"
  fi
else
  FILES_MODIFIED="  []"
fi

# Checkout (append to log)
cat >> "${LOG_FILE}" << EOF
---
timestamp: "$(date -Iseconds)"
agent_id: "${AGENT_ID}"
agent_name: "${AGENT_NAME}"
status: "${STATUS}"
duration_seconds: ${DURATION}
files_modified:
${FILES_MODIFIED}
report_path: "${REPORT_PATH}"
summary: "${SUMMARY}"
errors: []
EOF

# Print checkout confirmation
if [ "${STATUS}" == "SUCCESS" ]; then
  echo ""
  echo "✅ Agent ${AGENT_ID} checked out: ${STATUS} (${DURATION}s)"
  echo "   Report: ${REPORT_PATH}"
else
  echo ""
  echo "❌ Agent ${AGENT_ID} checked out: ${STATUS} (${DURATION}s)"
  echo "   Check logs: /tmp/agent_${AGENT_ID}.log"
fi

exit $AGENT_STATUS
