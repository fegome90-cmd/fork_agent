# Gentle-AI Agent Adapter + Component Injection Pipeline

## Status: success

## Summary: Complete technical spec of the 11-agent adapter system, factory/registry pattern, 5 system prompt strategies, 4 MCP strategies, 7-component injection pipeline, and golden test verification pattern.

## Artifacts: /tmp/fork-ga-adapters.md

---

## 1. Agent Interface (`agents.Adapter`)

The `Adapter` interface is the core abstraction. Components call adapter methods instead of switch statements on AgentID, making it trivial to add new agents.

```go
type Adapter interface {
    // Identity
    Agent() model.AgentID
    Tier() model.SupportTier

    // Detection
    Detect(ctx, homeDir) (installed, binaryPath, configPath, configFound, error)

    // Installation
    SupportsAutoInstall() bool
    InstallCommand(profile) ([][]string, error)

    // Config paths — components use these, never hardcode
    GlobalConfigDir(homeDir) string
    SystemPromptDir(homeDir) string
    SystemPromptFile(homeDir) string
    SkillsDir(homeDir) string
    SettingsPath(homeDir) string

    // Config strategies — HOW to inject, not WHERE
    SystemPromptStrategy() model.SystemPromptStrategy
    MCPStrategy() model.MCPStrategy

    // MCP path resolution
    MCPConfigPath(homeDir, serverName) string

    // Optional capabilities — declared by each agent
    SupportsOutputStyles() bool
    OutputStyleDir(homeDir) string
    SupportsSlashCommands() bool
    CommandsDir(homeDir) string
    SupportsSkills() bool
    SupportsSystemPrompt() bool
    SupportsMCP() bool
}
```

**Return types for Detect:** `(installed bool, binaryPath string, configPath string, configFound bool, err error)`

---

## 2. Factory Pattern

```
NewAdapter(agentID) → Adapter    // switch on 11 agent IDs
NewDefaultRegistry() → Registry  // all 11 adapters pre-registered
NewMVPRegistry() → Registry      // Claude Code + OpenCode only (backward compat)
```

**Flow:**

1. `NewAdapter(agentID)` dispatches via switch to the correct package constructor
2. `NewDefaultRegistry()` creates all 11 adapters and registers them in a `map[AgentID]Adapter`
3. `Registry.Get(agentID)` returns the adapter for a specific agent
4. `Registry.SupportedAgents()` returns sorted list of all registered IDs

**Error handling:** `AgentNotSupportedError` for unknown IDs, `ErrDuplicateAdapter` for duplicate registration.

---

## 3. Agent Tier System

Currently **single tier** — all 11 agents are `TierFull`. The tier constant exists as metadata for future differentiation.

```go
type SupportTier string
const TierFull SupportTier = "full"
```

Historical note: The codebase previously had `TierMinimal` and `TierEmerging` but simplified to all-full. The `catalog` package still defines `allAgents` and `mvpAgents` (Claude Code + OpenCode) for UI display purposes.

---

## 4. Per-Adapter Comparison Table

