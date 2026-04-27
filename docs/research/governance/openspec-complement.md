# OpenSpec vs spec-kit vs Our Governance Stack

Date: 2026-04-23
Project: tmux_fork governance research

## Sources reviewed

- `/tmp/fork-research-openspec.md` — not present at analysis time
- `/Users/felipe_gonzalez/Developer/tmux_fork/docs/research/governance/governance-integration-research.md`
- `/Users/felipe_gonzalez/Developer/tmux_fork/docs/research/governance/complement-analysis.md`
- `/Users/felipe_gonzalez/Developer/tmux_fork/docs/research/governance/spec-kit-analysis.md`
- `/tmp/OpenSpec/openspec/config.yaml`
- `/tmp/OpenSpec/openspec/changes/IMPLEMENTATION_ORDER.md`
- `/tmp/OpenSpec/schemas/spec-driven/schema.yaml`
- `/tmp/OpenSpec/README.md`
- `/tmp/OpenSpec/docs/commands.md`
- `/tmp/OpenSpec/docs/workflows.md`
- `/tmp/OpenSpec/docs/concepts.md`

---

## Executive take

OpenSpec sits between spec-kit and our stack.

- **Compared to spec-kit**, OpenSpec is lighter, more change-centric, and has a much better built-in story for **active changes, sync, verify, and archive**.
- **Compared to our stack**, OpenSpec is less rigorous on governance and verification, but better packaged as a **self-contained repo-local change system** with a clean artifact topology.
- **Compared to both**, OpenSpec's strongest distinctive move is: **live specs as current truth + separate change folders as delta workspaces + archive as first-class lifecycle closure**.

---

## 3-way comparison

| Dimension | OpenSpec | spec-kit | Our Stack |
|-----------|----------|----------|-----------|
| **Spec format** | Main specs in `openspec/specs/<domain>/spec.md` with `### Requirement` + `#### Scenario`; change deltas use `ADDED / MODIFIED / REMOVED / RENAMED` requirement sections | `spec.md` with User Stories `[P1]/[P2]/[P3]`, FRs, SCs, Edge Cases, Assumptions | SDD delta specs with `ADDED / MODIFIED / REMOVED` requirements and Given/When/Then scenarios; plus `anchor.md` as sprint SSOT |
| **Change system** | First-class change folders in `openspec/changes/<change>/` with `proposal.md`, `specs/`, `design.md`, `tasks.md`, optional `.openspec.yaml`; schema-driven artifact DAG | Feature/spec workflow under `specs/NNN-feature/`; strong artifact chain but **no true built-in change/archive lifecycle** | `sdd-propose` names the change, then `spec → design → tasks → apply → verify → archive`; governance anchored by anchor_dope + CLOOP + tmux_fork |
| **Validation** | Built-in artifact constraints, repo-local generation rules from `config.yaml`, `/opsx:verify` for completeness/correctness/coherence, sync/archive merge checks | Constitution gates, `/speckit.analyze`, `/speckit.checklist`, plan-time analysis | `sdd-gate` pre-implementation, `sdd-verify` post-implementation compliance matrix, `anchor_dope doctor` structural validation |
| **Archive** | **Yes**: `/opsx:sync`, `/opsx:archive`, `/opsx:bulk-archive`; archives change and merges deltas into main specs | **No built-in archive**; extensions fill parts of the gap | **Yes**: `sdd-archive` syncs deltas to main specs and archives/reporting |
| **CLI** | `openspec` CLI + `/opsx:*` slash-command workflow | `specify` CLI + `/speckit.*` commands | `memory workflow ...` Python CLI + pi skills + tmux_fork orchestration |
| **Persistence** | Filesystem only: `openspec/specs/`, `openspec/changes/`, `openspec/schemas/`, `openspec/config.yaml` | Filesystem only: `.specify/`, feature folders, templates, extensions | Hybrid: filesystem artifacts + memory MCP / persistent DB; governance state can be split across artifacts and memory |
| **Workflow philosophy** | Fluid, action-oriented, iterative, brownfield-first; dependencies are enablers, not hard phase gates | More methodical and constitution-driven; stronger up-front analysis and artifact discipline | Governance-heavy, phase-aware, explicitly gated, orchestration-first |
| **Design artifact** | `design.md` is optional and only created when complexity warrants it | `plan.md` is always central; design context expanded into `research.md`, `data-model.md`, `contracts/`, `quickstart.md` | `sdd-design` is explicit and separate from proposal/spec |
| **Verification posture** | Advisory verification before archive; archive can proceed with warnings | Strong artifact analysis before implementation, but no native archive/merge loop | Stronger blocking gates before and after implementation; compliance matrix is stricter than advisory verify |
| **Customization model** | Repo-local schema YAML defines artifact graph and instructions | Templates, presets, extensions, workflow engine | Skills, templates, orchestration protocol, persistence modes |

