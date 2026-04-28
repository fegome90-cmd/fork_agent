## Status: success

## Summary: Complete technical spec of the gentle-ai skills system — SKILL.md structure, skill resolver protocol, registry generation, AGENTS.md index, shared conventions, TDD enforcement, inject.go deployment, and judgment-day protocol.

## Artifacts: /tmp/fork-ga-skills.md

## Next: none

## Risks: None

## TDD Evidence: N/A (explorer role)

# Gentle-AI Skills System — Technical Spec

## 1. System Overview

Gentle-AI implements a **skill-based agent instruction system** where reusable behavior modules (skills) are defined as SKILL.md files, indexed in a registry, resolved by context, and injected into agent prompts. The system has two main skill categories:

1. **SDD Workflow Skills** (`sdd-*`) — a 9-phase spec-driven development lifecycle (explore → propose → spec → design → tasks → apply → verify → archive + onboard)
2. **Project Skills** — domain-specific coding standards (go-testing, branch-pr, issue-creation, judgment-day)

Skills are **embedded in the Go binary** via `internal/assets/` and written to the filesystem at install time via `inject.go`.

---

## 2. SKILL.md Structure

Every skill is defined by a `SKILL.md` file with this anatomy:

### 2.1 Frontmatter (YAML)

```yaml
---
name: <skill-id> # Unique identifier, kebab-case
description: >
  <human-readable description>
  Trigger: <when to activate>
license: MIT | Apache-2.0
metadata:
  author: gentleman-programming
  version: "X.Y"
---
```

| Field              | Required | Purpose                                                         |
| ------------------ | -------- | --------------------------------------------------------------- |
| `name`             | Yes      | Unique skill ID, used as directory name and in inject.go        |
| `description`      | Yes      | Human-readable description + `Trigger:` clause for the registry |
| `license`          | Yes      | SPDX identifier                                                 |
| `metadata.author`  | Yes      | Author attribution                                              |
| `metadata.version` | Yes      | Semantic version for the skill definition                       |

### 2.2 Body Sections

After frontmatter, a typical skill contains:

1. **Purpose** — 2-4 sentence description of what the skill does and the agent's role
2. **What You Receive** — inputs from the orchestrator (change name, mode, artifacts)
3. **Execution and Persistence Contract** — how to read/write artifacts per mode
4. **What to Do** — numbered steps with specific instructions
5. **Rules** — MUST/MUST NOT constraints
6. **Return Format** — structured envelope the agent must return

### 2.3 Special: \_shared (Support Package)

The `_shared/` directory is **not an invokable skill**. It contains reference documents consumed by real skills:

| File                      | Purpose                                                                                                          |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `skill-resolver.md`       | Universal protocol for resolving and injecting skills into sub-agents                                            |
| `sdd-phase-common.md`     | Boilerplate shared across all SDD phase skills (skill loading, artifact retrieval, persistence, return envelope) |
| `persistence-contract.md` | Defines 4 persistence modes (engram, openspec, hybrid, none) with behavior per mode                              |
| `engram-convention.md`    | Naming rules for engram artifacts (`sdd/{change}/{type}`)                                                        |
| `openspec-convention.md`  | Filesystem paths for openspec artifacts (`openspec/changes/{change}/`)                                           |

---

## 3. Skill Resolver Protocol

Defined in `_shared/skill-resolver.md`. This is the **universal protocol** for any agent that delegates work to sub-agents.

### 3.1 Resolution Steps

1. **Obtain registry** (once per session):
   - Cache from earlier in session
   - `mem_search("skill-registry")` → `mem_get_observation(id)`
   - Fallback: read `.atl/skill-registry.md` from project root
   - No registry → warn user, proceed without skills

2. **Match relevant skills** on two dimensions:
   - **Code Context**: file extensions map to skills (`.go` → go-testing, `.tsx` → react-19, etc.)
   - **Task Context**: action type maps to skills (PR → branch-pr, review → framework skill)

3. **Inject into sub-agent prompt** as `## Project Standards (auto-resolved)` block — containing **compact rules** (5-15 lines per skill), NOT full SKILL.md paths

