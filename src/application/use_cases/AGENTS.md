# Use Cases - AGENTS.md

> Business logic orchestration layer

## OVERVIEW

Use-case layer orchestrating business rules via domain ports (score 21).

## WHERE TO LOOK

- `save_observation.py` - Save observation use case
- `get_observation.py` - Get observation use case
- `list_observations.py` - List observations use case
- `search_observations.py` - Search use case
- `delete_observation.py` - Delete use case
- `fork_terminal.py` - Fork terminal orchestration

## CONVENTIONS

- UseCase naming: CamelCase (e.g., CreateOrderUseCase)
- Entry method: execute(input: InputDto) -> OutputDto
- Inputs/Outputs as Pydantic models or dataclasses
- Keep use cases stateless
- Dependencies injected via constructor (ports)

## ANTI-PATTERNS

- Call repositories/infrastructure directly
- Embed UI/API concerns in use cases
- Duplicate business logic
- Bypass DTOs
