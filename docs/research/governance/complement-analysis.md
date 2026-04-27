# Complement Analysis: spec-kit vs anchor_dope vs SDD

> Generated: 2026-04-23 | Method: Triangulated comparison from source analysis

---

## 1. Comparison Table

| Dimension | spec-kit (GitHub) | anchor_dope | SDD (our skills) |
|-----------|------------------|-------------|-------------------|
| **Origin** | GitHub Open Source (30+ agent integrations) | Internal project (Felipe) | Internal skills (11 skills) |
| **Spec format** | `spec.md` — User Stories (P1/P2/P3) + FR-### requirements + Success Criteria (SC-###) + Edge Cases + Assumptions | `anchor.md` — 50-line SSOT: Objetivo + In Scope + Out of Scope + Exit Criteria | Delta spec — ADDED/MODIFIED/REMOVED Requirements with Given/When/Then scenarios |
| **Plan format** | `plan.md` — Technical Context + Constitution Check + Project Structure + Complexity Tracking + research.md + data-model.md + contracts/ + quickstart.md | N/A — anchor IS the plan. No separate plan document. | `proposal.md` — Intent + Scope + Capabilities + Approach + Affected Areas + Risks + Rollback |
| **Task format** | `tasks.md` — Phases (Setup/Foundational/User Stories/Polish) + [P] parallel markers + T### IDs + dependencies + execution strategies | N/A — no task decomposition. anchor.md has Exit Criteria checklist only | `tasks.md` — Phases (Foundation/Core/Integration/Testing/Cleanup) + hierarchical checklist + quality criteria |
| **Gates** | Phase -1 pre-implementation gates (Simplicity, Anti-Abstraction, Integration-First from constitution) + `/speckit.analyze` cross-artifact consistency check | 4 pre-flight gates (Contexto, Fase, Superficie, Estado limpio) | 3-agent quality gate (sdd-structure, sdd-design, sdd-risk) with BLOCK/REVIEW/PASS thresholds |
| **Constitution** | `constitution.md` — 9 articles (Library-First, CLI Interface, Test-First, Simplicity, Anti-Abstraction, etc.) + amendment process + version tracking | Constitución AI v1.1 — 13 leyes (referenced but content not in scope of analysis) | N/A — no constitution concept. Standards come from `sdd-init` detection |
| **Validation** | `/speckit.analyze` — cross-artifact consistency analysis (duplication, ambiguity, coverage gaps, constitution alignment) + `/speckit.checklist` | `doctor.sh` — structural validation (directory structure, required sections, slug consistency, line limits, reference resolution) | `sdd-verify` — Spec Compliance Matrix (every scenario → test → result) + real test execution + coverage analysis |
| **Lifecycle** | constitution → specify → clarify → plan → analyze → tasks → implement (6 commands, linear) | create → validate → execute (3 implicit phases, template-stamped) | init → explore → propose → spec + design → tasks → gate → apply → verify → archive (9 explicit phases) |
| **Implementation** | `/speckit.implement` — task-by-task execution with TDD, progress tracking, error handling, checkpoint validation | N/A — no implementation skill. Relies on external executor. | `sdd-apply` — Strict TDD mode (RED→GREEN→TRIANGULATE→REFACTOR) or standard mode |
| **Persistence** | Filesystem only — `.specify/` directory (specs/, memory/, templates/, scripts/) | Filesystem only — `_ctx/plans/YYYY/PLAN-YYYY-NNNN-slug/` structure | 4 modes: engram (memory DB), openspec (filesystem), hybrid (both), none |
| **Conflict resolution** | Constitution supersedes all practices. Complexity must be justified in Complexity Tracking table. | anchor.md > SKILL.md > agents.md/prime.md (strict hierarchy, no exceptions) | Proposal Capabilities section drives spec creation. Spec drives design and tasks. |
| **Extensibility** | Extension system (catalog.community.json, 50+ extensions) + Preset system + Project-local overrides + Hook system | Template-based (`.tmpl` files) — 2 variables, no conditionals | Skill-based (11 skills) + conditional module loading (TDD on/off) + persistence mode selection |
| **Agent support** | 30+ AI agents (Claude, Copilot, Gemini, Codex, Cursor, Kiro, Pi, etc.) via integration registry | Agent-agnostic — conventions document IS the contract | pi ecosystem only — skills loaded by pi agent |
| **Scale** | Greenfield (0-to-1) + Brownfield + Creative Exploration | Sprint pack — single sprint scope | Change-level — single feature/change at a time |
| **Size constraints** | No explicit limits on spec/plan/tasks length | 50 lines (anchor) / 80 lines (SKILL) / 40 lines (agents) / 50 lines (prime) — HARD limits | Word budgets: proposal ≤450, spec ≤650, design ≤800, tasks ≤530 |
| **Research phase** | `/speckit.clarify` (clarification) + `research.md` in plan output | N/A — no research phase | `sdd-explore` — pre-proposal codebase investigation |
| **Archive/post** | No built-in archive. Extensions exist (spec-kit-archive, spec-kit-retro) | No archive concept — plan exists until superseded | `sdd-archive` — syncs delta specs to main specs, produces archive report |
| **Workflow engine** | Full YAML-based workflow engine with 10 step types (command, shell, gate, if, switch, while, fan-out, fan-in, prompt, do-while) + state persistence + resume | N/A — no workflow engine | N/A — orchestrator drives phases externally |
| **CLI** | `specify` CLI — init, extension, preset, integration, workflow, check, version commands | No CLI — templates only, delegates to `trifecta` | N/A — skills invoked by orchestrator |

