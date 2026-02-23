# Orchestration Service - AGENTS.md

> High-complexity orchestration with hooks/events

## OVERVIEW

Orchestration service with hooks and event-driven flows (score 18).

## WHERE TO LOOK

- `events/` - Event definitions and payload schemas
- `hooks/` - Hook handlers, listeners, and adapters
- `dispatcher.py` - Core orchestration engine
- `specs.py` - Action specifications
- `hook_service.py` - Hook service implementation
- `actions.py` - Action definitions

## CONVENTIONS

- Favor immutable event payloads
- Use ports/protocols for event buses, inject via DI
- Emission/handling must be decoupled
- Async-first: prefer non-blocking handlers

## ANTI-PATTERNS

- Tight coupling between emitters and listeners
- Synchronous sleep/calls inside listeners
- Mutating event payloads in-flight
- Accessing DB directly from hooks
