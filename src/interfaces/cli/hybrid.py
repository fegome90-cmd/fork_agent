"""Hybrid dispatch: routes CLI commands through MCP server when available,
falls back to direct service calls transparently. All 17 MCP-routable commands."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.domain.entities.observation import Observation

if TYPE_CHECKING:
    from mcp.client.session import ClientSession

logger = logging.getLogger("memory-hybrid")


def _get_default_db_path() -> Path:
    """Resolve the default DB path without importing the full container."""
    from src.infrastructure.persistence.container import get_default_db_path

    return get_default_db_path()


class DispatchMode(StrEnum):
    MCP_CLIENT = "mcp_client"
    DIRECT = "direct"
    FALLBACK = "direct_fallback"


@dataclass(frozen=True)
class DispatchReceipt:
    mode: DispatchMode
    command: str
    latency_ms: float
    reason: str | None = None
    server_pid: int | None = None


def _write_receipt(receipt: DispatchReceipt) -> None:
    receipt_dir = Path(os.environ.get("FORK_DATA_DIR", os.path.expanduser("~/.local/share/fork")))
    receipt_dir.mkdir(parents=True, exist_ok=True)
    with open(receipt_dir / ".hybrid-receipts.jsonl", "a") as f:
        f.write(
            json.dumps(
                {
                    "mode": receipt.mode.value,
                    "command": receipt.command,
                    "latency_ms": round(receipt.latency_ms, 1),
                    "reason": receipt.reason,
                    "server_pid": receipt.server_pid,
                    "timestamp": time.time(),
                }
            )
            + "\n"
        )


def _get_port_file() -> Path:
    data_dir = Path(os.environ.get("FORK_DATA_DIR", os.path.expanduser("~/.local/share/fork")))
    return data_dir / ".mcp-server.json"


def discover_server() -> dict[str, Any] | None:
    """Read port file, verify PID alive, return server info or None. Cleans stale files."""
    port_file = _get_port_file()
    if not port_file.exists():
        return None
    try:
        info: dict[str, Any] = json.loads(port_file.read_text())
        pid = info.get("pid", 0)
        if pid <= 0:
            return None
        os.kill(pid, 0)  # Raises ProcessLookupError if dead
        return info
    except (json.JSONDecodeError, ProcessLookupError, PermissionError, KeyError, OSError):
        try:
            port_file.unlink()
        except OSError:
            pass
        return None


def _to_observations(result: Any) -> list[Observation]:
    if not isinstance(result, list):
        return []
    observations: list[Observation] = []
    for o in result:
        try:
            observations.append(
                Observation(**{k: v for k, v in o.items() if k in Observation.__dataclass_fields__})
            )
        except (TypeError, KeyError):
            continue
    return observations


class MCPClientSDK:
    """MCP client using official SDK (handles SSE + session management internally)."""

    def __init__(self, url: str, timeout: float = 10.0) -> None:
        self._url = url
        self._timeout = timeout
        self._session: ClientSession | None = None
        self._http_cm: Any = None
        self._session_cm: Any = None

    def call_tool_sync(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Synchronous wrapper — CLI is sync, SDK is async."""
        return asyncio.run(self._call_tool(tool_name, arguments))

    async def _ensure_session(self) -> ClientSession:
        """Get or create a cached MCP session."""
        if self._session is not None:
            return self._session
        from mcp.client.session import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        # Use local vars first — only commit to instance on success
        http_cm = streamablehttp_client(url=self._url, timeout=self._timeout)
        read, write, _ = await http_cm.__aenter__()
        session_cm = ClientSession(read, write)
        session: ClientSession = await session_cm.__aenter__()
        await session.initialize()
        # Success — commit to instance
        self._http_cm = http_cm
        self._session_cm = session_cm
        self._session = session
        return session

    async def _call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        session = await self._ensure_session()
        result = await session.call_tool(tool_name, arguments)
        if result.isError:
            raise RuntimeError(f"MCP tool error: {result.content}")
        for content in result.content:
            if hasattr(content, "text"):
                text_value = getattr(content, "text", None)
                if isinstance(text_value, str):
                    return json.loads(text_value)
        return None

    async def close(self) -> None:
        """Clean up cached session."""
        if self._session_cm is not None:
            try:
                await self._session_cm.__aexit__(None, None, None)
            except Exception:
                pass
        if self._http_cm is not None:
            try:
                await self._http_cm.__aexit__(None, None, None)
            except Exception:
                pass
        self._session = None
        self._session_cm = None
        self._http_cm = None


