## Status: success

## Summary: Complete technical spec of the persona injection system — 8 asset files analyzed, inject.go strategy documented with per-agent strategy/path mapping, output-style and neutral persona roles documented.

## Artifacts: /tmp/fork-ga-persona.md

# Gentle-AI Persona Injection System — Technical Spec

## 1. Overview

The persona injection system defines a consistent AI personality ("the Gentleman") across 11+ coding agents (Claude, OpenCode, Kiro, Cursor, Gemini, VS Code Copilot, Windsurf, Codex, Kilocode, Qwen, Antigravity). Each agent gets a tailored persona variant written to its system prompt file via an agent-specific injection strategy.

**Core files:**

- `internal/components/persona/inject.go` — the `Inject()` function (main orchestrator)
- `internal/components/persona/inject_test.go` — 25+ tests covering injection, idempotency, auto-heal, legacy cleanup

---

## 2. Persona IDs

| PersonaID                | Value         | Behavior                                            |
| ------------------------ | ------------- | --------------------------------------------------- |
| `model.PersonaGentleman` | `"gentleman"` | Full Gentleman persona + output style (Claude only) |
| `model.PersonaNeutral`   | `"neutral"`   | Same teacher philosophy, no regional language       |
| `model.PersonaCustom`    | `"custom"`    | No injection — user keeps their own config          |

---

## 3. Base Persona Structure (`generic/persona-gentleman.md`)

The base Gentleman persona has 8 sections:

| Section          | Content                                                                                            |
| ---------------- | -------------------------------------------------------------------------------------------------- |
| `## Rules`       | 7 hard rules: no AI attribution, no builds, wait on questions, verify claims, propose alternatives |
| `## Personality` | Senior Architect, 15+ years, GDE & MVP. Passionate teacher. Frustrated by shortcuts — from caring. |
| `## Language`    | Spanish → Rioplatense voseo ("loco", "hermano", "dale"). English → warm energy ("dude", "come on") |
| `## Tone`        | Passionate + direct, from CARING. 3-step correction pattern. CAPS for emphasis.                    |
| `## Philosophy`  | 4 pillars: CONCEPTS > CODE, AI IS A TOOL, SOLID FOUNDATIONS, AGAINST IMMEDIACY                     |
| `## Expertise`   | Clean/Hexagonal/Screaming Architecture, testing, atomic design, LazyVim, Tmux, Zellij              |
| `## Behavior`    | Push back on code without context, architecture analogies, ruthless correction with WHY            |
| `## Skills`      | Auto-load table: `go-testing` for Go tests/Bubbletea, `skill-creator` for new AI skills            |

---

## 4. Per-Agent Variants — Diff Table

### 4.1 Claude Variant (`claude/persona-gentleman.md`)

| Difference           | Detail                                                                                                                      |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| **Rules**            | Adds: `Never use cat/grep/find/sed/ls. Use bat/rg/fd/sd/eza instead`                                                        |
| **Skills table**     | Header changes to `Read this file` instead of `Skill to load`; paths become absolute `~/.claude/skills/go-testing/SKILL.md` |
| **Skills directive** | "read the corresponding skill file" instead of "load the corresponding skill"                                               |
| **Everything else**  | Identical to generic                                                                                                        |

### 4.2 OpenCode Variant (`opencode/persona-gentleman.md`)

| Difference          | Detail                                                    |
| ------------------- | --------------------------------------------------------- |
| **Rules**           | Identical to generic — no extra rules                     |
| **Skills table**    | Identical to generic                                      |
| **Everything else** | Byte-for-byte identical to `generic/persona-gentleman.md` |

### 4.3 Kiro Variant (`kiro/persona-gentleman.md`)

| Difference          | Detail                                                    |
| ------------------- | --------------------------------------------------------- |
| **Rules**           | Identical to generic — no extra rules                     |
| **Skills table**    | Identical to generic                                      |
| **Everything else** | Byte-for-byte identical to `generic/persona-gentleman.md` |

### 4.4 Agents Using Generic Directly

These agents receive `generic/persona-gentleman.md` without any agent-specific variant:

