# Authority Flow Audit: Implementation Plan — Consolidated Report

> **Date:** 2026-04-23
> **Mode:** repo-audit (Tier 2) on the plan itself
> **Agents:** 3 parallel (artifact writers, pipeline conflicts, SDD verification)
> **Target:** `docs/research/governance/implementation-plan.md` (647→718 lines)

---

## Executive Summary

The plan is **safe to execute** with 4 defects fixed inline and 7 open issues tracked.

### What Changed in the Plan
| Change | Reason |
|--------|--------|
| Run 6 CANCELLED | `.fork/schema.yaml` is false authority — no validator, no consumer |
| `[P]` markers removed | Invented convention, sdd-tasks produces flat markdown |
| Persistence API fixed | `mem_save()` MCP tool, not `memory save` CLI |
| Two-step retrieval documented | `mem_get_observation(id)` required for full content |
| SDD prerequisites added | sdd-init prerequisite, return envelope contract, degraded modes |

### What Was Already Correct
- CLOOP dispatch via skill-hub ✅
- topic_key convention ✅
- sdd-gate-skill 3-agent dispatch ✅
- sdd-archive merge logic ✅
- Compliance matrix format ✅
- GOVERNANCE=1 env var pattern (as advisory) ✅

### Open Issues (tracked in plan, not blocking)
- O1: GOVERNANCE=1 advisory (accept as-is)
- O2: anchor_dope gates conditional on script existence
- O3: Per-gate recovery actions (define in Run 3)
- O4: Human override traceability (add logging)
- O5: Quality loop tmux guard
- O6: MAX_ITERATIONS escalation
- O7: Context budget allocation for SDD artifacts

### Artifact Authority Map (post-implementation)

```
SKILL.md (entry point — TRUE AUTHORITY)
  └─ references protocol.md (phase SSOT — TRUE AUTHORITY)
       ├─ references governance.md (advisory — EVIDENCE)
       │    └─ artifact DAG as markdown table (reference, not config)
       └─ references sdd-bridge.md (contract — EVIDENCE)
            └─ references sdd-* skills (independent — TRUE AUTHORITY for SDD lifecycle)
```

No double-writers. No circular references. No false SSOTs (schema YAML cancelled).

---

## Sources

- `/tmp/fork-plan-audit-writers.md` — Agent PA1: Artifact writers (317 lines)
- `/tmp/fork-plan-audit-pipelines.md` — Agent PA2: Pipeline conflicts (291 lines)
- `/tmp/fork-plan-audit-sdd.md` — Agent PA3: SDD verification (43 lines)
