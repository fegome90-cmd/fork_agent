# Authority-Flow Audit: Governance Integration Plan

> **Subject:** `docs/research/governance/governance-integration-research.md`
> **Mode:** change-audit (proposed integration — not yet implemented)
> **Date:** 2026-04-23
> **Auditor:** authority-flow-audit v2.1
> **Confidence baseline:** medium-high (docs + skill sources traced; no running code to grep)

---

## Executive Summary

The governance integration plan proposes a 4-layer pipeline: **CLOOP → anchor_dope → SDD → tmux_fork**. The design is architecturally sound in principle — each layer feeds the next — but the audit reveals **11 findings**: 2 CRITICAL, 3 HIGH, 4 MEDIUM, 2 LOW. The dominant risk pattern is **competing pipelines for the same artifact type**, with anchor_dope and SDD both claiming authority over plan decomposition, and CLOOP competing with tmux_fork's existing Phase 0/1 for the clarification + planning surface.

The most dangerous finding is a **double-writer on ANCHOR.md**: both the orchestrator (via plan generation) and anchor_dope (via sprint pack scaffolding) can write to the same file without coordination.

---

## Surface Inventory (Tier 1)

| # | Surface | Type | Writes To | Inbound | Outbound |
|---|---------|------|-----------|---------|----------|
| 1 | CLOOP (plan-architect skill) | skill | Goal statement, architecture diagram, phase breakdown, risk register | User request | anchor_dope templates |
| 2 | anchor_dope (CLI scaffolding) | script | ANCHOR.md, SKILL.md, AGENTS.md, PRIME.md | CLOOP output | SDD sdd-propose |
| 3 | SDD sdd-propose | skill | Change proposal (engram/openspec) | ANCHOR.md scope | sdd-spec, sdd-design |
| 4 | SDD sdd-spec + sdd-design | skill | Delta specs, design doc (engram/openspec) | sdd-propose | sdd-tasks |
| 5 | SDD sdd-tasks | skill | Task breakdown (engram) | sdd-spec/design | tmux_fork Phase 3 |
| 6 | SDD sdd-gate-skill | skill | Quality gate verdict | specs/design/tasks | — |
| 7 | SDD sdd-verify | skill | Verification results | specs/design + implementation | anchor_dope doctor |
| 8 | SDD sdd-archive | skill | Main spec sync, archive marker | delta specs | engram/openspec |
| 9 | tmux_fork Phase 0 (Clarify) | protocol | Questions → user answers | User request | Phase 1 |
| 10 | tmux_fork Phase 1 (Plan) | protocol | PLAN.md, subtask decomposition | Phase 0 output | Phase 1.5 |
| 11 | tmux_fork Phase 1.5 (Plan Gate) | protocol | Plan approval/rejection | PLAN.md | Phase 1.6 |
| 12 | tmux_fork Phase 1.6 (Pre-flight) | protocol | Pre-flight verdict | init.yaml, skill-resolver | Phase 2 |
| 13 | tmux_fork Phase 3 (Spawn) | protocol | Sub-agent prompts, /tmp/fork-*.md | PLAN.md + tasks | Phase 4 |
| 14 | `memory workflow outline` | CLI | Workflow plan in memory DB | User task | workflow execute |
| 15 | anchor_dope `doctor.sh` | script | Structural validation report | ANCHOR.md + SKILL.md | — |
| 16 | anchor_dope `new_sprint_pack.sh` | script | Full sprint pack directory | CLOOP output | — |

---

## Findings

### Finding 1: Double Writer on ANCHOR.md — Orchestrator vs anchor_dope
- **Severity**: CRITICAL
- **Type**: double-writer
- **Components**: tmux_fork Phase 1 (Plan), anchor_dope sprint pack scaffolding
- **Description**: Both the tmux_fork orchestrator (Phase 1: Plan) and anchor_dope (`new_sprint_pack.sh`) can write to ANCHOR.md. The orchestrator produces PLAN.md as its canonical plan artifact (see protocol.md Phase 1 step 7, phase-common.md §H). anchor_dope produces ANCHOR.md as its SSOT sprint document. The integration plan proposes that CLOOP output feeds anchor_dope templates which generate ANCHOR.md, but also proposes that CLOOP Layout/Operate enriches tmux_fork Phase 1. This means two surfaces — the orchestrator's plan generation and anchor_dope's scaffolding — both claim authority over the same conceptual artifact (the plan), and could both write to overlapping files.
  - **Evidence**: governance doc §5.2 shows contract "CLOOP output → anchor.md template vars". Protocol.md Phase 1 produces PLAN.md. Section §5.1 flow shows anchor_dope running inside Phase 1. Both operate in the same phase on overlapping content.
  - **Confidence**: high
