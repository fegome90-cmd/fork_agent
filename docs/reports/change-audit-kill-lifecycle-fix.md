# Authority-Flow Audit Report: Change-Audit — Kill Path Lifecycle Fix

**Mode:** change-audit (delta-first)
**Scope:** Skill `tmux-fork-orchestrator/scripts/lib/` + Repo `src/interfaces/cli/commands/launch.py`
**Date:** 2026-04-27
**Change:** Fixes F1-F5 from authority-flow audit (branch `feat/agent-launch-lifecycle`)
**Baseline commit:** `c572f5e3` (pre-fix) → `5bb572a1` (post-fix)

---

## 1. Verdict

**HEALTHY.** The change closes an authority vacuum (kill path had no lifecycle transition) by delegating writes through the existing CLI boundary. No new competing writers introduced. No SSOT violations. All new surfaces are reader-only or delegated through the canonical CLI pipeline.

---

## 2. Surface Inventory

| # | Surface | Type | File:Lines | Calls | Called By |
|---|---------|------|------------|-------|-----------|
| 1 | **[NEW]** `lifecycle_get_launch_id()` | function | `lifecycle.sh:69-73` | `jq` on `.meta` | `cmd_kill`, `cmd_stop` |
| 2 | **[NEW]** `lifecycle_mark_failed()` | function | `lifecycle.sh:76-81` | `_call_fork_launch mark-failed` | `cmd_kill`, `cmd_stop`, `cmd_kill_all` |
| 3 | **[NEW]** `lifecycle_reconcile()` | function | `lifecycle.sh:84-88` | `_call_fork_launch summary` | `cmd_init` |
| 4 | **[MODIFIED]** `cmd_kill()` | function | `kill.sh:4-14` | `lifecycle_get_launch_id`, `lifecycle_mark_failed`, `kill_pane_proc`, `unregister` | `cmd_stop`, dispatcher |
| 5 | **[MODIFIED]** `cmd_stop()` | function | `kill.sh:16-33` | `lifecycle_get_launch_id`, `lifecycle_mark_failed` (safety net) | dispatcher |
| 6 | **[MODIFIED]** `cmd_kill_all()` | function | `kill.sh:35-58` | `lifecycle_mark_failed` (loop), `kill-pane`, `find -delete`, `rm -rf` | dispatcher |
| 7 | **[MODIFIED]** `cmd_init()` | function | `cli.sh:33` | `lifecycle_reconcile` | dispatcher |
| 8 | **[MODIFIED]** done-helper generation | generator | `spawn.sh:174` | `_call_fork_launch mark-failed` (with `${_ec}`) | `cmd_spawn_with_meta` |
| 9 | **[MODIFIED]** `lifecycle_get_cli_base()` | function | `lifecycle.sh:91-101` | — | `cmd_spawn_with_meta` |
| 10 | **[BASELINE]** `_call_fork_launch()` | function | `lifecycle.sh:4-30` | CLI subprocess | all lifecycle wrappers |
| 11 | **[BASELINE]** `launch.py` (10 commands) | cli | `src/interfaces/cli/commands/launch.py` | Service → Repository | skill via `_call_fork_launch` |
| 12 | **[BASELINE]** `AgentLaunchLifecycleService` | service | `src/application/services/agent_launch_lifecycle_service.py` | Repository | `launch.py` |
| 13 | **[BASELINE]** `SqliteAgentLaunchRepository` | repository | `src/infrastructure/persistence/repositories/agent_launch_repository.py` | SQLite | Service |

---

## 3. Authority Table

