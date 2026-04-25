# fork_agent - AGENTS.md (Quick Reference)
> Referencia rápida para orquestación de agentes autónomos y sub-agentes.
> **Última actualización**: 2026-04-25 | **Versión**: 2.7 (Test Coverage)
> **Fuente canónica**: `~/.pi/agent/skills/tmux-fork-orchestrator/SKILL.md`

---

## Source of Truth
Este repositorio opera bajo la **Constitucion de Codigo Agentico v1.1**.  
Source of Truth: `https://github.com/fegome90-cmd/constitucion-ai`

| Seccion | Fuente |
|---------|--------|
| Agent Rules | [AGENTS.md](AGENTS.md) |
| System Architecture | `src/infrastructure/` |
| Orquestación | `src/application/services/orchestration/` |

---

## 🏗 Arquitectura de Orquestación

`tmux_fork` es un orquestador multi-agente diseñado para manejar tareas de alta complejidad mediante la paralelización y el uso de un grafo de conocimiento (Trifecta).

### Componentes Clave:
- **Orquestador (Tú)**: Planifica, delega y monitorea.
- **Trifecta (v2.0)**: Motor de contexto semántico con latencia <1ms.
- **tmux-live**: Infraestructura de visualización de agentes en tiempo real.
- **Hybrid Mode (`FORK_HYBRID=1`)**: Despacho de herramientas vía MCP (21 tools disponibles).

---

## 🚦 Protocolo de 10 Fases (MANDATORIO)

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

| Rol | Modelo Recomendado | Propósito |
| :--- | :--- | :--- |
| **Explorer** | `deepseek/deepseek-v4-flash` | Investigación y mapeo. |
| **Architect** | `zai/glm-5.1` | Diseño y toma de decisiones. |
| **Implementer** | `zai/glm-5-turbo` | Escritura de código. |
| **Verifier** | `zai/glm-5-turbo` | Validación y tests. |
| **Analyst** | `zai/glm-5-turbo` | Investigación + propuesta de fix exacto. |

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

### Gestión de Tareas (Fork CLI):
```bash
fork task create "Descripción"   # PENDING -> PLANNING
fork task submit-plan <id>       # PLANNING -> APPROVED
fork task start <id>             # APPROVED -> IN_PROGRESS
fork task complete <id>          # IN_PROGRESS -> COMPLETED
```

### Orquestación en Vivo (tmux-live):
```bash
tmux-live init                   # Inicializar panel de control
tmux-live launch <role> <name>   # Lanzar sub-agente
tmux-live wait <name> 600        # Esperar finalización
tmux-live kill-all               # Limpieza total
```

---
*Nota: Referencia rápida — fuente canónica: `~/.pi/agent/skills/tmux-fork-orchestrator/SKILL.md`. Si hay discrepancias, SKILL.md tiene prioridad.*