| Agent           | AgentID          | Config Dir              | System Prompt File                                  | Prompt Strategy      | MCP Strategy          | Auto-Install     | Detection                          |
| --------------- | ---------------- | ----------------------- | --------------------------------------------------- | -------------------- | --------------------- | ---------------- | ---------------------------------- |
| Claude Code     | `claude-code`    | `~/.claude`             | `~/.claude/CLAUDE.md`                               | **MarkdownSections** | **SeparateMCPFiles**  | Yes              | `claude` binary on PATH            |
| OpenCode        | `opencode`       | `~/.config/opencode`    | `~/.config/opencode/AGENTS.md`                      | **FileReplace**      | **MergeIntoSettings** | Yes              | `opencode` binary on PATH          |
| Kilo Code       | `kilocode`       | `~/.config/kilo`        | `~/.config/kilo/AGENTS.md`                          | **FileReplace**      | **MergeIntoSettings** | Yes              | `kilo` binary on PATH              |
| Gemini CLI      | `gemini-cli`     | `~/.gemini`             | `~/.gemini/GEMINI.md`                               | **FileReplace**      | **MergeIntoSettings** | Yes              | `gemini` binary on PATH            |
| Cursor          | `cursor`         | `~/.cursor`             | `~/.cursor/rules/gentle-ai.mdc`                     | **FileReplace**      | **MCPConfigFile**     | No (desktop)     | `~/.cursor` dir exists             |
| VS Code Copilot | `vscode-copilot` | `~/.copilot`            | `~/.../Code/User/prompts/gentle-ai.instructions.md` | **InstructionsFile** | **MCPConfigFile**     | No (desktop)     | `code` binary on PATH              |
| Codex           | `codex`          | `~/.codex`              | `~/.codex/agents.md`                                | **FileReplace**      | **TOMLFile**          | Yes              | `codex` binary on PATH             |
| Antigravity     | `antigravity`    | `~/.gemini/antigravity` | `~/.gemini/GEMINI.md`                               | **AppendToFile**     | **MCPConfigFile**     | No (desktop IDE) | `~/.gemini/antigravity` dir exists |
| Windsurf        | `windsurf`       | `~/.codeium/windsurf`   | `~/.codeium/windsurf/memories/global_rules.md`      | **AppendToFile**     | **MCPConfigFile**     | No (desktop)     | `~/.codeium/windsurf` dir exists   |
| Qwen Code       | `qwen-code`      | `~/.qwen`               | `~/.qwen/QWEN.md`                                   | **FileReplace**      | **MergeIntoSettings** | Yes              | `qwen` binary on PATH              |
| Kiro IDE        | `kiro-ide`       | `~/.kiro`               | `~/.kiro/steering/gentle-ai.md`                     | **SteeringFile**     | **MCPConfigFile**     | No (desktop)     | `kiro` binary on PATH              |

### Optional Capabilities Matrix

| Capability     | Claude | OpenCode | Kilo | Gemini | Cursor | VS Code | Codex | Anti | Windsurf | Qwen | Kiro |
| -------------- | ------ | -------- | ---- | ------ | ------ | ------- | ----- | ---- | -------- | ---- | ---- |
| Output Styles  | YES    | -        | -    | -      | -      | -       | -     | -    | -        | -    | -    |
| Slash Commands | -      | YES      | YES  | -      | -      | -       | -     | -    | -        | YES  | -    |
| Sub-Agents     | -      | -        | -    | -      | YES    | -       | -     | -    | -        | -    | YES  |
| Workflows      | -      | -        | -    | -      | -      | -       | -     | -    | YES      | -    | -    |

---

## 5. System Prompt Strategies (5 total)

| Strategy             | Constant                   | Used By                                     | Behavior                                                                                                                                                         |
| -------------------- | -------------------------- | ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **MarkdownSections** | `StrategyMarkdownSections` | Claude Code                                 | Injects `<!-- gentle-ai:ID -->` marker sections into existing file without clobbering user content. Supports surgical add/replace/remove of individual sections. |
| **FileReplace**      | `StrategyFileReplace`      | OpenCode, Kilo, Gemini, Cursor, Codex, Qwen | Replaces the entire system prompt file. Persona/SDD components must coordinate to avoid overwriting each other's sections.                                       |
| **AppendToFile**     | `StrategyAppendToFile`     | Antigravity, Windsurf                       | Appends content to existing file with idempotency checks (skips if content already present).                                                                     |
| **InstructionsFile** | `StrategyInstructionsFile` | VS Code Copilot                             | Writes a `.instructions.md` file with YAML frontmatter (`name`, `description`, `applyTo`).                                                                       |
| **SteeringFile**     | `StrategySteeringFile`     | Kiro IDE                                    | Writes a steering file with `inclusion: always` frontmatter to `~/.kiro/steering/gentle-ai.md`.                                                                  |

---

## 6. MCP Strategies (4 total)

| Strategy              | Constant                    | Used By                                      | Behavior                                                                                                                                                |
| --------------------- | --------------------------- | -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **SeparateMCPFiles**  | `StrategySeparateMCPFiles`  | Claude Code                                  | One JSON file per server: `~/.claude/mcp/{serverName}.json`                                                                                             |
| **MergeIntoSettings** | `StrategyMergeIntoSettings` | OpenCode, Kilo, Gemini, Qwen                 | Deep-merges `mcpServers` (or `mcp` for OpenCode) into settings JSON. OpenCode uses `__replace__` sentinel for atomic replacement.                       |
| **MCPConfigFile**     | `StrategyMCPConfigFile`     | Cursor, VS Code, Antigravity, Windsurf, Kiro | Writes to a dedicated `mcp.json` file. VS Code uses `"servers"` key instead of `"mcpServers"`.                                                          |
| **TOMLFile**          | `StrategyTOMLFile`          | Codex                                        | Upserts `[mcp_servers.engram]` block in `~/.codex/config.toml`. Also writes `model_instructions_file` and `experimental_compact_prompt_file` TOML keys. |

