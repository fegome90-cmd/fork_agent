"""CLI commands for workspace management using Click.

This module provides CLI commands for managing git worktree-based workspaces.
"""

from __future__ import annotations

import sys

import click

from src.application.services.workspace.entities import LayoutType
from src.application.services.workspace.exceptions import (
    GitError,
    WorkspaceError,
    WorkspaceExistsError,
    WorkspaceNotCleanError,
    WorkspaceNotFoundError,
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
    # Only create HookRunner if hooks_dir is configured and run_hooks is True
    hook_runner: HookRunner | None = None
    if run_hooks and config.hooks_dir is not None:
        hook_runner = HookRunner(hooks_dir=config.hooks_dir)
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
    # Validate workspace name: reject slashes to stay consistent with remove
    if "/" in name:
        click.echo(f"Error: Invalid workspace name '{name}' (slashes are not allowed)", err=True)
        sys.exit(1)

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
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Skip confirmation prompt",
)
def remove(name: str, force: bool, yes: bool) -> None:
    """Remove a workspace.

    Removes the git worktree with the specified name.

    NAME is the name of the workspace to remove.

    Examples:
        fork workspace remove my-feature
        fork workspace remove my-feature --force
    """
    # Validate workspace name to prevent injection
    # Strip allowed separators and check minimum meaningful length
    stripped = name.replace("-", "").replace("_", "")
    if not name or not stripped.isalnum() or len(stripped) < 2:
        click.echo(f"Error: Invalid workspace name '{name}' (must contain at least 2 alphanumeric characters)", err=True)
        sys.exit(1)

    # Confirmation prompt unless --yes is passed
    if not yes:
        click.echo(f"This will remove workspace '{name}' and delete its branch.")
        if not click.confirm("Are you sure?"):
            click.echo("Aborted.")
            return

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
@click.argument("name")
@click.option(
    "--spawn-terminal",
    "-s",
    is_flag=True,
    default=False,
    help="Spawn a new terminal in the workspace directory",
)
def enter(name: str, spawn_terminal: bool) -> None:
    """Enter an existing workspace.

    Finds an existing workspace by name and either prints its path
    or spawns a terminal in it.

    NAME is the name of the workspace to enter.

    Examples:
        fork workspace enter my-feature              # Print path
        cd $(fork workspace enter my-feature)        # cd into it
        fork workspace enter my-feature --spawn      # Open terminal
    """
    try:
        manager = _create_workspace_manager()
        ws = manager.start_workspace(name)

        if spawn_terminal:
            import subprocess

            # Try to open a new terminal in the workspace
            terminal_cmd = None
            import shutil

            if shutil.which("tmux"):
                terminal_cmd = ["tmux", "new-session", "-c", str(ws.path)]
            elif shutil.which("open") and sys.platform == "darwin":
                # macOS - use osascript to reliably set working directory
                terminal_cmd = [
                    "osascript",
                    "-e",
                    f'tell application "Terminal" to do script "cd {ws.path} && exec $SHELL"',
                ]
            elif shutil.which("gnome-terminal"):
                terminal_cmd = ["gnome-terminal", "--working-directory", str(ws.path)]

            if terminal_cmd:
                subprocess.Popen(terminal_cmd)
                click.echo(f"Opened terminal in workspace '{name}' at {ws.path}")
            else:
                click.echo(f"Workspace '{name}' is at: {ws.path}")
                click.echo("(No terminal emulator found)")
        else:
            # Just print the path (useful for cd $(fork workspace enter name))
            click.echo(str(ws.path))

    except WorkspaceNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
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
@click.argument("name")
@click.option(
    "--target",
    "-t",
    "target_branch",
    default="main",
    help="Target branch to merge into (default: main)",
)
@click.option(
    "--no-delete",
    is_flag=True,
    default=False,
    help="Keep the branch after merging",
)
def merge(name: str, target_branch: str, no_delete: bool) -> None:
    """Merge a workspace branch into target.

    Merges the specified workspace branch into the target branch (default: main)
    and optionally deletes the workspace branch.

    NAME is the workspace/branch name to merge.

    Examples:
        fork workspace merge my-feature
        fork workspace merge my-feature --target develop --no-delete
    """
    try:
        manager = _create_workspace_manager(run_hooks=False)
        manager.merge_workspace(
            name=name,
            target_branch=target_branch,
            delete_branch=not no_delete,
        )

        action = "merged and branch deleted"
        if no_delete:
            action = "merged (branch kept)"
        click.echo(f"Workspace '{name}' {action} into '{target_branch}'.")

    except WorkspaceNotFoundError as e:
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
        from src.infrastructure.config.workspace_config import ForkAgentConfig

        config_path = ForkAgentConfig._find_config_file()

        if config_path is None or not config_path.exists():
            click.echo(
                "No configuration file found. Create .fork_agent.yaml in repo root "
                "or ~/.config/fork_agent.yaml.",
                err=True,
            )
            sys.exit(1)

        editor = click.edit(filename=str(config_path))
        if editor is not None:
            click.echo(f"Configuration updated ({config_path}).")
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
    workspace()
    return 0


if __name__ == "__main__":
    sys.exit(run_workspace_cli())