---

## 2. What spec-kit does that anchor_dope and SDD don't

1. **Constitution-driven governance** — spec-kit's `constitution.md` is a formal, versioned contract with 9 articles that constrain ALL downstream artifacts. anchor_dope has a "Constitución AI v1.1" but it's external reference, not embedded in the sprint pack. SDD has no constitution concept at all.

2. **Cross-artifact consistency analysis** — `/speckit.analyze` performs a non-destructive, multi-dimensional analysis across spec + plan + tasks with severity assignment (CRITICAL/HIGH/MEDIUM/LOW), coverage gap detection, and constitution alignment checking. Neither anchor_dope nor SDD has an equivalent.

3. **Extension ecosystem** — 50+ community extensions covering Jira sync, Azure DevOps, security review, V-Model, worktree isolation, retrospectives, and more. Neither anchor_dope nor SDD has an extension/plugin model.

4. **Multi-agent integration** — 30+ agent integrations via a registry pattern (MarkdownIntegration, TomlIntegration, YamlIntegration, SkillsIntegration base classes). SDD is pi-only. anchor_dope is agent-agnostic but has no explicit integrations.

5. **Workflow engine** — Full YAML-based workflow engine with 10 step types, expression engine, state persistence, resume capability, and catalog system. Neither competitor has this.

6. **User Story prioritization** — spec-kit forces P1/P2/P3 prioritization with independent testability per story. SDD organizes tasks by phase (Foundation/Core/Integration). anchor_dope has no task decomposition.

7. **Research as first-class artifact** — `research.md` is a required output of `/speckit.plan`, capturing tech stack decisions, version pinning, and library comparisons. SDD has `sdd-explore` but it's optional and pre-proposal.

8. **Clarification workflow** — `/speckit.clarify` is a structured, coverage-based questioning that records answers in a Clarifications section. Neither competitor has an explicit clarification step.

9. **Preset system** — Stackable presets that customize terminology, templates, and workflow without code changes. Neither competitor has this.

10. **Quality checklist generation** — `/speckit.checklist` generates custom quality checklists (like "unit tests for English"). SDD has quality criteria in tasks but no separate checklist generator.

---

## 3. What anchor_dope does that spec-kit doesn't

1. **Strict SSOT with line limits** — anchor.md is THE single source of truth at 50 lines max. This forces extreme precision. spec-kit specs can be arbitrarily long.

2. **Conflict resolution hierarchy** — Explicit, deterministic priority: anchor.md > SKILL.md > agents.md/prime.md. No ambiguity. spec-kit has "constitution supersedes" but no hierarchy between spec artifacts.

3. **Pre-flight gates as executable protocol** — 4 gates (Context, Phase, Surface, Clean State) with Condition/Evidence/If-Fails structure. These are designed to be verified before ANY action, not just at a review checkpoint.

4. **Template-stamped sprint packs** — You create a sprint pack, you get a fixed structure. No configuration. No mode selection. This is intentional — the constraint IS the feature.

5. **Constitución AI v1.1** — While spec-kit has a constitution, anchor_dope's is specifically designed for AI-agent governance (13 laws). Different scope.

6. **Skill bridge (SKILL.md)** — A dedicated document that bridges the anchor to resources with a fixed load order. spec-kit has no equivalent — templates are self-contained.

7. **Structural validation (doctor.sh)** — Validates directory structure, section presence, slug consistency, line limits, and reference resolution. spec-kit has `/speckit.analyze` but that's semantic, not structural.

---

## 4. What SDD does that spec-kit doesn't

1. **Delta specs** — SDD tracks ADDED/MODIFIED/REMOVED requirements against a main spec. This is critical for brownfield/iterative development. spec-kit creates fresh specs per feature with no concept of delta.

2. **Spec Compliance Matrix** — Every requirement scenario mapped to a test with explicit COMPLIANT/FAILING/UNTESTED/PARTIAL status. spec-kit has no verification against specs post-implementation.