---

## 7. Component Injection Pipeline

Execution order: **engram → persona → sdd → skills → mcp → permissions → gga**

Each component's `Inject()` receives the adapter and uses its methods to determine paths/strategies. No component has agent-specific switch statements — the adapter abstracts all differences.

### 7.1 Engram (Memory MCP Server)

**What it does:**

1. Writes MCP server config pointing to `engram mcp --tools=agent`
2. Injects engram memory protocol into system prompt via `<!-- gentle-ai:engram-protocol -->` marker

**Agent-specific behavior (via adapter.MCPStrategy()):**

- **SeparateMCPFiles (Claude):** Writes `~/.claude/mcp/engram.json` with `{"command": "...", "args": ["mcp", "--tools=agent"]}`. Preserves absolute engram path if already set by `engram setup`.
- **MergeIntoSettings (OpenCode/Kilo):** Merges `mcp.engram` with `__replace__` sentinel and `command` as array (OpenCode 1.3.3+ requirement).
- **MCPConfigFile (Cursor/Antigravity/Windsurf/Kiro):** Merges `mcpServers.engram` into `mcp.json`. VS Code uses `servers.engram`.
- **TOMLFile (Codex):** Upserts `[mcp_servers.engram]` block + instruction files at `~/.codex/engram-instructions.md` and `~/.codex/engram-compact-prompt.md`.

**Setup flow:** `engram setup <agent-slug>` runs BEFORE Inject. Slugs: `opencode`, `kilocode`, `claude-code`, `gemini-cli`, `codex`, `antigravity`, `windsurf`, `qwen-code`. Cursor and VS Code are excluded (no `engram setup` support).

### 7.2 Persona (Gentleman/Neutral/Custom)

**What it does:**

1. Injects persona content into system prompt
2. Writes output style file (Claude only)
3. Merges output style into settings.json (Claude only)
4. Defines OpenCode Tab-switchable agents (`gentleman` + `sdd-orchestrator`)

**Agent-specific behavior (via adapter.SystemPromptStrategy()):**

- **MarkdownSections (Claude):** Auto-heals legacy free-text persona, strips ATL blocks, injects `<!-- gentle-ai:persona -->` section.
- **FileReplace (OpenCode/Kilo):** Same healing logic. For non-Gentleman personas, preserves existing managed sections (SDD, engram markers).
- **InstructionsFile (VS Code):** Wraps content in YAML frontmatter. Cleans legacy `~/.github/copilot-instructions.md` if present.
- **SteeringFile (Kiro):** Wraps content in `---\ninclusion: always\n---` frontmatter. Preserves managed sections.
- **AppendToFile (Antigravity/Windsurf):** Idempotent append with content-presence check.
- **Custom persona:** No-op for all agents.

**Persona asset routing:** Claude → `claude/persona-gentleman.md`, OpenCode/Kilo → `opencode/persona-gentleman.md`, Kiro → `kiro/persona-gentleman.md`, all others → `generic/persona-gentleman.md`.

### 7.3 SDD (Spec-Driven Development Orchestrator)

**What it does:**

1. Injects SDD orchestrator instructions into system prompt
2. Writes 9 SDD skill files + shared files to skills directory
3. Writes slash commands (OpenCode/Kilo/Qwen only)
4. Merges agent definitions into OpenCode settings (orchestrator + sub-agents)
5. Installs OpenCode plugins (background-agents.ts)
6. Writes native workflow files (Windsurf only: `.windsurf/workflows/`)
7. Writes native sub-agent files (Cursor/Kiro only: `~/.cursor/agents/`, `~/.kiro/agents/`)
8. Post-injection verification checks

**Agent-specific behavior:**

