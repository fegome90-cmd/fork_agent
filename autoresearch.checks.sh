#!/bin/bash
set -euo pipefail

# Backpressure checks — ensure no tests break
cd "$(git rev-parse --show-toplevel)"
uv run pytest tests/unit/ -q --tb=short -n 8 --dist=worksteal 2>&1 | tail -30
