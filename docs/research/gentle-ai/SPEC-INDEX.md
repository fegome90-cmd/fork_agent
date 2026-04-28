# Gentle-AI Spec Docs — Index & Executive Summary

**Date**: 2026-04-28 | **Scope**: Full agentic instruction system documentation
**Source**: 4 parallel explorer agents (glm-5-turbo, paid tier)

---

## File Index

| #   | File                            | Size               | Sections                                                                                                                                                                          | Focus                                        |
| --- | ------------------------------- | ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| 1   | `spec-persona-injection.md`     | 23 KB, 12 sections | Persona IDs, base structure, per-agent variants, injection strategies, auto-heal, idempotency, test coverage (35 tests), data flow diagram                                        | How identity is defined and injected         |
| 2   | `spec-sdd-orchestrator.md`      | 21 KB, 10 sections | Phase DAG (9 phases), 7 agent execution models, persistence contract (4 modes), TDD enforcement, skill resolver, model assignments, Go wiring layer, engram topic keys            | How SDD workflow is instructed               |
| 3   | `spec-agent-adapters.md`        | 23 KB, 11 sections | Agent interface (15+ methods), factory pattern, tier system, per-adapter comparison (11 agents), 5 system prompt strategies, 4 MCP strategies, 7-component pipeline, golden tests | How instructions reach 11 different AI tools |
| 4   | `spec-skills-registry.md`       | 22 KB, 13 sections | SKILL.md structure, skill resolver protocol, registry generation, AGENTS.md index, shared conventions, TDD enforcement, 18-skill catalog, judgment-day protocol                   | How reusable behavior modules work           |
| 5   | `diff-gentle-ai-vs-tmuxfork.md` | 14 KB, 8 sections  | Gap analysis, persona diff, injection pipeline diff, SDD diff, skills diff, prioritized action plan (13 items)                                                                    | What we should adopt and what we shouldn't   |

**Total**: ~103 KB of structured technical documentation.

---

## Architecture Overview

```
                         Gentle-AI Binary (Go)
                                │
                ┌───────────────┼───────────────┐
                │               │               │
         Agent Adapters    Components       Assets
         (11 agents)      (7 pipeline)     (Markdown)
                │               │               │
    ┌───────────┤      ┌────────┤      ┌────────┤
    │ Claude    │      │ engram │      │ persona│
    │ OpenCode  │      │ persona│      │ sdd    │
    │ Cursor    │      │ sdd    │      │ skills │
    │ Kiro      │      │ skills │      │ shared │
    │ Gemini    │      │ mcp    │      └────────┤
    │ Windsurf  │      │ perms  │              │
    │ Codex     │      │ gga    │              │
    │ VSCode    │      └────────┘              │
    │ Kilocode  │                              │
    │ Qwen      │                              │
    │ Antigrav  │                              │
    └───────────┘                              │
         │                                     │
         │  Each adapter implements:           │
         │  - SystemPromptStrategy()           │
         │  - MCPStrategy()                    │
         │  - SkillsDir()                      │
         │  - SupportsSkills()                 │
         │  - Detect() → installed?            │
         │                                     │
         └─────► Components call adapter methods
                   (zero hardcoded agent knowledge)
```

---

## Key Findings

### 1. Persona Injection (spec-persona-injection.md)

