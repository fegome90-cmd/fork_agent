# OpenSpec Deep Dive — Core Architecture & Spec System

## Executive summary

OpenSpec is a repo-scoped, spec-driven change management system built around two persistent stores:

- `openspec/specs/` = canonical source of truth for current behavior
- `openspec/changes/` = isolated proposed changes, each with planning artifacts and delta specs

The newer **OPSX** model is not a separate file format. It is the **workflow/command system** (`/opsx:*`) plus schema-driven artifact generation. The actual persisted artifacts are still mostly **Markdown** (`proposal.md`, `design.md`, `tasks.md`, `spec.md`) plus **YAML** (`config.yaml`, `schema.yaml`, `.openspec.yaml`).

The core design idea is:

1. keep canonical specs stable in `openspec/specs/`
2. express changes as deltas in `openspec/changes/<change>/specs/...`
3. validate both the delta and the rebuilt canonical spec
4. merge on sync/archive
5. preserve full change history in `openspec/changes/archive/`

---

# Area 1 — Core model and lifecycle

## 1) Actual lifecycle

The practical lifecycle is:

1. **`openspec init`**
   - creates `openspec/specs/`, `openspec/changes/`, `openspec/changes/archive/`
   - sets up tool integrations (skills and/or command files)
   - optionally creates `openspec/config.yaml`

2. **Optional exploration**
   - `/opsx:explore`
   - no canonical artifact is required here; this is pre-change reasoning and investigation

3. **Start a change**
   - default/core path: `/opsx:propose`
   - expanded path: `/opsx:new`, then `/opsx:continue` or `/opsx:ff`

4. **Create planning artifacts**
   - `proposal.md`
   - delta specs under `specs/<capability>/spec.md`
   - `design.md`
   - `tasks.md`
   - ordering is schema-driven, not hardcoded phase-gated

5. **Validate / inspect while planning**
   - `openspec status`
   - `openspec instructions`
   - `openspec validate`
   - `openspec show`, `list`, `view`

6. **Implement**
   - `/opsx:apply`
   - reads `tasks.md`, executes work, marks checkboxes

7. **Optional verification / sync**
   - `/opsx:verify` = implementation-vs-artifact review
   - `/opsx:sync` = merge delta specs into main specs without archiving

8. **Archive**
   - `/opsx:archive` or `openspec archive`
   - validates, applies spec deltas, then moves change to `changes/archive/YYYY-MM-DD-name/`

So the most accurate lifecycle is:

```text
init
→ explore (optional)
→ propose | new
→ continue | ff
→ validate/status/instructions (as needed)
→ apply
→ verify (optional)
→ sync (optional)
→ archive
```

## 2) Core architectural split

OpenSpec is built around a clean separation:

- **Specs** = current truth
- **Changes** = proposed modifications

This allows:

- parallel active changes
- review of changes before they affect the base specs
- archival history with full proposal/design/tasks context
- brownfield-friendly updates via deltas instead of rewriting whole specs

## 3) Default vs expanded workflow

### Core profile (default)

- `/opsx:propose`
- `/opsx:explore`
- `/opsx:apply`
- `/opsx:archive`

### Expanded workflow

- `/opsx:new`
- `/opsx:continue`
- `/opsx:ff`
- `/opsx:verify`
- `/opsx:sync`
- `/opsx:bulk-archive`
- `/opsx:onboard`

The default install is intentionally smaller. The expanded set is enabled via profile/config and then materialized by `openspec update`.

---

# Area 2 — OPSX and artifact format

## 1) What “OPSX” actually is

OPSX is the **new workflow model** and command namespace:

- `/opsx:propose`
- `/opsx:explore`
- `/opsx:apply`
- `/opsx:archive`
- etc.

It replaces the older legacy `/openspec:*` phase-locked workflow with a more fluid, action-based model.

## 2) Is there a `.opsx` file format?

I found **no actual `.opsx` file format** in this codebase.

What exists instead:

- OPSX **commands/workflow concepts**
- generated `opsx-*` command files for supported tools
- OPSX-related skills such as `openspec-propose`, `openspec-apply-change`, etc.
- regular persisted artifacts in `.md` and `.yaml`

So if you were expecting a serialized `.opsx` spec file, that is **not what this project implements**.

## 3) How OPSX differs from `.md` specs

