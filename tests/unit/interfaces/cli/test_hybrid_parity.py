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
        _, receipt = d.dispatch_message_send(
            to_agent="session:main.agent", payload="hello", from_agent="session:main.orch"
        )
        assert receipt.mode == DispatchMode.MCP_CLIENT

    def test_message_receive_mcp_receipt(
        self, mock_service: MagicMock, mock_mcp: MagicMock, receipt_file: Path
    ) -> None:
        d = _dispatcher_with_mcp(mock_service, mock_mcp)
        _, receipt = d.dispatch_message_receive(agent_id="session:main.agent", limit=10)
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
        _, receipt = d.dispatch_message_send(
            to_agent="session:main.a", payload="hi", from_agent="session:main.b"
        )
        assert receipt.mode == DispatchMode.FALLBACK

    def test_message_receive_fallback(
        self, mock_service: MagicMock, mock_mcp: MagicMock, receipt_file: Path
    ) -> None:
        mock_mcp.call_tool_sync.side_effect = ConnectionError("refused")
        d = _dispatcher_with_mcp(mock_service, mock_mcp)
        _, receipt = d.dispatch_message_receive(agent_id="session:main.a", limit=10)
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
            d.dispatch_message_send(
                to_agent="session:main.a", payload="hi", from_agent="session:main.b"
            )

    def test_message_receive_require_fails(
        self, mock_service: MagicMock, mock_mcp: MagicMock, receipt_file: Path, monkeypatch
    ) -> None:
        monkeypatch.setenv("FORK_MCP_REQUIRE", "1")
        mock_mcp.call_tool_sync.side_effect = RuntimeError("MCP down")
        d = _dispatcher_with_mcp(mock_service, mock_mcp)
        with pytest.raises(RuntimeError, match="FORK_MCP_REQUIRE"):
            d.dispatch_message_receive(agent_id="session:main.a", limit=10)


class TestDataCorrectness:
    """Verify returned data comes from the correct backend (MCP vs direct)."""

    def test_save_returns_mcp_data_not_local(
        self, mock_service: MagicMock, mock_mcp: MagicMock, receipt_file: Path
    ) -> None:
        """When MCP succeeds, returned observation should have MCP's ID, not local DB's."""
        mock_mcp.call_tool_sync.return_value = {
            "id": "mcp-obs-999",
            "timestamp": 1000000,
            "content": "from mcp",
        }
        mock_service.get_by_id.return_value = _make_observation(id="local-obs-1")
        d = _dispatcher_with_mcp(mock_service, mock_mcp)
        obs, receipt = d.dispatch_save(content="test")
        assert receipt.mode == DispatchMode.MCP_CLIENT
        # Observation should be from MCP result, not local DB fetch
        assert obs.id == "mcp-obs-999"

    def test_save_fetches_local_when_mcp_returns_partial(
        self, mock_service: MagicMock, mock_mcp: MagicMock, receipt_file: Path
    ) -> None:
        """When MCP returns only {id, status}, _to_observation fails and dispatcher falls back to get_by_id."""
        mock_mcp.call_tool_sync.return_value = {"id": "mcp-obs-999", "status": "ok"}
        mock_service.get_by_id.return_value = _make_observation(
            id="mcp-obs-999", content="from local"
        )
        d = _dispatcher_with_mcp(mock_service, mock_mcp)
        obs, receipt = d.dispatch_save(content="test")
        assert receipt.mode == DispatchMode.MCP_CLIENT
        # Falls back to local fetch since MCP didn't return full Observation
        mock_service.get_by_id.assert_called_once_with("mcp-obs-999")
        assert obs.id == "mcp-obs-999"

    def test_search_returns_mcp_data(
        self, mock_service: MagicMock, mock_mcp: MagicMock, receipt_file: Path
    ) -> None:
        mock_mcp.call_tool_sync.return_value = [{"id": "mcp-1", "timestamp": 1000, "content": "c"}]
        d = _dispatcher_with_mcp(mock_service, mock_mcp)
        results, receipt = d.dispatch_search(query="test")
        assert receipt.mode == DispatchMode.MCP_CLIENT
        assert len(results) == 1
        assert results[0].id == "mcp-1"


class TestForkMcpRequireNoServer:
    """Verify FORK_MCP_REQUIRE=1 raises when no server is discoverable.

    This tests the _get_mcp_client() code path, not the _on_mcp_error path.
    """

    def test_no_server_raises_require(
        self, mock_service: MagicMock, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setenv("FORK_MCP_REQUIRE", "1")
        monkeypatch.setenv("FORK_DATA_DIR", str(tmp_path))
        d = HybridDispatcher(mock_service)
        # No port file exists — discover_server returns None
        with pytest.raises(RuntimeError, match="FORK_MCP_REQUIRE"):
            d._get_mcp_client()

    def test_no_server_dispatch_save_raises(
        self, mock_service: MagicMock, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setenv("FORK_MCP_REQUIRE", "1")
        monkeypatch.setenv("FORK_DATA_DIR", str(tmp_path))
        d = HybridDispatcher(mock_service)
        with pytest.raises(RuntimeError, match="FORK_MCP_REQUIRE"):
            d.dispatch_save(content="test")


class TestWriteReceiptResilience:
    """Verify _write_receipt never crashes a dispatch."""

    def test_receipt_write_failure_does_not_crash(
        self, mock_service: MagicMock, mock_mcp: MagicMock, tmp_path: Path, monkeypatch
    ) -> None:
        # Point receipt to a read-only path (0o555 = r-x — allows reading but not writing)
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o555)
        monkeypatch.setenv("FORK_DATA_DIR", str(readonly_dir))

        mock_mcp.call_tool_sync.return_value = {
            "id": "mcp-id",
            "timestamp": 1000,
            "content": "test",
        }
        d = _dispatcher_with_mcp(mock_service, mock_mcp)
        # Should NOT raise even though receipt file is unwritable
        obs, receipt = d.dispatch_save(content="test")
        assert receipt.mode == DispatchMode.MCP_CLIENT

        # Cleanup
        readonly_dir.chmod(0o755)
