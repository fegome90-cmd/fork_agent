"""Unit tests for MCP server setup."""

from __future__ import annotations

from unittest.mock import patch

from src.interfaces.mcp.server import create_mcp_server


class TestServerCreation:
    def test_creates_fastmcp_instance(self) -> None:
        mcp = create_mcp_server()
        assert mcp.name == "memory-server"

    @patch("src.interfaces.mcp.server._configure_logging")
    def test_configure_logging_called(self, mock_log: object) -> None:
        create_mcp_server()
        mock_log.assert_called_once()
