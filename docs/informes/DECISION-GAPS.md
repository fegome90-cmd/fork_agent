# fork_agent - Decision Gaps

> **Generated:** 2026-02-23 | **Auditor:** Sisyphus
> 
> This document catalogues data gaps that block engineering decisions.

---

## 1. Runtime tmux Gaps

### GAP-TM-001: Session Lifecycle Monitoring

| Property | Value |
|----------|-------|
| **Question** | How do we detect and clean up orphaned tmux sessions? |
| **Missing Data** | Session health check mechanism, zombie detection algorithm |
| **Where to Look** | `src/infrastructure/tmux_orchestrator/__init__.py`, AgentManager |
| **How to Measure** | Count sessions in `tmux ls` vs tracked in `_agents` dict |
| **Impact** | Resource leaks, confusing user experience |
| **Priority** | P1 |

### GAP-TM-002: Session Naming Collision

| Property | Value |
|----------|-------|
| **Question** | What happens if two agents with same name spawn simultaneously? |
| **Missing Data** | Collision handling behavior, session uniqueness enforcement |
| **Where to Look** | `tmux-session-per-agent.sh`, `TmuxAgent.spawn()` |
| **How to Measure** | Test: spawn two agents with same name concurrently |
| **Impact** | Session creation failure, unpredictable behavior |
| **Priority** | P2 |

### GAP-TM-003: Session Resource Limits

| Property | Value |
|----------|-------|
| **Question** | How many concurrent tmux sessions can the system handle? |
| **Missing Data** | Performance limits, resource usage per session |
| **Where to Look** | System documentation, load testing |
| **How to Measure** | Load test with increasing session counts |
| **Impact** | System failure under load |
| **Priority** | P2 |

---

## 2. Workflow/Gates Gaps

### GAP-WF-001: State Schema Versioning

| Property | Value |
|----------|-------|
| **Question** | How do we handle state file schema changes? |
| **Missing Data** | Schema version field, migration strategy |
| **Where to Look** | `src/application/services/workflow/state.py` |
| **How to Measure** | Check for `schema_version` field in state files |
| **Impact** | Breaking changes corrupt existing workflows |
| **Priority** | P1 |

### GAP-WF-002: State Validation

| Property | Value |
|----------|-------|
| **Question** | How do we validate state files match reality? |
| **Missing Data** | State verification logic, drift detection |
| **Where to Look** | workflow.py, state.py |
| **How to Measure** | Compare state file tasks with actual filesystem/git state |
| **Impact** | Stale state causes incorrect workflow behavior |
| **Priority** | P2 |

### GAP-WF-003: Phase Skip Prevention

| Property | Value |
|----------|-------|
| **Question** | Can workflow phases be bypassed programmatically? |
| **Missing Data** | API-level enforcement (not just CLI) |
| **Where to Look** | MemoryService, Use Cases |
| **How to Measure** | Test: call workflow methods directly, skip phases |
| **Impact** | Unverified code shipped via API |
| **Priority** | P1 |

### GAP-WF-004: Concurrent Workflow Access

| Property | Value |
|----------|-------|
| **Question** | What happens if two processes modify workflow state simultaneously? |
| **Missing Data** | File locking, concurrent access handling |
| **Where to Look** | state.py save/load methods |
| **How to Measure** | Test: concurrent writes to same state file |
| **Impact** | State corruption, lost updates |
| **Priority** | P2 |

---

## 3. Hooks Gaps

### GAP-HK-001: Hook Criticality Levels

| Property | Value |
|----------|-------|
| **Question** | Which hooks are critical (must succeed) vs observantional (can fail)? |
| **Missing Data** | Criticality metadata in hooks.json, abort behavior |
| **Where to Look** | `.hooks/hooks.json`, ShellActionRunner, EventDispatcher |
| **How to Measure** | Check for `critical` field in hook config |
| **Impact** | Non-critical hook failure blocks workflow |
| **Priority** | P1 |

### GAP-HK-002: Hook Output Schema

| Property | Value |
|----------|-------|
| **Question** | What is the expected output format from hooks? |
| **Missing Data** | Output schema definition, validation |
| **Where to Look** | Hook scripts, ShellActionRunner |
| **How to Measure** | Analyze hook output parsing code |
| **Impact** | Inconsistent hook output breaks orchestration |
| **Priority** | P2 |

