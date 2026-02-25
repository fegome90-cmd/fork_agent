# Hooks System - Gap Analysis

> **Generated**: 2026-02-25 | **Scope**: Event-driven automation for agent workflows

## Executive Summary

🚨 **CRITICAL FINDING**: Los eventos NUNCA son despachados. El sistema de hooks tiene scripts implementados y configuración completa, pero **HookService nunca es invocado** desde ningún entrypoint (CLI, API, workflow). Todo el sistema es "headless" - definido pero no conectado.

---

## What IS Implemented

### Hook Scripts (`.hooks/`)

| Script | Event | Status | Implementation |
|--------|-------|--------|----------------|
| `workspace-init.sh` | SessionStart | ✅ FULL | Crea `.claude/traces/`, workspace ID |
| `tmux-session-per-agent.sh` | SubagentStart | ✅ FULL | Crea sesión tmux aislada |
| `memory-trace-writer.sh` | SubagentStop | ✅ FULL | Escribe trace a `.claude/traces/` |
| `git-branch-guard.sh` | PreToolUse | ✅ FULL | Git allowlist/blocklist |

### Hook Configuration (`.hooks/hooks.json`)

```json
{
  "hooks": {
    "SessionStart": [...],
    "SubagentStart": [...],
    "SubagentStop": [...],
    "PreToolUse": [...]
  }
}
```

### Core Infrastructure (`src/application/services/orchestration/`)

| Componente | Status | Descripción |
|------------|--------|-------------|
| `events.py` | ✅ FULL | 6 eventos definidos |
| `hook_service.py` | ✅ FULL | HookService con dispatch |
| `dispatcher.py` | ✅ FULL | EventDispatcher con rules |
| `specs.py` | ✅ FULL | Action specifications |
| `actions.py` | ✅ FULL | Action definitions |

### Events Defined

| Event | Status | En hooks.json |
|-------|--------|---------------|
| `UserCommandEvent` | ✅ Defined | ❌ NOT configured |
| `FileWrittenEvent` | ✅ Defined | ❌ NOT configured |
| `ToolPreExecutionEvent` | ✅ Defined | ✅ (PreToolUse) |
| `SessionStartEvent` | ✅ Defined | ✅ Configured |
| `SubagentStartEvent` | ✅ Defined | ✅ Configured |
| `SubagentStopEvent` | ✅ Defined | ✅ Configured |

---

## 🚨 CRITICAL GAP: Events Never Dispatched

### Evidence

```bash
# Search for event instantiation in codebase:
SessionStartEvent(    # NO MATCHES
SubagentStartEvent(   # NO MATCHES
HookService(          # Only in tests
dispatch(             # Only in tests and hook_service.py itself
```

### What This Means

```
┌─────────────────────────────────────────────────────────────┐
│                    ARCHITECTURE GAP                         │
├─────────────────────────────────────────────────────────────┤
│  CLI Entry Points     API Routes      Workflow Commands    │
│       │                   │                  │              │
│       │                   │                  │              │
│       ▼                   ▼                  ▼              │
│   [NO DISPATCH]     [NO DISPATCH]     [NO DISPATCH]        │
│                                                             │
│  ═══════════════════════════════════════════════════════   │
│                                                             │
│  HookService.dispatch() ← NEVER CALLED                     │
│  EventDispatcher     ← EXISTS BUT NOT INVOKED              │
│  hooks.json          ← CONFIGURED BUT NO TRIGGER           │
│  Hook scripts        ← IMPLEMENTED BUT NEVER RUN           │
└─────────────────────────────────────────────────────────────┘
```

---

## Integration Gaps

### Workflow Integration

| Feature | Status | Gap |
|---------|--------|-----|
| Dispatch on phase change | ❌ MISSING | No WorkflowPhaseChangeEvent |
| HookService in workflow.py | ❌ MISSING | No import, no dispatch |
| Workflow hooks in hooks.json | ❌ MISSING | No workflow events |

### API Integration

| Feature | Status | Gap |
|---------|--------|-----|
| Dispatch on API calls | ❌ MISSING | No events from routes |
| Webhook execution | ⚠️ INCOMPLETE | CRUD only, no HTTP callback |

### User Extensibility

| Feature | Status | Gap |
|---------|--------|-----|
| hooks.json extension | ⚠️ LIMITED | Manual edit required |
| Programmatic extension | ⚠️ CODE CHANGE | `create_event_dispatcher(extra_rules=...)` |
| User-friendly CLI | ❌ MISSING | No `hook add/remove` commands |

---

## Missing Events

### Defined but NOT Configured

| Event | Purpose | Should Trigger |
|-------|---------|----------------|
| `UserCommandEvent` | Track CLI usage | On every `memory *` command |
| `FileWrittenEvent` | Track file changes | On Write tool usage |

### NOT Defined (Missing)

| Event | Purpose | Location |
|-------|---------|----------|
| `WorkflowPhaseChangeEvent` | Track workflow progress | workflow.py |
| `WorkflowOutlineStart` | Hook before planning | workflow.py |
| `WorkflowExecuteStart` | Hook before execution | workflow.py |
| `WorkflowVerifyStart` | Hook before verification | workflow.py |
| `WorkflowShipStart` | Hook before shipping | workflow.py |
| `AgentSpawnEvent` | Track agent creation | agent_manager.py |
| `AgentTerminateEvent` | Track agent cleanup | agent_manager.py |

---

## Pre-commit Hooks

| Feature | Status |
|---------|--------|
| `.pre-commit-config.yaml` | ✅ EXISTS |
| ruff | ✅ Configured |
| mypy | ✅ Configured |
| Standard hooks | ✅ trailing-whitespace, end-of-file-fixer |
| Custom application hooks | ❌ MISSING |

---

## Recommendations

### Tier 1 - Critical (Fix Immediately)

1. **Wire HookService to CLI entrypoint**
```python
# src/interfaces/cli/main.py
from src.application.services.orchestration.hook_service import HookService
from src.application.services.orchestration.events import SessionStartEvent

@app.callback()
def main(ctx: typer.Context):
    hook_service = HookService()
    hook_service.dispatch(SessionStartEvent(session_id=generate_session_id()))
```

2. **Dispatch events from workflow commands**
```python
# workflow.py
def execute(...):
    hook_service.dispatch(WorkflowExecuteStartEvent(plan_id=plan.session_id))
    # ... actual execution ...
    hook_service.dispatch(WorkflowExecuteCompleteEvent(plan_id=plan.session_id))
```

### Tier 2 - Important

3. **Add missing events to events.py**
4. **Configure UserCommand and FileWritten in hooks.json**
5. **Implement webhook HTTP callback execution**

### Tier 3 - Enhancement

6. **Add CLI commands for hook management**
7. **Add custom pre-commit hooks for project-specific checks**

---

## Files Involved

| Archivo | Propósito |
|---------|-----------|
| `.hooks/hooks.json` | Hook configuration |
| `.hooks/*.sh` | Hook scripts |
| `src/application/services/orchestration/hook_service.py` | Hook service |
| `src/application/services/orchestration/dispatcher.py` | Event dispatcher |
| `src/application/services/orchestration/events.py` | Event definitions |
| `src/infrastructure/orchestration/rule_loader.py` | Config loader |
| `src/infrastructure/orchestration/shell_action_runner.py` | Script executor |
| `src/interfaces/api/routes/webhooks.py` | Webhook API (incomplete) |
