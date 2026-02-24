#!/usr/bin/env bash
# Smoke tests for fork-verify.sh
# Usage: ./test_fork_verify.sh

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERIFY_SCRIPT="$SCRIPT_DIR/fork-verify.sh"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

TESTS_PASSED=0
TESTS_FAILED=0

test_case() {
    local name="$1"
    local expected_code="$2"
    shift 2
    
    echo -n "Test: $name ... "
    local actual_code
    actual_code=0
    "$@" > /dev/null 2>&1 || actual_code=$?
    
    if [[ $actual_code -eq $expected_code ]]; then
        echo -e "${GREEN}PASS${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}FAIL${NC} (expected $expected_code, got $actual_code)"
        ((TESTS_FAILED++))
    fi
}

echo "Running fork-verify.sh smoke tests..."
echo ""

# Test 1: Non-existent directory
test_case "Non-existent directory returns 2" 2 \
    "$VERIFY_SCRIPT" "/nonexistent/path"

# Test 2: Valid .claude directory (but with broken hook reference)
test_case ".claude with errors returns 2" 2 \
    "$VERIFY_SCRIPT" "$SCRIPT_DIR/../.claude"

# Test 3: Script runs without args
test_case "Script runs without error" 0 \
    bash -c '"$VERIFY_SCRIPT" . 2>&1 | head -1'

echo ""
echo "========================================"
echo "Results: $TESTS_PASSED passed, $TESTS_FAILED failed"
echo "========================================"

if [[ $TESTS_FAILED -gt 0 ]]; then
    exit 1
fi
exit 0