---

## 1. What OpenSpec does BETTER than spec-kit

1. **Built-in lifecycle closure**
   - OpenSpec has native `/opsx:sync`, `/opsx:archive`, and `/opsx:bulk-archive`.
   - spec-kit is strong on planning and analysis, but weak on a built-in “finish the change and merge it back” loop.

2. **Cleaner brownfield mental model**
   - OpenSpec separates:
     - `openspec/specs/` = current truth
     - `openspec/changes/` = proposed deltas
   - That is simpler and more operationally clear than spec-kit's feature-folder model.

3. **More fluid operator UX**
   - OpenSpec explicitly rejects rigid phase-locking.
   - `/opsx:propose`, `/opsx:continue`, `/opsx:ff`, `/opsx:apply`, `/opsx:verify` is easier to teach and easier to recover mid-stream.

4. **Better support for parallel active changes**
   - `bulk-archive` plus conflict-aware spec merging is a real advantage.
   - spec-kit has artifacts and workflows, but not the same first-class parallel-change closeout model.

5. **Lower ceremony for common work**
   - OpenSpec gives a short default path: `propose → apply → archive`.
   - spec-kit is more powerful, but also heavier.

---

## 2. What OpenSpec does that NEITHER spec-kit nor our stack does

1. **Repo-local schema-driven artifact DAG as the primary workflow contract**
   - `schemas/spec-driven/schema.yaml` explicitly defines artifacts, generated files, dependencies, and apply requirements.
   - Our stack has a fixed skill pipeline; spec-kit has templates/workflows/extensions, but not the same simple per-schema artifact contract as the center of the model.

2. **Native bulk archive with conflict resolution across multiple completed changes**
   - `/opsx:bulk-archive` is unusually practical.
   - Neither spec-kit nor our current stack has that as a first-class built-in command.

3. **A clean “changes as folders, specs as truth, archive as chronology” filesystem UX**
   - We conceptually do deltas and archive in SDD, but OpenSpec packages this as a very legible default repo structure.
   - spec-kit does not.

---

## 3. Where our stack SUPERSEDES OpenSpec

1. **Governance rigor**
   - We have a stacked model: **CLOOP → anchor_dope → SDD → tmux_fork**.
   - OpenSpec is intentionally lighter; our stack is more suitable when governance correctness matters more than speed.

2. **Pre-implementation quality gates**
   - `sdd-gate` is stronger than OpenSpec's advisory model.
   - OpenSpec's `/opsx:verify` is useful, but it is not equivalent to a formal blocking gate.

3. **Post-implementation traceability**
   - `sdd-verify` with a compliance matrix is stricter than OpenSpec's completeness/correctness/coherence report.
   - We are closer to “prove implementation satisfies spec,” not just “review for drift.”

4. **Strict TDD posture**
   - Our stack explicitly supports strict TDD and stronger verification discipline.
   - OpenSpec is more workflow-centric than test-discipline-centric.

5. **Hybrid persistence and memory**
   - We can persist in files and memory DB/MCP.
   - OpenSpec is filesystem-only.

6. **Orchestration and parallel agent execution**
   - tmux_fork gives us an execution engine.
   - OpenSpec gives artifact workflow, not serious orchestration depth.

7. **SSOT and authority rules**
   - anchor_dope's hierarchy and our authority-flow work provide stronger ownership semantics.
   - OpenSpec is simpler, but less explicit about inter-artifact authority than our intended governance layer.

---

## 4. What 3 ideas should we STEAL from OpenSpec

### 1. Explicit `specs/` vs `changes/` filesystem topology
Why steal it:
- It makes the current truth vs proposed delta distinction obvious.
- It improves reviewability and onboarding.

How to apply:
- Keep SDD semantics, but make the repo-local artifact layout more visually obvious and durable.

### 2. Schema YAML for artifact graphs
Why steal it:
- `schema.yaml` is a compact, auditable way to define artifact order, dependencies, and instructions.
- It gives a repo-local workflow contract without hardcoding everything into skills.

How to apply:
- Use schema files as declarative config for our orchestrator/SDD bridge, while keeping our stronger gates.

