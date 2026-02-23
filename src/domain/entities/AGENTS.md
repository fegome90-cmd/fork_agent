OVERVIEW
Immutable domain entity models for this package: value objects that encode core invariants.

WHERE TO LOOK
- Domain entity definitions live in src/domain/entities/*.py
- Look for @dataclass(frozen=True) definitions that model core domain concepts
- See tests under tests/unit/domain/entities and tests for domain invariants

CONVENTIONS
- Use from __future__ import annotations and standard typing hints
- Prefer @dataclass(frozen=True) for immutability; avoid mutable fields
- Name classes in PascalCase; fields in snake_case
- Keep entities shallow and focus on identity and invariants, not persistence
- If a field is a collection, use tuple or FrozenList; use field(default_factory=...) for defaults
- Implement invariants in __post_init__ to enforce business rules
- Equality and hashing derive from all relevant fields to maintain value semantics

ANTI-PATTERNS
- Do not mutate state after creation; entities should be immutable
- Avoid embedding infrastructure concerns (DB columns, serialization) in entities
- Do not expose internal mutable structures directly; wrap in tuples/frozensets
- Avoid coupling domain entities to services; keep behavior focused on invariants
- Do not create anemic entities; include meaningful domain methods that preserve invariants
