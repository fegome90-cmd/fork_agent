# Plan: Fixes Pendientes del Branch Review

**Fecha**: 2026-02-27
**Estado**: ⏸️ Esperando confirmación
**Estimación corregida**: LOW–MEDIUM (45 min)

---

## 1. Restatement de Requerimientos

**Objetivo**: Resolver findings P1 identificados por branch-review para alcanzar veredicto PASS, con guardrails de senior.

**Findings a resolver**:

| ID | Código | Ubicación | Descripción |
|----|--------|-----------|-------------|
| P1-1 | SIM102 | `memory_hook.py:97` | Nested if statements |
| P1-2 | B904 | `integrations.py` (6x) | `raise HTTPException` sin `from` clause |
| P1-3 | ARG002 | `task_decomposer.py:88,129` | Argumento `goal` sin uso |
| P1-4 | ARG002 | `pi_backend.py:25` | Argumento `model` sin uso |

**Out of scope**:
- 69 ruff issues P2 (SIM, ARG, B, I) - code quality, no blocking
- 2 E2E tests fallando (requieren tmux runtime) → skip determinista

---

## 2. Supuestos y Decisiones Tomadas

### Decisiones Basadas en Guardrails Senior

| Pregunta | Decisión | Rationale |
|----------|----------|-----------|
| **ARG002**: ¿Prefijar o eliminar? | **Prefijar con `_`** | Más seguro, menos riesgo de romper interfaces. En segunda pasada se evalúa eliminación. |
| **B904**: ¿`from e` o `from None`? | **`from None`** | Código ya loggea el error original. Es borde de API, no filtrar tracebacks. |
| **E2E tests**: ¿Skip cuando tmux no disponible? | **Sí, con gate determinista** | `@pytest.mark.requires_tmux` + check `TMUX` env y `shutil.which("tmux")` |

### Supuestos
1. Los fixes son backwards-compatible (no cambian API pública)
2. No se requiere migración de DB
3. Los tests existentes cubren las áreas afectadas
4. El logging actual en `integrations.py` es suficiente para diagnósticos

---

## 3. Fases de Implementación

### FASE 1: SIM102 - Flatten nested conditionals (5 min)

**Archivo**: `src/application/services/messaging/memory_hook.py:97-105`

**Cambio**:
```python
# Before
if self._config.rate_limit_enabled:
    rate_key = self._build_rate_key(msg, context)
    if not self._rate_limiter.is_allowed(rate_key):
        logger.debug("Rate limited: %s", rate_key)
        return False

# After
if self._config.rate_limit_enabled and not self._rate_limiter.is_allowed(
    self._build_rate_key(msg, context)
):
    logger.debug("Rate limited: %s", self._build_rate_key(msg, context))
    return False
```

**Riesgo**: LOW - Early return pattern se mantiene

**DoD**:
- [ ] `ruff check src/application/services/messaging/memory_hook.py --select=SIM102` pasa
- [ ] `pytest tests/unit/application/services/messaging/test_memory_hook.py` pasa (14 tests)

---

### FASE 2: B904 - Add `from None` en integrations.py (10 min)

**Archivo**: `src/interfaces/api/routes/integrations.py`

**Ubicaciones**: Líneas 41, 59, 78, 120, 126, 151 (6 instances)

**Patrón actual**:
```python
except Exception as e:
    logger.error(f"Failed to ...: {e}")  # ← YA hay logging
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"... API unavailable: {e}",
    )
```

**Patrón objetivo**:
```python
except Exception as e:
    logger.error(f"Failed to ...: {e}")
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"... API unavailable: {e}",
    ) from None  # ← Oculta traceback, logging ya captura contexto
```

**Rationale**:
- Borde de API → no filtrar tracebacks internos
- Logging ya captura error original → no perdemos diagnóstico
- `from None` es más limpio para el usuario

**Riesgo**: LOW - Traceback se preserva en logs

**DoD**:
- [ ] `ruff check src/interfaces/api/routes/integrations.py --select=B904` pasa
- [ ] Verificar que logging funciona (ejemplo de log/trace cuando ocurre error)

