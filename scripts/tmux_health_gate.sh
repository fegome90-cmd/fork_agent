#!/usr/bin/env bash
set -euo pipefail

# Trifecta Daemon health check
if [[ -f "./scripts/trifecta_health.sh" ]]; then
    ./scripts/trifecta_health.sh || { echo "trifecta-health-gate: FAIL" >&2; exit 1; }
fi

# Health gate for tmux runtime.

# - If tmux is not installed: exit 0 (neutral in non-tmux environments)
# - If tmux is installed and unhealthy/degraded: exit 1

REPORT_JSON="$(uv run fork doctor status --json 2>/dev/null || true)"

python3 - <<'PY' "$REPORT_JSON"
import json
import sys

raw = sys.argv[1]

# Be resilient to accidental preamble text before JSON.
json_start = raw.find("{")
if json_start > 0:
    raw = raw[json_start:]

try:
    report = json.loads(raw)
except Exception:
    print("tmux-health-gate: could not parse JSON report", file=sys.stderr)
    sys.exit(1)

tmux_installed = bool(report.get("tmux_installed", False))
status = str(report.get("status", "unknown"))
orphans = int(report.get("orphan_sessions", 0))

if not tmux_installed:
    print("tmux-health-gate: tmux not installed -> neutral pass")
    sys.exit(0)

if status == "unhealthy" or orphans > 0:
    print(f"tmux-health-gate: FAIL (status={status}, orphans={orphans})", file=sys.stderr)
    sys.exit(1)

print(f"tmux-health-gate: PASS (status={status}, orphans={orphans})")
PY
