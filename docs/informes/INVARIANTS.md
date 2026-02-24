# fork_agent - System Invariants

> **Generated:** 2026-02-23 | **Auditor:** Sisyphus
> 
> This document defines explicit, verifiable invariants that must hold for system correctness.

---

## 1. Workflow Phase Invariants

### INV-WF-001: Phase Ordering

| Property | Value |
|----------|-------|
| **Description** | Workflow phases must follow strict order: outline → execute → verify → ship |
| **Enforcement** | CLI command checks in `src/interfaces/cli/commands/workflow.py` |
| **Location** | L23-47 (check functions), L87-88, L111-112, L133-138 |
| **How Verified** | `_check_plan_exists()`, `_check_execute_exists()`, `_check_verify_exists()` |
| **Risk if Fails** | Operations executed without plan, untested code shipped |
| **Coverage** | Partial - CLI enforces, but programmatic API bypass possible |
| **Priority** | P0 |

```python
# Evidence: workflow.py L23-29
def _check_plan_exists() -> PlanState:
    plan_path = get_plan_state_path()
    plan = PlanState.load(plan_path)
    if plan is None:
        typer.echo("Error: No plan found. Run 'memory workflow outline' first.", err=True)
        raise typer.Exit(1)
    return plan
```

### INV-WF-002: Ship Gate (unlock_ship)

| Property | Value |
|----------|-------|
| **Description** | `ship` command requires `verify-state.json` with `unlock_ship=True` |
| **Enforcement** | CLI check in workflow.py L133-138 |
| **Location** | `src/interfaces/cli/commands/workflow.py:133-138` |
| **How Verified** | `if not verify_state.unlock_ship: raise typer.Exit(1)` |
| **Risk if Fails** | Unverified code deployed to production |
| **Coverage** | Good - enforced at CLI level |
| **Priority** | P0 |

```python
# Evidence: workflow.py L133-138
@app.command("ship")
def ship(...) -> None:
    verify_state = _check_verify_exists()
    if not verify_state.unlock_ship:
        typer.echo("Error: Verification not complete...", err=True)
        raise typer.Exit(1)
```

### INV-WF-003: State File Consistency & Versioning

| Property | Value |
|----------|-------|
| **Description** | State files must contain valid JSON with required fields and schema version |
| **Enforcement** | `from_json()` with schema versioning and migration logic |
| **Location** | `src/application/services/workflow/state.py` |
| **How Verified** | `schema_version` field, `migrated_from` tracking, fail-closed on unknown versions |
| **Risk if Fails** | Corrupted state causes workflow to fail or misbehave |
| **Coverage** | Full - v0→v1 migration, fail-closed for future versions, validation on load |
| **Priority** | P0 |

```python
# Evidence: state.py - CURRENT_SCHEMA_VERSION = 1
# - v0 states (no schema_version) auto-migrate to v1
# - Future versions (>1) raise UnsupportedSchemaError
# - Invalid JSON / missing session_id raise InvalidStateError
```

---

## 2. tmux Session Invariants

### INV-TM-001: Session Naming Convention

| Property | Value |
|----------|-------|
| **Description** | All fork sessions must follow pattern: `agent-{agent_name}-{timestamp}` |
| **Enforcement** | Hook script `.hooks/tmux-session-per-agent.sh` L19 + `TmuxAgent.__init__` |
| **Location** | `src/application/services/agent/agent_manager.py:214` |
| **How Verified** | Unit test: `test_invariants.py::TestTmuxSessionNaming` |
| **Risk if Fails** | Session collisions, orphaned sessions |
| **Coverage** | Full (tested) - 3 tests |
| **Priority** | P1 |

### INV-TM-002: Session Uniqueness

| Property | Value |
|----------|-------|
| **Description** | No two agents with the same name should have concurrent sessions |
| **Enforcement** | **Not enforced** - timestamp provides de facto uniqueness |
| **Location** | N/A |
| **How Verified** | None |
| **Risk if Fails** | Multiple sessions for same agent, confusion |
| **Coverage** | Not covered |
| **Priority** | P2 |

