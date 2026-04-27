"""CLI commands for agent template management.

Commands:
  fork template list              -- list all templates
  fork template show <name>       -- show template details
  fork template save <name>       -- create/update template
  fork template delete <name>     -- remove template
  fork template toggle <name>     -- enable/disable
  fork template discover          -- scan filesystem + sync
  fork template team-create       -- create a team
  fork template team-list         -- list teams
  fork template team-delete       -- delete a team
"""

from __future__ import annotations

from typing import Annotated

import typer

app = typer.Typer(name="template", help="Agent template management")
team_app = typer.Typer(name="team", help="Team definition management")
app.add_typer(team_app, name="team")


def _get_service():
    from src.infrastructure.persistence.container import get_template_service

    return get_template_service()


@app.command("list")
def template_list(
    scope: Annotated[
        str | None,
        typer.Option("--scope", "-s", help="Filter by scope (BUILTIN/USER/PROJECT)"),
    ] = None,
    team: Annotated[
        str | None,
        typer.Option("--team", "-t", help="Filter by team ID"),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
) -> None:
    """List agent templates."""
    svc = _get_service()
    templates = svc.list_templates(scope=scope, team_id=team)

    if json_output:
        import json

        print(
            json.dumps(
                [
                    {
                        "name": t.name,
                        "scope": t.scope.value,
                        "model": t.model,
                        "status": t.status.value,
                    }
                    for t in templates
                ],
                indent=2,
            )
        )
        return

    if not templates:
        print("No templates found. Run 'fork template discover' to scan filesystem.")
        return

    print(f"{'NAME':<20} {'SCOPE':<10} {'MODEL':<20} {'STATUS':<10}")
    print("-" * 60)
    for t in templates:
        print(f"{t.name:<20} {t.scope.value:<10} {t.model or 'default':<20} {t.status.value:<10}")


@app.command("show")
def template_show(
    name: Annotated[str, typer.Argument(help="Template name or ID")],
) -> None:
    """Show template details."""
    svc = _get_service()
    template = svc.get_template(name)

    if template is None:
        print(f"Template '{name}' not found.")
        raise typer.Exit(code=1)

    print(f"Name:        {template.name}")
    print(f"ID:          {template.id}")
    print(f"Scope:       {template.scope.value}")
    print(f"Status:      {template.status.value}")
    print(f"Model:       {template.model or '(default)'}")
    print(f"Tools:       {', '.join(template.tools) or '(none)'}")
    print(f"Skills:      {', '.join(template.skills) or '(none)'}")
    print(f"Output:      {template.output or '(none)'}")
    print(f"Interactive: {template.interactive}")
    print(f"Max Depth:   {template.max_depth}")
    print(f"Default Reads: {', '.join(template.default_reads) or '(none)'}")
    print(f"Team:        {template.team_id or '(none)'}")
    print(f"File:        {template.file_path or '(none)'}")
    if template.system_prompt:
        preview = template.system_prompt[:200]
        ellipsis = "..." if len(template.system_prompt) > 200 else ""
        print(f"\nSystem Prompt:\n  {preview}{ellipsis}")


@app.command("save")
def template_save(
    name: Annotated[str, typer.Argument(help="Template name")],
    description: Annotated[str, typer.Option("--desc", "-d", help="Description")] = "",
    model: Annotated[str, typer.Option("--model", "-m", help="Provider/model")] = "",
    prompt: Annotated[str, typer.Option("--prompt", "-p", help="System prompt")] = "",
    tools: Annotated[str, typer.Option("--tools", "-t", help="Comma-separated tools")] = "",
    skills: Annotated[str, typer.Option("--skills", "-k", help="Comma-separated skills")] = "",
    scope: Annotated[str, typer.Option("--scope", help="Scope (USER/PROJECT)")] = "USER",
    output: Annotated[str, typer.Option("--output", "-o", help="Output filename pattern")] = "",
    team: Annotated[str, typer.Option("--team", help="Team ID")] = "",
) -> None:
    """Create or update an agent template."""
    if not description and not prompt:
        print("Provide at least --desc or --prompt.")
        raise typer.Exit(code=1)

    svc = _get_service()
    template = svc.save_template(
        name=name,
        description=description,
        model=model,
        system_prompt=prompt,
        tools=tuple(t.strip() for t in tools.split(",")) if tools else (),
        skills=tuple(s.strip() for s in skills.split(",")) if skills else (),
        scope=scope,
        output=output,
        team_id=team,
    )
    print(f"Template '{template.name}' saved ({template.id[:8]}).")


@app.command("delete")
def template_delete(
    name: Annotated[str, typer.Argument(help="Template name")],
) -> None:
    """Delete an agent template."""
    svc = _get_service()
    if svc.delete_template(name):
        print(f"Template '{name}' deleted.")
    else:
        print(f"Template '{name}' not found.")
        raise typer.Exit(code=1)


@app.command("toggle")
def template_toggle(
    name: Annotated[str, typer.Argument(help="Template name")],
) -> None:
    """Toggle template between ACTIVE and DISABLED."""
    svc = _get_service()
    template = svc.toggle_template(name)
    if template is None:
        print(f"Template '{name}' not found.")
        raise typer.Exit(code=1)
    print(f"Template '{template.name}' is now {template.status.value}.")


@app.command("discover")
def template_discover(
    project_dir: Annotated[str | None, typer.Option("--project", help="Project directory")] = None,
) -> None:
    """Scan filesystem for .md agent definitions and sync to DB."""
    svc = _get_service()
    templates = svc.discover_templates(project_dir)
    print(f"Discovered {len(templates)} templates:")
    for t in templates:
        print(f"  {t.name} ({t.scope.value})")


@app.command("resolve-role")
def template_resolve_role(
    role: Annotated[str, typer.Argument(help="Role name to resolve (e.g. explorer, implementer)")],
) -> None:
    """Resolve agent configuration for a role from templates.

    Outputs JSON with model, tools, skills, and prompt if a matching
    template is found. Returns exit code 1 if no template matches.
    Used by tmux-live to bridge template system -> protocol spawning.
    """
    import json as json_mod

    svc = _get_service()
    templates = svc.list_templates(active_only=True)

    # Find by exact name match or by role in description
    match = None
    for t in templates:
        if t.name.lower() == role.lower():
            match = t
            break
    if match is None:
        for t in templates:
            if role.lower() in t.description.lower():
                match = t
                break

    if match is None:
        print(json_mod.dumps({"found": False}))
        raise typer.Exit(code=1)

    print(
        json_mod.dumps(
            {
                "found": True,
                "name": match.name,
                "model": match.model,
                "tools": list(match.tools),
                "skills": list(match.skills),
                "system_prompt": match.system_prompt[:200] if match.system_prompt else "",
                "interactive": match.interactive,
            }
        )
    )


@team_app.command("create")
def team_create(
    name: Annotated[str, typer.Argument(help="Team name")],
    description: Annotated[str, typer.Option("--desc", "-d", help="Description")] = "",
    agents: Annotated[str, typer.Option("--agents", "-a", help="Comma-separated agent names")] = "",
) -> None:
    """Create a team of agent templates."""
    svc = _get_service()
    team = svc.create_team(
        name=name,
        description=description,
        agent_names=tuple(a.strip() for a in agents.split(",")) if agents else (),
    )
    print(f"Team '{team.name}' created ({team.id[:8]}) with {len(team.agent_names)} agents.")


@team_app.command("list")
def team_list() -> None:
    """List all teams."""
    svc = _get_service()
    teams = svc.list_teams()
    if not teams:
        print("No teams found.")
        return
    for t in teams:
        agent_count = len(t.agent_names)
        agent_names = ", ".join(t.agent_names) or "(none)"
        print(f"  {t.name} ({t.id[:8]}) -- {agent_count} agents: {agent_names}")


@team_app.command("delete")
def team_delete(
    name: Annotated[str, typer.Argument(help="Team name")],
) -> None:
    """Delete a team."""
    svc = _get_service()
    if svc.delete_team(name):
        print(f"Team '{name}' deleted.")
    else:
        print(f"Team '{name}' not found.")
        raise typer.Exit(code=1)
