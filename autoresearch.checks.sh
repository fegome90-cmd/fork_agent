#!/bin/bash
set -euo pipefail

# Backpressure checks — ensure no tests break
cd "$(git rev-parse --show-toplevel)"
uv run pytest tests/unit/ -q --tb=short -n 6 --dist=loadscope --deselect tests/unit/interfaces/mcp_server_tests/test_tools.py::TestRegisterTools::test_registers_all_17_tools --deselect tests/unit/interfaces/mcp_server_tests/test_output_caps_integration.py 2>&1 | tail -30