- **Recommendation**: Designate ONE writer. Either: (a) anchor_dope produces ANCHOR.md, and the orchestrator reads it (never writes), or (b) the orchestrator produces PLAN.md, and anchor_dope consumes it as input (never writes to the same directory). Add a coordination gate: "if ANCHOR.md exists, Phase 1 skips plan generation and reads it."

### Finding 2: Competing Pipeline — CLOOP Clarify vs tmux_fork Phase 0
- **Severity**: HIGH
- **Type**: competing-pipeline
- **Components**: CLOOP Clarify (plan-architect), tmux_fork Phase 0 (Clarify)
- **Description**: The integration plan explicitly states CLOOP Clarify should **REPLACE** tmux_fork Phase 0 (§2 table: "Reemplazar — CLOOP es más riguroso"). However, the protocol already has Phase 0 with its own behavior (2-3 targeted questions, max 6 rounds, skip when unambiguous). If CLOOP is installed, which code path runs? The doc says "replace" but the protocol.md text remains unchanged. No mechanism ensures one wins. A user with both skills active gets two clarification behaviors with no arbiter.
  - **Evidence**: §2 mapping table: "CLOOP → Phase 0 — Reemplazar". §5.1 flow: "Phase 0: CLOOP Clarify". But protocol.md Phase 0 still describes the original behavior.
  - **Confidence**: high
- **Recommendation**: Modify protocol.md Phase 0 to dispatch: "If plan-architect skill is available, delegate to CLOOP Clarify. Otherwise, use inline clarification." Make the protocol the arbiter, not the skill. Delete the competing Phase 0 text.

### Finding 3: Competing Pipeline — CLOOP Layout/Operate vs tmux_fork Phase 1
- **Severity**: HIGH
- **Type**: competing-pipeline
- **Components**: CLOOP Layout + Operate (plan-architect), tmux_fork Phase 1 (Plan)
- **Description**: The plan states CLOOP Layout "enriches" Phase 1 and CLOOP Operate also "enriches" Phase 1. This is ambiguous enrichment: two separate CLOOP phases feed into one protocol phase. The output of CLOOP Layout (architecture diagram, interfaces, checklist) and CLOOP Operate (phases, dependencies, order) both map to Phase 1's decomposition step. If CLOOP produces a different decomposition structure than the protocol expects (subtasks with roles + acceptance criteria), Phase 1's downstream consumers (Phase 3 Spawn, Phase 5.5 Validate) will receive malformed input.
  - **Evidence**: §2 mapping: Layout → Phase 1 "Enriquecer", Operate → Phase 1 "Enriquecer". Protocol.md Phase 1 steps 2-6 define specific decomposition structure.
  - **Confidence**: high
- **Recommendation**: Define a transformation layer: CLOOP Layout + Operate → normalize to Phase 1's expected schema (subtasks, roles, acceptance criteria). Either the plan-architect skill or a bridge script performs this normalization. Phase 1 must receive data in its expected format regardless of upstream source.

### Finding 4: Competing Pipeline — `memory workflow outline` vs SDD propose+spec+design+tasks
- **Severity**: HIGH
- **Type**: competing-pipeline
- **Components**: `memory workflow outline` (CLI), SDD sdd-propose/spec/design/tasks
- **Description**: The doc acknowledges this gap (§4): `memory workflow outline` combines propose + spec + design + tasks into one step, while SDD separates them into 4 distinct phases with separate persistence. The integration plan does not resolve this — Open Question #5 asks "¿memory workflow outline se reemplaza por CLOOP o conviven?" without an answer. If both are active, the user gets two decomposition pipelines that produce different artifact shapes (one flat, one structured into specs/design/tasks).
  - **Evidence**: §4 "Flujo existente en memory CLI" table shows the gap. §7 Open Questions Q5.
  - **Confidence**: high