4. **Include Project Conventions** — paths + notes from the registry's conventions section

### 3.2 Token Budget

- 50-150 tokens per skill in compact rules
- Max 5 skill blocks per delegation (prioritize code context over task context)
- Typical delegation: ~400-600 tokens total

### 3.3 Compaction Safety

- Registry lives in engram/filesystem, not orchestrator memory
- Compact rules are copied into each sub-agent's prompt at launch
- Feedback loop: sub-agents report skill resolution status (`injected`, `fallback-registry`, `fallback-path`, `none`)
- Orchestrator self-corrects on non-`injected` reports

---

## 4. Skill Registry

Defined in `skill-registry/SKILL.md`. The registry is the **foundation of the skill resolver**.

### 4.1 Generation Process

1. **Scan user skills**: Glob `*/SKILL.md` across all known directories:
   - User-level: `~/.claude/skills/`, `~/.config/opencode/skills/`, `~/.gemini/skills/`, `~/.cursor/skills/`, `~/.copilot/skills/`, parent of skill file
   - Project-level: `.claude/skills/`, `.gemini/skills/`, `.agent/skills/`, `skills/`
   - **Skip**: `sdd-*`, `_shared`, `skill-registry` directories
   - **Deduplicate**: project-level wins over user-level

2. **Generate compact rules**: For each skill, extract 5-15 lines of actionable rules (no purpose/motivation/install steps)

3. **Scan project conventions**: Check for `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `GEMINI.md`, `copilot-instructions.md`. If an index file is found, read it and extract all referenced paths.

4. **Write registry**: Always to `.atl/skill-registry.md`. Also to engram if available.

### 4.2 Registry Format

```markdown
# Skill Registry

## User Skills

| Trigger | Skill | Path |
| ------- | ----- | ---- |

## Compact Rules

### {skill-name}

- Rule 1
- Rule 2

## Project Conventions

| File | Path | Notes |
| ---- | ---- | ----- |
```

### 4.3 Integration Points

- Called by `sdd-init` as part of project initialization
- Also callable standalone when user says "update skills" / "skill registry"
- Consumed by the Skill Resolver Protocol for every sub-agent delegation

---

## 5. AGENTS.md as Skill Index

The root `AGENTS.md` serves as a **project-level skill index** for agents working on the gentle-ai repo itself:

```markdown
# Gentle AI — Agent Skills Index

## Skills

| Skill                      | Trigger                         | Path                             |
| -------------------------- | ------------------------------- | -------------------------------- |
| `gentle-ai-issue-creation` | When creating a GitHub issue... | `skills/issue-creation/SKILL.md` |
| `gentle-ai-branch-pr`      | When creating a pull request... | `skills/branch-pr/SKILL.md`      |
```

**How it works**:

1. Agent reads `AGENTS.md` at project start
2. Checks the trigger column for the current task
3. Loads the matching SKILL.md by reading the file at the listed path
4. Follows ALL patterns and rules from the loaded skill

**Scope**: This index is for the gentle-ai project's own development workflow (issue-first enforcement). It is NOT the same as the skill registry (which is for cross-project skill injection into sub-agents).

---

## 6. Shared Conventions

### 6.1 Engram Naming Convention

All SDD artifacts follow deterministic naming:

```
title:     sdd/{change-name}/{artifact-type}
topic_key: sdd/{change-name}/{artifact-type}
type:      architecture
project:   {project-name}
```

Artifact types: `explore`, `proposal`, `spec`, `design`, `tasks`, `apply-progress`, `verify-report`, `archive-report`, `state`.

Key behavior: **upsert** — same `topic_key` + `project` overwrites previous content. No revision history.

### 6.2 OpenSpec File Convention

Filesystem structure for file-based persistence:

```
openspec/
├── config.yaml              # Project config with stack, rules, testing
├── specs/{domain}/spec.md   # Source of truth (main specs)
└── changes/{change-name}/   # Active changes
    ├── state.yaml
    ├── proposal.md
    ├── specs/{domain}/spec.md  # Delta specs
    ├── design.md
    ├── tasks.md
    └── verify-report.md
