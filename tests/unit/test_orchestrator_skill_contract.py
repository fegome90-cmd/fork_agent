"""Orchestrator Skill Contract Tests — SDD tmux-orchestrator-runtime-alignment.

Verifies the orchestrator skill files at ~/.pi/agent/skills/tmux-fork-orchestrator/
declare MCP tools as the canonical interface and CLI as fallback/debug only.

These tests prevent skill regression where CLI-first wording sneaks back in
after refactors, which would mislead orchestrator agents into using CLI
commands as the primary interface.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

SKILL_ROOT = Path("~/.pi/agent/skills/tmux-fork-orchestrator").expanduser()
SKILL_MD = SKILL_ROOT / "SKILL.md"
PHASE_COMMON = SKILL_ROOT / "_contracts" / "phase-common.md"
MEMORY_COMMANDS = SKILL_ROOT / "resources" / "memory-commands.md"
PROTOCOL = SKILL_ROOT / "resources" / "protocol.md"
KNOWN_ISSUES = SKILL_ROOT / "resources" / "known-issues.md"


@pytest.fixture()
def skill_installed() -> None:
    """Skip if skill files are not installed at expected path."""
    if not SKILL_MD.exists():
        pytest.skip("Skill not installed at ~/.pi/agent/skills/tmux-fork-orchestrator/")


class TestSkillMCPFirstDeclaration:
    """SKILL.md must declare MCP as canonical interface."""

    def test_skill_md_exists(self, skill_installed: None) -> None:
        assert SKILL_MD.is_file()

    def test_declares_mcp_first(self, skill_installed: None) -> None:
        content = SKILL_MD.read_text()
        assert "Canonical Interface: MCP-First" in content, (
            "SKILL.md must have 'Canonical Interface: MCP-First' section header."
        )

    def test_declares_memory_mcp_as_canonical_backend(self, skill_installed: None) -> None:
        content = SKILL_MD.read_text()
        assert "memory-mcp" in content, (
            "SKILL.md must reference 'memory-mcp' as the canonical backend entry point."
        )

    def test_declares_cli_as_fallback(self, skill_installed: None) -> None:
        content = SKILL_MD.read_text()
        assert "fallback" in content.lower() or "debug only" in content.lower(), (
            "SKILL.md must describe CLI commands as fallback/debug only."
        )

    def test_declares_tool_registry_authority(self, skill_installed: None) -> None:
        content = SKILL_MD.read_text()
        assert "__init__.py" in content and "21" in content, (
            "SKILL.md must reference the tool registry authority and count."
        )


class TestPhaseCommonMCPFirst:
    """phase-common.md sections B and C must use MCP-first wording."""

    def test_phase_common_exists(self, skill_installed: None) -> None:
        assert PHASE_COMMON.is_file()

    def test_section_b_says_canonical_mcp(self, skill_installed: None) -> None:
        content = PHASE_COMMON.read_text()
        assert "Canonical" in content and "memory_search" in content, (
            "phase-common.md §B must declare memory_search MCP tool as canonical."
        )

    def test_section_c_says_canonical_mcp(self, skill_installed: None) -> None:
        content = PHASE_COMMON.read_text()
        assert "memory_save" in content, (
            "phase-common.md §C must declare memory_save MCP tool as canonical."
        )

    def test_cli_described_as_fallback(self, skill_installed: None) -> None:
        content = PHASE_COMMON.read_text()
        assert "CLI Fallback" in content or "debug/recovery only" in content, (
            "phase-common.md must describe CLI as 'Fallback' or 'debug/recovery only'."
        )

    def test_transport_aware_project_detection(self, skill_installed: None) -> None:
        content = PHASE_COMMON.read_text()
        assert "stdio" in content.lower(), (
            "phase-common.md must mention stdio transport for project auto-detection."
        )


class TestMemoryCommandsSplit:
    """memory-commands.md must split MCP canonical vs CLI fallback."""

    def test_memory_commands_exists(self, skill_installed: None) -> None:
        assert MEMORY_COMMANDS.is_file()

    def test_has_mcp_tools_section(self, skill_installed: None) -> None:
        content = MEMORY_COMMANDS.read_text()
        assert "MCP Tools" in content and "Canonical" in content, (
            "memory-commands.md must have 'MCP Tools — Canonical (Primary)' section."
        )

    def test_has_cli_fallback_section(self, skill_installed: None) -> None:
        content = MEMORY_COMMANDS.read_text()
        assert "CLI" in content and "Fallback" in content, (
            "memory-commands.md must have CLI fallback section."
        )

    def test_lists_17_memory_tools(self, skill_installed: None) -> None:
        content = MEMORY_COMMANDS.read_text()
        memory_tool_mentions = re.findall(r"memory_\w+", content)
        unique_memory = set(memory_tool_mentions)
        assert len(unique_memory) >= 15, (
            f"memory-commands.md must list memory_* MCP tools. "
            f"Found {len(unique_memory)} unique: {sorted(unique_memory)}"
        )

    def test_lists_4_messaging_tools(self, skill_installed: None) -> None:
        content = MEMORY_COMMANDS.read_text()
        fork_tool_mentions = re.findall(r"fork_\w+", content)
        unique_fork = set(fork_tool_mentions)
        assert len(unique_fork) >= 4, (
            f"memory-commands.md must list fork_* MCP tools. "
            f"Found {len(unique_fork)} unique: {sorted(unique_fork)}"
        )

    def test_transport_table_present(self, skill_installed: None) -> None:
        content = MEMORY_COMMANDS.read_text()
        assert "stdio" in content and "SSE" in content, (
            "memory-commands.md must have transport-aware project resolution table."
        )


class TestProtocolMCPFirst:
    """protocol.md phases must use MCP-first persistence wording."""

    def test_protocol_exists(self, skill_installed: None) -> None:
        assert PROTOCOL.is_file()

    def test_phase_2_mcp_first(self, skill_installed: None) -> None:
        content = PROTOCOL.read_text()
        phase2 = content[content.find("Phase 2:") : content.find("Phase 3:")]
        assert "MCP Tool (Canonical)" in phase2 or "Canonical: MCP" in phase2, (
            "protocol.md Phase 2 must declare MCP as canonical."
        )

    def test_phase_5_mcp_first(self, skill_installed: None) -> None:
        content = PROTOCOL.read_text()
        phase5 = content[content.find("Phase 5:") : content.find("Phase 5.5:")]
        assert "MCP Tool (Canonical)" in phase5 or "Canonical: MCP" in phase5, (
            "protocol.md Phase 5 must declare MCP as canonical."
        )

    def test_phase_6_mcp_first(self, skill_installed: None) -> None:
        content = PROTOCOL.read_text()
        phase6 = content[content.find("Phase 6:") : content.find("Phase 6.2:")]
        assert "MCP Tool (Canonical)" in phase6 or "Canonical: MCP" in phase6, (
            "protocol.md Phase 6 must declare MCP as canonical."
        )


class TestKnownIssuesTransportDocs:
    """known-issues.md must document transport-specific project resolution."""

    def test_known_issues_exists(self, skill_installed: None) -> None:
        assert KNOWN_ISSUES.is_file()

    def test_has_transport_project_resolution_issue(self, skill_installed: None) -> None:
        content = KNOWN_ISSUES.read_text()
        assert "stdio" in content and "SSE" in content, (
            "known-issues.md must document transport-specific project auto-detection."
        )
        assert "project" in content.lower() and "explicit" in content.lower(), (
            "known-issues.md must describe explicit project param override."
        )
