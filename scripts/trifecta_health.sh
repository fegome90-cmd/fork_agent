#!/bin/bash
# scripts/trifecta_health.sh - On-demand health check for Trifecta Daemon
# Standards applied: bash-cleanup-trap, bash-robust-integer-comparison

set -euo pipefail

REPO_ID="fc994b59"
PID_FILE="$HOME/.local/share/trifecta/repos/$REPO_ID/runtime/daemon/pid"
STATUS_FILE="_ctx/telemetry/daemon.status"

# Ensure telemetry dir exists
mkdir -p _ctx/telemetry

update_status() {
    local pid="${1:-0}"
    local status="${2:-unknown}"
    local now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    # Sanitize PID (bash-robust-integer-comparison)
    pid="${pid//[^0-9]/}"
    pid="${pid:-0}"

    cat <<EOF > "$STATUS_FILE"
{
  "pid": $pid,
  "status": "$status",
  "last_check": "$now"
}
EOF
}

# Check if PID file exists
if [[ -f "$PID_FILE" ]]; then
    PID=$(cat "$PID_FILE" 2>/dev/null || echo "0")
    
    # Sanitize captured PID
    PID="${PID//[^0-9]/}"
    PID="${PID:-0}"

    if [[ "$PID" -gt 0 ]] && ps -p "$PID" > /dev/null 2>&1; then
        # Extra safety: Check if it's actually trifecta daemon
        # We exclude the health script itself from the check
        if ps -p "$PID" -o args= 2>/dev/null | grep "trifecta" | grep -v "trifecta_health.sh" | grep -q "daemon"; then
            update_status "$PID" "healthy"
            exit 0
        fi
    fi
    
    # Orphaned PID file or wrong process
    echo "[trifecta-health] Cleaning up orphaned PID file for $PID"
    rm -f "$PID_FILE"
fi

# Daemon not running - attempt auto-restart
echo "[trifecta-health] Daemon not running. Attempting restart..."
if trifecta daemon start --repo . > /dev/null 2>&1; then
    # Give it a second to start and write PID
    sleep 1
    if [[ -f "$PID_FILE" ]]; then
        NEW_PID=$(cat "$PID_FILE" 2>/dev/null || echo "0")
        NEW_PID="${NEW_PID//[^0-9]/}"
        
        if [[ "${NEW_PID:-0}" -gt 0 ]]; then
            update_status "$NEW_PID" "recovered"
            echo "[trifecta-health] Daemon recovered with PID $NEW_PID"
            exit 0
        fi
    fi
fi

# Total failure
update_status 0 "unhealthy"
echo "[trifecta-health] CRITICAL: Failed to start Trifecta Daemon"
exit 1
