# fork_agent - AGENTS.md (Quick Reference)

> Referencia rápida para orquestación de agentes autónomos y sub-agentes.
> **Última actualización**: 2026-04-25 | **Versión**: 2.7 (Test Coverage)
> **Fuente canónica**: `~/.pi/agent/skills/tmux-fork-orchestrator/SKILL.md`

---

## Source of Truth

Este repositorio opera bajo la **Constitucion de Codigo Agentico v1.1**.  
Source of Truth: `https://github.com/fegome90-cmd/constitucion-ai`

| Seccion             | Fuente                                    |
| ------------------- | ----------------------------------------- |
| Agent Rules         | [AGENTS.md](AGENTS.md)                    |
| System Architecture | `src/infrastructure/`                     |
| Orquestación        | `src/application/services/orchestration/` |

---

## 🏗 Arquitectura de Orquestación

`tmux_fork` es un orquestador multi-agente diseñado para manejar tareas de alta complejidad mediante la paralelización y el uso de un grafo de conocimiento (Trifecta).

### Componentes Clave:

- **Orquestador (Tú)**: Planifica, delega y monitorea.
- **Trifecta (v2.0)**: Motor de contexto semántico con latencia <1ms.
- **tmux-live**: Infraestructura de visualización de agentes en tiempo real.
- **Hybrid Mode (`FORK_HYBRID=1`)**: Despacho de herramientas vía MCP (21 tools disponibles).

---

## Clasificación de Tamaño

| Tamaño | Umbral                        | Workflow                      |
| ------ | ----------------------------- | ----------------------------- |
| Small  | <50 líneas, 1 archivo         | Directo — sin protocolo       |
| Medium | 50-300 líneas, pocos archivos | Sequential — sin sub-agentes  |
| Large  | >300 líneas o "usa fork"      | Full orchestration — 10 fases |

## Protocolo de 10 Fases (MANDATORIO para Large)

Cualquier cambio sustancial DEBE seguir este flujo para garantizar la integridad del sistema:

1.  **Clarify**: Resolver ambigüedades con el usuario.
2.  **Plan**: Crear el plan de implementación (`memory workflow outline`).
3.  **Plan Gate**: MANDATORY. Present plan to user and wait for approval. See protocol.md §1.5.
4.  **Pre-flight**: Verificación de entorno (`trifecta-daemon-warmup` + `trifecta-auto-sync`).
5.  **Save**: Persistir el estado inicial en memoria (`memory save`).
6.  **Spawn**: Lanzar sub-agentes en tmux con contexto inyectado (`trifecta-context-inject`).
7.  **Monitor**: Seguimiento en vivo vía `tmux-live progress`.
8.  **Consolidate**: Unificar hallazgos y resolver conflictos (`conflict-detect`).
9.  **Validate**: Verificación técnica (tests + `trifecta-verifier-check`).
10. **Cleanup**: Limpieza de recursos y log de sesión (`trifecta-session-log`).

---

## 🧠 Integración con Trifecta v2

Trifecta provee el contexto necesario para que los agentes no operen a ciegas.

### Comandos Esenciales:

- `trifecta ctx search "<query>"`: Búsqueda semántica en el grafo.
- `trifecta ast symbols <file>`: Extracción de símbolos y tipos.
- `trifecta-context-inject`: Script para ensamblar el prompt enriquecido.
- `fork doctor status`: Verificación de salud del sistema de contexto.

---

## 🤖 Asignación de Modelos (Tier Pro)

**Regla de Oro (P11)**: Los modelos gratuitos fallan un 30-70% en tareas paralelas. Usar el tier pagado para 2+ agentes concurrentes.

| Rol                    | Modelo Recomendado           | Propósito                                |
| :--------------------- | :--------------------------- | :--------------------------------------- |
| **Explorer (locate)**  | `opencode/minimax-m2.5-free` | Búsquedas, grep, paths.                  |
| **Explorer (analyze)** | `zai/glm-5-turbo`            | Análisis, comparación, síntesis.         |
| **Architect**          | `zai/glm-5.1`                | Diseño y toma de decisiones.             |
| **Implementer**        | `zai/glm-5-turbo`            | Escritura de código.                     |
| **Verifier**           | `zai/glm-5-turbo`            | Validación y tests.                      |
| **Analyst**            | `zai/glm-5-turbo`            | Investigación + propuesta de fix exacto. |

