"""Raw subprocess MCP round-trip integration test.

Starts the MCP server as a subprocess via stdio, sends JSON-RPC 2.0
messages directly (no MCP SDK dependency), and verifies the full
request/response lifecycle.

Tests cover:
  - JSON-RPC initialize handshake
  - tools/list returns expected tools
  - memory_save → memory_search roundtrip
  - memory_save → memory_get roundtrip
  - memory_delete removes observation
  - Error handling for invalid tool calls
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from dataclasses import dataclass
from typing import Any

import pytest


@dataclass(frozen=True, slots=True)
class _JsonRpcResponse:
    """Immutable container for a parsed JSON-RPC 2.0 response."""

    jsonrpc: str
    id: str | int | None
    result: Any | None
    error: dict[str, Any] | None

    @classmethod
    def from_raw(cls, raw: bytes) -> _JsonRpcResponse:
        """Parse raw bytes into a JSON-RPC response.

        Raises:
            ValueError: If the raw bytes cannot be decoded or parsed.
        """
        text = raw.decode("utf-8").strip()
        # Server may emit debug lines on stderr; only parse JSON lines.
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict) and data.get("jsonrpc") == "2.0":
                return cls(
                    jsonrpc=data["jsonrpc"],
                    id=data.get("id"),
                    result=data.get("result"),
                    error=data.get("error"),
                )
        raise ValueError(f"No valid JSON-RPC response in: {text[:200]}")

    @property
    def is_error(self) -> bool:
        """Return True if the response contains an error.

        MCP tool errors are returned as results with ``isError: True``,
        not as JSON-RPC error objects.  Both forms are checked.
        """
        if self.error is not None:
            return True
        # MCP spec: tool errors are results with isError flag.
        if isinstance(self.result, dict) and self.result.get("isError") is True:
            return True
        return False


class _McpSubprocessClient:
    """Manages a MCP server subprocess communicating over stdio JSON-RPC.

    Provides synchronous send/receive helpers.  Each send writes a
    single JSON-RPC request line to stdin and reads exactly one
    response line from stdout.
    """

    def __init__(self, proc: subprocess.Popen[bytes]) -> None:
        self._proc = proc
        self._next_id = 1

    def send(self, method: str, params: dict[str, Any] | None = None) -> _JsonRpcResponse:
        """Send a JSON-RPC request and return the parsed response.

        Args:
            method: JSON-RPC method name (e.g. ``initialize``, ``tools/list``).
            params: Optional parameters dict.

        Returns:
            Parsed _JsonRpcResponse.

        Raises:
            ValueError: If the server produces no parseable response.
            RuntimeError: If the server process has exited.
        """
        if self._proc.poll() is not None:
            raise RuntimeError(f"MCP server exited with code {self._proc.returncode}")

        request_id = self._next_id
        self._next_id += 1

        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        request_line = json.dumps(payload) + "\n"
        self._proc.stdin.write(request_line.encode("utf-8"))  # type: ignore[union-attr]
        self._proc.stdin.flush()  # type: ignore[union-attr]

        response_line = self._proc.stdout.readline()  # type: ignore[union-attr]
        if not response_line:
            raise ValueError("Server closed stdout without responding")
        return _JsonRpcResponse.from_raw(response_line)

    def close(self) -> None:
        """Terminate the MCP server subprocess."""
        try:
            self._proc.stdin.close()  # type: ignore[union-attr]
        except OSError:
            pass
        try:
            self._proc.terminate()
            self._proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._proc.kill()
            self._proc.wait(timeout=3)


@pytest.fixture
def mcp_client(tmp_path: object) -> Any:
    """Start MCP server as subprocess and yield a _McpSubprocessClient.

    Uses a temporary database file to avoid polluting real data.
    """
    db_path = str(tmp_path) + "/test_mcp_roundtrip.db"
    env = {**os.environ, "FORK_MEMORY_DB": db_path}

    proc = subprocess.Popen(
        [
            "uv",
            "run",
            "memory",
            "mcp",
            "serve",
            "--db",
            db_path,
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd=os.environ.get("PROJECT_DIR", os.getcwd()),
    )

    # Give server time to start up.
    time.sleep(1.5)

    client = _McpSubprocessClient(proc)
    yield client
    client.close()


def _unique_prefix() -> str:
    """Generate a unique prefix for test data isolation."""
    return f"roundtrip-{uuid.uuid4().hex[:8]}"


def _extract_text_content(result: Any) -> str | list[Any] | dict[str, Any]:
    """Extract text content from a tools/call result.

    Returns parsed JSON (dict or list) or raw string.
    """
    if isinstance(result, dict):
        content = result.get("content", [])
        if isinstance(content, list) and content:
            first = content[0]
            if isinstance(first, dict) and "text" in first:
                text = first["text"]
                try:
                    return json.loads(text)
                except (json.JSONDecodeError, TypeError):
                    return text
        return result
    return result


@pytest.mark.integration
class TestMcpRawRoundtrip:
    """Raw subprocess MCP round-trip integration tests.

    These tests validate the MCP server by communicating over stdio
    using the JSON-RPC 2.0 protocol directly, without the MCP SDK.
    """

    def test_initialize_handshake(self, mcp_client: _McpSubprocessClient) -> None:
        """AC-1: Server responds to initialize with correct capabilities."""
        resp = mcp_client.send(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "0.1.0"},
            },
        )
        assert not resp.is_error, f"Initialize failed: {resp.error}"
        result: dict[str, Any] = resp.result  # type: ignore[assignment]
        assert result.get("serverInfo", {}).get("name") == "memory-server"
        assert result.get("capabilities", {}).get("tools") is not None

    def test_initialized_notification(self, mcp_client: _McpSubprocessClient) -> None:
        """Server accepts initialized notification after handshake."""
        mcp_client.send(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "0.1.0"},
            },
        )
        # Send notification (no id = no response expected).
        notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        }
        mcp_client._proc.stdin.write(json.dumps(notification).encode("utf-8") + b"\n")  # type: ignore[union-attr]
        mcp_client._proc.stdin.flush()  # type: ignore[union-attr]

    def test_tools_list_returns_core_tools(self, mcp_client: _McpSubprocessClient) -> None:
        """AC-2: tools/list returns at least memory_save and memory_search."""
        mcp_client.send(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "0.1.0"},
            },
        )
        resp = mcp_client.send("tools/list")
        assert not resp.is_error, f"tools/list failed: {resp.error}"
        result = resp.result
        assert isinstance(result, dict)
        tools = result.get("tools", [])
        tool_names = {t["name"] for t in tools}
        required = {"memory_save", "memory_search", "memory_get", "memory_delete"}
        missing = required - tool_names
        assert not missing, f"Missing required tools: {missing}"
        assert len(tool_names) >= 10, f"Expected >=10 tools, got {len(tool_names)}"

    def test_save_and_search_roundtrip(self, mcp_client: _McpSubprocessClient) -> None:
        """AC-3: memory_save creates observation retrievable by memory_search."""
        prefix = _unique_prefix()
        test_content = f"{prefix} zebra apple banana quantum physics"

        mcp_client.send(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "0.1.0"},
            },
        )

        # Save
        save_resp = mcp_client.send(
            "tools/call",
            {
                "name": "memory_save",
                "arguments": {"content": test_content},
            },
        )
        assert not save_resp.is_error, f"memory_save failed: {save_resp.error}"
        save_data = _extract_text_content(save_resp.result)
        assert isinstance(save_data, dict)
        assert save_data.get("status") == "saved"
        obs_id = save_data.get("id")
        assert obs_id is not None

        # Search
        search_resp = mcp_client.send(
            "tools/call",
            {
                "name": "memory_search",
                "arguments": {"query": f"{prefix} quantum"},
            },
        )
        assert not search_resp.is_error, f"memory_search failed: {search_resp.error}"
        search_data = _extract_text_content(search_resp.result)
        assert isinstance(search_data, list)
        assert len(search_data) >= 1, f"Expected results, got {search_data}"
        matched = any(prefix in str(obs) for obs in search_data)
        assert matched, f"Saved observation not found in search results: {search_data}"

    def test_save_and_get_roundtrip(self, mcp_client: _McpSubprocessClient) -> None:
        """AC-4: memory_save creates observation retrievable by memory_get."""
        prefix = _unique_prefix()
        test_content = f"{prefix} unique roundtrip test content"

        mcp_client.send(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "0.1.0"},
            },
        )

        # Save
        save_resp = mcp_client.send(
            "tools/call",
            {
                "name": "memory_save",
                "arguments": {"content": test_content},
            },
        )
        assert not save_resp.is_error, f"memory_save failed: {save_resp.error}"
        save_data = _extract_text_content(save_resp.result)
        assert isinstance(save_data, dict)
        obs_id: str = save_data["id"]

        # Get by ID
        get_resp = mcp_client.send(
            "tools/call",
            {
                "name": "memory_get",
                "arguments": {"id": obs_id},
            },
        )
        assert not get_resp.is_error, f"memory_get failed: {get_resp.error}"
        get_data = _extract_text_content(get_resp.result)
        assert isinstance(get_data, dict)
        assert test_content in get_data.get("content", ""), (
            f"Content mismatch: expected '{test_content}' in '{get_data.get('content', '')}'"
        )
        assert get_data.get("id") == obs_id

    def test_delete_removes_observation(self, mcp_client: _McpSubprocessClient) -> None:
        """AC-5: memory_delete removes an observation."""
        prefix = _unique_prefix()
        test_content = f"{prefix} to be deleted"

        mcp_client.send(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "0.1.0"},
            },
        )

        # Save
        save_resp = mcp_client.send(
            "tools/call",
            {
                "name": "memory_save",
                "arguments": {"content": test_content},
            },
        )
        save_raw = _extract_text_content(save_resp.result)
        assert isinstance(save_raw, dict)
        obs_id = save_raw["id"]

        # Delete
        del_resp = mcp_client.send(
            "tools/call",
            {
                "name": "memory_delete",
                "arguments": {"id": obs_id},
            },
        )
        assert not del_resp.is_error, f"memory_delete failed: {del_resp.error}"
        del_data = _extract_text_content(del_resp.result)
        assert isinstance(del_data, dict)
        assert del_data.get("status") == "deleted", f"Delete status: {del_data}"

        # Verify gone
        get_resp = mcp_client.send(
            "tools/call",
            {
                "name": "memory_get",
                "arguments": {"id": obs_id},
            },
        )
        # After delete, get should return an error.
        assert get_resp.is_error, f"Expected error after delete, got: {get_resp.result}"

    def test_invalid_tool_returns_error(self, mcp_client: _McpSubprocessClient) -> None:
        """AC-6: Calling a non-existent tool returns an error."""
        mcp_client.send(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "0.1.0"},
            },
        )

        resp = mcp_client.send(
            "tools/call",
            {
                "name": "nonexistent_tool_xyz",
                "arguments": {},
            },
        )
        assert resp.is_error, f"Expected error for unknown tool, got: {resp.result}"

    def test_list_returns_saved_observations(self, mcp_client: _McpSubprocessClient) -> None:
        """AC-7: memory_list returns saved observations."""
        prefix = _unique_prefix()

        mcp_client.send(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "0.1.0"},
            },
        )

        # Save two observations
        for i in range(2):
            mcp_client.send(
                "tools/call",
                {
                    "name": "memory_save",
                    "arguments": {"content": f"{prefix} list-test-{i}"},
                },
            )

        # List
        list_resp = mcp_client.send(
            "tools/call",
            {
                "name": "memory_list",
                "arguments": {"limit": 5},
            },
        )
        assert not list_resp.is_error, f"memory_list failed: {list_resp.error}"
        list_data = _extract_text_content(list_resp.result)
        assert isinstance(list_data, list)
        assert len(list_data) >= 2, f"Expected >=2 results, got {len(list_data)}"
        matched = any(prefix in str(obs) for obs in list_data)
        assert matched, f"Saved observations not found in list: {list_data}"
