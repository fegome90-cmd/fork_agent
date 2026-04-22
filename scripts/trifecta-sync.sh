#!/usr/bin/env bash
# Rebuild Trifecta context pack + graph on commit (if trifecta is available)
set -euo pipefail

if command -v trifecta &>/dev/null; then
    echo "[trifecta-sync] Rebuilding context pack..."
    trifecta index -r . --json 2>/dev/null || true
    # Graph reindex (auto-index after commit)
    if [ -d ".trifecta" ]; then
        echo "[trifecta-sync] Reindexing graph..."
        START_MS=$(python3 -c "import time; print(int(time.time()*1000))")
        INDEX_OUTPUT=$(trifecta graph index -s . --json 2>/dev/null || echo '{}')
        END_MS=$(python3 -c "import time; print(int(time.time()*1000))")
        DURATION=$((END_MS - START_MS))

        # Parse node/edge counts
        NODES=$(echo "$INDEX_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('node_count',0))" 2>/dev/null || echo "0")
        EDGES=$(echo "$INDEX_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('edge_count',0))" 2>/dev/null || echo "0")

        # Emit telemetry (best-effort)
        memory save "trifecta/index: nodes=$NODES edges=$EDGES duration=${DURATION}ms" -t observation -m "{\"topic_key\":\"trifecta/index\",\"duration_ms\":$DURATION,\"node_count\":$NODES,\"edge_count\":$EDGES}" 2>/dev/null || true
    fi
    echo "[trifecta-sync] Done"
fi
