"""Filesystem discovery for agent templates.

Reads .md agent definition files from 3 scopes:
1. BUILTIN: shipped with tmux_fork package
2. USER: ~/.pi/agent/fork-templates/agents/
3. PROJECT: <cwd>/.fork-templates/agents/

File format (frontmatter + body):
---
name: explorer
description: Explore codebase sections
model: zai/glm-5-turbo
tools: [memory, ctx, skill-hub]
skills: [codebase-explorer]
output: /tmp/explorer-{name}.md
default_reads: [README.md, AGENTS.md]
interactive: true
max_depth: 1
team_id: ""
---

You are an expert codebase explorer...
"""

from __future__ import annotations

import re
from pathlib import Path

from src.domain.entities.agent_template import (
    AgentTemplate,
    TemplateScope,
)

# Validate template names — alphanumeric, hyphens, underscores only
_SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")

_BUILTIN_DIR = Path(__file__).parent.parent.parent / "fork_templates" / "agents"
_USER_DIR = Path.home() / ".pi" / "agent" / "fork-templates" / "agents"
_PROJECT_DIR_NAME = Path(".fork-templates") / "agents"  # relative to project root

_FRONTMATTER_RE = re.compile(
    r"^---\s*\n(.*?)\n---\s*\n?(.*)",
    re.DOTALL,
)


def _parse_frontmatter(content: str) -> tuple[dict[str, object], str]:
    """Split a .md file into frontmatter dict and body text.

    Falls back to manual YAML-like parsing if pyyaml is unavailable.
    """
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}, content

    raw_fm = match.group(1)
    body = match.group(2).strip()

    try:
        import yaml

        parsed = yaml.safe_load(raw_fm)
        if isinstance(parsed, dict):
            return parsed, body
        return {}, body
    except ImportError:
        return _manual_parse_frontmatter(raw_fm), body
    except Exception:
        return _manual_parse_frontmatter(raw_fm), body


def _manual_parse_frontmatter(raw: str) -> dict[str, object]:
    """Minimal YAML-like parser for frontmatter (fallback when pyyaml missing).

    Supports:
    - key: value (strings)
    - key: [a, b, c] (lists)
    - key: true/false (booleans)
    - key: 42 (integers)
    """
    result: dict[str, object] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        colon_idx = line.find(":")
        if colon_idx == -1:
            continue
        key = line[:colon_idx].strip()
        val_str = line[colon_idx + 1 :].strip()

        # List: [a, b, c]
        if val_str.startswith("[") and val_str.endswith("]"):
            inner = val_str[1:-1]
            if inner.strip():
                result[key] = [
                    item.strip().strip("\"'") for item in inner.split(",") if item.strip()
                ]
            else:
                result[key] = []
        # Boolean
        elif val_str.lower() == "true":
            result[key] = True
        elif val_str.lower() == "false":
            result[key] = False
        # Integer (including negative)
        elif val_str.lstrip("-").isdigit() and val_str.count("-") <= 1:
            result[key] = int(val_str)
        # Float (including negative)
        elif (
            val_str.replace(".", "", 1).lstrip("-").isdigit()
            and val_str.count("-") <= 1
            and val_str.count(".") <= 1
        ):
            result[key] = float(val_str)
        # Empty string
        elif val_str == '""' or val_str == "''":
            result[key] = ""
        # String
        else:
            result[key] = val_str
    return result


def _frontmatter_to_template(
    fm: dict[str, object],
    body: str,
    scope: TemplateScope,
    file_path: Path,
) -> AgentTemplate | None:
    """Convert parsed frontmatter + body into an AgentTemplate.

    Returns None if required fields are missing.
    """
    name = str(fm.get("name", ""))
    description = str(fm.get("description", ""))

    if not name or not description:
        return None

    return AgentTemplate(
        id=f"{scope.value.lower()}:{name}",
        name=name,
        description=description,
        scope=scope,
        model=str(fm.get("model", "")),
        system_prompt=body,
        tools=_ensure_tuple(fm.get("tools")),
        skills=_ensure_tuple(fm.get("skills")),
        output=str(fm.get("output", "")),
        default_reads=_ensure_tuple(fm.get("default_reads")),
        interactive=bool(fm.get("interactive", True)),
        max_depth=int(fm["max_depth"])
        if "max_depth" in fm and isinstance(fm["max_depth"], (int, str))
        else 1,
        file_path=str(file_path),
        team_id=str(fm.get("team_id")) if fm.get("team_id") else None,
    )


def _ensure_tuple(value: object) -> tuple[str, ...]:
    """Coerce a value to tuple[str, ...]."""
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value)
    return ()