OPSX is **the orchestration layer**.
Markdown specs are **the persisted behavior artifacts**.

### OPSX provides

- workflow commands
- artifact dependency resolution
- instruction generation
- profile/delivery/tool integration
- human/agent interaction model

### `spec.md` provides

- the actual behavioral contract
- requirements and scenarios
- delta operations when inside a change

In short:

- **OPSX = how work moves**
- **`spec.md` = what behavior is described**

---

# Area 3 — Spec model and schema system

## 1) Canonical spec structure

Main specs live in:

```text
openspec/specs/<domain>/spec.md
```

They describe the current behavior of the system.

Typical structure:

- `# <Name> Specification`
- `## Purpose`
- `## Requirements`
- `### Requirement: ...`
- `#### Scenario: ...`

Important semantic rules from docs and validation:

- requirement text should use **SHALL** or **MUST**
- every requirement should have at least one scenario
- scenarios must use exact `#### Scenario:` headings in delta specs

## 2) Default schema: `spec-driven`

The built-in schema (`schemas/spec-driven/schema.yaml`) defines:

```text
proposal
→ specs
→ design
→ tasks
→ apply
```

Actual dependencies:

- `proposal` requires nothing
- `specs` requires `proposal`
- `design` requires `proposal`
- `tasks` requires both `specs` and `design`
- `apply` requires `tasks` and tracks `tasks.md`

## 3) What the schema controls

A schema defines:

- artifact IDs
- generated output paths
- templates
- creation instructions
- dependencies between artifacts
- what apply depends on/tracks

So OpenSpec’s planning flow is **schema-driven**, not hardcoded phase logic.

## 4) Artifact-specific behavior in the default schema

### `proposal`
Captures:
- why
- what changes
- capabilities affected
- impact

Important detail: proposal establishes which capabilities will need spec files.

### `specs`
Creates one delta spec per capability and supports:
- `ADDED`
- `MODIFIED`
- `REMOVED`
- `RENAMED`

### `design`
Captures:
- technical decisions
- risks/trade-offs
- migration plan
- open questions

### `tasks`
Creates strict checkbox-based implementation steps:
- required format: `- [ ] X.Y Task description`
- `apply` depends on this parser-friendly structure

---

# Area 4 — Change system

## 1) What a change is

A change is a self-contained unit of proposed work under:

```text
openspec/changes/<change-name>/
```

Typical contents:

```text
proposal.md
design.md
tasks.md
.openspec.yaml      # metadata, optional
specs/              # delta specs
```

## 2) Why changes are folders

The folder model gives OpenSpec:

- isolated work packages
- parallel active changes
- reviewable units
- portable audit history
- mergeable deltas into canonical specs

## 3) Delta spec system

This is the key brownfield feature.

Inside a change, spec files do **not** restate the whole canonical spec. They describe **what changes**.

Supported delta sections:

- `## ADDED Requirements`
- `## MODIFIED Requirements`
- `## REMOVED Requirements`
- `## RENAMED Requirements`

### Merge semantics

- **ADDED**: appended as new requirements
- **MODIFIED**: replaces existing requirement blocks
- **REMOVED**: deletes existing requirements
- **RENAMED**: renames requirement headers before other operations finalize

## 4) Important delta authoring rule

For `MODIFIED`, the system expects the **full replacement requirement block**, not a partial patch. That matters because archive/sync rebuilds the canonical spec from parsed requirement blocks.

## 5) Parallel changes

OpenSpec explicitly supports multiple active changes at once. There is also a `bulk-archive` concept for archiving several completed changes together and resolving spec conflicts chronologically.

---

# Area 5 — Validation system

## 1) Validation layers

Validation is a combination of:

1. **schema/shape validation** using Zod
2. **Markdown parsing** into structured spec/change models
3. **semantic/spec rules** applied after parsing
4. **delta-specific validation** for change specs
5. **pre-write validation** of rebuilt canonical specs during sync/archive

## 2) Main spec validation

`Validator.validateSpec()` does:

- parse markdown with `MarkdownParser`
- validate against `SpecSchema`
- apply additional spec rules
- return a report with issues and summary counts

Extra spec checks include:

- structural checks on canonical spec layout
- `Purpose` length warnings
- overly long requirement text info messages
- missing scenarios warnings

