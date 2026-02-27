"""Unit tests for discovery models."""

from datetime import datetime

from src.interfaces.api.models.discovery import (
    AgentBackendInfo,
    AuthInfo,
    CardType,
    DiscoveryCardEnvelope,
    EndpointSummary,
    ErrorGuidance,
    OverviewCardData,
    WorkflowCardData,
    WorkflowStep,
)


class TestCardType:
    """Tests for CardType enum."""

    def test_card_type_has_overview(self) -> None:
        """CardType should have OVERVIEW value."""
        assert CardType.OVERVIEW == "overview"

    def test_card_type_has_workflow(self) -> None:
        """CardType should have WORKFLOW value."""
        assert CardType.WORKFLOW == "workflow"

    def test_card_type_has_error(self) -> None:
        """CardType should have ERROR value."""
        assert CardType.ERROR == "error"


class TestAuthInfo:
    """Tests for AuthInfo model."""

    def test_auth_info_creates_with_required_fields(self) -> None:
        """AuthInfo should create with required fields."""
        auth = AuthInfo(
            type="api_key",
            header="X-API-Key",
            example="X-API-Key: your-key-here",
        )
        assert auth.type == "api_key"
        assert auth.header == "X-API-Key"
        assert auth.example == "X-API-Key: your-key-here"

    def test_auth_info_optional_description(self) -> None:
        """AuthInfo should accept optional description."""
        auth = AuthInfo(
            type="api_key",
            header="X-API-Key",
            example="X-API-Key: your-key-here",
            description="API key authentication",
        )
        assert auth.description == "API key authentication"


class TestEndpointSummary:
    """Tests for EndpointSummary model."""

    def test_endpoint_summary_creates_with_required_fields(self) -> None:
        """EndpointSummary should create with required fields."""
        endpoint = EndpointSummary(
            path="/api/v1/health",
            method="GET",
            auth_required=False,
            curl_example="curl http://localhost:8080/api/v1/health",
        )
        assert endpoint.path == "/api/v1/health"
        assert endpoint.method == "GET"
        assert endpoint.auth_required is False
        assert endpoint.curl_example == "curl http://localhost:8080/api/v1/health"

    def test_endpoint_summary_optional_fields(self) -> None:
        """EndpointSummary should accept optional fields."""
        endpoint = EndpointSummary(
            path="/api/v1/agents/sessions",
            method="POST",
            auth_required=True,
            request_body='{"task": "implement X"}',
            curl_example="curl -X POST http://localhost:8080/api/v1/agents/sessions -H 'X-API-Key: $API_KEY' -d '{\"task\": \"...\"}'",
            description="Create agent session",
        )
        assert endpoint.request_body == '{"task": "implement X"}'
        assert endpoint.description == "Create agent session"


class TestAgentBackendInfo:
    """Tests for AgentBackendInfo model."""

    def test_agent_backend_info_creates_with_required_fields(self) -> None:
        """AgentBackendInfo should create with required fields."""
        backend = AgentBackendInfo(
            name="opencode",
            display_name="OpenCode CLI",
            available=True,
        )
        assert backend.name == "opencode"
        assert backend.display_name == "OpenCode CLI"
        assert backend.available is True

    def test_agent_backend_info_unavailable(self) -> None:
        """AgentBackendInfo should represent unavailable backends."""
        backend = AgentBackendInfo(
            name="pi",
            display_name="pi.dev Agent",
            available=False,
        )
        assert backend.available is False


class TestWorkflowStep:
    """Tests for WorkflowStep model."""

    def test_workflow_step_creates_with_required_fields(self) -> None:
        """WorkflowStep should create with required fields."""
        step = WorkflowStep(
            step_number=1,
            action="outline",
            endpoint="POST /api/v1/workflow/outline",
            description="Create a plan for the task",
        )
        assert step.step_number == 1
        assert step.action == "outline"
        assert step.endpoint == "POST /api/v1/workflow/outline"
        assert step.description == "Create a plan for the task"

    def test_workflow_step_optional_request_body(self) -> None:
        """WorkflowStep should accept optional request body."""
        step = WorkflowStep(
            step_number=1,
            action="outline",
            endpoint="POST /api/v1/workflow/outline",
            description="Create a plan",
            request_body='{"task": "implement feature X"}',
        )
        assert step.request_body == '{"task": "implement feature X"}'


class TestWorkflowCardData:
    """Tests for WorkflowCardData model."""

    def test_workflow_card_data_creates_with_required_fields(self) -> None:
        """WorkflowCardData should create with required fields."""
        workflow = WorkflowCardData(
            workflow_id="full-development-cycle",
            name="Full Development Cycle",
            description="Complete development workflow from planning to shipping",
            steps=[
                WorkflowStep(
                    step_number=1,
                    action="outline",
                    endpoint="POST /api/v1/workflow/outline",
                    description="Create plan",
                ),
            ],
        )
        assert workflow.workflow_id == "full-development-cycle"
        assert workflow.name == "Full Development Cycle"
        assert len(workflow.steps) == 1

    def test_workflow_card_data_multiple_steps(self) -> None:
        """WorkflowCardData should handle multiple steps."""
        workflow = WorkflowCardData(
            workflow_id="quick-agent-session",
            name="Quick Agent Session",
            description="Start and manage an agent session",
            steps=[
                WorkflowStep(
                    step_number=1,
                    action="create",
                    endpoint="POST /api/v1/agents/sessions",
                    description="Create session",
                ),
                WorkflowStep(
                    step_number=2,
                    action="check",
                    endpoint="GET /api/v1/agents/sessions/{session_id}",
                    description="Check status",
                ),
            ],
        )
        assert len(workflow.steps) == 2


