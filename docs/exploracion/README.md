# Fork Agent - Exploration Reports

> **Generated**: 2026-02-25 | **Agent**: OpenCode (glm-5-free)

## Executive Summary

Análisis exhaustivo del repositorio fork_agent identificando features **NO implementados** o **incompletos** en los subsistemas principales.

### Critical Findings

| Subsystem | Implementation | Integration | Critical Gap |
|-----------|---------------|-------------|--------------|
| **Workflow** | ⚠️ STUB | ❌ None | Commands don't do actual work |
| **Tmux** | ✅ Full | ❌ Isolated | Not wired to CLI/workflow |
| **Memory** | ✅ Full | ❌ Isolated | cm-save/cm-load missing |
| **Worktrees** | ✅ Full | ❌ Isolated | No auto-creation per agent |
| **Hooks** | ⚠️ Headless | ❌ Not dispatched | Events NEVER triggered |

### Root Cause

**Los 5 subsistemas están bien implementados individualmente pero NO están integrados entre sí.** No existe una capa de orquestación unificada que los conecte.

---

## Reports Index

| # | Report | Focus | Critical Issues |
|---|--------|-------|-----------------|
| 01 | [Workflow Gaps](./01-workflow-gaps.md) | outline/execute/verify/ship | All commands are stubs |
| 02 | [Tmux Integration](./02-tmux-integration.md) | Session management | No CLI commands, not wired |
| 03 | [Memory System](./03-memory-system.md) | Observations CRUD | cm-save/cm-load missing |
| 04 | [Worktrees Gaps](./04-worktrees-gaps.md) | Workspace management | No auto-creation, no isolation |
| 05 | [Hooks System](./05-hooks-system.md) | Event-driven automation | Events NEVER dispatched |
| 06 | [Integration Matrix](./06-integration-matrix.md) | Cross-system wiring | All systems isolated |

---

## Quick Reference: Implementation Status

### ✅ Fully Implemented

- Memory CRUD (save/search/list/get/delete)
- TmuxOrchestrator core operations
- AgentManager with reconcile/cleanup
- WorkspaceManager (create/list/remove/enter)
- Git worktree operations
- Hook scripts (workspace-init, tmux-session, memory-trace, git-guard)
- Circuit breaker, retry, DLQ patterns
- Workflow state management (JSON)

### ⚠️ Partially Implemented

- Workflow CLI (scaffolding exists, logic is stub)
- API routes (endpoints exist, return mocks)
- Hooks (scripts exist, not triggered)
- Worktrees (schema exists, not populated)

### ❌ Not Implemented

- **Hook dispatch** - Events defined but never dispatched
- **Workflow execution** - Commands don't spawn agents
- **Workflow verification** - Mock results only
- **Workflow shipping** - Just prints messages
- **cm-save/cm-load** - Documented but no code
- **Memory isolation per worktree** - Single DB
- **Unified orchestration layer** - Doesn't exist
- **work_O system** - Documented in brain_dope, never built

---

## Priority Actions

### Phase 1: Quick Wins (1-2 days)
1. **Wire HookService to CLI** - Add dispatch calls in entrypoints
2. **Add workflow events to hooks.json** - Enable workflow hooks
3. **Dispatch phase events** - Connect workflow to hooks

### Phase 2: Core Integration (1 week)
4. **Connect workflow → tmux** - Spawn sessions on execute
5. **Connect workflow → memory** - Save observations on phase change
6. **Populate Task.worktree_path** - Enable worktree tracking

### Phase 3: Full Orchestration (2 weeks)
7. **Build Orchestrator class** - Unified coordination
8. **Workspace-aware memory** - Per-worktree DB paths
9. **Implement cm-save/cm-load** - Session checkpoint system

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     CURRENT STATE                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│   │ Workflow │  │   Tmux   │  │  Memory  │  │ Worktree │  │
│   │  (STUB)  │  │  (FULL)  │  │  (FULL)  │  │  (FULL)  │  │
│   └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
│        │             │             │             │         │
│        │   NO CONNECTIONS   │             │             │   │
│        │             │             │             │         │
│   ┌────▼─────┐  ┌────▼─────┐  ┌────▼─────┐  ┌────▼─────┐  │
│   │  Hooks   │  │   API    │  │    DB    │  │   Git    │  │
│   │(HEADLESS)│  │  (STUB)  │  │ (Shared) │  │  (Full)  │  │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     TARGET STATE                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                    ┌─────────────┐                         │
│                    │ Orchestrator│ ← NEW                   │
│                    └──────┬──────┘                         │
│                           │                                │
│        ┌──────────────────┼──────────────────┐            │
│        │                  │                  │            │
│   ┌────▼────┐       ┌─────▼─────┐      ┌────▼────┐       │
│   │Workflow │◄─────►│  Hooks    │◄────►│  Tmux   │       │
│   └────┬────┘       └───────────┘      └────┬────┘       │
│        │                                   │              │
│        ├──────────────┬────────────────────┤              │
│        │              │                    │              │
│   ┌────▼────┐   ┌─────▼─────┐      ┌──────▼──────┐       │
│   │ Memory  │   │ Worktrees │      │ Per-Workspace│       │
│   │(Isolated)│  │ (Auto)    │      │     DB      │       │
│   └─────────┘   └───────────┘      └─────────────┘       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Methodology

This exploration was conducted using 6 parallel OpenCode agents (glm-5-free model):

1. **Workflow Agent** - Analyzed workflow commands and state management
2. **Tmux Agent** - Analyzed tmux orchestrator and agent manager
3. **Memory Agent** - Analyzed memory service and observation repository
4. **Worktrees Agent** - Analyzed workspace manager and git operations
5. **Hooks Agent** - Analyzed hook service and event dispatching
6. **Integration Agent** - Analyzed cross-system connections

Each agent explored the codebase independently, then findings were consolidated into these reports.

---

## Files Structure

```
docs/exploracion/
├── README.md                    # This file (index)
├── 01-workflow-gaps.md          # Workflow system analysis
├── 02-tmux-integration.md       # Tmux integration analysis
├── 03-memory-system.md          # Memory system analysis
├── 04-worktrees-gaps.md         # Worktrees analysis
├── 05-hooks-system.md           # Hooks system analysis
└── 06-integration-matrix.md     # Cross-system integration
```
