"""Integration tests for MCP server using ClientSession."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from mcp import StdioServerParameters


@pytest.fixture
def server_params(tmp_path: Path) -> StdioServerParameters:
    """Create MCP server parameters for stdio transport."""
    from mcp import StdioServerParameters

    return StdioServerParameters(
        command="uv",
        args=[
            "run",
            "memory",
            "mcp",
            "serve",
            "--db",
            str(tmp_path / "test_memory.db"),
        ],
    )


@pytest.mark.asyncio
async def test_initialize_handshake(server_params: StdioServerParameters) -> None:
    """AC-1: Server responds to initialize with correct capabilities."""
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client

    async with stdio_client(server_params) as (read, write):  # noqa: SIM117
        async with ClientSession(read, write) as session:
            result = await session.initialize()

            assert result.serverInfo.name == "memory-server"
            assert result.capabilities.tools is not None


@pytest.mark.asyncio
async def test_tools_list_returns_mvp_tools(server_params: StdioServerParameters) -> None:
    """AC-2: tools/list returns at least the core MVP tools."""
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client

    async with stdio_client(server_params) as (read, write):  # noqa: SIM117
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()

            tool_names = {t.name for t in tools_result.tools}
            required = {
                "memory_save",
                "memory_search",
                "memory_get",
                "memory_list",
                "memory_delete",
                "memory_context",
            }
            missing = required - tool_names
            assert not missing, f"Missing required tools: {missing}"
            assert len(tool_names) >= 10, f"Expected >=10 tools, got {len(tool_names)}"


@pytest.mark.asyncio
async def test_save_and_get_roundtrip(server_params: StdioServerParameters) -> None:
    """AC-3: memory_save creates observation retrievable by memory_get."""
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client
    from mcp.types import TextContent

    async with stdio_client(server_params) as (read, write):  # noqa: SIM117
        async with ClientSession(read, write) as session:
            await session.initialize()

            save_result = await session.call_tool(
                "memory_save", {"content": "integration test observation"}
            )
            assert isinstance(save_result.content[0], TextContent)
            save_data = json.loads(save_result.content[0].text)
            assert save_data["status"] == "saved"
            obs_id = save_data["id"]

            get_result = await session.call_tool("memory_get", {"id": obs_id})
            assert isinstance(get_result.content[0], TextContent)
            get_data = json.loads(get_result.content[0].text)
            assert "integration test observation" in get_data["content"]
            assert get_data["id"] == obs_id


@pytest.mark.asyncio
async def test_save_and_search_roundtrip(server_params: StdioServerParameters) -> None:
    """AC-4: memory_search finds saved observations."""
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client
    from mcp.types import TextContent

    async with stdio_client(server_params) as (read, write):  # noqa: SIM117
        async with ClientSession(read, write) as session:
            await session.initialize()

            await session.call_tool(
                "memory_save", {"content": "python async patterns integration test"}
            )

            search_result = await session.call_tool("memory_search", {"query": "python async"})
            assert isinstance(search_result.content[0], TextContent)
            search_data = json.loads(search_result.content[0].text)
            assert len(search_data) >= 1
            assert any("python async" in obs["content"] for obs in search_data)


@pytest.mark.asyncio
async def test_list_returns_observations(server_params: StdioServerParameters) -> None:
    """AC-5: memory_list returns recent observations with pagination."""
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client
    from mcp.types import TextContent

    async with stdio_client(server_params) as (read, write):  # noqa: SIM117
        async with ClientSession(read, write) as session:
            await session.initialize()

            await session.call_tool("memory_save", {"content": "list test observation 1"})

            list_result = await session.call_tool("memory_list", {"limit": 5})
            assert isinstance(list_result.content[0], TextContent)
            list_data = json.loads(list_result.content[0].text)
            assert len(list_data) >= 1
            assert any("list test" in obs["content"] for obs in list_data)


@pytest.mark.asyncio
async def test_delete_removes_observation(server_params: StdioServerParameters) -> None:
    """AC-6: memory_delete removes observation."""
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client
    from mcp.types import TextContent

    async with stdio_client(server_params) as (read, write):  # noqa: SIM117
        async with ClientSession(read, write) as session:
            await session.initialize()

            save_result = await session.call_tool("memory_save", {"content": "to be deleted"})
            assert isinstance(save_result.content[0], TextContent)
            obs_id = json.loads(save_result.content[0].text)["id"]

            delete_result = await session.call_tool("memory_delete", {"id": obs_id})
            assert isinstance(delete_result.content[0], TextContent)
            delete_data = json.loads(delete_result.content[0].text)
            assert delete_data["status"] == "deleted"

            get_result = await session.call_tool("memory_get", {"id": obs_id})
            assert get_result.isError


@pytest.mark.asyncio
async def test_empty_search_returns_empty_array(server_params: StdioServerParameters) -> None:
    """Empty search returns empty array."""
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client
    from mcp.types import TextContent

    async with stdio_client(server_params) as (read, write):  # noqa: SIM117
        async with ClientSession(read, write) as session:
            await session.initialize()

            search_result = await session.call_tool(
                "memory_search", {"query": "nonexistent_xyz_123"}
            )
            assert isinstance(search_result.content[0], TextContent)
            search_data = json.loads(search_result.content[0].text)
            assert search_data == []
