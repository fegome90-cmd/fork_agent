"""Goal analysis service for deriving requirements from goals."""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.domain.entities.derived_requirement import (
    DerivedRequirement,
    RequirementPriority,
    RequirementSource,
)
from src.domain.entities.goal import Goal


def slugify(text: str) -> str:
    """Convert text to a slug-friendly identifier."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = text.strip("-")
    return text


class GoalAnalysisError(Exception):
    """Raised when goal analysis fails to produce requirements."""

    pass


class GoalAnalyzer:
    """Analyzes goals to derive implicit requirements."""

    # Keyword-based derivation rules
    DERIVATION_RULES = {
        frozenset(["api", "rest", "endpoint", "http"]): [
            ("error-handling", "Error handling for all endpoints", RequirementPriority.MUST),
            ("input-validation", "Input validation", RequirementPriority.MUST),
            ("status-codes", "Proper HTTP status codes", RequirementPriority.MUST),
            ("api-documentation", "API documentation", RequirementPriority.NICE),
        ],
        frozenset(["auth", "login", "password", "jwt", "token"]): [
            ("password-hashing", "Secure password hashing", RequirementPriority.MUST),
            ("session-management", "Session management", RequirementPriority.MUST),
            ("password-reset", "Password reset functionality", RequirementPriority.NICE),
            ("two-factor", "Two-factor authentication", RequirementPriority.NICE),
        ],
        frozenset(["payment", "stripe", "checkout", "transaction"]): [
            ("webhook-handling", "Webhook handling", RequirementPriority.MUST),
            ("receipt-generation", "Receipt generation", RequirementPriority.NICE),
            ("refund-handling", "Refund processing", RequirementPriority.NICE),
            ("payment-logging", "Payment transaction logging", RequirementPriority.MUST),
        ],
        frozenset(["database", "db", "sql", "postgres", "mysql"]): [
            ("database-migrations", "Database migrations", RequirementPriority.MUST),
            ("connection-pooling", "Connection pooling", RequirementPriority.MUST),
            ("backup-strategy", "Backup strategy", RequirementPriority.NICE),
        ],
        frozenset(["frontend", "ui", "web", "react", "vue"]): [
            ("responsive-design", "Responsive design", RequirementPriority.MUST),
            ("accessibility", "Accessibility (a11y)", RequirementPriority.NICE),
            ("loading-states", "Loading states", RequirementPriority.NICE),
            ("error-messages", "User-friendly error messages", RequirementPriority.MUST),
        ],
        frozenset(["email", "notification"]): [
            ("email-templates", "Email templates", RequirementPriority.MUST),
            ("unsubscribe-handling", "Unsubscribe handling", RequirementPriority.MUST),
            ("email-deliverability", "Email deliverability", RequirementPriority.NICE),
        ],
        frozenset(["file", "upload", "storage", "s3"]): [
            ("file-validation", "File validation", RequirementPriority.MUST),
            ("storage-cleanup", "Storage cleanup", RequirementPriority.NICE),
            ("upload-progress", "Upload progress tracking", RequirementPriority.NICE),
        ],
        frozenset(["security", "encryption", "crypto"]): [
            ("encryption-at-rest", "Encryption at rest", RequirementPriority.MUST),
            ("encryption-in-transit", "Encryption in transit (TLS)", RequirementPriority.MUST),
            ("audit-logging", "Audit logging", RequirementPriority.MUST),
            ("security-headers", "Security headers", RequirementPriority.MUST),
        ],
    }

    def analyze(self, goal: Goal | None) -> list[DerivedRequirement]:
        """Derive requirements from goal and explicit requirements.

        Args:
            goal: The goal to analyze, or None for backward compatibility.

        Returns:
            List of derived requirements.

        Raises:
            GoalAnalysisError: If no requirements are produced.
        """
        if goal is None:
            return []

        requirements = []

        # 1. Start with must_haves as explicit requirements
        for must_have in goal.must_haves:
            req_id = slugify(must_have)
            # Avoid duplicates
            if not any(r.id == req_id for r in requirements):
                requirements.append(
                    DerivedRequirement(
                        id=req_id,
                        description=must_have,
                        source=RequirementSource.EXPLICIT,
                        priority=RequirementPriority.MUST,
                    )
                )

        # 2. Add nice-to-haves
        for nice in goal.nice_to_haves:
            req_id = slugify(nice)
            if not any(r.id == req_id for r in requirements):
                requirements.append(
                    DerivedRequirement(
                        id=req_id,
                        description=nice,
                        source=RequirementSource.EXPLICIT,
                        priority=RequirementPriority.NICE,
                    )
                )

        # 3. Analyze goal for implicit requirements
        implicit = self._derive_implicit(goal)
        for req in implicit:
            if not any(r.id == req.id for r in requirements):
                requirements.append(req)

        # CRITICAL: Validate we have at least some requirements
        if not requirements:
            raise GoalAnalysisError(
                "Goal analysis produced no requirements. "
                "Please provide at least one --must-have or use a more descriptive goal."
            )

        return requirements

    def _derive_implicit(self, goal: Goal) -> list[DerivedRequirement]:
        """Derive implicit requirements from goal text.

        Args:
            goal: The goal to analyze.

        Returns:
            List of implicitly derived requirements.
        """
        implicit: list[DerivedRequirement] = []
        objective_lower = goal.objective.lower()

        # Check each keyword group
        for keywords, reqs in self.DERIVATION_RULES.items():
            # Check if any keyword matches
            if any(kw in objective_lower for kw in keywords):
                for req_id, desc, priority in reqs:
                    # Check if not already explicitly provided
                    explicit_ids = {slugify(m) for m in goal.must_haves}
                    explicit_ids |= {slugify(n) for n in goal.nice_to_haves}

                    if req_id not in explicit_ids:
                        # Check if not already added
                        if not any(r.id == req_id for r in implicit):
                            implicit.append(
                                DerivedRequirement(
                                    id=req_id,
                                    description=desc,
                                    source=RequirementSource.DERIVED,
                                    priority=priority,
                                )
                            )

        return implicit
