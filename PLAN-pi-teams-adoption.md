# Plan: Adopt pi-teams Features into tmux_fork

## Summary

Implement 5 workstreams from pi-teams analysis: terminal adapters (tmux/zellij/iterm2), task board with plan approval, race condition tests, autonomous agent polling, and team templates. Smart model resolution excluded — keeping static ZAI table.

## In Scope
- Terminal Adapter Protocol (ABC + TmuxAdapter + ZellijAdapter + Iterm2Adapter)
- Task Board entity with status workflow, blocking deps, plan approval
- Race condition tests for SQLite concurrent write correctness
- Autonomous agent polling with inbox-based self-assignment
- Team templates with save/load workflow
- CLI commands: fork task create/list/update/approve/reject
- Protocol integration with 10-phase orchestration

## Out of Scope
- Smart model resolution (keeping static ZAI model table)
- WezTerm, Windows, Cmux terminal adapters
- Migration of tmux-live bash to Python
- Changes to existing domain entities (Session, Observation, Message)

## Architecture Decisions
- Terminal adapters are primitives, not replacements — tmux-live bash stays unchanged
- Task Board uses SQLite with WAL mode, not file-based locking
- Sync Protocol with async wrappers at API boundary
- Layout is orchestrator concern, not adapter concern
- Autonomous polling is hybrid — orchestrator spawns, agent self-assigns

## Tasks

### Workstream 1: Terminal Adapter Pattern (Week 1)
- [ ] Task 1.1: CREATE src/domain/ports/multiplexer_adapter.py — ABC Protocol with detect(), spawn(), kill(), is_alive(), set_title(), configure_pane()
- [ ] Task 1.2: CREATE src/infrastructure/multiplexer/spawn_options.py — SpawnOptions + PaneInfo frozen dataclasses
- [ ] Task 1.3: CREATE src/infrastructure/multiplexer/tmux_adapter.py — TmuxAdapter using subprocess.run, TMUX env detection, remain-on-exit
- [ ] Task 1.4: CREATE src/infrastructure/multiplexer/zellij_adapter.py — ZellijAdapter using zellij CLI, ZELLIJ env detection
- [ ] Task 1.5: CREATE src/infrastructure/multiplexer/iterm2_adapter.py — Iterm2Adapter using AppleScript, TERM_PROGRAM detection, macOS only
- [ ] Task 1.6: CREATE src/infrastructure/multiplexer/adapter_registry.py — auto-detect by env vars, cached singleton
- [ ] Task 1.7: CREATE tests/unit/infrastructure/multiplexer/ — 5 test files

### Workstream 3: Race Condition Tests (Week 1, parallel with WS1)
- [ ] Task 3.1: CREATE tests/unit/test_sqlite_race_counter.py — N concurrent saves verify exactly N observations
- [ ] Task 3.2: CREATE tests/unit/test_messaging_completeness.py — 100 concurrent messages verify 0 loss
- [ ] Task 3.3: CREATE tests/unit/test_input_sanitization_matrix.py — parametrized path traversal, injection, null bytes

### Workstream 2: Task Board (Weeks 2-3)
- [ ] Task 2.1: CREATE src/domain/entities/task.py — frozen dataclass Task with Status enum PENDING/PLANNING/APPROVED/IN_PROGRESS/COMPLETED/DELETED
- [ ] Task 2.2: CREATE src/domain/ports/task_repository.py — ABC save/get/list_by_status/list_by_owner/list_blocked/delete
- [ ] Task 2.3: MODIFY src/infrastructure/persistence/migrations.py — add tasks table with indexes
- [ ] Task 2.4: CREATE src/infrastructure/persistence/repositories/task_repository.py — SQLite implementation
- [ ] Task 2.5: CREATE src/application/services/task_service.py — CRUD + submit_plan/approve/reject/resolve_blockers
- [ ] Task 2.6: CREATE src/interfaces/cli/commands/task.py — Typer CLI fork task create/list/update/submit-plan/approve/reject/delete
- [ ] Task 2.7: REGISTER task command in src/interfaces/cli/fork.py
- [ ] Task 2.8: CREATE tests/unit/domain/test_task_entity.py
- [ ] Task 2.9: CREATE tests/unit/application/test_task_service.py
- [ ] Task 2.10: CREATE tests/unit/infrastructure/test_task_repository.py

### Workstream 4: Autonomous Agent Polling (Week 4)
- [ ] Task 4.1: CREATE scripts/fork-autonomous-poll — bash polling loop for approved tasks + inbox
- [ ] Task 4.2: MODIFY protocol Phase 3 — add --autonomous flag to agent prompt
- [ ] Task 4.3: MODIFY protocol Phase 4 — monitor autonomous agents by task status
- [ ] Task 4.4: CREATE src/application/services/agent_polling_service.py

### Workstream 5: Team Templates (Week 5)
- [ ] Task 5.1: CREATE ~/.pi/agent/fork-templates/ with teams.yaml + agents/*.md
- [ ] Task 5.2: CREATE scripts/fork-template-list
- [ ] Task 5.3: CREATE scripts/fork-template-save
- [ ] Task 5.4: CREATE scripts/fork-template-show
- [ ] Task 5.5: MODIFY protocol Phase 1 — template matching

## Execution Phases

**Phase A (Week 1):** WS1 + WS3 in parallel — 2 implementers
**Phase B (Weeks 2-3):** WS2 sequential — 3 implementers in batches
**Phase C (Week 4):** WS4 sequential — 1 implementer
**Phase D (Week 5):** WS5 — 1 implementer

## Validation
- uv run pytest tests/unit/infrastructure/multiplexer/ -v
- uv run pytest tests/unit/test_sqlite_race_counter.py -v
- uv run pytest tests/unit/test_messaging_completeness.py -v
- uv run pytest tests/unit/domain/test_task_entity.py -v
- uv run mypy src/ --strict
- uv run ruff check src/
- fork task create --subject "test" --description "test"
- fork task list --status PENDING

## Risks
- Sync/async mismatch — asyncio.to_thread() at boundary
- Zellij synthetic IDs — derive from session+name
- Autonomous agent file conflicts — FILE_TOUCHED + conflict-detect
- remain-on-exit semantics — configure_pane() in Protocol
- Migration compat — additive migration only