### GAP-HK-003: Hook Retry Policy

| Property | Value |
|----------|-------|
| **Question** | Should failed hooks be retried? |
| **Missing Data** | Retry configuration, DLQ for hooks |
| **Where to Look** | ShellActionRunner, EventDispatcher |
| **How to Measure** | Check for retry logic in hook execution |
| **Impact** | Transient hook failures cause permanent failures |
| **Priority** | P2 |

### GAP-HK-004: Hook Execution Order

| Property | Value |
|----------|-------|
| **Question** | Are hooks executed in order? In parallel? |
| **Missing Data** | Execution semantics, ordering guarantee |
| **Where to Look** | EventDispatcher.dispatch() |
| **How to Measure** | Test: multiple hooks for same event, check execution order |
| **Impact** | Unexpected hook execution order |
| **Priority** | P3 |

---

## 4. Memory/SQLite Gaps

### GAP-DB-001: Migration System

| Property | Value |
|----------|-------|
| **Question** | How are database schema migrations handled? |
| **Missing Data** | Migration runner, version tracking, rollback |
| **Where to Look** | `src/infrastructure/persistence/migrations.py` (imported but not found) |
| **How to Measure** | Check for migrations table, migration files |
| **Impact** | Schema changes require manual DB recreation |
| **Priority** | P1 |

### GAP-DB-002: Idempotency Mechanism

| Property | Value |
|----------|-------|
| **Question** | How do we ensure operations are idempotent? |
| **Missing Data** | Event ID, deduplication, idempotency keys |
| **Where to Look** | ObservationRepository, MessageStore |
| **How to Measure** | Check for UNIQUE constraints, deduplication logic |
| **Impact** | Duplicate operations on retry |
| **Priority** | P1 |

### GAP-DB-003: Connection Pooling

| Property | Value |
|----------|-------|
| **Question** | Is there connection pooling or just thread-local? |
| **Missing Data** | Connection pool configuration, limits |
| **Where to Look** | DatabaseConnection |
| **How to Measure** | Check for pool implementation |
| **Impact** | Connection exhaustion under load |
| **Priority** | P2 |

### GAP-DB-004: Backup/Restore

| Property | Value |
|----------|-------|
| **Question** | How do we backup and restore the database? |
| **Missing Data** | Backup mechanism, restore procedure |
| **Where to Look** | Infrastructure layer |
| **How to Measure** | Check for backup commands/API |
| **Impact** | Data loss on corruption |
| **Priority** | P2 |

---

## 5. Observability Gaps

### GAP-OBS-001: Alerting on Circuit Breaker

| Property | Value |
|----------|-------|
| **Question** | How do we know when circuit breaker opens? |
| **Missing Data** | Alerting mechanism, notification |
| **Where to Look** | metrics.py, health.py |
| **How to Measure** | Check for alert/notification code |
| **Impact** | Silent failures, delayed response |
| **Priority** | P1 |

### GAP-OBS-002: Correlation IDs

| Property | Value |
|----------|-------|
| **Question** | Are there correlation/session IDs in logs? |
| **Missing Data** | Structured logging, correlation fields |
| **Where to Look** | json_logging.py, all log statements |
| **How to Measure** | Check log output for correlation IDs |
| **Impact** | Difficult to trace operations across system |
| **Priority** | P2 |

### GAP-OBS-003: Health Check Depth

| Property | Value |
|----------|-------|
| **Question** | What does health() actually check? |
| **Missing Data** | Health check criteria, dependencies checked |
| **Where to Look** | health.py |
| **How to Measure** | Analyze health() implementation |
| **Impact** | False healthy status |
| **Priority** | P2 |

### GAP-OBS-004: Metrics Granularity

| Property | Value |
|----------|-------|
| **Question** | Are metrics per-session or global? |
| **Missing Data** | Per-session metrics, labels |
| **Where to Look** | metrics.py |
| **How to Measure** | Check for session labels in metrics |
| **Impact** | Cannot isolate problematic sessions |
| **Priority** | P3 |

---

## 6. Portability/Adapters Gaps

### GAP-PT-001: Multi-Agent Platform Support

