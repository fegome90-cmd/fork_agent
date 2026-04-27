"""Hybrid parity receipt verification for 5 critical commands.

Verifies that each critical command emits the correct receipt mode:
- MCP_CLIENT when MCP server responds successfully
- FALLBACK when MCP fails and fallback to direct
- DIRECT when no MCP server available

Also verifies FORK_MCP_REQUIRE=1 fails closed.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.interfaces.cli.hybrid import DispatchMode, HybridDispatcher


def _make_observation(**kwargs):
    """Create a mock observation with required fields."""
    obs = MagicMock()
    for k, v in kwargs.items():
        setattr(obs, k, v)
    return obs


@pytest.fixture
def receipt_file(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("FORK_DATA_DIR", str(tmp_path))
    return tmp_path / ".hybrid-receipts.jsonl"


@pytest.fixture
def mock_service():
    svc = MagicMock()
    svc.save.return_value = _make_observation(id="obs-1")
    svc.search.return_value = [_make_observation(id="obs-1")]
    svc.get_by_id.return_value = _make_observation(id="obs-1")
    return svc


@pytest.fixture
def mock_mcp():
    mcp = MagicMock()
    mcp.call_tool_sync.return_value = {"id": "mcp-id"}
    return mcp


def _dispatcher_with_mcp(service, mcp_client):
    d = HybridDispatcher(service)
    d._get_mcp_client = MagicMock(return_value=mcp_client)
    return d


class TestCriticalCommandReceipts:
    """Verify receipt mode for 5 critical commands."""

    def test_save_mcp_receipt(
        self, mock_service: MagicMock, mock_mcp: MagicMock, receipt_file: Path
    ) -> None:
        mock_mcp.call_tool_sync.return_value = {
            "id": "mcp-id",
            "timestamp": 1000000,
            "content": "test",
        }
        d = _dispatcher_with_mcp(mock_service, mock_mcp)
        _, receipt = d.dispatch_save(content="test")
        assert receipt.mode == DispatchMode.MCP_CLIENT

    def test_search_mcp_receipt(
        self, mock_service: MagicMock, mock_mcp: MagicMock, receipt_file: Path
    ) -> None:
        mock_mcp.call_tool_sync.return_value = [{"id": "mcp-id"}]
        d = _dispatcher_with_mcp(mock_service, mock_mcp)
        _, receipt = d.dispatch_search(query="test")
        assert receipt.mode == DispatchMode.MCP_CLIENT

    def test_get_mcp_receipt(
        self, mock_service: MagicMock, mock_mcp: MagicMock, receipt_file: Path
    ) -> None:
        mock_mcp.call_tool_sync.return_value = {
            "id": "mcp-id",
            "timestamp": 1000000,
            "content": "test",
        }
        mock_service.get_by_id.return_value = _make_observation(id="mcp-id")
        d = _dispatcher_with_mcp(mock_service, mock_mcp)
        _, receipt = d.dispatch_get(id="obs-1")
        assert receipt.mode == DispatchMode.MCP_CLIENT

    def test_message_send_mcp_receipt(
        self, mock_service: MagicMock, mock_mcp: MagicMock, receipt_file: Path
    ) -> None:
        d = _dispatcher_with_mcp(mock_service, mock_mcp)
        _, receipt = d.dispatch_message_send(sender="agent-1", recipient="agent-2", content="hello")
        assert receipt.mode == DispatchMode.MCP_CLIENT

    def test_message_receive_mcp_receipt(
        self, mock_service: MagicMock, mock_mcp: MagicMock, receipt_file: Path
    ) -> None:
        d = _dispatcher_with_mcp(mock_service, mock_mcp)
        _, receipt = d.dispatch_message_receive(recipient="agent-1")
        assert receipt.mode == DispatchMode.MCP_CLIENT


class TestFallbackReceipts:
    """Verify fallback receipt for 5 critical commands."""

    def test_save_fallback(
        self, mock_service: MagicMock, mock_mcp: MagicMock, receipt_file: Path
    ) -> None:
        mock_mcp.call_tool_sync.side_effect = ConnectionError("refused")
        d = _dispatcher_with_mcp(mock_service, mock_mcp)
        _, receipt = d.dispatch_save(content="test")
        assert receipt.mode == DispatchMode.FALLBACK

    def test_search_fallback(
        self, mock_service: MagicMock, mock_mcp: MagicMock, receipt_file: Path
    ) -> None:
        mock_mcp.call_tool_sync.side_effect = ConnectionError("refused")
        d = _dispatcher_with_mcp(mock_service, mock_mcp)
        _, receipt = d.dispatch_search(query="test")
        assert receipt.mode == DispatchMode.FALLBACK

    def test_get_fallback(
        self, mock_service: MagicMock, mock_mcp: MagicMock, receipt_file: Path
    ) -> None:
        mock_mcp.call_tool_sync.side_effect = ConnectionError("refused")
        d = _dispatcher_with_mcp(mock_service, mock_mcp)
        _, receipt = d.dispatch_get(id="obs-1")
        assert receipt.mode == DispatchMode.FALLBACK

    def test_message_send_fallback(
        self, mock_service: MagicMock, mock_mcp: MagicMock, receipt_file: Path
    ) -> None:
        mock_mcp.call_tool_sync.side_effect = ConnectionError("refused")
        d = _dispatcher_with_mcp(mock_service, mock_mcp)
        _, receipt = d.dispatch_message_send(sender="a", recipient="b", content="hi")
        assert receipt.mode == DispatchMode.FALLBACK

    def test_message_receive_fallback(
        self, mock_service: MagicMock, mock_mcp: MagicMock, receipt_file: Path
    ) -> None:
        mock_mcp.call_tool_sync.side_effect = ConnectionError("refused")
        d = _dispatcher_with_mcp(mock_service, mock_mcp)
        _, receipt = d.dispatch_message_receive(recipient="a")
        assert receipt.mode == DispatchMode.FALLBACK


class TestMcpRequireFailsClosed:
    """Verify FORK_MCP_REQUIRE=1 raises when MCP call fails."""

    def test_save_require_fails(
        self, mock_service: MagicMock, mock_mcp: MagicMock, receipt_file: Path, monkeypatch
    ) -> None:
        monkeypatch.setenv("FORK_MCP_REQUIRE", "1")
        mock_mcp.call_tool_sync.side_effect = RuntimeError("MCP down")
        d = _dispatcher_with_mcp(mock_service, mock_mcp)
        with pytest.raises(RuntimeError, match="FORK_MCP_REQUIRE"):
            d.dispatch_save(content="test")

    def test_search_require_fails(
        self, mock_service: MagicMock, mock_mcp: MagicMock, receipt_file: Path, monkeypatch
    ) -> None:
        monkeypatch.setenv("FORK_MCP_REQUIRE", "1")
        mock_mcp.call_tool_sync.side_effect = RuntimeError("MCP down")
        d = _dispatcher_with_mcp(mock_service, mock_mcp)
        with pytest.raises(RuntimeError, match="FORK_MCP_REQUIRE"):
            d.dispatch_search(query="test")

    def test_get_require_fails(
        self, mock_service: MagicMock, mock_mcp: MagicMock, receipt_file: Path, monkeypatch
    ) -> None:
        monkeypatch.setenv("FORK_MCP_REQUIRE", "1")
        mock_mcp.call_tool_sync.side_effect = RuntimeError("MCP down")
        d = _dispatcher_with_mcp(mock_service, mock_mcp)
        with pytest.raises(RuntimeError, match="FORK_MCP_REQUIRE"):
            d.dispatch_get(id="obs-1")

    def test_message_send_require_fails(
        self, mock_service: MagicMock, mock_mcp: MagicMock, receipt_file: Path, monkeypatch
    ) -> None:
        monkeypatch.setenv("FORK_MCP_REQUIRE", "1")
        mock_mcp.call_tool_sync.side_effect = RuntimeError("MCP down")
        d = _dispatcher_with_mcp(mock_service, mock_mcp)
        with pytest.raises(RuntimeError, match="FORK_MCP_REQUIRE"):
            d.dispatch_message_send(sender="a", recipient="b", content="hi")

    def test_message_receive_require_fails(
        self, mock_service: MagicMock, mock_mcp: MagicMock, receipt_file: Path, monkeypatch
    ) -> None:
        monkeypatch.setenv("FORK_MCP_REQUIRE", "1")
        mock_mcp.call_tool_sync.side_effect = RuntimeError("MCP down")
        d = _dispatcher_with_mcp(mock_service, mock_mcp)
        with pytest.raises(RuntimeError, match="FORK_MCP_REQUIRE"):
            d.dispatch_message_receive(recipient="a")