class TestErrorGuidance:
    """Tests for ErrorGuidance model."""

    def test_error_guidance_creates_with_required_fields(self) -> None:
        """ErrorGuidance should create with required fields."""
        guidance = ErrorGuidance(
            status_code=401,
            title="Unauthorized",
            description="API key is missing or invalid",
            recovery_steps=[
                "Ensure X-API-Key header is included",
                "Verify API key is correct",
            ],
        )
        assert guidance.status_code == 401
        assert guidance.title == "Unauthorized"
        assert len(guidance.recovery_steps) == 2

    def test_error_guidance_optional_example(self) -> None:
        """ErrorGuidance should accept optional curl example."""
        guidance = ErrorGuidance(
            status_code=401,
            title="Unauthorized",
            description="API key is missing or invalid",
            recovery_steps=["Add X-API-Key header"],
            example_curl="curl -H 'X-API-Key: your-key' http://localhost:8080/api/v1/agents/sessions",
        )
        assert guidance.example_curl is not None


class TestOverviewCardData:
    """Tests for OverviewCardData model."""

    def test_overview_card_data_creates_with_required_fields(self) -> None:
        """OverviewCardData should create with required fields."""
        overview = OverviewCardData(
            api_name="Fork Agent API",
            version="1.0.0",
            base_url="http://localhost:8080",
            auth=AuthInfo(
                type="api_key",
                header="X-API-Key",
                example="X-API-Key: your-key",
            ),
            endpoints=[
                EndpointSummary(
                    path="/api/v1/health",
                    method="GET",
                    auth_required=False,
                    curl_example="curl http://localhost:8080/api/v1/health",
                ),
            ],
        )
        assert overview.api_name == "Fork Agent API"
        assert overview.version == "1.0.0"
        assert len(overview.endpoints) == 1

    def test_overview_card_data_with_backends(self) -> None:
        """OverviewCardData should accept available backends."""
        overview = OverviewCardData(
            api_name="Fork Agent API",
            version="1.0.0",
            base_url="http://localhost:8080",
            auth=AuthInfo(
                type="api_key",
                header="X-API-Key",
                example="X-API-Key: key",
            ),
            endpoints=[],
            available_agents=[
                AgentBackendInfo(name="opencode", display_name="OpenCode CLI", available=True),
                AgentBackendInfo(name="pi", display_name="pi.dev Agent", available=False),
            ],
        )
        assert len(overview.available_agents) == 2

    def test_overview_card_data_with_common_errors(self) -> None:
        """OverviewCardData should accept common error codes."""
        overview = OverviewCardData(
            api_name="Fork Agent API",
            version="1.0.0",
            base_url="http://localhost:8080",
            auth=AuthInfo(
                type="api_key",
                header="X-API-Key",
                example="X-API-Key: key",
            ),
            endpoints=[],
            common_errors=[401, 404, 429, 503],
        )
        assert overview.common_errors == [401, 404, 429, 503]


class TestDiscoveryCardEnvelope:
    """Tests for DiscoveryCardEnvelope model."""

    def test_overview_envelope(self) -> None:
        """DiscoveryCardEnvelope should wrap overview card."""
        envelope = DiscoveryCardEnvelope(
            card_type=CardType.OVERVIEW,
            version="1.0.0",
            generated_at=datetime.now(),
            cache_ttl=3600,
            data=OverviewCardData(
                api_name="Fork Agent API",
                version="1.0.0",
                base_url="http://localhost:8080",
                auth=AuthInfo(
                    type="api_key",
                    header="X-API-Key",
                    example="X-API-Key: key",
                ),
                endpoints=[],
            ),
            quick_actions=["GET /api/v1/health"],
        )
        assert envelope.card_type == CardType.OVERVIEW
        assert envelope.version == "1.0.0"
        assert envelope.cache_ttl == 3600
        assert envelope.quick_actions == ["GET /api/v1/health"]

    def test_workflow_envelope(self) -> None:
        """DiscoveryCardEnvelope should wrap workflow card."""
        envelope = DiscoveryCardEnvelope(
            card_type=CardType.WORKFLOW,
            version="1.0.0",
            generated_at=datetime.now(),
            cache_ttl=3600,
            data=WorkflowCardData(
                workflow_id="test-workflow",
                name="Test Workflow",
                description="A test workflow",
                steps=[],
            ),
        )
        assert envelope.card_type == CardType.WORKFLOW

    def test_error_envelope(self) -> None:
        """DiscoveryCardEnvelope should wrap error guidance."""
        envelope = DiscoveryCardEnvelope(
            card_type=CardType.ERROR,
            version="1.0.0",
            generated_at=datetime.now(),
            cache_ttl=86400,
            data=ErrorGuidance(
                status_code=401,
                title="Unauthorized",
                description="Invalid API key",
                recovery_steps=["Check API key"],
            ),
        )
        assert envelope.card_type == CardType.ERROR
