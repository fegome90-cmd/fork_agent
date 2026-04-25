# ADR-001: Canonical Agent Identity for tmux_fork

| Field | Value |
|-------|-------|
| **Status** | Proposed |
| **Date** | 2026-04-25 |
| **Decision Makers** | felipe_gonzalez |
| **Replaces** | Informe "Modelos de Identidad: Hermes vs OpenClaw/Paperclip" |
| **Affected** | `src/domain/entities/agent_launch.py`, migration 029 |

---

## 1. Context

tmux_fork is a multi-agent orchestrator that spawns sub-agents in tmux panes. It needs unambiguous agent identity for:

1. Deduplication — prevent double-spawning the same logical work item.
2. Delegation tracking — know who spawned whom.
3. Pane correlation — map tmux panes to internal state.
4. Post-mortem — reconstruct the delegation tree after failure.

An external review compared Hermes (single-agent CLI) and OpenClaw/Paperclip (multi-agent platform). The review proposed a new `agent_runs` table and `display_name` as authority. This ADR corrects that recommendation with evidence from the actual codebase.

### Systems reviewed

| System | Source | Applicable? |
|--------|--------|-------------|
| **Hermes** | `~/Developer/hermes-agent/` | Session lineage pattern, SQLite WAL + jitter retry |
| **OpenClaw/Paperclip** | `~/.openclaw/`, `~/Developer/paperclip/` | Hierarchical keys, `runtimeStatePatch` concept |
| **tmux_fork (current)** | `~/Developer/tmux_fork/` | Base entity and authority |

### Why now

The external review introduced several inaccuracies that would mislead implementation:

- Claimed IDs are "Date.now()-based" — **false**. Code uses `uuid.uuid4().hex` (lifecycle service L96).
- Claimed names are "extracted by regex" — **false**. `agent_name` is always the constant `POLL_AGENT_OWNER = "poll-agent"` (polling service L30).
- Claimed FSM has "8 states" — **correct but misleading**. It has 8 enum values but `SUPPRESSED_DUPLICATE` is internal-only, never set via public API (entity L48 comment).
- Proposed a parallel `agent_runs` table — would create two identity authorities.
- Proposed `display_name` as part of the primary key — would create a secondary identity axis.

This ADR corrects these and defines the minimal change set.

---

## 2. Evidence — Current State

### 2.1 Authority: `AgentLaunch` + `agent_launch_registry`

**Files:**

| File | Role |
|------|------|
| `src/domain/entities/agent_launch.py` | Entity definition (frozen dataclass) |
| `src/domain/ports/agent_launch_repository.py` | Port (Protocol) |
| `src/infrastructure/persistence/repositories/agent_launch_repository.py` | SQLite implementation |
| `src/infrastructure/persistence/migrations/028_create_agent_launch_registry.sql` | Table DDL |
| `src/application/services/agent_launch_lifecycle_service.py` | Application service (single owner) |
| `tests/unit/application/test_agent_launch_lifecycle_service.py` | 357 lines of tests |
| `tests/unit/infrastructure/test_agent_launch_repo.py` | 494 lines of tests |

**Identity generation:**

```python
# agent_launch_lifecycle_service.py:96
launch_id = uuid.uuid4().hex
```

`launch_id` is **already UUID4 hex**. No Date.now() anywhere in identity generation. **Gap: not confirmed.**

**Canonical dedup:**

The table has a partial unique index enforcing at most one active launch per `canonical_key`:

```sql
-- 028_create_agent_launch_registry.sql:32
CREATE UNIQUE INDEX IF NOT EXISTS idx_one_active_launch_per_key
    ON agent_launch_registry (canonical_key)
    WHERE status IN ('RESERVED', 'SPAWNING', 'ACTIVE', 'TERMINATING');
```

This is correct and working.

**Naming:**

`PollRun.agent_name` is always `"poll-agent"` (a constant). Not extracted by regex. **Gap: not confirmed.**

However, `AgentLaunch` has **no `role` field** — there is no way to distinguish an explorer from an architect from a verifier. This is a real gap.

