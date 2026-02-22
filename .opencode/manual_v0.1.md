Why Would You Need Hooks?
Imagine you want to:

🔒 Prevent OpenCode from reading sensitive files like .env
✅ Automatically format code after OpenCode edits it
📢 Send notifications to Slack when a coding session completes
🔍 Log all AI interactions for compliance or analysis
🚀 Trigger deployments after successful code changes
🧪 Run tests automatically when files are modified
All of this is possible with OpenCode's hook system. Let me show you how.

Six Ways to Implement Hooks in OpenCode
OpenCode provides six different mechanisms for hooks and extensibility. You can choose the one that fits your use case:

1. Plugin System (Most Powerful)
The plugin system is your main tool for implementing hooks. Plugins are JavaScript or TypeScript files that can intercept events and tool executions.

When to use: Complex logic, event handling, custom validations

Example - Protect sensitive files:

import type { Plugin } from "@opencode-ai/plugin"

export const EnvProtection: Plugin = async ({ client }) => {
  return {
    tool: {
      execute: {
        before: async (input, output) => {
          // This runs BEFORE any tool executes
          if (input.tool === "read" && 
              output.args.filePath.includes(".env")) {
            throw new Error("🚫 Cannot read .env files")
          }
        }
      }
    }
  }
}
Save this as .opencode/plugin/env-protection.ts and it automatically prevents OpenCode from reading environment files!

Example - Auto-format code after edits:

export const AutoFormat: Plugin = async ({ $ }) => {
  return {
    tool: {
      execute: {
        after: async (input, output) => {
          // This runs AFTER the tool completes
          if (input.tool === "edit") {
            await $`prettier --write ${output.args.filePath}`
            console.log("✨ Code formatted!")
          }
        }
      }
    }
  }
}
2. SDK with Event Streaming
The SDK gives you programmatic control over OpenCode from external applications. It uses Server-Sent Events (SSE) to stream what's happening in real-time.

When to use: External integrations, monitoring, CI/CD automation

Example - Monitor sessions and send notifications:

import { createOpencodeClient } from "@opencode-ai/sdk"

const client = createOpencodeClient({
  baseUrl: "http://localhost:4096"
})

// Subscribe to all events
const eventStream = await client.event.subscribe()

for await (const event of eventStream) {
  console.log("📡 Event:", event.type)

  if (event.type === "session.idle") {
    // Session completed - send notification
    await sendSlackMessage("OpenCode session completed!")
  }
}
Start the OpenCode server: opencode serve --port 4096

Install SDK: npm install @opencode-ai/sdk

3. MCP Servers (Model Context Protocol)
MCP servers let you add external tools and capabilities that OpenCode can use during coding sessions.

When to use: Adding new tools, integrating third-party services

Example configuration in opencode.json:

{
  "mcp": {
    "database-query": {
      "type": "local",
      "command": ["node", "./mcp-servers/database.js"],
      "enabled": true
    },
    "company-docs": {
      "type": "remote",
      "url": "https://docs.mycompany.com/mcp",
      "enabled": true,
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY"
      }
    }
  }
}
Real-world MCP servers you can use:

Appwrite - Backend services
Context7 - Documentation search
Bright Data - Web scraping
Playwright - Browser automation
4. GitHub Integration
The GitHub integration works like webhooks for your repositories. OpenCode automatically responds to comments in issues and PRs.

When to use: PR automation, issue triage, code review

Setup:

opencode github install
Usage in GitHub:

Comment /opencode explain this issue on any issue
Comment /opencode fix this bug to create a branch and PR
Comment /opencode review these changes on a PR
Manual workflow configuration:

name: opencode
on:
  issue_comment:
    types: [created]

jobs:
  opencode:
    if: contains(github.event.comment.body, '/opencode')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: sst/opencode/github@latest
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        with:
          model: anthropic/claude-sonnet-4-20250514
5. Custom Commands
Custom commands are reusable prompts saved as Markdown files. They can execute shell commands and accept arguments.

When to use: Common tasks, templates, simple automation

Example .opencode/command/test.md:

---
description: "Run tests with coverage"
---
Run the full test suite with coverage:
`!npm test -- --coverage`

Analyze the results and suggest improvements for:
- Test coverage gaps
- Slow tests
- Flaky tests
Usage: Type /test in OpenCode to run this command.

