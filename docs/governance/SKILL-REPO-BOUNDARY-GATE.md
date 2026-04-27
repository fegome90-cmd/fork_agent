# SKILL-REPO-BOUNDARY-GATE — Governance Document

> Status: Proposed | Date: 2026-04-26 | ADR: ADR-002-skill-repo-boundary.md
> Category: POLICY_STANDARD (per gate-authority-matrix-v2.md)
> Enforceability: Contract tests (bats) + exit code verification

---

## 1. Purpose

This document defines the enforceable boundary contract between the **skill/orquestador** (tmux-live, tf:* prompts) and the **repo/backend** (AgentLaunchLifecycleService, TaskBoardService, API, CLI).

It is the prerequisite for any integration between the two layers. No cableado may proceed without this contract being accepted and tested.

---

## 2. Authority Split

| Concern | Authority | Evidence |
|---------|-----------|----------|
| Launch permission | `AgentLaunchLifecycleService` (repo) | CAS claim + launch_id |
| Agent execution | `tmux-live` (skill) | Pane creation + process PID |
| Phase progress | Memory MCP (skill) | `fork/{change}/state` |
| Task lifecycle | `TaskBoardService` (repo) | CAS transitions |
| Quality validation | `enforce-envelope` (skill) | Exit code + JSON verdict |

**Rule**: Each authority owns its surface. No cross-imports. Communication via CLI/API only.

---

## 3. Contract: `fork launch` CLI

### 3.1 Commands

| Command | Purpose | Exit codes |
|---------|---------|-----------|
| `fork launch request` | Request launch permission | 0=claimed, 1=suppressed/error, 2=usage |
| `fork launch confirm-spawning` | Confirm spawn started | 0=ok, 1=CAS fail |
| `fork launch confirm-active` | Confirm agent running | 0=ok, 1=CAS fail |
| `fork launch mark-failed` | Report spawn failure | 0=ok, 1=already terminal |
| `fork launch begin-termination` | Start cleanup | 0=ok, 1=invalid transition |
| `fork launch confirm-terminated` | Confirm cleanup done | 0=ok, 1=CAS fail |
| `fork launch status` | Query launch state | 0=found, 1=not found |
| `fork launch list-active` | List active launches | 0=ok |

### 3.2 JSON Schema

All commands with `--json` flag return:
```json
{
  "decision": "claimed" | "suppressed" | "error" | null,
  "launch_id": "<hex>" | null,
  "status": "<string>" | null,
  "reason": "<string>" | null
}
```

### 3.3 Fallback

If `fork launch request` is unavailable:
- Skill proceeds without lifecycle tracking
- Logs warning: "fork launch request unavailable"
- `LAUNCH_ID=null` → downstream lifecycle calls skipped
- No abort, no error exit

---

## 4. Canonical Key Convention

| Caller | Format | Example |
|--------|--------|---------|
| Skill (tmux-live) | `skill:<phase>:<role>-<name>` | `skill:3:explorer-exp-01` |
| API session | `api:<agent-type>:<task-hash>` | `api:claude:a1b2c3d4e5f6` |
| Workflow | `workflow:<branch>:<role>-<idx>` | `workflow:fix-auth:impl-1` |

---

## 5. Rollback Rules

| Scenario | Action |
|----------|--------|
| `confirm-active` fails after spawn | Agent keeps running. Launch stays SPAWNING. Lease expiry quarantines it. |
| CLI unavailable mid-lifecycle | Proceed without tracking. Orphan record quarantined by lease expiry. |
| `request` returns suppressed | Skip agent. Not an error. Log reason. Continue orchestration. |
| `request` returns error | Fail closed. Log error. Proceed without tracking (same as CLI unavailable). |

---

## 6. Test Requirements

### 6.1 Contract Tests (bats)

Must verify:
- CLI command exists and returns valid JSON
- Duplicate request returns suppressed
- Full lifecycle (request → confirm-spawning → confirm-active → terminate)
- Graceful fallback when CLI not in PATH

### 6.2 Schema Stability Tests

Must verify:
- JSON output has required fields (decision, launch_id, reason)
- Exit codes match contract (0/1/2)
- No schema regression across versions

---

## 7. Prerequisites Before Cableado

| Step | Status |
|------|--------|
| This document accepted | Pending |
| ADR-002 accepted | Pending |
| RB-25, RB-26, RB-27 repaired | Pending |
| `fork launch` CLI commands implemented | Pending |
| Contract tests (bats) passing | Pending |
| `tmux-live launch` modified to call CLI | Pending |

No step may be skipped. Steps must execute in order.

---

## 8. Prohibited Patterns

| Pattern | Why prohibited |
|---------|---------------|
| `tmux-live` importing Python from repo | Breaks layer separation |
| `tmux-live` reading SQLite directly | Fragile, version-dependent |
| `tmux-live` calling API over HTTP | Requires server running |
| Shared state files between skill and repo | Race conditions, no CAS |
| `tmux-live` depending on repo internals | Any internal change breaks skill |
