## Status: success
## Summary: Complete SDD orchestrator system spec across 7 agent variants, 14 source files analyzed. The system defines a universal DAG of 9 phases with 4 execution modes (sub-agent, inline, multi-agent, solo), a 4-tier persistence contract, mandatory TDD enforcement via orchestrator injection, and a Go injection layer that wires ~500 LOC per agent via adapter interfaces.
## Artifacts: /tmp/fork-ga-sdd.md

---

# SDD Orchestrator System — Technical Specification

> gentle-ai `internal/assets/` and `internal/components/sdd/`
> 14 files analyzed, 7 agent variants documented

---

## 1. Base SDD Orchestrator Structure

### 1.1 Phase DAG

```
proposal -> specs --> tasks -> apply -> verify -> archive
             ^
             |
           design
```

9 phases total: `explore`, `propose`, `spec`, `design`, `tasks`, `apply`, `verify`, `archive`, `onboard`.

### 1.2 Commands

| Type | Commands | Execution |
|------|----------|-----------|
| **Skills** (autocomplete) | `/sdd-init`, `/sdd-explore`, `/sdd-apply`, `/sdd-verify`, `/sdd-archive`, `/sdd-onboard` | Phase executor |
| **Meta-commands** (orchestrator-only) | `/sdd-new`, `/sdd-continue`, `/sdd-ff` | Orchestrator handles, NOT skills |

### 1.3 Init Guard (MANDATORY)

Every SDD command checks `sdd-init/{project}` in Engram. If not found, `sdd-init` runs automatically before the requested command. This caches:
- Testing capabilities (runner, layers, coverage, quality tools)
- Strict TDD Mode status
- Project context (stack, conventions, architecture)

### 1.4 Result Contract

Every phase returns: `status`, `executive_summary`, `artifacts`, `next_recommended`, `risks`, `skill_resolution`.

### 1.5 Execution Modes

| Mode | Behavior |
|------|----------|
| `auto` | All phases back-to-back without pausing |
| `interactive` | Pause after each phase, show summary, ask "Continue?" |

Default: `interactive`. Cached per session.

### 1.6 Size Classification (Kiro + Windsurf only)

| Size | Threshold | Workflow |
|------|-----------|----------|
| Small | <50 lines, single file | Direct — no SDD |
| Medium | 50-300 lines | Native spec generation → approval → implement |
| Large | >300 lines or user says "use SDD" | Full SDD pipeline |

---

## 2. Agent Variant Comparison

### 2.1 Execution Architecture

| Agent | Execution Model | Sub-agents | Convention Path |
|-------|----------------|------------|-----------------|
| **Generic** (Claude) | Sub-agent delegation via Agent tool | ✅ async/sync | `~/.claude/skills/_shared/` |
| **Antigravity** (Gemini/Mission Control) | Inline + built-in Browser/Terminal | ❌ inline only | `~/.gemini/antigravity/skills/_shared/` |
| **Claude** | Sub-agent delegation (Agent tool) | ✅ async/sync | `~/.claude/skills/_shared/` |
| **Cursor** | Native sub-agents via `~/.cursor/agents/` | ✅ isolated context windows | `~/.cursor/skills/_shared/` |
| **Kiro** | Native sub-agents via `/sdd-<phase>` | ✅ isolated context windows | `~/.kiro/steering/` |
| **Windsurf** (Cascade) | Solo inline (no sub-agents) | ❌ solo only | `~/.codeium/windsurf/skills/_shared/` |
| **Codex** | Sub-agent delegation via Agent tool | ✅ async/sync | `~/.codex/skills/_shared/` |
| **OpenCode** | JSON overlay into `opencode.json` | ✅ (multi) or single | `.atl/` + `~/.config/opencode/` |

### 2.2 Key Architectural Differences

**Sub-agent delegation (Generic, Claude, Codex)**:
- Orchestrator maintains thin thread
- Sub-agents get fresh context, NO shared memory
- Orchestrator passes artifact references (topic keys), NOT content
- `delegate` (async) default, `task` (sync) for blocking needs
- Anti-pattern: reading 4+ files inline → delegate exploration

**Inline execution (Antigravity, Windsurf)**:
- Orchestrator IS the executor
- Phases run sequentially in same conversation
- "Defer" means complete phase, save artifacts, pause for approval
- Mission Control's built-in Browser/Terminal may be invoked transparently
- Context inflation is the primary risk — phase boundaries manage it

