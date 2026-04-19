# gentle-ai vs tmux_fork — Full Ecosystem Diff
> Date: 2026-04-17
> gentle-ai: github.com/Gentleman-Programming/gentle-ai (Go, 65K lines, 11 agents)
> tmux_fork: commit b7bbe723 (Python 3.11+, DDD, Pi extensions)

## Executive Summary

**gentle-ai** is a **meta-ecosystem installer** — not a memory system. It's a Go binary (65,348 LOC)
that configures 11 AI agents (Claude Code, OpenCode, Cursor, Windsurf, Kiro, Gemini CLI, Codex,
VSCode Copilot, Antigravity, KiloCode, Qwen Code) with a unified stack:

- **Engram** — persistent memory (MCP stdio server, Go binary)
- **SDD** — Spec-Driven Development orchestrator (11-phase, multi-model profiles)
- **Skills** — curated coding patterns library
- **MCP servers** — Context7 integration
- **Persona** — teaching-oriented agent personality
- **Permissions** — security-first defaults
- **GGA** — Gentleman Git Automation
- **Theme** — visual consistency
- **FileMerge** — atomic file operations with rollback

**tmux_fork** is a **memory-first agent-adjacent system** — Python CLI + Pi TypeScript extensions
focused on persistent memory, session lifecycle, orchestration (tmux), and telemetry.

### Key Insight

These are **complementary systems, not competitors.** gentle-ai installs Engram (memory) + SDD (workflow)
+ Skills + Persona into agents. tmux_fork provides memory + orchestration + telemetry that any agent
can use via CLI or Pi extensions. They overlap only in the Engram/memory component.

---

## Architecture Comparison

| Aspect | gentle-ai | tmux_fork |
|--------|-----------|-----------|
| **Core purpose** | Agent ecosystem installer/configurator | Memory CLI + agent orchestration |
| **Language** | Go 1.24+ (single binary, no CGO) | Python 3.11+ (uv runtime) |
| **Total LOC** | 65,348 Go | ~8,000 Python + ~600 TypeScript |
| **Architecture** | Component-based (11 components) | DDD (domain/application/infrastructure/interfaces) |
| **Agents supported** | 11 (adapter pattern per agent) | Pi (native), any (CLI) |
| **Distribution** | Homebrew, binary download, curl | pip/uv package |
| **Pipeline** | Prepare → Apply → Rollback (with FailurePolicy) | Sequential execution |
| **State** | JSON plans with step tracking | SQLite (15 migrations) |
| **TUI** | Bubbletea (30+ screens) | None (CLI only) |
| **Self-update** | Atomic rename, GitHub releases | None |

---

## Component-by-Component Comparison

### 1. Memory System

> This is the ONLY area of direct overlap.

| Feature | gentle-ai (via Engram) | tmux_fork | Gap |
|---------|----------------------|-----------|-----|
| Storage | SQLite + FTS5 (modernc.org) | SQLite + FTS5 (stdlib) | None |
| Schema | ~8 tables | ~12 tables (15 migrations) | tmux_fork + |
| FTS5 fields | content, prompts, tool_name, type | content | Engram + |
| Sync | Chunked JSONL + git | Schema stubs only | Engram ++ |
| Privacy | `<private>` tag stripping | No equivalent | Engram + |
| MCP server | 15 tools (agent/admin profiles) | 3 Pi native tools | Engram + |
| HTTP API | :7437 REST | None | Engram + |
| TUI | Bubbletea browse | None | Engram + |
| Obsidian export | Beta | None | Engram + |
| Telemetry | Minimal | Full (3 tables, dashboard) | tmux_fork ++ |
| Auto-backup | Unknown | Yes (rotation, last 3) | tmux_fork + |
| Topic key upserts | No | Yes (ON CONFLICT) | tmux_fork + |
| Proactive keyword search | No | Yes (Pi before_agent_start) | tmux_fork + |
| Session lifecycle | Basic | Full (goal, summary, auto-end) | tmux_fork + |
| Scheduled tasks | No | Yes (cron-like) | tmux_fork + |
| Promise contracts | No | Yes (state machine) | tmux_fork + |

**Memory Score:** Engram 78/100 | tmux_fork 76/100 | Gap: 2 pts (unchanged from previous analysis)

### 2. SDD (Spec-Driven Development)