With arguments:

---
description: Test a specific component
---
Run tests for the $COMPONENT component:
`!npm test -- $COMPONENT.test.ts`

Review the results and suggest fixes.
Usage: /test Button automatically substitutes $COMPONENT with Button

6. Non-Interactive Mode
The non-interactive mode lets you script OpenCode for automation without the TUI interface.

When to use: CI/CD pipelines, pre-commit hooks, batch processing

Examples:

# Run a command and get JSON output
opencode run "analyze code quality" -f json -q

# Continue a previous session
opencode run "implement the fixes" -c session-id

# Use in a pre-commit hook
opencode run "review my changes and ensure no secrets are committed" -q
Complete Comparison Table
Mechanism	Complexity	Flexibility	Best For
Plugin System	High	Very High	Custom logic, event hooks, validations
SDK/API	Medium	Very High	Full programmatic control, integrations
MCP Servers	Medium	High	External tools, third-party protocols
GitHub Integration	Low	Medium	PR/issue workflows, repository automation
Custom Commands	Low	Low	Reusable prompts, simple automation
Non-Interactive	Low	Medium	CI/CD, scripts, batch processing
Practical Use Cases with Code
Security: Prevent Reading Sensitive Files
export const SecurityPlugin: Plugin = async ({ client }) => {
  const sensitivePatterns = ['.env', 'secret', 'credentials', 'private-key']

  return {
    tool: {
      execute: {
        before: async (input, output) => {
          if (input.tool === "read") {
            const filePath = output.args.filePath.toLowerCase()

            if (sensitivePatterns.some(pattern => filePath.includes(pattern))) {
              throw new Error(`🚫 Blocked: Cannot read sensitive file ${output.args.filePath}`)
            }
          }
        }
      }
    }
  }
}
Quality: Auto-format and Test After Edits
export const QualityPlugin: Plugin = async ({ $ }) => {
  return {
    tool: {
      execute: {
        after: async (input, output) => {
          if (input.tool === "edit") {
            const file = output.args.filePath

            // Format the file
            await $`prettier --write ${file}`
            console.log("✨ Formatted:", file)

            // Run tests
            const result = await $`npm test ${file}`.quiet()
            if (result.exitCode !== 0) {
              console.warn("⚠️  Tests failed for:", file)
            }
          }
        }
      }
    }
  }
}
Notifications: Slack Integration
export const SlackNotifier: Plugin = async () => {
  return {
    event: async ({ event }) => {
      if (event.type === "session.idle") {
        await fetch(process.env.SLACK_WEBHOOK_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            text: `✅ OpenCode session completed!`,
            blocks: [{
              type: "section",
              text: {
                type: "mrkdwn",
                text: `*Session ID:* ${event.properties.sessionId}\n*Files modified:* ${event.properties.filesModified}`
              }
            }]
          })
        })
      }
    }
  }
}
Automated Code Review with SDK
import { createOpencodeClient } from "@opencode-ai/sdk"

async function autoReview() {
  const client = createOpencodeClient({
    baseUrl: "http://localhost:4096"
  })

  // Create a new session
  const session = await client.session.create({
    title: "Automated Code Review"
  })

  // Get modified files
  const files = await client.file.status()
  const modifiedFiles = files.filter(f => f.status === "modified")

  // Review each file
  for (const file of modifiedFiles) {
    const content = await client.file.read({ path: file.path })

    await client.session.chat({
      id: session.id,
      providerID: "anthropic",
      modelID: "claude-sonnet-4-20250514",
      parts: [{
        type: "text",
        text: `Review this file for:
- Code quality issues
- Security vulnerabilities
- Performance problems
- Best practice violations

File: ${file.path}
\`\`\`
${content}
\`\`\``
      }]
    })
  }

  // Share the review
  const shared = await client.session.share({ id: session.id })
  console.log("📊 Review URL:", shared.shareUrl)
}
Getting Started: Step-by-Step
1. Install OpenCode
npm install -g @opencode-ai/cli
2. Create Your First Plugin
# Create plugin directory
mkdir -p .opencode/plugin

# Install plugin types
npm install @opencode-ai/plugin
Create .opencode/plugin/my-first-plugin.ts:

import type { Plugin } from "@opencode-ai/plugin"

