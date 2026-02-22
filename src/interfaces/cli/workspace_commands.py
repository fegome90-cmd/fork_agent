"""CLI commands for workspace management using Click.

This module provides CLI commands for managing git worktree-based workspaces.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from src.application.services.workspace.entities import LayoutType
from src.application.services.workspace.exceptions import (
    GitError,
    WorkspaceExistsError,
    WorkspaceNotCleanError,
    WorkspaceNotFoundError,
    WorkspaceError,
)
from src.application.services.workspace.workspace_manager import WorkspaceManager


# Default configuration factory
def _get_default_config() -> dict:
    """Get default workspace configuration."""
    return {
        "default_layout": LayoutType.NESTED,
        "auto_cleanup": False,
        "hooks_dir": None,
    }


def _create_workspace_manager(run_hooks: bool = True) -> WorkspaceManager:
    """Create a WorkspaceManager instance with default configuration.
    
    Args:
        run_hooks: Whether to run setup/teardown hooks.
    
    Returns:
        Configured WorkspaceManager instance.
    """
    from src.application.services.workspace.entities import WorkspaceConfig
    from src.application.services.workspace.hook_runner import HookRunner
    from src.infrastructure.platform.git.git_command_executor import GitCommandExecutor
    
    config = WorkspaceConfig(
        default_layout=LayoutType.NESTED,
        auto_cleanup=False,
        hooks_dir=None,
    )
    
    git_executor = GitCommandExecutor()
    hook_runner: HookRunner | None = HookRunner(config) if run_hooks else None
    return WorkspaceManager(git_executor=git_executor, config=config, hook_runner=hook_runner)


@click.group()
def workspace() -> None:
    """Workspace management commands.
    
    Manage git worktree-based workspaces for isolated development environments.
    """
    pass


@workspace.command()
@click.argument("name")
@click.option(
    "--layout",
    type=click.Choice(["NESTED", "OUTER_NESTED", "SIBLING"]),
    default=None,
    help="Layout type for the workspace",
)
@click.option(
    "--no-hooks",
    is_flag=True,
    default=False,
    help="Skip running setup hooks",
)
def create(name: str, layout: str | None, no_hooks: bool) -> None:
    """Create a new workspace.
    
    Creates a new git worktree with the specified name.
    
    NAME is the name of the workspace (and branch) to create.
    
    Examples:
        fork workspace create my-feature
        fork workspace create my-feature --layout SIBLING
    """
    try:
        layout_type = LayoutType[layout] if layout else None
        
        manager = _create_workspace_manager(run_hooks=not no_hooks)
        ws = manager.create_workspace(name=name, layout=layout_type)
        
        click.echo(f"Workspace '{ws.name}' created successfully at {ws.path}")
        click.echo(f"Layout: {ws.layout.value}")
        
    except WorkspaceExistsError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except GitError as e:
        click.echo(f"Git error: {e}", err=True)
        sys.exit(1)
    except WorkspaceError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@workspace.command()
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Show detailed information about each workspace",
)
def list(verbose: bool) -> None:
    """List all workspaces.
    
    Shows all git worktrees in the current repository.
    
    Examples:
        fork workspace list
        fork workspace list --verbose
    """
    try:
        manager = _create_workspace_manager()
        workspaces = manager.list_workspaces()
        
        if not workspaces:
            click.echo("No workspaces found.")
            return
        
        if verbose:
            click.echo(f"Found {len(workspaces)} workspace(s):\n")
            for ws in workspaces:
                click.echo(f"  Name: {ws.name}")
                click.echo(f"  Path: {ws.path}")
                click.echo(f"  Layout: {ws.layout.value}")
                click.echo(f"  State: {ws.state.value}")
                click.echo()
        else:
            for ws in workspaces:
                click.echo(ws.name)
                
    except GitError as e:
        click.echo(f"Git error: {e}", err=True)
        sys.exit(1)
    except WorkspaceError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@workspace.command()
@click.argument("name")
@click.option(
    "--force",
    "-f",
    is_flag=True,
    default=False,
    help="Force removal even with uncommitted changes",
)
def remove(name: str, force: bool) -> None:
    """Remove a workspace.
    
    Removes the git worktree with the specified name.
    
    NAME is the name of the workspace to remove.
    
    Examples:
        fork workspace remove my-feature
        fork workspace remove my-feature --force
    """
    try:
        manager = _create_workspace_manager()
        manager.remove_workspace(name=name, force=force)
        
        click.echo(f"Workspace '{name}' removed successfully.")
        
    except WorkspaceNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except WorkspaceNotCleanError as e:
        click.echo(f"Error: {e}", err=True)
        click.echo("Use --force to remove anyway.", err=True)
        sys.exit(1)
    except GitError as e:
        click.echo(f"Git error: {e}", err=True)
        sys.exit(1)
    except WorkspaceError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@workspace.command()
def detect() -> None:
    """Detect workspace from current directory.
    
    Detects if the current directory is inside a workspace and shows
    information about it.
    
    Examples:
        fork workspace detect
    """
    try:
        manager = _create_workspace_manager()
        ws = manager.detect_workspace()
        
        if ws is None:
            click.echo("Not inside a workspace.")
            return
        
        click.echo(f"Workspace: {ws.name}")
        click.echo(f"Path: {ws.path}")
        click.echo(f"Layout: {ws.layout.value}")
        click.echo(f"State: {ws.state.value}")
        
    except GitError as e:
        click.echo(f"Git error: {e}", err=True)
        sys.exit(1)
    except WorkspaceError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@workspace.command()
@click.option(
    "--edit",
    is_flag=True,
    default=False,
    help="Open configuration file in editor",
)
def config(edit: bool) -> None:
    """Show or edit configuration.
    
    Displays the current workspace configuration. Use --edit to modify.
    
    Examples:
        fork workspace config
        fork workspace config --edit
    """
    if edit:
        # Try to open the config file in editor
        config_path = Path(__file__).parent.parent.parent / ".env"
        
        if not config_path.exists():
            click.echo("No configuration file found.", err=True)
            sys.exit(1)
        
        # Use the default editor
        editor = click.edit(filename=str(config_path))
        if editor is not None:
            click.echo("Configuration updated.")
        return
    
    # Show current configuration
    default_config = _get_default_config()
    
    click.echo("Workspace Configuration:")
    click.echo(f"  Default Layout: {default_config['default_layout'].value}")
    click.echo(f"  Auto Cleanup: {default_config['auto_cleanup']}")
    click.echo(f"  Hooks Dir: {default_config['hooks_dir']}")


# Entry point for direct execution
def run_workspace_cli() -> int:
    """Run the workspace CLI.
    
    Returns:
        Exit code.
    """
    return workspace()


if __name__ == "__main__":
    sys.exit(run_workspace_cli())
