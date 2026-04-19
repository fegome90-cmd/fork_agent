# Context Analysis

## Run Information
- **Run ID**: run_20260227_8eb3edc3
- **Branch**: review/main-a0c15354
- **Base Branch**: main
- **Generated**: 2026-02-27T20:42:19.031Z

## Stack Detection

### Primary Stack
- **Languages**: Python, SQL
- **Frameworks**: None detected
- **Runtimes**: Python

### Secondary Components
- **Databases**: None detected
- **Services**: None detected
- **Build Tools**: pip, poetry/pdm

## Sensitive Zones Touched

| Zone | Files | Risk Level |
|------|-------|------------|
| Tests | docs/testing/bug-hunt-report.md, docs/testing/bug-report-template.md, tests/conftest.py... | LOW |
| Utilities | src/application/services/messaging/memory_hook.py | LOW |
| Configuration | src/application/services/messaging/memory_hook_config.py | MEDIUM |
| Database/Schema | src/infrastructure/persistence/migrations/006_create_promise_contracts_table.sql, src/infrastructure/persistence/migrations/008_add_idempotency_key.sql | HIGH |
| Authentication | src/infrastructure/persistence/migrations/007_add_tmux_sessions_killed_to_telemetry_sessions.sql | HIGH |
| API Endpoints | src/interfaces/api/config.py, src/interfaces/api/dependencies.py, src/interfaces/api/main.py... | MEDIUM |

## Relevant Commands

### Build/Test
```bash
bun run dev
bun run lint
```

### Database
```bash
bun run db:push
bun run db:generate
```

## Obvious Risks
1. Schema changes may require migrations - check for data loss scenarios
2. Authentication changes may affect security - careful review required
3. SQL queries present - check for injection vulnerabilities

## Recommended Agents

Based on detected stack:
- **Always**: code-reviewer, code-simplifier
- **Third**: silent-failure-hunter

## Recommended Static Tools

- ruff: Python linter and formatter
- pyrefly: Python type checker
- pytest: Python test execution gate
- coderabbit: AI external review (optional)