3. **Strict TDD with cycle evidence** — RED→GREEN→TRIANGULATE→REFACTOR with evidence tables, assertion quality rules, mock ratio limits, and extract-before-mock patterns. spec-kit mentions TDD but doesn't enforce it with this granularity.

4. **Conditionally-loaded modules** — TDD modules load only when `strict_tdd=true`, saving ~650 lines of context when not needed. spec-kit has no conditional loading.

5. **Pre-implementation quality gate** — `sdd-gate-skill` runs 3 parallel agents (structure, design, risk) with BLOCK/REVIEW/PASS thresholds BEFORE code is written. spec-kit's `/speckit.analyze` is closest but runs after tasks are generated, not before implementation.

6. **Persistence flexibility** — 4 modes (engram, openspec, hybrid, none) with deterministic topic_key naming for upserts. spec-kit is filesystem-only.

7. **Artifact lineage** — Every artifact has explicit producer/consumer contracts and dependency graphs. spec-kit has implicit dependencies between spec→plan→tasks.

8. **Archive with spec sync** — `sdd-archive` merges delta specs back into main specs. spec-kit has no built-in archival (community extensions fill this gap).

9. **Design as separate phase** — `sdd-design` produces architecture decisions, data flow diagrams, file changes, interfaces, and testing strategy as a separate artifact from the spec. spec-kit embeds design in `plan.md` but doesn't separate it.

10. **Size budgets per artifact** — Word budgets (450/650/800/530) enforce conciseness. spec-kit has no explicit limits.

---

## 5. COMPLEMENT Space — What to Borrow Without Competing

### Safe to adopt (no overlap with anchor_dope's SSOT role)

| Idea | From | Why it complements | Where to apply |
|------|------|--------------------|----------------|
| **Cross-artifact analysis** | spec-kit `/speckit.analyze` | anchor_dope has doctor.sh for structure, not semantic consistency. We need BOTH structural + semantic validation. | `tmux_fork` protocol Phase 1.5 — after SDD artifacts exist, before apply |
| **Constitution as governance layer** | spec-kit constitution.md | anchor_dope's Constitución AI v1.1 covers AI behavior. We need a project-level constitution for tech decisions (stack, testing, architecture). | `.specify/constitution.md` or `docs/constitution.md` in tmux_fork |
| **User Story prioritization** | spec-kit P1/P2/P3 | SDD tasks are phase-based (Foundation/Core). Adding priority within phases would help parallel agent assignment. | `sdd-tasks` output format — add [P1]/[P2] markers alongside [P] |
| **Clarification workflow** | spec-kit `/speckit.clarify` | SDD's explore is codebase-focused. We miss a user-facing clarification step. | New skill or protocol phase between CLOOP Clarify and sdd-propose |
| **Coverage gap detection** | spec-kit analyze | SDD verify checks spec compliance AFTER implementation. We should check coverage BEFORE implementation. | Enhance `sdd-gate-skill` with coverage analysis |
| **Hook system** | spec-kit extensions.yml | anchor_dope has no hooks. SDD has no hooks. A simple pre/post hook mechanism for each phase would allow project-specific validation. | `.sdd/hooks.yml` — before_apply, after_verify, etc. |
| **Quality checklist generator** | spec-kit `/speckit.checklist` | Neither anchor_dope nor SDD generates review checklists. Useful for the Plan Gate. | Protocol Phase 1.5 — generate from spec + constitution |

### Risky to adopt (potential overlap)

| Idea | From | Risk | Verdict |
|------|------|------|---------|
| **Full extension system** | spec-kit | Over-engineering for our scale. We have skills already. | AVOID — use skill-hub instead |
| **Workflow engine** | spec-kit | Massive complexity. Our orchestrator is tmux_fork protocol. | AVOID — tmux_fork IS our workflow engine |
| **Multi-agent integration** | spec-kit | We only use pi. Supporting 30+ agents is not our scope. | AVOID — stay pi-native |
| **Preset system** | spec-kit | Our templates are anchor_dope templates + SDD skills. Adding a preset layer adds complexity for no gain. | AVOID — conventions.md already handles this |
| **Constitution template** | spec-kit | anchor_dope already has Constitución AI v1.1. Two constitutions = confusion. | CAREFUL — only if scope is clearly different (AI behavior vs project tech) |

---

## 6. What We Should AVOID Copying (We Already Have Better)

