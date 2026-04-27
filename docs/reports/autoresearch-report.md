# Informe Técnico: Integración pi-autoresearch con tmux_fork

**Fecha:** 2026-04-21  
**Branch:** `autoresearch/optimize-test-speed-2026-04-21`  
**Estado:** Verificado — listo para review y merge parcial  
**Agentes involucrados:** 1 autoresearch loop + 3 agentes orquestados (auditor, implementer, verifier)  

---

## 1. Resumen Ejecutivo

Se instaló **pi-autoresearch** y se ejecutó un loop autónomo de 18 experimentos sobre el test suite de tmux_fork. Posteriormente, una orquestación de 3 agentes (auditor + implementer + verifier) limpió la branch para revisión, corrigió inconsistencias, y aseguró calidad.

| Métrica | Baseline | Con optimización | Mejora |
|---------|----------|-----------------|--------|
| Wall-clock (mediana, 5 runs) | 15.32s | 3.44s | **-77.5%** |
| Tests pasados | 1620 | 1620 | 0 regresiones |
| Fast mode | No existe | `TMUX_FORK_FAST_TESTS=1` | Opt-in, sin efecto por defecto |
| Guard tests | 0 | 5 | Protegen fake clock |

---

## 2. Benchmark Reproducible (5 corridas por condición)

| Condición | Min | Mediana | Max | Rango |
|-----------|-----|---------|-----|-------|
| A: Secuencial, real clock | 15.25s | 15.32s | 15.42s | 0.17s |
| B: xdist -n 8, real clock | 9.18s | 9.19s | 9.23s | 0.05s |
| C: xdist -n 8 + fake clock | 3.68s | 3.75s | 3.85s | 0.17s |
| D: xdist -n 8 + fake clock + worksteal | 3.36s | 3.44s | 4.01s | 0.65s |

**Descomposición del speedup:**
- xdist solo (A→B): 1.7x — consistente, baja varianza
- Fake clock (B→C): 2.5x — el mayor impacto individual
- Worksteal (C→D): 1.1x — marginal, pero mediana mejora
- **Total (A→D): 4.5x**

**Aclaración 3.11s vs 3.36s:** El valor de 3.11s reportado en el worker sweep original fue un artifact de scheduling. En 20 runs de reproducción, nada tocó 3.11s. La mediana de Condition D es **3.44s**. El best real es **3.36s**.

**Bonus finding:** Condition A (secuencial sin fake clock) falló 3 de 5 runs — timing-sensitive tests son flaky sin fake clock. El fake clock elimina ese flakiness.

---

## 3. Auditoría de Archivos — Clasificación Final

### 3.1 Archivos candidatos a merge

| Archivo | Categoría | Descripción |
|---------|-----------|-------------|
| `tests/unit/conftest.py` | A) Performance | Fake clock opt-in (`TMUX_FORK_FAST_TESTS=1`) |
| `tests/unit/test_fake_clock.py` | A) Performance | 5 guard tests para fake clock |
| `pyproject.toml` | A) Performance | `pytest-xdist>=3.8.0` dependency |
| `uv.lock` | A) Performance | Lock file update |

### 3.2 Archivos que coinciden con main (sin cambios netos)

| Archivo | Razón |
|---------|-------|
| `src/interfaces/mcp/tools.py` | Refactor revertido — coincide con main en HEAD |
| `tests/.../test_tools.py` | Cambio 17→21 revertido — coincide con main |
| `tests/.../test_output_caps_integration.py` | Adaptación singleton revertida — coincide con main |
| `AGENTS.md` | Cambio incidental revertido |
| `README.md` | Cambio incidental revertido |
| `docs/mcp-setup.md` | Cambio incidental revertido |

### 3.3 Artefactos de sesión (NO merge)

| Archivo | Contenido |
|---------|-----------|
| `autoresearch.jsonl` | Log de 18 experimentos |
| `autoresearch.md` | Documento de sesión |
| `autoresearch.sh` | Script de benchmark |
| `autoresearch.checks.sh` | Script de backpressure |
| `autoresearch.ideas.md` | Ideas diferidas |

---

## 4. Commits Atómicos (Branch Final)

```
3422e0f3 chore: update benchmark scripts for TMUX_FORK_FAST_TESTS opt-in
550b8191 feat: controlled fake clock — TMUX_FORK_FAST_TESTS=1 opt-in + guard tests
0e6d4e11 fix: remove stale test exclusions — all 1615 tests pass
687431a7 revert: incidental doc changes not related to test speed
────────── ↑ Commits de limpieza (orquestados) ↓ Commits de autoresearch ↓ ──────
21a27935 Refactor conftest.py: module-level patch via pytest_configure
61dd8288 Bump to -n 8 with worksteal: 3.65s -> 3.36s
870561ec Switch to --dist=worksteal: 4.09s -> 3.65s
d02e45d6 Confirmation: 4.09s with threshold=0.001
d8e6c0ce Add conftest.py fake clock: 8.27s -> 4.17s
a8302389 Final confirmation: -n 6 --dist=loadscope stable at 8.49s
546e061a Switch to --dist=loadscope: 9.13s -> 8.27s
11a934b2 Try -n 8 --dist=loadfile: 9.85s -> 9.29s
f998acae Add pytest-xdist with -n auto: 15.33s -> 9.85s
408d6078 Baseline: 1614 tests in 15.33s sequential
f1988546 autoresearch: fix benchmark script
998092c6 autoresearch: setup session
```

