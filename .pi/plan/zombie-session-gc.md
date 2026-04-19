# Plan: zombie-session-gc (v2 — post-audit)

## Auditoría aplicada
- patch-dedup-1 ✅ Secuencia de startup explícita (restore → sweep → loop)
- patch-dedup-2 ✅ Logs estructurados + respuesta coherente en gc/status antes del primer run
- patch-dedup-3 ✗ Rechazado (falso positivo bun — proyecto usa uv/mypy/ruff)
- patch-dedup-4 ✅ 1 commit atómico por fase (A, B, C, tests)
- patch-dedup-5 ✅ Cobertura mínima confirmada (4 unit + 2 integration)

## 1. Contexto

220 sesiones `fork-opencode-*` zombie observadas en tmux.
Raíz: `POST /sessions` crea sesión tmux pero no existe GC automático.
Infraestructura necesaria **ya existe**: `cleanup_orphans()`, `reconcile_sessions()`,
`_load_session_from_disk()`, `SessionStore` con persistencia en `.claude/api-sessions/`.
Solo falta el wiring: loop periódico + restore al startup + endpoint de estado.

## 2. Secuencia de startup (patch-dedup-1)

Orden explícito e invariante dentro del `lifespan`:

```
lifespan startup:
  1. _restore_sessions_from_disk()    ← sincrono, reconstruye SessionStore desde disco
  2. _run_gc(min_age=0)              ← sweep histórico sincrono, única vez al arrancar
  3. asyncio.create_task(_gc_loop()) ← loop periódico con sleep inicial de GC_INTERVAL
```

Garantía: el primer GC cycle nunca ve sesiones "huérfanas" que en realidad
están en disco pero no en memoria.

## 3. Fases

### Fase A — `_restore_sessions_from_disk` + secuencia lifespan

**Archivo:** `src/interfaces/api/routes/agents.py`

```python
def _restore_sessions_from_disk() -> int:
    """Load all persisted sessions into SessionStore at startup."""
    if not _sessions_dir.exists():
        return 0
    count = 0
    for f in _sessions_dir.glob("*.json"):
        session = _load_session_from_disk(f.stem)
        if session and not SessionStore.exists(session.session_id):
            SessionStore.set(session.session_id, session)
            count += 1
    logger.info("gc: sessions restored from disk", extra={"count": count})
    return count
```

**Archivo:** `src/interfaces/api/main.py`

```python
GC_INTERVAL_SECONDS = int(os.getenv("GC_INTERVAL_SECONDS", "60"))
GC_MIN_AGE_SECONDS  = int(os.getenv("GC_MIN_AGE_SECONDS",  "300"))

async def lifespan(_app):
    # 1. Restore persisted sessions before any GC
    from src.interfaces.api.routes.agents import _restore_sessions_from_disk
    restored = _restore_sessions_from_disk()
    logger.info(f"Startup: restored {restored} sessions from disk")

    # 2. Startup sweep (no min_age — cleans historical accumulation)
    _run_gc(min_age_seconds=0)

    # 3. Start periodic GC loop
    gc_task = asyncio.create_task(_gc_loop())

    yield  # API serving

    gc_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await gc_task
```

### Fase B — GC loop + `_run_gc` con logs estructurados

**Archivo:** `src/interfaces/api/main.py`

```python
async def _gc_loop() -> None:
    while True:
        await asyncio.sleep(GC_INTERVAL_SECONDS)
        _run_gc(min_age_seconds=GC_MIN_AGE_SECONDS)

def _run_gc(min_age_seconds: int = GC_MIN_AGE_SECONDS) -> CleanupResult:
    t0 = time.monotonic()
    manager = get_agent_manager()
    result = manager.cleanup_orphans(dry_run=False, min_age_seconds=min_age_seconds)
    duration_ms = int((time.monotonic() - t0) * 1000)

    _update_gc_state(result, duration_ms)  # para el endpoint

    if result.cleaned_sessions:
        logger.warning(
            "gc: zombie sessions cleaned",
            extra={"count": len(result.cleaned_sessions),
                   "sessions": result.cleaned_sessions,
                   "duration_ms": duration_ms},
        )
    if result.failed_sessions:
        logger.error(
            "gc: failed to clean sessions",
            extra={"count": len(result.failed_sessions),
                   "sessions": result.failed_sessions,
                   "duration_ms": duration_ms},
        )
    return result
```

### Fase C — Endpoint `GET /sessions/gc/status`

**Archivo:** `src/interfaces/api/routes/agents.py`

Estado mutable protegido con Lock:

```python
@dataclass
class _GcState:
    last_run_at: datetime | None = None
    cleaned_count: int = 0
    failed_count: int = 0
    last_duration_ms: int = 0

_gc_state = _GcState()
_gc_state_lock = Lock()
```

Endpoint:

```python
GET /sessions/gc/status
→ 200 {
    "last_run_at": "2026-03-02T10:00:00" | null,
    "cleaned_count": 5,
    "failed_count": 0,
    "last_duration_ms": 123,
    "gc_interval_seconds": 60,
    "gc_min_age_seconds": 300,
    "status": "never_run" | "ok" | "partial_failure" | "all_failed"
  }
```

`status="never_run"` si `last_run_at is None` — respuesta coherente antes del primer cycle
(patch-dedup-2: no `null` crudo).

## 4. Archivos a modificar

| Archivo | Cambio |
|---------|--------|
| `src/interfaces/api/main.py` | lifespan con secuencia explícita + `_gc_loop` + `_run_gc` |
| `src/interfaces/api/routes/agents.py` | `_restore_sessions_from_disk` + `_GcState` + endpoint |

## 5. Commits atómicos (patch-dedup-4)

1. `feat(gc): restore sessions from disk at startup`
2. `feat(gc): add periodic zombie session GC loop`
3. `feat(gc): add GET /sessions/gc/status endpoint`
4. `test(gc): unit and integration tests for zombie GC`

## 6. Tests — cobertura mínima (patch-dedup-5)

### Unit (sin tmux real)
- `test_restore_sessions_from_disk_populates_store` — JSON en tmp_path → SessionStore
- `test_restore_skips_invalid_json` — archivo corrupto → no crash, 0 restored
- `test_run_gc_logs_cleaned` — mock cleanup_orphans retorna cleaned → logger.warning llamado
- `test_run_gc_logs_failed` — mock retorna failed → logger.error llamado
- `test_gc_status_never_run` — GET /sessions/gc/status → status="never_run"
- `test_gc_status_after_run` — después de _run_gc → status="ok", cleaned_count correcto

### Integration (con tmux real — skipif no tmux)
- `test_startup_sweep_kills_orphan` — crear sesión fork-* sin registro, arrancar GC → killed
- `test_gc_respects_min_age` — sesión joven no debe ser eliminada

## 7. Quality gates

- `uv run mypy src/interfaces/api/main.py src/interfaces/api/routes/agents.py` PASS
- `uv run ruff check` PASS
- `pytest tests/unit/interfaces/api/test_gc.py` PASS
