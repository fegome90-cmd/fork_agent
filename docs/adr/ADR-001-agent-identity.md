# ADR-001: Canonical Agent Identity for tmux_fork (Revision B)

| Field | Value |
|-------|-------|
| **Status** | Proposed |
| **Revision** | B (Final for Implementation) |
| **Date** | 2026-04-25 |
| **Commit SHA** | `3435d68f3873ab3c0ef5f5a45a5164a2b4c70e23` |
| **Decision Makers** | felipe_gonzalez |
| **Affected** | `src/domain/entities/agent_launch.py`, `src/application/services/agent_launch_lifecycle_service.py`, `src/application/services/memory/event_metadata.py`, migration 030 |

---

## 1. Context

tmux_fork is a multi-agent orchestrator that spawns sub-agents in tmux panes. It needs unambiguous agent identity for deduplication, delegation tracking, and post-mortem analysis.

This Revision B refines the identity authority, enforces stricter invariants for `role` and `EventMetadata`, and specifies authoritative reconciliation for lost tmux panes.

---

## 2. Evidence — Snapshot (`3435d68`)

### 2.1 Current Authority
- **Authority**: `agent_launch_registry` table (Migration 028).
- **Identity Gen**: `uuid.uuid4().hex` in `agent_launch_lifecycle_service.py:96`.
- **Latest Migration**: `029_add_poll_run_canonical_key.sql`.
- **Test Baseline**: 40/40 tests passing (Unit/Repo).

### 2.2 Confirmed Gaps (Internal Audit)
- No `parent_launch_id` (Causal tracking).
- No `role` field (Identity typing).
- No pane reconciliation (Runtime state drift).
- `EventMetadata` uses secondary identity (`session:window`).

---

## 3. Decision

**AgentLaunch.launch_id is the SOLE identity authority.**

### 3.1 Vocabulary & Normalization
| Term | Authority | Rule |
|------|-----------|------|
| **launch_id** | `AgentLaunch.launch_id` | UUID4 hex. The canonical identity. |
| **role** | `AgentLaunch.role` | Mandatory for new launches. Enum-like string. |
| **display_name** | Computed Property | `{role}:{launch_id[:8]}`. **UI/Log only.** NEVER authority. |
| **agent_id** | `MemoryEventMetadata` | **MUST** store `launch_id`. Deprecate `session:window`. |

### 3.2 Role Invariant
- **Legacy Rows**: NULL allowed.
- **New Launches**: `role` is **REQUIRED** at `request_launch()`.
- **Mapping**: Legacy paths without explicit role MUST default to `poll-agent` during transition.

### 3.3 Cycle Detection (Acceptance Criterion)
- `parent_launch_id` must reference a valid `launch_id` in the registry.
- `AgentLaunchLifecycleService` must reject any `parent_launch_id` that generates a cycle.
- **Max Depth**: 16 generations.

---

## 4. Execution Rules — Pane Reconciliation

The system must distinguish between "Confirmed Failure" and "Ambiguous Disappearance".

1. **QUARANTINED (reason="pane_lost")**: Transition here if `status=ACTIVE` and the tmux pane is missing, but no terminal evidence (exit code, artifact) exists.
2. **FAILED**: Transition here ONLY if there is clear evidence of failure (crash logs, non-zero exit code).
3. **TERMINATED**: Transition here ONLY if there is evidence of successful completion.

Reconciliation is triggered by `AgentLaunchLifecycleService.reconcile_lost_panes()`.

---

## 5. Migration Strategy (030)

```sql
-- 030_add_agent_launch_identity_fields.sql
ALTER TABLE agent_launch_registry ADD COLUMN parent_launch_id TEXT 
    REFERENCES agent_launch_registry(launch_id);
ALTER TABLE agent_launch_registry ADD COLUMN role TEXT;
ALTER TABLE agent_launch_registry ADD COLUMN model TEXT;
ALTER TABLE agent_launch_registry ADD COLUMN output_artifact TEXT;

CREATE INDEX IF NOT EXISTS idx_launch_parent ON agent_launch_registry (parent_launch_id);
CREATE INDEX IF NOT EXISTS idx_launch_role ON agent_launch_registry (role);
```

---

## 6. Test Acceptance List

- [ ] **Authority**: Verify `launch_id` remains the primary key and sole authority.
- [ ] **Persistence**: Verify `display_name` is **NOT** stored in the database.
- [ ] **Identity Invariant**: Verify `EventMetadata` rejects `display_name` and requires `launch_id`.
- [ ] **Role Validation**: 
    - Verify legacy rows with `role=NULL` load successfully.
    - Verify `request_launch()` fails if `role` is missing for new records.
- [ ] **Delegation**:
    - Verify `parent_launch_id` correctly links child to parent.
    - Verify cycles are detected and rejected (Max depth 16).
    - Verify unknown `parent_launch_id` is rejected.
- [ ] **Reconciliation**:
    - Verify `ACTIVE` launch with missing pane moves to `QUARANTINED` with `pane_lost`.
    - Verify `FAILED` status is not reached without failure evidence.

---

## 7. What Changed (Revision A -> Revision B)

1. **EventMetadata Identity**: Hardened `agent_id` to be strictly `launch_id`. Rev A allowed `display_name` as identity; Rev B demotes it to visual-only.
2. **Role Requirement**: Elevated `role` from optional to mandatory for new launches.
3. **Reconciliation Logic**: Changed missing pane transition from `FAILED` (Rev A) to `QUARANTINED` (Rev B) to prevent false failure reports.
4. **Cycle Detection**: Elevated from a risk to a mandatory implementation criterion with defined depth.
5. **Acceptance List**: Added a concrete, testable checklist for implementation validation.
6. **Evidence**: Anchored to commit `3435d68` and latest migration `029`.