---

### FASE 3: ARG002 - Prefijar argumentos sin uso (10 min)

#### 3.1 task_decomposer.py (2 instances)

**Archivo**: `src/application/services/workflow/task_decomposer.py`

**Línea 88**:
```python
# Before
def _create_foundation_tasks(self, goal: Goal) -> list[Task]:

# After
def _create_foundation_tasks(self, _goal: Goal) -> list[Task]:
```

**Línea 129**:
```python
# Before
def _create_integration_tasks(self, goal: Goal, core_tasks: list[Task]) -> list[Task]:

# After
def _create_integration_tasks(self, _goal: Goal, core_tasks: list[Task]) -> list[Task]:
```

**Rationale**: Métodos privados, pero se pasa `goal` consistentemente desde `decompose()`. Prefijar es más seguro.

#### 3.2 pi_backend.py (1 instance)

**Archivo**: `src/infrastructure/agent_backends/pi_backend.py:25`

```python
# Before
def get_launch_command(self, task: str, model: str) -> str:

# After
def get_launch_command(self, task: str, _model: str) -> str:
```

**Rationale**: Firma es parte de contrato de backend (API compatibility). NO eliminar, solo prefijar.

**Riesgo**: LOW - No cambia firma, solo suprime warning

**DoD**:
- [ ] `ruff check src/application/services/workflow/task_decomposer.py src/infrastructure/agent_backends/pi_backend.py --select=ARG002` pasa
- [ ] `pytest tests/unit/application/services/workflow/test_executor.py tests/unit/infrastructure/agent_backends/test_backends.py` pasa

---

### FASE 4: E2E tests - Skip determinista (15 min)

**Archivo**: `tests/integration/test_messaging_e2e.py`

**Tests afectados**:
1. `TestMessageSendAndCapture::test_send_message_to_session`
2. `TestMessageBroadcast::test_broadcast_includes_created_sessions`

**Cambio**:

1. Agregar fixture/condición en `tests/conftest.py`:
```python
import shutil
import pytest

def tmux_available() -> bool:
    """Check if tmux is available."""
    import os
    return "TMUX" in os.environ or shutil.which("tmux") is not None

@pytest.fixture
def skip_if_no_tmux():
    """Skip test if tmux is not available."""
    if not tmux_available():
        pytest.skip("tmux not available")
```

2. Marcar tests que requieren tmux:
```python
@pytest.mark.integration
class TestMessageSendAndCapture:
    """Tests for sending messages and capturing them."""

    def test_send_message_to_session(self, tmux_cleanup, temp_db, skip_if_no_tmux) -> None:
        """Should send a message to a tmux session and store it."""
        # ... existing code ...
```

**Rationale**:
- Tests de integración E2E que requieren tmux real
- Skip determinista basado en `TMUX` env + `shutil.which("tmux")`
- NO son tests de policy que puedan ser unitarios

**Riesgo**: LOW - Solo afecta ejecución de tests, no código de producción

**DoD**:
- [ ] Tests se skippean automáticamente si tmux no está disponible
- [ ] Tests pasan si tmux está disponible
- [ ] `pytest -m "not integration"` pasa sin tmux

---

### FASE 5: Verificación final (5 min)

**Comandos**:
```bash
# 1. Lint específico para códigos P1
uv run ruff check src/ tests/ --select=SIM102,B904,ARG002

# 2. Tests unitarios afectados
uv run pytest tests/unit/application/services/messaging/test_memory_hook.py -v
uv run pytest tests/unit/application/services/workflow/test_executor.py -v
uv run pytest tests/unit/infrastructure/agent_backends/test_backends.py -v

# 3. Full suite (sin E2E que requieren tmux)
uv run pytest tests/ -q --tb=no -m "not integration"
```

**DoD final**:
- [ ] `ruff check --select=SIM102,B904,ARG002` = 0 findings
- [ ] `pytest` pasa (unit + integration con skips correctos)
- [ ] Ejemplo de log/trace cuando ocurre error en integrations.py (para B904)