- **Claude (MarkdownSections):** Injects `<!-- gentle-ai:sdd-orchestrator -->` section. Strips legacy bare orchestrator blocks.
- **OpenCode/Kilo:** Does NOT inject into AGENTS.md (SDD is scoped to `sdd-orchestrator` agent only). Instead merges agent definitions into `opencode.json`. Supports single-mode and multi-mode overlays. Multi-mode writes 10 phase sub-agents with `{file:/abs/path}` prompt references.
- **FileReplace/Append/Instructions/Steering agents:** Uses `InjectMarkdownSection` with `<!-- gentle-ai:sdd-orchestrator -->` marker. Falls back to appending if markers not supported.
- **Windsurf:** Also copies workflow files from embedded `windsurf/workflows/` to `<workspace>/.windsurf/workflows/` (requires `workflowInjector` interface).
- **Cursor/Kiro:** Also copies sub-agent `.md` files from embedded `cursor/agents/` or `kiro/agents/` to home directory (requires `subAgentInjector` interface). Kiro resolves `{{KIRO_MODEL}}` placeholder via `kiroModelResolver`.

**SDD orchestrator asset routing:** Each agent gets its own asset (`gemini/sdd-orchestrator.md`, `codex/sdd-orchestrator.md`, `cursor/sdd-orchestrator.md`, etc.) with `generic/sdd-orchestrator.md` as fallback.

### 7.4 Skills (Non-SDD Skill Files)

**What it does:** Writes embedded `SKILL.md` files to `adapter.SkillsDir()`.

**Key behavior:**

- Skips SDD skills (`sdd-*` prefix) — those are written by the SDD component
- Uses `adapter.SkillsDir(homeDir)` for target directory (zero agent-specific logic)
- Individual skill failures are logged and skipped (not fatal)
- Skills are organized as `skills/{skillID}/SKILL.md` in the embedded FS

### 7.5 MCP / Context7 (Documentation MCP Server)

**What it does:** Injects Context7 documentation server config.

**Agent-specific behavior (via adapter.MCPStrategy()):**

- **SeparateMCPFiles (Claude):** Writes `~/.claude/mcp/context7.json`
- **MergeIntoSettings (OpenCode/Kilo):** Merges into settings with OpenCode-specific overlay format
- **MCPConfigFile (Cursor/Antigravity/VS Code):** Merges into `mcp.json`. Each has a specific overlay format (VS Code uses `"servers"` key, Antigravity has its own overlay)
- **TOMLFile (Codex):** Not supported — Context7 not injected via MCP for Codex

### 7.6 Permissions (Safety Guards)

**What it does:** Merges permission overlays into `adapter.SettingsPath()`.

**Agent-specific overlays:**

| Agent           | Overlay Key                           | Behavior                                                             |
| --------------- | ------------------------------------- | -------------------------------------------------------------------- |
| Claude Code     | `permissions.defaultMode`             | `"bypassPermissions"` with deny list for `.env` and `rm -rf /`       |
| OpenCode/Kilo   | `permission.bash` + `permission.read` | Bash: `allow *`, deny `.env`/`secrets`. Git push/rebase/reset: `ask` |
| Gemini CLI      | `general.defaultApprovalMode`         | `"auto_edit"`                                                        |
| Qwen Code       | `permissions.defaultMode`             | `"auto_edit"`                                                        |
| VS Code Copilot | `chat.tools.autoApprove`              | `true`                                                               |
| Cursor          | nil                                   | Managed via `cli-config.json`, not settings.json                     |
| Antigravity     | nil                                   | Managed via IDE UI (Artifact Review Policy)                          |
| Codex           | nil                                   | No known settings.json path                                          |

### 7.7 GGA (Gentleman Git Automation)

**What it does:** Writes `~/.config/gga/config` + `~/.config/gga/AGENTS.md` template.

**Agent-specific behavior:** Auto-detects provider from selected agents: claude > opencode > gemini > codex > claude (default). GGA is agent-agnostic — it writes to its own config directory, not to any agent's config dir.

---

## 8. Agent Detection & Discovery

### Detection (`Adapter.Detect`)

Three detection patterns:

1. **CLI binary on PATH** (Claude, OpenCode, Kilo, Gemini, Codex, Qwen, VS Code): `exec.LookPath(binaryName)`
2. **Config directory exists** (Cursor, Antigravity, Windsurf): `os.Stat(configDir)`
3. **Hybrid** (Kiro): Binary on PATH + config dir check

Desktop apps return `AgentNotInstallableError` from `InstallCommand()`.

