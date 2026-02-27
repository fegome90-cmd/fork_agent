"""Discovery routes for API self-documentation.

These endpoints provide LLM-optimized "cards" that help external agents
self-discover how to use the Fork Agent API without needing verbose
OpenAPI/Swagger documentation.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from src.infrastructure.agent_backends import get_available_backends, list_all_backends
from src.interfaces.api.dependencies import verify_api_key
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/discovery", tags=["discovery"])

# Base URL for the API
BASE_URL = "http://localhost:8080"


def _build_auth_info() -> AuthInfo:
    """Build authentication info for the overview card."""
    return AuthInfo(
        type="api_key",
        header="X-API-Key",
        example="X-API-Key: tmux-agents-local",
        description="API key authentication via header",
    )


def _build_endpoint_summaries() -> list[EndpointSummary]:
    """Build list of endpoint summaries with curl examples."""
    return [
        # Health endpoint (no auth)
        EndpointSummary(
            path="/api/v1/health",
            method="GET",
            auth_required=False,
            curl_example=f"curl {BASE_URL}/api/v1/health",
            description="Check API health and available agent backends",
        ),
        # Agent sessions
        EndpointSummary(
            path="/api/v1/agents/sessions",
            method="POST",
            auth_required=True,
            request_body='{"agent_type": "opencode", "task": "implement X"}',
            curl_example=f"curl -X POST {BASE_URL}/api/v1/agents/sessions "
            f"-H 'X-API-Key: $API_KEY' "
            f"-H 'Content-Type: application/json' "
            f"-d '{{\"agent_type\": \"opencode\", \"task\": \"your task\"}}'",
            description="Create a new agent session",
        ),
        EndpointSummary(
            path="/api/v1/agents/sessions",
            method="GET",
            auth_required=True,
            curl_example=f"curl -H 'X-API-Key: $API_KEY' {BASE_URL}/api/v1/agents/sessions",
            description="List all agent sessions",
        ),
        EndpointSummary(
            path="/api/v1/agents/sessions/{{session_id}}",
            method="GET",
            auth_required=True,
            curl_example=f"curl -H 'X-API-Key: $API_KEY' {BASE_URL}/api/v1/agents/sessions/{{session_id}}",
            description="Get session details by ID",
        ),
        EndpointSummary(
            path="/api/v1/agents/sessions/{{session_id}}",
            method="DELETE",
            auth_required=True,
            curl_example=f"curl -X DELETE -H 'X-API-Key: $API_KEY' {BASE_URL}/api/v1/agents/sessions/{{session_id}}",
            description="Delete an agent session",
        ),
        # Workflow endpoints
        EndpointSummary(
            path="/api/v1/workflow/outline",
            method="POST",
            auth_required=True,
            request_body='{"task": "implement feature X"}',
            curl_example=f"curl -X POST {BASE_URL}/api/v1/workflow/outline "
            f"-H 'X-API-Key: $API_KEY' "
            f"-H 'Content-Type: application/json' "
            f"-d '{{\"task\": \"your task\"}}'",
            description="Create a development plan for a task",
        ),
        EndpointSummary(
            path="/api/v1/workflow/execute/{{plan_id}}",
            method="POST",
            auth_required=True,
            curl_example=f"curl -X POST -H 'X-API-Key: $API_KEY' {BASE_URL}/api/v1/workflow/execute/{{plan_id}}",
            description="Execute a development plan",
        ),
        EndpointSummary(
            path="/api/v1/workflow/verify/{{execute_id}}",
            method="POST",
            auth_required=True,
            curl_example=f"curl -X POST -H 'X-API-Key: $API_KEY' {BASE_URL}/api/v1/workflow/verify/{{execute_id}}",
            description="Run tests and verify implementation",
        ),
        EndpointSummary(
            path="/api/v1/workflow/ship/{{verify_id}}",
            method="POST",
            auth_required=True,
            request_body='{"branch": "feature/x", "commit_message": "Add X"}',
            curl_example=f"curl -X POST {BASE_URL}/api/v1/workflow/ship/{{verify_id}} "
            f"-H 'X-API-Key: $API_KEY' "
            f"-H 'Content-Type: application/json' "
            f"-d '{{\"branch\": \"feature/x\", \"commit_message\": \"Add X\"}}'",
            description="Ship the implementation (commit and push)",
        ),
        EndpointSummary(
            path="/api/v1/workflow/status",
            method="GET",
            auth_required=True,
            curl_example=f"curl -H 'X-API-Key: $API_KEY' {BASE_URL}/api/v1/workflow/status",
            description="Get current workflow status",
        ),
        # Memory endpoints
        EndpointSummary(
            path="/api/v1/memory",
            method="POST",
            auth_required=True,
            request_body='{"content": "observation text"}',
            curl_example=f"curl -X POST {BASE_URL}/api/v1/memory "
            f"-H 'X-API-Key: $API_KEY' "
            f"-H 'Content-Type: application/json' "
            f"-d '{{\"content\": \"your observation\"}}'",
            description="Save an observation to memory",
        ),
        EndpointSummary(
            path="/api/v1/memory/search",
            method="GET",
            auth_required=True,
            curl_example=f"curl -H 'X-API-Key: $API_KEY' '{BASE_URL}/api/v1/memory/search?q=query'",
            description="Search memory observations",
        ),
        # Discovery endpoints
        EndpointSummary(
            path="/api/v1/discovery",
            method="GET",
            auth_required=True,
            curl_example=f"curl -H 'X-API-Key: $API_KEY' {BASE_URL}/api/v1/discovery",
            description="Get API overview card",
        ),
        EndpointSummary(
            path="/api/v1/discovery/workflows",
            method="GET",
            auth_required=True,
            curl_example=f"curl -H 'X-API-Key: $API_KEY' {BASE_URL}/api/v1/discovery/workflows",
            description="Get available workflow recipes",
        ),
        EndpointSummary(
            path="/api/v1/discovery/errors/{{status_code}}",
            method="GET",
            auth_required=True,
            curl_example=f"curl -H 'X-API-Key: $API_KEY' {BASE_URL}/api/v1/discovery/errors/401",
            description="Get error recovery guidance",
        ),
    ]


def _build_agent_backend_info() -> list[AgentBackendInfo]:
    """Build list of agent backend info."""
    all_backends = list_all_backends()
    available_backends = get_available_backends()

    result = []
    for name in all_backends:
        backend = next((b for b in available_backends if b.name == name), None)
        if backend:
            result.append(
                AgentBackendInfo(
                    name=backend.name,
                    display_name=backend.display_name,
                    available=True,
                )
            )
        else:
            # Backend is registered but not available
            from src.infrastructure.agent_backends import get_backend

            b = get_backend(name)
            if b:
                result.append(
                    AgentBackendInfo(
                        name=b.name,
                        display_name=b.display_name,
                        available=False,
                    )
                )

    return result


# Error guidance templates
_ERROR_GUIDANCE: dict[int, ErrorGuidance] = {
    400: ErrorGuidance(
        status_code=400,
        title="Bad Request",
        description="The request was malformed or contained invalid parameters",
        recovery_steps=[
            "Check request body format matches the expected schema",
            "Ensure all required fields are included",
            "Validate field types (string, number, boolean)",
            "Check for JSON syntax errors in request body",
        ],
    ),
    401: ErrorGuidance(
        status_code=401,
        title="Unauthorized",
        description="API key is missing or invalid",
        recovery_steps=[
            "Ensure X-API-Key header is included in all requests",
            "Verify the API key is correct and not expired",
            "Check that the API key has the required permissions",
            "Request a new API key if the current one is invalid",
        ],
        example_curl=f"curl -H 'X-API-Key: your-api-key' {BASE_URL}/api/v1/agents/sessions",
    ),
    404: ErrorGuidance(
        status_code=404,
        title="Not Found",
        description="The requested resource was not found",
        recovery_steps=[
            "Verify the resource ID in the URL is correct",
            "Check if the resource has been deleted",
            "Ensure you're using the correct endpoint path",
            "List available resources to find the correct ID",
        ],
    ),
    409: ErrorGuidance(
        status_code=409,
        title="Conflict",
        description="The request conflicts with the current state of the resource",
        recovery_steps=[
            "Check if the resource already exists",
            "Verify the resource is not in a conflicting state",
            "Get current resource state and resolve conflicts",
            "Retry after resolving the conflict",
        ],
    ),
    429: ErrorGuidance(
        status_code=429,
        title="Too Many Requests",
        description="Rate limit exceeded",
        recovery_steps=[
            "Wait before making more requests",
            "Implement exponential backoff in your client",
            "Reduce request frequency",
            "Check Retry-After header for wait time",
        ],
    ),
    500: ErrorGuidance(
        status_code=500,
        title="Internal Server Error",
        description="An unexpected error occurred on the server",
        recovery_steps=[
            "Retry the request after a short delay",
            "Check server logs for error details",
            "Report the issue if it persists",
            "Use health endpoint to check server status",
        ],
    ),
    503: ErrorGuidance(
        status_code=503,
        title="Service Unavailable",
        description="The service is temporarily unavailable",
        recovery_steps=[
            "Wait and retry the request",
            "Check /api/v1/health endpoint for service status",
            "Verify agent backends are installed (for agent endpoints)",
            "Contact administrator if issue persists",
        ],
        example_curl=f"curl {BASE_URL}/api/v1/health",
    ),
}

# Default guidance for unknown errors
_DEFAULT_ERROR_GUIDANCE = ErrorGuidance(
    status_code=0,
    title="Unknown Error",
    description="An unexpected error occurred",
    recovery_steps=[
        "Check the error response body for details",
        "Verify your request format is correct",
        "Try the request again",
        "Check the API documentation",
        "Contact support if the issue persists",
    ],
)


def _build_error_guidance(status_code: int) -> ErrorGuidance:
    """Get error guidance for a specific status code."""
    if status_code in _ERROR_GUIDANCE:
        guidance = _ERROR_GUIDANCE[status_code].model_copy()
        # Update status_code to match requested
        guidance.status_code = status_code
        return guidance

    # Return generic guidance with the actual status code
    guidance = _DEFAULT_ERROR_GUIDANCE.model_copy()
    guidance.status_code = status_code
    return guidance


# Workflow recipes
_WORKFLOW_RECIPES: list[WorkflowCardData] = [
    WorkflowCardData(
        workflow_id="full-development-cycle",
        name="Full Development Cycle",
        description="Complete development workflow from planning to shipping. Use for implementing new features or making significant changes.",
        steps=[
            WorkflowStep(
                step_number=1,
                action="outline",
                endpoint="POST /api/v1/workflow/outline",
                description="Create a detailed plan for the task",
                request_body='{"task": "Describe what you want to implement"}',
            ),
            WorkflowStep(
                step_number=2,
                action="execute",
                endpoint="POST /api/v1/workflow/execute/{plan_id}",
                description="Execute the plan - implements the code",
            ),
            WorkflowStep(
                step_number=3,
                action="verify",
                endpoint="POST /api/v1/workflow/verify/{execute_id}",
                description="Run tests and verify the implementation works",
            ),
            WorkflowStep(
                step_number=4,
                action="ship",
                endpoint="POST /api/v1/workflow/ship/{verify_id}",
                description="Ship the changes - commit and push to remote",
                request_body='{"branch": "feature/your-feature", "commit_message": "Your message"}',
            ),
        ],
    ),
    WorkflowCardData(
        workflow_id="quick-agent-session",
        name="Quick Agent Session",
        description="Start an agent session to work on a task. Useful for ad-hoc work that doesn't need full workflow tracking.",
        steps=[
            WorkflowStep(
                step_number=1,
                action="create",
                endpoint="POST /api/v1/agents/sessions",
                description="Create a new agent session with your task",
                request_body='{"agent_type": "opencode", "task": "Your task description", "tmux": true}',
            ),
            WorkflowStep(
                step_number=2,
                action="check",
                endpoint="GET /api/v1/agents/sessions/{session_id}",
                description="Check the session status and output",
            ),
            WorkflowStep(
                step_number=3,
                action="cleanup",
                endpoint="DELETE /api/v1/agents/sessions/{session_id}",
                description="Clean up the session when done",
            ),
        ],
    ),
    WorkflowCardData(
        workflow_id="memory-assisted-development",
        name="Memory-Assisted Development",
        description="Use the memory system to store context and observations during development. Useful for long-running tasks.",
        steps=[
            WorkflowStep(
                step_number=1,
                action="save-observation",
                endpoint="POST /api/v1/memory",
                description="Save an observation or insight to memory",
                request_body='{"content": "Important context to remember"}',
            ),
            WorkflowStep(
                step_number=2,
                action="search-memory",
                endpoint="GET /api/v1/memory/search?q={query}",
                description="Search for relevant past observations",
            ),
            WorkflowStep(
                step_number=3,
                action="create-agent",
                endpoint="POST /api/v1/agents/sessions",
                description="Create agent with task context from memory",
                request_body='{"agent_type": "opencode", "task": "Task with context from memory"}',
            ),
        ],
    ),
]


def _build_workflow_cards() -> list[WorkflowCardData]:
    """Get all workflow recipes."""
    return _WORKFLOW_RECIPES.copy()


@router.get("", response_model=DiscoveryCardEnvelope)
async def get_discovery_overview(
    _: str = Depends(verify_api_key),
) -> DiscoveryCardEnvelope:
    """Get the main discovery card with API overview.

    This endpoint provides a concise, LLM-optimized summary of the API
    including authentication, available endpoints, and agent backends.
    """
    logger.info("Discovery overview requested")

    overview_data = OverviewCardData(
        api_name="Fork Agent API",
        version="1.0.0",
        base_url=BASE_URL,
        auth=_build_auth_info(),
        endpoints=_build_endpoint_summaries(),
        available_agents=_build_agent_backend_info(),
        common_errors=[401, 404, 409, 429, 503],
    )

    return DiscoveryCardEnvelope(
        card_type=CardType.OVERVIEW,
        version="1.0.0",
        data=overview_data,
        quick_actions=[
            "GET /api/v1/health - Check backends and health",
            "POST /api/v1/agents/sessions - Start an agent",
            "POST /api/v1/workflow/outline - Create a plan",
        ],
    )


@router.get("/workflows", response_model=WorkflowListResponse)
async def get_workflow_cards(
    _: str = Depends(verify_api_key),
) -> WorkflowListResponse:
    """Get available workflow recipes.

    Returns predefined workflow recipes that can be followed
    to accomplish common tasks using the API.
    """
    logger.info("Discovery workflows requested")

    return WorkflowListResponse(workflows=_build_workflow_cards())


@router.get("/errors/{status_code}", response_model=DiscoveryCardEnvelope)
async def get_error_guidance(
    status_code: int,
    _: str = Depends(verify_api_key),
) -> DiscoveryCardEnvelope:
    """Get guidance for recovering from a specific error.

    Args:
        status_code: HTTP status code to get guidance for.

    Returns a card with recovery steps and examples for the error.
    """
    logger.info(f"Error guidance requested for status code: {status_code}")

    guidance = _build_error_guidance(status_code)

    return DiscoveryCardEnvelope(
        card_type=CardType.ERROR,
        cache_ttl=86400,  # Cache for 24 hours
        data=guidance,
        quick_actions=[
            "GET /api/v1/health - Check service status",
            "GET /api/v1/discovery - View API overview",
        ],
    )