export const MyFirstPlugin: Plugin = async ({ app, client, $ }) => {
  console.log("🎉 Plugin loaded!")

  return {
    event: async ({ event }) => {
      console.log("📡 Event:", event.type)
    }
  }
}
3. Enable Your Plugin
Create/edit opencode.json:

{
  "$schema": "https://opencode.ai/config.json",
  "plugins": {
    "my-first-plugin": {
      "enabled": true
    }
  }
}
4. Test It
opencode
# You should see: 🎉 Plugin loaded!
Configuration Priority
OpenCode looks for configuration in this order:

OPENCODE_CONFIG environment variable
./opencode.json (project directory)
~/.config/opencode/opencode.json (global)
Community Demand and Real-World Usage
The OpenCode community actively requested hooks before the current system was fully documented:

Issue #1473 "Hooks support?" - Developer wanted to automate commits and PRs after tasks
Issue #753 "Extensible Plugin System" - Proposed complete architecture with lifecycle, conversation, and tool call hooks
Issue #2185 "Hooks for commands" - Requested command-level hooks for pre/post LLM processing
Community integrations:

opencode.nvim - Forwards OpenCode events as Neovim autocmds
opencode-mcp-tool - MCP server to control OpenCode from other systems
Context7 MCP - Documentation search integration
Bright Data Web MCP - Advanced web scraping
Developers on X/Twitter share custom hook implementations regularly. Articles on Medium and DEV Community rank OpenCode above Claude Code and Aider specifically for plugin and hook flexibility.

What OpenCode Doesn't Have
For completeness, OpenCode does NOT have:

❌ Traditional HTTP webhooks (POST endpoints)
❌ Direct git hooks (pre-commit, post-commit)
❌ Webhook receiver endpoints for external services
But the event-driven internal hooks cover the same use cases in a more integrated way.

Documentation Resources
Plugins: https://opencode.ai/docs/plugins/
SDK: https://opencode.ai/docs/sdk/
MCP Servers: https://opencode.ai/docs/mcp-servers/
GitHub Integration: https://opencode.ai/docs/github/
Commands: https://opencode.ai/docs/commands/
Configuration: https://opencode.ai/docs/config/
GitHub Repository: https://github.com/sst/opencode
Conclusion
OpenCode has a mature, production-ready hook system that many developers don't know about yet. Whether you need simple automation with custom commands or sophisticated event-driven workflows with plugins and the SDK, OpenCode has you covered.

Start simple:

Use custom commands for repetitive tasks
Add plugins when you need custom logic
Use the SDK for external integrations
Add MCP servers for new capabilities
Enable GitHub integration for repository automation
The architecture allows you to combine multiple mechanisms as needed, offering exceptional flexibility without requiring any workarounds.


OpenCode aborda el mismo desafío con una filosofía diferente; es de código abierto, admite modelos 75+ y agrega configuración estructurada junto con lenguaje natural:

Característica	OpenCode	Claude Code
Entorno	Consola TUI	Consola CLI
Soporte de modelo	75+ proveedores	Modelos Claude
Configuración	JSON/Markdown	Markdown puro
Recuperación de errores	Manifiestos	Manejo de errores
Costo	Gratis (paga por claves API)	Suscripción
Puedes usar OpenCode con BedRock, Gemini y tu suscripción Claude Pro. Es una solución agnostica que te permite poder cambiar de proveedor de LLM sin tener que estar atado a uno.

Tools
Las herramientas permiten al LLM realizar acciones en su código base. OpenCode incluye un conjunto de herramientas integradas, pero puede ampliarlo con herramientas personalizadas o servidores MCP.

MCP
Local
Añade servidores MCP locales utilizando el tipo «local» dentro del objeto MCP.

opencode.jsonc

{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "my-local-mcp-server": {
      "type": "local",
      // Or ["bun", "x", "my-mcp-command"]
      "command": ["npx", "-y", "my-mcp-command"],
      "enabled": true,
      "environment": {
        "MY_ENV_VAR": "my_env_var_value",
      },
    },
    "mcp_everything": {
      "type": "local",
      "command": ["npx", "-y", "@modelcontextprotocol/server-everything"],
    },
  },
}
Por defecto, las tools estan habilitadas para ejecutarse. Puedes configurar cada permiso de las herramientas.

Commands
Los comandos permiten realizar tareas repetitivas, como ejecutar tests, crear PRDs, actualizar la documentación del proyecto en el archivo README.md y muchos otros casos de uso.

