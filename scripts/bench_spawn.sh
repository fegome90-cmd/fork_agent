#!/usr/bin/env bash
# Benchmark: sub-agent spawn latency
# Measures wall-clock time for a trivial pi sub-agent task
set -euo pipefail

WARMUP=${1:-1}
RUNS=${2:-3}
TASK="Write 'hello' to /tmp/fork-bench-spawn.md"

echo "# Sub-agent spawn benchmark"
echo "# Warmup: ${WARMUP}, Runs: ${RUNS}"
echo "# Task: ${TASK}"
echo ""

# Warmup run (cold start)
for i in $(seq 1 "$WARMUP"); do
  timeout 120 env PI_LENS_STARTUP_MODE=quick pi \
    --provider zai --model glm-5-turbo \
    -nc --mode json -p "$TASK" > /dev/null 2>&1 || true
  rm -f /tmp/fork-bench-spawn.md
done

# Measured runs
TOTAL_MS=0
for i in $(seq 1 "$RUNS"); do
  START=$(python3 -c "import time; print(int(time.time()*1000))")
  timeout 120 env PI_LENS_STARTUP_MODE=quick pi \
    --provider zai --model glm-5-turbo \
    -nc --mode json -p "$TASK" > /dev/null 2>&1 || true
  END=$(python3 -c "import time; print(int(time.time()*1000))")
  ELAPSED=$((END - START))
  TOTAL_MS=$((TOTAL_MS + ELAPSED))
  echo "Run ${i}: ${ELAPSED}ms"
  rm -f /tmp/fork-bench-spawn.md
done

AVG=$((TOTAL_MS / RUNS))
echo ""
echo "METRIC spawn_ms=${AVG}"
echo "Average: ${AVG}ms over ${RUNS} runs"
