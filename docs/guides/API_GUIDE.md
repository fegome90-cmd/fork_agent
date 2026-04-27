# fork_agent - Guía de API para Integración Externa

Guía rápida para usar la API de fork_agent desde otro repositorio.

## Configuración Inicial

### 1. Variables de Entorno

En el repo donde usarás la API, crea `.env`:

```bash
# API Configuration
API_KEY=tu-api-key-aqui
API_HOST=127.0.0.1  # o IP del servidor
API_PORT=8080

# Optional: si corres la API localmente
FORK_API_URL=http://127.0.0.1:8080
```

### 2. Obtener API Key

La API key está en `.env` del proyecto fork_agent:

```bash
# En tmux_fork/
cat .env | grep API_KEY
# API_KEY=559f4341b1277fe62ca2bab328370959c6f622e7d1dd1a10a80160f031ac7897
```

## Iniciar la API

### Desde el Proyecto fork_agent

```bash
# Opción 1: Usando el CLI
cd /Users/felipe_gonzalez/Developer/tmux_fork
source .venv/bin/activate
fork-api

# Opción 2: Con uvicorn directo
uv run uvicorn src.interfaces.api.main:app --host 127.0.0.1 --port 8080

# Opción 3: Con PM2 (producción)
pm2 start ecosystem.config.cjs
```

### Verificar que está corriendo

```bash
curl http://127.0.0.1:8080/
# {"message":"Fork Agent API","version":"1.0.0","docs":"/docs"}
```

## Autenticación

Todas las requests requieren header `X-API-Key`:

```bash
curl -H "X-API-Key: tu-api-key" http://127.0.0.1:8080/api/v1/health
```

## Endpoints Principales

### Health Check

```bash
GET /api/v1/health
```

```bash
curl -H "X-API-Key: $API_KEY" http://127.0.0.1:8080/api/v1/health
```

### Agentes - Crear Sesión

```bash
POST /api/v1/agents/sessions
```

**Body:**
```json
{
  "agent_type": "opencode",  // o "pi"
  "task": "Implementar autenticación OAuth2",
  "tmux": true,              // Crear sesión tmux
  "model": "glm-5-free",     // Opcional: modelo a usar
  "hooks": true              // Ejecutar hooks de inicialización
}
```

**Ejemplo:**
```bash
curl -X POST http://127.0.0.1:8080/api/v1/agents/sessions \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "opencode",
    "task": "Refactorizar módulo de pagos",
    "tmux": true
  }'
```

**Response:**
```json
{
  "data": {
    "session_id": "fork-opencode-a1b2c3d4e5f6",
    "agent_type": "opencode",
    "status": "running",
    "started_at": "2026-03-01T15:30:00",
    "tmux_session": "fork-opencode-a1b2c3",
    "hooks": []
  }
}
```

### Agentes - Listar Sesiones

```bash
GET /api/v1/agents/sessions
```

```bash
curl -H "X-API-Key: $API_KEY" http://127.0.0.1:8080/api/v1/agents/sessions
```

### Agentes - Obtener Sesión

```bash
GET /api/v1/agents/sessions/{session_id}
```

### Agentes - Eliminar Sesión

```bash
DELETE /api/v1/agents/sessions/{session_id}
```

## Memoria

### Guardar Observación

```bash
POST /api/v1/memory
```

```bash
curl -X POST http://127.0.0.1:8080/api/v1/memory \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"content": "Patrón Observer implementado en auth module"}'
```

### Buscar Observaciones

```bash
GET /api/v1/memory/search?q=query
```

```bash
curl -H "X-API-Key: $API_KEY" "http://127.0.0.1:8080/api/v1/memory/search?q=auth"
```

### Query Estructurado (Filtros)

```bash
GET /api/v1/memory/query?agent=id&run=id&event-type=type&since=24h
```

```bash
curl -H "X-API-Key: $API_KEY" "http://127.0.0.1:8080/api/v1/memory/query?run=run-123&event-type=task_completed"
```

### Timeline de Run

```bash
GET /api/v1/memory/timeline/{run_id}
```

```bash
curl -H "X-API-Key: $API_KEY" http://127.0.0.1:8080/api/v1/memory/timeline/run-123
```

### Listar Observaciones

```bash
GET /api/v1/memory
```

## Workflow (outline → execute → verify → ship)

### 1. Crear Plan

```bash
POST /api/v1/workflow/outline
```

```bash
curl -X POST http://127.0.0.1:8080/api/v1/workflow/outline \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"task": "Implementar sistema de caché"}'
```

### 2. Ejecutar Plan

```bash
POST /api/v1/workflow/{plan_id}/execute
```

### 3. Verificar Plan

```bash
POST /api/v1/workflow/{plan_id}/verify
```

### 4. Ship (Deploy)

```bash
POST /api/v1/workflow/{plan_id}/ship
```

```json
{
  "branch": "feature/cache-system",
  "commit_message": "feat: add cache layer"
}
```

### Ver Estado

```bash
GET /api/v1/workflow/{plan_id}/status
```

## CLI Commands (Uso Local)

Si tienes el proyecto instalado:

```bash
# Memoria
memory save "nota importante"
memory search "query"
memory list
memory get <id>
memory delete <id>

# Workflow
memory workflow outline "Tarea a realizar"
memory workflow execute
memory workflow verify
memory workflow ship
memory workflow status

# Scheduling
memory schedule add "echo hello" 60  # cada 60 segundos
memory schedule list
memory schedule show <task_id>
memory schedule cancel <task_id>

# Workspace
memory workspace create <name>
memory workspace list
memory workspace enter <name>
memory workspace detect
```