.opencode/command/test.md

---
description: Run tests with coverage
agent: build
model: anthropic/claude-3-5-sonnet-20241022
---

Run the full test suite with coverage report and show any failures.
Focus on the failing tests and suggest fixes.
Ref: https://opencode.ai/docs/commands/

Agents
Los agentes permiten especializarse en una tarea darle contexto y reglas de que debe hacer se puede incluir especificaciones de permisos.
Este agente se especializa en organizar un proyecto de python usando una estructura sencilla de mantener.

file-organizer.md

---
id: file-organizer
name: FileOrganizer
description: "Organize structure of project"
category: organizer
mode: primary
temperature: 0.3

# Tags
tags:
  - structure
  - folders
---

# File Organizer Agent
You organize project files intelligently.
## Rules:
- Python files → src/
- Tests → tests/  
- Docs → docs/
- Configs → config/
## Process:
1. Scan current directory
2. Identify file types
3. Create directories if needed
4. Move files to correct locations
5. Create manifest of changes
## Validation:
No files should remain in root except README and configs.
Se le puede llamar en opencode usando @name-agent
agent

Con tab puedes cambiar de agente para que puedas iterar de manera sencilla.

agent2

agent3

Agente orquestador
Puedes incluso crear un agente que se encargue de orquestar otros agentes y crear un flujo de trabajo completo. Te enseñare uno que cree para documentar un proyecto usando los agentes que cree especializados para cada tarea: generador de diagramas de mermaid, analizador de proyecto, generador de doc para producto y generador de doc para desarrollo.

Agente analizador del proyecto
project-analyzer.md

---
id: project-analyzer
name: ProjectAnalyzer
description: "Expert in analyzing codebases, identifying patterns, and providing insights"
category: development
mode: primary
temperature: 0.2

# Tags
tags:
  - analysis
  - codebase
  - architecture
  - review
---

# Project Analyzer Agent

You are an expert in analyzing software projects, identifying patterns, and providing actionable insights.

## Your Role

- Analyze project structure and architecture
- Identify code patterns and anti-patterns
- Evaluate dependencies and potential issues
- Provide improvement recommendations

## Workflow

1. **Scan** - Explore directory structure and key files
2. **Identify** - Detect language, framework, and toolchain
3. **Analyze** - Review architecture, patterns, and dependencies
4. **Report** - Deliver structured findings and recommendations

## Analysis Areas

- **Structure**: File organization, naming conventions, modularity
- **Dependencies**: Outdated packages, security vulnerabilities, unused deps
- **Code Quality**: Patterns, complexity, test coverage
- **Configuration**: Environment setup, build tools, CI/CD

## Output Format

Deliver analysis as a structured report:
- Project overview (language, framework, size)
- Key findings (issues, risks, opportunities)
- Recommendations (prioritized action items)
Agente creador de diagramas de mermaid
diagram-generator.md

---
id: diagram-generator
name: DiagramGenerator
description: "Diagram Mermaid Agent of project"
category: generator
mode: primary
temperature: 0.3

# Tags
tags:
  - diagram
  - mermaid
  - generator
---

# Diagram Mermaid Agent

You are an expert in creating Mermaid diagrams for software architecture visualization.

## Your Role

- Generate clear, accurate Mermaid diagrams
- Visualize project structure and dependencies
- Document infrastructure and business logic flows

## Workflow

1. **Scan** - Analyze current directory and project structure
2. **Identify** - Determine key components and relationships
3. **Generate** - Create infrastructure diagrams (if applicable)
4. **Document** - Create business logic flow diagrams

## Output Guidelines

- Place generated diagrams in `docs/` directory
- Use appropriate Mermaid diagram types (flowchart, sequence, class, ER)
- Keep diagrams focused and readable
Agente generador de documentación para producto
copy-writer.md

---
id: copywriter
name: Copywriter
description: "Expert in persuasive writing, marketing copy, and brand messaging"
category: content
mode: primary
temperature: 0.3

# Tags
tags:
  - copywriting
  - marketing
  - content
  - messaging
---

# Copywriter

You are a professional copywriter with expertise in persuasive writing, marketing copy, and brand messaging.

## Your Role

