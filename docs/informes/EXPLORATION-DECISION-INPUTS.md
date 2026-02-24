# fork_agent - Exploration Decision Inputs

> **Generated:** 2026-02-23 | **Auditor:** Sisyphus
> 
> Evidence-based report for engineering decisions.

---

## 1. Executive Summary

This audit of the `fork_agent` codebase reveals a well-architected DDD system with solid resilience patterns (CircuitBreaker, Retry, DLQ) but significant gaps in test coverage for critical paths, missing schema versioning, and no automated recovery mechanisms.

**Key Findings:**
- **63 test files** with ~802 tests total, but **workflow state machine has no unit tests**
- **Resilience layer complete**: CircuitBreaker, Retry, DLQ all implemented with tests
- **18 invariants** identified, **7 not covered** by tests
- **19 failure modes** catalogued, **6 with no mitigation**
- **24 decision gaps** requiring data collection before next development phase

---

## 2. Evidence Map

### 2.1 Test Coverage Evidence

| Component | Test File | Location | Tests | Coverage |
|-----------|-----------|----------|-------|----------|
| CircuitBreaker | `test_circuit_breaker.py` | `tests/unit/infrastructure/tmux_orchestrator/` | 8 | Good |
| DeadLetterQueue | `test_dead_letter_queue.py` | `tests/unit/infrastructure/tmux_orchestrator/` | 9 | Good |
| Retry | `test_retry.py` | `tests/unit/infrastructure/tmux_orchestrator/` | 7 | Good |
| HookRunner | `test_hook_runner.py` | `tests/unit/application/services/workspace/` | 9 | Partial |
| HookSecurity | `test_hook_runner_security.py` | `tests/integration/` | 11 | Good |
| MessageStore | `test_message_store.py` | `tests/unit/infrastructure/persistence/` | 19 | Good |
| ScheduledTask | `test_scheduled_task_repository.py` | `tests/unit/infrastructure/persistence/` | 21 | Good |
| Fork CLI | `test_fork.py` | `tests/unit/interfaces/cli/` | 6 | Limited |
| Workflow | **No unit tests** | N/A | 0 | **Not covered** |

### 2.2 Resilience Evidence

| Component | File | Lines | Config Values |
|-----------|------|-------|---------------|
| TmuxCircuitBreaker | `circuit_breaker.py` | L18-80 | failure_threshold=3, recovery_timeout=30, half_open_max_calls=2 |
| ExponentialBackoff | `retry.py` | L31-46 | base_delay=1.0, max_delay=10.0, exponential_base=2.0 |
| RetryConfig | `retry.py` | L15-20 | max_retries=3 |
| DeadLetterQueue | `dead_letter_queue.py` | L26-148 | max_size=1000 |
| AgentManager.CircuitBreaker | `agent_manager.py` | L57-103 | failure_threshold=5, recovery_timeout=60 (different from Tmux!) |

**Note:** Two different CircuitBreaker implementations exist with different configs:
- `TmuxCircuitBreaker`: threshold=3, recovery=30s
- `AgentManager.CircuitBreaker`: threshold=5, recovery=60s

### 2.3 Database Evidence

| Component | File | Lines | Evidence |
|-----------|------|-------|----------|
| WAL Mode | `database.py` | L133-134 | `PRAGMA journal_mode=WAL` |
| Busy Timeout | `database.py` | L135 | `PRAGMA busy_timeout=5000` |
| Foreign Keys | `database.py` | L136-137 | `PRAGMA foreign_keys=ON` |
| Thread-Local | `database.py` | L14, L93-101 | `_thread_local = threading.local()` |
| Observation Schema | `observation_repository.py` | L39-42 | id, timestamp, content, metadata |
| Message Schema | `message_store.py` | L46-55 | 9 columns + 4 indexes |

### 2.4 Workflow Evidence

| Component | File | Lines | Evidence |
|-----------|------|-------|----------|
| WorkflowPhase | `state.py` | L12-21 | 8 phases: PLANNING → SHIPPED |
| PlanState | `state.py` | L33-95 | session_id, status, phase, tasks[], plan_file |
| ExecuteState | `state.py` | L97-158 | session_id, status, phase, tasks[], current_task_index |
| VerifyState | `state.py` | L161-207 | session_id, status, unlock_ship, test_results, evidence |
| Gate: outline | `workflow.py` | L50-79 | No prerequisites |
| Gate: execute | `workflow.py` | L82-104 | Requires plan-state.json (L87-88) |
| Gate: verify | `workflow.py` | L107-125 | Requires execute-state.json (L111-112) |
| Gate: ship | `workflow.py` | L128-141 | Requires verify-state.json + unlock_ship=True (L133-138) |

**Critical Gap:** No schema version field in state files.

### 2.5 Hooks Evidence

