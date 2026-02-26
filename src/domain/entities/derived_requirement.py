from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RequirementPriority(StrEnum):
    """Requirement priority enum with string values for database persistence."""

    MUST = "must"
    NICE = "nice"


class RequirementSource(StrEnum):
    """Requirement source enum with string values for database persistence."""

    EXPLICIT = "explicit"
    DERIVED = "derived"


@dataclass(frozen=True)
class DerivedRequirement:
    """Immutable derived requirement entity.

    Represents a requirement derived from goal analysis.

    Attributes:
        id: Unique identifier for the requirement.
        description: The requirement description.
        source: Source of the requirement (explicit or derived).
        priority: Priority level (must or nice).
    """

    id: str
    description: str
    source: RequirementSource
    priority: RequirementPriority

    def __post_init__(self) -> None:
        if not isinstance(self.id, str):
            raise TypeError("id must be a string")
        if not self.id:
            raise ValueError("id cannot be empty")
        if not isinstance(self.description, str):
            raise TypeError("description must be a string")
        if not self.description:
            raise ValueError("description cannot be empty")
        if not isinstance(self.source, RequirementSource):
            raise TypeError("source must be a RequirementSource")
        if not isinstance(self.priority, RequirementPriority):
            raise TypeError("priority must be a RequirementPriority")