| Agent           | Strategy                                                                                       |
| --------------- | ---------------------------------------------------------------------------------------------- |
| Gemini CLI      | `StrategyFileReplace` → `~/.gemini/GEMINI.md`                                                  |
| Cursor          | `StrategyFileReplace` → `~/.cursor/rules/gentle-ai.mdc`                                        |
| VS Code Copilot | `StrategyInstructionsFile` → `~/.config/github-copilot/instructions/gentle-ai.instructions.md` |
| Windsurf        | `StrategyAppendToFile` → `~/.windsurf/rules/global_rules.md`                                   |
| Codex           | `StrategyFileReplace` → `~/.codex/agents.md`                                                   |
| Kilocode        | `StrategyFileReplace` → `~/.config/kilo/AGENTS.md`                                             |
| Qwen            | `StrategyFileReplace` → `~/.qwen/QWEN.md`                                                      |
| Antigravity     | `StrategyAppendToFile` → `~/.gemini/GEMINI.md`                                                 |

---

## 5. Persona Neutral (`generic/persona-neutral.md`)

Used when the user selects `PersonaNeutral`. Same 8-section structure as Gentleman with these differences:

| Section         | Gentleman                              | Neutral                                                                                                                                 |
| --------------- | -------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| **Language**    | Rioplatense voseo + warm English slang | "Always respond in the same language the user writes in. Use a warm, professional, and direct tone. No slang, no regional expressions." |
| **Tone**        | Identical                              | Identical (verified by test `TestNeutralAndGentlemanToneSectionsMatch`)                                                                 |
| **Personality** | Identical                              | Identical                                                                                                                               |
| **Philosophy**  | Identical                              | Identical                                                                                                                               |
| **Behavior**    | Identical                              | Identical                                                                                                                               |
| **Skills**      | Identical                              | Identical                                                                                                                               |
| **Rules**       | Identical                              | Identical                                                                                                                               |
| **Expertise**   | Identical                              | Identical                                                                                                                               |

**Key insight:** Neutral is Gentleman minus regional language personality. The teacher passion and philosophy remain intact.

---

## 6. Output Style (`claude/output-style-gentleman.md`)

This is a **Claude-only** companion file that provides more detailed behavioral guidance than the system prompt persona. It's written to `~/.claude/output-styles/gentleman.md` and activated via `settings.json` merge.

### Structure

| Section                           | Purpose                                                                                        |
| --------------------------------- | ---------------------------------------------------------------------------------------------- |
| **YAML Frontmatter**              | `name: Gentleman`, `description: ...`, `keep-coding-instructions: true`                        |
| **Core Principle**                | "Be helpful FIRST. You're a mentor, not an interrogator." — calibrates the push-back intensity |
| **Personality**                   | Expanded version of system prompt personality                                                  |
| **Language Rules**                | Explicit anti-sarcasm rule: "NEVER sarcastically or mockingly. No air quotes"                  |
| **Tone**                          | Adds "rhetorical questions", "repeat for emphasis", "MENTOR not drill sergeant"                |
| **Philosophy**                    | Expanded with inline quotes for each pillar                                                    |
| **Being a Collaborative Partner** | NEW section — calibrates when to challenge vs when to just help                                |
| **Speech Patterns**               | NEW section — rhetorical questions, repetition, anticipation, impact closings                  |
| **When Asking Questions**         | Reinforces the "STOP after asking" rule                                                        |

### How it complements the persona

The system prompt persona (CLAUDE.md section) is the **identity definition** — who the agent IS. The output style is the **behavioral calibration** — how the agent SHOULD behave in practice. The output style adds nuance that would bloat the system prompt:

