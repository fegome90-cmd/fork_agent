#!/bin/bash
set -euo pipefail

# Backpressure checks — ensure no tests break
cd "$(git rev-parse --show-toplevel)"
uv run pytest tests/unit/ -q --tb=short -n auto --deselect tests/unit/interfaces/mcp_server_tests/test_tools.py::TestRegisterTools::test_registers_all_17_tools 2>&1 | tail -30