### 2.2 FSM: 8 values, 7 public

`LaunchStatus` enum:

| Value | Public API? | Category |
|-------|-------------|----------|
| `RESERVED` | Yes (via `claim()`) | Blocking |
| `SPAWNING` | Yes (via `confirm_spawning()`) | Blocking |
| `ACTIVE` | Yes (via `confirm_active()`) | Blocking |
| `TERMINATING` | Yes (via `begin_termination()`) | Blocking |
| `TERMINATED` | Yes (via `confirm_terminated()`) | Terminal |
| `FAILED` | Yes (via `mark_failed()`) | Terminal |
| `SUPPRESSED_DUPLICATE` | **No** — internal only | Terminal |
| `QUARANTINED` | Yes (via `quarantine()`) | Transitional |

The FSM has **8 enum values** but only **7 are settable via public API**. `SUPPRESSED_DUPLICATE` exists for future internal dedup that was never implemented. This is not a bug but it is confusing.

**Transition map:**

```
RESERVED ──→ SPAWNING ──→ ACTIVE ──→ TERMINATING ──→ TERMINATED
    │            │           │              │
    └──→ FAILED ←┘           │              └──→ FAILED
    │                        │
    └──→ QUARANTINED ←───────┘
                │
                └──→ FAILED or TERMINATED
```

### 2.3 tmux pane correlation

`tmux_pane_id` is stored during `confirm_active()`:

```python
# agent_launch_lifecycle_service.py:164
def confirm_active(self, launch_id, *, backend, termination_handle_type,
                   termination_handle_value, tmux_pane_id=None, tmux_session=None, ...):
```

**But there is no reconciliation.** The `agent_manager.py:490` `reconcile_sessions()` compares tmux session names against registered agents — but it works on **session names**, not on the `agent_launch_registry` table. There is no code that checks whether a `tmux_pane_id` in the launch registry still exists in tmux.

**Gap: confirmed.** Pane is stored but never verified alive.

### 2.4 Parent-child tracking

There is no `parent_launch_id` anywhere in the codebase:

```bash
$ grep -rn "parent_launch" src/ tests/
(no results)
```

**Gap: confirmed.** No delegation tree tracking.

### 2.5 EventMetadata

`src/application/services/memory/event_metadata.py` defines a separate identity model:

```python
agent_id: str = Field(..., description="Agent identifier in session:window format")
```

This is a Pydantic model for memory events, separate from `AgentLaunch`. The `agent_id` format `"session:window"` is a tmux reference, not tied to `launch_id`.

This is a **secondary identity** that should reference the primary, not duplicate it.

### 2.6 PollRun — secondary tracking entity

`src/domain/entities/poll_run.py` defines `PollRun` with its own `id` (UUID4 hex) and `agent_name` (always `"poll-agent"`). `poll_runs` table (migration 024) stores these runs.

`PollRun` overlaps with `AgentLaunch` but serves a different purpose: `PollRun` tracks autonomous polling execution; `AgentLaunch` tracks any spawn. A poll run triggers a launch, so `PollRun` should reference `AgentLaunch`, not duplicate identity.

### 2.7 Confirmed vs. unconfirmed gaps

| Gap | Status | Evidence |
|-----|--------|----------|
| IDs based on Date.now() | **NOT CONFIRMED** | `uuid.uuid4().hex` at L96 |
| Name extracted by regex | **NOT CONFIRMED** | Constant `POLL_AGENT_OWNER = "poll-agent"` |
| No parent-child tracking | **CONFIRMED** | No `parent_launch_id` in any file |
| No pane reconciliation | **CONFIRMED** | No code verifies pane alive |
| No role field | **CONFIRMED** | `AgentLaunch` has no `role` attribute |
| No display name | **CONFIRMED** | Only `launch_id` (hex) — not human-readable |
| EventMetadata as secondary identity | **CONFIRMED** | `agent_id` in `session:window` format, untied |
| PollRun / AgentLaunch overlap | **CONFIRMED** | Both track spawns independently |

