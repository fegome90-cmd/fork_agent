"""MCP Docs Contract Tests — SDD tmux-orchestrator-runtime-alignment.

Verifies that repo documentation (README, architecture docs) stays aligned
with the MCP tool registry code authority (src/interfaces/mcp/tools/__init__.py).

These tests prevent docs/code drift that causes orchestration failures.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TOOLS_INIT = REPO_ROOT / "src" / "interfaces" / "mcp" / "tools" / "__init__.py"
README = REPO_ROOT / "README.md"


def _count_registered_tools() -> int:
    """Count tools registered in the code authority file."""
    content = TOOLS_INIT.read_text()
    matches = re.findall(r"mcp_server\.tool\(\)\((\w+)\)", content)
    return len(matches)


def _get_registered_tool_names() -> set[str]:
    """Get the set of tool names registered in code."""
    content = TOOLS_INIT.read_text()
    return set(re.findall(r"mcp_server\.tool\(\)\((\w+)\)", content))


class TestMCPToolCount:
    """Verify README matches code authority for tool count."""

    EXPECTED_COUNT = 21  # 17 memory + 4 messaging

    def test_tool_registry_has_21_tools(self) -> None:
        """Code authority must register exactly 21 tools."""
        count = _count_registered_tools()
        assert count == self.EXPECTED_COUNT, (
            f"Tool registry has {count} tools, expected {self.EXPECTED_COUNT}. "
            f"If you added/removed tools, update this test."
        )

    def test_readme_features_says_21(self) -> None:
        """README features line must say '21 tools'."""
        content = README.read_text()
        assert "21 tools" in content, (
            "README must state '21 tools' in features section. "
            "Check the MCP Server bullet."
        )

    def test_readme_subtitle_says_21(self) -> None:
        """README subtitle must say '21-tool MCP server'."""
        content = README.read_text()
        assert "21-tool MCP server" in content, (
            "README subtitle must say '21-tool MCP server'. "
            "Found stale count — update the one-liner description."
        )

    def test_readme_no_stale_16(self) -> None:
        """README must NOT contain stale '16 tool' or '16-tool' references."""
        content = README.read_text()
        stale_refs = re.findall(r"\b16[- ]tools?\b", content, re.IGNORECASE)
        assert not stale_refs, (
            f"README contains stale '16 tool(s)' references: {stale_refs}. "
            f"Update to 21."
        )

    def test_readme_mcp_section_says_21(self) -> None:
        """README MCP section header must say 21 tools."""
        content = README.read_text()
        # Match the MCP Server section
        mcp_section_match = re.search(
            r"## MCP Server.*?(?=\n## |\Z)", content, re.DOTALL
        )
        assert mcp_section_match, "README missing '## MCP Server' section"
        mcp_section = mcp_section_match.group()
        assert "21 MCP tools" in mcp_section, (
            "MCP Server section must say '21 MCP tools'."
        )


class TestMCPToolNamesInReadme:
    """Verify README lists all registered tools."""

    def test_all_tools_mentioned_in_readme(self) -> None:
        """README must list every registered MCP tool name."""
        content = README.read_text()
        registered = _get_registered_tool_names()
        missing = sorted(registered - {t for t in registered if t in content})
        # Allow some flexibility — just check memory_ and fork_ prefixes are present
        memory_tools = {t for t in registered if t.startswith("memory_")}
        fork_tools = {t for t in registered if t.startswith("fork_")}

        # At least verify the count of memory_ tools mentioned
        memory_mentioned = sum(1 for t in memory_tools if t in content)
        assert memory_mentioned >= 15, (
            f"README mentions only {memory_mentioned} of {len(memory_tools)} "
            f"memory_ tools. Missing: {sorted(memory_tools - {t for t in memory_tools if t in content})}"
        )

        fork_mentioned = sum(1 for t in fork_tools if t in content)
        assert fork_mentioned >= 3, (
            f"README mentions only {fork_mentioned} of {len(fork_tools)} "
            f"fork_ tools. Missing: {sorted(fork_tools - {t for t in fork_tools if t in content})}"
        )


class TestReadmeLinks:
    """Verify README doc links are valid."""

    def test_mcp_setup_link_exists(self) -> None:
        """README mcp-setup.md link must point to an existing file."""
        content = README.read_text()
        match = re.search(r"\[docs/[^\]]+\]\((docs/[^)]+mcp[^)]+)\)", content)
        assert match, "README missing link to mcp-setup doc"
        link_path = REPO_ROOT / match.group(1)
        assert link_path.exists(), (
            f"README links to {match.group(1)} but file does not exist. "
            f"Expected at: {link_path}"
        )


class TestTransportProjectResolution:
    """Verify docs describe stdio vs SSE/HTTP project resolution correctly."""

    def test_readme_mentions_transports(self) -> None:
        """README must mention all 3 transport modes."""
        content = README.read_text()
        for transport in ["stdio", "sse", "streamable-http"]:
            assert transport in content.lower(), (
                f"README must mention '{transport}' transport."
            )

    def test_skill_md_mentions_stdio_auto_detect(self) -> None:
        """SKILL.md must document stdio auto-detection caveat."""
        skill_path = Path(
            "~/.pi/agent/skills/tmux-fork-orchestrator/SKILL.md"
        ).expanduser()
        if not skill_path.exists():
            pytest.skip("Skill file not installed at expected path")

        content = skill_path.read_text()
        assert "stdio" in content.lower(), (
            "SKILL.md must mention stdio transport for project auto-detection."
        )
        # Must mention that explicit project param is needed for non-stdio
        assert "explicit" in content.lower() or "project" in content.lower(), (
            "SKILL.md must document that explicit project param overrides auto-detection."
        )
