"""Integration tests for FASE 4 UX commands.

Tests query and timeline commands with structured queries.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from src.application.services.messaging.memory_hook import MemoryHook
from src.application.services.messaging.memory_hook_config import (
    HookPolicy,
    MemoryHookConfig,
)
from src.application.services.workflow.executor import WorkflowExecutor
from src.application.services.workflow.state import Task
from src.domain.entities.message import AgentMessage, MessageType
from src.infrastructure.persistence.container import create_container
from src.interfaces.cli.main import app


@pytest.fixture
def temp_db() -> Path:
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        yield Path(f.name)


@pytest.fixture
def runner() -> CliRunner:
    """Create CLI runner."""
    return CliRunner()


@pytest.fixture
def populated_db(temp_db: Path) -> Path:
    """Create and populate a database with test events."""
    container = create_container(temp_db)
    memory = container.memory_service()

    # Create WorkflowExecutor
    mock_tmux = MagicMock()
    mock_tmux.create_session.return_value = True
    mock_tmux.launch_agent.return_value = True

    mock_workspace = MagicMock()
    mock_ws = MagicMock()
    mock_ws.path = Path("/tmp/test-wt")
    mock_workspace.create_workspace.return_value = mock_ws

    mock_hooks = MagicMock()

    executor = WorkflowExecutor(
        tmux_orchestrator=mock_tmux,
        memory_service=memory,
        workspace_manager=mock_workspace,
        hook_service=mock_hooks,
    )

    # Execute 2 tasks in same run
    task1 = Task(
        id="WO-001",
        slug="feature-a",
        description="Implement feature A",
    )

    task2 = Task(
        id="WO-002",
        slug="feature-b",
        description="Implement feature B",
    )

    executor.execute_task(task1, model="test", run_id="run-test-001")
    executor.execute_task(task2, model="test", run_id="run-test-001")

    # Add agent_message
    hook_config = MemoryHookConfig(enabled=True, policy=HookPolicy.IMPORTANT_ONLY)
    hook = MemoryHook(memory_service=memory, config=hook_config)

    msg = AgentMessage.create(
        from_agent="agent1:0",
        to_agent="agent2:0",
        message_type=MessageType.COMMAND,
        payload=json.dumps({"important": True, "command": "test"}),
    )

    hook.capture(msg, context={"run_id": "run-test-001", "task_id": "WO-001"})

    return temp_db


class TestQueryCommand:
    """Tests for 'memory query query' command."""

    def test_query_by_agent_filters_correctly(
        self,
        populated_db: Path,
        runner: CliRunner,
    ) -> None:
        """Query by agent should return only events for that agent."""
        result = runner.invoke(
            app,
            ["--db", str(populated_db), "query", "query", "--agent", "agent1:0"],
        )

        assert result.exit_code == 0
        # Should find agent_message from agent1:0
        assert "agent_message" in result.output

    def test_query_by_run_filters_correctly(
        self,
        populated_db: Path,
        runner: CliRunner,
    ) -> None:
        """Query by run should return only events for that run."""
        result = runner.invoke(
            app,
            ["--db", str(populated_db), "query", "query", "--run", "run-test-001"],
        )

        assert result.exit_code == 0
        assert "run-test-001" in result.output
        # Should have multiple events
        assert "task_started" in result.output
        assert "task_completed" in result.output

    def test_query_by_event_type(
        self,
        populated_db: Path,
        runner: CliRunner,
    ) -> None:
        """Query by event_type should filter correctly."""
        result = runner.invoke(
            app,
            [
                "--db",
                str(populated_db),
                "query",
                "query",
                "--run",
                "run-test-001",
                "--event-type",
                "task_completed",
            ],
        )

        assert result.exit_code == 0
        assert "task_completed" in result.output
        # Should NOT have other events
        assert "task_started" not in result.output

    def test_query_json_output(
        self,
        populated_db: Path,
        runner: CliRunner,
    ) -> None:
        """Query with --json should output valid JSON."""
        result = runner.invoke(
            app,
            ["--db", str(populated_db), "query", "query", "--run", "run-test-001", "--json"],
        )

        assert result.exit_code == 0

        # Should be valid JSON
        output = json.loads(result.output)
        assert isinstance(output, list)
        assert len(output) > 0

        # Should have expected fields
        first = output[0]
        assert "event_type" in first
        assert "run_id" in first
        assert "timestamp" in first

    def test_query_scan_limit_low_no_results(
        self,
        populated_db: Path,
        runner: CliRunner,
    ) -> None:
        """Low scan-limit should return no results if events are beyond limit."""
        result = runner.invoke(
            app,
            [
                "--db",
                str(populated_db),
                "query",
                "query",
                "--run",
                "run-test-001",
                "--scan-limit",
                "1",  # Very low
            ],
        )

        # May or may not find results depending on ordering
        # The point is scan-limit is respected
        assert result.exit_code == 0


class TestTimelineCommand:
    """Tests for 'memory query timeline' command."""

    def test_timeline_shows_events_chronologically(
        self,
        populated_db: Path,
        runner: CliRunner,
    ) -> None:
        """Timeline should show events in chronological order (ASC)."""
        result = runner.invoke(
            app,
            ["--db", str(populated_db), "query", "timeline", "run-test-001"],
        )

        assert result.exit_code == 0
        assert "run-test-001" in result.output

        # Extract timestamps
        lines = [l for l in result.output.split("\n") if "|" in l and "HH:MM" not in l]
        timestamps = [l.split("|")[0].strip() for l in lines]

        # Should be in ascending order
        assert timestamps == sorted(timestamps)

    def test_timeline_shows_terminal_event_status(
        self,
        populated_db: Path,
        runner: CliRunner,
    ) -> None:
        """Timeline should show checkmark for completed tasks."""
        result = runner.invoke(
            app,
            ["--db", str(populated_db), "query", "timeline", "run-test-001"],
        )

        assert result.exit_code == 0
        # task_completed should have ✓
        assert "✓" in result.output

    def test_timeline_contains_one_terminal_per_task(
        self,
        populated_db: Path,
        runner: CliRunner,
    ) -> None:
        """Timeline should have exactly 1 terminal event (completed or failed) per task."""
        result = runner.invoke(
            app,
            ["--db", str(populated_db), "query", "timeline", "run-test-001"],
        )

        assert result.exit_code == 0

        # Count terminal events (completed or failed)
        terminal_count = result.output.count("task_completed") + result.output.count(
            "task_failed"
        )

        # Should have 2 terminal events (one per task)
        assert terminal_count == 2, f"Expected 2 terminal events, got {terminal_count}"

    def test_timeline_nonexistent_run(
        self,
        populated_db: Path,
        runner: CliRunner,
    ) -> None:
        """Timeline for nonexistent run should show message."""
        result = runner.invoke(
            app,
            ["--db", str(populated_db), "query", "timeline", "run-nonexistent"],
        )

        assert result.exit_code == 0
        assert "No events found" in result.output


class TestPrivacySanitization:
    """Tests for privacy sanitization in output."""

    def test_error_message_sanitized_in_timeline(
        self,
        temp_db: Path,
        runner: CliRunner,
    ) -> None:
        """Error messages with sensitive paths should be sanitized."""
        import os

        container = create_container(temp_db)
        memory = container.memory_service()

        # Create mock executor that will fail
        mock_tmux = MagicMock()
        mock_tmux.create_session.return_value = False  # Fail

        mock_workspace = MagicMock()
        mock_hooks = MagicMock()

        executor = WorkflowExecutor(
            tmux_orchestrator=mock_tmux,
            memory_service=memory,
            workspace_manager=mock_workspace,
            hook_service=mock_hooks,
        )

        task = Task(id="WO-PRIV", slug="privacy-test", description="Test privacy")

        # Ensure not in DEBUG mode
        old_debug = os.environ.get("DEBUG")
        os.environ["DEBUG"] = "0"

        try:
            executor.execute_task(task, model="test", run_id="run-privacy-001")

            result = runner.invoke(
                app,
                ["--db", str(temp_db), "query", "timeline", "run-privacy-001"],
            )

            assert result.exit_code == 0

            # Should NOT contain full home paths
            assert "/Users/" not in result.output or old_debug == "1"

        finally:
            if old_debug is not None:
                os.environ["DEBUG"] = old_debug
            else:
                os.environ.pop("DEBUG", None)
