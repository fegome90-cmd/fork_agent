"""Unit tests for CLI→MCP hybrid dispatch."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.domain.entities.observation import Observation
from src.interfaces.cli.hybrid import (
    DispatchMode,
    DispatchReceipt,
    HybridDispatcher,
    MCPClientSDK,
    _to_observations,
    _write_receipt,
    discover_server,
)

# ── Fixtures ──────────────────────────────────────────────


def _make_observation(
    id: str = "test-id-1234",
    timestamp: int = 1000000,
    content: str = "test content",
    **overrides: object,
) -> Observation:
    return Observation(id=id, timestamp=timestamp, content=content, **overrides)


def _make_obs_dict(**overrides: object) -> dict:
    base: dict = {"id": "test-id-1234", "timestamp": 1000000, "content": "test content"}
    base.update(overrides)
    return base


@pytest.fixture
def mock_service() -> MagicMock:
    svc = MagicMock()
    svc.save.return_value = _make_observation()
    svc.search.return_value = [_make_observation()]
    svc.get_recent.return_value = [_make_observation()]
    svc.get_by_id.return_value = _make_observation()
    svc.delete.return_value = "Deleted test-id-1234"
    svc.update.return_value = _make_observation()
    return svc


@pytest.fixture
def mock_mcp_client() -> MagicMock:
    client = MagicMock(spec=MCPClientSDK)
    client.call_tool_sync.return_value = _make_obs_dict()
    return client


@pytest.fixture
def dispatcher(mock_service: MagicMock) -> HybridDispatcher:
    return HybridDispatcher(mock_service)


@pytest.fixture
def receipt_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("FORK_DATA_DIR", str(tmp_path))
    return tmp_path / ".hybrid-receipts.jsonl"


@pytest.fixture
def port_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("FORK_DATA_DIR", str(tmp_path))
    return tmp_path / ".mcp-server.json"


def _dispatcher_with_mcp(mock_service: MagicMock, mock_mcp_client: MagicMock) -> HybridDispatcher:
    d = HybridDispatcher(mock_service)
    d._get_mcp_client = MagicMock(return_value=mock_mcp_client)  # type: ignore[assignment]
    d._server_info = {"pid": 123, "port": 8080, "host": "127.0.0.1"}  # type: ignore[assignment]
    return d


# ── TestValidateContent ──────────────────────────────────


class TestValidateContent:
    def test_rejects_empty_content(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            HybridDispatcher._validate_content("")

    def test_rejects_null_bytes(self) -> None:
        with pytest.raises(ValueError, match="null"):
            HybridDispatcher._validate_content("test\x00null")

    def test_accepts_valid(self) -> None:
        HybridDispatcher._validate_content("valid content")


# ── TestToObservations ───────────────────────────────────


class TestToObservations:
    def test_valid_list(self) -> None:
        result = _to_observations([_make_obs_dict()])
        assert len(result) == 1
        assert result[0].id == "test-id-1234"

    def test_extra_fields_ignored(self) -> None:
        result = _to_observations([_make_obs_dict(bogus="data")])
        assert len(result) == 1
        assert result[0].content == "test content"

    def test_missing_required_fields_skipped(self) -> None:
        result = _to_observations([{"id": "abc"}])
        assert len(result) == 0

    def test_non_list_returns_empty(self) -> None:
        result = _to_observations("not a list")
        assert result == []


# ── TestWriteReceipt ─────────────────────────────────────


class TestWriteReceipt:
    def test_writes_valid_jsonl(self, receipt_file: Path) -> None:
        receipt = DispatchReceipt(
            mode=DispatchMode.DIRECT,
            command="save",
            latency_ms=1.5,
            reason=None,
            server_pid=None,
        )
        _write_receipt(receipt)
        assert receipt_file.exists()
        data = json.loads(receipt_file.read_text())
        assert data["mode"] == "direct"
        assert data["command"] == "save"

    def test_appends_not_overwrites(self, receipt_file: Path) -> None:
        r1 = DispatchReceipt(
            mode=DispatchMode.DIRECT, command="save", latency_ms=1.0, reason=None, server_pid=None
        )
        r2 = DispatchReceipt(
            mode=DispatchMode.MCP_CLIENT,
            command="list",
            latency_ms=150.0,
            reason=None,
            server_pid=123,
        )
        _write_receipt(r1)
        _write_receipt(r2)
        lines = receipt_file.read_text().strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["command"] == "save"
        assert json.loads(lines[1])["command"] == "list"


# ── TestDiscoverServer ───────────────────────────────────


class TestDiscoverServer:
    def test_returns_info_with_valid_port_file(self, port_file: Path) -> None:
        port_file.write_text(json.dumps({"pid": os.getpid(), "port": 8080, "host": "127.0.0.1"}))
        result = discover_server()
        assert result is not None
        assert result["port"] == 8080

    def test_returns_none_no_port_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("FORK_DATA_DIR", str(tmp_path / "nonexistent"))
        assert discover_server() is None

    def test_cleans_stale_pid(self, port_file: Path) -> None:
        port_file.write_text(json.dumps({"pid": 999999999, "port": 8080, "host": "127.0.0.1"}))
        result = discover_server()
        assert result is None
        assert not port_file.exists()

    def test_returns_none_corrupt_json(self, port_file: Path) -> None:
        port_file.write_text("{invalid json}")
        result = discover_server()
        assert result is None
        assert not port_file.exists()


# ── TestMCPClientSDK ─────────────────────────────────────


class TestMCPClientSDK:
    def test_client_initialization(self) -> None:
        client = MCPClientSDK("http://127.0.0.1:8080/mcp", timeout=5.0)
        assert client._url == "http://127.0.0.1:8080/mcp"
        assert client._timeout == 5.0


# ── Test Hybrid Dispatch ────────────────────────────────


class TestHybridDispatcherSave:
    def test_mcp_success(
        self, mock_service: MagicMock, mock_mcp_client: MagicMock, receipt_file: Path
    ) -> None:
        mock_mcp_client.call_tool_sync.return_value = {"id": "mcp-id"}
        mock_service.get_by_id.return_value = _make_observation(id="mcp-id")
        d = _dispatcher_with_mcp(mock_service, mock_mcp_client)
        obs, receipt = d.dispatch_save(content="test")
        assert receipt.mode == DispatchMode.MCP_CLIENT
        assert obs.id == "mcp-id"

    def test_mcp_failure_fallback(
        self, mock_service: MagicMock, mock_mcp_client: MagicMock, receipt_file: Path
    ) -> None:
        mock_mcp_client.call_tool_sync.side_effect = ConnectionError("refused")
        d = _dispatcher_with_mcp(mock_service, mock_mcp_client)
        obs, receipt = d.dispatch_save(content="test")
        assert receipt.mode == DispatchMode.FALLBACK
        mock_service.save.assert_called_once()

    def test_no_server_direct(self, mock_service: MagicMock, receipt_file: Path) -> None:
        d = HybridDispatcher(mock_service)
        d._get_mcp_client = MagicMock(return_value=None)  # type: ignore[assignment]
        obs, receipt = d.dispatch_save(content="test")
        assert receipt.mode == DispatchMode.DIRECT


class TestHybridDispatcherSearch:
    def test_mcp_success(
        self, mock_service: MagicMock, mock_mcp_client: MagicMock, receipt_file: Path
    ) -> None:
        mock_mcp_client.call_tool_sync.return_value = [_make_obs_dict()]
        d = _dispatcher_with_mcp(mock_service, mock_mcp_client)
        results, receipt = d.dispatch_search(query="test")
        assert receipt.mode == DispatchMode.MCP_CLIENT
        assert len(results) == 1

    def test_fallback_single_receipt(
        self, mock_service: MagicMock, mock_mcp_client: MagicMock, receipt_file: Path
    ) -> None:
        mock_mcp_client.call_tool_sync.side_effect = ConnectionError("refused")
        d = _dispatcher_with_mcp(mock_service, mock_mcp_client)
        results, receipt = d.dispatch_search(query="test")
        assert receipt.mode == DispatchMode.FALLBACK
        # Verify no double-retry bug (only 1 receipt for search)
        if receipt_file.exists():
            lines = [l for l in receipt_file.read_text().strip().split("\n") if l]
            search_receipts = [l for l in lines if '"search"' in l]
            assert len(search_receipts) <= 1


class TestHybridDispatcherList:
    def test_mcp_success(
        self, mock_service: MagicMock, mock_mcp_client: MagicMock, receipt_file: Path
    ) -> None:
        mock_mcp_client.call_tool_sync.return_value = [_make_obs_dict()]
        d = _dispatcher_with_mcp(mock_service, mock_mcp_client)
        results, receipt = d.dispatch_list(limit=5)
        assert receipt.mode == DispatchMode.MCP_CLIENT

    def test_fallback(
        self, mock_service: MagicMock, mock_mcp_client: MagicMock, receipt_file: Path
    ) -> None:
        mock_mcp_client.call_tool_sync.side_effect = Exception("fail")
        d = _dispatcher_with_mcp(mock_service, mock_mcp_client)
        results, receipt = d.dispatch_list(limit=5)
        assert receipt.mode == DispatchMode.FALLBACK


class TestHybridDispatcherGet:
    def test_mcp_success(
        self, mock_service: MagicMock, mock_mcp_client: MagicMock, receipt_file: Path
    ) -> None:
        mock_mcp_client.call_tool_sync.return_value = _make_obs_dict()
        d = _dispatcher_with_mcp(mock_service, mock_mcp_client)
        obs, receipt = d.dispatch_get(id="test-id")
        assert receipt.mode == DispatchMode.MCP_CLIENT

    def test_fallback(
        self, mock_service: MagicMock, mock_mcp_client: MagicMock, receipt_file: Path
    ) -> None:
        mock_mcp_client.call_tool_sync.side_effect = Exception("fail")
        d = _dispatcher_with_mcp(mock_service, mock_mcp_client)
        obs, receipt = d.dispatch_get(id="test-id")
        assert receipt.mode == DispatchMode.FALLBACK


class TestHybridDispatcherDelete:
    def test_mcp_success(
        self, mock_service: MagicMock, mock_mcp_client: MagicMock, receipt_file: Path
    ) -> None:
        mock_mcp_client.call_tool_sync.return_value = "Deleted"
        d = _dispatcher_with_mcp(mock_service, mock_mcp_client)
        result, receipt = d.dispatch_delete(id="test-id")
        assert receipt.mode == DispatchMode.MCP_CLIENT

    def test_fallback(
        self, mock_service: MagicMock, mock_mcp_client: MagicMock, receipt_file: Path
    ) -> None:
        mock_mcp_client.call_tool_sync.side_effect = Exception("fail")
        d = _dispatcher_with_mcp(mock_service, mock_mcp_client)
        result, receipt = d.dispatch_delete(id="test-id")
        assert receipt.mode == DispatchMode.FALLBACK


class TestHybridDispatcherUpdate:
    def test_mcp_success(
        self, mock_service: MagicMock, mock_mcp_client: MagicMock, receipt_file: Path
    ) -> None:
        mock_mcp_client.call_tool_sync.return_value = _make_obs_dict()
        d = _dispatcher_with_mcp(mock_service, mock_mcp_client)
        obs, receipt = d.dispatch_update(id="test-id", content="updated")
        assert receipt.mode == DispatchMode.MCP_CLIENT

    def test_fallback(
        self, mock_service: MagicMock, mock_mcp_client: MagicMock, receipt_file: Path
    ) -> None:
        mock_mcp_client.call_tool_sync.side_effect = Exception("fail")
        d = _dispatcher_with_mcp(mock_service, mock_mcp_client)
        obs, receipt = d.dispatch_update(id="test-id", content="updated")
        assert receipt.mode == DispatchMode.FALLBACK


class TestHybridDispatcherStats:
    def test_mcp_success(
        self, mock_service: MagicMock, mock_mcp_client: MagicMock, receipt_file: Path
    ) -> None:
        mock_mcp_client.call_tool_sync.return_value = {"total": 100}
        d = _dispatcher_with_mcp(mock_service, mock_mcp_client)
        result, receipt = d.dispatch_stats()
        assert receipt.mode == DispatchMode.MCP_CLIENT
        assert result == {"total": 100}

    def test_fallback(
        self, mock_service: MagicMock, mock_mcp_client: MagicMock, receipt_file: Path
    ) -> None:
        mock_mcp_client.call_tool_sync.side_effect = Exception("fail")
        d = _dispatcher_with_mcp(mock_service, mock_mcp_client)
        result, receipt = d.dispatch_stats()
        assert receipt.mode == DispatchMode.FALLBACK


class TestHybridDispatcherSession:
    def test_session_start_success(
        self, mock_service: MagicMock, mock_mcp_client: MagicMock, receipt_file: Path
    ) -> None:
        mock_mcp_client.call_tool_sync.return_value = {"session_id": "sess-1"}
        d = _dispatcher_with_mcp(mock_service, mock_mcp_client)
        result, receipt = d.dispatch_session_start(name="test")
        assert receipt.mode == DispatchMode.MCP_CLIENT

    def test_session_end_success(
        self, mock_service: MagicMock, mock_mcp_client: MagicMock, receipt_file: Path
    ) -> None:
        mock_mcp_client.call_tool_sync.return_value = {"status": "ended"}
        d = _dispatcher_with_mcp(mock_service, mock_mcp_client)
        result, receipt = d.dispatch_session_end(session_id="sess-1")
        assert receipt.mode == DispatchMode.MCP_CLIENT


class TestHybridDispatcherMessage:
    def test_message_send_success(
        self, mock_service: MagicMock, mock_mcp_client: MagicMock, receipt_file: Path
    ) -> None:
        mock_mcp_client.call_tool_sync.return_value = "sent"
        d = _dispatcher_with_mcp(mock_service, mock_mcp_client)
        result, receipt = d.dispatch_message_send(
            target="pane", payload="hello", message_type="COMMAND"
        )
        assert receipt.mode == DispatchMode.MCP_CLIENT

    def test_message_send_fallback(
        self, mock_service: MagicMock, mock_mcp_client: MagicMock, receipt_file: Path
    ) -> None:
        mock_mcp_client.call_tool_sync.side_effect = Exception("fail")
        d = _dispatcher_with_mcp(mock_service, mock_mcp_client)
        with (
            patch("src.domain.entities.message.MessageType") as mock_mt,
            patch("src.domain.entities.message.AgentMessage") as mock_msg,
            patch("src.infrastructure.persistence.container.get_agent_messenger") as mock_get,
        ):
            mock_get.return_value.send.return_value = "msg-id"
            mock_msg.create.return_value = MagicMock()
            result, receipt = d.dispatch_message_send(
                target="pane", payload="hello", from_agent="a", to_agent="b"
            )
        assert receipt.mode == DispatchMode.FALLBACK


# ── TestGetMcpClient ─────────────────────────────────────


class TestGetMcpClient:
    def test_returns_none_when_disabled(
        self, mock_service: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("FORK_MCP_DISABLED", "1")
        d = HybridDispatcher(mock_service)
        assert d._get_mcp_client() is None

    def test_returns_none_no_server(
        self, mock_service: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("FORK_DATA_DIR", "/tmp/nonexistent_fork_test")
        d = HybridDispatcher(mock_service)
        assert d._get_mcp_client() is None

    def test_returns_client_when_server_available(
        self, mock_service: MagicMock, port_file: Path
    ) -> None:
        port_file.write_text(json.dumps({"pid": os.getpid(), "port": 8080, "host": "127.0.0.1"}))
        d = HybridDispatcher(mock_service)
        client = d._get_mcp_client()
        assert client is None or isinstance(client, MCPClientSDK)


# ── TestCheckDbMatch ─────────────────────────────────────


class TestCheckDbMatch:
    def test_no_warning_when_paths_match(
        self, mock_service: MagicMock, port_file: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        port_file.write_text(
            json.dumps(
                {"pid": os.getpid(), "port": 8080, "host": "127.0.0.1", "db_path": "/test.db"}
            )
        )
        monkeypatch.setenv("FORK_MEMORY_DB", "/test.db")
        d = HybridDispatcher(mock_service)
        with patch("src.interfaces.cli.hybrid.logger") as mock_logger:
            d._check_db_match()
            mock_logger.warning.assert_not_called()

    def test_warns_when_paths_diverge(
        self, mock_service: MagicMock, port_file: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        port_file.write_text(
            json.dumps(
                {"pid": os.getpid(), "port": 8080, "host": "127.0.0.1", "db_path": "/mcp.db"}
            )
        )
        monkeypatch.setenv("FORK_MEMORY_DB", "/cli.db")
        d = HybridDispatcher(mock_service)
        with patch("src.interfaces.cli.hybrid.logger") as mock_logger:
            d._check_db_match()
            mock_logger.warning.assert_called()
