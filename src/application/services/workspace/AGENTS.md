OVERVIEW: High-complexity workspace management service for OpenCode agents.

WHERE TO LOOK
- src/application/services/workspace: orchestration, use cases, and workflow logic.
- src/domain/ports: WorkspaceRepository and related ports the service depends on.
- src/infrastructure/persistence: repository implementations and adapters (DB, memory stores).
- src/infrastructure/container.py: DI wiring for workspace components.
- tests/unit/workspace: unit tests mirroring src structure.
- tests/integration/workspace: integration tests for persistence and orchestration.
- src/interfaces/cli/commands/workspace.py: CLI interactions that trigger workspace operations.
- docs/architecture/workspace.md: architecture notes and decisions for the workspace module.
- src/application/services/workspace/README.md: module-level guidance for contributors.

CONVENTIONS
- Follow DDD: keep business rules in domain, orchestration in application services.
- Use immutable domain entities; return new instances instead of mutating existing ones.
- Typing: Python 3.11+, explicit type hints, X | None for Optional.
- Naming: WorkspaceService, CreateWorkspaceUseCase, LoadWorkspaceUseCase, UpdateContextUseCase.
- DI: rely on container.py to inject repositories and memory providers.
- Tests: unit tests for ports and services; integration tests for storage and memory GC.
- Events: publish workspace events on context changes; avoid silent failures.
- Documentation: link architecture notes in docs/architecture/workspace.md if present.
- Event contracts: standardize event payloads for workspace actions (save, load, prune).

ANTI-PATTERNS
- Mixing persistence code into application services; breach of ports/adapters.
- Mutating domain objects in place; produce new instances instead.
- Silent failures in workspace operations; always raise or log with context.
- Tightly coupling to a concrete store; depend on WorkspaceRepository port.
- Memory leaks or unbounded context histories without pruning rules.
- Skipping tests for workspace scenarios or edge cases.
- Blocking I/O on critical paths; use asynchronous patterns where appropriate.