### INV-TM-003: Session Cleanup

| Property | Value |
|----------|-------|
| **Description** | Terminated agents must have their tmux sessions killed |
| **Enforcement** | `TmuxAgent.terminate()` in agent_manager.py L250-268 |
| **Location** | `src/application/services/agent/agent_manager.py:250-268` |
| **How Verified** | Test: `test_agent_manager.py` (partial) |
| **Risk if Fails** | Orphaned sessions consume resources |
| **Coverage** | Partial - no zombie detection |
| **Priority** | P1 |

---

## 3. Circuit Breaker Invariants

### INV-CB-001: Failure Threshold

| Property | Value |
|----------|-------|
| **Description** | Circuit opens after exactly `failure_threshold` consecutive failures |
| **Enforcement** | `TmuxCircuitBreaker.record_failure()` |
| **Location** | `src/infrastructure/tmux_orchestrator/circuit_breaker.py:54-60` |
| **How Verified** | Unit test: `test_circuit_breaker.py::test_opens_after_threshold_failures` |
| **Risk if Fails** | Cascading failures, resource exhaustion |
| **Coverage** | Good - 8 unit tests |
| **Priority** | P0 |

```python
# Evidence: circuit_breaker.py L54-60
def record_failure(self) -> None:
    with self._lock:
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self._failure_threshold:
            self._state = CircuitState.OPEN
```

### INV-CB-002: Recovery Timeout

| Property | Value |
|----------|-------|
| **Description** | Circuit transitions to HALF_OPEN after `recovery_timeout` seconds |
| **Enforcement** | `TmuxCircuitBreaker.state` property |
| **Location** | `src/infrastructure/tmux_orchestrator/circuit_breaker.py:40-47` |
| **How Verified** | Unit test: `test_circuit_breaker.py::test_opens_immediately_with_zero_timeout` |
| **Risk if Fails** | System stuck in OPEN state permanently |
| **Coverage** | Partial - only zero timeout tested |
| **Priority** | P1 |

### INV-CB-003: HALF_OPEN Call Limit

| Property | Value |
|----------|-------|
| **Description** | Only `half_open_max_calls` (default 2) allowed in HALF_OPEN state |
| **Enforcement** | `TmuxCircuitBreaker.can_execute()` |
| **Location** | `src/infrastructure/tmux_orchestrator/circuit_breaker.py:66-70` |
| **How Verified** | No explicit test |
| **Risk if Fails** | Too many calls during recovery, repeated failures |
| **Coverage** | Not covered |
| **Priority** | P1 |

---

## 4. Persistence Invariants

### INV-DB-001: WAL Mode Enabled

| Property | Value |
|----------|-------|
| **Description** | Database must use WAL journal mode for concurrent access |
| **Enforcement** | `DatabaseConnection._apply_pragmas()` |
| **Location** | `src/infrastructure/persistence/database.py:133-137` |
| **How Verified** | Manual inspection |
| **Risk if Fails** | Database locks, corruption under concurrent access |
| **Coverage** | Not tested |
| **Priority** | P1 |

### INV-DB-002: Foreign Key Enforcement

| Property | Value |
|----------|-------|
| **Description** | SQLite foreign key constraints must be enabled |
| **Enforcement** | `PRAGMA foreign_keys=ON` in database.py L137 |
| **Location** | `src/infrastructure/persistence/database.py:137` |
| **How Verified** | Manual inspection |
| **Risk if Fails** | Orphan records, referential integrity violations |
| **Coverage** | Not tested |
| **Priority** | P1 |

### INV-DB-003: Observation ID Uniqueness

| Property | Value |
|----------|-------|
| **Description** | Observation IDs must be unique (PRIMARY KEY) |
| **Enforcement** | SQLite constraint + Repository error handling |
| **Location** | `src/infrastructure/persistence/repositories/observation_repository.py:44-48` |
| **How Verified** | `RepositoryError` raised on duplicate |
| **Risk if Fails** | Duplicate observations, data corruption |
| **Coverage** | Partial - error handling tested |
| **Priority** | P0 |

