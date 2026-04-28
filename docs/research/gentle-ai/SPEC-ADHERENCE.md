# Gentle-AI Adherence Mechanisms — How They Ensure the LLM Follows Instructions

**Date**: 2026-04-28 | **Purpose**: Understand gentle-ai's adherence techniques for tmux_fork improvement
**Source**: 6 files analyzed (sdd-orchestrator.md × 2, engram-protocol.md, persistence-contract.md, sdd-phase-common.md, skill-resolver.md, section.go)

---

## The Core Question

Gentle-ai is a Go binary that generates agent instruction files for 11 different AI tools. It does NOT run alongside the LLM — it writes files and exits. So how does it ensure adherence?

**Answer**: It doesn't enforce at runtime. It ensures adherence through **structural design** — the instructions are architected to be self-reinforcing, self-correcting, and compaction-safe.

---

## Mechanism 1: Self-Reinforcing Instructions (Mandatory Markers)

Every instruction that MUST be followed uses these textual markers:

| Marker                   | Effect                                                                              |
| ------------------------ | ----------------------------------------------------------------------------------- |
| `MANDATORY`              | Bold emphasis — "Do NOT skip this check"                                            |
| `This is NON-NEGOTIABLE` | Explicit escalation — "Do not rely on the sub-agent discovering this independently" |
| `Do NOT ...`             | Explicit prohibition — "Do NOT invoke them as skills"                               |
| `ALWAYS` / `NEVER`       | Binary rules — no room for interpretation                                           |
| `CRITICAL`               | Warning header — "Skipping this BREAKS the pipeline"                                |
| `WITHOUT BEING ASKED`    | Proactive trigger — don't wait for user instruction                                 |
| `IMMEDIATELY`            | Urgency — prevents deferral                                                         |

**Pattern**: They repeat consequences. Not just "do X" but "do X because if you don't, Y breaks."

Example from persistence-contract.md:

```
If you return without calling mem_save, the next phase CANNOT find your
artifact and the pipeline BREAKS.
```

### Our Gap

Our SKILL.md and protocol.md use some markers but inconsistently. The protocol.md uses `MANDATORY` in headers but many critical instructions lack consequence chains.

---

## Mechanism 2: Self-Correction Loops (Feedback Mechanisms)

Gentle-ai builds explicit self-correction into the orchestrator:

### Skill Resolution Feedback Loop

```
After every delegation, check skill_resolution field:
- injected → all good
- fallback-registry → skill cache was lost. Re-read registry IMMEDIATELY.
- none → no skills loaded. Re-read registry IMMEDIATELY.
```

**Why it works**: The orchestrator is told to CHECK after every delegation, not just trust that it did the right thing. This catches compaction-induced context loss.

### Apply-Progress Continuity

```
When launching sdd-apply for a continuation batch:
1. Search for existing apply-progress
2. If found, tell the sub-agent: "PREVIOUS PROGRESS EXISTS. You MUST read it first."
3. If not found, no special instruction needed.
```

**Why it works**: Prevents silent data loss across batches. The orchestrator doesn't assume — it checks.

### Our Gap

We have `enforce-envelope` as post-launch validation, but no **orchestrator-level feedback loop**. After spawning, we validate the output file exists but don't check whether the sub-agent followed all instructions (e.g., did it use `-nc`? did it persist to memory?).

---

## Mechanism 3: Result Contract (Structured Output)

Every sub-agent MUST return a structured envelope:

```markdown
**Status**: success|partial|blocked
**Summary**: <1-3 sentences>
**Artifacts**: <paths or none>
**Next**: <recommended next phase>
**Risks**: <risks or None>
**Skill Resolution**: injected|fallback-registry|fallback-path|none
```

**Why it works**:

1. The envelope format is enforced by the prompt AND the `enforce-envelope` script
2. The `skill_resolution` field is the feedback mechanism — it tells the orchestrator whether skills were loaded correctly
3. The `status` field prevents ambiguous results — no "I think it worked"

### Our Gap

We have the envelope (`## Status: success|partial|blocked`) but our envelope is simpler. We don't include `skill_resolution` or `next_recommended`. Our `enforce-envelope` checks format but not content quality.

---

## Mechanism 4: Context Budget + Progressive Disclosure

Gentle-ai uses a strict context budget:

1. **SKILL.md** (entry point): ~80 lines. Just the table of contents + search hints.
2. **Phase-specific files**: Loaded on-demand via Trifecta search.
3. **Skill Resolver**: Pre-digested compact rules injected into sub-agents (50-150 tokens per skill).
4. **Sub-agents NEVER read SKILL.md files** — they receive pre-digested rules.

**Why it works**: The orchestrator never loads the full protocol into context. It loads what it needs, when it needs it. This prevents context window exhaustion AND prevents the orchestrator from getting confused by too many instructions.

### Our Gap

Our SKILL.md is already compact (~80 lines) with Trifecta-based loading. But our sub-agents sometimes load AGENTS.md (which caused the Role Confusion bug). We added `-nc` to fix this, but we don't pre-digest skill rules into sub-agent prompts — we just tell them "you are a {role}".

---

## Mechanism 5: Executor Boundary (Role Isolation)

From `sdd-phase-common.md`:

```
Executor boundary: every SDD phase agent is an EXECUTOR, not an orchestrator.
Do the phase work yourself. Do NOT launch sub-agents, do NOT call delegate/task,
and do NOT bounce work back unless the phase skill explicitly says to stop and
report a blocker.
```