| Surface | Type | Primary Action | State Reads | State Writes | Authority | Competes With | Pipeline | Risk | Confidence | Evidence Class | Decision |
|---------|------|---------------|-------------|-------------|-----------|--------------|----------|------|------------|----------------|----------|
| **[NEW]** `lifecycle_get_launch_id()` | function | Read launch_id from .meta | `.meta` JSON | none | reader-only | none | skill-meta | INFO | high | call-chain | keep |
| **[NEW]** `lifecycle_mark_failed()` | function | Delegate mark-failed to CLI | none | `agent_launch_registry` (via CLI) | delegated | none | lifecycle | INFO | high | call-chain | keep |
| **[NEW]** `lifecycle_reconcile()` | function | Delegate summary to CLI | `agent_launch_registry` (via CLI) | none | reader-only | none | lifecycle | INFO | high | call-chain | keep |
| **[MODIFIED]** `cmd_kill()` | function | Kill agent + mark-failed | `.meta`, `agent_launch_registry` | `agent_launch_registry` (delegated) | delegated | none | kill-lifecycle | INFO | high | call-chain | keep |
| **[MODIFIED]** `cmd_stop()` | function | Stop agent + safety net mark-failed | `.meta`, `.done` | `agent_launch_registry` (delegated, safety net) | delegated | done-helper | stop-lifecycle | INFO | high | call-chain | keep |
| **[MODIFIED]** `cmd_kill_all()` | function | Kill all + bulk mark-failed | all `.meta` files | `agent_launch_registry` (delegated, bulk) | delegated | none | kill-all-lifecycle | INFO | high | call-chain | keep |
| **[MODIFIED]** `cmd_init()` | function | Init + reconcile | `agent_launch_registry` | none | reader-only | none | init | INFO | high | call-chain | keep |
| **[MODIFIED]** done-helper | generator | Dynamic error with exit code | `$_ec` | `agent_launch_registry` (via CLI) | delegated | none | spawn-lifecycle | INFO | high | call-chain | keep |
| **[MODIFIED]** `lifecycle_get_cli_base()` | function | Return CLI base path | `.venv`, `fork` binary | none | reader-only | none | lifecycle | INFO | high | call-chain | keep |
| **[BASELINE]** `_call_fork_launch()` | function | Invoke CLI subprocess | — | — | delegated | none | lifecycle | BASELINE | high | call-chain | — |
| **[BASELINE]** `launch.py` | cli | 10 subcommands | `agent_launch_registry` | `agent_launch_registry` | authoritative | none | lifecycle | BASELINE | high | direct-write | — |

---

## 4. Pipelines Detected

### Pipeline: `agent_launch_registry` DB writes

| Path | Entry Point | Steps | Active | Authority | Notes |
|------|------------|-------|--------|-----------|-------|
| **[BASELINE]** Official (spawn) | `cmd_launch` → `lifecycle_request` | `request` → `confirm-spawning` → `confirm-active` → `done-helper` → `terminate`/`mark-failed` | yes | `SqliteAgentLaunchRepository` | Original spawn path |
| **[MODIFIED]** Kill path | `cmd_kill` → `lifecycle_mark_failed` | `get_launch_id` → `_call_fork_launch mark-failed` | yes | `SqliteAgentLaunchRepository` (delegated) | **NEW**: kill now delegates to CLI |
| **[MODIFIED]** Kill-all path | `cmd_kill_all` → loop → `lifecycle_mark_failed` | iterate `.meta` → `_call_fork_launch mark-failed` × N | yes | `SqliteAgentLaunchRepository` (delegated) | **NEW**: bulk kill delegates to CLI |
| **[MODIFIED]** Stop safety net | `cmd_stop` (is_done) → `lifecycle_mark_failed` | `get_launch_id` → `_call_fork_launch mark-failed` | yes | `SqliteAgentLaunchRepository` (delegated) | **NEW**: safety net for done agents |
| **[NEW]** Init reconcile | `cmd_init` → `lifecycle_reconcile` | `_call_fork_launch summary` | yes | reader-only | Read-only, no writes |
| **[BASELINE]** Reconcile expiry | `reconcile_expired_leases` | Service → `cas_update_status` → QUARANTINED | yes (no caller in skill) | `SqliteAgentLaunchRepository` | Safety net for lease expiry |

**Pipeline type:** single-pipeline. All write paths reach `SqliteAgentLaunchRepository` via `launch.py` → `AgentLaunchLifecycleService`. Skill never writes directly.

### Pipeline: `.meta` files

| Path | Entry Point | Steps | Active | Authority |
|------|------------|-------|--------|-----------|
| **[BASELINE]** Register | `cmd_spawn_with_meta` → `register()` | Write JSON to `.meta` | yes | `register()` |
| **[BASELINE]** Done update | done-helper → `jq` update | Update `exitCode`, `stopReason`, `finished_at` | yes | done-helper |
| **[MODIFIED]** Kill read | `cmd_kill` → `lifecycle_get_launch_id` | Read `launch_id` from `.meta` | yes | reader-only |
| **[MODIFIED]** Kill-all read | `cmd_kill_all` → `jq` loop | Read `launch_id` from each `.meta` | yes | reader-only |

**Pipeline type:** single-pipeline. Only `register()` and `done-helper` write. Kill path is read-only.

### Pipeline: `.done` files

