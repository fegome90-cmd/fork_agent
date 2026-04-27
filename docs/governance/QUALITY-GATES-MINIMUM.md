# Quality Gates — Minimum Standard

> Version: 1.1 | 2026-04-24
> Scope: Transversal. Applies to any plan, RC, WO, skill, backend change, or agent action.
> This document defines gates. It does NOT implement them.

---

## Purpose

Seven gates that any change must pass before proceeding. Not all gates apply to all contexts — see [Application by Context](#application-by-context).

---

## The Seven Gates

### A. Authority Gate

Who decides. What is canonical.

| Check | Question |
|-------|----------|
| SSOT declared | Is there exactly one authoritative source for this surface? |
| Non-authoritative surfaces identified | Are caches, renders, logs, and UI views explicitly marked as non-authoritative? |
| Legacy producers/consumers mapped | Do any old systems still write to or read from the authoritative surface? |
| No duplication proven | Can no other system produce the same state for the same surface? |

**Fails if**: Two systems both claim authority over the same surface, or no system claims authority.

### B. Evidence vs Authority Gate

Evidence informs. Authority decides.

| Check | Question |
|-------|----------|
| Decision authority identified | Which component produces the go/no-go verdict? |
| Evidence-only surfaces listed | Which outputs (logs, reports, dashboards) inform but do not decide? |
| Minimum evidence defined | What must be produced before a decision is valid? |
| Insufficient evidence flagged | What evidence looks conclusive but is not? |

**Fails if**: A log, report, or test result is treated as a decision when it is only evidence.

### C. Lifecycle Gate

State transitions have owners.

| Check | Question |
|-------|----------|
| Initial state defined | What does "starting" look like? |
| Terminal state defined | What does "done" look like? |
| Entrypoint owner | Exactly one component owns each transition? |
| Locking | Is concurrent mutation prevented (CAS, lock, lease)? |
| Rollback | Can a failed transition be undone? |
| Crash safety | What happens if the process dies mid-transition? |
| Audit trail | Can every transition be traced after the fact? |

**Fails if**: A state exists with no owner, or a transition has no lock and no crash recovery.

### D. Ownership Gate

One owner per responsibility.

| Check | Question |
|-------|----------|
| Single owner | Does exactly one component own this responsibility? |
| Allowed callers | Which components may invoke this gate? |
| Forbidden callers | Which components must NOT bypass this gate? |
| Parallel path guard | Is there a grep/test that catches unauthorized alternative paths? |

**Fails if**: Two components can both decide the same thing, or callers bypass the owner.

### E. Scope Gate

Minimum change. No parallel systems.

| Check | Question |
|-------|----------|
| Minimum change | Is this the smallest change that solves the problem? |
| No new infrastructure | Unless strongly justified, no new scripts, services, or systems. |
| No parallel system | Does this not duplicate an existing system's responsibility? |
| Debt accepted explicitly | If debt is introduced, is it documented with a reason and owner? |

**Fails if**: The change creates a new system for a surface that already has one, or adds infrastructure without justification.

### F. Validation Gate

Prove it works.

| Check | Question |
|-------|----------|
| Exact contract | What does "pass" mean in precise terms? |
| Reproducible test | Is there a command that anyone can run to verify? |
| Edge case | Does the test cover at least one boundary condition? |
| Uncovered risk | What risk is accepted without a test? |

**Fails if**: "Pass" is undefined, or no reproducible verification exists.

### G. Claim Discipline Gate

Claims match evidence.

| Check | Question |
|-------|----------|
| Maturity level | Is the claim ("stable", "closed", "SSOT") supported by evidence? |
| Supporting evidence | What specific test, audit, or run proves the claim? |
| Missing evidence | What evidence would be needed but does not exist yet? |
| Residual risk | What could go wrong despite the claim? |
| Invalidation condition | Under what condition would this claim become false? |

**Fails if**: A claim is made without evidence, or a stronger claim is made than evidence supports.

---

## Application by Context

Not every gate applies to every situation. Apply based on context.

### A. Pre-task Gates — Orchestrator

Apply before an agent starts a task.

| Gate | Required | Why |
|------|----------|-----|
| Authority | YES | Who decides if the task can start? |
| Evidence vs Authority | YES | Health checks inform; they do not decide. |
| Lifecycle | YES | Task has states: pending → in_progress → completed. |
| Ownership | YES | One owner decides launch permission. |
| Scope | YES | Prevent scope creep mid-orchestration. |
| Validation | YES | Contract for "task ready to start" must be explicit. |
| Claim Discipline | YES | No claiming "task is ready" without evidence. |

### B. RC Closure Gates

Apply when closing a release candidate or milestone.

| Gate | Required | Why |
|------|----------|-----|
| Authority | YES | Who declares the RC closed? |
| Evidence vs Authority | YES | Authority declares closure, but minimum evidence must sustain the decision. Evidence alone does not close an RC — it supports the authority's claim. |
| Lifecycle | If state/versions exist | RC labels, reopening conditions, version bumps. |
| Ownership | Optional | Usually single-owner (the author). |
| Scope | YES | Prevent "one more thing" under the current RC. |
| Validation | YES | Specific tests/audits must pass for closure. |
| Claim Discipline | YES | "Closed" requires evidence. Residual risks must be stated. |

### C. Backend / Repo Gates

Apply to code-first services and infrastructure.

| Gate | Required | Why |
|------|----------|-----|
| Authority | YES | Which service owns each entity's lifecycle? |
| Evidence vs Authority | YES | When logs, metrics, tests, reports, or audits are used to justify state or readiness, they must be classified as evidence, not authority. |
| Lifecycle | YES | State machines, transitions, persistence. |
| Ownership | YES | One service per entity transition. |
| Scope | YES | No parallel implementations for the same surface. |
| Validation | YES | Tests must cover the contract. |
| Claim Discipline | YES, when claims are made | Required when anyone claims maturity, stability, SSOT, production-ready, closed, ready, or frictionless. Tests do not speak for themselves — the claim must be explicit and supported. |
| Crash safety | When writing state | Atomic writes, CAS, lease mechanisms. |

### D. Skill / Repo Boundary Gates

Apply when the skill executes and the repo maintains authority.

| Gate | Required | Why |
|------|----------|-----|
| Authority | YES | Who executes, who decides. |
| Evidence vs Authority | YES | Skill output is evidence; repo state is authority. |
| Lifecycle | YES | Skill and repo may track the same lifecycle differently. |
| Ownership | YES | Skill must not bypass repo's authority on shared surfaces. |
| Scope | YES | No creating a third system. |
| Validation | YES | Boundary contract must be explicit. |
| Claim Discipline | YES | Skill claims about repo surfaces require repo evidence. |

---

## No-Mix Rule

These are separate concerns. Do not mix them.

- **Not every gate is pre-task.** Pre-task is one context. RC closure is another. Backend is another. Boundary is another.
- **Not every closure is lifecycle.** Closing an RC is a scope and claim decision, not a state transition.
- **Not every governance document is enforcement.** Advisory guidelines exist. They should be labeled as such.
- **Not every test is authority.** Tests are evidence. They inform decisions but do not replace ownership.
- **The skill orchestrator and the repo backend are distinct systems.** They will converge in the future. Until then, treat them separately.
- **Memory Lifecycle RC-2 is a point closure.** It is not the model for all gates. It is an example of claim discipline.

---

## Acceptance Criteria

This document passes if:

- [x] Defines all 7 minimum quality gates
- [x] Separates pre-task, RC closure, backend, and skill/repo boundary
- [x] Does not create a third system
- [x] Maintains gates as a transversal standard
- [x] Does not promise implementation
- [x] States clearly what must be explored next (context-specific gate documents)

> **Note**: These checkboxes represent declared documentary acceptance, not executable validation. They confirm the author's intent, not runtime enforcement.

---

## Next Steps

1. Create `PRE-TASK-GATES-ORCHESTRATOR.md` — operational gates for the skill orchestrator
2. Create `RC-CLOSURE-GATE.md` — template for RC milestone closures
3. Create `BACKEND-LIFECYCLE-GATE.md` — gates for repo code-first services
4. Create `SKILL-REPO-BOUNDARY-GATE.md` — contract between skill execution and repo authority
5. Map the 12 fixes from `docs/reports/skill-gates-fix-list.md` to the correct context (pre-task, RC closure, backend, or boundary) before implementing any of them. Fixes applied to the wrong context create the same problem this document exists to prevent.