**Why it works**: Explicit boundary prevents the #1 failure mode — an executor agent trying to orchestrate. This is the same bug we had (Orchestrator Hallucination).

### Our Status

We fixed this with `-nc` flag. But we could make it even more explicit in the prompt template — adding an explicit "You are NOT the orchestrator" line.

---

## Mechanism 6: Idempotent Injection (Marker-Based)

From `section.go` — `InjectMarkdownSection`:

```go
// Markers: <!-- gentle-ai:SECTION_ID --> ... <!-- /gentle-ai:SECTION_ID -->
// If section exists → replace content. If not → append.
// Content outside markers is NEVER touched.
```

**Why it works**: Re-running the installer doesn't duplicate or corrupt. The LLM sees exactly one copy of each instruction block. No "which version do I follow?" confusion.

### Our Gap

We don't have marker-based injection (we're a Pi runtime, not a Go binary). But the principle applies: our AGENTS.md should have clear section boundaries that the LLM can identify. We already use `## Section` headers, which is good.

---

## Mechanism 7: Consequence Chains

Gentle-ai links every mandatory action to its consequence:

| Instruction                                          | Consequence Chain                                                                                          |
| ---------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| "You MUST call mem_save"                             | "If you return without calling mem_save, the next phase CANNOT find your artifact and the pipeline BREAKS" |
| "You MUST read full content via mem_get_observation" | "Skipping this produces wrong output"                                                                      |
| "You MUST check skill_resolution"                    | "Do NOT ignore fallback reports — they indicate the orchestrator dropped context"                          |
| "Do NOT ask the user — just run init silently"       | "This ensures testing capabilities are always detected and cached"                                         |

**Why it works**: LLMs are instruction-following machines. When you explain WHY a rule exists, they follow it more reliably. The consequence chain makes the instruction grounded rather than arbitrary.

### Our Gap

Our protocol.md has some consequences but many rules are bare. Example:

```
"ALWAYS use @file for prompts" — but no consequence chain.
```

Should be:

```
"ALWAYS use @file for prompts. Inline multi-line prompts have ~40% failure rate
because the shell breaks on quotes and the agent receives a truncated prompt."
```

---

## Mechanism 8: Session-Level Caching with Cache-Miss Recovery

From the orchestrator:

```
Orchestrator skill resolution (do once per session):
1. mem_search("skill-registry") → cache compact rules
2. Fallback: read .atl/skill-registry.md
3. If no registry → warn user and proceed without

For each sub-agent launch:
- Inject cached compact rules as text (not paths)
- If cache lost (compaction) → re-read immediately
```

**Why it works**: The orchestrator does NOT re-read the registry on every delegation. It caches once. But if it detects a cache miss (via `skill_resolution` feedback), it self-heals immediately.

### Our Gap

We don't have a skill registry or compact rules injection. Our sub-agents get role instructions + task description, but no project-specific standards.

---

## Summary: Adherence Scorecard

| Mechanism                  | Gentle-AI                                               | tmux_fork                        | Gap       |
| -------------------------- | ------------------------------------------------------- | -------------------------------- | --------- |
| Self-reinforcing markers   | ✅ `MANDATORY`, `NON-NEGOTIABLE`, consequence chains    | ⚠️ Some markers, missing chains  | Medium    |
| Self-correction loops      | ✅ skill_resolution feedback, apply-progress continuity | ❌ No feedback mechanism         | Large     |
| Structured result contract | ✅ 6-field envelope with feedback                       | ⚠️ 4-field envelope, no feedback | Medium    |
| Context budget             | ✅ 80-line SKILL.md + Trifecta on-demand                | ✅ Same pattern                  | None      |
| Executor boundary          | ✅ Explicit "you are NOT orchestrator"                  | ✅ Fixed with `-nc`              | Fixed     |
| Idempotent injection       | ✅ Marker-based (Go binary)                             | ⚠️ Manual edits (Pi runtime)     | By design |
| Consequence chains         | ✅ Every MANDATORY has a "because..."                   | ❌ Many bare rules               | Large     |
| Session caching + recovery | ✅ Cache once, self-heal on miss                        | ❌ No skill registry/cache       | Medium    |

---

## Actionable Improvements for tmux_fork

### P0: Add Consequence Chains to Protocol

Every `ALWAYS`/`NEVER`/`MANDATORY` in protocol.md should have a "because..." explaining the failure mode.

### P1: Add Feedback Loop to Sub-agent Envelope

Extend the sub-agent envelope to include:

```
## Instructions Followed: yes|partial|unknown
## Context Loaded: nc-flag|full|unknown
```

And the orchestrator should check this after every delegation.

### P1: Add Explicit Executor Boundary to Prompt Template

Add to the prompt template:

```
# Boundary: You are an EXECUTOR. You are NOT the orchestrator.
# Do NOT launch sub-agents, do NOT search memory for session state,
# do NOT try to recover from compaction. Do YOUR task and write YOUR output.
```

### P2: Add Skill Registry (Compact Rules Injection)

Consider building a lightweight skill registry that the orchestrator caches once per session and injects as compact rules into every sub-agent prompt. This prevents sub-agents from working without project context.

### P2: Add Self-Correction to Orchestrator

After compaction, the orchestrator should:

1. Recover state from memory
2. Re-read skill registry if it was cached
3. Check if any in-flight delegations lost their skill injection
4. Re-inject if needed