| Path | Entry Point | Steps | Active | Authority |
|------|------------|-------|--------|-----------|
| **[BASELINE]** Done write | done-helper | `printf JSON > .done` | yes | done-helper |
| **[BASELINE]** Trap write | trap-helper | `echo JSON > .done` | yes | trap-helper |
| **[BASELINE]** Kill delete | `cmd_kill_all` | `find -delete .done` | yes | `cmd_kill_all` |

**Pipeline type:** single-pipeline. Sequential (one writer at a time).

---

## 5. Duplications and Conflicts

| # | Conflict Type | Surfaces Involved | State/Artifact | Evidence | Severity | Confidence | Evidence Class |
|---|--------------|------------------|---------------|----------|----------|------------|----------------|
| 1 | **[RESOLVED]** lifecycle-escape | ~~`cmd_kill`~~ → `cmd_kill` + `lifecycle_mark_failed` | `agent_launch_registry` | `kill.sh:8-9` | ~~HIGH~~ → INFO | high | call-chain |
| 2 | **[RESOLVED]** lifecycle-escape | ~~`cmd_kill_all`~~ → `cmd_kill_all` + lifecycle loop | `agent_launch_registry` | `kill.sh:39-43` | ~~HIGH~~ → INFO | high | call-chain |
| 3 | **[RESOLVED]** lifecycle-escape | ~~`cmd_stop` (is_done)~~ → safety net `mark-failed` | `agent_launch_registry` | `kill.sh:24-26` | ~~MEDIUM~~ → INFO | high | call-chain |

No remaining conflicts. All kill paths now delegate through the canonical CLI pipeline.

---

## 6. Side Effects and Contention Points

| # | Side Effect | Triggering Surface | Target | Concurrent With | Coordination | Severity | Confidence | Evidence Class |
|---|-------------|-------------------|--------|-----------------|-------------|----------|------------|----------------|
| 1 | **[MODIFIED]** `mark-failed` CLI call before SIGKILL | `cmd_kill` | `agent_launch_registry` | done-helper (same agent) | Sequential (kill runs after SIGKILL, before unregister) | INFO | high | call-chain |
| 2 | **[MODIFIED]** bulk `mark-failed` calls | `cmd_kill_all` | `agent_launch_registry` × N | — | Sequential loop | INFO | high | call-chain |
| 3 | **[MODIFIED]** safety net `mark-failed` | `cmd_stop` (is_done branch) | `agent_launch_registry` | done-helper (already ran) | `|| true` (idempotent, CAS guard in repository) | INFO | high | call-chain |
| 4 | **[MODIFIED]** legacy `/tmp` cleanup | `cmd_kill_all` | `/tmp/fork-live-registry/`, `/tmp/fork-live-done/` | — | After kill-panes, before log | INFO | high | call-chain |
| 5 | **[NEW]** `summary` CLI call on init | `cmd_init` | `agent_launch_registry` (read) | — | Read-only | INFO | high | call-chain |

**Key observation:** `lifecycle_mark_failed` uses `|| true` — if the CLI call fails (no venv, timeout), the kill proceeds anyway. This is correct: kill is the critical path, lifecycle is best-effort.

**Race condition analysis:** `cmd_kill` calls `lifecycle_mark_failed` BEFORE `unregister` (which deletes `.meta`). This is correct ordering: read launch_id → call lifecycle → then clean up files.

---

## 7. Proposed Official Entrypoints

| Artifact/State | Proposed Authority | Current Authority | Rationale |
|---------------|-------------------|------------------|-----------|
| `agent_launch_registry` DB | `launch.py` CLI (via `_call_fork_launch`) | `launch.py` CLI | **Confirmed.** All skill paths delegate through CLI. No change needed. |
| `.meta` files | `register()` (create) + done-helper (update) | `register()` + done-helper | **Confirmed.** Kill path is read-only on `.meta`. |
| `.done` files | done-helper / trap-helper | done-helper / trap-helper | **Confirmed.** Kill path deletes but does not write. |

No changes proposed. Authority is correct after fixes.

---

## 8. Surfaces That Must Not Mutate Official State

| Surface | Currently Mutates | Should Be | Required Change |
|---------|------------------|-----------|----------------|
| None | — | — | — |

All surfaces correctly delegate or are reader-only. No surfaces mutate state outside their authority.

---

## 9. Prioritized Risks

