from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Goal:
    """Immutable goal entity representing an objective.

    Represents a structured goal with requirements and scope definitions.

    Attributes:
        objective: The main goal description.
        must_haves: Non-negotiable requirements.
        nice_to_haves: Optional enhancements.
        scope_in: In-scope items.
        scope_out: Out-of-scope items.
    """

    objective: str
    must_haves: tuple[str, ...] = ()
    nice_to_haves: tuple[str, ...] = ()
    scope_in: tuple[str, ...] = ()
    scope_out: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.objective, str):
            raise TypeError("objective must be a string")
        if not self.objective:
            raise ValueError("objective cannot be empty")
        if len(self.objective) > 10000:
            raise ValueError("objective must not exceed 10000 characters")
        if not isinstance(self.objective, str):
            raise TypeError("objective must be a string")
        if len(self.objective) > 10000:
            raise ValueError("objective must not exceed 10000 characters")
        # Validate scope disjointness
        scope_in_set = set(self.scope_in)
        scope_out_set = set(self.scope_out)
        overlap = scope_in_set & scope_out_set
        if overlap:
            raise ValueError(f"scope_in and scope_out must be disjoint, found: {overlap}")
        # Validate collections are tuples
        if not isinstance(self.must_haves, tuple):
            raise TypeError("must_haves must be a tuple")
        if not isinstance(self.nice_to_haves, tuple):
            raise TypeError("nice_to_haves must be a tuple")
        if not isinstance(self.scope_in, tuple):
            raise TypeError("scope_in must be a tuple")
        if not isinstance(self.scope_out, tuple):
            raise TypeError("scope_out must be a tuple")