- **Recommendation**: Decide explicitly. Recommended: deprecate `memory workflow outline` for SDD-aware projects, and make `sdd-propose` the canonical decomposition entry point. Keep `memory workflow outline` as a fast-path for non-SDD projects (simple tasks that don't need spec/design separation).

### Finding 5: False SSOT — anchor_dope Conflict Resolution Rule #1
- **Severity**: MEDIUM
- **Type**: false-ssot
- **Components**: anchor_dope, ANCHOR.md
- **Description**: anchor_dope declares "anchor.md gana sobre cualquier otro documento — sin excepciones" (§3, rule 1). But ANCHOR.md doesn't exist yet — the scripts that generate it (`new_sprint_pack.sh`) don't exist on disk (§3 Gaps). An SSOT that doesn't exist cannot be authoritative. Additionally, if the orchestrator produces PLAN.md (which it does today, per protocol §H), and ANCHOR.md is declared supreme over "any other document," then PLAN.md is implicitly subordinate to a file that doesn't exist. This creates an authority vacuum masked by a strong declaration.
  - **Evidence**: §3 "Gaps actuales: new_sprint_pack.sh y doctor.sh están referenciados pero no existen en disco". §3 rule 1: "anchor.md gana sobre cualquier otro documento — sin excepciones".
  - **Confidence**: high
- **Recommendation**: Either implement the missing scripts before declaring ANCHOR.md as SSOT, or qualify the rule: "When ANCHOR.md exists, it takes precedence." The authority chain should be: PLAN.md is SSOT when anchor_dope is not active; ANCHOR.md is SSOT when anchor_dope is active.

### Finding 6: Competing Pipeline — anchor_dope 4 Gates vs tmux_fork Pre-flight
- **Severity**: MEDIUM
- **Type**: competing-pipeline
- **Components**: anchor_dope 4 pre-flight gates, tmux_fork Phase 1.6 (Pre-flight)
- **Description**: anchor_dope defines 4 gates (Context, Phase, Surface, Clean State). tmux_fork Phase 1.6 defines its own pre-flight checks (Acceptance criteria, Role+artifact, TDD flag, fork init, Skill injection, Trifecta daemon). The integration plan proposes CLOOP Reflect + anchor_dope Gates feed into Phase 1.5, then Phase 1.6 adds CLOOP Observe. This creates two separate gate stages with different checks but no defined merge. A task could pass anchor_dope gates but fail Phase 1.6, or vice versa, with no clear rule for which gate has veto power.
  - **Evidence**: §5.1 flow shows "Phase 1.5: CLOOP Reflect + anchor_dope Gates" then "Phase 1.6: Pre-flight + CLOOP Observe". Two consecutive gate stages.
  - **Confidence**: medium
- **Recommendation**: Merge into a single gate phase. Define: anchor_dope gates are prerequisites (they validate context awareness), tmux_fork pre-flight checks are operational (they validate infrastructure readiness). Run anchor_dope gates first (they're cheaper), then tmux_fork pre-flight. Either set can veto execution.

### Finding 7: Competing Pipeline — SDD sdd-gate-skill vs tmux_fork Phase 1.5 (Plan Gate)
- **Severity**: MEDIUM
- **Type**: competing-pipeline
- **Components**: SDD sdd-gate-skill, tmux_fork Phase 1.5 (Plan Gate)
- **Description**: The plan proposes sdd-gate-skill as a quality check at Phase 1.5 (§4 mapping: "Phase 1.5: Plan Gate → sdd-gate-skill agrega quality check de specs"). But Phase 1.5 already has a purpose: human plan approval. The sdd-gate-skill is an automated quality check. If sdd-gate returns FAIL but the human approves, which wins? If the human denies but sdd-gate returns PASS, does the plan proceed? No arbiter is defined.
  - **Evidence**: §4 mapping table. Protocol.md Phase 1.5: "Human Approval".
  - **Confidence**: medium
- **Recommendation**: Define execution order: sdd-gate-skill runs BEFORE human review. If sdd-gate FAIL → auto-reject (human never sees it). If sdd-gate PASS/PASS-WITH-WARNINGS → forward to human for approval. Human has final veto. This prevents humans from approving plans that fail automated quality checks.

### Finding 8: Bottleneck — SDD Persistence Mode Fragmentation
- **Severity**: MEDIUM
- **Type**: bottleneck
- **Components**: SDD skills (11 total), engram, openspec, memory DB
- **Description**: SDD skills support 4 persistence modes (engram, openspec, hybrid, none) determined at `sdd-init` time. The integration plan doesn't specify which mode the governance pipeline uses. If different projects choose different modes, the orchestrator must handle all 4 modes when reading SDD artifacts in Phase 5 (Consolidate) and Phase 5.5 (Validate). This creates a compatibility matrix explosion: each phase must support reading from engram, openspec, hybrid, or memory DB.
  - **Evidence**: §4: "Persistencia: engram/openspec/hybrid/none" per skill. §7 Open Question Q2: "¿SDD persistence mode default: engram o hybrid?"
  - **Confidence**: medium
- **Recommendation**: Pin the governance pipeline to a single persistence mode. Recommended: `hybrid` (engram for exploration/proposals, openspec for specs/design). Document this as a governance constraint, not a per-project choice. The orchestrator only needs to support one read path.

### Finding 9: Authority Vacuum — anchor_dope Missing Scripts
- **Severity**: MEDIUM
- **Type**: false-ssot
- **Components**: anchor_dope (`new_sprint_pack.sh`, `doctor.sh`)
- **Description**: The governance design depends on anchor_dope scripts that don't exist (§3 Gaps). `new_sprint_pack.sh` is the entry point for generating the sprint pack (ANCHOR.md, SKILL.md, AGENTS.md, PRIME.md). `doctor.sh` is the validation tool referenced in Phase 5.5. Without these scripts, the entire anchor_dope layer is vapor — it appears in the architecture diagram and contracts table but cannot execute. The integration plan treats anchor_dope as an active component when it's actually a design-only component.
  - **Evidence**: §3: "new_sprint_pack.sh y doctor.sh están referenciados pero no existen en disco". §5.2 contracts: "CLOOP output → anchor.md template vars".
  - **Confidence**: high
- **Recommendation**: Block P1 deliverables on anchor_dope script implementation. Remove anchor_dope from the integration flow until scripts exist, or implement them as part of the P1 deliverable. The audit considers this a prerequisite, not a parallel track.

### Finding 10: Competing Pipeline — SDD sdd-verify vs tmux_fork Phase 5.5 Validate
- **Severity**: LOW
- **Type**: competing-pipeline
- **Components**: SDD sdd-verify, tmux_fork Phase 5.5 (Validate)
- **Description**: The integration proposes sdd-verify as an additional verification layer at Phase 5.5. But Phase 5.5 already has a full validation protocol (Spec Compliance, TDD Compliance, Verifier Check script). Adding sdd-verify creates a second verification pipeline. The doc says "sdd-verify como verification layer formal" but doesn't specify how it integrates with the existing validation steps.
  - **Evidence**: §4 mapping: "Phase 5.5: Validate → sdd-verify + anchor_dope doctor". Protocol.md Phase 5.5: existing Spec Compliance + TDD Compliance + Verifier Check.
  - **Confidence**: high
- **Recommendation**: sdd-verify should REPLACE the spec compliance check, not run alongside it. Define: Phase 5.5 runs sdd-verify (which includes spec compliance as a subset) + TDD compliance + verifier check. Avoid running two spec-checking pipelines.

### Finding 11: Dead Resources Still Referenced
- **Severity**: LOW
- **Type**: bottleneck
- **Components**: `resources/plannotator-gate.md`, `resources/sdd-integration-plan.md`
- **Description**: The doc identifies these as DEAD (§6 Resources: 2 dead). Yet SKILL.md Resources Index still lists both: `resources/plannotator-gate.md` (Phase 1.5) and `resources/sdd-integration-plan.md` (SDD gate planning). Loading a dead resource wastes the context budget and could cause the orchestrator to follow outdated instructions.
  - **Evidence**: §6: "DEAD: 2 — plannotator-gate.md, sdd-integration-plan.md". SKILL.md Resources Index lists both.
  - **Confidence**: high
- **Recommendation**: Immediate P0 action (as the doc states). Delete both files and remove from Resources Index. This is non-controversial cleanup.

---

## Authority Map

```
User Request
    │
    ├── [Phase 0: Clarify] ← CONFLICT: CLOOP vs protocol (Finding 2)
    │       ↓
    ├── [Phase 1: Plan] ← CONFLICT: CLOOP Layout/Operate vs protocol decomposition (Finding 3)
    │       ├── ANCHOR.md ← CONFLICT: orchestrator vs anchor_dope (Finding 1)
    │       ├── PLAN.md ← SSOT when anchor_dope inactive
    │       └── sdd-tasks output ← feeds Phase 3 Spawn
    │       ↓
    ├── [Phase 1.5: Plan Gate] ← CONFLICT: sdd-gate vs human approval (Finding 7)
    │       ↓
    ├── [Phase 1.6: Pre-flight] ← CONFLICT: anchor_dope gates vs protocol checks (Finding 6)
    │       ↓
    ├── [Phase 2-5: Execute] ← no governance conflicts
    │       ↓
    ├── [Phase 5.5: Validate] ← CONFLICT: sdd-verify vs existing checks (Finding 10)
    │       ↓
    └── [Phase 6: Cleanup] ← sdd-archive integration undefined
```

## Data Flow Direction

The primary flow is unidirectional (CLOOP → anchor_dope → SDD → tmux_fork), which is architecturally correct. No cycles detected in the main pipeline. However, two feedback loops create potential authority inversions:

1. **sdd-verify → anchor_dope doctor**: Verification results feed back to anchor_dope for structural validation. If doctor.sh rejects a plan that sdd-verify passed, which verdict wins? (Finding 9 makes this moot until scripts exist.)
2. **CLOOP Reflect → Phase 1.5**: Risk assessment from CLOOP feeds back into plan approval. This is architecturally sound (risk info informs approval) but the double-gate (Finding 7) complicates it.

## Risk Priority Matrix

| Finding | Severity | Confidence | Priority | Action |
|---------|----------|------------|----------|--------|
| F1: Double Writer ANCHOR.md | CRITICAL | high | **P1** | Block. Assign single writer before implementation. |
| F2: CLOOP vs Phase 0 | HIGH | high | **P1** | Block. Define dispatch arbiter in protocol. |
| F3: CLOOP vs Phase 1 | HIGH | high | **P1** | Block. Define normalization layer. |
| F4: workflow outline vs SDD | HIGH | high | **P1** | Block. Decide explicit replacement/coexistence. |
| F5: False SSOT ANCHOR.md | MEDIUM | high | **P2** | Qualify SSOT declaration. Implement scripts. |
| F6: Double Gate (1.5 + 1.6) | MEDIUM | medium | **P3** | Merge into ordered gate sequence. |
| F7: sdd-gate vs Plan Gate | MEDIUM | medium | **P3** | Define execution order + arbiter. |
| F8: Persistence fragmentation | MEDIUM | medium | **P3** | Pin governance pipeline to one mode. |
| F9: Missing scripts | MEDIUM | high | **P2** | Block P1 on implementation. |
| F10: sdd-verify vs Validate | LOW | high | **P3** | Replace, don't duplicate. |
| F11: Dead resources | LOW | high | **P3** | Immediate cleanup. |

## Recommendations Summary

1. **Before any implementation**: Resolve Findings 1-4 (P1). These are architectural conflicts that compound if built upon.
2. **Prerequisite check**: anchor_dope scripts must exist before the integration can proceed (Finding 9).
3. **SSOT hierarchy**: Define a clear chain: CLOOP produces intent → anchor_dope materializes artifacts → SDD decomposes → tmux_fork executes. Each layer READS from the previous and WRITES its own artifacts. No layer writes to another layer's artifacts.
4. **Gate consolidation**: Merge anchor_dope gates + protocol pre-flight into a single ordered gate sequence (Finding 6).
5. **Persistence**: Pin governance to `hybrid` mode (Finding 8).
6. **Dead resources**: Delete immediately (Finding 11).

---

*End of audit. 11 findings. 4 P1, 2 P2, 4 P3, 1 informational.*