class TemplateDirectory:
    """Filesystem-based discovery for agent template .md files.

    Mirrors pi-subagents' discoverAgents() — reads from 3 directories
    and merges results. Higher scopes (PROJECT) override lower ones (USER/BUILTIN)
    when templates share the same name.
    """

    def discover_all(
        self,
        project_dir: Path | None = None,
    ) -> list[AgentTemplate]:
        """Discover templates from all 3 scopes, merging by name.

        PROJECT overrides USER overrides BUILTIN for same-name templates.
        """
        templates: dict[str, AgentTemplate] = {}

        # Load in priority order: lowest first, highest last (overwrites)
        for scope, search_dir in self._scope_dirs(project_dir):
            if search_dir.is_dir():
                for template in self.load_from_dir(search_dir, scope):
                    templates[template.name] = template

        return list(templates.values())

    def load_from_dir(
        self,
        directory: Path,
        scope: TemplateScope,
    ) -> list[AgentTemplate]:
        """Parse all .md files in a directory as agent templates."""
        templates: list[AgentTemplate] = []
        if not directory.is_dir():
            return templates

        for md_file in sorted(directory.glob("*.md")):
            template = self._load_single(md_file, scope)
            if template is not None:
                templates.append(template)

        return templates

    def save_template(self, template: AgentTemplate, project_dir: Path | None = None) -> Path:
        """Write an AgentTemplate as a .md file to the correct scope directory.

        Returns the path to the written file.
        Raises ValueError if name contains path separators or invalid characters.
        Raises ValueError for BUILTIN scope.
        """
        if not _SAFE_NAME_RE.match(template.name):
            raise ValueError(
                f"Template name '{template.name}' contains invalid characters. "
                "Use only letters, digits, hyphens, and underscores."
            )
        if template.scope == TemplateScope.BUILTIN:
            raise ValueError("Cannot save to BUILTIN scope — builtin templates are read-only.")

        target_dir = self._scope_dir_for(template.scope, project_dir)
        target_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        target_path = target_dir / f"{template.name}.md"
        # Verify resolved path stays within target directory
        if not target_path.resolve().is_relative_to(target_dir.resolve()):
            raise ValueError(
                f"Resolved path escapes target directory for template '{template.name}'"
            )
        content = self._serialize_template(template)
        target_path.write_text(content, encoding="utf-8")
        return target_path

    def delete_template(
        self,
        name: str,
        scope: TemplateScope,
        project_dir: Path | None = None,
    ) -> bool:
        """Remove a .md file from the given scope directory.

        Returns True if the file was deleted, False if not found.
        Raises ValueError for BUILTIN scope or invalid names.
        """
        if not _SAFE_NAME_RE.match(name):
            raise ValueError(f"Template name '{name}' contains invalid characters.")
        if scope == TemplateScope.BUILTIN:
            raise ValueError("Cannot delete BUILTIN templates — they are read-only.")

        target_dir = self._scope_dir_for(scope, project_dir)
        target_path = target_dir / f"{name}.md"
        if not target_path.exists():
            return False
        # Verify resolved path stays within target directory
        if not target_path.resolve().is_relative_to(target_dir.resolve()):
            raise ValueError(f"Resolved path escapes target directory for template '{name}'")
        target_path.unlink()
        return True

    def _load_single(
        self,
        file_path: Path,
        scope: TemplateScope,
    ) -> AgentTemplate | None:
        """Load and parse a single .md template file."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except OSError:
            return None

        fm, body = _parse_frontmatter(content)
        return _frontmatter_to_template(fm, body, scope, file_path)

    @staticmethod
    def _serialize_template(template: AgentTemplate) -> str:
        """Serialize an AgentTemplate to .md file format with frontmatter."""
        fm_dict = template.to_frontmatter_dict()
        lines: list[str] = ["---"]
        for key, value in fm_dict.items():
            if isinstance(value, list):
                items = ", ".join(f'"{item}"' for item in value)
                lines.append(f"{key}: [{items}]")
            elif isinstance(value, bool):
                lines.append(f"{key}: {str(value).lower()}")
            elif isinstance(value, int):
                lines.append(f"{key}: {value}")
            else:
                lines.append(f"{key}: {value}")
        lines.append("---")
        lines.append("")
        if template.system_prompt:
            lines.append(template.system_prompt)
        return "\n".join(lines)

    def _scope_dirs(
        self,
        project_dir: Path | None,
    ) -> list[tuple[TemplateScope, Path]]:
        """Return (scope, directory) pairs for all 3 scopes."""
        result: list[tuple[TemplateScope, Path]] = [
            (TemplateScope.BUILTIN, _BUILTIN_DIR),
            (TemplateScope.USER, _USER_DIR),
        ]
        if project_dir is not None:
            result.append((TemplateScope.PROJECT, project_dir / _PROJECT_DIR_NAME))
        return result

    @staticmethod
    def _scope_dir_for(scope: TemplateScope, project_dir: Path | None = None) -> Path:
        """Return the filesystem directory for a given scope."""
        if scope == TemplateScope.BUILTIN:
            return _BUILTIN_DIR
        if scope == TemplateScope.USER:
            return _USER_DIR
        if scope == TemplateScope.PROJECT:
            if project_dir is None:
                raise ValueError("PROJECT scope requires project_dir parameter")
            return project_dir / _PROJECT_DIR_NAME
        raise ValueError(f"Unknown scope: {scope}")