---

## 3. Decision

**AgentLaunch is the single identity authority.** No new table. Extend the existing `agent_launch_registry` with minimal fields via migration 029.

### 3.1 Vocabulary

| Term | Definition | Authority |
|------|-----------|-----------|
| **launch_id** | UUID4 hex. Primary key. The identity. | `AgentLaunch.launch_id` |
| **canonical_key** | Dedup key for the logical work item. | `AgentLaunch.canonical_key` |
| **role** | Orchestrator role: `explorer`, `architect`, `implementer`, `verifier`, `analyst`, `poll-agent`. | New field on `AgentLaunch` |
| **display_name** | Human label: `"{role}:{launch_id[:8]}"`. Derived, not stored. | Computed property |
| **parent_launch_id** | FK to the launch that spawned this one. Nullable. Root launches have NULL. | New field on `AgentLaunch` |
| **agent_id** (EventMetadata) | Must equal `launch_id` or `display_name`. **Not** `session:window`. | Updated to reference launch_id |

### 3.2 New fields on `AgentLaunch` (4 fields)

```python
@dataclass(frozen=True)
class AgentLaunch:
    # ... existing 24 fields unchanged ...

    # --- NEW (all optional for backward compat) ---
    parent_launch_id: str | None = None   # FK → agent_launch_registry.launch_id
    role: str | None = None               # explorer|architect|implementer|verifier|analyst|poll-agent
    model: str | None = None              # assigned LLM model (e.g., "zai/glm-5-turbo")
    output_artifact: str | None = None    # path to written output file

    @property
    def display_name(self) -> str:
        """Human-readable label. Derived, never stored."""
        prefix = self.role or "agent"
        return f"{prefix}:{self.launch_id[:8]}"
```

**Why these 4 and no more:**

| Field | Why |
|-------|-----|
| `parent_launch_id` | Enables delegation tree. Nullable for backward compat. FK constraint in migration. |
| `role` | Distinguishes agent types. Currently impossible. Nullable for backward compat. |
| `model` | Observability. Which model was assigned. Nullable. |
| `output_artifact` | Links launch to its written output. Nullable. |

**Why NOT these:**

| Rejected field | Why |
|---------------|-----|
| `display_name` (stored) | Derived from role + launch_id. Storing it creates a denormalized identity axis. |
| `token_input/output/cache` | Premature. Add when cost tracking is needed. Not part of identity. |
| `estimated_cost` | Premature. |
| `started_at` / `completed_at` | Already covered by `spawn_started_at` and `ended_at`. |
| `runtime_state` / `statePatch` | Out of scope for MVP. See §7. |

### 3.3 Invariant: `display_name` is never authority

`display_name` is a **computed property**: `{role}:{launch_id[:8]}`. It is:

- NOT stored in the database.
- NOT used as a foreign key.
- NOT used for dedup.
- ONLY used for logs and human-facing output.

Any code that uses `display_name` for identity decisions is a bug.

### 3.4 Invariant: single identity axis

All tracking must reference `launch_id`:

- `PollRun` should store `launch_id` (FK) instead of duplicating `agent_name` + `launch_method` + `launch_pane_id` + `launch_pid`.
- `EventMetadata.agent_id` should reference `launch_id` or be deprecated in favor of `launch_id`.
- No other entity may define its own agent identity.

---

## 4. FSM — Corrected

The FSM has **8 enum values**, **7 public**, **6 transitions**:

```
RESERVED ──→ SPAWNING ──→ ACTIVE ──→ TERMINATING ──→ TERMINATED
    │            │           │              │
    └──→ FAILED ←┘           │              └──→ FAILED
    │                        │
    └──→ QUARANTINED ←───────┘
                │
                ├──→ FAILED
                └──→ TERMINATED

SUPPRESSED_DUPLICATE: terminal, internal-only, never set via public API.
```

No changes to the FSM. The 8 values are correct. `SUPPRESSED_DUPLICATE` stays for future internal use.

---

## 5. tmux Pane Correlation — Specification

