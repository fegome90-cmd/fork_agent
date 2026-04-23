# Spec-Kit Deep-Dive Research Report

**Source**: GitHub `spec-kit` (github/spec-kit)  
**Date**: 2026-04-23  
**Files Analyzed**: 20 (README, methodology, AGENTS.md, 8 templates, 8 commands, 4 architecture docs)

---

## Table of Contents

1. [Core Philosophy](#1-core-philosophy)
2. [Spec Lifecycle](#2-spec-lifecycle-constitution--specify--clarify--plan--tasks--implement--verify)
3. [Constitution System](#3-constitution-system)
4. [Template Formats & Sections](#4-template-formats--sections)
5. [Command Architecture](#5-command-architecture)
6. [Validation & Quality Gates](#6-validation--quality-gates)
7. [Extension System](#7-extension-system)
8. [Preset System](#8-preset-system)
9. [Workflow Engine](#9-workflow-engine)
10. [Integration Architecture (30+ AI Agents)](#10-integration-architecture-30-ai-agents)
11. [Relationship Map: Artifacts](#11-relationship-map-artifacts)
12. [Key Design Patterns & Observations](#12-key-design-patterns--observations)

---

## 1. Core Philosophy

**Spec-Driven Development (SDD)** inverts traditional development: specifications generate code, not the reverse.

### Core Principles

| Principle | Description |
|-----------|-------------|
| **Specifications as Lingua Franca** | Spec is the primary artifact; code is its expression in a language/framework |
| **Executable Specifications** | Specs must be precise, complete, unambiguous enough to generate working systems |
| **Continuous Refinement** | Validation is ongoing, not a one-time gate |
| **Research-Driven Context** | Research agents gather context throughout (lib compat, perf, security) |
| **Bidirectional Feedback** | Production reality informs spec evolution |
| **Branching for Exploration** | Multiple implementations from same spec for different optimization targets |
| **Intent-Driven Development** | Natural language intent → spec → code |

### The "Power Inversion"

Traditional: Code is king, specs are scaffolding  
SDD: Specs are king, code is generated output

> "The PRD isn't a guide for implementation; it's the source that generates implementation."

### Three Development Phases

| Phase | Focus |
|-------|-------|
| 0-to-1 (Greenfield) | Generate from scratch |
| Creative Exploration | Parallel implementations, diverse solutions |
| Iterative Enhancement (Brownfield) | Add features iteratively, modernize legacy |

---

## 2. Spec Lifecycle: Constitution → Specify → Clarify → Plan → Tasks → Implement → Verify

The complete lifecycle follows this sequence:

```
1. constitution  →  Establish project principles
2. specify       →  Create feature spec (WHAT + WHY, no HOW)
3. clarify       →  Resolve ambiguities (up to 5 targeted questions)
4. plan          →  Technical implementation plan (tech stack, architecture)
5. tasks         →  Break plan into actionable, ordered tasks
6. analyze       →  Cross-artifact consistency check (READ-ONLY)
7. checklist     →  Generate quality checklists ("unit tests for English")
8. implement     →  Execute tasks, build the feature
```

### Lifecycle Detail per Command

#### `/speckit.constitution` — Foundation
- Creates/updates `.specify/memory/constitution.md`
- Fills template placeholders with project-specific principles
- Propagates changes to all dependent templates
- Generates a Sync Impact Report (version change, modified principles, template status)
- Follows semver for constitution versions (MAJOR/MINOR/PATCH)

#### `/speckit.specify` — Feature Spec Creation
- Takes natural language feature description as input
- Auto-generates short name (2-4 words)
- Creates branch (via extension hook or auto-numbering)
- Creates `specs/NNN-feature-name/spec.md` from template
- Fills: User Stories (prioritized P1/P2/P3), Functional Requirements (FR-NNN), Key Entities, Success Criteria (SC-NNN), Assumptions
- Runs quality validation against checklist
- Max 3 `[NEEDS CLARIFICATION]` markers
- Outputs to `specs/NNN-feature-name/checklists/requirements.md`

#### `/speckit.clarify` — Ambiguity Resolution
- Runs BEFORE `/speckit.plan`
- Uses a 10-category ambiguity taxonomy (Functional Scope, Domain & Data, Interaction/UX, Non-Functional, Integration, Edge Cases, Constraints, Terminology, Completion Signals, Misc/Placeholders)
- Max 5 sequential questions, one at a time
- Each question: recommended option + alternatives table
- Answers written back into spec incrementally under `## Clarifications` → `### Session YYYY-MM-DD`
- Updates affected spec sections (FRs, User Stories, Data Model, Success Criteria, Edge Cases)
- Coverage summary at end: Resolved / Deferred / Clear / Outstanding

#### `/speckit.plan` — Technical Planning
- Phase 0: Research — resolve all NEEDS CLARIFICATION, research tech options
- Phase 1: Design — data-model.md, contracts/, quickstart.md
- Fills Technical Context (language, deps, storage, testing, platform, constraints)
- Runs Constitution Check gates (Simplicity Gate, Anti-Abstraction Gate, Integration-First Gate)
- Complexity Tracking table for justified violations
- Updates agent context file between `<!-- SPECKIT START -->` markers

#### `/speckit.tasks` — Task Breakdown
- Reads plan.md (required), spec.md (required), data-model.md, contracts/, research.md
- Organized by User Story (P1 → P2 → P3)
- Strict format: `- [ ] T001 [P?] [US1] Description with file path`
- Phase structure: Setup → Foundational (blocking) → User Story N → Polish
- `[P]` = parallelizable, `[US1]` = maps to user story
- Tests OPTIONAL unless explicitly requested
- MVP-first strategy: complete User Story 1 independently

#### `/speckit.analyze` — Cross-Artifact Consistency
- READ-ONLY: never modifies files
- Compares spec.md ↔ plan.md ↔ tasks.md against constitution
- 6 detection passes: Duplication, Ambiguity, Underspecification, Constitution Alignment, Coverage Gaps, Inconsistency
- Severity: CRITICAL / HIGH / MEDIUM / LOW
- Output: Findings table, Coverage Summary, Metrics (coverage %, ambiguity count, etc.)
- Constitution violations are always CRITICAL

#### `/speckit.checklist` — Requirements Quality ("Unit Tests for English")
- Tests the REQUIREMENTS, not the implementation
- Categories: Completeness, Clarity, Consistency, Measurability, Coverage, Edge Cases
- Items are questions: "Are error handling requirements defined for all API failure modes?"
- NOT: "Verify the button clicks correctly"
- Stored in `specs/NNN-feature/checklists/<domain>.md`
- Appends to existing checklists, never replaces

#### `/speckit.implement` — Execution
- Checks checklist completion status first (gate)
- Loads all context: tasks.md, plan.md, data-model.md, contracts/, research.md, quickstart.md
- Creates/verifies ignore files (.gitignore, .dockerignore, etc.) based on tech stack
- Executes phase-by-phase: Setup → Tests → Core → Integration → Polish
- Marks completed tasks as `[X]` in tasks.md
- Handles parallel [P] tasks appropriately

---

## 3. Constitution System

### Purpose
The constitution is the **architectural DNA** of the project — immutable principles that govern how specs become code.

### File Location
`.specify/memory/constitution.md`

### Template Structure
```markdown
# [PROJECT_NAME] Constitution

## Core Principles
### [PRINCIPLE_1_NAME]        (e.g., I. Library-First)
[Description with MUST/SHOULD statements]

## [SECTION_2_NAME]          (e.g., Additional Constraints)
## [SECTION_3_NAME]          (e.g., Development Workflow)
## Governance

**Version**: X.Y.Z | **Ratified**: YYYY-MM-DD | **Last Amended**: YYYY-MM-DD
```

### The "Nine Articles" (from spec-driven.md)

| Article | Name | Rule |
|---------|------|------|
| I | Library-First | Every feature starts as standalone library |
| II | CLI Interface | Every library exposes CLI (text in/out) |
| III | Test-First (NON-NEGOTIABLE) | TDD mandatory: Red → Green → Refactor |
| IV | Integration Testing | Focus on contract tests, inter-service, shared schemas |
| V | Observability | Text I/O, structured logging |
| VI | Versioning | MAJOR.MINOR.BUILD, breaking changes policy |
| VII | Simplicity | ≤3 projects initially, YAGNI |
| VIII | Anti-Abstraction | Use framework directly, no wrapper layers |
| IX | Integration-First Testing | Real DBs over mocks, actual services over stubs |

### Constitutional Enforcement
- Plan template has "Phase -1: Pre-Implementation Gates" with explicit checkpoints
- Constitution Check section in plan.md re-evaluated after Phase 1 design
- `/speckit.analyze` treats constitution violations as CRITICAL (non-negotiable)
- Complexity Tracking table required for any justified gate violation

### Version Semantics
- MAJOR: Backward incompatible principle removal/redefinitions
- MINOR: New principle/section or materially expanded guidance
- PATCH: Clarifications, wording fixes, non-semantic refinements

### Sync Propagation
When constitution changes:
1. plan-template.md Constitution Check must align
2. spec-template.md scope/requirements must align
3. tasks-template.md must reflect principle-driven task types
4. All command files checked for outdated references
5. Runtime guidance docs updated
6. Sync Impact Report prepended as HTML comment

---

## 4. Template Formats & Sections

### spec-template.md — Feature Specification

**Mandatory Sections:**
1. **User Scenarios & Testing** — Prioritized user stories (P1/P2/P3) with Given/When/Then acceptance scenarios
2. **Edge Cases** — Boundary conditions and error scenarios
3. **Requirements** — Functional Requirements (FR-NNN), Key Entities
4. **Success Criteria** — Measurable, technology-agnostic outcomes (SC-NNN)

**Optional Sections:**
- Assumptions
- Clarifications (added by `/speckit.clarify`)

**Key Rules:**
- Focus on WHAT + WHY, never HOW
- Max 3 `[NEEDS CLARIFICATION]` markers
- Written for business stakeholders
- Each user story is independently testable/deployable (MVP slices)

### plan-template.md — Implementation Plan

**Sections:**
1. **Summary** — Extracted from spec
2. **Technical Context** — Language, deps, storage, testing, platform, constraints
3. **Constitution Check** — Gate results (Simplicity, Anti-Abstraction, Integration-First)
4. **Project Structure** — Single project / Web app / Mobile+API options
5. **Complexity Tracking** — Justified violations table

**Generated Artifacts (by `/speckit.plan`):**
- `research.md` — Decision/Rationale/Alternatives
- `data-model.md` — Entities, fields, relationships, validation rules
- `contracts/` — API specs, interface definitions
- `quickstart.md` — Key validation scenarios

### tasks-template.md — Task Breakdown

**Format:** `- [ ] T001 [P?] [Story?] Description with file path`

**Phase Structure:**
1. Setup — Project initialization
2. Foundational — Blocking prerequisites (MUST complete before user stories)
3. User Story N (one per priority) — Tests → Models → Services → Endpoints
4. Polish — Cross-cutting concerns

**Key Rules:**
- Tasks organized by user story for independent implementation
- `[P]` = parallelizable (different files, no dependencies)
- `[US1]` label maps to user story for traceability
- Tests OPTIONAL unless explicitly requested
- MVP = User Story 1 only

### checklist-template.md — Requirements Quality

**Purpose:** "Unit tests for English" — validates REQUIREMENTS quality, not implementation

**Categories:**
- Requirement Completeness
- Requirement Clarity
- Requirement Consistency
- Acceptance Criteria Quality
- Scenario Coverage
- Edge Case Coverage
- Non-Functional Requirements
- Dependencies & Assumptions

**Item Format:** `- [ ] CHK### Question about requirement quality [Dimension, Spec §X.Y]`

### constitution-template.md — Project Principles

Placeholder-based template with:
- Core Principles (variable count)
- Additional sections (constraints, workflow, etc.)
- Governance (amendment process, versioning)
- Version/Ratified/Last Amended metadata

---

## 5. Command Architecture

### Common Pattern

Every command follows this lifecycle:

```
1. Pre-Execution Checks → Extension hooks (before_*)
2. Outline              → Main execution logic
3. Post-Execution Checks → Extension hooks (after_*)
```

### Hook System

Defined in `.specify/extensions.yml`:

```yaml
hooks:
  before_specify:
    - extension: git-extension
      command: speckit.git.create-branch
      optional: false    # mandatory = auto-execute
      description: "..."
      prompt: "..."
  after_specify:
    - extension: ...
```

**Hook Types:**
- `optional: true` → Presented as suggestion, user chooses
- `optional: false` → Automatically executed, agent waits for result

**Hook Events:** `before_specify`, `after_specify`, `before_clarify`, `after_clarify`, `before_plan`, `after_plan`, `before_tasks`, `after_tasks`, `before_implement`, `after_implement`, `before_analyze`, `after_analyze`, `before_checklist`, `after_checklist`, `before_constitution`, `after_constitution`

### Handoff System

Commands declare handoffs in frontmatter:

```yaml
handoffs:
  - label: Build Technical Plan
    agent: speckit.plan
    prompt: Create a plan for the spec. I am building with...
    send: true    # auto-send to next agent
```

### Script Integration

Commands run prerequisite scripts:

```yaml
scripts:
  sh: scripts/bash/check-prerequisites.sh --json --paths-only
  ps: scripts/powershell/check-prerequisites.ps1 -Json -PathsOnly
```

Script output provides: `FEATURE_DIR`, `FEATURE_SPEC`, `IMPL_PLAN`, `TASKS`, `BRANCH`

### Argument Patterns

| Agent Format | Placeholder |
|-------------|-------------|
| Markdown | `$ARGUMENTS` |
| TOML (Gemini) | `{{args}}` |
| YAML (Goose) | `{{args}}` |
| Forge | `{{parameters}}` |
| Script paths | `{SCRIPT}` |
| Agent name | `__AGENT__` |

---

## 6. Validation & Quality Gates

### Multi-Layered Validation

```
Layer 1: Spec Quality Checklist (inside /speckit.specify)
  ↓
Layer 2: Clarification Coverage (inside /speckit.clarify)
  ↓
Layer 3: Constitution Gates (inside /speckit.plan)
  ↓
Layer 4: Cross-Artifact Analysis (/speckit.analyze)
  ↓
Layer 5: Requirements Quality Checklists (/speckit.checklist)
  ↓
Layer 6: Checklist Gate (inside /speckit.implement)
```

### Constitution Gates (Phase -1)

| Gate | Article | Checks |
|------|---------|--------|
| Simplicity Gate | VII | ≤3 projects? No future-proofing? |
| Anti-Abstraction Gate | VIII | Using framework directly? Single model representation? |
| Integration-First Gate | IX | Contracts defined? Contract tests written? |

### `/speckit.analyze` Detection Passes

1. **Duplication Detection** — Near-duplicate requirements
2. **Ambiguity Detection** — Vague adjectives ("fast", "scalable") without metrics
3. **Underspecification** — Missing objects/outcomes, undefined file references
4. **Constitution Alignment** — Conflicts with MUST principles
5. **Coverage Gaps** — Requirements with zero tasks, tasks with no requirements
6. **Inconsistency** — Terminology drift, conflicting specs

### Severity Heuristic

| Level | Criteria |
|-------|----------|
| CRITICAL | Constitution MUST violation, missing core artifact, zero-coverage requirement |
| HIGH | Duplicate/conflicting requirement, ambiguous security/perf, untestable criterion |
| MEDIUM | Terminology drift, missing NFR task coverage, underspecified edge case |
| LOW | Style improvements, minor redundancy |

### Checklist Philosophy

> "If your spec is code written in English, the checklist is its unit test suite."

**Tests requirements quality, NOT implementation correctness.**

---

## 7. Extension System

### Purpose
Extensions add new capabilities (new commands, workflows, integrations) beyond core SDD.

### Installation
```bash
specify extension add <name>
```

### Extension Categories

| Category | Description | Effect |
|----------|-------------|--------|
| `docs` | Read/validate/generate spec artifacts | Read-only or Read+Write |
| `code` | Review/validate/modify source code | Read-only or Read+Write |
| `process` | Orchestrate workflow across phases | Read+Write |
| `integration` | Sync with external platforms | Read+Write |
| `visibility` | Report project health/progress | Read-only |

### Notable Extensions (60+ community)

| Extension | Purpose |
|-----------|---------|
| spec-kit-jira | Sync Jira Epics/Stories from specs |
| spec-kit-verify | Post-impl quality gate vs spec |
| spec-kit-worktree | Git worktree isolation for parallel dev |
| spec-kit-maqa | Multi-agent QA with parallel worktrees |
| spec-kit-canon | Canon-driven (baseline) workflows |
| spec-kit-bugfix | Structured bugfix workflow |
| spec-kit-doctor | Project health diagnostics |
| spec-kit-pr-bridge | Auto-generate PR descriptions from specs |

### Hook Integration

Extensions register hooks in `.specify/extensions.yml`:

```yaml
hooks:
  before_specify:
    - extension: git-extension
      command: speckit.git.create-branch
      optional: false
      condition: "git.is_clean"    # evaluated by HookExecutor
```

Commands check hooks at pre/post execution. Hooks can be:
- **Mandatory** (`optional: false`): Auto-executed, blocks command
- **Optional** (`optional: true`): Presented as suggestion
- **Conditional**: `condition` field evaluated by HookExecutor implementation

---

## 8. Preset System

### Purpose
Presets customize HOW Spec Kit works — override templates, commands, terminology without adding new capabilities.

### Installation
```bash
specify preset add <name> --priority N
```

### Template Resolution (Priority Stack)

| Priority | Source | Path |
|----------|--------|------|
| 1 (highest) | Project Override | `.specify/templates/overrides/` |
| 2 | Preset | `.specify/presets/<id>/templates/` |
| 3 | Extension | `.specify/extensions/<id>/templates/` |
| 4 (lowest) | Core | `.specify/templates/` |

**Resolution**: Walk top-down, return first match. Multiple presets sorted by `priority` field.

### Command Registration

Presets with `type: command` entries register into all detected agent directories:

```mermaid
preset add → detect agents → render per format → write to agent dirs
```

**Agent Format Rendering:**
- Claude/Cursor/Windsurf → `.md` with `$ARGUMENTS`
- Copilot → `.agent.md` + `.prompt.md`
- Gemini/Qwen/Tabnine → `.toml` with `{{args}}`

**Safety**: Extension commands (3+ dot segments like `speckit.myext.cmd`) only registered if extension is installed.

### Cleanup
`specify preset remove` deletes registered command files from agent directories, restoring next-highest-priority version.

### When to Use What

| Goal | Use |
|------|-----|
| Add new command/workflow | Extension |
| Customize spec/plan/tasks format | Preset |
| Integrate external tool | Extension |
| Enforce organizational standards | Preset |
| One-off project tweak | Project Override (`.specify/templates/overrides/`) |

---

## 9. Workflow Engine

### Purpose
Automate multi-step SDD processes — chain commands, prompts, shell steps, human checkpoints into repeatable sequences.

### Built-in Workflow: Full SDD Cycle

```yaml
specify → gate(review spec) → plan → gate(review plan) → tasks → implement
```

### Step Types (10 built-in)

| Type | Purpose | Returns next_steps? |
|------|---------|---------------------|
| `command` | Invoke Spec Kit command | No |
| `prompt` | Send arbitrary prompt | No |
| `shell` | Run shell command | No |
| `gate` | Human review/approval | No (pauses) |
| `if` | Conditional branching | Yes |
| `switch` | Multi-branch dispatch | Yes |
| `while` | Loop while true | Yes |
| `do-while` | Loop, at least once | Yes |
| `fan-out` | Dispatch per item | No (engine expands) |
| `fan-in` | Aggregate fan-out results | No |

### Expression Engine

Jinja2-like `{{ expression }}` syntax supporting:
- Variable access: `{{ inputs.name }}`
- Step outputs: `{{ steps.plan.output.file }}`
- Comparisons, boolean logic, membership
- Filters: `default`, `join`, `contains`, `map`

### State Persistence & Resume

- State saved after each step
- `specify workflow resume <run_id>` continues from exact point
- States: CREATED → RUNNING → COMPLETED / PAUSED / FAILED / ABORTED
- Run state at `.specify/workflows/runs/<run_id>/state.json`

### Catalog System

Resolution order:
1. `SPECKIT_WORKFLOW_CATALOG_URL` env var (overrides all)
2. `.specify/workflow-catalogs.yml` (project)
3. `~/.specify/workflow-catalogs.yml` (user)
4. Built-in defaults (official + community)

1-hour cache, per-URL, SHA256-hashed.

---

## 10. Integration Architecture (30+ AI Agents)

### Base Classes

| Base Class | Use For | Command Format |
|------------|---------|----------------|
| `MarkdownIntegration` | Standard `.md` commands | Markdown with `$ARGUMENTS` |
| `TomlIntegration` | TOML-format commands | TOML with `{{args}}` |
| `YamlIntegration` | YAML recipe files | YAML with `{{args}}` |
| `SkillsIntegration` | Skill directories | `speckit-<name>/SKILL.md` |
| `IntegrationBase` | Fully custom | Custom |

### Registry Pattern

```
INTEGRATION_REGISTRY (singleton)
  ├── _register_builtins() → import + _register() each integration
  └── Per-integration: key, config, registrar_config, context_file
```

### Integration Subpackage Structure

```
src/specify_cli/integrations/<key>/
├── __init__.py        # <Agent>Integration class
└── scripts/
    ├── update-context.sh    # Delegates to shared script
    └── update-context.ps1   # Delegates to shared script
```

### Key Design Rules

- CLI-based agents: `key` must match executable name (for `shutil.which()`)
- IDE-based agents: use canonical identifier
- Context file varies: `CLAUDE.md`, `GEMINI.md`, `AGENTS.md`, `.github/copilot-instructions.md`, etc.

### Special Processing

| Agent | Custom Logic |
|-------|-------------|
| Copilot | `.agent.md` + `.prompt.md` companions, VS Code settings merge |
| Forge | `{{parameters}}` instead of `$ARGUMENTS`, strips `handoffs` frontmatter |
| Goose | YAML recipe format with Block's recipe system |
| Codex | Skills-based (`speckit-<name>/SKILL.md`) |

### File Tracking

`IntegrationManifest` tracks all installed files per integration for clean uninstall.

---

## 11. Relationship Map: Artifacts

```
constitution.md ──────────────────────────────────────────────────────┐
   │ (governs all)                                                      │
   ▼                                                                    │
spec.md ◄── clarify ──► Clarifications section                        │
   │                                                                   │
   ├── plan.md ◄── plan command                                        │
   │     ├── research.md      (Phase 0)                                │
   │     ├── data-model.md    (Phase 1)                                │
   │     ├── contracts/       (Phase 1)                                │
   │     └── quickstart.md    (Phase 1)                                │
   │                                                                   │
   ├── tasks.md ◄── tasks command                                      │
   │     └── references plan.md + spec.md + data-model.md + contracts/ │
   │                                                                   │
   ├── checklists/ ◄── checklist command                               │
   │     ├── requirements.md  (from specify)                           │
   │     ├── ux.md                                                     │
   │     ├── security.md                                               │
   │     └── ...                                                       │
   │                                                                   │
   └── analyze ◄── reads all three (spec + plan + tasks)               │
         └── Output: findings table, coverage metrics                  │
                                                                       │
   implement ◄── reads tasks.md + plan.md + all design docs            │
         └── checks checklists/ gate                                   │
                                                                       │
   constitution check ─────────────────────────────────────────────────┘
```

### File Location Convention

```
.specify/
├── memory/
│   └── constitution.md
├── templates/
│   ├── spec-template.md
│   ├── plan-template.md
│   ├── tasks-template.md
│   ├── checklist-template.md
│   ├── constitution-template.md
│   ├── commands/
│   │   ├── specify.md
│   │   ├── clarify.md
│   │   ├── plan.md
│   │   ├── tasks.md
│   │   ├── implement.md
│   │   ├── analyze.md
│   │   ├── checklist.md
│   │   └── constitution.md
│   └── overrides/              (project-local, highest priority)
├── extensions/
│   └── <ext-id>/
│       └── templates/
├── presets/
│   └── <preset-id>/
│       └── templates/
├── scripts/
│   ├── bash/
│   └── powershell/
├── extensions.yml              (hook definitions)
├── feature.json                (current feature directory)
├── init-options.json           (branch numbering strategy)
└── workflows/
    ├── workflow-registry.json
    ├── runs/<run_id>/
    └── .cache/

specs/
└── NNN-feature-name/
    ├── spec.md
    ├── plan.md
    ├── research.md
    ├── data-model.md
    ├── quickstart.md
    ├── contracts/
    ├── tasks.md
    └── checklists/
        ├── requirements.md
        ├── ux.md
        └── ...
```

---

## 12. Key Design Patterns & Observations

### Template as Prompt Engineering

Templates are sophisticated prompts that constrain LLM behavior:
1. **Prevent premature implementation** — Explicit WHAT/WHY vs HOW separation
2. **Force uncertainty markers** — `[NEEDS CLARIFICATION]` prevents guessing
3. **Structured self-review** — Checklists act as "unit tests for specs"
4. **Constitutional gates** — Over-engineering requires explicit justification
5. **Hierarchical detail** — Main docs stay readable, complexity in separate files
6. **Test-first thinking** — Contract → Integration → E2E → Unit ordering
7. **Anti-speculative** — No "might need" features, everything traces to user stories

### Progressive Disclosure

- Spec: business-level, no tech
- Plan: high-level tech, details in separate files
- Tasks: actionable, with exact file paths
- Analyze: read-only, only surfaces findings
- Checklist: questions about requirements, not implementation

### Agent-Agnostic Design

The system supports 30+ AI agents through:
- Integration registry pattern (base class hierarchy)
- Format-specific renderers (Markdown, TOML, YAML, Skills)
- Shared script infrastructure (bash + PowerShell)
- `feature.json` for cross-command feature discovery
- Agent-specific context files (`CLAUDE.md`, `AGENTS.md`, etc.)

### Extension Safety

- Extension commands only registered if extension installed
- Hook conditions evaluated by implementation, not by command
- Invalid YAML silently skipped (no cascade failures)
- Optional hooks don't block, mandatory hooks auto-execute and block

### Task Independence

Every user story is designed to be:
- Independently implementable
- Independently testable
- Independently deployable
- An MVP slice (P1 = minimum viable product)

### Separation of Concerns

| Concern | Tool |
|---------|------|
| Requirements quality | `/speckit.checklist` |
| Cross-artifact consistency | `/speckit.analyze` |
| Ambiguity resolution | `/speckit.clarify` |
| Constitutional compliance | Gates in `/speckit.plan` |
| Implementation correctness | `/speckit.implement` |

### Stateless Command Design

Each command:
1. Runs prerequisites script to discover context
2. Loads only needed artifacts
3. Performs its specific function
4. Reports results
5. Triggers hooks

No command maintains internal state between runs. State lives in:
- File system (specs, plans, tasks)
- `.specify/feature.json` (feature discovery)
- Workflow run state (`state.json`)