- **3 personas**: Gentleman (rioplatense + warm), Neutral (same philosophy, no slang), Custom (user's own)
- **8-section structure**: Rules → Personality → Language → Tone → Philosophy → Expertise → Behavior → Skills
- **5 injection strategies**: MarkdownSections (Claude), FileReplace (most), AppendToFile (Windsurf/Antigravity), InstructionsFile (VS Code), SteeringFile (Kiro)
- **Auto-heal**: Detects and migrates legacy persona blocks with fingerprint verification (all 3 must match before stripping)
- **35 test functions** covering injection, idempotency, migrations, edge cases
- **Key insight**: Neutral = Gentleman minus regional language. Teacher passion intact.

### 2. SDD Orchestrator (spec-sdd-orchestrator.md)

- **9 phases**: explore → propose → spec → design → tasks → apply → verify → archive (+ onboard)
- **4 execution models**: Sub-agent (Claude/Codex), Inline (Antigravity/Windsurf), Multi-agent (Cursor/Kiro), Solo (OpenCode)
- **4 persistence modes**: engram (memory), openspec (files), hybrid (both), none (inline only)
- **TDD enforcement**: Init Guard checks `sdd-init/{project}` → if `strict_tdd: true`, orchestrator injects "STRICT TDD MODE IS ACTIVE" into every apply/verify sub-agent
- **Model assignments**: opus (orchestrator/propose/design), sonnet (explore/spec/tasks/apply/verify), haiku (archive)
- **Delegation Matrix**: Read 1-3 files = inline, 4+ = defer to explore phase. Write 1 file = inline, multi-file = defer to apply phase.
- **Key insight**: Orchestrator enforces TDD, not sub-agents. Sub-agents don't even know TDD is active — they just follow the injected instructions.

### 3. Agent Adapters (spec-agent-adapters.md)

- **Interface**: 15+ methods including Agent(), Tier(), Detect(), SystemPromptStrategy(), MCPStrategy(), SkillsDir(), SupportsSkills(), etc.
- **Factory**: Switch on 11 AgentIDs → return concrete adapter
- **Detection**: Binary on PATH + config dir existence → `(installed, binaryPath, configPath, configFound, err)`
- **7-component pipeline**: engram → persona → sdd → skills → mcp → permissions → gga (sequential, each calls adapter methods)
- **Golden tests**: Input (agent + component selections) → expected output (files written). 40+ golden files.
- **Key insight**: Components NEVER switch on AgentID. They call `adapter.SystemPromptStrategy()` or `adapter.SkillsDir(homeDir)`. Adding a new agent = implement the interface. Zero component changes.

### 4. Skills Registry (spec-skills-registry.md)

- **18 skills**: 10 SDD phases + 4 project skills (go-testing, branch-pr, issue-creation, judgment-day) + skill-creator + skill-registry + \_shared conventions
- **Skill resolver**: Match by code context (file extensions) AND task context (what actions). Load compact rules as text, not paths.
- **AGENTS.md as index**: Table with Skill / Trigger / Path columns. Loaded at session start.
- **Shared conventions**: engram naming (`sdd/{change}/{type}`), openspec paths (`openspec/changes/{change}/`), persistence contract (4 modes), phase common boilerplate
- **Judgment-day**: Adversarial review with 2 blind judges + convergence threshold. Prevents both nit-picking loops and single-reviewer blind spots.
- **Key insight**: Strict TDD is opt-out, not opt-in. If test runner detected and no config says otherwise, TDD is enabled.

---

## Lessons for tmux_fork

### What to adopt

| Priority | Item                                                    | From Spec            | Effort |
| -------- | ------------------------------------------------------- | -------------------- | ------ |
| P0       | Sub-agent Role Isolation (`-nc` + explicit role prompt) | SDD inline vs defer  | S      |
| P0       | Persistence Contract (write to disk before advancing)   | SDD persistence      | S      |
| P0       | Delegation Matrix (read 1-3 = inline, 4+ = defer)       | SDD orchestrator     | S      |
| P1       | Caring anchor ("te corrijo porque me importa")          | Persona gentleman    | S      |
| P1       | Voseo dictionary expansion                              | Persona language     | S      |
| P1       | Anti-sarcasm + help-first rules                         | Persona output-style | S      |
| P1       | Init Guard (verify project context before workflow)     | SDD init guard       | M      |
| P1       | Size classification (skip workflow for <50 lines)       | SDD size             | S      |
| P2       | SKILL.md frontmatter standardization                    | Skills structure     | M      |
| P2       | Skill resolution feedback loop                          | Skills resolver      | M      |
| P2       | Persona Neutral variant                                 | Persona IDs          | S      |

### What NOT to copy

| Item                         | Reason                                    |
| ---------------------------- | ----------------------------------------- |
| Go binary injection pipeline | We use Pi, not a custom binary            |
| 11 agent adapters            | We have 1 runtime (Pi)                    |
| 5 injection strategies       | Pi handles system prompt loading natively |
| Auto-heal system             | No legacy prompt versions to migrate      |
| Agent tier system            | Single tier (Pi only)                     |

---

## Source Files Analyzed

| Category                | Count          | Location                                                                                                                        |
| ----------------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Persona assets          | 8              | `internal/assets/{generic,claude,opencode,kiro}/persona-*.md`                                                                   |
| SDD orchestrator assets | 14             | `internal/assets/{generic,claude,antigravity,cursor,kiro,windsurf,codex,opencode,gemini,qwen}/*orchestrator*.md`                |
| Agent adapters          | 18             | `internal/agents/{claude,opencode,cursor,kiro,antigravity,gemini,codex,windsurf,vscode,kilocode,qwen}/*.go`                     |
| Component injectors     | 7              | `internal/components/{engram,persona,sdd,skills,mcp,permissions,gga}/inject.go`                                                 |
| Skills                  | 23             | `internal/assets/skills/{_shared,sdd-*,branch-pr,issue-creation,go-testing,judgment-day,skill-creator,skill-registry}/SKILL.md` |
| Tests                   | ~35            | `internal/components/persona/inject_test.go`, golden files                                                                      |
| **Total**               | **~128 files** | `/Users/felipe_gonzalez/Developer/gentle-ai/`                                                                                   |
