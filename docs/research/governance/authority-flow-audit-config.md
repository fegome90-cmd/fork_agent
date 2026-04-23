# Authority Flow Audit: Config System — Consolidated Report

> **Date:** 2026-04-23
> **Mode:** repo-audit (Tier 2)
> **Target:** Config authority chain for governance feature flag
> **Agents:** 3 parallel (writers, consumers, SSOT)

---

## Executive Summary

**`.fork_agent.yaml` is dead config.** ForkAgentConfig.load() exists but has zero runtime consumers. The DI container (`_container_di.py:156`) hardcodes all `WorkspaceConfig` defaults. Adding `governance: bool` to `WorkspaceConfigModel` would be cosmetic — the field would never be read.

**GOVERNANCE=1 env var** is the correct mechanism, following the established `FORK_HYBRID=1` pattern used by 18 CLI commands.

---

## Findings

### F1: Dead Config — `.fork_agent.yaml` (CRITICAL, HIGH confidence)

| Evidence | Detail |
|----------|--------|
| `ForkAgentConfig.load()` | Reads YAML but nobody calls it for runtime values |
| `ForkAgentConfig.save()` | Has **zero callers** in entire codebase |
| `.fork_agent.yaml` file | **0 bytes** (empty) |
| DI container | Constructs `WorkspaceConfig` with hardcoded defaults |

**Classification:** Orphaned authority — exists but bypassed.

### F2: Default Drift — auto_cleanup (HIGH, HIGH confidence)

| Location | Value |
|----------|-------|
| `_container_di.py:156` | `auto_cleanup=True` |
| `workspace_commands.py:28` | `auto_cleanup=False` |
| `WorkspaceConfigModel` | `auto_cleanup=False` (Pydantic default) |

Two code paths produce different runtime behavior for the same field.

### F3: `.fork/init.yaml` is Orphan (HIGH, HIGH confidence)

- Exists on disk with project metadata
- **Zero references in `src/`** — not imported, not loaded
- Only referenced in research docs
- Created manually or by a defunct script

### F4: ConfigLoader is Dead Code (MEDIUM, HIGH confidence)

- `ConfigLoader.get_config()` has **zero callers** in production code
- Exports `FORK_AGENT_DEBUG`, `FORK_AGENT_SHELL`, `FORK_AGENT_DEFAULT_TERMINAL`
- Reads from `.env` but nothing consumes the results

### F5: FORK_* Env Vars are the Live Pattern (LOW severity, HIGH confidence)

- 18 CLI commands check `FORK_HYBRID` via `os.environ.get()`
- Pattern: inline check, no config model, no DI
- This is the correct pattern for `GOVERNANCE=1`

### F6: Two Disconnected Config Hierarchies (HIGH, HIGH confidence)

1. **Domain entities** (`WorkspaceConfig` dataclass): Used by LayoutResolver, WorkspaceManager
2. **Infrastructure config** (`ForkAgentConfig` Pydantic): Loaded from YAML but never injected into services

The bridge between them happens only in `workspace_commands.py` for display — not for runtime behavior.

---

## Risk Matrix

| Finding | Severity | Confidence | Decision |
|---------|----------|------------|----------|
| F1: Dead config | CRITICAL | HIGH | Do NOT add governance to WorkspaceConfigModel |
| F2: Default drift | HIGH | HIGH | Separate work order: fix DI → read from YAML |
| F3: Orphan init.yaml | HIGH | HIGH | Separate work order: merge or delete |
| F4: Dead ConfigLoader | MEDIUM | HIGH | Separate work order: integrate or delete |
| F5: FORK_* pattern | LOW | HIGH | Use as governance pattern |
| F6: Disconnected hierarchies | HIGH | HIGH | Consequence of F1+F2 |

---

## Decisions

| Decision | Rationale |
|----------|-----------|
| Governance = env var only (GOVERNANCE=1) | Follows live pattern (FORK_HYBRID), no dead config dependency |
| Do NOT add governance to WorkspaceConfigModel | Would be cosmetic — 0 runtime consumers |
| Config system fix = separate work order | Out of scope for governance implementation, but must be tracked |
| Protocol.md text is the governance authority | AI orchestrator reads SKILL.md, not Python config |

## Deferred Work Orders

- **WO-001: Wire ForkAgentConfig.load() into DI container** — Make YAML the true SSOT
- **WO-002: Fix auto_cleanup default drift** — Single source for defaults
- **WO-003: Decide on .fork/init.yaml** — Merge into .fork_agent.yaml or formalize role
- **WO-004: Delete or integrate ConfigLoader** — Dead code hazard

---

## Sources

- `/tmp/fork-audit-config-writers.md` — Agent 1: Writer tracing (77 lines)
- `/tmp/fork-audit-config-consumers.md` — Agent 2: Consumer analysis (59 lines)
- `/tmp/fork-audit-config-ssot.md` — Agent 3: SSOT verification (91 lines)