```

Archive moves changes to `openspec/changes/archive/YYYY-MM-DD-{change-name}/`.

### 6.3 Persistence Modes

| Mode       | Read                             | Write      | Files | Recovery                     |
| ---------- | -------------------------------- | ---------- | ----- | ---------------------------- |
| `engram`   | Engram                           | Engram     | Never | Cross-session via mem_search |
| `openspec` | Filesystem                       | Filesystem | Yes   | Via git                      |
| `hybrid`   | Engram (primary) + FS (fallback) | Both       | Yes   | Both                         |
| `none`     | Prompt context                   | Nowhere    | Never | None (ephemeral)             |

Default: engram if available, otherwise none.

### 6.4 SDD Phase Common Protocol

All SDD phase skills follow identical boilerplate:

- **Section A: Skill Loading** — check for injected Project Standards, fallback to registry, fallback to SKILL: Load instructions
- **Section B: Artifact Retrieval** — parallel `mem_search` → parallel `mem_get_observation` (mandatory full retrieval, not previews)
- **Section C: Artifact Persistence** — mandatory persist per mode
- **Section D: Return Envelope** — structured response with status, summary, artifacts, next_recommended, risks, skill_resolution

---

## 7. SDD Workflow Skills — Complete Catalog

### 7.1 Phase DAG

```
explore → propose → spec → design → tasks → apply → verify → archive
                    ↑                            ↓
                  onboard (linear walkthrough of full cycle)
```

### 7.2 Phase Details

| Phase   | Skill ID      | Artifact                      | Size Budget | Key Responsibility                                     |
| ------- | ------------- | ----------------------------- | ----------- | ------------------------------------------------------ |
| Explore | `sdd-explore` | `sdd/{change}/explore`        | —           | Investigate codebase, compare approaches               |
| Propose | `sdd-propose` | `sdd/{change}/proposal`       | <450 words  | Intent, scope, capabilities, rollback                  |
| Spec    | `sdd-spec`    | `sdd/{change}/spec`           | <650 words  | Delta specs with Given/When/Then scenarios             |
| Design  | `sdd-design`  | `sdd/{change}/design`         | <800 words  | Architecture decisions, file changes, testing strategy |
| Tasks   | `sdd-tasks`   | `sdd/{change}/tasks`          | <530 words  | Phase-organized implementation checklist               |
| Apply   | `sdd-apply`   | `sdd/{change}/apply-progress` | —           | Write code per specs/design, mark tasks complete       |
| Verify  | `sdd-verify`  | `sdd/{change}/verify-report`  | —           | Spec compliance matrix, test execution, verdict        |
| Archive | `sdd-archive` | `sdd/{change}/archive-report` | —           | Sync deltas to main specs, move to archive             |
| Onboard | `sdd-onboard` | —                             | —           | Guided walkthrough of full SDD cycle                   |
| Init    | `sdd-init`    | `sdd-init/{project}`          | —           | Detect stack, bootstrap persistence, build registry    |

### 7.3 Spec Phase Delta Format

Delta specs use three sections:

- **ADDED Requirements** — new behavior
- **MODIFIED Requirements** — changed behavior (MUST copy full requirement + all scenarios, then edit)
- **REMOVED Requirements** — deprecated behavior

Each requirement uses RFC 2119 keywords (MUST/SHALL/SHOULD/MAY) and Given/When/Then scenarios.

---

## 8. TDD Enforcement

### 8.1 Strict TDD Mode

Resolved by `sdd-init` via priority chain:

1. System prompt / agent config marker (highest)
2. `openspec/config.yaml` → `strict_tdd` field
3. Default: `true` if test runner detected
4. `false` if no test runner exists

### 8.2 Apply Phase (strict-tdd.md)

When Strict TDD is active, the standard workflow is **replaced entirely** by the TDD module:

```
FOR EACH TASK:
├── 0. SAFETY NET — run existing tests, capture baseline
├── 1. UNDERSTAND — read spec scenarios, design, existing code
├── 2. RED — write failing test FIRST
├── 3. GREEN — write minimum code to pass
├── 4. TRIANGULATE — add edge case tests
├── 5. REFACTOR — clean up, tests stay green
└── Record TDD Cycle Evidence table
```

**Hard Gate**: apply phase MUST produce a TDD Cycle Evidence table. Verify phase will reject if missing.

**No silent fallback**: if Strict TDD is resolved as active, the agent follows it or reports failure. It does NOT quietly switch to Standard Mode.

### 8.3 Verify Phase (strict-tdd-verify.md)

Additional verification steps when Strict TDD is active:

- **Step 5a**: TDD Compliance Check — verify apply-progress evidence against actual files
- **Step 5d expanded**: Per-file coverage for changed files, uncovered line ranges
- **Step 5e**: Quality Metrics — test-to-production code ratio, assertion density
- **Step 7a**: Test Layer Validation — distribution across unit/integration/e2e

When Strict TDD is NOT active: `strict-tdd-verify.md` is **never loaded** — zero tokens consumed.

---

## 9. inject.go — Deployment Mechanism

### 9.1 How Skills Reach Agents

File: `internal/components/skills/inject.go`

```go
func Inject(homeDir string, adapter agents.Adapter, skillIDs []model.SkillID) (InjectionResult, error)
```

The mechanism:

1. **Skills are embedded** in the Go binary via `internal/assets/` (using `//go:embed`)
2. **At install time**, `Inject()` is called with a list of skill IDs
3. For each skill ID, it reads the embedded asset at `skills/{id}/SKILL.md`
4. It writes the file to `{adapter.SkillsDir(homeDir)}/{id}/SKILL.md`
5. Uses `filemerge.WriteFileAtomic()` for safe writes (no partial writes)