| Property | Value |
|----------|-------|
| **Question** | How easily can we add new agent platforms? |
| **Missing Data** | Agent interface abstraction, platform adapters |
| **Where to Look** | Agent abstract class, agent_manager.py |
| **How to Measure** | Count TmuxAgent-specific references |
| **Impact** | Hard to add support for iTerm2, screen, etc. |
| **Priority** | P2 |

### GAP-PT-002: Database Backend Abstraction

| Property | Value |
|----------|-------|
| **Question** | Can we switch from SQLite to PostgreSQL? |
| **Missing Data** | Database adapter interface, SQL dialect abstraction |
| **Where to Look** | Repository implementations |
| **How to Measure** | Check for SQLite-specific SQL |
| **Impact** | Locked into SQLite |
| **Priority** | P3 |

---

## 7. Fork Generation Gaps

### GAP-FG-001: Fork Verification

| Property | Value |
|----------|-------|
| **Question** | How do we verify a generated fork is complete and valid? |
| **Missing Data** | Verification step, doctor command |
| **Where to Look** | fork-generate.sh |
| **How to Measure** | Check for verify subcommand or post-generation checks |
| **Impact** | Incomplete forks cause runtime failures |
| **Priority** | P1 |

### GAP-FG-002: Assumptions About Environment

| Property | Value |
|----------|-------|
| **Question** | What does fork-generate.sh assume exists? |
| **Missing Data** | Prerequisites documentation, validation |
| **Where to Look** | fork-generate.sh |
| **How to Measure** | Analyze script for implicit dependencies |
| **Impact** | Fork fails on different environments |
| **Priority** | P2 |

### GAP-FG-003: Coupling to Directory Structure

| Property | Value |
|----------|-------|
| **Question** | How tightly coupled is fork generation to .claude/.opencode structure? |
| **Missing Data** | Abstraction of agent directory structure |
| **Where to Look** | fork-generate.sh |
| **How to Measure** | Count hardcoded .claude references |
| **Impact** | Breaks if agent structure changes |
| **Priority** | P3 |

---

## 8. Decision Gaps Summary

| ID | Category | Question | Priority | Impact |
|----|----------|----------|----------|--------|
| GAP-TM-001 | tmux | Orphan session detection | P1 | Resource leaks |
| GAP-TM-002 | tmux | Session naming collision | P2 | Unpredictable behavior |
| GAP-TM-003 | tmux | Resource limits | P2 | System failure |
| GAP-WF-001 | Workflow | State schema versioning | P1 | Breaking changes |
| GAP-WF-002 | Workflow | State validation | P2 | Stale state |
| GAP-WF-003 | Workflow | Phase skip prevention | P1 | Unverified code |
| GAP-WF-004 | Workflow | Concurrent access | P2 | Corruption |
| GAP-HK-001 | Hooks | Criticality levels | P1 | Blocking failures |
| GAP-HK-002 | Hooks | Output schema | P2 | Parse errors |
| GAP-HK-003 | Hooks | Retry policy | P2 | Transient failures |
| GAP-HK-004 | Hooks | Execution order | P3 | Unexpected order |
| GAP-DB-001 | Database | Migration system | P1 | Manual migrations |
| GAP-DB-002 | Database | Idempotency | P1 | Duplicate ops |
| GAP-DB-003 | Database | Connection pooling | P2 | Exhaustion |
| GAP-DB-004 | Database | Backup/restore | P2 | Data loss |
| GAP-OBS-001 | Observability | Circuit breaker alerting | P1 | Silent failures |
| GAP-OBS-002 | Observability | Correlation IDs | P2 | Hard tracing |
| GAP-OBS-003 | Observability | Health check depth | P2 | False positives |
| GAP-OBS-004 | Observability | Metrics granularity | P3 | Isolation |
| GAP-PT-001 | Portability | Multi-platform support | P2 | Locked to tmux |
| GAP-PT-002 | Portability | Database backend | P3 | Locked to SQLite |
| GAP-FG-001 | Fork | Verification | P1 | Incomplete forks |
| GAP-FG-002 | Fork | Environment assumptions | P2 | Env failures |
| GAP-FG-003 | Fork | Directory coupling | P3 | Structure changes |

---

*Document generated by decision gaps audit - 2026-02-23*