| Component | File | Lines | Evidence |
|-----------|------|-------|----------|
| hooks.json | `.hooks/hooks.json` | L1-54 | 4 events configured |
| SessionStart | hooks.json | L5-15 | workspace-init.sh, timeout=5 |
| SubagentStart | hooks.json | L17-28 | tmux-session-per-agent.sh, timeout=10 |
| SubagentStop | hooks.json | L29-40 | memory-trace-writer.sh, timeout=5 |
| PreToolUse | hooks.json | L41-52 | git-branch-guard.sh, timeout=1 |
| DANGEROUS_ENV_VARS | `shell_action_runner.py` | L12-31 | 16 vars blocked |
| SAFE_DEFAULT_ENV_VARS | `shell_action_runner.py` | L33-46 | 10 vars allowed |

**Critical Gap:** No `critical` field to distinguish blocking vs non-blocking hooks.

### 2.6 fork-generate Evidence

| Component | File | Lines | Evidence |
|-----------|------|-------|----------|
| Agent validation | `fork-generate.sh` | L28-38 | Only .claude, .opencode, .kilocode, .gemini |
| Directory creation | `fork-generate.sh` | L42-61 | Per-agent structure |
| Commands copied | `fork-generate.sh` | L64-98 | fork-checkpoint, fork-resume, fork-prune |
| Hooks copied | `fork-generate.sh` | L100-157 | .sh scripts + settings.json |
| Skills copied | `fork-generate.sh` | L159-182 | fork_terminal/, fork_agent_session.md |
| State files | `fork-generate.sh` | L184-201 | plan/execute/verify-state.json |

**Critical Gap:** No verification step after generation.

---

## 3. Coverage Matrix

### 3.1 Component vs Tests

| Component | Unit Tests | Integration | E2E | Total | Status |
|-----------|------------|-------------|-----|-------|--------|
| tmux_orchestrator | 24 | 0 | 0 | 24 | ✅ Good |
| workflow/state | **0** | 24 | 0 | 24 | ⚠️ No unit tests |
| hooks | 9 | 11 | 10 | 30 | ✅ Good |
| persistence | 40+ | 0 | 0 | 40+ | ✅ Good |
| fork (CLI) | 6 | 0 | 0 | 6 | ⚠️ Limited |
| agent_manager | 8 | 0 | 0 | 8 | ⚠️ Partial |
| orchestration | 4 | 0 | 0 | 4 | ⚠️ Limited |

### 3.2 Invariants vs Coverage

| Invariant | Priority | Test Coverage | Status |
|-----------|----------|---------------|--------|
| INV-WF-001 Phase ordering | P0 | Partial (CLI only) | ⚠️ |
| INV-WF-002 Ship gate | P0 | Good | ✅ |
| INV-WF-003 State consistency | P1 | Partial | ⚠️ |
| INV-CB-001 Failure threshold | P0 | Good (8 tests) | ✅ |
| INV-CB-002 Recovery timeout | P1 | Partial | ⚠️ |
| INV-CB-003 HALF_OPEN limit | P1 | **Not covered** | ❌ |
| INV-DB-001 WAL mode | P1 | **Not tested** | ❌ |
| INV-DB-002 Foreign keys | P1 | **Not tested** | ❌ |
| INV-DB-003 ID uniqueness | P0 | Partial | ⚠️ |
| INV-DB-004 Thread-local | P1 | **Not tested** | ❌ |
| INV-HK-001 Timeout | P1 | Partial | ⚠️ |
| INV-HK-002 Env filtering | P0 | Good (11 tests) | ✅ |
| INV-HK-003 Git guard | P1 | **Not tested** | ❌ |

---

## 4. Missing Data for Decisions (Top 10)

### 4.1 P0/P1 Gaps

| # | Gap | Question | Where to Look | Impact |
|---|-----|----------|---------------|--------|
| 1 | **State Schema Versioning** | How do we handle state file schema changes? | `state.py` - no version field | Breaking changes corrupt workflows |
| 2 | **Migration System** | How are database schema migrations handled? | `migrations.py` - imported but not found | Manual DB recreation required |
| 3 | **Idempotency Mechanism** | How do we ensure operations are idempotent? | Repositories - no event_id/dedup | Duplicate operations on retry |
| 4 | **Orphan Session Detection** | How do we detect/clean up orphaned tmux sessions? | AgentManager - no zombie detection | Resource leaks |
| 5 | **Hook Criticality Levels** | Which hooks are critical vs non-blocking? | hooks.json - no critical field | Non-critical hooks block workflow |
| 6 | **Circuit Breaker Alerting** | How do we know when circuit opens? | metrics.py - no notifications | Silent failures |
| 7 | **Fork Verification** | How do we verify generated fork is complete? | fork-generate.sh - no verify step | Incomplete forks cause errors |
| 8 | **Concurrent Workflow Access** | What happens with simultaneous state writes? | state.py - no file locking | State corruption |
| 9 | **HALF_OPEN Call Limit** | Is the 2-call limit actually enforced? | circuit_breaker.py L66-70 - no test | Recovery overload |
| 10 | **Database Thread Safety** | Are thread-local connections actually safe? | database.py - no concurrent tests | Race conditions |

---

## 5. Recommended Next WOs (Prioritized)

### WO-1: Add State Schema Versioning + Migration (P0)

**Rationale:** Without versioning, any schema change corrupts existing workflows. This is a **breaking change waiting to happen**.

