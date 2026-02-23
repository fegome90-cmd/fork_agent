# PM2 Fork Agent API Specification

## Overview

API REST para gestionar procesos fork_agent via PM2. Expone control de procesos, monitoreo y gestión remota del sistema de orquestación de agentes.

**Versión:** 1.0.0  
**Base URL:** `http://localhost:8080/api/v1`  
**Authentication:** API Key (header `X-API-Key`)

---

## Endpoints

### 1. Procesos

#### Listar procesos

```http
GET /processes
```

**Response 200:**
```json
{
  "data": [
    {
      "name": "fork-agent-main",
      "pm_id": 0,
      "pid": 1234,
      "status": "online",
      "cpu": 2.5,
      "memory": "128MB",
      "uptime": "2026-02-22T10:00:00Z",
      "restarts": 0,
      "health": "healthy"
    }
  ],
  "meta": {
    "total": 1,
    "version": "1.0.0"
  }
}
```

#### Obtener proceso específico

```http
GET /processes/{pm_id}
```

**Response 200:**
```json
{
  "data": {
    "name": "fork-agent-main",
    "pm_id": 0,
    "pid": 1234,
    "status": "online",
    "cpu": 2.5,
    "memory": "128MB",
    "uptime": "2026-02-22T10:00:00Z",
    "restarts": 0,
    "health": "healthy",
    "env": {
      "NODE_ENV": "production"
    }
  }
}
```

#### Iniciar proceso

```http
POST /processes
```

**Body:**
```json
{
  "name": "my-agent",
  "script": "src/interfaces/cli/main.py",
  "args": "workflow outline",
  "cwd": "/Users/felipe_gonzalez/Developer/tmux_fork",
  "env": {
    "FORK_MODE": "agent"
  }
}
```

**Response 201:**
```json
{
  "data": {
    "pm_id": 2,
    "name": "my-agent",
    "status": "launching"
  }
}
```

#### Detener proceso

```http
POST /processes/{pm_id}/stop
```

**Response 200:**
```json
{
  "data": {
    "pm_id": 2,
    "status": "stopped"
  }
}
```

#### Reiniciar proceso

```http
POST /processes/{pm_id}/restart
```

#### Eliminar proceso

```http
DELETE /processes/{pm_id}
```

#### Escalar proceso (cluster)

```http
POST /processes/{pm_id}/scale
```

**Body:**
```json
{
  "instances": 4
}
```

---

### 2. Orquestación de Agentes

#### Iniciar sesión de agente

```http
POST /agents/sessions
```

**Body:**
```json
{
  "agent_type": "claude-code",
  "task": "Implementar autenticación",
  "workspace": "/path/to/workspace",
  "hooks": true,
  "tmux": true
}
```

**Response 201:**
```json
{
  "data": {
    "session_id": "fork-claude-1234567890",
    "tmux_session": "fork-claude-code-1234567890",
    "status": "starting",
    "hooks": [
      {
        "type": "workspace-init",
        "status": "pending"
      }
    ]
  }
}
```

#### Listar sesiones activas

```http
GET /agents/sessions
```

**Response 200:**
```json
{
  "data": [
    {
      "session_id": "fork-claude-1234567890",
      "agent_type": "claude-code",
      "status": "running",
      "started_at": "2026-02-22T10:00:00Z",
      "tmux_session": "fork-claude-code-1234567890"
    }
  ]
}
```

#### Obtener estado de sesión

```http
GET /agents/sessions/{session_id}
```

#### Terminar sesión

```http
DELETE /agents/sessions/{session_id}
```

---

### 3. Workflow

#### Crear plan

```http
POST /workflow/outline
```

**Body:**
```json
{
  "task": "Implementar autenticación JWT",
  "description": "Agregar login y registro con JWT"
}
```

**Response 201:**
```json
{
  "data": {
    "plan_id": "plan-abc123",
    "task": "Implementar autenticación JWT",
    "status": "created",
    "created_at": "2026-02-22T10:00:00Z"
  }
}
```

#### Ejecutar plan

```http
POST /workflow/{plan_id}/execute
```

**Response 200:**
```json
{
  "data": {
    "execute_id": "exec-xyz789",
    "plan_id": "plan-abc123",
    "status": "running",
    "started_at": "2026-02-22T10:05:00Z"
  }
}
```

#### Verificar plan

```http
POST /workflow/{plan_id}/verify
```