Strict mode changes validity semantics:

- default: only **ERRORS** fail validation
- strict: **WARNINGS also fail**

## 3) Change delta validation

`validateChangeDeltaSpecs()` specifically validates change delta specs.

It checks:

- at least one delta exists across the change
- presence of delta section headers
- empty delta sections
- duplicate requirements within sections
- cross-section conflicts
- `ADDED` and `MODIFIED` contain requirement text
- `ADDED` and `MODIFIED` contain **SHALL** or **MUST**
- `ADDED` and `MODIFIED` include at least one `#### Scenario:`
- `RENAMED` pairs are well formed
- rename conflicts with modified/added entries

This is stronger than simple markdown linting: it validates the delta semantics the merge system depends on.

## 4) CLI validation behavior

`openspec validate` supports:

- single change/spec validation
- bulk validation
- JSON output
- concurrency for bulk mode
- interactive selection when no item is supplied

The noun-specific commands also exist:

- `openspec spec validate ...`
- `openspec change validate ...`

But the code marks noun-based commands as deprecated in favor of verb-first UX.

## 5) Validation during archive/apply

Archive does not blindly move files.
It:

- validates the change delta specs
- builds updated canonical specs in memory
- validates rebuilt canonical spec content before writing
- only writes if the rebuilt result is valid

That prevents corrupt canonical specs from being committed to `openspec/specs/`.

---

# Area 6 — Spec application and archive mechanics

## 1) How spec application works

`src/core/specs-apply.ts` is the reusable merge engine.

High-level flow:

1. find change delta spec files under `openspec/changes/<change>/specs/*/spec.md`
2. map each one to `openspec/specs/<capability>/spec.md`
3. parse delta plan
4. pre-validate duplicates/conflicts
5. load existing canonical spec or create a skeleton if new
6. parse canonical requirements into named blocks
7. apply operations in order:
   - `RENAMED`
   - `REMOVED`
   - `MODIFIED`
   - `ADDED`
8. rebuild the canonical `## Requirements` section
9. validate rebuilt full spec
10. write to disk

## 2) New spec creation behavior

If a canonical target spec does not exist:

- `ADDED` is allowed
- `MODIFIED` and `RENAMED` are rejected
- `REMOVED` is ignored with a warning
- a skeleton spec is created with:
  - title
  - `## Purpose`
  - `## Requirements`

## 3) Archive process details

`src/core/archive.ts` performs more than a file move.

Actual sequence:

1. verify change directory exists
2. optionally prompt for change selection
3. validate proposal and delta specs unless validation is skipped
4. inspect `tasks.md` progress and warn on incomplete tasks
5. detect target spec files to update
6. build every updated canonical spec in memory
7. validate every rebuilt canonical spec
8. write updated canonical specs
9. create archive path `changes/archive/YYYY-MM-DD-<change>`
10. move change folder there

## 4) Notable archive options

- `--skip-specs` = archive without updating canonical specs
- `--no-validate` = skip validation, with warning/confirmation
- `--yes` = skip confirmations

## 5) Windows-safe move behavior

Archive has explicit fallback behavior for `fs.rename()` failures:

- if rename fails with `EPERM` or `EXDEV`, it does copy-then-remove

That is a pragmatic cross-platform detail, especially relevant for IDE/file watcher heavy Windows setups.

---

# Area 7 — CLI surface and source structure

## 1) Human-facing CLI categories

From `docs/cli.md`, the main CLI groups are:

- setup: `init`, `update`
- browsing: `list`, `view`, `show`
- validation: `validate`
- lifecycle: `archive`
- workflow support: `status`, `instructions`, `templates`, `schemas`
- schema management: `schema init/fork/validate/which`
- config: `config ...`

## 2) Source files requested

### `src/commands/spec.ts`
- shows canonical specs
- supports raw markdown output or JSON projection
- can filter requirements/scenarios in JSON mode
- includes deprecated noun-style `spec` subcommands

### `src/commands/change.ts`
- shows/list/validates active changes
- parses proposals and deltas
- can emit JSON summaries with task status

### `src/commands/validate.ts`
- unified validation command
- detects whether an item is a change or a spec
- supports bulk validation with concurrency and JSON output

### `src/core/list.ts`
- lists changes or specs
- change list includes task progress and recency
- spec list includes requirement counts