---

## 4. Archivos Candidatos a Modificar

| Archivo | Cambio | Riesgo |
|---------|--------|--------|
| `src/application/services/messaging/memory_hook.py` | Flatten nested if | LOW |
| `src/interfaces/api/routes/integrations.py` | Add `from None` (6x) | LOW |
| `src/application/services/workflow/task_decomposer.py` | Prefix `_goal` (2x) | LOW |
| `src/infrastructure/agent_backends/pi_backend.py` | Prefix `_model` | LOW |
| `tests/conftest.py` | Add `skip_if_no_tmux` fixture | LOW |
| `tests/integration/test_messaging_e2e.py` | Use `skip_if_no_tmux` | LOW |

---

## 5. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Regresión en rate limiting | LOW | MEDIUM | Ejecutar 14 tests de memory_hook |
| Perder traceback diagnóstico | LOW | MEDIUM | Logging ya captura error original |
| Interface break en backends | LOW | LOW | Prefijar `_` mantiene signature |
| Skip mask real failures | LOW | HIGH | Gate determinista + mark explícito |

---

## 6. Estrategia de Pruebas

### Tests Existentes (no requieren cambios)
- `tests/unit/application/services/messaging/test_memory_hook.py` (14 tests)
- `tests/unit/application/services/workflow/test_executor.py` (14 tests)
- `tests/unit/infrastructure/agent_backends/test_backends.py` (6 tests)

### Tests Modificados
- `tests/integration/test_messaging_e2e.py` (2 tests → skip determinista)

### Verificación Manual
```bash
# 1. Lint específico
uv run ruff check src/ --select=SIM102,B904,ARG002

# 2. Tests unitarios afectados
uv run pytest tests/unit/application/services/messaging/ -v
uv run pytest tests/unit/application/services/workflow/ -v
uv run pytest tests/unit/infrastructure/agent_backends/ -v

# 3. Full suite sin E2E
uv run pytest tests/ -q --tb=no -m "not integration"
```

---

## 7. Estimación de Complejidad

**Overall: LOW–MEDIUM** (corregido de "LOW")

| Fase | Tiempo | Complejidad | Riesgo Real |
|------|--------|-------------|-------------|
| FASE 1: SIM102 | 5 min | LOW | Bajo - early return se mantiene |
| FASE 2: B904 | 10 min | LOW–MEDIUM | Medio - no perder trazabilidad |
| FASE 3: ARG002 | 10 min | LOW | Bajo - solo prefijar |
| FASE 4: E2E skip | 15 min | LOW–MEDIUM | Medio - no esconder fallos reales |
| FASE 5: Verify | 5 min | LOW | Bajo |
| **Total** | **45 min** | **LOW–MEDIUM** | |

**Por qué LOW–MEDIUM y no LOW**:
- La parte peligrosa es el alcance, no el cambio mecánico
- B904: riesgo de perder trazabilidad si no hay logging
- E2E skip: riesgo de mask failures reales si el gate está mal

---

## 8. DoD Consolidado

- [ ] `ruff check src/ tests/ --select=SIM102,B904,ARG002` = 0 findings
- [ ] `pytest tests/unit/` pasa (100%)
- [ ] `pytest tests/integration/` pasa con skips correctos cuando tmux no disponible
- [ ] Ejemplo de log cuando ocurre error en integrations.py (verificar B904 no rompe diagnóstico)
- [ ] Commit atómico por fase (opcional) o commit único con mensaje descriptivo

---

## 9. Preguntas Resueltas

| # | Pregunta | Decisión |
|---|----------|----------|
| 1 | ARG002: ¿Prefijar o eliminar? | **Prefijar `_`** - más seguro |
| 2 | B904: ¿`from e` o `from None`? | **`from None`** - borde de API con logging |
| 3 | E2E tests: ¿Skip cuando tmux no disponible? | **Sí, con gate determinista** |

---

**Estado**: ⏸️ Esperando confirmación para ejecutar

**Próximo paso**: ¿Apruebas el plan para ejecución?