```python
# Evidence: observation_repository.py L44-48
except sqlite3.IntegrityError as e:
    raise RepositoryError(
        f"Observation with id '{observation.id}' already exists",
        e,
    ) from e
```

### INV-DB-004: Thread-Local Connections

| Property | Value |
|----------|-------|
| **Description** | Each thread gets its own database connection |
| **Enforcement** | `threading.local()` in database.py |
| **Location** | `src/infrastructure/persistence/database.py:14, 93-101` |
| **How Verified** | Code inspection |
| **Risk if Fails** | Connection sharing, thread safety violations |
| **Coverage** | Not tested for thread safety |
| **Priority** | P1 |

---

## 5. Hook Invariants

### INV-HK-001: Hook Timeout Enforcement

| Property | Value |
|----------|-------|
| **Description** | Hooks must complete within configured timeout (default 30s) |
| **Enforcement** | `subprocess.run(timeout=...)` in ShellActionRunner |
| **Location** | `src/infrastructure/orchestration/shell_action_runner.py:113-123` |
| **How Verified** | `RuntimeError` raised on timeout |
| **Risk if Fails** | Hanging hooks block system |
| **Coverage** | Partial - test_hook_runner_security.py tests timeout |
| **Priority** | P1 |

```python
# Evidence: shell_action_runner.py L113-123
try:
    result = subprocess.run(
        action.command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=safe_env,
    )
except subprocess.TimeoutExpired as e:
    raise RuntimeError(f"Action timed out after {timeout} seconds...") from e
```

### INV-HK-002: Dangerous Environment Variables Blocked

| Property | Value |
|----------|-------|
| **Description** | `LD_PRELOAD`, `LD_LIBRARY_PATH`, etc. must be filtered |
| **Enforcement** | `_get_safe_env()` in ShellActionRunner |
| **Location** | `src/infrastructure/orchestration/shell_action_runner.py:66-93` |
| **How Verified** | Test: `test_hook_runner_security.py` |
| **Risk if Fails** | Code injection, privilege escalation |
| **Coverage** | Good - 11 security tests |
| **Priority** | P0 |

### INV-HK-003: Git Guard Enforcement

| Property | Value |
|----------|-------|
| **Description** | Dangerous git commands must be blocked |
| **Enforcement** | `git-branch-guard.sh` allowlist |
| **Location** | `.hooks/git-branch-guard.sh:15-18, 21-24` |
| **How Verified** | Exit code 2 = blocked |
| **Risk if Fails** | Accidental destructive git operations |
| **Coverage** | Not tested |
| **Priority** | P1 |

---

## 6. Dead Letter Queue Invariants

### INV-DLQ-001: Max Size Enforcement

| Property | Value |
|----------|-------|
| **Description** | DLQ must not exceed `max_size` (default 1000) items |
| **Enforcement** | `queue.Queue(maxsize=max_size)` |
| **Location** | `src/infrastructure/tmux_orchestrator/dead_letter_queue.py:33, 54-58` |
| **How Verified** | `queue.Full` exception logged, item dropped |
| **Risk if Fails** | Memory exhaustion |
| **Coverage** | Partial - test exists for max_size |
| **Priority** | P2 |

### INV-DLQ-002: Persistence Format

| Property | Value |
|----------|-------|
| **Description** | DLQ persisted to JSON with specific schema |
| **Enforcement** | `DeadLetterQueue.persist()` serialization |
| **Location** | `src/infrastructure/tmux_orchestrator/dead_letter_queue.py:87-109` |
| **How Verified** | `DeadLetterQueue.load()` deserialization |
| **Risk if Fails** | Lost messages on restart |
| **Coverage** | Partial - persist/load tested |
| **Priority** | P2 |

---

## 10. Resilience Policy Invariants (Post WO-Next-05)

### INV-RES-001: Single Source of Truth

| Property | Value |
|----------|-------|
| **Description** | All circuit breakers must use the same resilience policy from `resilience_policy.py` |
| **Enforcement** | Both `TmuxCircuitBreaker` and `AgentManager.CircuitBreaker` use `ResiliencePolicy` |
| **Location** | `src/infrastructure/tmux_orchestrator/resilience_policy.py` |
| **How Verified** | Both classes now accept `policy` parameter and use `DEFAULT_POLICY` |
| **Risk if Fails** | Inconsistent behavior across components |
| **Coverage** | Full - refactored |
| **Priority** | P1 |

