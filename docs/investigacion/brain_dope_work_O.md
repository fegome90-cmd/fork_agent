# Brain Dope - work_O

Fecha: 2026-02-08

## Objetivo
Capturar toda la informacion relevante de work_O para planificar mejoras.

## Resumen rapido
- Proyecto: wo-system (work order orchestration).
- Clean Architecture + FP boundaries.
- CLI con Typer, output con Rich.
- Config TOML + defaults hardcoded.
- Locking con fcntl + stale detection.

## Estructura del repo
- src/wo_system/
  - domain/ (result, wo_entities, wo_transactions)
  - application/ (wo_service, artifact_generator)
  - infrastructure/ (config, file_lock, checkpoint_system, github_client)
  - cli/ (main, output, github_helpers)
  - interfaces/ (vacio)
- scripts/
  - wo_take.sh, wo_finish.sh, wo_handoff.sh, wo_checkpoint.sh, wo_lib.sh
- docs/
  - architecture/ (ADR-0001)
  - plans/ (bootstrap, repo-config, clean-arch, TDD refactor, workflow analysis)

## Tooling y calidad
- Python >= 3.12
- uv + ruff + mypy + pytest + pyrefly + ty
- Makefile: venv, install, lint, test, type, type-canary
- CLI entry: wo = wo_system.cli.main:app

## Arquitectura declarada
- domain: puro, sin IO
- application: orquesta domain + infra
- infrastructure: IO (FS, GitHub, locks)

## Dominio
- Result monad: Ok/Err + map/and_then
- WorkOrder:
  - id: WO-#### (regex)
  - states: pending, running, done, failed, partial
  - priority: critical, high, medium, low
  - invariants: no self-deps, timestamps consistentes
- Governance.must valida IDs WO-####

## Configuracion
- Config via config/settings.toml o WO_CONFIG_DIR
- Defaults: _ctx/jobs/{pending,running,done,failed}, handoff, logs
- worktree_parent: .worktrees
- max_concurrent_wos, lock_timeout_seconds, base_branch

## Ejemplos (TOML/YAML)

### settings.toml (override defaults)
```toml
# Example settings.toml
max_concurrent_wos = 5
lock_timeout_seconds = 1800
base_branch = "main"
worktree_parent = ".worktrees"

ctx_dir = "_ctx"
jobs_pending = "_ctx/jobs/pending"
jobs_running = "_ctx/jobs/running"
jobs_done = "_ctx/jobs/done"
jobs_failed = "_ctx/jobs/failed"
logs_dir = "_ctx/logs"
handoff_dir = "_ctx/handoff"
```

### WO YAML (pending)
```yaml
id: WO-0001
epic_id: EPIC-001
title: Integration Test WO
priority: high
status: pending
dod_id: DOD-001
dependencies: []
```

### WO YAML (running)
```yaml
id: WO-0001
epic_id: EPIC-001
title: Integration Test WO
priority: high
status: running
dod_id: DOD-001
dependencies: []
owner: testuser
started_at: "2026-02-08T10:30:00+00:00"
branch: "wo/wo-0001"
worktree: ".worktrees/wo-0001"
```

## Locking
- FileLock con fcntl
- Guarda JSON con holder, acquired_at, pid
- stale detection por edad (default 3600s)
- timeout + retry

## WOService (core)
- take_wo:
  - Lee WO en pending
  - Valida WO y deps (salvo --force)
  - Lock en running
  - Actualiza owner/status/started_at
  - Genera branch y worktree path (solo metadata)
  - Mueve YAML a running con write atomico
- finish_wo:
  - Lee WO en running
  - Actualiza status/finished_at
  - Mueve a done/failed
  - Libera lock (borra archivo)
- list_wos: lee por estado, valida, ordena por id
- get_wo: busca en pending/running/done/failed

## CheckpointSystem
- validate_message: no vacio, max 200, sanitiza newlines
- add_checkpoint: lock + append en YAML
- list_checkpoints: devuelve Result

## CLI
- Comandos WO: take, finish, get, list
- Checkpoints: checkpoint add/list
- Artifacts: artifacts generate/validate
- GitHub: github push/pr (via GitHubClient)
- Owner se resuelve por flag o env WO_OWNER

## Scripts shell
- wo_take.sh, wo_finish.sh, wo_handoff.sh, wo_checkpoint.sh, wo_lib.sh
- Parecen workflow legacy/auxiliar (no integrados en CLI Python)

## Docs y planes
- ADR-0001: Clean Architecture + FP boundaries
- Planes de bootstrap y repo-config
- Plan Phase3 TDD refactor: 15 issues (crit/high/med) con TDD estricto
- workflow-completion-analysis.md:
  - Comparativa con trifecta_dope/mininotebook
  - Gaps criticos: worktree creation, cleanup, wo next
  - Recomendacion: foundation de recovery/cleanup antes de features

## Workflow actual (segun docs)
- Branch naming actual: wo/WO-XXXX (inconsistente con otros sistemas)
- Worktree path actual: .wt/WO-XXXX (segun doc), pero config usa .worktrees
- take_wo no crea worktree real (solo metadata)
- finish_wo no limpia worktree

## Riesgos / gaps destacados (docs)
- Falta worktree creation y cleanup
- Falta wo next y wo status
- Falta recovery y cleanup de orphans
- Branch naming inconsistente
- Config vs docs inconsistente (.worktrees vs .wt)

## Notas abiertas
- Definir fuente de verdad para paths (config vs docs)
- Decidir estrategia de worktrees y naming
- Integrar scripts shell o eliminarlos