### 3. `/verify` and `/bulk-archive` UX
Why steal it:
- `verify` gives a clean human-readable pre-closeout report.
- `bulk-archive` solves a real operational problem in parallel work streams.

How to apply:
- Add a tmux_fork/SDD-facing verification summary layer and a multi-change archive/sync command.

---

## 5. What should we AVOID from OpenSpec

1. **Over-indexing on fluidity**
   - “Dependencies are enablers, not gates” is good for usability, but dangerous if it weakens governance.
   - Our stack exists precisely to prevent drift and silent divergence.

2. **Advisory-only verification**
   - OpenSpec verification is useful, but too soft for our target posture.
   - We should keep blocking gates where correctness matters.

3. **Parser-fragile markdown contracts**
   - OpenSpec's spec rules include sharp edges like exact heading levels (`#### Scenario`) and warnings about silent failure.
   - We should avoid syntax where one markdown typo degrades semantics invisibly.

4. **Too many user-facing workflow variants without governance boundaries**
   - `core` vs expanded profiles are nice, but can create ambiguity if not paired with authority rules.
   - In our stack, fast paths must still respect governance.

5. **Filesystem-only state**
   - For us, that would be a regression.
   - We should keep hybrid state and structured memory.

---

## 6. How does OpenSpec's change system compare to SDD's delta spec system?

## Shared strengths

Both systems agree on the important part:
- changes are first-class
- specs should evolve through deltas
- proposal/spec/design/tasks is a coherent artifact chain
- archive should merge delta specs back into the long-lived truth

That means OpenSpec is **much closer to SDD than spec-kit is** on change semantics.

## Key differences

### A. OpenSpec is folder-native; SDD is pipeline-native
- **OpenSpec** centers the **change folder** as the operational unit.
- **SDD** centers the **skill pipeline** and lets persistence vary.

### B. OpenSpec is fluid; SDD is governed
- **OpenSpec** lets you create artifacts whenever dependencies allow it.
- **SDD** is more explicit about stage intent and quality gates.

### C. OpenSpec verify is advisory; SDD verify is compliance-oriented
- OpenSpec asks: “does implementation still line up with artifacts?”
- SDD asks: “can we demonstrate the implementation satisfies spec/design/tasks?”

### D. OpenSpec is filesystem-only; SDD can be hybrid
- OpenSpec assumes repo-local markdown is the whole system.
- SDD can split state across filesystem and memory-backed persistence.

### E. OpenSpec's schema is declarative; SDD's workflow is encoded in skills/protocol
- OpenSpec makes artifact dependencies easy to inspect in YAML.
- SDD is richer, but less trivially inspectable by repo readers.

## Bottom line

OpenSpec's change system is the **closest external analogue** to our SDD delta-spec direction, but it is a **lighter and less governed** version of it.

---

## 7. Is there a fundamental philosophical difference between OpenSpec and spec-kit?

**Yes. A real one.**

### OpenSpec philosophy
- fluid, iterative, easy, brownfield-first
- optimize for adoption and day-to-day usability
- treat artifacts as practical tools for change management
- keep the workflow lightweight enough that people actually use it

### spec-kit philosophy
- specification-first with stronger up-front rigor
- constitution-driven governance
- artifact analysis and consistency checking before implementation
- broader platform/ecosystem ambition

## Plainly stated

- **OpenSpec** says: “make specs practical enough for real-world brownfield work and keep the workflow moving.”
- **spec-kit** says: “make the specification system rigorous enough that it governs implementation behavior.”

That is not just a UX difference. It is a **governance difference**.

OpenSpec optimizes for **friction reduction**.
spec-kit optimizes for **spec discipline**.

Our stack is closer to **spec discipline plus orchestration discipline**, which is why OpenSpec is interesting mainly as a packaging and lifecycle model, not as a governance replacement.

---

## Recommended synthesis

If we integrate lessons from OpenSpec, the right move is:

1. **Keep our governance stack** as the authority layer.
2. **Borrow OpenSpec's repository ergonomics**:
   - clear `specs/` vs `changes/`
   - explicit archive chronology
   - human-readable verify/closeout UX
3. **Borrow OpenSpec's schema YAML idea** as a declarative config layer.
4. **Do not relax our gates** to match OpenSpec's lighter posture.

In other words:

- **spec-kit** contributes analysis ideas
- **OpenSpec** contributes lifecycle packaging ideas
- **our stack** remains the stronger governance/execution system

That is the clean complement story.
