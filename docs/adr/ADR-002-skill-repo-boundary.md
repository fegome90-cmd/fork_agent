# ADR-002: Skill-Repo Boundary Contract

| Field | Value |
|-------|-------|
| **Status** | Proposed |
| **Date** | 2026-04-26 |
| **Decision Makers** | felipe_gonzalez |
| **Supersedes** | None |
| **Affected** | `tmux-live`, `src/interfaces/cli/commands/`, `src/interfaces/api/routes/agents.py`, `SKILL-REPO-BOUNDARY-GATE.md` |

---

## 1. Context

### Problem

The skill (`tmux-live launch`) spawns agents without consulting `AgentLaunchLifecycleService`. The repo's API route (`POST /agents/sessions`) already uses lifecycle correctly with CAS, dedup, and crash safety. The skill and repo operate as independent systems with no contract between them.

From `gate-authority-matrix-v2.md`:
- 24 BACKEND_FUTURE_GATE exist in the repo (CAS, tests) — none invoked by the skill
- The skill has 11 HARD_EXECUTABLE_INVOKED gates — all infrastructure/format, none semantic
- C5: "Skill bypassa AgentLaunchLifecycleService — spawns sin dedup/lease"

### Evidence

| Surface | Skill | Repo API | Match? |
|---------|-------|----------|--------|
| Agent spawning | `tmux-live launch` → `pi --mode json` directly | `POST /agents/sessions` → `lifecycle.request_launch()` → CAS | NO |
| Dedup | `tmux-live:284` name collision only | `canonical_key` dedup via partial unique index | NO |
| Lease/crash recovery | DONE signal file (basic) | 5min lease + quarantine + reconcile | NO |
| State tracking | Memory MCP (SSOT per state-format.md) | AgentLaunch entity (SSOT per lifecycle service) | NO |
| Termination | `tmux-live kill-all` (manual) | `begin_termination()` → `confirm_terminated()` (CAS) | NO |

### Constraint

`tmux-live` is a bash script. It cannot import Python modules. The contract must be a subprocess call to a CLI or HTTP call to an API — no shared memory, no imports, no SQLite access.

---

## 2. Decision

### Interface: CLI command (primary), API endpoint (secondary)

**Primary**: Add a CLI command `fork launch` to the repo that wraps `AgentLaunchLifecycleService`. `tmux-live launch` calls this CLI command via subprocess.

**Secondary**: The API endpoint `POST /agents/sessions` already exists and uses lifecycle. It can serve as fallback when the API server is running.

**Why CLI as primary**:
1. `tmux-live` is bash. A subprocess call is the natural interface.
2. No dependency on API server being up.
3. The CLI already exists as a Typer app (`src/interfaces/cli/main.py`) — adding a subcommand is minimal.
4. Tests can mock the CLI command without running the repo.

### CLI Contract

```
fork launch request \
  --canonical-key <key> \
  --surface <surface> \
  --owner-type <type> \
  --owner-id <id> \
  --json
```

**Output** (JSON on stdout):
```json
{
  "decision": "claimed" | "suppressed" | "error",
  "launch_id": "<hex>" | null,
  "reason": "<string>" | null
}
```

**Exit codes**:
- 0 = claimed (proceed with spawn)
- 1 = suppressed or error (do NOT spawn)
- 2 = CLI usage error

**Post-launch commands**:
```
fork launch confirm-spawning --launch-id <id> --json
fork launch confirm-active --launch-id <id> \
  --backend tmux \
  --termination-handle-type tmux-session \
  --termination-handle-value <session-name> \
  --tmux-session <session-name> \
  --json

fork launch mark-failed --launch-id <id> --error "<message>" --json
fork launch begin-termination --launch-id <id> --json
fork launch confirm-terminated --launch-id <id> --json
fork launch status --launch-id <id> --json
fork launch list-active --json
```

### Integration in tmux-live

```bash
# Before spawning (Phase 3 - Spawn):
RESULT=$(fork launch request \
  --canonical-key "$CANONICAL_KEY" \
  --surface skill \
  --owner-type agent \
  --owner-id "$AGENT_NAME" \
  --json 2>/dev/null) || {
    # CLI not available — graceful fallback
    log_warn "fork launch request unavailable, proceeding without lifecycle tracking"
    RESULT='{"decision":"claimed","launch_id":null,"reason":"cli_unavailable"}'
  }

DECISION=$(echo "$RESULT" | jq -r '.decision')
if [[ "$DECISION" != "claimed" ]]; then
  log_info "Launch suppressed: $(echo "$RESULT" | jq -r '.reason')"
  return 0  # Skip this agent, not an error
fi

LAUNCH_ID=$(echo "$RESULT" | jq -r '.launch_id')

# Confirm spawning
[[ -n "$LAUNCH_ID" ]] && fork launch confirm-spawning --launch-id "$LAUNCH_ID" --json >/dev/null

# ... actual tmux split-window + pi command ...

# Confirm active
[[ -n "$LAUNCH_ID" ]] && fork launch confirm-active \
  --launch-id "$LAUNCH_ID" \
  --backend tmux \
  --termination-handle-type tmux-session \
  --termination-handle-value "$TMUX_SESSION_NAME" \
  --tmux-session "$TMUX_SESSION_NAME" \
  --json >/dev/null

# On failure:
[[ -n "$LAUNCH_ID" ]] && fork launch mark-failed \
  --launch-id "$LAUNCH_ID" \
  --error "$ERROR_MSG" --json >/dev/null
```

