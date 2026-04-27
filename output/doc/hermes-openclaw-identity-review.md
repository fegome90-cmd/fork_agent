# Modelos de Identidad de Agente: Hermes vs OpenClaw/Paperclip

> **Informe Tecnico** — Aplicabilidad al sistema de orquestacion tmux_fork
>
> **Fecha**: 25 de abril de 2026 | **Proyecto**: tmux_fork / fork_agent
>
> **Clasificacion**: Interno — Revision Arquitectonica

---

## Tabla de Contenidos

- [1. Resumen Ejecutivo](#1-resumen-ejecutivo)
- [2. Contexto y Motivacion](#2-contexto-y-motivacion)
- [3. Hermes: Modelo de Identidad](#3-hermes-modelo-de-identidad)
  - [3.1 Arquitectura de Identidad](#31-arquitectura-de-identidad)
  - [3.2 Modelo de Datos](#32-modelo-de-datos)
  - [3.3 Session Lineage y Compresion](#33-session-lineage-y-compresion)
  - [3.4 Fortalezas](#34-fortalezas)
  - [3.5 Debilidades para Orquestacion](#35-debilidades-para-orquestacion)
- [4. OpenClaw / Paperclip: Modelo de Identidad](#4-openclaw--paperclip-modelo-de-identidad)
  - [4.1 Arquitectura de Identidad](#41-arquitectura-de-identidad)
  - [4.2 Modelo de Datos](#42-modelo-de-datos)
  - [4.3 Protocolo de Adapter](#43-protocolo-de-adapter)
  - [4.4 Sistema de Autenticacion](#44-sistema-de-autenticacion)
  - [4.5 Fortalezas](#45-fortalezas)
  - [4.6 Debilidades](#46-debilidades)
- [5. tmux_fork: Estado Actual](#5-tmux_fork-estado-actual)
  - [5.1 Modelo de Identidad Existente](#51-modelo-de-identidad-existente)
  - [5.2 Gaps Identificados](#52-gaps-identificados)
- [6. Analisis Comparativo](#6-analisis-comparativo)
  - [6.1 Tabla Comparativa de Dimensiones](#61-tabla-comparativa-de-dimensiones)
  - [6.2 Matriz de Aplicabilidad](#62-matriz-de-aplicabilidad)
  - [6.3 Trade-offs Clave](#63-trade-offs-clave)
- [7. Recomendacion de Diseno](#7-recomendacion-de-diseno)
  - [7.1 Principios de Diseno](#71-principios-de-diseno)
  - [7.2 Propuesta de Identidad de Agente](#72-propuesta-de-identidad-de-agente)
  - [7.3 Propuesta de Tracking de Runs](#73-propuesta-de-tracking-de-runs)
  - [7.4 Schema SQLite Propuesto](#74-schema-sqlite-propuesto)
  - [7.5 Lo que NO Implementar](#75-lo-que-no-implementar)
- [8. Plan de Implementacion Sugerido](#8-plan-de-implementacion-sugerido)
- [9. Riesgos y Mitigaciones](#9-riesgos-y-mitigaciones)
- [10. Conclusiones](#10-conclusiones)
- [A. Apéndice: Referencia de Schema](#a-apendice-referencia-de-schema)

---

## 1. Resumen Ejecutivo

Este informe analiza los modelos de identidad de agente utilizados por dos sistemas de produccion — Hermes (agente unico de conversacion) y OpenClaw/Paperclip (plataforma multi-agente) — y evalua su aplicabilidad al diseno del sistema de identidad de tmux_fork, un orquestador multi-agente basado en tmux.

El objetivo es identificar que patrones, estructuras de datos y mecanismos de tracking de cada sistema son relevantes para tmux_fork, y cuales representan over-engineering o no aplican al caso de uso local.

**Hallazgos principales:**

- **Hermes** ofrece un modelo de conversacion solido (session lineage, compression chains, title inheritance) pero cero soporte para jerarquia de sub-agentes. Aporta el patron de title lineage y la solidez de SQLite WAL con jitter retry.
- **OpenClaw/Paperclip** tiene la arquitectura correcta para orquestacion: jerarquia agent-run-task, session keys con prefijo de agente, adapter protocol tipado, y autenticacion por tiers. Sin embargo, su stack completo (PostgreSQL, Ed25519, 6-component subsystem) es excesivo para un orquestador local.
- **tmux_fork** ya posee la entidad AgentLaunch (8-state FSM, canonical_key dedup, lease expiry) que es la base mas solida del repo. Los gaps son: IDs fragiles (`Date.now()`), nombres por regex, sin correlacion pane-estado, sin parent-child.
- **La recomendacion** es un enfoque hibrido: tomar de Hermes el session lineage + title pattern, de OpenClaw las claves jerarquicas + adapter result tipado, mantener SQLite, y saltear Ed25519, PostgreSQL y protocolo complejo de adapter.

---

## 2. Contexto y Motivacion

tmux_fork es un orquestador multi-agente que coordina sub-agentes autonomos a traves de tmux panes. El sistema necesita un modelo de identidad robusto que permita:

- Identificar univocamente cada agente spawned (explorer, architect, implementer, verifier, analyst)
- Trackear la jerarquia de spawns (orquestrador lanza N sub-agentes)
- Correlacionar el pane de tmux con el estado interno del agente
- Persistir el historial de runs para debugging y analisis post-mortem
- Soportar reanudacion de sesiones (session resume)
- Mantener un budget de contexto razonable (~300 lineas por recurso)

El sistema actual tiene debilidades fundamentales (IDs basados en timestamp, nombres extraidos por regex) que deben resolverse antes de escalar la orquestacion.

**Fuentes analizadas:**

| Fuente | Ubicacion | Descripcion |
|--------|-----------|-------------|
| Hermes | `~/Developer/hermes-agent/` | Agente CLI de un solo proceso con SQLite |
| OpenClaw | `~/.openclaw/` | Sistema de agentes local con Ed25519 + session keys |
| Paperclip | `~/Developer/paperclip/` | Plataforma multi-agente con PostgreSQL + adapter protocol |
| tmux_fork | `~/Developer/tmux_fork/` | El orquestador objetivo |

---

## 3. Hermes: Modelo de Identidad

### 3.1 Arquitectura de Identidad

Hermes es un agente CLI de un solo proceso que maneja conversaciones a traves de multiples plataformas (CLI, Telegram, Discord). Su modelo de identidad es inherentemente flat: un agente, multiples sesiones de conversacion.

```
Session Identity:
  session_id:        UUID4 (primary key)
  source:            "cli" | "telegram" | "discord" | ...
  user_id:           Optional[str]  — sin multi-tenancy real
  parent_session_id: Optional[str]  — SOLO para compression chains
  model:             str — modelo LLM usado
  title:             Optional[str]  — titulo sanitizado, unique
```

La identidad se reduce a un `session_id` unico por conversacion. No existe el concepto de "agente" como entidad separada — el proceso Hermes es el agente.

### 3.2 Modelo de Datos

Schema SQLite (version 8, con migraciones incrementales):

| Tabla | Proposito | Columnas Clave |
|-------|-----------|----------------|
| `sessions` | Registro de conversaciones | `id`, `source`, `user_id`, `model`, `parent_session_id`, `title`, `started_at`, `ended_at`, `end_reason` |
| `messages` | Historial de mensajes | `id`, `session_id`, `role`, `content`, `tool_calls`, `timestamp`, `token_count`, `finish_reason`, `reasoning` |
| `messages_fts` | Busqueda full-text (FTS5) | `content` (virtual table sobre messages) |
| `schema_version` | Versionado de schema | `version INTEGER` |

El manejo de concurrencia es notable: WAL mode + application-level retry con random jitter (20-150ms, max 15 retries) para evitar convoy effects en write contention. `CHECKPOINT_EVERY_N_WRITES = 50` con PASSIVE mode.

### 3.3 Session Lineage y Compresion

Hermes implementa un mecanismo de compression donde una sesion que crece demasiado se cierra (`end_reason='compression'`) y se crea una sesion hija con `parent_session_id` apuntando a la padre.

```
Compression Chain:

  Session A (end_reason='compression')
    └── Session B (parent_session_id = A)
          └── Session C (parent_session_id = B)

  get_compression_tip(A) → C  (camina hasta el vivo)
  list_sessions_rich() proyecta A → C (muestra C con started_at de A)
```

El metodo `get_compression_tip()` camina la cadena forward para siempre apuntar a la sesion activa. `list_sessions_rich()` proyecta las sesiones raiz hacia sus tips, mostrando una conversacion logica como una sola entrada.

El title lineage tambien es sofisticado: `get_next_title_in_lineage()` genera `"Mi sesion #2"`, `"Mi sesion #3"` etc., resolviendo el problema de continuidad visual para el usuario.

### 3.4 Fortalezas

- **Session title con lineage**: Resolucion automatica de conflictos con `#2`, `#3`. Unique index con NULLs allowed.
- **Compression chain walking**: `get_compression_tip()` siempre apunta al vivo. Proyeccion en `list_sessions_rich()` para UX limpia.
- **Prefix resolution**: `resolve_session_id()` acepta prefijos unicos de UUID.
- **SQLite WAL con jitter retry**: Patron productivo para write contention. 15 retries con random 20-150ms.
- **Title sanitization**: Limpieza de caracteres de control, CJK detection, max 100 chars, validacion de colisiones.
- **FTS5 search**: Full-text search sobre mensajes con sanitizacion de query (preserva quoted phrases, escapa FTS5 specials).
- **Billing granular**: Tracking de input/output/cache/reasoning tokens, estimated vs actual cost, pricing version.

### 3.5 Debilidades para Orquestacion

- **Cero soporte para sub-agentes**: No existe el concepto de jerarquia, delegacion, ni tracking de spawns. `parent_session_id` es SOLO para compresion.
- **Sin device identity ni auth**: Todo es local trust. Sin API keys, sin JWT, sin notion de "quien" ejecuta.
- **Sin multi-tenancy**: `user_id` es opcional y no hay scoping por company.
- **Sin runtime state**: No persiste estado resumible entre sesiones. Cada sesion empieza desde cero con el system prompt.
- **Sin adapter protocol**: No hay abstraccion sobre el runtime subyacente.

> **VEREDICTO**: Hermes es un modelo de conversacion, no de orquestacion. Su valor para tmux_fork esta en los patrones de session lineage, title management y SQLite concurrency, NO en el modelo de identidad de agente.

---

## 4. OpenClaw / Paperclip: Modelo de Identidad

### 4.1 Arquitectura de Identidad

OpenClaw (capa local) y Paperclip (capa servidor) conforman una plataforma multi-agente completa con jerarquia real, autenticacion por tiers, y persistencia estructurada de runs.

```
Identity Hierarchy:

  Device  → Ed25519 keypair (~/.openclaw/identity/device.json)
            {deviceId, publicKeyPem, privateKeyPem, createdAtMs}

  Agent   → {id, name, identity: {name, theme, emoji, avatar},
             auth-profiles, models}
            Stored at ~/.openclaw/agents/{agentId}/

  Session → Key format: agent:{agentId}:{type}:{uuid}
            Strategies: "fixed", "issue", "run"

  Run     → {runId, agentId, companyId, adapterType, sessionId,
             wakeupSource, prompt, runtimeState}
            Tracked in heartbeat_runs (PostgreSQL)

  Task    → {taskKey, companyId, agentId, adapterType,
             sessionParamsJson, sessionDisplayId}
            Tracked in agent_task_sessions (PostgreSQL)
```

### 4.2 Modelo de Datos

Schema PostgreSQL (Drizzle ORM):

| Tabla | Proposito | Columnas Clave |
|-------|-----------|----------------|
| `agent_runtime_state` | Estado resumible por agente | `agentId` (PK), `companyId`, `adapterType`, `sessionId`, `stateJson`, `totalInputTokens`, `totalOutputTokens`, `totalCostCents`, `lastRunId`, `lastError` |
| `agent_task_sessions` | Sesiones por tarea | `id` (UUID), `companyId`, `agentId`, `adapterType`, `taskKey` (UNIQUE composite), `sessionParamsJson`, `sessionDisplayId`, `lastRunId` |
| `heartbeat_runs` | Lifecycle de ejecuciones | `id`, `agentId`, `companyId`, `status`, `exitCode`, `errorMessage`, `usage` (tokens), `costUsd` |

La tabla `agent_task_sessions` tiene un unique index compuesto `(companyId, agentId, adapterType, taskKey)` que garantiza una sola sesion por tarea por agente, habilitando reanudacion natural.

### 4.3 Protocolo de Adapter

Paperclip define un adapter protocol tipado (`agent-run/v1`) con interfaces formales para invoke, hooks y resultado:

```typescript
// Adapter Protocol (agent-run/v1)

interface AdapterInvokeInput {
  protocolVersion: "agent-run/v1";
  companyId: string;
  agentId: string;
  runId: string;
  wakeupSource: "timer" | "assignment" | "on_demand" | "automation";
  cwd: string;
  prompt: string;
  adapterConfig: Record<string, unknown>;
  runtimeState: Record<string, unknown>;
  env: Record<string, string>;
  timeoutSec: number;
}

interface AdapterInvokeResult {
  outcome: "succeeded" | "failed" | "cancelled" | "timed_out";
  exitCode: number | null;
  errorMessage?: string | null;
  summary?: string | null;
  sessionId?: string | null;
  usage?: TokenUsage | null;
  provider?: string | null;
  model?: string | null;
  costUsd?: number | null;
  runtimeStatePatch?: Record<string, unknown>;  // clave para resumabilidad
}

interface AgentRunAdapter {
  type: string;
  protocolVersion: "agent-run/v1";
  capabilities: {
    resumableSession: boolean;
    statusUpdates: boolean;
    logStreaming: boolean;
    tokenUsage: boolean;
  };
  validateConfig(config: unknown): { ok: true } | { ok: false; errors: string[] };
  invoke(input: AdapterInvokeInput, hooks: AdapterHooks, signal: AbortSignal): Promise<AdapterInvokeResult>;
}
```

El campo `runtimeStatePatch` en el resultado permite que el adapter devuelva estado parcial que se mergea con el existente, habilitando reanudacion exacta en el siguiente run.

### 4.4 Sistema de Autenticacion

Paperclip implementa autenticacion en 3 tiers:

| Tier | Trust Model | Mecanismo | Token Lifetime |
|------|-------------|-----------|----------------|
| **Tier 1: Local Adapter** | Mismo proceso/host | JWT HS256 (no stored) | 48h, overlap window |
| **Tier 2: CLI Key Exchange** | Developer con shell access | Long-lived API key (hashed server-side) | Indefinido |
| **Tier 3: Self-Registration** | Agente autonomo externo | Invite URL + approval gate | Post-approval: API key |

El JWT para local adapters se genera por heartbeat invocation: `createLocalAgentJwt(agentId, companyId, adapterType, runId)` produce un token con claims `{sub, company_id, adapter_type, run_id, iat, exp}`. El server valida la firma HMAC-SHA256 con timing-safe comparison.

### 4.5 Fortalezas

- **Jerarquia real agent-run-task**: Cada nivel tiene ID propio, estado propio, y relacion explicita con el nivel superior.
- **Session keys con prefijo de agente**: Formato `agent:{agentId}:{type}:{uuid}` garantiza aislamiento natural entre agentes.
- **runtimeStatePatch**: El adapter devuelve estado parcial que se mergea. Resumabilidad exacta sin re-procesar todo.
- **Multi-tenancy por companyId**: Scoping en todas las tablas. Un agente no ve datos de otro company.
- **Auth maduro por tiers**: Complejidad de auth proporcional al trust boundary. Local = JWT simple, remoto = API key + approval.
- **Observabilidad en tiempo real**: WebSocket/SSE push, status updates con color, log streaming pluggable (local_file, object_store, postgres).
- **Unique index por tarea**: `agent_task_sessions` garantiza una sesion por `(company, agent, adapter, taskKey)`. Dedup natural.

### 4.6 Debilidades

- **Ed25519 para device identity**: Overkill para orquestacion local. Generar y verificar keypairs agrega complejidad sin beneficio cuando todo corre en la misma maquina bajo el mismo usuario.
- **PostgreSQL como requisito**: Infraestructura pesada para un orquestador CLI que corre en developer laptops. SQLite es mas apropiado.
- **6-component subsystem**: Adapter Registry, Wakeup Coordinator, Run Executor, Runtime State Store, Run Log Store, Realtime Event Hub. Demasiado para un sistema que maneja 3-5 agentes concurrentes.
- **Drizzle ORM dependency**: Coupling con un ORM especifico de TypeScript.
- **Over-engineering para CLI**: El adapter protocol define capabilities, validateConfig, hooks de streaming, log storage pluggable. Un sub-agente en tmux no necesita todo esto.

---

## 5. tmux_fork: Estado Actual

### 5.1 Modelo de Identidad Existente

tmux_fork ya tiene entidades de dominio maduras para el lifecycle de agentes. La entidad `AgentLaunch` es la pieza mas solida del sistema.

#### AgentLaunch Entity

```python
@dataclass(frozen=True)
class AgentLaunch:
    launch_id:            str          # UUID4
    canonical_key:        str          # Dedup key
    surface:              str          # polling|workflow|api|manager|bug_hunt
    owner_type:           str          # task|run|session|batch
    owner_id:             str
    status:               LaunchStatus # 8-state FSM
    backend:              str | None   # tmux|subprocess
    tmux_session:         str | None
    tmux_pane_id:         str | None
    termination_handle:   dict[str, str | None]
    prompt_digest:        str | None
    request_fingerprint:  str | None
    lease_expires_at:     int | None   # safety cutoff

    # States: RESERVED → SPAWNING → ACTIVE → TERMINATING → TERMINATED
    #                                          → FAILED
    #                                          → QUARANTINED
```

#### EventMetadata

```python
@dataclass
class EventMetadata:
    run_id:     str   # UUID of current run/session
    task_id:    str   # Task being worked on
    agent_id:   str   # Agent identifier in session:window format

    # Event key format: {run_id}:{task_id}:{event_type}:{sequence}
```

### 5.2 Gaps Identificados

| Gap | Severidad | Descripcion | Impacto |
|-----|-----------|-------------|---------|
| IDs basados en `Date.now()` | **ALTA** | Colisiones posibles bajo spawns rapidos. No es criptograficamente unico. | Dos agentes pueden recibir el mismo ID, corrompiendo tracking y dedup. |
| Nombre por regex | **MEDIA** | El nombre del agente se extrae via regex del prompt. Fragil ante cambios de formato. | Nombres incorrectos rompen correlacion con pane y dificultan debugging. |
| Sin pane-estado correlacion | **ALTA** | El tmux pane id se almacena pero no se correlaciona con el estado del agente. | Imposible saber que esta haciendo un agente desde tmux sin parsing manual. |
| Sin parent-child | **ALTA** | `AgentLaunch` no tiene `parent_launch_id`. No se trackea quien spawn a quien. | No se puede reconstruir el arbol de delegacion post-mortem. |
| TaskExecute roto | **CRITICA** | pi TaskExecute requiere `@tintinweb/pi-subagents` (bloqueado por policy). | Delegacion nativa via pi no funciona. Workaround: bash background + `pi --mode json`. |
| Sin session resume | **MEDIA** | No se persiste runtime state resumible. Cada spawn empieza desde cero. | No se puede reanudar un agente que fallo sin re-ejecutar todo el prompt. |

---

## 6. Analisis Comparativo

### 6.1 Tabla Comparativa de Dimensiones

| Dimension | Hermes | OpenClaw/Paperclip | tmux_fork (actual) |
|-----------|--------|--------------------|--------------------|
| Tipo de sistema | Agente unico (conversacion) | Plataforma multi-agente (produccion) | Orquestador multi-agente (local CLI) |
| Identidad de agente | N/A (proceso = agente) | `{id, name, identity, auth-profiles, models}` | `canonical_key` + `surface` + `owner_type/owner_id` |
| Identidad de sesion | UUID4 `session_id` | `agent:{agentId}:{type}:{uuid}` | `launch_id` (UUID4) |
| Jerarquia | Flat (solo compression chain) | Agent → Run → Task → Runtime State | Flat (sin parent-child) |
| Sub-agent tracking | No | Si (`childSessionKey`, `controllerSessionKey`) | No |
| Session resume | No (cada sesion empieza de cero) | Si (`runtimeStatePatch` + `sessionId` persistente) | No |
| Autenticacion | Local trust | 3-tier (JWT, API key, invite URL) | Local trust |
| Persistencia | SQLite WAL + FTS5 | PostgreSQL (Drizzle ORM) | SQLite |
| Concurrency | Jitter retry (15 att, 20-150ms) | DB-level (Postgres locks) | Thread locks basicos |
| Observabilidad | Title + message count + token tracking | WebSocket/SSE push, log streaming, status color | AgentLaunch status FSM (8 estados) |
| Token/cost tracking | Granular (7 campos de tokens + cost) | Acumulativo por agente (`totalInputTokens`, `totalCostCents`) | No implementado |
| Busqueda | FTS5 full-text | PostgreSQL full-text | N/A |
| Multi-tenancy | No | Si (`companyId`) | No (local) |
| Complejidad | Baja (2 tablas core) | Alta (6 componentes, 3 tablas core) | Media (5+ entidades) |

### 6.2 Matriz de Aplicabilidad

Que componentes de cada sistema son aplicables a tmux_fork:

| Componente | Fuente | Aplica? | Justificacion |
|------------|--------|---------|---------------|
| Session lineage (compression) | Hermes | **SI** | Util para agentes de larga duracion que exceden context window. |
| Title lineage (#2, #3) | Hermes | **SI** | Resuelve continuidad visual cuando un agente se re-lanza. |
| SQLite WAL + jitter retry | Hermes | **SI** | Patron productivo para write contention. Ya lo usa tmux_fork. |
| FTS5 full-text search | Hermes | **TAL VEZ** | Util si se indexan outputs de agentes. No critico para MVP. |
| Token/cost tracking granular | Hermes | **SI** | 7 campos de tokens + cost estimation. Valioso para budget control. |
| Hierarchical session keys | OpenClaw | **SI** | Formato `agent:{role}:{hex8}` da aislamiento natural. |
| runtimeStatePatch | OpenClaw | **SI** | Clave para reanudabilidad. Merge de estado parcial. |
| Agent → Run → Task hierarchy | OpenClaw | **SI** | Estructura correcta para orquestacion. Ya parcialmente en AgentLaunch. |
| Unique index por tarea | OpenClaw | **SI** | Dedup natural. Ya existe via `canonical_key` en AgentLaunch. |
| Adapter protocol (6 componentes) | OpenClaw | **NO** | Over-engineering para 3-5 agentes. Simplificar a invoke + result. |
| Ed25519 device identity | OpenClaw | **NO** | Overkill para orquestacion local. No hay trust boundary. |
| PostgreSQL | OpenClaw | **NO** | SQLite es apropiado para CLI local. Menos dependencias. |
| 3-tier auth | OpenClaw | **NO** | Solo local trust es necesario. Tier 1 (JWT) si se integra con Paperclip. |
| WebSocket/SSE push | OpenClaw | **NO** | tmux-live ya proporciona observabilidad en panes. |
| Drizzle ORM | OpenClaw | **NO** | tmux_fork usa Python + raw SQL. No agregar dependency. |

### 6.3 Trade-offs Clave

- **Simplicidad vs Resumabilidad**: Agregar `runtimeStatePatch` incrementa complejidad pero habilita reanudacion. Para un MVP, se puede empezar sin ella y agregarla cuando la reanudacion sea critica.
- **Jerarquia vs Flat**: Un modelo jerarquico (parent-child) es mas complejo de consultar pero indispensable para debugging post-mortem. El costo de no tenerlo es alto: imposible reconstruir quien spawneo a quien.
- **IDs deterministas vs aleatorios**: UUID4 es aleatorio y no colisiona. `Date.now()` es determinista pero colisiona bajo alta concurrencia. La recomendacion es UUID4 para `launch_id` y un formato legible (`agent:{role}:{hex8}`) para display.
- **SQLite vs PostgreSQL**: SQLite es suficiente para un orquestador local. PostgreSQL agrega setup cost, dependency, y complejidad operacional que no se justifica para el caso de uso.

---

## 7. Recomendacion de Diseno

### 7.1 Principios de Diseno

- **CORRECTNESS**: IDs que no colisionen, transiciones de estado validas, dedup confiable.
- **OBSERVABILITY**: Poder reconstruir el arbol de delegacion post-mortem.
- **SIMPLICITY**: SQLite, sin crypto, sin ORM, sin protocolo complejo.
- **COMPATIBILITY**: Reutilizar AgentLaunch existente. Agregar campos, no reescribir.
- **INCREMENTAL**: Cada fase agrega valor independiente. No blocking dependencies.

### 7.2 Propuesta de Identidad de Agente

```
Agent Identity Format:

  Display:   explorer:01   architect:a3   implementer:f7
  Internal:  agent:{role}:{hex8}
  Full ID:   {launch_id}  (UUID4, primary key)

  Role mapping:
    explorer    → deepseek/deepseek-v4-flash
    architect   → zai/glm-5.1
    implementer → zai/glm-5-turbo
    verifier    → zai/glm-5-turbo
    analyst     → zai/glm-5-turbo

  Properties:
    - Deterministic for display (role:hex8)
    - Unique via UUID4 launch_id
    - Human-readable role prefix
    - 8-char hex suffix from launch_id (first 8 chars)
```

### 7.3 Propuesta de Tracking de Runs

Extender AgentLaunch con parent-child:

```python
# AgentLaunch Extensions:

+ parent_launch_id:  Optional[str]  # quien spawneo este agente
+ display_name:      str            # "explorer:01" legible
+ role:              str            # explorer|architect|implementer|...
+ model:             str            # modelo LLM asignado
+ output_artifact:   Optional[str]  # path al archivo de salida
+ started_at:        Optional[int]  # ms epoch
+ completed_at:      Optional[int]  # ms epoch
+ token_usage:       Optional[dict] # {input, output, cache, cost}

# Query patterns:
#   - Arbol de delegacion:   WHERE parent_launch_id = X
#   - Runs activos:          WHERE status IN (RESERVED, SPAWNING, ACTIVE)
#   - Historial por rol:     WHERE role = 'explorer'
#   - Costo acumulado:       SUM(token_usage.cost) GROUP BY role
```

### 7.4 Schema SQLite Propuesto

```sql
-- agent_runs: extends existing AgentLaunch table
CREATE TABLE agent_runs (
    launch_id           TEXT PRIMARY KEY,         -- UUID4
    canonical_key       TEXT NOT NULL,            -- dedup
    display_name        TEXT NOT NULL,            -- "explorer:01"
    role                TEXT NOT NULL,            -- explorer|architect|...
    model               TEXT,                     -- assigned LLM model
    surface             TEXT NOT NULL,            -- polling|workflow|api
    owner_type          TEXT NOT NULL,            -- task|run|session
    owner_id            TEXT NOT NULL,
    parent_launch_id    TEXT,                     -- hierarchy
    status              TEXT NOT NULL DEFAULT 'RESERVED',
    backend             TEXT,                     -- tmux|subprocess
    tmux_session        TEXT,
    tmux_pane_id        TEXT,
    prompt_path         TEXT,                     -- @/tmp/fork-prompt-...
    output_artifact     TEXT,                     -- @/tmp/fork-ROLE-ID.md
    prompt_digest       TEXT,
    request_fingerprint TEXT,
    token_input         INTEGER DEFAULT 0,
    token_output        INTEGER DEFAULT 0,
    token_cache         INTEGER DEFAULT 0,
    estimated_cost      REAL DEFAULT 0.0,
    created_at          INTEGER NOT NULL,         -- ms epoch
    started_at          INTEGER,
    completed_at        INTEGER,
    ended_at            INTEGER,
    lease_expires_at    INTEGER,
    last_error          TEXT,
    quarantine_reason   TEXT,

    FOREIGN KEY (parent_launch_id) REFERENCES agent_runs(launch_id)
);

CREATE INDEX idx_runs_parent    ON agent_runs(parent_launch_id);
CREATE INDEX idx_runs_status    ON agent_runs(status);
CREATE INDEX idx_runs_role      ON agent_runs(role);
CREATE INDEX idx_runs_canonical ON agent_runs(canonical_key);
CREATE UNIQUE INDEX idx_runs_display ON agent_runs(display_name);
```

### 7.5 Lo que NO Implementar

> **EXCLUSIONES EXPLICITAS** — Los siguientes componentes se excluyen por ser over-engineering para el caso de uso de tmux_fork:

- **Ed25519 device identity**: No hay trust boundary entre agentes locales.
- **PostgreSQL**: SQLite es suficiente y apropiado para CLI local.
- **3-tier auth**: Solo local trust. JWT solo si se integra con Paperclip.
- **6-component adapter subsystem**: Simplificar a `invoke(resultado)` directo.
- **WebSocket/SSE push**: tmux-live ya maneja observabilidad.
- **Drizzle ORM**: Raw SQL es mas simple y sin coupling.
- **Log storage pluggable**: Archivos en `/tmp` son suficientes.

---

## 8. Plan de Implementacion Sugerido

| Fase | Componente | Dependencias | Esfuerzo | Valor |
|------|------------|-------------|----------|-------|
| 1 | Agent identity format (`agent:{role}:{hex8}`) | Ninguna | 1-2h | Fundacional |
| 2 | `parent_launch_id` en AgentLaunch | Fase 1 | 2-3h | Arbol de delegacion |
| 3 | SQLite schema para `agent_runs` | Fase 2 | 3-4h | Persistencia |
| 4 | Delegation tree query API (parent-child) | Fase 3 | 2-3h | Post-mortem debugging |
| 5 | Token/cost tracking por run | Fase 3 | 2-3h | Budget control |
| 6 | `runtimeStatePatch` (session resume) | Fase 5 | 4-6h | Reanudabilidad |

---

## 9. Riesgos y Mitigaciones

| Riesgo | Prob. | Impacto | Mitigacion |
|--------|-------|---------|------------|
| Migracion de AgentLaunch rompe backward compat | Media | Alto | Nueva tabla `agent_runs` con migration. AgentLaunch existente sin cambios. Dual-write durante transicion. |
| Display name colision (role + hex8 duplicado) | Baja | Bajo | hex8 son primeros 8 chars de UUID4. Colision: 1 en 4 billion. Unique index como safety net. |
| SQLite write contention bajo alta concurrencia | Media | Medio | Adoptar patron Hermes: WAL mode + jitter retry (20-150ms, 15 att). PASSIVE checkpoint cada 50 writes. |
| Scope creep hacia plataforma completa | Alta | Alto | Principio de exclusion explicita. No implementar auth tiers, Ed25519, o adapter protocol completo. |
| TaskExecute roto bloquea delegacion nativa | Alta | Critico | Workaround: bash background + `pi --mode json`. Monitorear fix en `@tintinweb/pi-subagents`. |

---

## 10. Conclusiones

El analisis de Hermes y OpenClaw/Paperclip revela dos enfoques complementarios al problema de identidad de agentes. Hermes demuestra que un modelo de sesion bien implementado (con lineage, compression, y title inheritance) puede funcionar robustamente con SQLite y un schema minimalista. OpenClaw demuestra que la jerarquia agent-run-task con session keys aisladas es la estructura correcta para orquestacion multi-agente.

Para tmux_fork, la respuesta no es adoptar uno u otro completamente, sino tomar selectivamente lo mejor de cada uno:

- **De Hermes**: Session lineage, title management, SQLite WAL con jitter retry, token tracking granular.
- **De OpenClaw**: Hierarchical session keys, `runtimeStatePatch`, agent-run-task structure, unique index por tarea.
- **De tmux_fork actual**: Reutilizar AgentLaunch (8-state FSM, `canonical_key` dedup, lease expiry) como base.

La implementacion se puede realizar incrementalmente en 6 fases, cada una agregando valor independiente. El principio clave es mantener la simplicidad: SQLite, sin crypto, sin ORM, sin protocolo de adapter completo. El orquestador debe seguir siendo un CLI liviano que corre en developer laptops sin dependencias externas.

---

## A. Apéndice: Referencia de Schema

### A.1 Hermes Schema v8 (SQLite)

```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    user_id TEXT,
    model TEXT,
    model_config TEXT,
    system_prompt TEXT,
    parent_session_id TEXT REFERENCES sessions(id),
    started_at REAL NOT NULL,
    ended_at REAL,
    end_reason TEXT,
    message_count INTEGER DEFAULT 0,
    tool_call_count INTEGER DEFAULT 0,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cache_read_tokens INTEGER DEFAULT 0,
    cache_write_tokens INTEGER DEFAULT 0,
    reasoning_tokens INTEGER DEFAULT 0,
    billing_provider TEXT,
    billing_base_url TEXT,
    billing_mode TEXT,
    estimated_cost_usd REAL,
    actual_cost_usd REAL,
    cost_status TEXT,
    cost_source TEXT,
    pricing_version TEXT,
    title TEXT,
    api_call_count INTEGER DEFAULT 0
);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    role TEXT NOT NULL,
    content TEXT,
    tool_call_id TEXT,
    tool_calls TEXT,
    tool_name TEXT,
    timestamp REAL NOT NULL,
    token_count INTEGER,
    finish_reason TEXT,
    reasoning TEXT,
    reasoning_content TEXT,
    reasoning_details TEXT,
    codex_reasoning_items TEXT
);

-- FTS5 virtual table
CREATE VIRTUAL TABLE messages_fts USING fts5(
    content, content=messages, content_rowid=id
);

-- Indexes
CREATE UNIQUE INDEX idx_sessions_title_unique
    ON sessions(title) WHERE title IS NOT NULL;
CREATE INDEX idx_sessions_source ON sessions(source);
CREATE INDEX idx_sessions_parent ON sessions(parent_session_id);
CREATE INDEX idx_sessions_started ON sessions(started_at DESC);
CREATE INDEX idx_messages_session ON messages(session_id, timestamp);
```

### A.2 OpenClaw/Paperclip Schema (PostgreSQL/Drizzle)

```typescript
// agent_runtime_state
export const agentRuntimeState = pgTable("agent_runtime_state", {
    agentId:       uuid("agent_id").primaryKey(),
    companyId:     uuid("company_id").notNull(),
    adapterType:   text("adapter_type").notNull(),
    sessionId:     text("session_id"),
    stateJson:     jsonb("state_json")
                       .notNull().default({}),
    lastRunId:     uuid("last_run_id"),
    lastRunStatus: text("last_run_status"),
    totalInputTokens:  bigint("total_input_tokens").default(0),
    totalOutputTokens: bigint("total_output_tokens").default(0),
    totalCachedInputTokens: bigint("total_cached_input_tokens").default(0),
    totalCostCents:    bigint("total_cost_cents").default(0),
    lastError:     text("last_error"),
    createdAt:     timestamp("created_at").defaultNow(),
    updatedAt:     timestamp("updated_at").defaultNow(),
});

// agent_task_sessions
export const agentTaskSessions = pgTable("agent_task_sessions", {
    id:                 uuid("id").primaryKey().defaultRandom(),
    companyId:          uuid("company_id").notNull(),
    agentId:            uuid("agent_id").notNull(),
    adapterType:        text("adapter_type").notNull(),
    taskKey:            text("task_key").notNull(),
    sessionParamsJson:  jsonb("session_params_json"),
    sessionDisplayId:   text("session_display_id"),
    lastRunId:          uuid("last_run_id"),
    lastError:          text("last_error"),
    createdAt:          timestamp("created_at").defaultNow(),
    updatedAt:          timestamp("updated_at").defaultNow(),
}, (table) => ({
    companyAgentTaskUniqueIdx: uniqueIndex(
        "agent_task_sessions_company_agent_adapter_task_uniq"
    ).on(
        table.companyId, table.agentId,
        table.adapterType, table.taskKey,
    ),
}));
```

### A.3 tmux_fork Schema Propuesto (SQLite)

```sql
CREATE TABLE agent_runs (
    launch_id           TEXT PRIMARY KEY,
    canonical_key       TEXT NOT NULL,
    display_name        TEXT NOT NULL,
    role                TEXT NOT NULL,
    model               TEXT,
    surface             TEXT NOT NULL,
    owner_type          TEXT NOT NULL,
    owner_id            TEXT NOT NULL,
    parent_launch_id    TEXT REFERENCES agent_runs(launch_id),
    status              TEXT NOT NULL DEFAULT 'RESERVED',
    backend             TEXT,
    tmux_session        TEXT,
    tmux_pane_id        TEXT,
    prompt_path         TEXT,
    output_artifact     TEXT,
    prompt_digest       TEXT,
    request_fingerprint TEXT,
    token_input         INTEGER DEFAULT 0,
    token_output        INTEGER DEFAULT 0,
    token_cache         INTEGER DEFAULT 0,
    estimated_cost      REAL DEFAULT 0.0,
    created_at          INTEGER NOT NULL,
    started_at          INTEGER,
    completed_at        INTEGER,
    ended_at            INTEGER,
    lease_expires_at    INTEGER,
    last_error          TEXT,
    quarantine_reason   TEXT
);

CREATE INDEX idx_runs_parent    ON agent_runs(parent_launch_id);
CREATE INDEX idx_runs_status    ON agent_runs(status);
CREATE INDEX idx_runs_role      ON agent_runs(role);
CREATE INDEX idx_runs_canonical ON agent_runs(canonical_key);
CREATE UNIQUE INDEX idx_runs_display ON agent_runs(display_name);
```
