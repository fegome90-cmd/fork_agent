#!/usr/bin/env bash
set -euo pipefail

# tmux_fork unit test benchmark for autoresearch
# Runs the full unit test suite and reports timing metrics

cd "$(git rev-parse --show-toplevel)"

# Pre-check: ensure tests can be collected
uv run pytest tests/unit/ --co -q > /dev/null 2>&1 || {
  echo "FAIL: test collection failed"
  exit 1
}

# Run the full suite, capture timing
START=$(python3 -c "import time; print(time.time())")

OUTPUT=$(uv run pytest tests/unit/ -q --tb=no 2>&1)
EXIT_CODE=$?

END=$(python3 -c "import time; print(time.time())")

TOTAL_SECONDS=$(python3 -c "print(f'{$END - $START:.2f}')")

# Extract passed count from pytest output
PASSED=$(echo "$OUTPUT" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+' || echo "0")
FAILED=$(echo "$OUTPUT" | grep -oE '[0-9]+ failed' | grep -oE '[0-9]+' || echo "0")
SKIPPED=$(echo "$OUTPUT" | grep -oE '[0-9]+ skipped' | grep -oE '[0-9]+' || echo "0")

# Report metrics
echo "METRIC total_seconds=$TOTAL_SECONDS"
echo "METRIC passed_tests=$PASSED"
echo "METRIC failed_tests=$FAILED"
echo "METRIC skipped_tests=$SKIPPED"

# Show summary line
echo "$OUTPUT" | tail -3

if [ "$EXIT_CODE" -ne 0 ]; then
  echo "FAIL: pytest exited with code $EXIT_CODE"
  exit 1
fi

# Sanity check: must have 1500+ tests passing (baseline is ~1615)
if [ "$PASSED" -lt 1500 ]; then
  echo "FAIL: too few tests passed ($PASSED < 1500)"
  exit 1
fi
