"""Agent template entity for reusable agent definitions.

Adopted from pi-subagents AgentConfig pattern:
- 3-scope discovery (builtin/user/project)
- Frontmatter-parsed .md files
- Override layer for builtin agents
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class TemplateScope(StrEnum):
    """Where a template definition lives."""

    BUILTIN = "BUILTIN"  # Shipped with tmux_fork
    USER = "USER"  # ~/.pi/agent/fork-templates/agents/
    PROJECT = "PROJECT"  # <project>/.fork-templates/agents/


class TemplateStatus(StrEnum):
    """Template availability status."""

    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


@dataclass(frozen=True)
class AgentTemplate:
    """Reusable agent definition template.

    Inspired by pi-subagents AgentConfig:
    - name: identifier (maps to filename without .md)
    - description: what the agent does
    - model: provider/model string (e.g. "zai/glm-5-turbo")
    - system_prompt: the agent's prompt template
    - tools: list of tool names the agent can use
    - skills: list of skill-hub tags to resolve
    - scope: where the definition lives
    - status: ACTIVE or DISABLED
    - output: default output filename pattern
    - default_reads: files the agent should read by default
    - interactive: whether agent runs in interactive mode
    - max_depth: max sub-agent nesting depth
    - file_path: where the .md definition file lives
    - team_id: which team this template belongs to (optional)
    """

    id: str
    name: str
    description: str
    scope: TemplateScope
    status: TemplateStatus = TemplateStatus.ACTIVE
    model: str = ""
    system_prompt: str = ""
    tools: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()
    output: str = ""
    default_reads: tuple[str, ...] = ()
    interactive: bool = True
    max_depth: int = 1
    file_path: str = ""
    team_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id:
            raise ValueError("id must be a non-empty string")
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("name must be a non-empty string")
        if not isinstance(self.description, str):
            raise ValueError("description must be a string")
        if not isinstance(self.scope, TemplateScope):
            raise TypeError("scope must be a TemplateScope")
        if not isinstance(self.status, TemplateStatus):
            raise TypeError("status must be a TemplateStatus")
        if not isinstance(self.max_depth, int) or self.max_depth < 0:
            raise ValueError("max_depth must be a non-negative integer")

    def is_active(self) -> bool:
        return self.status == TemplateStatus.ACTIVE

    def to_frontmatter_dict(self) -> dict[str, object]:
        """Serialize to frontmatter-compatible dict for .md file writing."""
        result: dict[str, object] = {
            "name": self.name,
            "description": self.description,
            "model": self.model,
            "tools": self.tools,
            "skills": self.skills,
            "output": self.output,
            "default_reads": self.default_reads,
            "interactive": self.interactive,
            "max_depth": self.max_depth,
        }
        if self.team_id:
            result["team_id"] = self.team_id
        return result


@dataclass(frozen=True)
class TeamDefinition:
    """A team of agent templates that work together.

    Inspired by pi-subagents ChainConfig — a named group of
    agent templates with execution order and dependencies.
    """

    id: str
    name: str
    description: str
    agent_names: tuple[str, ...] = ()
    team_dir: str = ""  # directory containing the team's agents

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id:
            raise ValueError("id must be a non-empty string")
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("name must be a non-empty string")
