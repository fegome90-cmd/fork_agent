"""HTTP client for branch-review API."""

from __future__ import annotations

import logging
import os
from typing import Any, cast

import httpx

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_BASE_URL = "http://localhost:3001"
DEFAULT_TIMEOUT = 130.0  # Slightly longer than branch-review's 120s command timeout


class BranchReviewClient:
    """Client for branch-review API.

    Provides methods to interact with the branch-review service
    for multi-agent code review orchestration.
    """

    def _request_json(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Execute request and normalize branch-review envelope.

        Raises BranchReviewError with API code/message for expected failures.
        """
        response = self.client.request(method, path, **kwargs)

        try:
            payload = response.json()
        except Exception:
            payload = {
                "data": None,
                "error": {"code": "INVALID_RESPONSE", "message": response.text},
            }

        if response.status_code >= 400:
            error = payload.get("error") if isinstance(payload, dict) else None
            if error:
                raise BranchReviewError(
                    error.get("code", f"HTTP_{response.status_code}"),
                    error.get("message", "Request failed"),
                )
            raise BranchReviewError(
                f"HTTP_{response.status_code}", f"Request failed: {response.reason_phrase}"
            )

        if isinstance(payload, dict) and payload.get("error"):
            error = payload["error"]
            raise BranchReviewError(
                error.get("code", "UNKNOWN_ERROR"), error.get("message", "Request failed")
            )

        if isinstance(payload, dict):
            return cast(dict[str, Any], payload.get("data", payload))

        return {"result": payload}

    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the client.

        Args:
            base_url: API base URL (defaults to BRANCH_REVIEW_URL env or localhost:3001)
            token: Auth token (defaults to BRANCH_REVIEW_TOKEN env)
            timeout: Request timeout in seconds
        """
        self.base_url = (base_url or os.getenv("BRANCH_REVIEW_URL", DEFAULT_BASE_URL) or DEFAULT_BASE_URL).rstrip("/")
        self.token = token or os.getenv("BRANCH_REVIEW_TOKEN", "")
        self.timeout = timeout
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            headers = {}
            if self.token:
                headers["X-Review-Token"] = self.token

            self._client = httpx.Client(
                base_url=self.base_url,
                headers=headers,
                timeout=self.timeout,
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self) -> BranchReviewClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # --- Discovery ---

    def get_info(self) -> dict[str, Any]:
        """Get API metadata (public endpoint, no auth required).

        Returns:
            API info including endpoints, rate limits, workflow.
        """
        return self._request_json("GET", "/api/review/info")

    # --- Run Status ---

    def get_run(self) -> dict[str, Any]:
        """Get current run status.

        Returns:
            Current run data or error.
        """
        return self._request_json("GET", "/api/review/run")

    def get_state(self) -> dict[str, Any]:
        """Get run state snapshot.

        Returns:
            State snapshot data.
        """
        return self._request_json("GET", "/api/review/state")

    def get_final(self, run_id: str) -> dict[str, Any]:
        """Get final verdict for a run.

        Args:
            run_id: The run identifier.

        Returns:
            Final verdict data.
        """
        return self._request_json("GET", "/api/review/final", params={"runId": run_id})

    # --- Commands ---

    ALLOWED_COMMANDS = ["init", "explore", "plan", "run", "ingest", "verdict", "merge", "cleanup"]

    def execute_command(
        self,
        command: str,
        args: dict[str, str | int | bool] | None = None,
    ) -> dict[str, Any]:
        """Execute a reviewctl command.

        Args:
            command: Command name (init, explore, plan, run, ingest, verdict, merge, cleanup)
            args: Optional command arguments.

        Returns:
            Command output.

        Raises:
            BranchReviewError: If the command fails.
            ValueError: If command is not allowed.
        """
        if command not in self.ALLOWED_COMMANDS:
            raise ValueError(
                f"Invalid command: {command}. Allowed: {', '.join(self.ALLOWED_COMMANDS)}"
            )

        payload = {"command": command, "args": args or {}}

        return self._request_json("POST", "/api/review/command", json=payload)

    # --- Convenience methods for workflow ---

    def init_run(self) -> dict[str, Any]:
        """Initialize a new review run."""
        return self.execute_command("init")

    def explore_context(self) -> dict[str, Any]:
        """Explore repository context."""
        return self.execute_command("explore", {"mode": "context"})

    def explore_diff(self) -> dict[str, Any]:
        """Explore branch diff."""
        return self.execute_command("explore", {"mode": "diff"})

    def plan_review(self) -> dict[str, Any]:
        """Generate review plan."""
        return self.execute_command("plan")

    def run_agents(self) -> dict[str, Any]:
        """Create handoff requests for agents."""
        return self.execute_command("run")

    def ingest_agent(self, agent: str) -> dict[str, Any]:
        """Ingest agent output.

        Args:
            agent: Agent name (e.g., 'code-reviewer', 'code-simplifier').
        """
        return self.execute_command("ingest", {"agent": agent})

    def generate_verdict(self) -> dict[str, Any]:
        """Generate final verdict."""
        return self.execute_command("verdict")

    def merge_branch(self) -> dict[str, Any]:
        """Merge the reviewed branch."""
        return self.execute_command("merge")

    def cleanup(self) -> dict[str, Any]:
        """Clean up run artifacts."""
        return self.execute_command("cleanup")

    # --- Full workflow ---

    def run_full_review(self, agents: list[str] | None = None) -> dict[str, Any]:
        """Run a complete review workflow.

        Args:
            agents: List of agents to ingest (default: ['code-reviewer']).

        Returns:
            Final verdict.
        """
        agents = agents or ["code-reviewer"]

        logger.info("Starting full review workflow")

        # 1. Init
        result = self.init_run()
        logger.info(f"Init: {result.get('output', '')[:100]}")

        # 2. Explore context
        result = self.explore_context()
        logger.info(f"Explore context: {result.get('output', '')[:100]}")

        # 3. Explore diff
        result = self.explore_diff()
        logger.info(f"Explore diff: {result.get('output', '')[:100]}")

        # 4. Plan
        result = self.plan_review()
        logger.info(f"Plan: {result.get('output', '')[:100]}")

        # 5. Run agents
        result = self.run_agents()
        logger.info(f"Run: {result.get('output', '')[:100]}")

        # 6. Ingest each agent
        for agent in agents:
            result = self.ingest_agent(agent)
            logger.info(f"Ingest {agent}: {result.get('output', '')[:100]}")

        # 7. Verdict
        result = self.generate_verdict()
        logger.info(f"Verdict: {result.get('output', '')[:100]}")

        # 8. Get final
        run_data = self.get_run()
        run_id = run_data.get("run", {}).get("runId")

        if run_id:
            return self.get_final(run_id)

        return {"verdict": "unknown", "message": "Could not retrieve final verdict"}


class BranchReviewError(Exception):
    """Error from branch-review API."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")
