# API Routes - AGENTS.md

> HTTP endpoints layer

## OVERVIEW

API routing layer for HTTP endpoints (score 21).

## WHERE TO LOOK

- `routes/` - Endpoint definitions (agents.py, memory.py, processes.py, system.py, webhooks.py, workflow.py)
- `schemas/` - Request/response models
- `middleware/` - Auth, error handling
- `services/` - Business logic invoked by routes

## CONVENTIONS

- Routes delegate to application services; keep controllers thin
- Use explicit validation models (Pydantic)
- Return consistent HTTP status codes and JSON payloads
- Type hints everywhere

## ANTI-PATTERNS

- Business logic in route handlers
- Direct DB/ORM access in routes
- Broad except blocks
- API layer coupling to domain implementation