class HybridDispatcher:
    """Routes all 17 MCP-routable commands through MCP when available, direct otherwise."""

    @staticmethod
    def _validate_content(content: str) -> None:
        """Validate content before dispatch (null bytes, empty check)."""
        if not content or not content.strip():
            raise ValueError("Content cannot be empty")
        if "\x00" in content:
            raise ValueError("Content contains null bytes")

    def __init__(self, memory_service: Any, db_path: str | None = None) -> None:
        self._service = memory_service
        self._mcp_client: MCPClientSDK | None = None
        self._server_info: dict | None = None
        self._db_path = db_path
        self._cli_db_path = db_path or os.environ.get("FORK_MEMORY_DB", str(_get_default_db_path()))
        self._check_db_match()

    def _check_db_match(self) -> None:
        """Warn if CLI and MCP server use different databases."""
        info = discover_server()
        if info is None:
            return
        mcp_db = info.get("db_path")
        if mcp_db and mcp_db != self._cli_db_path:
            logger.warning(
                "DB path mismatch: CLI=%s, MCP=%s. Hybrid dispatch may return stale data.",
                self._cli_db_path,
                mcp_db,
            )

    def _get_mcp_client(self) -> MCPClientSDK | None:
        if os.environ.get("FORK_MCP_DISABLED") == "1":
            return None
        info = discover_server()
        if info is None:
            if os.environ.get("FORK_MCP_REQUIRE") == "1":
                raise RuntimeError(
                    "FORK_MCP_REQUIRE=1 but no MCP server available. Run 'memory mcp start' first."
                )
            return None
        self._server_info = info
        # Reuse cached client if URL matches
        if self._mcp_client is not None and self._mcp_client._url.endswith(
            f":{info.get('port', 8080)}/mcp"
        ):
            return self._mcp_client
        self._mcp_client = MCPClientSDK(
            f"http://{info.get('host', '127.0.0.1')}:{info.get('port', 8080)}/mcp"
        )
        return self._mcp_client

    def _track_dispatch(self, receipt: DispatchReceipt) -> None:
        """Track hybrid dispatch via telemetry."""
        try:
            from src.infrastructure.persistence.container import get_telemetry_service

            db = self._db_path or os.environ.get("FORK_MEMORY_DB")
            if not db:
                data_dir = os.environ.get(
                    "FORK_DATA_DIR", os.path.expanduser("~/.local/share/fork")
                )
                db = str(Path(data_dir) / "memory.db")
            telemetry = get_telemetry_service(Path(db))
            telemetry.track_hybrid_dispatch(
                command=receipt.command,
                mode=receipt.mode.value,
                latency_ms=receipt.latency_ms,
                server_pid=receipt.server_pid,
                reason=receipt.reason,
            )
            telemetry.flush()
        except Exception:
            logger.debug("telemetry tracking failed", exc_info=True)

    def _record(self, receipt: DispatchReceipt) -> None:
        """Write receipt file and track telemetry."""
        _write_receipt(receipt)
        self._track_dispatch(receipt)

    def _on_mcp_error(self, error: Exception) -> None:
        """Re-raise if FORK_MCP_REQUIRE=1, otherwise silently fallback."""
        if os.environ.get("FORK_MCP_REQUIRE") == "1":
            raise RuntimeError(f"MCP call failed (FORK_MCP_REQUIRE=1): {error}") from error

    def _mcp_receipt(self, start: float, command: str) -> DispatchReceipt:
        return DispatchReceipt(
            mode=DispatchMode.MCP_CLIENT,
            command=command,
            latency_ms=(time.monotonic() - start) * 1000,
            server_pid=self._server_info.get("pid") if self._server_info else None,
        )

    def _direct_receipt(self, start: float, command: str, client: Any) -> DispatchReceipt:
        reason = None if client is None else "protocol_error"
        mode = DispatchMode.DIRECT if client is None else DispatchMode.FALLBACK
        return DispatchReceipt(
            mode=mode,
            command=command,
            latency_ms=(time.monotonic() - start) * 1000,
            reason=reason,
        )

    def _mcp_call(self, tool: str, kwargs: dict, start: float, cmd: str) -> Any | None:
        """Attempt MCP call. Returns result or None (fallback signal)."""
        client = self._get_mcp_client()
        if client is None:
            return None
        try:
            result = client.call_tool_sync(tool, kwargs)
            receipt = self._mcp_receipt(start, cmd)
            self._record(receipt)
            return result
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Phase 1 — save and list (unchanged)
    # ------------------------------------------------------------------

    def dispatch_save(self, **kwargs: Any) -> tuple[Observation, DispatchReceipt]:
        self._validate_content(kwargs.get("content", ""))
        start = time.monotonic()
        client = self._get_mcp_client()
        if client is not None:
            try:
                result = client.call_tool_sync("memory_save", kwargs)
                obs = self._service.get_by_id(result["id"])
                receipt = self._mcp_receipt(start, "save")
                self._record(receipt)
                return obs, receipt
            except Exception as e:
                self._on_mcp_error(e)
        obs = self._service.save(**kwargs)
        receipt = self._direct_receipt(start, "save", client)
        self._record(receipt)
        return obs, receipt

    def dispatch_list(self, **kwargs: Any) -> tuple[list[Observation], DispatchReceipt]:
        start = time.monotonic()
        client = self._get_mcp_client()
        if client is not None:
            try:
                result = client.call_tool_sync("memory_list", kwargs)
                receipt = self._mcp_receipt(start, "list")
                self._record(receipt)
                return _to_observations(result), receipt
            except Exception as e:
                self._on_mcp_error(e)
        results = self._service.get_recent(**kwargs)
        receipt = self._direct_receipt(start, "list", client)
        self._record(receipt)
        return results, receipt

    # ------------------------------------------------------------------
    # Group A — ctx.obj MemoryService commands
    # ------------------------------------------------------------------

    def dispatch_search(self, **kwargs: Any) -> tuple[list[Observation], DispatchReceipt]:
        start = time.monotonic()
        client = self._get_mcp_client()
        if client is not None:
            try:
                result = client.call_tool_sync("memory_search", kwargs)
                receipt = self._mcp_receipt(start, "search")
                self._record(receipt)
                return _to_observations(result), receipt
            except Exception as e:
                self._on_mcp_error(e)
        observations = self._service.search(**kwargs)
        receipt = self._direct_receipt(start, "search", client)
        self._record(receipt)
        return observations, receipt

    def dispatch_get(self, **kwargs: Any) -> tuple[Observation, DispatchReceipt]:
        start = time.monotonic()
        client = self._get_mcp_client()
        if client is not None:
            try:
                result = client.call_tool_sync("memory_get", kwargs)
                obs = Observation(**result) if isinstance(result, dict) else result
                receipt = self._mcp_receipt(start, "get")
                self._record(receipt)
                return obs, receipt
            except Exception as e:
                self._on_mcp_error(e)
        obs = self._service.get_by_id(kwargs["id"])
        receipt = self._direct_receipt(start, "get", client)
        self._record(receipt)
        return obs, receipt

    def dispatch_delete(self, **kwargs: Any) -> tuple[str, DispatchReceipt]:
        start = time.monotonic()
        client = self._get_mcp_client()
        obs_id = kwargs.get("id", kwargs.get("observation_id", ""))
        if client is not None:
            try:
                result = client.call_tool_sync("memory_delete", kwargs)
                deleted_id = result.get("id", obs_id) if isinstance(result, dict) else obs_id
                receipt = self._mcp_receipt(start, "delete")
                self._record(receipt)
                return deleted_id, receipt
            except Exception as e:
                self._on_mcp_error(e)
        self._service.delete(obs_id)
        receipt = self._direct_receipt(start, "delete", client)
        self._record(receipt)
        return obs_id, receipt

    def dispatch_update(self, **kwargs: Any) -> tuple[Observation, DispatchReceipt]:
        start = time.monotonic()
        client = self._get_mcp_client()
        if client is not None:
            try:
                result = client.call_tool_sync("memory_update", kwargs)
                obs = Observation(**result) if isinstance(result, dict) else result
                receipt = self._mcp_receipt(start, "update")
                self._record(receipt)
                return obs, receipt
            except Exception as e:
                self._on_mcp_error(e)
        obs = self._service.update(**kwargs)
        receipt = self._direct_receipt(start, "update", client)
        self._record(receipt)
        return obs, receipt

    def dispatch_context(self, **kwargs: Any) -> tuple[list[Observation], DispatchReceipt]:
        start = time.monotonic()
        client = self._get_mcp_client()
        if client is not None:
            try:
                result = client.call_tool_sync("memory_context", kwargs)
                receipt = self._mcp_receipt(start, "context")
                self._record(receipt)
                return _to_observations(result), receipt
            except Exception as e:
                self._on_mcp_error(e)
        results = self._service.get_recent(**kwargs)
        receipt = self._direct_receipt(start, "context", client)
        self._record(receipt)
        return results, receipt

    # ------------------------------------------------------------------
    # Group B — Additional services (lazy imports)
    # ------------------------------------------------------------------

    def dispatch_retrieve(self, **kwargs: Any) -> tuple[list[Observation], DispatchReceipt]:
        start = time.monotonic()
        client = self._get_mcp_client()
        if client is not None:
            try:
                result = client.call_tool_sync("memory_retrieve", kwargs)
                receipt = self._mcp_receipt(start, "retrieve")
                self._record(receipt)
                return _to_observations(result), receipt
            except Exception as e:
                self._on_mcp_error(e)
        from src.infrastructure.persistence.container import get_repository
        from src.infrastructure.retrieval.v2.enhanced_search import EnhancedRetrievalSearchService

        repository = get_repository()
        svc = EnhancedRetrievalSearchService(repository)  # type: ignore[arg-type]
        results = svc.search(
            query=kwargs.get("query", ""),
            limit=kwargs.get("limit"),
            project=kwargs.get("project"),
            type=kwargs.get("type"),
        )
        receipt = self._direct_receipt(start, "retrieve", client)
        self._record(receipt)
        return results, receipt

    def dispatch_stats(self, **kwargs: Any) -> tuple[dict, DispatchReceipt]:
        start = time.monotonic()
        client = self._get_mcp_client()
        if client is not None:
            try:
                result = client.call_tool_sync("memory_stats", kwargs)
                receipt = self._mcp_receipt(start, "stats")
                self._record(receipt)
                return result, receipt
            except Exception as e:
                self._on_mcp_error(e)
        from src.interfaces.cli.dependencies import get_health_check_service

        svc = get_health_check_service()
        stats = svc.get_stats()
        receipt = self._direct_receipt(start, "stats", client)
        self._record(receipt)
        return stats, receipt

    def dispatch_session_start(self, **kwargs: Any) -> tuple[dict, DispatchReceipt]:
        start = time.monotonic()
        client = self._get_mcp_client()
        if client is not None:
            try:
                result = client.call_tool_sync("memory_session_start", kwargs)
                receipt = self._mcp_receipt(start, "session_start")
                self._record(receipt)
                return result, receipt
            except Exception as e:
                self._on_mcp_error(e)
        from src.interfaces.cli.dependencies import get_session_service

        svc = get_session_service()
        session = svc.start_session(
            agent_name=kwargs.get("agent_name", ""),
            project=kwargs.get("project"),
        )
        result = {"session_id": session.id, "status": "started"}
        receipt = self._direct_receipt(start, "session_start", client)
        self._record(receipt)
        return result, receipt

    def dispatch_session_end(self, **kwargs: Any) -> tuple[dict, DispatchReceipt]:
        start = time.monotonic()
        client = self._get_mcp_client()
        if client is not None:
            try:
                result = client.call_tool_sync("memory_session_end", kwargs)
                receipt = self._mcp_receipt(start, "session_end")
                self._record(receipt)
                return result, receipt
            except Exception as e:
                self._on_mcp_error(e)
        from src.interfaces.cli.dependencies import get_session_service

        svc = get_session_service()
        session = svc.end_session(session_id=kwargs["session_id"], summary=kwargs.get("summary"))
        result = {"session_id": session.id, "status": "ended"}
        receipt = self._direct_receipt(start, "session_end", client)
        self._record(receipt)
        return result, receipt

    def dispatch_message_send(self, **kwargs: Any) -> tuple[str, DispatchReceipt]:
        start = time.monotonic()
        client = self._get_mcp_client()
        if client is not None:
            try:
                result = client.call_tool_sync("fork_message_send", kwargs)
                msg_id = result if isinstance(result, str) else str(result)
                receipt = self._mcp_receipt(start, "message_send")
                self._record(receipt)
                return msg_id, receipt
            except Exception as e:
                self._on_mcp_error(e)
        from src.application.services.messaging.agent_messenger import AgentMessenger
        from src.domain.entities.message import AgentMessage, MessageType
        from src.infrastructure.persistence.container import get_agent_messenger

        messenger: AgentMessenger = get_agent_messenger()
        msg = AgentMessage.create(
            from_agent=kwargs.get("from_agent", ""),
            to_agent=kwargs.get("to_agent", ""),
            message_type=MessageType[kwargs.get("message_type", "COMMAND")],
            payload=kwargs.get("payload", ""),
        )
        messenger.send(msg)
        receipt = self._direct_receipt(start, "message_send", client)
        self._record(receipt)
        return msg.id, receipt

    def dispatch_message_receive(self, **kwargs: Any) -> tuple[list, DispatchReceipt]:
        start = time.monotonic()
        client = self._get_mcp_client()
        if client is not None:
            try:
                result = client.call_tool_sync("fork_message_receive", kwargs)
                receipt = self._mcp_receipt(start, "message_receive")
                self._record(receipt)
                return result if isinstance(result, list) else [], receipt
            except Exception as e:
                self._on_mcp_error(e)
        from src.infrastructure.persistence.container import get_agent_messenger

        messenger = get_agent_messenger()
        messages = messenger.get_messages(
            agent_id=kwargs.get("agent_id", ""),
            limit=kwargs.get("limit", 50),
        )
        result = [{"id": m.id, "from_agent": m.from_agent, "payload": m.payload} for m in messages]
        receipt = self._direct_receipt(start, "message_receive", client)
        self._record(receipt)
        return result, receipt

    def dispatch_message_broadcast(self, **kwargs: Any) -> tuple[int, DispatchReceipt]:
        start = time.monotonic()
        client = self._get_mcp_client()
        if client is not None:
            try:
                result = client.call_tool_sync("fork_message_broadcast", kwargs)
                count = result if isinstance(result, int) else int(result)
                receipt = self._mcp_receipt(start, "message_broadcast")
                self._record(receipt)
                return count, receipt
            except Exception as e:
                self._on_mcp_error(e)
        from src.infrastructure.persistence.container import get_agent_messenger

        messenger = get_agent_messenger()
        count = messenger.broadcast(
            from_agent=kwargs.get("from_agent", ""),
            payload=kwargs.get("payload", ""),
        )
        receipt = self._direct_receipt(start, "message_broadcast", client)
        self._record(receipt)
        return count, receipt

    def dispatch_message_history(self, **kwargs: Any) -> tuple[list, DispatchReceipt]:
        start = time.monotonic()
        client = self._get_mcp_client()
        if client is not None:
            try:
                result = client.call_tool_sync("fork_message_history", kwargs)
                receipt = self._mcp_receipt(start, "message_history")
                self._record(receipt)
                return result if isinstance(result, list) else [], receipt
            except Exception as e:
                self._on_mcp_error(e)
        from src.infrastructure.persistence.container import get_agent_messenger

        messenger = get_agent_messenger()
        messages = messenger.get_history(
            agent_id=kwargs.get("agent_id", ""),
            limit=kwargs.get("limit", 100),
        )
        result = [{"id": m.id, "from_agent": m.from_agent, "payload": m.payload} for m in messages]
        receipt = self._direct_receipt(start, "message_history", client)
        self._record(receipt)
        return result, receipt

    def dispatch_message_cleanup(self, **kwargs: Any) -> tuple[str, DispatchReceipt]:
        start = time.monotonic()
        client = self._get_mcp_client()
        if client is not None:
            try:
                result = client.call_tool_sync("fork_message_cleanup", kwargs)
                msg = str(result) if result else "Cleanup complete"
                receipt = self._mcp_receipt(start, "message_cleanup")
                self._record(receipt)
                return msg, receipt
            except Exception as e:
                self._on_mcp_error(e)
        from src.application.services.messaging.message_protocol import cleanup_temp_files
        from src.infrastructure.persistence.container import get_agent_messenger

        messenger = get_agent_messenger()
        db_count = messenger.store.cleanup_expired()
        fs_count = cleanup_temp_files(max_age_seconds=kwargs.get("max_age", 300))
        msg = f"Database: {db_count} messages removed, Filesystem: {fs_count} files removed"
        receipt = self._direct_receipt(start, "message_cleanup", client)
        self._record(receipt)
        return msg, receipt

    def dispatch_project_merge(self, **kwargs: Any) -> tuple[dict, DispatchReceipt]:
        start = time.monotonic()
        client = self._get_mcp_client()
        if client is not None:
            try:
                result = client.call_tool_sync("memory_merge_projects", kwargs)
                receipt = self._mcp_receipt(start, "project_merge")
                self._record(receipt)
                return result, receipt
            except Exception as e:
                self._on_mcp_error(e)
        result = self._service.merge_projects(
            from_projects=kwargs.get("from_projects", ""),
            to_project=kwargs.get("to_project", ""),
        )
        receipt = self._direct_receipt(start, "project_merge", client)
        self._record(receipt)
        return result, receipt

    def dispatch_timeline(self, **kwargs: Any) -> tuple[list[Observation], DispatchReceipt]:
        start = time.monotonic()
        client = self._get_mcp_client()
        if client is not None:
            try:
                result = client.call_tool_sync("memory_timeline", kwargs)
                receipt = self._mcp_receipt(start, "timeline")
                self._record(receipt)
                return _to_observations(result), receipt
            except Exception as e:
                self._on_mcp_error(e)
        run_id = kwargs.get("run_id", kwargs.get("run", ""))
        scan_limit = kwargs.get("scan_limit", 1000)
        observations = self._service.get_recent(limit=scan_limit, offset=0)
        filtered = [
            obs for obs in observations if obs.metadata and obs.metadata.get("run_id") == run_id
        ]
        filtered.sort(key=lambda o: o.timestamp)
        receipt = self._direct_receipt(start, "timeline", client)
        self._record(receipt)
        return filtered, receipt
