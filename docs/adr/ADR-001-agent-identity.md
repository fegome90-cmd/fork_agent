# ADR-001: Canonical Agent Identity for tmux_fork (Revision C)

| Field | Value |
|-------|-------|
| **Status** | Proposed |
| **Revision** | C (Post-Review Architecture) |
| **Date** | 2026-04-26 |
| **Commit SHA** | `3435d68f3873ab3c0ef5f5a45a5164a2b4c70e23` |
| **Decision Makers** | felipe_gonzalez |
| **Affected** | `src/domain/entities/agent_launch.py`, `src/application/services/agent_launch_lifecycle_service.py`, `src/application/services/memory/event_metadata.py`, migration 030 |

---

## 1. Context

tmux_fork is a multi-agent orchestrator that spawns sub-agents in tmux panes. It needs unambiguous agent identity for deduplication, delegation tracking, and post-mortem analysis. 

This Revision C refines the model by incorporating proven patterns from **Hermes Agent** and **OpenClaw**, while strictly enforcing the single-authority principle to avoid architectural drift.

---

## 2. External Patterns & Inspiration

### 2.1 Patterns Imported
- **From Hermes**:
    - **Robust Persistence**: SQLite WAL mode + application-level retry with jitter (20-150ms).
    - **Lineage Pattern**: Conceptual precedent for linking related execution units.
    - **UX Continuity**: Title/display naming patterns (e.g., `#2`, `#3`) for human readability.
- **From OpenClaw**:
    - **Scoped Isolation**: Agent-scoped state and session isolation principles.
    - **Namespacing**: Hierarchical key patterns (e.g., `agent:{role}:{uuid}`).
    - **Central Authority**: Gateway/Service pattern—clients (like the skill) request state changes; the service owns and validates them.

### 2.2 Exclusions (What NOT to import)
- **OpenClaw Platform Complexity**: No implementation of institutional identity, sandboxing, or full security delegates.
- **OpenClaw Transcript Authority**: Transcripts/JSONL files are artifacts/evidence, NOT identity authority.
- **Hermes Lineage Semantics**: Hermes `parent_session_id` means "compression continuity". In tmux_fork, `parent_launch_id` means "delegation causality" (Launch A triggered Launch B).

---

## 3. Decision: Single Identity Authority

**AgentLaunch.launch_id is the SOLE identity authority.** 

No agent-local or session-local identifier may become an identity authority. `tmux pane id`, `session key`, `display name`, `EventMetadata.agent_id`, and `output artifact` are references or evidence only.

### 3.1 Vocabulary & Normalization
| Term | Authority | Rule |
|------|-----------|------|
| **launch_id** | `AgentLaunch.launch_id` | UUID4 hex. The canonical identity. |
| **role** | `AgentLaunch.role` | Mandatory for new launches. |
| **display_name** | Computed Property | `{role}:{launch_id[:8]}`. UI/Log label ONLY. NEVER authority. |
| **agent_id** | `MemoryEventMetadata` | **MUST** store `launch_id`. Deprecate `session:window`. |
| **parent_launch_id**| `AgentLaunch` | Delegation causality (A → B). NOT compression lineage. |

### 3.2 Invariants
- **Role Invariant**: Required for all launches created post-migration 030. Legacy routes without explicit role MUST default to `poll-agent` during transition.
- **Cycle Detection**: `AgentLaunchLifecycleService` must reject any `parent_launch_id` that generates a cycle. Max depth: 16 generations.
- **Boundary Coupling (ADR-002)**: Skill-side spawning (`tmux-live`) MUST NOT bypass `AgentLaunchLifecycleService`. It must request/confirm lifecycle through the CLI/API boundary.

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
- [ ] **Boundary**: Verify `tmux-live` calls the lifecycle service and respects `decision=suppressed`.

---

## 7. What Changed (Revision B -> Revision C)

1. **External Patterns**: Added explicit section for Hermes/OpenClaw imported patterns and exclusions.
2. **Lineage Semantics**: Clarified `parent_launch_id` means delegation causality, not compression.
3. **Authority Hardening**: Explicitly demoted tmux panes, display names, and event IDs to "evidence/references" status.
4. **Boundary Integration**: Added explicit coupling rule with ADR-002 (Gateway-authority principle).
5. **Acceptance Criteria**: Refined boundary validation in the checklist.