| Feature | gentle-ai | tmux_fork | Gap |
|---------|-----------|-----------|-----|
| SDD phases | 11 (init→explore→propose→spec→design→tasks→apply→verify→archive→onboard) | workflow commands (outline→execute→verify→ship) | Different paradigms |
| Multi-model profiles | Yes (balanced/performance/economy + custom) | Model assignment per sub-agent | gentle-ai + |
| Agent adapter injection | Yes (per-agent config injection) | N/A (Pi extensions) | gentle-ai + |
| Sub-agent delegation | OpenCode native (mode=primary/subagent) | tmux spawn + prompt files | gentle-ai + |
| SDD prompts | 11 embedded Markdown assets | workflow prompts in CLI | Both |
| Strict TDD mode | Yes (system prompt marker injection) | N/A | gentle-ai + |
| Profile CRUD | Create, detect, delete named profiles | N/A | gentle-ai + |
| File merge | Atomic writes with rollback | Standard Python file I/O | gentle-ai + |

**Score:** gentle-ai 90/100 | tmux_fork 30/100 (workflow only, no SDD)

### 3. Pipeline / Orchestration

| Feature | gentle-ai | tmux_fork |
|---------|-----------|-----------|
| Pattern | Prepare → Apply → Rollback | Sequential CLI commands |
| Failure policy | StopOnError / ContinueOnError | Stop on error |
| Rollback | Automatic (RollbackStep interface) | Manual (git stash) |
| Progress events | ProgressFunc callback | tmux capture-pane polling |
| Step tracking | PlanStep with status/result | Promise contracts table |
| Atomicity | filemerge.WriteFileAtomic | Standard writes |
| Multi-agent | 11 adapters (adapter pattern) | Pi + any CLI agent |
| Parallel execution | Per-stage sequential, parallel across stages | tmux parallel spawn |

**Score:** gentle-ai 85/100 | tmux_fork 55/100 (fork/orchestration exists but less structured)

### 4. Agent Support

| Agent | gentle-ai | tmux_fork |
|-------|-----------|-----------|
| Claude Code | Full adapter (paths, MCP, prompts) | Pi extensions (3 TS) |
| OpenCode | Full adapter | CLI (memory commands) |
| Cursor | Full adapter (sub-agents) | CLI |
| Windsurf | Full adapter (workflows) | CLI |
| Kiro IDE | Full adapter (native SDD subagents) | CLI |
| Gemini CLI | Full adapter | CLI |
| Codex | Full adapter | CLI |
| VSCode Copilot | Full adapter | CLI |
| Antigravity | Full adapter | CLI |
| KiloCode | Full adapter | CLI |
| Qwen Code | Full adapter | CLI |

**gentle-ai** wins breadth (11 adapters with per-agent config injection).  
**tmux_fork** wins depth for Pi (3 native extensions with proactive features).

### 5. TUI / UX

| Feature | gentle-ai | tmux_fork |
|---------|-----------|-----------|
| Installer TUI | Bubbletea (30+ screens, 14K LOC) | None |
| Memory browser | Engram TUI (Bubbletea) | None |
| Model picker | Per-engine (Claude, Kiro, generic) | None |
| Profile management | Create/delete/list screens | None |
| Dependency tree | Visual tree display | None |
| Backup management | Browse/restore | CLI `--fix` |
| CLI commands | ~8 (install, sync, uninstall) | 21+ (memory, fork, workflow, schedule, telemetry) |

**Score:** gentle-ai 85/100 | tmux_fork 40/100 (rich CLI, no TUI)

### 6. Safety & Operations

| Feature | gentle-ai | tmux_fork |
|---------|-----------|-----------|
| Auto-backup | Unknown | Yes (3-rotation) |
| Atomic writes | filemerge package | Standard |
| Rollback on failure | Automatic (pipeline) | Manual |
| Privacy redaction | `<private>` tag stripping | No |
| Permission system | Per-agent security defaults | None |
| Telemetry | Minimal | Full (events, metrics, sessions) |
| Health checks | Verify step in pipeline | `memory health --fix` |
| Self-update | GitHub releases, atomic rename | None |
| Uninstall | Granular (partial/full/full-remove/clean) | None |

### 7. Distribution

