"""Application service for agent template management.

Operations:
- discover: scan filesystem for .md agent definitions, sync to DB
- save: create/update a template (filesystem + DB)
- list: query templates by scope/team/status
- show: get template details by name or ID
- delete: remove template from filesystem + DB
- toggle: enable/disable a template
"""

from __future__ import annotations

import uuid
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.entities.agent_template import (
        AgentTemplate,
        TeamDefinition,
    )
    from src.domain.ports.agent_template_repository import (
        AgentTemplateRepository,
        TeamRepository,
    )
    from src.infrastructure.agent_templates.template_directory import TemplateDirectory


class TemplateService:
    """Application service for template CRUD + discovery."""

    __slots__ = ("_repo", "_team_repo", "_dir")

    def __init__(
        self,
        template_repo: AgentTemplateRepository,
        team_repo: TeamRepository,
        template_dir: TemplateDirectory,
    ) -> None:
        self._repo = template_repo
        self._team_repo = team_repo
        self._dir = template_dir

    # --- Template operations ---

    def discover_templates(self, project_dir: str | None = None) -> list[AgentTemplate]:
        """Scan filesystem for .md agent definitions and sync to DB."""

        project = Path(project_dir) if project_dir else None
        templates = self._dir.discover_all(project)
        if not templates:
            return []

        # Batch check existing names — single query via list
        existing_by_name: dict[str, AgentTemplate] = {}
        for t in self._repo.list_active():
            existing_by_name[t.name] = t
        for scope in ("BUILTIN", "USER", "PROJECT"):
            for t in self._repo.list_by_scope(scope):
                existing_by_name[t.name] = t

        for t in templates:
            existing = existing_by_name.get(t.name)
            if existing is None or existing.file_path != t.file_path:
                self._repo.save(t)

        return templates

    def save_template(
        self,
        name: str,
        description: str,
        model: str = "",
        system_prompt: str = "",
        tools: list[str] | None = None,
        skills: list[str] | None = None,
        scope: str = "USER",
        output: str = "",
        default_reads: list[str] | None = None,
        interactive: bool = True,
        max_depth: int = 1,
        team_id: str | None = None,
    ) -> AgentTemplate:
        """Create or update a template."""
        from src.domain.entities.agent_template import AgentTemplate, TemplateScope

        scope_val = scope.upper()
        template_id = uuid.uuid4().hex
        existing = self._repo.get_by_name(name)
        if existing is not None and existing.scope.value.upper() == scope_val:
            template_id = existing.id
        # If scope changed, keep new UUID to avoid stale prefix

        # Validate team exists when team_id provided
        if team_id and self._team_repo.get_by_id(team_id) is None:
            team = self._team_repo.get_by_name(team_id)
            if team is None:
                raise ValueError(f"Team '{team_id}' not found")

        template = AgentTemplate(
            id=template_id,
            name=name,
            description=description,
            scope=TemplateScope(scope_val),
            model=model,
            system_prompt=system_prompt,
            tools=tuple(tools) if tools else (),
            skills=tuple(skills) if skills else (),
            output=output,
            default_reads=tuple(default_reads) if default_reads else (),
            interactive=interactive,
            max_depth=max_depth,
            team_id=team_id if team_id else None,
        )

        # Persist to both filesystem and DB
        path = self._dir.save_template(template)
        template = replace(template, file_path=str(path))
        self._repo.save(template)

        return template

    def get_template(self, name_or_id: str) -> AgentTemplate | None:
        """Get template by name or ID."""
        result = self._repo.get_by_name(name_or_id)
        if result is None:
            result = self._repo.get_by_id(name_or_id)
        return result

    def list_templates(
        self,
        scope: str | None = None,
        team_id: str | None = None,
        active_only: bool = True,
    ) -> list[AgentTemplate]:
        """List templates with optional filters."""
        if team_id:
            templates = self._repo.list_by_team(team_id)
        else:
            templates = self._repo.list_by_scope(scope) if scope else self._repo.list_active()

        if active_only:
            templates = [t for t in templates if t.is_active()]
        return templates

    def delete_template(self, name: str) -> bool:
        """Remove template from filesystem and DB."""
        template = self._repo.get_by_name(name)
        if template is None:
            return False

        # Delete from filesystem
        self._dir.delete_template(template.name, template.scope)
        # Delete from DB
        return self._repo.remove(template.id)

    def toggle_template(self, name: str) -> AgentTemplate | None:
        """Toggle template between ACTIVE and DISABLED using CAS guard."""
        from src.domain.entities.agent_template import TemplateStatus

        template = self._repo.get_by_name(name)
        if template is None:
            return None

        new_status = TemplateStatus.DISABLED if template.is_active() else TemplateStatus.ACTIVE

        success = self._repo.update_status(template.id, new_status.value)
        if not success:
            return None
        return self._repo.get_by_id(template.id)

    # --- Team operations ---

    def create_team(
        self,
        name: str,
        description: str = "",
        agent_names: list[str] | None = None,
    ) -> TeamDefinition:
        """Create a team definition."""
        from src.domain.entities.agent_template import TeamDefinition

        team_id = uuid.uuid4().hex
        team = TeamDefinition(
            id=team_id,
            name=name,
            description=description,
            agent_names=tuple(agent_names) if agent_names else (),
        )
        self._team_repo.save(team)
        return team

    def list_teams(self) -> list[TeamDefinition]:
        return self._team_repo.list_all()

    def get_team(self, name_or_id: str) -> TeamDefinition | None:
        result = self._team_repo.get_by_name(name_or_id)
        if result is None:
            result = self._team_repo.get_by_id(name_or_id)
        return result

    def delete_team(self, name: str) -> bool:
        """Delete a team and clear team_id from orphaned templates."""
        team = self._team_repo.get_by_name(name)
        if team is None:
            return False
        team_id = team.id
        result = self._team_repo.remove(team_id)
        # Clear team_id from templates that referenced this team
        if result:
            for t in self._repo.list_by_team(team_id):
                updated = replace(t, team_id=None)
                self._repo.save(updated)
        return result