### Discovery (`agents.DiscoverInstalled`)

Pure filesystem check — iterates registry, calls `GlobalConfigDir()` for each, checks if directory exists on disk. No subprocess spawning. Returns `[]InstalledAgent{ID, ConfigDir}`.

---

## 9. Golden Test Pattern

Located in `internal/components/golden_test.go` with fixtures in `testdata/golden/`.

**Pattern:**

1. Create temp dir (`t.TempDir()`)
2. Mock engram binary path (`engram.SetLookPathForTest(t, "/opt/homebrew/bin/engram", "")`)
3. Call component `Inject()` with adapter
4. Read output file(s) from temp dir
5. Compare byte-for-byte against golden file

**Update mode:** `go test -update` regenerates all golden files.

**Coverage:** Golden tests exist for:

- **SDD injection:** Claude, OpenCode (single + multi), Cursor, Gemini, VS Code, Codex, Windsurf, Antigravity, Kiro
- **Persona injection:** Claude (Gentleman + Neutral + Custom), OpenCode (Gentleman + Neutral + Custom), Windsurf, Kiro, Antigravity
- **Engram injection:** Claude, OpenCode, Windsurf, Kiro, Antigravity
- **Skills injection:** Claude, OpenCode, Windsurf, Kiro
- **Combined injection:** Claude (persona + SDD + engram), Windsurf (persona + SDD + engram)

**Post-injection verification:** The SDD component performs runtime checks:

- OpenCode: verifies `sdd-orchestrator` and `sdd-apply` keys exist in merged settings JSON
- Skills: verifies `sdd-init`, `sdd-apply`, `sdd-verify` files exist and are >100 bytes
- Sub-agents (Cursor/Kiro): verifies `sdd-apply.md` and `sdd-verify.md` exist and are >50 bytes

---

## 10. Key Design Patterns

1. **Adapter Pattern:** All agent differences encapsulated in Adapter interface. Components never switch on AgentID.
2. **Strategy Pattern:** SystemPromptStrategy and MCPStrategy enums drive behavior in components.
3. **Embedded Assets:** All content (personas, skills, orchestrators, commands) embedded in Go binary via `embed.FS`. No filesystem reads for templates.
4. **Atomic Writes:** `filemerge.WriteFileAtomic()` writes to temp file then renames — prevents partial writes on crash.
5. **Idempotency:** All components use content comparison (byte-for-byte) before writing. Re-running is safe.
6. **Marker-Based Sections:** `<!-- gentle-ai:ID -->` markers enable surgical injection into existing files without clobbering user content (Claude Code primary).
7. **Legacy Migration:** Auto-healing strips old ATL (Agent Teams Lite) blocks, bare orchestrator sections, and unwrapped persona content from pre-marker installer versions.
8. **Optional Interfaces:** `workflowInjector`, `subAgentInjector`, `kiroModelResolver` — only implemented by agents that need them, avoiding no-op stubs on all adapters.

---

## 11. Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│                   gentle-ai CLI                      │
│                                                      │
│  ┌──────────┐   ┌──────────┐   ┌──────────────────┐ │
│  │ Factory   │──▶│ Registry │──▶│ DiscoverInstalled │ │
│  │(11 agents)│   │(map[ID]→ │   │(FS check only)    │ │
│  │           │   │ Adapter) │   └──────────────────┘ │
│  └──────────┘   └────┬─────┘                        │
└───────────────────────┼──────────────────────────────┘
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
   ┌────────────┐ ┌───────────┐ ┌──────────┐
   │  Adapter    │ │ Components│ │ Embedded │
   │  Interface  │ │ Pipeline  │ │ Assets   │
   │             │ │           │ │(embed.FS)│
   │ • Agent()   │ │ 1. Engram │ │          │
   │ • Tier()    │ │ 2. Persona│ │ personas/│
   │ • Detect()  │ │ 3. SDD    │ │ skills/  │
   │ • Paths()   │ │ 4. Skills │ │ sdd-*    │
   │ • Strategy()│ │ 5. MCP    │ │ commands/│
   │ • Supports* │ │ 6. Perms  │ │ agents/  │
   └────────────┘ │ 7. GGA    │ │ workflows│
                  └───────────┘ └──────────┘
```

Each component calls `adapter.Method()` to get paths and strategies — zero hardcoded agent knowledge in component code.