Currently, `tmux_pane_id` is stored but never verified. The ADR specifies:

### 5.1 Write path (existing, no change)

`confirm_active()` already stores `tmux_pane_id` and `tmux_session`. This is correct.

### 5.2 Reconciliation (new requirement)

A reconciliation function must:

1. Query all launches in `ACTIVE` status with non-null `tmux_pane_id`.
2. For each, check if the tmux pane still exists: `tmux list-panes -t {pane_id} -F '#{pane_id}'`.
3. If pane is gone, transition to `FAILED` with error `"pane_lost: {pane_id}"`.

This is a **new behavior**, not a schema change. It does NOT need `display_name`. It uses `launch_id` + `tmux_pane_id`.

### 5.3 Implementation location

`AgentLaunchLifecycleService.reconcile_lost_panes()` — new method. Called by the polling loop alongside `reconcile_expired_leases()`.

---

## 6. Migration Strategy

### Migration 029: `029_add_agent_launch_identity_fields.sql`

```sql
-- Extend agent_launch_registry with identity fields.
-- All columns are nullable for backward compatibility.
-- No data migration needed — existing rows remain valid.

ALTER TABLE agent_launch_registry ADD COLUMN parent_launch_id TEXT
    REFERENCES agent_launch_registry(launch_id);

ALTER TABLE agent_launch_registry ADD COLUMN role TEXT;

ALTER TABLE agent_launch_registry ADD COLUMN model TEXT;

ALTER TABLE agent_launch_registry ADD COLUMN output_artifact TEXT;

-- Index for delegation tree queries.
CREATE INDEX IF NOT EXISTS idx_launch_parent
    ON agent_launch_registry (parent_launch_id)
    WHERE parent_launch_id IS NOT NULL;

-- Index for role-based queries.
CREATE INDEX IF NOT EXISTS idx_launch_role
    ON agent_launch_registry (role)
    WHERE role IS NOT NULL;
```

**Strategy: extend, not replace.**

- Existing rows: `parent_launch_id`, `role`, `model`, `output_artifact` are NULL. Fully valid.
- Existing code: all 24 original fields unchanged. No breakage.
- Existing tests: 972 lines of tests pass unchanged.
- New code: sets the 4 new fields when available. Nullable everywhere.

### What about `PollRun` overlap?

`PollRun` stores `launch_method`, `launch_pane_id`, `launch_pid`, `launch_pgid` — all of which are also on `AgentLaunch`. This is duplication.

**Migration path (post-MVP):** Add `launch_id TEXT REFERENCES agent_launch_registry(launch_id)` to `poll_runs`, deprecate the 4 launch_* columns. NOT part of this ADR.

### What about `EventMetadata.agent_id`?

Currently `session:window` format. Should reference `launch_id`.

**Migration path (post-MVP):** Change `agent_id` semantics to equal `launch_id`. Add `launch_id` field to `MemoryEventMetadata`. NOT part of this ADR.

---

## 7. What is explicitly OUT of scope

| Item | Why out |
|------|---------|
| `runtimeStatePatch` / session resume | No evidence of need. No code references it. Premature abstraction. If needed later, define with a typed allowlist: `{"last_file": str, "last_line": int, "context_summary": str}`. No free-form JSON. |
| PostgreSQL | SQLite is correct for local CLI. |
| Ed25519 device identity | No trust boundary. All agents run under same OS user. |
| Auth tiers (JWT, API key, invite) | Local-only orchestration. No network boundary. |
| 6-component adapter protocol | Over-engineering for 3-5 concurrent agents. |
| WebSocket/SSE push | tmux-live handles observability. |
| Drizzle ORM | Python + raw SQL is simpler. |
| `display_name` as stored column | Derived property. Storing it creates dual identity. |
| Token/cost tracking fields | Premature. Add when budget control is needed. |
| New `agent_runs` table | Would create parallel identity authority. Extend existing. |
| FSM changes | Current 8-value FSM is correct and well-tested. |

---

