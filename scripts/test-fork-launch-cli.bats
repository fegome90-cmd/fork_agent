#!/usr/bin/env bats
# test-fork-launch-cli.bats — Contract tests for fork launch CLI
# Validates the boundary contract defined in ADR-002
# Run: bats scripts/test-fork-launch-cli.bats

setup() {
    FORK_CLI="uv run python -m src.interfaces.cli.main"
    PROJECT_DIR="/Users/felipe_gonzalez/Developer/tmux_fork"
    TEST_KEY="bats-$(date +%s)-$RANDOM"
}

# ─── 1. request: claimed for new key ──────────────────────────

@test "request returns exit 0 and decision=claimed for new canonical key" {
    cd "$PROJECT_DIR"
    run $FORK_CLI launch request \
      --canonical-key "$TEST_KEY" \
      --surface test \
      --owner-type test \
      --owner-id bats \
      --json
    [ "$status" -eq 0 ]
    decision=$(echo "$output" | jq -r '.decision')
    [ "$decision" = "claimed" ]
}

@test "request JSON has required fields (decision, launch_id, reason)" {
    cd "$PROJECT_DIR"
    run $FORK_CLI launch request \
      --canonical-key "$TEST_KEY-fields" \
      --surface test \
      --owner-type test \
      --owner-id bats \
      --json
    [ "$status" -eq 0 ]
    echo "$output" | jq -e '.decision' > /dev/null
    echo "$output" | jq -e '.launch_id' > /dev/null
    # reason can be null — just verify the key exists
    echo "$output" | jq -e 'has("reason")' > /dev/null
}

@test "request returns non-null launch_id when claimed" {
    cd "$PROJECT_DIR"
    run $FORK_CLI launch request \
      --canonical-key "$TEST_KEY-lid" \
      --surface test \
      --owner-type test \
      --owner-id bats \
      --json
    [ "$status" -eq 0 ]
    launch_id=$(echo "$output" | jq -r '.launch_id')
    [ "$launch_id" != "null" ]
    [ ${#launch_id} -ge 8 ]
}

# ─── 2. request: suppressed on duplicate ──────────────────────

@test "duplicate request returns exit 1 and decision=suppressed" {
    cd "$PROJECT_DIR"
    # First request — claimed
    $FORK_CLI launch request \
      --canonical-key "$TEST_KEY-dup" \
      --surface test \
      --owner-type test \
      --owner-id bats1 \
      --json >/dev/null

    # Second request — suppressed
    run $FORK_CLI launch request \
      --canonical-key "$TEST_KEY-dup" \
      --surface test \
      --owner-type test \
      --owner-id bats2 \
      --json
    [ "$status" -eq 1 ]
    decision=$(echo "$output" | jq -r '.decision')
    [ "$decision" = "suppressed" ]
}

# ─── 3. Full lifecycle ────────────────────────────────────────

@test "full lifecycle: request → confirm-spawning → confirm-active → terminate" {
    cd "$PROJECT_DIR"
    # Request
    run $FORK_CLI launch request \
      --canonical-key "$TEST_KEY-lifecycle" \
      --surface test \
      --owner-type test \
      --owner-id bats \
      --json
    [ "$status" -eq 0 ]
    LAUNCH_ID=$(echo "$output" | jq -r '.launch_id')

    # Confirm spawning
    run $FORK_CLI launch confirm-spawning \
      --launch-id "$LAUNCH_ID" --json
    [ "$status" -eq 0 ]

    # Confirm active
    run $FORK_CLI launch confirm-active \
      --launch-id "$LAUNCH_ID" \
      --backend tmux \
      --termination-handle-type tmux-session \
      --termination-handle-value "bats-test-session" \
      --tmux-session "bats-test-session" \
      --json
    [ "$status" -eq 0 ]

    # Begin termination
    run $FORK_CLI launch begin-termination \
      --launch-id "$LAUNCH_ID" --json
    [ "$status" -eq 0 ]

    # Confirm terminated
    run $FORK_CLI launch confirm-terminated \
      --launch-id "$LAUNCH_ID" --json
    [ "$status" -eq 0 ]
    status_val=$(echo "$output" | jq -r '.status')
    [ "$status_val" = "terminated" ]
}

# ─── 4. Status queries ────────────────────────────────────────

@test "status returns exit 0 for existing launch" {
    cd "$PROJECT_DIR"
    run $FORK_CLI launch request \
      --canonical-key "$TEST_KEY-status" \
      --surface test \
      --owner-type test \
      --owner-id bats \
      --json
    LAUNCH_ID=$(echo "$output" | jq -r '.launch_id')

    run $FORK_CLI launch status --launch-id "$LAUNCH_ID" --json
    [ "$status" -eq 0 ]
    status_val=$(echo "$output" | jq -r '.status')
    [ -n "$status_val" ]
    [ "$status_val" != "null" ]
}

@test "status returns exit 1 for nonexistent launch" {
    cd "$PROJECT_DIR"
    run $FORK_CLI launch status --launch-id "nonexistent-00000000" --json
    [ "$status" -eq 1 ]
    reason=$(echo "$output" | jq -r '.reason')
    [ "$reason" = "not_found" ]
}

# ─── 5. list-active ───────────────────────────────────────────

@test "list-active returns exit 0 and valid JSON array" {
    cd "$PROJECT_DIR"
    run $FORK_CLI launch list-active --json
    [ "$status" -eq 0 ]
    # Must be valid JSON array
    echo "$output" | jq -e 'type == "array"' > /dev/null
}

# ─── 6. mark-failed ──────────────────────────────────────────

@test "mark-failed on active launch returns exit 0" {
    cd "$PROJECT_DIR"
    run $FORK_CLI launch request \
      --canonical-key "$TEST_KEY-fail" \
      --surface test \
      --owner-type test \
      --owner-id bats \
      --json
    LAUNCH_ID=$(echo "$output" | jq -r '.launch_id')

    $FORK_CLI launch confirm-spawning --launch-id "$LAUNCH_ID" --json >/dev/null
    $FORK_CLI launch confirm-active \
      --launch-id "$LAUNCH_ID" \
      --backend test \
      --termination-handle-type test \
      --termination-handle-value test \
      --json >/dev/null

    run $FORK_CLI launch mark-failed \
      --launch-id "$LAUNCH_ID" --error "bats test failure" --json
    [ "$status" -eq 0 ]
    status_val=$(echo "$output" | jq -r '.status')
    [ "$status_val" = "failed" ]
}

# ─── 7. Usage error ──────────────────────────────────────────

@test "request with missing args returns non-zero exit" {
    cd "$PROJECT_DIR"
    run $FORK_CLI launch request --json 2>&1
    [ "$status" -ne 0 ]
}
