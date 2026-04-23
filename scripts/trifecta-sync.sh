#!/usr/bin/env bash
# Rebuild Trifecta context pack + graph on commit (if trifecta is available)
set -euo pipefail

if command -v trifecta &>/dev/null; then
    echo "[trifecta-sync] Starting synchronization..."

    # 1. Context Pack Sync (Regenerates context_pack.json)
    echo "[trifecta-sync] Regenerating context pack..."
    SYNC_START=$(python3 -c "import time; print(int(time.time()*1000))")
    trifecta ctx sync -s . 2>/dev/null || {
        echo "[trifecta-sync] WARNING: ctx sync failed, check AGENTS.md constitution" >&2
    }
    SYNC_END=$(python3 -c "import time; print(int(time.time()*1000))")
    SYNC_DURATION=$((SYNC_END - SYNC_START))
    
    if [ -f "_ctx/context_pack.json" ]; then
        CP_SIZE=$(ls -lh _ctx/context_pack.json | awk '{print $5}')
        echo "[trifecta-sync] Context pack regenerated in ${SYNC_DURATION}ms (Size: $CP_SIZE)"
    fi

    # 2. File Indexing
    echo "[trifecta-sync] Indexing files..."
    INDEX_OUTPUT=$(trifecta index -r . --json 2>/dev/null || echo '{"indexed":0}')
    FILE_COUNT=$(echo "$INDEX_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('indexed',0))" 2>/dev/null || echo "0")
    echo "[trifecta-sync] Indexed $FILE_COUNT files"

    # 3. Graph Reindex
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
    echo "[trifecta-sync] Synchronization complete"
fi