---

## 🛠 Configuración de Rutas

- `PROJECT_DIR`: El repositorio que estás orquestando (Target).
- `BACKEND_DIR`: El código fuente del orquestador (`~/Developer/tmux_fork`).
- **Persistencia**: La base de datos de memoria reside por defecto en `~/.local/share/fork/memory.db`.

---

## 🛡 Governance Mode

**Advisory-only:** `GOVERNANCE=1` activa guidelines para el orquestador. Sin code enforcement.

Cuando está activo, las fases del protocolo se enriquecen con:

- **CLOOP** (Clarify→Layout→Operate→Observe→Reflect)
- **SDD** (propose→spec→design→tasks→gate→apply→verify→archive)
- **Quality Check** (Phase 5.7)

Sin `GOVERNANCE=1`, todo funciona idéntico.

---

## ⚡ Hybrid Mode

`FORK_HYBRID=1` despacha herramientas vía MCP server (21 tools).
Latencia: ~28ms por call (raw httpx JSON-RPC) vs ~234ms (MCP SDK).

---

## 📋 Comandos de Referencia Rápida

### Gestión de Tareas (fork task):

```bash
fork task create "Descripción"        # Crear tarea en estado PENDING
fork task submit-plan <id>            # Enviar plan para aprobación
fork task approve <id>                # Aprobar plan
fork task reject <id>                 # Rechazar plan (vuelve a PENDING)
fork task start <id>                  # Iniciar tarea aprobada
fork task complete <id>               # Marcar como completada
fork task list                        # Listar tareas
fork task update <id>                 # Actualizar tarea
fork task delete <id>                 # Eliminar tarea (soft delete)
fork task assign <id>                 # Asignar tarea a agente
```

### Orquestación en Vivo (tmux-live):

```bash
tmux-live init                   # Inicializar panel de control
tmux-live launch <role> <name>   # Lanzar sub-agente
tmux-live wait <name> 600        # Esperar finalización
tmux-live wait-all               # Esperar todos los agentes
tmux-live kill-all               # Limpieza total
```

### Fork CLI:

```bash
fork run "<command>"                  # Forkear un terminal
fork doctor status                    # Health check del sistema
fork doctor reconcile                 # Reconciliar sesiones tmux
fork doctor cleanup-orphans           # Limpiar sesiones huérfanas
fork poll start                       # Iniciar polling autónomo
fork adapter detect                   # Detectar adapter de terminal
fork template list                    # Listar templates de agente
```

### Memory CLI:

```bash
# Launch lifecycle (10 subcommands)
memory launch request                 # Solicitar permiso para lanzar agente
memory launch confirm-spawning <id>   # Confirmar spawn iniciado
memory launch confirm-active <id>     # Confirmar agente activo
memory launch mark-failed <id>        # Marcar lanzamiento como fallido
memory launch begin-termination <id>  # Iniciar terminación
memory launch confirm-terminated <id> # Confirmar terminación completa
memory launch status <id>             # Estado de un lanzamiento
memory launch list-active             # Listar lanzamientos activos
memory launch summary                 # Conteo por estado
memory launch list-quarantined        # Listar lanzamientos en cuarentena

# MCP server
memory mcp serve                      # Iniciar MCP stdio server
memory mcp start                      # Iniciar MCP HTTP server (background)
memory mcp stop                       # Detener MCP server
memory mcp status                     # Estado del MCP server

# Workspace (git worktree)
memory workspace create <name>        # Crear workspace
memory workspace list                 # Listar workspaces
memory workspace remove <name>        # Eliminar workspace

# Workflow
memory workflow outline               # Crear plan de workflow
memory workflow execute               # Ejecutar tareas del plan
memory workflow verify                # Verificar ejecución
```

---

_Nota: Referencia rápida — fuente canónica: `~/.pi/agent/skills/tmux-fork-orchestrator/SKILL.md`. Si hay discrepancias, SKILL.md tiene prioridad._