**Native multi-agent (Cursor, Kiro)**:
- Each phase has a dedicated agent file installed by gentle-ai
- Cursor: `~/.cursor/agents/sdd-*.md` (isolated context windows)
- Kiro: native sub-agents invoked via `/sdd-<phase>` slash commands
- Orchestrator invokes by name, synthesizes structured results
- Kiro adds `.kiro/specs/` integration (requirements.md, design.md, tasks.md)

**OpenCode-specific**:
- Two modes: `SDDModeSingle` (single orchestrator) and `SDDModeMulti` (per-phase agents)
- Multi-mode: overlay JSON defines `sdd-orchestrator` + 9 phase agents in `opencode.json`
- Prompts inlined as `{file:<absolutePath>}` references
- Model assignments injected into agent definitions before merge
- Profile system: named SDD profiles generate 11 agent definitions each
- Plugin system: `background-agents.ts` plugin installed with `unique-names-generator` dep

### 2.3 Delegation Rules Matrix

| Action | Sub-agent delegates | Inline executors |
|--------|---------------------|------------------|
| Read 1-3 files | ✅ inline | ✅ inline |
| Read 4+ files | ❌ delegate | ❌ defer to sdd-explore phase |
| Write atomic | ✅ inline | ✅ inline |
| Write multi-file | ❌ delegate | ❌ defer to sdd-apply phase |
| Bash for state (git, gh) | ✅ inline | ✅ inline |
| Bash for execution (test, build) | ❌ delegate | ❌ defer to sdd-verify phase |

### 2.4 OpenCode `/sdd-new` Command

```
WORKFLOW:
1. Launch sdd-explore sub-agent → investigate codebase
2. Present exploration summary to user
3. Launch sdd-propose sub-agent → create proposal
4. Present proposal summary → ask to continue
```

Context: working directory, project name, change name, artifact store mode. Sub-agents handle persistence automatically via engram topic keys.

---

## 3. Persistence Contract

### 3.1 Mode Resolution

| Mode | Cross-session | Shareable | History | Files Created |
|------|---------------|-----------|---------|---------------|
| `engram` | ✅ | ❌ (local DB) | ❌ (upsert overwrites) | Never |
| `openspec` | ❌ (needs git) | ✅ (committed files) | ✅ (git history) | Yes (`openspec/`) |
| `hybrid` | ✅ | ✅ (files) | ✅ (both) | Yes |
| `none` | ❌ | ❌ | ❌ | Never |

Default: `engram` if available, else `none`. Cached per session.

### 3.2 Mode Behavior

| Mode | Read from | Write to |
|------|-----------|----------|
| `engram` | Engram (mem_search + mem_get_observation) | Engram (mem_save with topic_key) |
| `openspec` | Filesystem (`openspec/changes/*/`) | Filesystem |
| `hybrid` | Engram primary, filesystem fallback | BOTH simultaneously |
| `none` | Orchestrator prompt context | Nowhere (inline return) |

### 3.3 OpenSpec Directory Structure

```
openspec/
├── config.yaml              ← Project-specific SDD config + testing capabilities
├── specs/                   ← Source of truth (empty initially)
└── changes/
    ├── <change-name>/       ← Active changes
    │   ├── state.yaml       ← DAG state
    │   ├── proposal.md
    │   ├── spec.md
    │   ├── design.md
    │   ├── tasks.md
    │   ├── apply-progress.md
    │   └── verify-report.md
    └── archive/             ← Completed changes
```

### 3.4 State Persistence

| Mode | Persist DAG State | Recover |
|------|-------------------|---------|
| `engram` | `mem_save(topic_key: "sdd/{change}/state")` | `mem_search` → `mem_get_observation` |
| `openspec` | Write `openspec/changes/{change}/state.yaml` | Read `state.yaml` |
| `hybrid` | Both | Engram first, filesystem fallback |
| `none` | Not possible | Not possible |

### 3.5 Sub-Agent Context Rules

| Context Type | Who Reads | Who Writes |
|--------------|-----------|------------|
| Non-SDD (general task) | Orchestrator searches engram, passes summary in prompt | Sub-agent saves via `mem_save` |
| SDD (phase with dependencies) | Sub-agent reads artifacts directly from backend | Sub-agent saves its artifact |
| SDD (no dependencies, e.g. explore) | Nobody reads | Sub-agent saves its artifact |

**Rationale**: SDD artifacts are large — inlining in orchestrator prompt would consume the entire context window. Sub-agents have full detail; nuance is lost by the time results flow back.

---

## 4. TDD Enforcement Mechanism

### 4.1 Strict TDD Mode Resolution Chain