**Response 200:**
```json
{
  "data": {
    "verify_id": "verify-123",
    "execute_id": "exec-xyz789",
    "status": "passed",
    "tests": {
      "total": 50,
      "passed": 50,
      "failed": 0
    },
    "coverage": 95.2
  }
}
```

#### Ship (desplegar)

```http
POST /workflow/{plan_id}/ship
```

**Body:**
```json
{
  "branch": "feature/auth",
  "commit_message": "feat: add JWT authentication"
}
```

#### Estado del workflow

```http
GET /workflow/{plan_id}/status
```

---

### 4. Memoria

#### Guardar observación

```http
POST /memory
```

**Body:**
```json
{
  "content": "El usuario prefers dark mode"
}
```

**Response 201:**
```json
{
  "data": {
    "id": "obs-123",
    "content": "El usuario prefers dark mode",
    "created_at": "2026-02-22T10:00:00Z"
  }
}
```

#### Buscar memoria

```http
GET /memory/search?q=theme
```

#### Listar observaciones

```http
GET /memory
```

#### Obtener observación

```http
GET /memory/{id}
```

#### Eliminar observación

```http
DELETE /memory/{id}
```

---

### 5. Sistema

#### Health check

```http
GET /health
```

**Response 200:**
```json
{
  "status": "healthy",
  "pm2": {
    "status": "online",
    "processes": 3
  },
  "version": "1.0.0"
}
```

#### Métricas

```http
GET /metrics
```

**Response 200:**
```json
{
  "cpu": 15.2,
  "memory": "512MB",
  "uptime": 3600,
  "requests_total": 1250,
  "errors_total": 0
}
```

#### Logs

```http
GET /logs
GET /logs/{pm_id}
```

**Query params:**
- `lines`: number (default: 100)
- `stream`: stdout | stderr | combined (default: combined)

---

## Códigos de Error

| Código | Descripción |
|--------|-------------|
| 400 | Bad Request - параметros inválidos |
| 401 | Unauthorized - API key inválida |
| 404 | Not Found - recurso no existe |
| 422 | Unprocessable Entity - validación fallida |
| 500 | Internal Server Error |
| 503 | Service Unavailable - PM2 no disponible |

### Formato de error

```json
{
  "error": {
    "code": "PROCESS_NOT_FOUND",
    "message": "Process with pm_id 5 not found",
    "details": {}
  }
}
```

---

## Autenticación

```http
Header: X-API-Key: sk_fork_agent_xxxxx
```

---

## Rate Limiting

- **Limit:** 100 requests/minute
- **Header:** `X-RateLimit-Remaining`

---

## Webhooks

Eventos disponibles:
- `process.started`
- `process.stopped`
- `process.restarted`
- `process.crashed`
- `agent.session.started`
- `agent.session.ended`
- `workflow.plan.created`
- `workflow.plan.completed`

### Configuración

```http
POST /webhooks
```

**Body:**
```json
{
  "url": "https://your-server.com/webhook",
  "events": ["process.started", "process.stopped"],
  "secret": "whsec_xxxxx"
}
```

---

## Deployment

### Docker

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install pm2@latest -g
COPY . .
EXPOSE 8080
CMD ["pm2-runtime", "start", "ecosystem.config.js"]
```

### Environment Variables

| Variable | Descripción | Default |
|----------|-------------|---------|
| PORT | Puerto del API | 8080 |
| API_KEY | Clave de API | - |
| PM2_HOST | Host de PM2 | localhost |
| PM2_PORT | Puerto de PM2 | 9615 |
| DATABASE_URL | SQLite path | ./data/memory.db |

---

## Cliente Python (Fork Agent CLI)

```python
from fork_agent_api import ForkAgentAPI

api = ForkAgentAPI(
    base_url="http://localhost:8080",
    api_key="sk_fork_agent_xxxxx"
)

# Listar procesos
processes = api.processes.list()

# Iniciar agente
session = api.agents.sessions.create(
    agent_type="claude-code",
    task="Fix bug #123"
)

# Workflow
plan = api.workflow.outline("Nueva feature")
api.workflow.execute(plan["id"])
```

---

## Postman Collection

Importar colección de Postman para testing:

```json
{
  "info": {
    "name": "Fork Agent PM2 API",
    "version": "1.0.0"
  },
  "variable": [
    {"key": "baseUrl", "value": "http://localhost:8080/api/v1"},
    {"key": "apiKey", "value": "sk_fork_agent_xxxxx"}
  ]
}
```