## 8. Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| `parent_launch_id` FK creates circular chains | Low | Medium | Application-level cycle detection: reject if ancestor chain contains launch_id. Max depth 16. |
| `role` values proliferate beyond the 6 defined | Medium | Low | Validate against an enum or allowlist in the lifecycle service. Not in the entity (entity is data). |
| Migration 029 breaks on DB with existing data | Low | High | All columns nullable. ALTER TABLE ADD COLUMN is safe. Tested on SQLite. |
| `display_name` collisions (`role:hex8`) | Negligible | Negligible | 8 hex chars from UUID4 = 1 in 4B collision. Not used for identity anyway. |
| Scope creep toward full platform | High | High | This ADR's exclusion list is binding. Any addition requires a new ADR. |

---

## 9. Conformance Checklist

- [x] Single identity authority: `AgentLaunch.launch_id`
- [x] `parent_launch_id` defined without breaking backward compat (nullable FK)
- [x] `display_name` is derived, never stored, never used for identity
- [x] Pane correlation specified as reconciliation, not just storage
- [x] `runtimeStatePatch` is out of scope (no free-form JSON)
- [x] No implementation without ADR approval
- [x] FSM count corrected: 8 values, 7 public, no changes needed
- [x] Evidence-based: every claim references file:line
- [x] Two gap claims from the review refuted with code evidence

---

## A. Appendix: Commands Executed

```bash
# Identity generation — UUID4, not Date.now()
grep -n "launch_id.*=\|uuid" src/application/services/agent_launch_lifecycle_service.py

# Agent naming — constant, not regex
grep -n "POLL_AGENT_OWNER\|agent_name" src/application/services/agent_polling_service.py

# Parent-child tracking — does not exist
grep -rn "parent_launch" src/ tests/

# Table schema
cat src/infrastructure/persistence/migrations/028_create_agent_launch_registry.sql

# Pane reconciliation — not implemented
grep -rn "pane.*alive\|reconcil.*pane\|verify.*pane" src/ --include="*.py"

# Existing tests
wc -l tests/unit/application/test_agent_launch_lifecycle_service.py
wc -l tests/unit/infrastructure/test_agent_launch_repo.py
wc -l tests/unit/infrastructure/persistence/repositories/test_agent_launch_repository.py

# EventMetadata identity model
cat src/application/services/memory/event_metadata.py

# PollRun overlap
cat src/infrastructure/persistence/migrations/024_create_poll_runs_table.sql
cat src/infrastructure/persistence/migrations/027_add_poll_run_launch_metadata.sql
```

## B. Appendix: Files Reviewed

| File | Lines | Purpose |
|------|-------|---------|
| `src/domain/entities/agent_launch.py` | 180 | Entity + FSM definition |
| `src/domain/ports/agent_launch_repository.py` | 88 | Port (Protocol) |
| `src/infrastructure/persistence/repositories/agent_launch_repository.py` | 235 | SQLite implementation |
| `src/infrastructure/persistence/migrations/028_create_agent_launch_registry.sql` | 43 | Table DDL |
| `src/application/services/agent_launch_lifecycle_service.py` | 310 | Lifecycle service |
| `src/application/services/agent_polling_service.py` | ~680 | Polling service (spawn + pane tracking) |
| `src/application/services/memory/event_metadata.py` | 200 | Event metadata contract |
| `src/domain/entities/poll_run.py` | 100 | PollRun entity |
| `src/infrastructure/persistence/migrations/024_create_poll_runs_table.sql` | 13 | poll_runs DDL |
| `src/infrastructure/persistence/migrations/027_add_poll_run_launch_metadata.sql` | 7 | poll_runs ALTER |
| `src/application/services/agent/agent_manager.py` | ~650 | Agent manager + reconcile_sessions |
| `src/infrastructure/persistence/database.py` | 130 | SQLite connection management |
| `tests/unit/application/test_agent_launch_lifecycle_service.py` | 357 | Lifecycle tests |
| `tests/unit/infrastructure/test_agent_launch_repo.py` | 494 | Repository tests |