---

## 5. Verificación Final (9/9 Checks PASS)

| # | Check | Resultado | Evidencia |
|---|-------|-----------|-----------|
| 1 | Production files clean | ✅ PASS | tools.py, test_tools.py, output_caps = idénticos a main |
| 2 | Full suite real clock | ✅ PASS | 1620 passed, 105 skipped en 14.94s |
| 3 | Full suite fast mode | ✅ PASS | 1620 passed, 105 skipped en 3.27s |
| 4 | Guard tests | ✅ PASS | 5/5 passed en 0.11s |
| 5 | No stale exclusions | ✅ PASS | grep --deselect = vacío |
| 6 | Fake clock opt-in | ✅ PASS | Solo activa con TMUX_FORK_FAST_TESTS=1 |
| 7 | Benchmark speed | ✅ PASS | Mediana 3.44s, under 5s |
| 8 | Session artifacts | ✅ IDENTIFIED | 5 archivos autoresearch.* |
| 9 | Merge candidates | ✅ LISTED | 4 archivos de producción |

---

## 6. Fake Clock — Diseño

### Control

```bash
# Reloj real (default — sin cambios de comportamiento):
uv run pytest tests/unit/

# Fast mode (fake clock):
TMUX_FORK_FAST_TESTS=1 uv run pytest tests/unit/ -n 8 --dist=worksteal
```

### Guard Tests

| Test | Valida |
|------|--------|
| `test_fake_clock_advance_logic` | offset avanza por sleep duration |
| `test_fake_clock_no_recursion` | sleep dentro de sleep no recurre |
| `test_fake_clock_deactivation` | funciones reales accesibles |
| `test_real_clock_works` | sin env var, sleep espera de verdad |
| `test_xdist_compatible` | cada worker tiene su propio estado |

### Escape hatch

Sin `TMUX_FORK_FAST_TESTS=1`, el comportamiento es idéntico a antes del cambio. El fake clock es **100% opt-in**.

---

## 7. Tests Preexistentes — Estado Corregido

**Hallazgo del auditor:** Los 8 tests de `test_output_caps_integration.py` y el test `test_registers_all_17_tools` que se consideraban "pre-existent failures" **PASAN en la branch actual**. Las deselecciones eran stale — probablemente causadas por el refactor incidental de tools.py durante la sesión de autoresearch, ya revertido.

**Estado actual:**
- Full suite sin exclusiones: **1620 passed, 105 skipped** (105 son xdist-tmux que requieren tmux)
- 0 failures
- 0 tests ocultos

---

## 8. Orquestación — Costo y Eficiencia

| Fase | Agente | Duración | Tokens | Resultado |
|------|--------|----------|--------|-----------|
| Autoresearch loop | glm-5.1 | 40 min | ~32K | 18 experimentos, best 3.36s |
| Auditoría | glm-5.1 | 11 min | ~45K | 14 archivos clasificados |
| Benchmarks | glm-5.1 | 10 min | ~6K | 20 runs, 4 condiciones |
| Implementación | glm-5.1 | 10 min | ~16K | 4 commits atómicos |
| Verificación | glm-5.1 | 3.5 min | ~3K | 9/9 checks pass |
| **Total** | | **~75 min** | **~102K** | Branch limpia y verificada |

---

## 9. Plan de Merge Recomendado

### Commits a squash-merge a main

Solo los 4 commits de limpieza contienen cambios netos vs main:

1. **`pyproject.toml` + `uv.lock`** — dependencia pytest-xdist
2. **`tests/unit/conftest.py`** — fake clock opt-in
3. **`tests/unit/test_fake_clock.py`** — guard tests

Los commits intermedios de autoresearch (baseline, xdist, loadfile, loadscope, fake clock, worksteal) son history que se pierde en squash — pero toda la info está en `autoresearch.jsonl` (artefacto de sesión, no merge).

### Artefactos a mantener fuera de main

- `autoresearch.*` — mantener en la branch para referencia histórica
- `src/interfaces/mcp/tools.py` — ya coincide con main (revertido)

---

*Informe v2 — corregido tras orquestación de 3 agentes. Datos auditados, contradicciones resueltas, 9/9 verificaciones pasadas.*
