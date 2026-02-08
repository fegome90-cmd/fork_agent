# Diff - MCP vs fork_agent

Fecha: 2026-02-08

## Alcance
Comparativa entre el MCP de referencia (claude-code-teams-mcp) y el repo fork_agent.

## MCP (referencia)
- MCP server con herramientas de equipos/tareas/mensajeria.
- Storage filesystem en ~/.claude/teams y ~/.claude/tasks.
- Locks fcntl y writes atomicos.
- Spawner basado en tmux (flags claude + prompt inicial).
- Tests extensivos para validaciones y edge cases.

## fork_agent (actual)
- Skill de fork terminal con soporte multi-plataforma.
- Cookbook y prompts para CLI (Claude/Codex/Gemini/Raw).
- No existe MCP server ni protocolo de equipos/tareas.
- No existe storage de inbox/tasks ni locks.
- No existe runtime de agentes persistente.

## Diferencias clave
- MCP implementa coordinacion multi-agente; fork_agent solo bifurca terminales.
- MCP define modelos de datos y persistencia; fork_agent no.
- MCP tiene API MCP; fork_agent no.
- MCP tiene spawner especializado; fork_agent usa ejecucion generica.

## Oportunidades de adaptacion (sin tmux)
- Reusar protocolo filesystem (JSON + locks) para coordinacion.
- Definir MCP interno para exponer herramientas.
- Implementar spawner alternativo (subprocess/systemd) con backend_type.
- Incorporar validaciones y edge cases de los tests MCP.