| spec-kit Feature | Our Equivalent | Why Ours Is Better |
|------------------|----------------|---------------------|
| **spec.md format** | SDD delta specs | Delta specs handle brownfield/iteration. spec-kit creates fresh specs every time — loses history. |
| **plan.md** | SDD proposal + design (2 separate docs) | Separation of concerns. spec-kit mixes requirements+design+architecture in one plan. |
| **tasks.md [P] markers** | SDD tasks + tmux_fork agent assignment | We have actual parallel execution via tmux panes. spec-kit's [P] is aspirational. |
| **implement command** | sdd-apply + strict TDD | Our TDD enforcement is far more rigorous (evidence tables, assertion audits, mock ratios). |
| **analyze command** | sdd-gate-skill (pre-implementation) + sdd-verify (post-implementation) | We catch issues BEFORE and AFTER. spec-kit only has post-tasks analysis. |
| **Constitution articles** | Constitución AI v1.1 (anchor_dope) | Our constitution covers AI governance specifically. spec-kit's covers generic dev practices. |
| **Filesystem persistence** | 4 persistence modes (engram/openspec/hybrid/none) | We have more flexibility for different workflows. |
| **Extension catalog** | skill-hub + pi skills ecosystem | We already have a skill registry and skill loading mechanism. |

---

## 7. Synthesis — Integration Architecture

```
                        OUR STACK (keep)                    BORROW FROM spec-kit
                    ┌─────────────────────┐            ┌──────────────────────────┐
                    │                     │            │                          │
                    │  anchor_dope        │            │  Constitution template   │
                    │  anchor.md (SSOT)   │            │  Cross-artifact analysis │
                    │  SKILL.md (bridge)  │            │  Clarification workflow  │
                    │  prime.md (gates)   │            │  Coverage gap detection  │
                    │  agents.md (roles)  │            │  Quality checklist gen   │
                    │                     │            │                          │
                    ├─────────────────────┤            └──────────────────────────┘
                    │                     │                       │
                    │  SDD skills         │                       ▼
                    │  propose → spec →   │            ┌──────────────────────────┐
                    │  design → tasks →   │            │  Enhanced protocol       │
                    │  gate → apply →     │            │  Phase 0.5: Clarify      │
                    │  verify → archive   │            │  Phase 1.5: Analyze      │
                    │                     │            │  Phase 5.5: Compliance   │
                    ├─────────────────────┤            └──────────────────────────┘
                    │                     │
                    │  tmux_fork          │
                    │  Protocol 7 phases  │
                    │  Parallel execution │
                    │  Agent coordination │
                    │                     │
                    └─────────────────────┘
```

### Concrete Borrow List (Prioritized)

| # | What | From spec-kit | Integration Point | Effort |
|---|------|--------------|-------------------|--------|
| 1 | **Clarification phase** | `/speckit.clarify` coverage-based questioning | New protocol phase 0.5, between CLOOP Clarify and sdd-propose | Medium |
| 2 | **Constitution for tech decisions** | constitution.md template (simplified) | `.sdd/constitution.md` — project tech stack + testing standards + architecture principles. NOT replacing Constitución AI | Small |
| 3 | **Coverage gap detection** | `/speckit.analyze` coverage analysis | Enhance `sdd-gate-skill` — add "requirements with zero tasks" check | Small |
| 4 | **User Story priority markers** | P1/P2/P3 in spec template | Add to SDD spec format — optional `[P1]` markers on requirements | Trivial |
| 5 | **Quality checklist generation** | `/speckit.checklist` | New resource or protocol phase — generate from spec + constitution at Plan Gate | Medium |

### NOT Borrowing

| What | Why Not |
|------|---------|
| Extension system | skill-hub covers this |
| Workflow engine | tmux_fork protocol is our engine |
| Multi-agent registry | pi-only is our scope |
| Preset system | conventions.md + template variables cover this |
| spec.md format | SDD delta specs are strictly better for our use case |
| implement command | sdd-apply with strict TDD is far more rigorous |
| Full analyze command | sdd-gate + sdd-verify cover both pre and post |

---

## 8. Key Insight

**The complement space is NARROW.** Our stack (anchor_dope + SDD + tmux_fork) already covers 85% of what spec-kit offers, and in several dimensions (delta specs, compliance matrix, strict TDD, parallel execution) we are strictly superior.

The borrow opportunities cluster around **pre-implementation quality gates** that neither anchor_dope (structural focus) nor SDD (spec compliance focus) fully address:

1. **Semantic consistency analysis** — "do these artifacts contradict each other?"
2. **Coverage gap detection** — "is every requirement covered by a task?"
3. **Clarification workflow** — "did we ask the right questions before designing?"

These fill the gap between anchor_dope's structural gates and SDD's compliance verification.

spec-kit's real innovation is the **ecosystem** (extensions, presets, 30+ integrations, workflow engine) — but that's a different game than what we're playing. We're building a focused, opinionated stack. They're building a platform. Different goals.