### INV-RES-002: HALF_OPEN Transition Determinism

| Property | Value |
|----------|-------|
| **Description** | Circuit must transition deterministically: CLOSED→OPEN→HALF_OPEN→CLOSED/OPEN |
| **Enforcement** | State property checks timeout, can_execute limits HALF_OPEN calls |
| **Location** | `src/infrastructure/tmux_orchestrator/circuit_breaker.py:60-90` |
| **How Verified** | Unit tests: `TestCircuitBreakerTransitions` (5 tests) |
| **Risk if Fails** | Unpredictable recovery behavior |
| **Coverage** | Full - tested |
| **Priority** | P1 |

### INV-RES-003: Policy Observable in Health

| Property | Value |
|----------|-------|
| **Description** | Effective policy must be visible in health/metrics endpoint |
| **Enforcement** | `build_health_response()` includes policy in CB info |
| **Location** | `src/infrastructure/tmux_orchestrator/health.py` |
| **How Verified** | HealthResponse includes `policy` dict |
| **Risk if Fails** | Cannot verify policy in production |
| **Coverage** | Full |
| **Priority** | P1 |

---

## 11. Invariant Coverage Summary (Updated Post WO-Next-06)

| ID | Description | Priority | Coverage | Test File |
|----|-------------|----------|----------|-----------|
| INV-WF-001 | Phase ordering | P0 | **Full** | `test_invariants.py::TestWorkflowPhaseOrdering` |
| INV-WF-002 | Ship gate (unlock_ship) | P0 | Good | - |
| INV-WF-003 | State file consistency | P1 | Full | `test_state.py` |
| INV-TMUX-001 | Session naming | P1 | **Full (tested)** | `test_invariants.py::TestTmuxSessionNaming` |
| INV-TMUX-002 | Orphan detection | P1 | Full (tested) | `test_agent_manager.py` |
| INV-OPS-001 | Doctor/reconcile safety | P0 | Full (tested) | `test_agent_manager.py` |
| INV-RES-001 | CB SSOT | P1 | **Full (tested)** | `test_invariants.py::TestResiliencePolicySSOT` |
| INV-RES-002 | HALF_OPEN determinism | P1 | Full (tested) | `test_circuit_breaker.py` |
| INV-RES-003 | Policy observable | P1 | Full | - |
| INV-CB-001 | Failure threshold | P0 | Good | `test_circuit_breaker.py` |
| INV-CB-002 | Recovery timeout | P1 | **Full (tested)** | `test_invariants.py::TestCircuitBreakerRecoveryTimeout` |
| INV-CB-003 | HALF_OPEN limit | P1 | Full (tested) | `test_circuit_breaker.py` |
| INV-DB-001 | WAL mode | P1 | Full (tested) | `test_database_config.py` |
| INV-DB-002 | Foreign keys | P1 | Full (tested) | `test_database_config.py` |
| INV-DB-003 | ID uniqueness | P0 | Partial | - |
| INV-DB-004 | Thread-local | P1 | **Full (tested)** | `test_invariants.py::TestDatabaseThreadLocal` |
| INV-HK-001 | Hook timeout | P1 | Partial | - |
| INV-HK-002 | Env var filtering | P0 | Good | `test_shell_action_runner.py` |
| INV-HK-003 | Git guard | P1 | **Full (tested)** | `test_invariants.py::TestGitGuard` |
| INV-HK-004 | Hook on_failure policy | P1 | **Full (tested)** | `test_invariants.py::TestHookOnFailurePolicy` |
| INV-DLQ-001 | DLQ max size | P2 | **Full (tested)** | `test_invariants.py::TestDLQMaxSize` |
| INV-DLQ-002 | DLQ persistence | P2 | Partial | - |

---

*Document updated by invariants audit - 2026-02-23 (Post Sprint 2)*