- Anti-sarcasm guardrails
- Help-first default (don't challenge every message)
- Specific speech patterns to emulate
- Collaborative partner guidelines

---

## 7. Injection Strategies

### 7.1 Strategy Enum

| Strategy                   | Value      | Description                                                                               |
| -------------------------- | ---------- | ----------------------------------------------------------------------------------------- |
| `StrategyMarkdownSections` | `iota` (0) | Uses `<!-- gentle-ai:persona -->` markers to inject/replace sections within a larger file |
| `StrategyFileReplace`      | 1          | Replaces entire system prompt file content                                                |
| `StrategyAppendToFile`     | 2          | Appends persona content to existing file (with idempotency check)                         |
| `StrategyInstructionsFile` | 3          | Writes `.instructions.md` with YAML frontmatter (`applyTo: "**"`)                         |
| `StrategySteeringFile`     | 4          | Writes steering file with `inclusion: always` frontmatter                                 |

### 7.2 Per-Agent Strategy and Path Mapping

| Agent           | Strategy                   | System Prompt File                                                | Output Styles                                |
| --------------- | -------------------------- | ----------------------------------------------------------------- | -------------------------------------------- |
| Claude Code     | `StrategyMarkdownSections` | `~/.claude/CLAUDE.md`                                             | Yes (`~/.claude/output-styles/gentleman.md`) |
| OpenCode        | `StrategyFileReplace`      | `~/.config/opencode/AGENTS.md`                                    | No                                           |
| Kiro IDE        | `StrategySteeringFile`     | `~/.kiro/steering/gentle-ai.md`                                   | No                                           |
| Cursor          | `StrategyFileReplace`      | `~/.cursor/rules/gentle-ai.mdc`                                   | No                                           |
| Gemini CLI      | `StrategyFileReplace`      | `~/.gemini/GEMINI.md`                                             | No                                           |
| VS Code Copilot | `StrategyInstructionsFile` | `~/.config/github-copilot/instructions/gentle-ai.instructions.md` | No                                           |
| Windsurf        | `StrategyAppendToFile`     | `~/.windsurf/rules/global_rules.md`                               | No                                           |
| Codex           | `StrategyFileReplace`      | `~/.codex/agents.md`                                              | No                                           |
| Kilocode        | `StrategyFileReplace`      | `~/.config/kilo/AGENTS.md`                                        | No                                           |
| Qwen            | `StrategyFileReplace`      | `~/.qwen/QWEN.md`                                                 | No                                           |
| Antigravity     | `StrategyAppendToFile`     | `~/.gemini/GEMINI.md`                                             | No                                           |

---

## 8. Inject.go Algorithm

```
Inject(homeDir, adapter, persona):
  1. Early exits:
     - adapter.SupportsSystemPrompt() == false → return empty
     - persona == PersonaCustom → return empty

  2. Resolve content:
     - personaContent(agent, persona) → reads embedded asset
     - Gentleman: agent-specific asset first, then generic fallback
     - Neutral: always "generic/persona-neutral.md"

  3. Write persona based on strategy:
     - StrategyMarkdownSections: read file → StripLegacyPersonaBlock → StripLegacyATLBlock → InjectMarkdownSection → WriteFileAtomic
     - StrategyFileReplace: read file → (OpenCode: conditional legacy stripping) → (non-Gentleman: preserveManagedSections) → write
     - StrategyInstructionsFile: cleanLegacyVSCodePersona → preserveManagedSections → wrapInstructionsFile (adds YAML frontmatter) → write
     - StrategySteeringFile: preserveManagedSections → wrapSteeringFile (adds `inclusion: always` frontmatter) → write
     - StrategyAppendToFile: read file → idempotency check (skip if content already present) → append with separator → write

  4. OpenCode/Kilocode agent definitions (Tab-switchable agents):
     - Merge `openCodeAgentOverlayJSON` into settings.json
     - Defines "gentleman" (primary) and "sdd-orchestrator" (Tab-switchable) agents
     - Both reference `{file:./AGENTS.md}` for system prompt

  5. Gentleman-only: Output style (Claude only):
     - Write `claude/output-style-gentleman.md` → `~/.claude/output-styles/gentleman.md`
     - Merge `{"outputStyle": "Gentleman"}` into `~/.claude/settings.json`

  6. Return InjectionResult{Changed, Files}
```

---

## 9. Auto-Heal System

The injector includes migration logic for older installations:

| Heal                       | Trigger                                                                                          | Action                                                                                                                            |
| -------------------------- | ------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------- |
| **Legacy persona block**   | `StrategyMarkdownSections`: free-text persona content before markers                             | `StripLegacyPersonaBlock()` — requires ALL 3 fingerprints (`## Rules`, `## Personality`, `## Language`) to match before stripping |
| **Legacy ATL block**       | All strategies: standalone Agent Teams Lite markers                                              | `StripLegacyATLBlock()` — strips `<!-- BEGIN:agent-teams-lite -->` blocks                                                         |
| **Managed persona legacy** | `StrategyFileReplace` + OpenCode: existing file has `<!-- gentle-ai:persona -->` marker          | `shouldStripManagedLegacyPersona()` — only strips when managed marker already exists (proof of installer ownership)               |
| **Exact legacy asset**     | `StrategyFileReplace` + OpenCode: file is byte-for-byte match of known asset                     | `isExactLegacyPersonaAsset()` — safe full replacement                                                                             |
| **VS Code legacy path**    | `StrategyInstructionsFile`: `~/.github/copilot-instructions.md` exists with persona fingerprints | `cleanLegacyVSCodePersona()` — removes old file only if it matches ALL fingerprints                                               |

### Safety Guardrails

- **Never strip user content that merely looks like persona** — requires ALL fingerprints, not just one
- **ATL markers do NOT enable persona stripping** — only `<!-- gentle-ai:persona -->` does
- **OpenCode preserves user preface** — even with `## Rules` + `## Personality` headings, if no managed marker exists the content is treated as user-authored
- **`preserveManagedSections()`** — when switching from Gentleman to Neutral, SDD/engram sections survive

---

## 10. Idempotency

Every strategy is idempotent:

- `StrategyMarkdownSections`: `InjectMarkdownSection` replaces in-place by marker ID
- `StrategyFileReplace`: `WriteFileAtomic` compares bytes — no change = no write
- `StrategyAppendToFile`: explicit `strings.Contains` check before appending
- `StrategyInstructionsFile`: `WriteFileAtomic` byte comparison
- `StrategySteeringFile`: `WriteFileAtomic` byte comparison

Verified by dedicated tests: `TestInjectClaudeIsIdempotent`, `TestInjectOpenCodeIsIdempotent`, `TestInjectWindsurfIsIdempotent`, `TestInjectVSCodeIdempotentAfterHeal`, `TestInjectNeutralIdempotentWithManagedSections`.

---

## 11. Test Coverage Summary

| Category                     | Count | Key Tests                                                                                                       |
| ---------------------------- | ----- | --------------------------------------------------------------------------------------------------------------- |
| Basic injection              | 6     | Claude, OpenCode, Cursor, Gemini, VS Code, Windsurf                                                             |
| Neutral persona              | 5     | Content verification, no output style, managed section preservation                                             |
| Custom persona               | 2     | Claude and OpenCode do-nothing                                                                                  |
| Idempotency                  | 5     | Claude, OpenCode, Windsurf, VS Code, Neutral+managed                                                            |
| Auto-heal (Claude)           | 3     | Stale free-text, persona-only file, non-persona content preservation                                            |
| Auto-heal (VS Code)          | 3     | Legacy path cleanup, user file preservation, idempotent after heal                                              |
| OpenCode edge cases          | 5     | User content preservation, lookalike protection, ATL+preface, exact legacy asset, managed markers above preface |
| Managed section preservation | 3     | OpenCode neutral switch, VS Code neutral switch, marker-at-byte-zero                                            |
| Output style                 | 3     | File write, settings merge, key preservation                                                                    |

**Total: ~35 test functions** covering normal flow, edge cases, migrations, and safety.

---

## 12. Data Flow Diagram

```
                    ┌─────────────────────┐
                    │   personaContent()   │
                    │                     │
                    │  gentleman:         │
                    │   claude  → claude/ │
                    │   opencode→ opencode│
                    │   kiro    → kiro/   │
                    │   other   → generic │
                    │  neutral:            │
                    │   always → generic/ │
                    │  custom:             │
                    │   return ""         │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │   Inject() switch    │
                    │   on strategy        │
                    └──────────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
   MarkdownSections      FileReplace            AppendToFile
   (Claude)              (OpenCode, Cursor,     (Windsurf,
        │               Gemini, Codex, etc.)    Antigravity)
        │                      │                      │
   StripLegacy           StripLegacy             Idempotency
   + InjectSection       + preserveManaged        + append
        │               + write                      │
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Post-injection      │
                    │                      │
                    │  OpenCode/Kilocode:  │
                    │   merge agent defs   │
                    │                      │
                    │  Claude + Gentleman: │
                    │   write output-style │
                    │   merge settings     │
                    └─────────────────────┘
```

## Next: none

## Risks: none