**Scope:**
- Add `schema_version` field to PlanState, ExecuteState, VerifyState
- Implement migration logic in `from_json()` methods
- Add tests for forward/backward compatibility

**Files:**
- `src/application/services/workflow/state.py`
- `tests/unit/application/services/workflow/test_state.py` (new)

**Effort:** 4-6 hours

---

### WO-2: Implement Orphan Session Detection/Cleanup (P1)

**Rationale:** tmux sessions persist after agent termination, causing resource leaks and confusion.

**Scope:**
- Add `cleanup_orphans()` method to AgentManager
- Compare `tmux ls` with tracked `_agents` dict
- Add `--cleanup-orphans` CLI option
- Run on session start as health check

**Files:**
- `src/application/services/agent/agent_manager.py`
- `src/interfaces/cli/fork.py`
- `tests/unit/application/services/agent/test_agent_manager.py`

**Effort:** 3-4 hours

---

### WO-3: Add Hook Criticality Levels (P1)

**Rationale:** Currently all hooks can block workflow. Non-critical hooks (observational) should not block.

**Scope:**
- Add `critical: bool` field to hooks.json schema
- Modify ShellActionRunner to handle critical vs non-critical
- Critical hooks abort workflow on failure
- Non-critical hooks log and continue

**Files:**
- `.hooks/hooks.json`
- `src/infrastructure/orchestration/shell_action_runner.py`
- `src/infrastructure/orchestration/rule_loader.py`
- `tests/unit/infrastructure/orchestration/test_shell_action_runner.py`

**Effort:** 2-3 hours

---

### WO-4: Add Circuit Breaker Open Alerting (P1)

**Rationale:** Circuit breaker opens silently, causing all operations to fail with no notification.

**Scope:**
- Add callback mechanism to CircuitBreaker
- Fire callback on state transition to OPEN
- Log warning with context
- Consider Slack/email notification (future)

**Files:**
- `src/infrastructure/tmux_orchestrator/circuit_breaker.py`
- `src/infrastructure/tmux_orchestrator/metrics.py`
- `tests/unit/infrastructure/tmux_orchestrator/test_circuit_breaker.py`

**Effort:** 2-3 hours

---

### WO-5: Add fork-generate Verify Command (P1)

**Rationale:** Generated forks may be incomplete, causing runtime failures at destination.

**Scope:**
- Add `--verify` flag to fork-generate.sh
- Check all expected files exist
- Validate JSON files parse correctly
- Verify permissions on scripts

**Files:**
- `scripts/fork-generate.sh`
- `tests/e2e/test_fork_generate_e2e.py` (new)

**Effort:** 2 hours

---

## 6. Risks if We Continue Without Closing Gaps

### 6.1 Immediate Risks (P0)

| Risk | Gap | Consequence | Likelihood |
|------|-----|-------------|------------|
| **State Corruption** | No schema versioning | Existing workflows break on update | High |
| **Duplicate Operations** | No idempotency | Data corruption on retries | Medium |
| **Silent Failures** | No CB alerting | Operations fail without detection | Medium |

### 6.2 Medium-Term Risks (P1)

| Risk | Gap | Consequence | Likelihood |
|------|-----|-------------|------------|
| **Resource Exhaustion** | No orphan cleanup | System slowdown, OOM | High |
| **Workflow Blocking** | No hook criticality | Non-critical hooks halt system | Medium |
| **Incomplete Deploys** | No fork verify | Runtime errors in new projects | Medium |
| **State Corruption** | No concurrent access handling | Lost updates, corruption | Medium |

### 6.3 Technical Debt Accumulation

Without addressing these gaps:
- Each new feature increases surface area for bugs
- Manual intervention becomes常态
- System reliability degrades over time
- On-call burden increases

---

## 7. Appendix: File Reference

| Category | File | Key Lines |
|----------|------|-----------|
| Architecture | `docs/ARCHITECTURE.md` | Full |
| Operations | `docs/OPERATIONS.md` | Full |
| Invariants | `docs/INVARIANTS.md` | Full |
| Failure Modes | `docs/FAILURE_MODES.md` | Full |
| Decision Gaps | `docs/DECISION-GAPS.md` | Full |
| Circuit Breaker | `src/infrastructure/tmux_orchestrator/circuit_breaker.py` | L18-80 |
| Retry | `src/infrastructure/tmux_orchestrator/retry.py` | L15-127 |
| DLQ | `src/infrastructure/tmux_orchestrator/dead_letter_queue.py` | L26-148 |
| Database | `src/infrastructure/persistence/database.py` | L61-170 |
| Workflow State | `src/application/services/workflow/state.py` | L12-223 |
| Workflow CLI | `src/interfaces/cli/commands/workflow.py` | L23-165 |
| Hooks Config | `.hooks/hooks.json` | L1-54 |
| Shell Runner | `src/infrastructure/orchestration/shell_action_runner.py` | L12-127 |
| Agent Manager | `src/application/services/agent/agent_manager.py` | L57-380 |
| Fork Generate | `scripts/fork-generate.sh` | L1-346 |
| Tests | `tests/` | 63 files |

---

*Document generated by evidence-based audit - 2026-02-23*