```
1. System prompt marker (highest priority)
   ├── Search for "strict-tdd-mode" in agent's system prompt file
   ├── "enabled" → strict_tdd: true
   └── "disabled" → strict_tdd: false

2. OpenSpec config
   ├── Read openspec/config.yaml → strict_tdd field
   └── Use that value

3. Auto-detect (if test runner found)
   ├── strict_tdd: true (enable if project CAN do TDD)
   └── Ensures TDD active even without gentle-ai TUI setup

4. No test runner
   └── strict_tdd: false (cannot enable without runner)
```

### 4.2 Orchestrator Injection (MANDATORY)

When launching `sdd-apply` or `sdd-verify`:

1. Search engram: `sdd-init/{project}`
2. If `strict_tdd: true`:
   - Add to sub-agent prompt: `"STRICT TDD MODE IS ACTIVE. Test runner: {test_command}. You MUST follow strict-tdd.md. Do NOT fall back to Standard Mode."`
   - **NON-NEGOTIABLE** — orchestrator enforces, sub-agent cannot silently switch
3. Resolve ONCE per session, cache result

### 4.3 Apply Phase TDD Behavior

| Mode | Behavior |
|------|----------|
| Strict TDD | Load `strict-tdd.md` module. RED→GREEN→REFACTOR per task. TDD Cycle Evidence table MANDATORY. |
| Standard | Zero TDD instructions loaded. `strict-tdd.md` never read, never consumes tokens. |

**Hard gate**: If Strict TDD active and a task completes WITHOUT tests written first → marked FAILED in evidence table. Verify phase WILL reject.

### 4.4 Verify Phase TDD Behavior

| Mode | Additional Steps |
|------|-----------------|
| Strict TDD | Steps 5a (TDD compliance), 5e (quality metrics), 7a (test layer validation). `strict-tdd-verify.md` loaded. |
| Standard | Steps 5a, 5e, 7a skipped entirely. `strict-tdd-verify.md` never loaded. |

### 4.5 Init Phase TDD Detection

`sdd-init` scans for ALL testing infrastructure:

```
├── Test Runner: vitest, jest, pytest, go test, cargo test, make test
├── Test Layers: unit (always), integration (@testing-library, httpx), E2E (playwright, cypress)
├── Coverage: vitest --coverage, coverage.py, go test -cover
└── Quality Tools: linter, type checker, formatter
```

Result persisted as `sdd/{project}/testing-capabilities` — prevents re-detection on every apply/verify run.

---

## 5. Skill Resolver Protocol

### 5.1 Registry Resolution (Orchestrator — once per session)

```
1. mem_search(query: "skill-registry", project: "{project}")
   → mem_get_observation(id) for full content
2. Fallback: read .atl/skill-registry.md
3. Cache Compact Rules section + User Skills trigger table
4. If no registry: warn and proceed
```

### 5.2 Per-Delegation Matching

For each sub-agent launch (or before each phase for inline executors):

1. Match skills by **code context** (file extensions/paths the work touches)
2. Match skills by **task context** (review, PR creation, testing, etc.)
3. Copy matching compact rule blocks into sub-agent prompt as `## Project Standards (auto-resolved)`
4. Inject BEFORE task-specific instructions

**Key rule**: Inject TEXT, not paths. Sub-agents never read SKILL.md files or the registry. Rules arrive pre-digested.

### 5.3 Skill Resolution Feedback

After every phase/delegation:

| Feedback | Meaning | Action |
|----------|---------|--------|
| `injected` | Skills pre-resolved by orchestrator | All good |
| `fallback-registry` | Self-loaded from engram registry | Re-read registry for subsequent |
| `fallback-path` | Loaded via SKILL: Load path | Re-read registry |
| `none` | No skills loaded | Check registry exists |

This is a **compaction-safe self-correction mechanism**. Each delegation re-reads the registry if the cache is lost.

### 5.4 Registry Generation