## tmux Integration

### Listar Sesiones tmux

```bash
tmux ls
```

### Conectarse a Sesión

```bash
tmux attach -t fork-opencode-a1b2c3
```

### Ver Logs de Sesión

```bash
# Capturar output de sesión tmux
tmux capture-pane -t fork-opencode-a1b2c3 -p
```

### Matar Sesión

```bash
tmux kill-session -t fork-opencode-a1b2c3
```

## Backends Disponibles

| Backend | Descripción | Disponibilidad |
|---------|-------------|----------------|
| `opencode` | OpenCode CLI con modelos free | Requiere `opencode` instalado |
| `pi` | Pi Coding Agent | Requiere `pi` instalado |

## Client Library (Python)

### Instalación

```bash
# En tu proyecto
pip install httpx
```

### Cliente Básico

```python
import os
from httpx import Client

class ForkAgentClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8080", api_key: str = None):
        self.base_url = base_url
        self.api_key = api_key or os.getenv("API_KEY")
        self.headers = {"X-API-Key": self.api_key}

    def create_session(self, agent_type: str, task: str, tmux: bool = True) -> dict:
        with Client() as client:
            response = client.post(
                f"{self.base_url}/api/v1/agents/sessions",
                headers=self.headers,
                json={"agent_type": agent_type, "task": task, "tmux": tmux}
            )
            response.raise_for_status()
            return response.json()

    def save_memory(self, content: str) -> dict:
        with Client() as client:
            response = client.post(
                f"{self.base_url}/api/v1/memory",
                headers=self.headers,
                json={"content": content}
            )
            response.raise_for_status()
            return response.json()

    def search_memory(self, query: str) -> list:
        with Client() as client:
            response = client.get(
                f"{self.base_url}/api/v1/memory/search",
                headers=self.headers,
                params={"q": query}
            )
            response.raise_for_status()
            return response.json()["data"]

# Uso
client = ForkAgentClient(api_key="tu-api-key")

# Crear sesión de agente
session = client.create_session("opencode", "Refactorizar auth module", tmux=True)
print(f"Sesión creada: {session['data']['session_id']}")

# Guardar en memoria
client.save_memory("Implementado patrón Repository en users module")

# Buscar en memoria
results = client.search_memory("auth")
```

## Integración desde Otro Repo

### Opción 1: API Remota

```python
# En tu proyecto
from httpx import Client

API_URL = "http://127.0.0.1:8080"  # o IP del servidor
API_KEY = "tu-api-key"

client = Client(base_url=API_URL, headers={"X-API-Key": API_KEY})

# Crear agente
response = client.post("/api/v1/agents/sessions", json={
    "agent_type": "opencode",
    "task": "Implementar feature X",
    "tmux": True
})
session = response.json()
```

### Opción 2: Importar Directamente

```python
# Solo si tienes acceso al código fuente
import sys
sys.path.insert(0, "/Users/felipe_gonzalez/Developer/tmux_fork")

from src.infrastructure.persistence.container import create_container
from src.application.services.memory_service import MemoryService

# Usar MemoryService directamente
container = create_container()
memory: MemoryService = container.memory_service()
memory.save("Nota importante")
```

### Opción 3: CLI via Subprocess

```python
import subprocess

def run_memory_command(cmd: str, *args: str) -> str:
    result = subprocess.run(
        ["memory", cmd, *args],
        cwd="/Users/felipe_gonzalez/Developer/tmux_fork",
        capture_output=True,
        text=True
    )
    return result.stdout

# Uso
output = run_memory_command("save", "Nota desde otro repo")
print(output)
```

## Troubleshooting

### Error: API key not configured

```bash
# Verificar que API_KEY esté en .env
cat .env | grep API_KEY
```

### Error: Agent backend not available

```bash
# Verificar instalación del backend
which opencode  # o which pi
```

### Error: tmux session failed

```bash
# Verificar tmux instalado
which tmux

# Listar sesiones
tmux ls
```

### Ver Logs de la API

```bash
# Si usas PM2
pm2 logs fork-api

# Si usas uvicorn directo, ver stdout
```

## Documentación Interactiva

La API tiene documentación Swagger UI:

```
http://127.0.0.1:8080/docs
```

## Resumen de Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Info de la API |
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/agents/sessions` | Crear sesión de agente |
| GET | `/api/v1/agents/sessions` | Listar sesiones |
| GET | `/api/v1/agents/sessions/{id}` | Obtener sesión |
| DELETE | `/api/v1/agents/sessions/{id}` | Eliminar sesión |
| POST | `/api/v1/memory` | Guardar observación |
| GET | `/api/v1/memory` | Listar observaciones |
| GET | `/api/v1/memory/search` | Buscar observaciones |
| GET | `/api/v1/memory/{id}` | Obtener observación |
| DELETE | `/api/v1/memory/{id}` | Eliminar observación |
| POST | `/api/v1/workflow/outline` | Crear plan |
| POST | `/api/v1/workflow/{id}/execute` | Ejecutar plan |
| POST | `/api/v1/workflow/{id}/verify` | Verificar plan |
| POST | `/api/v1/workflow/{id}/ship` | Ship plan |
| GET | `/api/v1/workflow/{id}/status` | Estado del plan |