### 9.2 SDD Skill Separation

SDD skills (`sdd-*` prefix) are **intentionally skipped** by the skills component:

```go
func isSDDSkill(id model.SkillID) bool {
    return strings.HasPrefix(string(id), "sdd-")
}
```

The SDD component installs its own skills separately. This prevents write conflicts when both the skills and SDD components are selected together.

### 9.3 Agent Adapter Pattern

Each agent type implements `agents.Adapter` with a `SkillsDir(homeDir)` method that returns the path where that agent expects skills. The inject function uses this path — no agent-specific switch statements needed.

### 9.4 Error Handling

- Missing embedded asset → log warning, skip skill, continue
- Empty embedded asset → return error (corrupt build)
- Write failure → return error (abort entire injection)
- Adapter doesn't support skills → skip all, return success

---

## 10. Judgment-Day Skill

### 10.1 What It Is

A **parallel adversarial review protocol** that launches two independent blind judge sub-agents to review the same target simultaneously.

### 10.2 Protocol

1. **Resolve skills** via Skill Resolver Protocol (Pattern 0) — inject Project Standards into all sub-agent prompts
2. **Launch Judge A + Judge B in parallel** — identical criteria, independent execution
3. **Synthesize verdict**: classify findings as Confirmed (both), Suspect (one), or Contradiction (disagree)
4. **Warning classification**: real (triggers in normal usage) vs theoretical (contrived scenario)
5. **Fix and re-judge**: if confirmed CRITICALs or real WARNINGs → delegate Fix Agent → re-launch both judges
6. **Convergence**: after Round 1, only re-judge for confirmed CRITICALs. Real WARNINGs fixed inline without re-judge.
7. **Terminal states**: APPROVED (both judges clean) or ESCALATED (user chose to stop)

### 10.3 Blocking Rules

- MUST NOT declare APPROVED until judges return clean
- MUST NOT push/commit after fixes until re-judgment completes
- MUST NOT save session summary until every JD reaches terminal state
- Fix Agent is a separate delegation — never use a judge as the fixer

---

## 11. Complete Skill Catalog

### 11.1 SDD Workflow Skills (9 + init)

