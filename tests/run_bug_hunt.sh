#!/bin/bash
# Bug Hunt Test Runner
# Runs bug detection tests with markers and JUnit output
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Create artifacts directory
mkdir -p "$PROJECT_ROOT/artifacts"

# Set environment for tests
export API_KEY="${API_KEY:-test-key}"

echo "=== Bug Hunt Test Runner ==="
echo "Project: $PROJECT_ROOT"
echo "Python: $(python3 --version)"
echo "Pytest: $(cd "$PROJECT_ROOT" && uv run pytest --version)"
echo ""

# Run bughunt marked tests
echo "=== Running bughunt tests ==="
cd "$PROJECT_ROOT"
uv run pytest -m bughunt \
    --timeout=300 \
    --tb=short \
    -v \
    --junitxml=artifacts/junit-bughunt.xml \
    || true

# Run integration tests
echo ""
echo "=== Running integration tests ==="
uv run pytest -m integration \
    --timeout=300 \
    --tb=short \
    -v \
    --junitxml=artifacts/junit-integration.xml \
    || true

echo ""
echo "=== Test Results ==="
if [ -f artifacts/junit-bughunt.xml ]; then
    echo "Bughunt JUnit: artifacts/junit-bughunt.xml"
    # Show summary
    grep -E "tests=|failures=|errors=" artifacts/junit-bughunt.xml | head -3
fi

if [ -f artifacts/junit-integration.xml ]; then
    echo "Integration JUnit: artifacts/junit-integration.xml"
    grep -E "tests=|failures=|errors=" artifacts/junit-integration.xml | head -3
fi

echo ""
echo "=== Complete ==="