Run by `sdd-init` (Step 7):
1. Scan user skills: glob `*/SKILL.md` across all known skill directories
2. Scan project conventions: check `agents.md`, `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `GEMINI.md`
3. Write `.atl/skill-registry.md` (mode-independent infrastructure)
4. If engram available, also save to engram

---

## 6. Model Assignment Table

Identical across ALL agent variants:

| Phase | Model | Reason |
|-------|-------|--------|
| orchestrator | **opus** | Coordinates, makes decisions |
| sdd-explore | **sonnet** | Reads code, structural — not architectural |
| sdd-propose | **opus** | Architectural decisions |
| sdd-spec | **sonnet** | Structured writing |
| sdd-design | **opus** | Architecture decisions |
| sdd-tasks | **sonnet** | Mechanical breakdown |
| sdd-apply | **sonnet** | Implementation |
| sdd-verify | **sonnet** | Validation against spec |
| sdd-archive | **haiku** | Copy and close |
| default | **sonnet** | Non-SDD general delegation |

### Model Resolution by Agent

| Agent | Mechanism |
|-------|-----------|
| Claude | HTML markers `<!-- gentle-ai:sdd-model-assignments -->` → `injectClaudeModelAssignments()` |
| OpenCode (multi) | `injectModelAssignments()` into overlay JSON before merge. TUI choice > existing agent > root model |
| OpenCode (single) | No model injection (all phases run in same context) |
| Antigravity | Table as reasoning-depth guide (cannot switch models mid-session) |
| Windsurf | Same reasoning-depth guide |
| Kiro | `kiroModelResolver` interface → `{{KIRO_MODEL}}` placeholder stamped per phase |
| Cursor | Table passed in invocation messages |
| Codex | Table cached and passed in Agent tool `model` parameter |

### OpenCode Multi-Mode Decision Tree

```
For EACH sub-agent:
1. TUI assignment exists → use it (always wins)
2. Agent already exists in user's opencode.json → skip (preserve user's choice)
3. Neither AND rootModelID set → inject rootModelID (break inheritance)
4. None apply → no model field (inherits from root)
```

---

## 7. Go inject.go — Wiring Layer

### 7.1 Entry Point

```go
func Inject(homeDir string, adapter agents.Adapter, sddMode model.SDDModeID, options ...InjectOptions) (InjectionResult, error)
```

Returns `InjectionResult{Changed: bool, Files: []string}`.

### 7.2 Adapter Interface Pattern

The injection uses the `agents.Adapter` interface with **optional capability interfaces** (Go's implicit interface satisfaction):

| Interface | Purpose | Used By |
|-----------|---------|---------|
| `agents.Adapter` | Base: `SupportsSystemPrompt()`, `Agent()`, `SystemPromptStrategy()`, `SystemPromptFile()`, `SupportsSlashCommands()`, `SupportsSkills()` | All agents |
| `workflowInjector` | Copy workflow files to workspace `.windsurf/workflows/` | Windsurf |
| `subAgentInjector` | Copy sub-agent `.md` files to `~/.cursor/agents/` or `~/.kiro/steering/` | Cursor, Kiro |
| `kiroModelResolver` | Resolve `ClaudeModelAlias` → native model ID, stamp `{{KIRO_MODEL}}` | Kiro |

### 7.3 Injection Steps

```
1. System Prompt Injection
   ├── StrategyMarkdownSections (Claude) → InjectMarkdownSection with HTML markers
   ├── StrategyFileReplace/AppendToFile/InstructionsFile/SteeringFile → injectFileAppend
   └── OpenCode/Kilocode: SKIP (handled by JSON overlay in step 2)

1b. Strict TDD Marker (if enabled)
    └── Inject "Strict TDD Mode: enabled" into system prompt via HTML marker

