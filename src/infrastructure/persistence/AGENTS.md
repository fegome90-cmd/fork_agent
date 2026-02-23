# Persistence - AGENTS.md

> Database adapters and repositories

## OVERVIEW

Database persistence layer with repositories and migrations (score 15).

## WHERE TO LOOK

- `container.py` - DI wiring for persistence
- `database.py` - Database connection/ORM setup
- `message_store.py` - Message storage implementation
- `repositories/` - Repository implementations
- `migrations/` - Schema migrations

## CONVENTIONS

- Follow DDD: ports in domain/ports, adapters here
- Type hints everywhere
- Use Protocols for repository contracts
- Tests mirror domain structure

## ANTI-PATTERNS

- Embed business rules in SQL queries
- Access DB from non-persistence layers
- Tight coupling to single DB engine
- Skip tests for persistence code
