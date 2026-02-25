#!/bin/bash
# Workflow event handler for fork_agent
# Logs workflow events for auditability

set -euo pipefail

# Configuration
LOG_DIR=".claude/traces"
LOG_FILE="${LOG_DIR}/workflow-events.log"
TIMEOUT_SECONDS=5

# Read event data from environment variables (set by hook system)
EVENT_TYPE="${EVENT_TYPE:-unknown}"
PLAN_ID="${PLAN_ID:-no-plan-id}"

# Ensure log directory exists
if ! mkdir -p "${LOG_DIR}" 2>/dev/null; then
    echo "Warning: Could not create log directory ${LOG_DIR}" >&2
    exit 0  # Don't fail the hook
fi

# Generate timestamp
TIMESTAMP=$(date -Iseconds 2>/dev/null || date "+%Y-%m-%dT%H:%M:%S%z")

# Write log entry with timeout
LOG_ENTRY="[${TIMESTAMP}] Workflow Event: ${EVENT_TYPE} - Plan: ${PLAN_ID}"

if command -v timeout &>/dev/null; then
    echo "${LOG_ENTRY}" | timeout "${TIMEOUT_SECONDS}" tee -a "${LOG_FILE}" >/dev/null 2>&1 || true
else
    echo "${LOG_ENTRY}" >> "${LOG_FILE}" 2>/dev/null || true
fi

exit 0
