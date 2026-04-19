#!/usr/bin/env bash
# Rebuild Trifecta context pack on commit (if trifecta is available)
set -euo pipefail

if command -v trifecta &>/dev/null; then
    echo "[trifecta-sync] Rebuilding context pack..."
    trifecta index -r . --json 2>/dev/null || true
    echo "[trifecta-sync] Done"
fi