| Skill ID      | Version | Role               | Artifact Type                 |
| ------------- | ------- | ------------------ | ----------------------------- |
| `sdd-init`    | 3.0     | Bootstrap          | `sdd-init/{project}`          |
| `sdd-explore` | 2.0     | Investigation      | `sdd/{change}/explore`        |
| `sdd-propose` | 2.0     | Planning           | `sdd/{change}/proposal`       |
| `sdd-spec`    | 2.0     | Specification      | `sdd/{change}/spec`           |
| `sdd-design`  | 2.0     | Architecture       | `sdd/{change}/design`         |
| `sdd-tasks`   | 2.0     | Breakdown          | `sdd/{change}/tasks`          |
| `sdd-apply`   | 3.0     | Implementation     | `sdd/{change}/apply-progress` |
| `sdd-verify`  | 3.0     | Verification       | `sdd/{change}/verify-report`  |
| `sdd-archive` | 2.0     | Closure            | `sdd/{change}/archive-report` |
| `sdd-onboard` | 1.0     | Guided walkthrough | —                             |

### 11.2 Project Skills

| Skill ID         | Version | Trigger                                              | License    |
| ---------------- | ------- | ---------------------------------------------------- | ---------- |
| `go-testing`     | 1.0     | Writing Go tests, teatest, test coverage             | Apache-2.0 |
| `branch-pr`      | 2.0     | Creating a PR, preparing changes for review          | Apache-2.0 |
| `issue-creation` | 1.0     | Creating a GitHub issue, bug report, feature request | Apache-2.0 |
| `judgment-day`   | 1.4     | "judgment day", adversarial review, dual review      | Apache-2.0 |

### 11.3 Infrastructure Skills

| Skill ID         | Role                                                                |
| ---------------- | ------------------------------------------------------------------- |
| `skill-registry` | Builds the compact rules registry from all discovered skills        |
| `_shared`        | Support package (not invokable) — shared conventions for SDD skills |

---

## 12. Loading Protocol Summary

```
┌─────────────────────────────────────────────────────────────┐
│                    SKILL LIFECYCLE                          │
│                                                             │
│  1. BUILD: SKILL.md files embedded in Go binary             │
│     └─ internal/assets/skills/{id}/SKILL.md                │
│                                                             │
│  2. INSTALL: inject.go writes to agent skills directories   │
│     └─ {adapter.SkillsDir()}/{id}/SKILL.md                 │
│     └─ SDD skills handled separately by SDD component      │
│                                                             │
│  3. INDEX: skill-registry scans all skill dirs              │
│     └─ Produces .atl/skill-registry.md                      │
│     └─ Compact rules: 5-15 lines per skill                  │
│     └─ Also saved to engram if available                    │
│                                                             │
│  4. RESOLVE: skill-resolver matches by code+task context    │
│     └─ Sub-agents receive pre-injected compact rules        │
│     └─ Fallback chain: injected → registry → SKILL: Load   │
│                                                             │
│  5. EXECUTE: agent follows skill instructions               │
│     └─ Skill loading (Section A) per sdd-phase-common       │
│     └─ Artifact I/O per persistence-contract                │
│     └─ Return envelope with skill_resolution status         │
│                                                             │
│  6. FEEDBACK: orchestrator corrects on non-injected reports │
│     └─ Re-reads registry, re-injects for future delegations │
└─────────────────────────────────────────────────────────────┘
```

---

## 13. Key Architectural Decisions

1. **Compact rules over full SKILL.md** — sub-agents receive 5-15 line summaries, not full skill files. Build-time cost (reading all skills) vs runtime cost (cheap injection).

2. **Upsert semantics for engram** — `topic_key` enables idempotent saves. No duplicate artifacts, but no revision history either.

3. **SDD skills separate from project skills** — inject.go skips `sdd-*` prefix. The SDD component owns its own installation lifecycle.

4. **4 persistence modes** — engram (fast, local, no history), openspec (git-friendly, team-shareable), hybrid (both), none (ephemeral). Default: engram if available.

5. **Strict TDD as opt-out, not opt-in** — if a test runner is detected and no config says otherwise, TDD is enabled by default. The strict-tdd.md module is only loaded when active (zero token cost when inactive).

6. **Agent adapter pattern** — `adapter.SkillsDir(homeDir)` abstracts per-agent paths. No switch statements in inject.go.

7. **Judgment-day adversarial review** — two blind judges + convergence threshold + user-controlled iteration limit. Prevents both false positives (nit-picking loops) and false negatives (single-reviewer blind spots).
