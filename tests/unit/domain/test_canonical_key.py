"""Tests for canonical launch key construction — SSOT."""

from __future__ import annotations

from src.domain.services.canonical_key import (
    _sanitize,
    build_api_key,
    build_manager_key,
    build_task_key,
    build_workflow_key,
)


class TestBuildApiKey:
    """API namespace: api:{agent_type}:{sha256_12hex|untitled}"""

    def test_normal_task_produces_hash(self) -> None:
        key = build_api_key("openai-codex", "implement feature X")
        assert key.startswith("api:openai-codex:")
        # 12 hex chars after agent_type
        parts = key.split(":")
        assert len(parts) == 3
        assert len(parts[2]) == 12

    def test_empty_task_produces_untitled(self) -> None:
        key = build_api_key("openai-codex", "")
        assert key == "api:openai-codex:untitled"

    def test_none_task_produces_untitled(self) -> None:
        key = build_api_key("openai-codex", None)
        assert key == "api:openai-codex:untitled"

    def test_deterministic(self) -> None:
        key1 = build_api_key("openai-codex", "same task")
        key2 = build_api_key("openai-codex", "same task")
        assert key1 == key2

    def test_different_tasks_different_keys(self) -> None:
        key1 = build_api_key("openai-codex", "task A")
        key2 = build_api_key("openai-codex", "task B")
        assert key1 != key2

    def test_different_agents_different_keys(self) -> None:
        key1 = build_api_key("agent-a", "same task")
        key2 = build_api_key("agent-b", "same task")
        assert key1 != key2


class TestBuildTaskKey:
    """Task namespace: task:{task_id}"""

    def test_normal(self) -> None:
        key = build_task_key("abc-123")
        assert key == "task:abc-123"

    def test_empty_id(self) -> None:
        key = build_task_key("")
        assert key == "task:"

    def test_tab_stripped(self) -> None:
        key = build_task_key("task\twith\ttabs")
        assert "\t" not in key

    def test_carriage_return_stripped(self) -> None:
        key = build_task_key("hello\rworld")
        assert "\r" not in key


class TestBuildManagerKey:
    """Manager namespace: manager:{agent_name}"""

    def test_normal(self) -> None:
        key = build_manager_key("explorer-01")
        assert key == "manager:explorer-01"


class TestBuildWorkflowKey:
    """Workflow namespace: workflow:{task_id}"""

    def test_normal(self) -> None:
        key = build_workflow_key("task-456")
        assert key == "workflow:task-456"


class TestNamespaceSeparation:
    """Different namespaces never collide."""

    def test_api_vs_task(self) -> None:
        api = build_api_key("agent", "same-id")
        task = build_task_key("same-id")
        assert api != task

    def test_task_vs_workflow(self) -> None:
        task = build_task_key("task-1")
        wf = build_workflow_key("task-1")
        assert task != wf

    def test_task_vs_manager(self) -> None:
        task = build_task_key("explorer")
        mgr = build_manager_key("explorer")
        assert task != mgr

    def test_all_four_distinct(self) -> None:
        keys = {
            build_api_key("x", "y"),
            build_task_key("x"),
            build_manager_key("x"),
            build_workflow_key("x"),
        }
        assert len(keys) == 4


class TestSanitize:
    """_sanitize strips whitespace and control characters from key segments."""

    def test_strips_leading_trailing_whitespace(self) -> None:
        assert _sanitize("  hello  ") == "hello"

    def test_replaces_newlines_with_space(self) -> None:
        assert _sanitize("hello\nworld") == "hello-world"

    def test_replaces_carriage_return_with_space(self) -> None:
        assert _sanitize("hello\rworld") == "hello-world"

    def test_replaces_tabs_with_space(self) -> None:
        assert _sanitize("hello\tworld") == "hello-world"

    def test_handles_mixed_whitespace(self) -> None:
        result = _sanitize("  hello \t\n\r world  ")
        assert "\t" not in result
        assert "\n" not in result
        assert "\r" not in result
        assert result == "hello-world"

    def test_truncates_to_max_length(self) -> None:
        long_input = "a" * 300
        assert len(_sanitize(long_input, max_length=64)) == 64

    def test_empty_string(self) -> None:
        assert _sanitize("") == ""

    def test_whitespace_only(self) -> None:
        assert _sanitize("  \t\n\r  ") == ""

    def test_preserves_valid_chars(self) -> None:
        assert _sanitize("task-123_abc.def") == "task-123_abc.def"