| Feature | gentle-ai | tmux_fork |
|---------|-----------|-----------|
| Install method | `curl \| sh` / Homebrew / binary | `uv sync` / `pip install` |
| Binary size | ~15MB (Go, no CGO) | ~50KB + Python runtime |
| Cross-platform | macOS, Linux, WSL, Windows, Termux | macOS (primary) |
| Dependencies | None (static binary) | Python 3.11+, uv, SQLite |
| CI/CD | GitHub Actions (Go test) | Local pytest |

---

## Scoring Summary (0-100)

| Category | gentle-ai | tmux_fork | Notes |
|----------|-----------|-----------|-------|
| Memory (core) | 78 | 76 | Minimal gap |
| SDD/Workflow | 90 | 30 | Different scope |
| Pipeline | 85 | 55 | gentle-ai structured |
| Agent support | 95 | 40 | 11 vs Pi+CLI |
| TUI/UX | 85 | 40 | 30+ screens vs CLI |
| Telemetry | 40 | 92 | tmux_fork dominates |
| Orchestration | 60 | 75 | tmux_fork multi-agent |
| Safety | 75 | 80 | Comparable |
| Distribution | 95 | 55 | Single binary vs Python |
| **Average** | **78** | **54** | **Scope difference** |

---

## Strategic Assessment

### These are NOT competing products

| Dimension | gentle-ai | tmux_fork |
|-----------|-----------|-----------|
| **What it IS** | Agent ecosystem installer | Memory + orchestration tool |
| **Users** | Developers setting up AI tools | Agents needing persistent context |
| **Use case** | First-time setup, multi-agent config | Runtime memory, session continuity |
| **Runtime** | Install-time only | Continuous (agent lifecycle) |

### Integration opportunity

gentle-ai **installs** Engram into agents. tmux_fork **is** a memory system. They could be complementary:

1. **gentle-ai could install tmux_fork** as a component (like it installs Engram)
2. **tmux_fork could adopt SDD patterns** from gentle-ai's 11-phase orchestrator
3. **Both could share schema** — already converged on SQLite+FTS5

### What tmux_fork should borrow from gentle-ai

| Priority | Feature | Effort | Impact |
|----------|---------|--------|--------|
| P1 | Rollback pipeline (Prepare→Apply→Rollback) | M | Safe operations |
| P1 | Privacy redaction (`<private>` tag stripping) | S | Security critical |
| P2 | Atomic file writes (filemerge pattern) | S | Data integrity |
| P2 | Multi-model SDD profiles | M | Quality control |
| P3 | Agent adapter pattern (per-agent config injection) | L | Multi-agent support |
| P3 | TUI (Bubbletea equivalent for Python = Textual) | L | UX improvement |
| P3 | Self-update mechanism | M | Distribution |

### What tmux_fork already does better

1. **Telemetry** — 3 tables, dashboard, slow-query log, session aggregates
2. **Proactive keyword search** — before_agent_start context injection
3. **Session lifecycle** — goal, summary, auto-end, isolation
4. **Topic key upserts** — progressive refinement without duplicates
5. **Scheduled tasks** — cron-like delayed actions
6. **Promise contracts** — state machine for workflow tracking
7. **Orchestration** — tmux-based multi-agent parallel execution

---

## Files Analyzed

| gentle-ai | Lines | Purpose |
|-----------|-------|---------|
| `PRD.md` | 1413 | Product requirements |
| `PRD-AGENT-BUILDER.md` | 953 | Agent builder PRD |
| `internal/pipeline/` | ~200 | Prepare→Apply→Rollback |
| `internal/model/` | ~400 | Types, plans, selection, profiles |
| `internal/agents/` | ~3500 | 11 agent adapters |
| `internal/components/engram/` | 2539 | Engram install/inject |
| `internal/components/sdd/` | 6905 | SDD orchestrator |
| `internal/components/persona/` | 1608 | Persona injection |
| `internal/components/mcp/` | 387 | Context7 MCP |
| `internal/tui/` | 13956 | 30+ Bubbletea screens |
| **Total** | **65348** | Go codebase |

| tmux_fork | Lines | Purpose |
|-----------|-------|---------|
| `src/domain/` | ~800 | Entities, ports |
| `src/application/` | ~2000 | Services, use cases |
| `src/infrastructure/` | ~3000 | DB, DI, persistence |
| `src/interfaces/cli/` | ~1500 | Typer commands |
| `src/extensions/` (TS) | ~600 | Pi extensions |
| `tests/` | ~3000 | Unit, integration, E2E |
| **Total** | ~11000 | Python + TypeScript |