### Fallback Behavior

If `fork launch request` is unavailable (not installed, PATH missing, CLI error):

1. **Log a warning**, do not abort the orchestration.
2. **Proceed without lifecycle tracking** — same behavior as today.
3. **Set `LAUNCH_ID=null`** so downstream confirm/terminate calls are skipped.

This ensures backward compatibility: the skill works with or without the repo CLI.

### Rollback

If `fork launch confirm-active` fails after the agent was already spawned:

1. The agent is running — do NOT kill it.
2. The launch record stays in SPAWNING state.
3. Lease expiry (5min) will quarantine it automatically via `reconcile_expired_leases()`.
4. Next orchestration run can proceed (quarantined launches don't block new ones).

---

## 3. Canonical Key Convention

| Surface | canonical_key format | Example |
|---------|---------------------|---------|
| Skill orchestrator | `skill:<phase>:<agent-role>-<agent-name>` | `skill:3:explorer-exp-01` |
| API session | `api:<agent-type>:<task-hash>` | `api:claude:a1b2c3d4e5f6` |
| Workflow bug-hunt | `workflow:<branch>:<role>-<idx>` | `workflow:fix-auth:implementer-1` |

---

## 4. Test Strategy

### Contract Tests (bats)

```bash
# Test: CLI command exists and returns valid JSON
fork launch request --canonical-key test-001 --surface test --owner-type test --owner-id test --json
# Expected: exit 0, JSON with decision=claimed

# Test: Suppressed on duplicate
fork launch request --canonical-key test-001 --surface test --owner-type test --owner-id test-2 --json
# Expected: exit 1, JSON with decision=suppressed

# Test: Full lifecycle
LAUNCH_ID=$(fork launch request ... --json | jq -r '.launch_id')
fork launch confirm-spawning --launch-id "$LAUNCH_ID" --json
fork launch confirm-active --launch-id "$LAUNCH_ID" --backend test ... --json
fork launch begin-termination --launch-id "$LAUNCH_ID" --json
fork launch confirm-terminated --launch-id "$LAUNCH_ID" --json
# Expected: all exit 0

# Test: Graceful fallback when CLI unavailable
PATH=/usr/bin tmux-live launch explorer test-001 @/tmp/prompt.txt
# Expected: agent spawns with warning, no error
```

### Unit Tests (pytest)

- CLI command wraps `AgentLaunchLifecycleService` correctly
- Exit codes match contract
- JSON output schema is stable
- Edge cases: concurrent requests, expired leases, quarantine recovery

---

## 5. Consequences

### Pros

1. **Skill gains dedup/lease/crash safety** without importing Python code.
2. **Backward compatible** — skill works without CLI, just without lifecycle tracking.
3. **Single authority** — `AgentLaunchLifecycleService` remains the ONLY launch owner.
4. **Testable contract** — bats tests validate CLI interface independently.
5. **No coupling to internals** — skill only knows CLI commands and JSON schema.

### Cons

1. **Subprocess overhead** — `fork launch request` adds ~200ms to each spawn.
2. **CLI must be installed** — skill users need `fork` in PATH. Fallback mitigates this.
3. **Two systems to maintain** — CLI commands must stay in sync with service API.
4. **State divergence risk** — if CLI fails silently, skill and repo diverge.

### Risks

| Risk | Mitigation |
|------|-----------|
| CLI not in PATH | Fallback: proceed without tracking, log warning |
| CLI hangs | `fork launch request` wrapped in `timeout 5` |
| State divergence | Lease expiry + reconcile catches orphaned records |
| CLI output format changes | Contract tests in bats catch schema drift |
| RB-25/26/27 broken gates | Repaired before cableado (boundary sequence step 2) |

---

## 6. Implementation Sequence

1. **Create `SKILL-REPO-BOUNDARY-GATE.md`** — governance document referencing this ADR
2. **Repair RB-25, RB-26, RB-27** — broken backend gates
3. **Add `fork launch` CLI commands** — wrap `AgentLaunchLifecycleService`
4. **Add CLI contract tests** — bats tests for the interface
5. **Modify `tmux-live launch`** — add `fork launch request` call with fallback
6. **Verify** — run full bats suite + integration test

---

## 7. Alternatives Considered

| Alternative | Rejected because |
|------------|-----------------|
| HTTP API call from tmux-live | Requires API server running. CLI works standalone. |
| Shared SQLite access | Bash reading SQLite is fragile. Breaks layer separation. |
| MCP tool call | MCP protocol overhead. tmux-live is bash, not an MCP client. |
| Move lifecycle to bash | Would lose CAS, tests, entity model. Massive regression. |
| No integration (current state) | Spawns without dedup/lease/crash safety. Risk C5 remains. |
