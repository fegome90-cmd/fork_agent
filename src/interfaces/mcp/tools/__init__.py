"""MCP server for tmux_fork memory operations and inter-agent messaging."""

from __future__ import annotations

from typing import Any

from src.interfaces.mcp.tools._shared import (  # noqa: F401
    _custom_db_path,
    _detect_project,
    _get_agent_messenger,
    _get_enhanced_search_service,
    _get_health_service,
    _get_memory_service,
    _get_session_service,
    _get_singleton,
    _map_error,
    _resolve_project,
    _singletons,
    init_service,
    logger,
)
from src.interfaces.mcp.tools.memory import (  # noqa: F401
    _cap_json_response,
    _extract_learnings,
    _infer_topic_family,
    _normalize_topic_segment,
    _serialize_observation,
    _serialize_observations,
    _serialize_session,
    _serialize_sessions,
    _suggest_topic_key,
    memory_capture_passive,
    memory_context,
    memory_delete,
    memory_get,
    memory_list,
    memory_merge_projects,
    memory_retrieve,
    memory_save,
    memory_save_prompt,
    memory_search,
    memory_session_end,
    memory_session_start,
    memory_session_summary,
    memory_stats,
    memory_suggest_topic_key,
    memory_timeline,
    memory_update,
)
from src.interfaces.mcp.tools.messaging import (  # noqa: F401
    _serialize_message,
    _serialize_messages,
    fork_message_broadcast,
    fork_message_history,
    fork_message_receive,
    fork_message_send,
)


def register_tools(mcp_server: Any) -> None:
    """Register all 21 MCP tools (17 memory + 4 messaging)."""
    # Memory tools (17)
    mcp_server.tool()(memory_save)
    mcp_server.tool()(memory_search)
    mcp_server.tool()(memory_retrieve)
    mcp_server.tool()(memory_get)
    mcp_server.tool()(memory_list)
    mcp_server.tool()(memory_delete)
    mcp_server.tool()(memory_context)
    mcp_server.tool()(memory_update)
    mcp_server.tool()(memory_stats)
    mcp_server.tool()(memory_timeline)
    mcp_server.tool()(memory_session_start)
    mcp_server.tool()(memory_session_end)
    mcp_server.tool()(memory_session_summary)
    mcp_server.tool()(memory_suggest_topic_key)
    mcp_server.tool()(memory_save_prompt)
    mcp_server.tool()(memory_capture_passive)
    mcp_server.tool()(memory_merge_projects)

    # Messaging tools (4)
    mcp_server.tool()(fork_message_send)
    mcp_server.tool()(fork_message_receive)
    mcp_server.tool()(fork_message_broadcast)
    mcp_server.tool()(fork_message_history)