2. Slash Commands
   └── Copy opencode/commands/*.md to adapter.CommandsDir()

2b. OpenCode/Kilocode Settings Merge
    ├── Read overlay JSON (single or multi based on sddMode)
    ├── Inline orchestrator prompt (generic/sdd-orchestrator.md)
    ├── Replace __PROMPT_FILE_{phase}__ with {file:absolutePath}
    ├── Inject model assignments (multi-mode only)
    ├── Merge overlay into opencode.json via MergeJSONObjects
    ├── Install background-agents plugin + npm dep
    └── Inject named profiles (each generates 11 agent definitions)

3. Skill Files
   ├── Write _shared/ (SKILL.md, persistence-contract.md, engram-convention.md, etc.)
   └── Write 11 skills (sdd-init through sdd-onboard + judgment-day)

3b. Workflow Files (workflowInjector)
    └── findProjectRoot() → copy embedded workflows to workspace

3c. Sub-Agent Files (subAgentInjector)
    ├── Copy embedded agent .md files to ~/.cursor/agents/ or ~/.kiro/steering/
    ├── Stamp {{KIRO_MODEL}} for kiroModelResolver adapters
    └── Post-check: verify sdd-apply.md and sdd-verify.md exist (>50 bytes)

4. Post-Injection Verification
   ├── OpenCode: validate "sdd-orchestrator" present in merged JSON (in-memory, disk fallback)
   ├── OpenCode multi: validate "sdd-apply" sub-agent present
   ├── Profiles: validate "sdd-orchestrator-{name}" present per profile
   └── Skills: validate sdd-init/SKILL.md, sdd-apply/SKILL.md, sdd-verify/SKILL.md exist (>100 bytes)
```

### 7.4 Agent-Specific Asset Routing

```go
func sddOrchestratorAsset(agent model.AgentID) string {
    switch agent {
    case model.AgentGeminiCLI:    return "gemini/sdd-orchestrator.md"
    case model.AgentCodex:        return "codex/sdd-orchestrator.md"
    case model.AgentAntigravity:  return "antigravity/sdd-orchestrator.md"
    case model.AgentWindsurf:     return "windsurf/sdd-orchestrator.md"
    case model.AgentCursor:       return "cursor/sdd-orchestrator.md"
    case model.AgentQwenCode:     return "qwen/sdd-orchestrator.md"
    case model.AgentKiroIDE:      return "kiro/sdd-orchestrator.md"
    default:                      return "generic/sdd-orchestrator.md"
    }
}
```

### 7.5 Project Root Detection

`findProjectRoot()` walks upward from the working directory:

1. **Monorepo markers** (highest priority, return immediately): `pnpm-workspace.yaml`, `nx.json`, `turbo.json`, `lerna.json`, `rush.json`
2. **Strong markers** (return immediately): `.git`, `go.mod`, `Cargo.toml`, `pyproject.toml`, `pom.xml`, `build.gradle`
3. **Weak marker** (`package.json`): record as candidate, keep walking (JS monorepo has package.json at every level)
4. Max depth: 20 directories

### 7.6 File Merge Strategy

- `InjectMarkdownSection`: HTML marker-based section injection (`<!-- gentle-ai:sdd-orchestrator -->`)
- `StripLegacyATLBlock`: removes bare (un-marked) orchestrator blocks from prior installs
- `MergeJSONObjects`: deep merge overlay into existing `opencode.json`
- `WriteFileAtomic`: temp file + rename for crash safety
- `migrateLegacyOpenCodeAgentsKey`: normalizes `agents` → `agent` key in old opencode.json

---

## 8. Engram Topic Key Schema

| Artifact | Topic Key |
|----------|-----------|
| Project context | `sdd-init/{project}` |
| Exploration | `sdd/{change-name}/explore` |
| Proposal | `sdd/{change-name}/proposal` |
| Spec | `sdd/{change-name}/spec` |
| Design | `sdd/{change-name}/design` |
| Tasks | `sdd/{change-name}/tasks` |
| Apply progress | `sdd/{change-name}/apply-progress` |
| Verify report | `sdd/{change-name}/verify-report` |
| Archive report | `sdd/{change-name}/archive-report` |
| DAG state | `sdd/{change-name}/state` |
| Testing capabilities | `sdd/{project}/testing-capabilities` |
| Skill registry | `skill-registry` |

Retrieval is always 2-step: `mem_search()` → get ID, then `mem_get_observation(id)` → full content. Search returns 300-char previews only.

---

## 9. Phase Read/Write Matrix

| Phase | Reads | Writes | Notes |
|-------|-------|--------|-------|
| `sdd-explore` | nothing | `explore` | Only phase with no dependencies |
| `sdd-propose` | exploration (optional) | `proposal` | |
| `sdd-spec` | proposal (required) | `spec` | |
| `sdd-design` | proposal (required) | `design` | |
| `sdd-tasks` | spec + design (required) | `tasks` | |
| `sdd-apply` | tasks + spec + design + apply-progress | `apply-progress` | Merge protocol for continuation batches |
| `sdd-verify` | spec + tasks + apply-progress | `verify-report` | |
| `sdd-archive` | all artifacts | `archive-report` | |

---

## 10. Recovery Rule

| Backend | Recovery |
|---------|----------|
| `engram` | `mem_search(...)` → `mem_get_observation(...)` |
| `openspec` | Read `openspec/changes/*/state.yaml` |
| `none` | State not persisted — explain to user |

---

## Summary

The SDD orchestrator is a **unified spec-driven development pipeline** that adapts to 7+ agent architectures through a single Go injection layer. The core invariant: **9-phase DAG with mandatory init guard, strict TDD enforcement via orchestrator injection, 4-tier persistence, and compaction-safe skill resolution**. Agent variants differ only in execution model (sub-agent vs inline) and injection mechanism (HTML markers, JSON overlay, file copy), while sharing 95%+ of the orchestration logic.

Key design decisions:
1. **Orchestrator enforces TDD, not sub-agents** — prevents silent fallback
2. **Compact rules injected as text, not paths** — compaction-safe
3. **Optional Go interfaces** for agent-specific capabilities — no stubs needed for unsupported features
4. **Engram as default persistence** — fast, no files, but no history
5. **OpenCode overlay pattern** — JSON deep merge with model injection and profile system