| Priority | Risk | Severity | Impact | Effort to Fix | Confidence | Evidence Class |
|----------|------|----------|--------|---------------|------------|----------------|
| 1 | `lifecycle_mark_failed` may race with `done-helper` if agent exits between mark-failed call and SIGKILL | LOW | CAS guard prevents double-write; second call is no-op | none (already handled) | high | call-chain |
| 2 | `cmd_kill_all` marks-failed BEFORE reading all `.meta` files into memory — a concurrent agent spawn could write a new `.meta` between the loop and pane kill | LOW | New agent would have launch_id but no lifecycle call on kill | S (read all meta before loop) | low | inferred |
| 3 | `lifecycle_reconcile` only reads summary — does not actually call `reconcile_expired_leases` | LOW | Stale launches only cleaned by lease expiry (5min) | M (add reconcile CLI subcommand) | high | call-chain |
| 4 | `cmd_stop` safety net calls `mark-failed` even when done-helper already called `begin-termination` + `confirm-terminated` — CAS guard prevents corruption but wastes a CLI call | INFO | No data impact, ~250ms wasted latency | S (check DB status first) | high | call-chain |

---

## 10. Recommended Intervention Order

1. **No immediate action required.** All findings are LOW/INFO severity. Authority vacuum (F1) is resolved.
2. **(Future)** Add `reconcile` CLI subcommand that calls `reconcile_expired_leases()` and wire it into `lifecycle_reconcile`. Current implementation only warms the DB connection.
3. **(Future)** Optimize `cmd_stop` safety net: check if launch is already TERMINATED before calling mark-failed.
4. **(Future)** Snapshot `.meta` files in `cmd_kill_all` before loop to prevent race with concurrent spawn.

---

## 11. Uncertainties and Evidence Gaps

| # | Uncertainty | What Cannot Be Determined | What Would Resolve It |
|---|------------|--------------------------|----------------------|
| 1 | Whether `lifecycle_mark_failed` races with done-helper in production (agent exits during kill) | Race timing in real tmux environment | Integration test with concurrent kill + agent exit |
| 2 | Whether `lifecycle_reconcile` summary call has any side effects beyond DB warm | `summary` is documented as read-only but `_call_fork_launch` runs arbitrary CLI code | Code review of `summary` command in `launch.py` (confirmed: pure `count_by_status()`) |
| 3 | Whether `/tmp/fork-live-registry/` and `/tmp/fork-live-done/` are still used by any code | Legacy monolith paths may still be referenced | Grep across all skill scripts for these paths |

---

## 12. Mandatory Checklist (Change-Audit)

| # | Dimension | Status | Details |
|---|-----------|--------|---------|
| 1 | New writers on owned state | **CLEAR** | `lifecycle_mark_failed` is delegated (writes via CLI). `lifecycle_get_launch_id` and `lifecycle_reconcile` are reader-only. |
| 2 | New entrypoints to pipelines | **CLEAR** | Kill path uses existing `_call_fork_launch` → `launch.py` → service → repository. No new CLI commands added. |
| 3 | Evidence-as-authority risk | **CLEAR** | No surface reads logs/reports to make state decisions. |
| 4 | New side effects | **CLEAR** | `mark-failed` CLI calls are intentional, documented, and delegated. `|| true` ensures graceful degradation. |
| 5 | Validation strength change | **CLEAR** | No validation weakened. CAS guard in repository unchanged. |
| 6 | Legacy path status | **CLEAR** | `/tmp/fork-live-registry/` and `/tmp/fork-live-done/` now cleaned in `kill-all` (F4). Not removed but contained. |
| 7 | Authority expansion | **CLEAR** | No surface gains write access to new artifacts. Kill path gains delegated write to `agent_launch_registry` (was missing, now correct). |
| 8 | Pipeline type transition | **CLEAR** | All pipelines remain single-pipeline. Kill path was an authority vacuum (no path), now single-pipeline (delegated via CLI). |

---

## Appendix: Methodology

- [x] **Surface Discovery:** Read kill.sh, lifecycle.sh, cli.sh, spawn.sh, launch.py, service.py, repository.py
- [x] **State Mapping:** Traced all write paths to `agent_launch_registry`, `.meta`, `.done`
- [x] **Authority Assignment:** Classified each surface as authoritative/delegated/reader-only
- [x] **Pipeline Detection:** Traced 6 write paths to DB, 2 to .meta, 3 to .done
- [x] **Conflict Analysis:** Applied H1-H5 core heuristics + H7 (fallback) + H11 (vacuum)
- [x] **Delta Comparison:** Compared baseline (c572f5e) vs current (5bb572a)
- [x] **Report Generation:** Template v2.1, all 11 sections + appendix
