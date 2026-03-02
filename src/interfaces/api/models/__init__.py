"""Modelos Pydantic para la API."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProcessInfo(BaseModel):
    """Información de un proceso PM2."""

    name: str
    pm_id: int
    pid: int
    status: str
    cpu: float
    memory: str
    uptime: datetime
    restarts: int
    health: str
    env: dict[str, str] | None = None


class ProcessListResponse(BaseModel):
    """Response para listar procesos."""

    data: list[ProcessInfo]
    meta: dict[str, int | str]


class ProcessStartRequest(BaseModel):
    """Request para iniciar un proceso."""

    name: str = Field(..., min_length=1, max_length=100)
    script: str = Field(..., min_length=1)
    args: str | None = None
    cwd: str | None = None
    env: dict[str, str] | None = None


class ProcessScaleRequest(BaseModel):
    """Request para escalar un proceso."""

    instances: int = Field(..., ge=1, le=16, description="Number of instances (1-16)")


class ProcessResponse(BaseModel):
    """Response generico de proceso."""

    data: dict[str, int | str]


class AgentSession(BaseModel):
    """Sesion de un agente."""

    session_id: str
    agent_type: str
    status: str
    started_at: datetime
    tmux_session: str | None = None
    hooks: list[dict[str, str]] | None = None


class AgentSessionCreate(BaseModel):
    """Request para crear sesion de agente."""

    agent_type: str = Field(
        default="opencode",
        min_length=1,
        description="Agent backend: 'opencode' or 'pi'",
    )
    task: str = Field(..., min_length=1)
    model: str | None = Field(
        default=None,
        description="Optional model override (uses backend default if not specified)",
    )
    workspace: str | None = None
    hooks: bool = True
    tmux: bool = True


class AgentSessionResponse(BaseModel):
    """Response de sesion de agente."""

    data: AgentSession


class SessionListResponse(BaseModel):
    """Response para listar sesiones."""

    data: list[AgentSession]


class WorkflowPlanRequest(BaseModel):
    """Request para crear plan de workflow."""

    task: str = Field(..., min_length=1)
    description: str | None = None


class WorkflowPlan(BaseModel):
    """Plan de workflow."""

    plan_id: str
    task: str
    status: str
    created_at: datetime


class WorkflowExecute(BaseModel):
    """Execution de workflow."""

    execute_id: str
    plan_id: str
    status: str
    started_at: datetime


class WorkflowVerify(BaseModel):
    """Verificacion de workflow."""

    verify_id: str
    execute_id: str
    status: str
    tests: dict[str, int]
    coverage: float


class WorkflowShip(BaseModel):
    """Ship de workflow."""

    branch: str
    commit_message: str


class WorkflowResponse(BaseModel):
    """Response generico de workflow."""

    data: dict[str, str | datetime | float | dict[str, int]]


class ObservationCreate(BaseModel):
    """Request para crear observacion."""

    content: str = Field(..., min_length=1, max_length=10000)


class Observation(BaseModel):
    """Observacion guardada."""

    id: str
    content: str
    timestamp: int
    metadata: dict[str, Any] | None = None
    idempotency_key: str | None = None


class ObservationResponse(BaseModel):
    """Response de observacion."""

    data: Observation


class ObservationListResponse(BaseModel):
    """Response para listar observaciones."""

    data: list[Observation]
    count: int | None = None


class QueryResponse(BaseModel):
    """Response for structured memory query."""

    data: list[dict[str, Any]]
    count: int


class AgentInfo(BaseModel):
    """Information about an agent backend."""

    name: str
    display_name: str
    available: bool


class HealthResponse(BaseModel):
    """Response de health check."""

    status: str
    pm2: dict[str, str | int]
    agents: list[AgentInfo] = Field(
        default_factory=list,
        description="Available agent backends",
    )
    version: str


class MetricsResponse(BaseModel):
    """Response de metricas."""

    cpu: float
    memory: str
    uptime: int
    requests_total: int
    errors_total: int


class ErrorResponse(BaseModel):
    """Response de error."""

    error: dict[str, str | dict]


class WebhookCreate(BaseModel):
    """Request para crear webhook."""

    url: str = Field(..., pattern=r"^https?://")
    events: list[str] = Field(..., min_length=1)
    secret: str | None = None


class Webhook(BaseModel):
    """Webhook configurado (interno)."""

    id: str
    url: str
    events: list[str]
    secret: str | None = None


class WebhookSafe(BaseModel):
    """Webhook sin secret para respuestas."""

    id: str
    url: str
    events: list[str]


class WebhookResponse(BaseModel):
    """Response de webhook (sin secret)."""

    data: WebhookSafe


class WebhookListResponse(BaseModel):
    """Response para listar webhooks."""

    data: list[WebhookSafe]


class GcStatusResponse(BaseModel):
    """Response for GC status endpoint."""

    last_run_at: datetime | None = None
    cleaned_count: int = 0
    failed_count: int = 0
    last_duration_ms: int = 0
    gc_interval_seconds: int = 0
    gc_min_age_seconds: int = 0
    status: str = "never_run"


# Discovery card models
from src.interfaces.api.models.discovery import (
    AgentBackendInfo,
    AuthInfo,
    CardType,
    DiscoveryCardEnvelope,
    EndpointSummary,
    ErrorGuidance,
    OverviewCardData,
    WorkflowCardData,
    WorkflowListResponse,
    WorkflowStep,
)

__all__ = [
    # Process models
    "ProcessInfo",
    "ProcessListResponse",
    "ProcessStartRequest",
    "ProcessScaleRequest",
    "ProcessResponse",
    # Agent models
    "AgentSession",
    "AgentSessionCreate",
    "AgentSessionResponse",
    "SessionListResponse",
    # Workflow models
    "WorkflowPlanRequest",
    "WorkflowPlan",
    "WorkflowExecute",
    "WorkflowVerify",
    "WorkflowShip",
    "WorkflowResponse",
    # Observation models
    "ObservationCreate",
    "Observation",
    "ObservationResponse",
    "ObservationListResponse",
    "QueryResponse",
    # System models
    "AgentInfo",
    "HealthResponse",
    "MetricsResponse",
    "ErrorResponse",
    # Webhook models
    "WebhookCreate",
    "Webhook",
    "WebhookSafe",
    "WebhookResponse",
    "WebhookListResponse",
    "GcStatusResponse",
    # Discovery models
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
