"""Pydantic models for API discovery cards.

These models provide structured, LLM-optimized information about the API
for external agents to self-discover how to use the Fork Agent API.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class CardType(StrEnum):
    """Types of discovery cards."""

    OVERVIEW = "overview"
    WORKFLOW = "workflow"
    ERROR = "error"


class AuthInfo(BaseModel):
    """Authentication information for the API."""

    type: str = Field(..., description="Authentication type (e.g., 'api_key')")
    header: str = Field(..., description="Header name for authentication")
    example: str = Field(..., description="Example header value")
    description: str | None = Field(None, description="Optional description of auth method")


class EndpointSummary(BaseModel):
    """Minimal endpoint information with curl example."""

    path: str = Field(..., description="Endpoint path")
    method: str = Field(..., description="HTTP method")
    auth_required: bool = Field(..., description="Whether authentication is required")
    curl_example: str = Field(..., description="Example curl command")
    request_body: str | None = Field(None, description="Example request body if applicable")
    description: str | None = Field(None, description="Brief description of what the endpoint does")


class AgentBackendInfo(BaseModel):
    """Information about an agent backend."""

    name: str = Field(..., description="Backend identifier")
    display_name: str = Field(..., description="Human-readable name")
    available: bool = Field(..., description="Whether the backend is installed and ready")


class WorkflowStep(BaseModel):
    """A single step in a workflow recipe."""

    step_number: int = Field(..., ge=1, description="Step number in sequence")
    action: str = Field(..., description="Action name/identifier")
    endpoint: str = Field(..., description="API endpoint to call")
    description: str = Field(..., description="What this step does")
    request_body: str | None = Field(None, description="Example request body")


class WorkflowCardData(BaseModel):
    """Data for a workflow recipe card."""

    workflow_id: str = Field(..., description="Unique workflow identifier")
    name: str = Field(..., description="Workflow name")
    description: str = Field(..., description="What this workflow accomplishes")
    steps: list[WorkflowStep] = Field(..., description="Ordered steps to execute")


class ErrorGuidance(BaseModel):
    """Guidance for recovering from an error."""

    status_code: int = Field(..., description="HTTP status code")
    title: str = Field(..., description="Error title")
    description: str = Field(..., description="What went wrong")
    recovery_steps: list[str] = Field(..., description="Steps to resolve the error")
    example_curl: str | None = Field(None, description="Example curl showing correct usage")


class OverviewCardData(BaseModel):
    """Data for the overview discovery card."""

    api_name: str = Field(..., description="API name")
    version: str = Field(..., description="API version")
    base_url: str = Field(..., description="Base URL for API requests")
    auth: AuthInfo = Field(..., description="Authentication information")
    endpoints: list[EndpointSummary] = Field(
        default_factory=list,
        description="Available endpoints",
    )
    available_agents: list[AgentBackendInfo] = Field(
        default_factory=list,
        description="Available agent backends",
    )
    common_errors: list[int] = Field(
        default_factory=lambda: [401, 404, 409, 429, 503],
        description="Common error codes to handle",
    )


class DiscoveryCardEnvelope(BaseModel):
    """Envelope for all discovery cards."""

    card_type: CardType = Field(..., description="Type of card")
    version: str = Field(default="1.0.0", description="Card schema version")
    generated_at: datetime = Field(
        default_factory=datetime.now,
        description="When this card was generated",
    )
    cache_ttl: int = Field(default=3600, description="Seconds to cache this card")
    data: (
        OverviewCardData | WorkflowCardData | ErrorGuidance | dict[str, Any]
    ) = Field(..., description="Card payload")
    quick_actions: list[str] = Field(
        default_factory=list,
        description="Quick action suggestions",
    )


class WorkflowListResponse(BaseModel):
    """Response containing list of workflow cards."""

    workflows: list[WorkflowCardData] = Field(..., description="Available workflows")


__all__ = [
    "CardType",
    "AuthInfo",
    "EndpointSummary",
    "AgentBackendInfo",
    "WorkflowStep",
    "WorkflowCardData",
    "ErrorGuidance",
    "OverviewCardData",
    "DiscoveryCardEnvelope",
    "WorkflowListResponse",
]