### `src/core/view.ts`
- interactive-ish dashboard summary in terminal
- groups changes into draft / active / completed
- summarizes spec and task counts

## 3) Agent-facing support commands

These are central to the architecture even if end users may not use them directly:

- `openspec status`
- `openspec instructions`
- `openspec templates`
- `openspec schemas`

These make OPSX usable by coding agents because they expose:

- current artifact state
- which artifact is ready
- the resolved prompt template
- dependency context
- available schemas

---

# Area 8 — Tool integrations

## 1) Delivery model

OpenSpec can generate:

- **skills**
- **commands**
- or **both**

Global config field:

- `delivery: both | skills | commands`

## 2) Supported integrations

The project supports a large matrix of assistants/editors, including:

- Claude Code
- Cursor
- Windsurf
- Codex
- Continue
- GitHub Copilot (IDE prompts, not CLI)
- Gemini CLI
- Kiro
- OpenCode
- Pi
- RooCode
- Amazon Q
- Cline
- Qwen Code
- and many others

Some tools have both skills and commands; some only get skills because no command adapter exists.

## 3) How setup works internally

`init.ts`:

- detects available tools in the project
- optionally cleans legacy OpenSpec artifacts
- generates selected skills and/or command files
- filters generated workflows based on the active profile
- can remove previously generated commands or skills when delivery mode changes

## 4) Important architecture detail

OPSX is explicitly designed as a **cross-tool skills/command generation system** rather than something tied to one IDE/editor.

---

# Area 9 — Profile and config system

## 1) Two config layers

From docs and source, the practical configuration model is:

- **global config** = user defaults for profile/delivery/workflows
- **project config** = `openspec/config.yaml` for schema/context/rules

There is a strong bias against adding more cascading layers.

## 2) Global config schema

From `src/core/config-schema.ts`:

Top-level global config fields are:

- `featureFlags: Record<string, boolean>`
- `profile: core | custom`
- `delivery: both | skills | commands`
- `workflows: string[]`

Defaults:

- `profile: core`
- `delivery: both`

The config schema also supports:

- dot-path get/set/unset helpers
- validation of allowed key paths
- string→boolean/number coercion for CLI set commands
- YAML-like formatting for display

## 3) Project config

`openspec/config.yaml` is the main per-project customization surface.

Supported concepts from docs/example config:

- `schema: <name>`
- `context: | ...`
- `rules:` keyed by artifact ID

### `context`
Injected into **all artifact generation**.
Good for:
- tech stack
- architecture constraints
- cross-platform rules
- recurring conventions

### `rules`
Injected only for the matching artifact type.
Good for:
- spec-writing rules
- proposal-review expectations
- design-specific conventions
- task granularity rules

## 4) Schema resolution precedence

When OpenSpec resolves which schema to use:

1. CLI flag `--schema`
2. `.openspec.yaml` in change folder
3. `openspec/config.yaml`
4. default `spec-driven`

## 5) Profile selection semantics

- `core` = default minimal workflow set
- `custom` = user-selected workflows

Workflow selection is configured via:

- `openspec config profile`
- followed by `openspec update` to regenerate files in the project

---

# Area 10 — Multi-project / multi-language handling

## 1) Multi-language support

This is already supported in a lightweight way.

There is **no separate i18n subsystem** for artifacts. Instead, language is driven by injected project context.

Example:

```yaml
context: |
  Language: Portuguese (pt-BR)
  All artifacts must be written in Brazilian Portuguese.
```

This means language handling is prompt/context-based, not schema-based.

What stays in English by convention:

- code examples
- file paths
- technical tokens if you instruct it that way

## 2) Multi-project / monorepo / multi-repo support

Current state is important to state precisely:

### What exists today
- OpenSpec is fundamentally **repo-root scoped**
- one `openspec/` directory per repo/root is the current model
- schemas can be project-local or user-global
- monorepo usage is possible within one root

### What is still exploratory
The `openspec/explorations/` documents show that true multi-root support is **not yet the primary shipped model**.
The exploration docs discuss future support for:

- nested spec organization
- scopes inside large monorepos
- initiatives as cross-scope planning artifacts
- neutral coordination workspaces for multi-repo work
- linked repo-local changes under a shared initiative

So the accurate answer is:

- **multi-language: supported now via context injection**
- **multi-project/multi-repo: actively explored, not yet the core shipped architecture**

---

# Area 11 — Explorations

## 1) What explorations are

The `openspec/explorations/` directory appears to be a **product/architecture research space**, not part of the currently canonical runtime artifact model.

These docs are exploratory design notes about future OpenSpec behavior.

Examples present:

- `explore-workflow-ux.md`
- `workspace-architecture.md`
- `workspace-roadmap.md`
- `workspace-user-journeys.md`
- `workspace-ux-simplification.md`

## 2) What they cover

They explore questions like:

- should `/opsx:explore` become exportable/persistent?
- how should OpenSpec handle scopes in monorepos?
- where should cross-repo planning live?
- what is the right split between shared contracts and local implementation specs?
- how should coordinated initiatives work?

## 3) What they are not

They are **not**:

- part of the canonical schema system
- enforced by current validators
- required runtime artifacts for a normal change

So “explorations” are best understood as:

> research/design notes for future OpenSpec evolution, especially workspace and coordination features.

---

# Direct answers to the requested extraction questions

## 1. What is the spec lifecycle?

Most accurate lifecycle:

```text
openspec init
→ /opsx:explore (optional)
→ /opsx:propose
   or /opsx:new → /opsx:continue|/opsx:ff
→ openspec validate / openspec status / openspec instructions (as needed)
→ /opsx:apply
→ /opsx:verify (optional)
→ /opsx:sync (optional)
→ /opsx:archive
```

## 2. What is the .opsx format? How does it differ from .md specs?

There is **no actual `.opsx` persisted file format** in this repo.

OPSX is the **workflow/command system**.
Artifacts are still written as `.md` and `.yaml` files.

- OPSX = orchestration model
- `.md` specs = persisted behavior contracts

## 3. What is the change system?

A change is an isolated folder under `openspec/changes/<name>/` containing:

- `proposal.md`
- delta specs
- `design.md`
- `tasks.md`
- optional `.openspec.yaml`

Delta specs express changes relative to canonical specs using ADDED / MODIFIED / REMOVED / RENAMED sections.
Multiple changes can exist in parallel.

## 4. How does validation work?

Validation combines:

- markdown parsing
- Zod schema validation
- semantic rules for specs and deltas
- bulk/single validation CLI support
- pre-write validation of rebuilt canonical specs during sync/archive

Strict mode makes warnings fail validation too.

## 5. How does the archive system work?

Archive:

1. validates change inputs
2. checks task completion status
3. finds target canonical spec files
4. rebuilds updated canonical specs in memory
5. validates rebuilt specs
6. writes updated canonical specs
7. moves the change folder to `changes/archive/YYYY-MM-DD-name/`

It preserves full audit history.

## 6. What tool integrations does it support?

A broad matrix of AI coding tools/editors, including Claude, Cursor, Windsurf, Codex, Continue, Copilot IDE, Gemini CLI, OpenCode, Pi, RooCode, Cline, Amazon Q, and others.

It generates skills and/or command files depending on delivery mode.

## 7. How does it handle multi-project/multi-language?

- **Multi-language**: via `context:` in `openspec/config.yaml`
- **Multi-project / multi-repo**: current architecture is still mainly one-root-per-project; workspace/initiative support is under exploration, not the primary shipped model yet

## 8. What is the profile/config system?

Two layers:

- global config: `profile`, `delivery`, `workflows`, `featureFlags`
- project config: `schema`, `context`, `rules`

Profiles decide which workflows are materialized. Project config shapes artifact generation.

## 9. What are explorations?

Explorations are markdown research/design docs under `openspec/explorations/` used to think through future UX, workspace, monorepo, and multi-repo behavior. They are not part of the normal canonical change/spec lifecycle.

---

# Bottom line

OpenSpec’s real architecture is:

- **repo-scoped canonical specs**
- **change folders with delta specs**
- **schema-driven artifact generation**
- **agent-facing workflow commands under OPSX**
- **validation before merge**
- **archive as merge + history preservation**

If I had to summarize it in one sentence:

> OpenSpec is a markdown-first, schema-driven change/spec workflow where OPSX orchestrates planning and implementation, delta specs capture behavioral change, and archive promotes validated deltas into canonical specs.
