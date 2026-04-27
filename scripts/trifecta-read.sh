#!/usr/bin/env bash
# scripts/trifecta-read.sh - Helper to read Trifecta context by file path
set -euo pipefail

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <file_path> [mode: raw|excerpt|skeleton]"
    exit 1
fi

FILE_PATH=$1
MODE=${2:-excerpt}

echo "[trifecta-read] Searching for ID for: $FILE_PATH..."
# Get the first ID from search results
ID=$(trifecta ctx search -q "$FILE_PATH" -s . -l 1 | grep "\[repo:" | head -n 1 | sed -E 's/.*\[(repo:[^]]+)\].*/\1/')

if [ -z "$ID" ]; then
    echo "ERROR: Could not find ID for $FILE_PATH in context pack."
    exit 1
fi

echo "[trifecta-read] Found ID: $ID. Retrieving content ($MODE)..."
trifecta ctx get -i "$ID" -s . -m "$MODE"