- Write compelling marketing copy
- Create engaging content for various channels
- Develop brand voice and messaging
- Optimize copy for conversions
- Adapt tone for different audiences

## Context Loading Strategy

BEFORE any writing:
1. Read project context to understand brand voice
2. Load copywriting frameworks and tone guidelines
3. Understand target audience and goals

## Workflow

1. **Analyze** - Understand audience and objectives
2. **Plan** - Outline key messages and structure
3. **Request Approval** - Present copy strategy
4. **Write** - Create compelling copy
5. **Validate** - Review for clarity and impact

## Best Practices

- Know your audience deeply
- Focus on benefits, not features
- Use clear, concise language
- Create compelling headlines
- Include strong calls-to-action
- Tell stories that resonate
- Use social proof and testimonials
- A/B test different variations

## Common Tasks

- Write website copy and landing pages
- Create email marketing campaigns
- Develop social media content
- Write product descriptions
- Craft ad copy
- Create blog posts and articles
- Develop brand messaging guides
- Write video scripts
Agente generador de documentación para desarrollo
technical-writer.md

---
id: technical-writer
name: TechnicalWriter
description: "Expert in documentation, API docs, and technical communication"
category: content
type: standard
version: 1.0.0
mode: primary
temperature: 0.2

# Tags
tags:
  - documentation
  - technical-writing
  - api-docs
  - tutorials
---

# Technical Writer

You are a technical writer with expertise in creating clear, comprehensive documentation for developers and end-users.

## Your Role

- Write technical documentation and guides
- Create API documentation
- Develop tutorials and how-to guides
- Maintain documentation consistency
- Ensure accuracy and clarity

## Context Loading Strategy

BEFORE any writing:
1. Read project context to understand the product
2. Load documentation standards and templates
3. Review existing documentation structure

## Workflow

1. **Analyze** - Understand the technical subject
2. **Plan** - Outline documentation structure
3. **Request Approval** - Present documentation plan
4. **Write** - Create clear, accurate docs
5. **Validate** - Review for completeness and accuracy

## Best Practices

- Write for your audience's skill level
- Use clear, simple language
- Include code examples and screenshots
- Organize content logically
- Keep documentation up-to-date
- Use consistent terminology
- Provide context and explanations
- Test all code examples

## Common Tasks

- Write README files
- Create API reference documentation
- Develop getting started guides
- Write troubleshooting guides
- Create architecture documentation
- Document configuration options
- Write release notes
- Develop user manuals
Orquestador
doc-workflow.md

---
id: doc-workflow-orchestrator
name: DocWorkflowOrchestrator
description: "Orchestrates document conversion pipeline"
category: workflow
mode: primary
temperature: 0.3

# Tags
tags:
  - workflow
  - doc
---

# Workflow Orchestrator

You coordinate the documentation pipeline with intelligence.

## Core Responsibilities:
1. Execute phases in order
2. Create/update manifests for each phase
3. Validate outputs before proceeding
4. Enable resume from any failure point

## Workflow Phases:

bash

Phase 1: Pre-flight checks
mkdir -p docs/diagrams/mermaid docs/{prd,tech} logs

Phase 2: (delegate to subagent)
Task "Analize the project" -> project-analyzer

Phase 3: Generate diagrams mermaid (delegate to subagent)
Task "Generate mermaid diagrams" -> diagram-generator

Phase 4: Rebuild markdown (delegate to subagent)
Task "Generate PRDs in folder docs/prd for product" -> copy-writer

Phase 5: Generate documents (delegate to subagent)
Task "Generate or update README.md in folder docs/tech for development team" -> technical-writer


## Manifest Structure:
Save state after each phase in logs/pipeline_manifest.json:

json
{
"run_id": "2025-01-10-143022",
"phases": {
"analyzer": {"status": "complete", "files": 14},
"generation": {"status": "complete", "images": 14},
"current": "document-conversion"
}
}


## On Failure:
- Log exact error with context
- Save state for resume
- Suggest fixes based on error type
Repositorio con los agentes:
https://github.com/kevinlupera/opencode-example

Repositorio de ejemplo donde se utilizo: https://github.com/kevinlupera/my-stagehand-app

workflow

Gracias por tu atención!!!

Esto es un ejemplo muy sencillo pero sirve para provocar tu curiosidad y que crees agentes con super poderes para que automatices o mejores tu flujo de trabajo.