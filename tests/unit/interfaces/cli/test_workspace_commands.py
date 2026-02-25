"""Tests for CLI workspace commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import click
from click.testing import CliRunner

from src.interfaces.cli import workspace_commands

runner = CliRunner()


class TestWorkspaceGroup:
    def test_workspace_group_exists(self) -> None:
        assert workspace_commands.workspace is not None

    def test_workspace_is_click_group(self) -> None:
        assert isinstance(workspace_commands.workspace, click.Group)


class TestCreateWorkspace:
    def test_create_workspace_command_exists(self) -> None:
        assert workspace_commands.create is not None

    def test_create_workspace_with_name(self) -> None:
        with patch.object(workspace_commands, "_create_workspace_manager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_ws = MagicMock()
            mock_ws.name = "test-workspace"
            mock_ws.path = "/path/to/test-workspace"
            mock_ws.layout.value = "NESTED"
            mock_manager.create_workspace.return_value = mock_ws
            mock_manager_class.return_value = mock_manager

            result = runner.invoke(workspace_commands.workspace, ["create", "test-workspace"])

            assert result.exit_code == 0
            assert "test-workspace" in result.output

    def test_create_workspace_with_layout(self) -> None:
        with patch.object(workspace_commands, "_create_workspace_manager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_ws = MagicMock()
            mock_ws.name = "test-workspace"
            mock_ws.path = "/path/to/test-workspace"
            mock_ws.layout.value = "SIBLING"
            mock_manager.create_workspace.return_value = mock_ws
            mock_manager_class.return_value = mock_manager

            result = runner.invoke(
                workspace_commands.workspace, ["create", "test-workspace", "--layout", "SIBLING"]
            )

            assert result.exit_code == 0

    def test_create_workspace_with_no_hooks(self) -> None:
        with patch.object(workspace_commands, "_create_workspace_manager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_ws = MagicMock()
            mock_ws.name = "test-workspace"
            mock_ws.path = "/path/to/test-workspace"
            mock_ws.layout.value = "NESTED"
            mock_manager.create_workspace.return_value = mock_ws
            mock_manager_class.return_value = mock_manager

            result = runner.invoke(
                workspace_commands.workspace, ["create", "test-workspace", "--no-hooks"]
            )

            assert result.exit_code == 0

    def test_create_workspace_error_exists(self) -> None:
        from src.application.services.workspace.exceptions import WorkspaceExistsError

        with patch.object(workspace_commands, "_create_workspace_manager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.create_workspace.side_effect = WorkspaceExistsError("exists")
            mock_manager_class.return_value = mock_manager

            result = runner.invoke(workspace_commands.workspace, ["create", "existing-workspace"])

            assert result.exit_code == 1

    def test_create_workspace_error_git(self) -> None:
        from src.application.services.workspace.exceptions import GitError

        with patch.object(workspace_commands, "_create_workspace_manager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.create_workspace.side_effect = GitError("git failed")
            mock_manager_class.return_value = mock_manager

            result = runner.invoke(workspace_commands.workspace, ["create", "test-workspace"])

            assert result.exit_code == 1
            assert "Git error" in result.output


class TestListWorkspaceErrorHandling:
    def test_list_workspace_git_error(self) -> None:
        from src.application.services.workspace.exceptions import GitError

        with patch.object(workspace_commands, "_create_workspace_manager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.list_workspaces.side_effect = GitError("git failed")
            mock_manager_class.return_value = mock_manager

            result = runner.invoke(workspace_commands.workspace, ["list"])

            assert result.exit_code == 1


class TestListWorkspace:
    def test_list_workspace_command_exists(self) -> None:
        assert workspace_commands.list is not None

    def test_list_workspaces_empty(self) -> None:
        with patch.object(workspace_commands, "_create_workspace_manager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.list_workspaces.return_value = []
            mock_manager_class.return_value = mock_manager

            result = runner.invoke(workspace_commands.workspace, ["list"])

            assert result.exit_code == 0
            assert "No workspaces found" in result.output

    def test_list_workspaces_with_content(self) -> None:
        with patch.object(workspace_commands, "_create_workspace_manager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_ws = MagicMock()
            mock_ws.name = "workspace-1"
            mock_manager.list_workspaces.return_value = [mock_ws]
            mock_manager_class.return_value = mock_manager

            result = runner.invoke(workspace_commands.workspace, ["list"])

            assert result.exit_code == 0
            assert "workspace-1" in result.output

    def test_list_workspaces_verbose(self) -> None:
        with patch.object(workspace_commands, "_create_workspace_manager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_ws = MagicMock()
            mock_ws.name = "workspace-1"
            mock_ws.path = "/path/to/workspace-1"
            mock_ws.layout.value = "NESTED"
            mock_ws.state.value = "READY"
            mock_manager.list_workspaces.return_value = [mock_ws]
            mock_manager_class.return_value = mock_manager

            result = runner.invoke(workspace_commands.workspace, ["list", "--verbose"])

            assert result.exit_code == 0
            assert "workspace-1" in result.output


class TestRemoveWorkspace:
    def test_remove_workspace_command_exists(self) -> None:
        assert workspace_commands.remove is not None

    def test_remove_workspace_success(self) -> None:
        with patch.object(workspace_commands, "_create_workspace_manager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager

            result = runner.invoke(
                workspace_commands.workspace, ["remove", "test-workspace", "--yes"]
            )

            assert result.exit_code == 0
            assert "removed successfully" in result.output

    def test_remove_workspace_not_found(self) -> None:
        from src.application.services.workspace.exceptions import WorkspaceNotFoundError

        with patch.object(workspace_commands, "_create_workspace_manager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.remove_workspace.side_effect = WorkspaceNotFoundError("Not found")
            mock_manager_class.return_value = mock_manager

            result = runner.invoke(workspace_commands.workspace, ["remove", "nonexistent", "--yes"])

            assert result.exit_code == 1

    def test_remove_workspace_not_clean(self) -> None:
        from src.application.services.workspace.exceptions import WorkspaceNotCleanError

        with patch.object(workspace_commands, "_create_workspace_manager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.remove_workspace.side_effect = WorkspaceNotCleanError("not clean")
            mock_manager_class.return_value = mock_manager

            result = runner.invoke(
                workspace_commands.workspace, ["remove", "test-workspace", "--yes"]
            )

            assert result.exit_code == 1
            assert "--force" in result.output

    def test_remove_workspace_git_error(self) -> None:
        from src.application.services.workspace.exceptions import GitError

        with patch.object(workspace_commands, "_create_workspace_manager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.remove_workspace.side_effect = GitError("git failed")
            mock_manager_class.return_value = mock_manager

            result = runner.invoke(
                workspace_commands.workspace, ["remove", "test-workspace", "--yes"]
            )

            assert result.exit_code == 1

    def test_remove_workspace_with_force(self) -> None:
        with patch.object(workspace_commands, "_create_workspace_manager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager

            result = runner.invoke(
                workspace_commands.workspace, ["remove", "test-workspace", "--force", "--yes"]
            )

            assert result.exit_code == 0


class TestEnterWorkspace:
    def test_enter_workspace_command_exists(self) -> None:
        assert workspace_commands.enter is not None

    def test_enter_workspace_success(self) -> None:
        with patch.object(workspace_commands, "_create_workspace_manager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_ws = MagicMock()
            mock_ws.path = "/path/to/workspace"
            mock_manager.start_workspace.return_value = mock_ws
            mock_manager_class.return_value = mock_manager

            result = runner.invoke(workspace_commands.workspace, ["enter", "test-workspace"])

            assert result.exit_code == 0
            assert "/path/to/workspace" in result.output

    def test_enter_workspace_with_spawn_tmux(self) -> None:
        with (
            patch.object(workspace_commands, "_create_workspace_manager") as mock_manager_class,
            patch("shutil.which") as mock_which,
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_manager = MagicMock()
            mock_ws = MagicMock()
            mock_ws.path = "/path/to/workspace"
            mock_manager.start_workspace.return_value = mock_ws
            mock_manager_class.return_value = mock_manager
            mock_which.return_value = "/usr/bin/tmux"

            result = runner.invoke(
                workspace_commands.workspace,
                ["enter", "test-workspace", "--spawn-terminal"],
            )

            assert result.exit_code == 0
            mock_popen.assert_called_once()

    def test_enter_workspace_spawn_no_terminal(self) -> None:
        with (
            patch.object(workspace_commands, "_create_workspace_manager") as mock_manager_class,
            patch("shutil.which") as mock_which,
        ):
            mock_manager = MagicMock()
            mock_ws = MagicMock()
            mock_ws.path = "/path/to/workspace"
            mock_manager.start_workspace.return_value = mock_ws
            mock_manager_class.return_value = mock_manager
            mock_which.return_value = None

            result = runner.invoke(
                workspace_commands.workspace, ["enter", "test-workspace", "--spawn-terminal"]
            )

            assert result.exit_code == 0
            assert "No terminal emulator found" in result.output

    def test_enter_workspace_spawn_darwin_open(self) -> None:
        with (
            patch.object(workspace_commands, "_create_workspace_manager") as mock_manager_class,
            patch("shutil.which") as mock_which,
            patch("subprocess.Popen") as mock_popen,
            patch("sys.platform", "darwin"),
        ):
            mock_manager = MagicMock()
            mock_ws = MagicMock()
            mock_ws.path = "/path/to/workspace"
            mock_manager.start_workspace.return_value = mock_ws
            mock_manager_class.return_value = mock_manager

            def which_side_effect(cmd):
                if cmd == "tmux":
                    return None
                if cmd == "open":
                    return "/usr/bin/open"
                return None

            mock_which.side_effect = which_side_effect

            result = runner.invoke(
                workspace_commands.workspace,
                ["enter", "test-workspace", "--spawn-terminal"],
            )

            assert result.exit_code == 0
            mock_popen.assert_called_once()

    def test_enter_workspace_spawn_gnome(self) -> None:
        with (
            patch.object(workspace_commands, "_create_workspace_manager") as mock_manager_class,
            patch("shutil.which") as mock_which,
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_manager = MagicMock()
            mock_ws = MagicMock()
            mock_ws.path = "/path/to/workspace"
            mock_manager.start_workspace.return_value = mock_ws
            mock_manager_class.return_value = mock_manager

            def which_side_effect(cmd):
                if cmd == "tmux":
                    return None
                if cmd == "open":
                    return None
                if cmd == "gnome-terminal":
                    return "/usr/bin/gnome-terminal"
                return None

            mock_which.side_effect = which_side_effect

            result = runner.invoke(
                workspace_commands.workspace,
                ["enter", "test-workspace", "--spawn-terminal"],
            )

            assert result.exit_code == 0
            mock_popen.assert_called_once()


class TestEnterWorkspaceErrorHandling:
    def test_enter_workspace_not_found(self) -> None:
        from src.application.services.workspace.exceptions import WorkspaceNotFoundError

        with patch.object(workspace_commands, "_create_workspace_manager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.start_workspace.side_effect = WorkspaceNotFoundError("not found")
            mock_manager_class.return_value = mock_manager

            result = runner.invoke(workspace_commands.workspace, ["enter", "nonexistent"])

            assert result.exit_code == 1

    def test_enter_workspace_git_error(self) -> None:
        from src.application.services.workspace.exceptions import GitError

        with patch.object(workspace_commands, "_create_workspace_manager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.start_workspace.side_effect = GitError("git failed")
            mock_manager_class.return_value = mock_manager

            result = runner.invoke(workspace_commands.workspace, ["enter", "test-workspace"])

            assert result.exit_code == 1

    def test_enter_workspace_error_workspace(self) -> None:
        from src.application.services.workspace.exceptions import WorkspaceError

        with patch.object(workspace_commands, "_create_workspace_manager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.start_workspace.side_effect = WorkspaceError("error")
            mock_manager_class.return_value = mock_manager

            result = runner.invoke(workspace_commands.workspace, ["enter", "test-workspace"])

            assert result.exit_code == 1


class TestDetectWorkspace:
    def test_detect_workspace_command_exists(self) -> None:
        assert workspace_commands.detect is not None

    def test_detect_workspace_found(self) -> None:
        with patch.object(workspace_commands, "_create_workspace_manager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_ws = MagicMock()
            mock_ws.name = "current-workspace"
            mock_ws.path = "/path/to/workspace"
            mock_ws.layout.value = "NESTED"
            mock_ws.state.value = "READY"
            mock_manager.detect_workspace.return_value = mock_ws
            mock_manager_class.return_value = mock_manager

            result = runner.invoke(workspace_commands.workspace, ["detect"])

            assert result.exit_code == 0
            assert "current-workspace" in result.output

    def test_detect_workspace_not_in_workspace(self) -> None:
        with patch.object(workspace_commands, "_create_workspace_manager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.detect_workspace.return_value = None
            mock_manager_class.return_value = mock_manager

            result = runner.invoke(workspace_commands.workspace, ["detect"])

            assert result.exit_code == 0
            assert "Not inside a workspace" in result.output


class TestDetectWorkspaceErrorHandling:
    def test_detect_workspace_git_error(self) -> None:
        from src.application.services.workspace.exceptions import GitError

        with patch.object(workspace_commands, "_create_workspace_manager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.detect_workspace.side_effect = GitError("git failed")
            mock_manager_class.return_value = mock_manager

            result = runner.invoke(workspace_commands.workspace, ["detect"])

            assert result.exit_code == 1

    def test_detect_workspace_error_workspace(self) -> None:
        from src.application.services.workspace.exceptions import WorkspaceError

        with patch.object(workspace_commands, "_create_workspace_manager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.detect_workspace.side_effect = WorkspaceError("error")
            mock_manager_class.return_value = mock_manager

            result = runner.invoke(workspace_commands.workspace, ["detect"])

            assert result.exit_code == 1


class TestConfigWorkspace:
    def test_config_command_exists(self) -> None:
        assert workspace_commands.config is not None

    def test_config_shows_defaults(self) -> None:
        result = runner.invoke(workspace_commands.workspace, ["config"])

        assert result.exit_code == 0
        assert "Workspace Configuration" in result.output

    def test_config_edit_no_file(self) -> None:
        with patch("pathlib.Path.exists", return_value=False):
            result = runner.invoke(workspace_commands.workspace, ["config", "--edit"])
            assert result.exit_code == 1
            assert "No configuration file found" in result.output

    def test_config_edit_with_file(self) -> None:
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("click.edit") as mock_edit,
        ):
            mock_edit.return_value = None
            result = runner.invoke(workspace_commands.workspace, ["config", "--edit"])
            assert result.exit_code == 0


class TestGetDefaultConfig:
    def test_get_default_config_returns_dict(self) -> None:
        config = workspace_commands._get_default_config()
        assert isinstance(config, dict)

    def test_get_default_config_has_expected_keys(self) -> None:
        config = workspace_commands._get_default_config()
        assert "default_layout" in config
        assert "auto_cleanup" in config
        assert "hooks_dir" in config


class TestRunWorkspaceCli:
    def test_run_workspace_cli_returns_zero(self) -> None:
        with patch.object(workspace_commands.workspace, "main", return_value=None):
            result = workspace_commands.run_workspace_cli()
            assert result == 0


class TestCreateWorkspaceErrorHandling:
    def test_create_workspace_error_workspace(self) -> None:
        from src.application.services.workspace.exceptions import WorkspaceError

        with patch.object(workspace_commands, "_create_workspace_manager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.create_workspace.side_effect = WorkspaceError("workspace error")
            mock_manager_class.return_value = mock_manager

            result = runner.invoke(workspace_commands.workspace, ["create", "test-workspace"])

            assert result.exit_code == 1
            assert "workspace error" in result.output.lower()


class TestListWorkspaceErrorWorkspaceError:
    def test_list_workspace_workspace_error(self) -> None:
        from src.application.services.workspace.exceptions import WorkspaceError

        with patch.object(workspace_commands, "_create_workspace_manager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.list_workspaces.side_effect = WorkspaceError("list error")
            mock_manager_class.return_value = mock_manager

            result = runner.invoke(workspace_commands.workspace, ["list"])

            assert result.exit_code == 1


class TestRemoveWorkspaceErrorHandling:
    def test_remove_workspace_workspace_error(self) -> None:
        from src.application.services.workspace.exceptions import WorkspaceError

        with patch.object(workspace_commands, "_create_workspace_manager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.remove_workspace.side_effect = WorkspaceError("remove error")
            mock_manager_class.return_value = mock_manager

            result = runner.invoke(
                workspace_commands.workspace, ["remove", "test-workspace", "--yes"]
            )

            assert result.exit_code == 1

    def test_remove_workspace_invalid_name(self) -> None:
        result = runner.invoke(workspace_commands.workspace, ["remove", "invalid name!", "--yes"])

        assert result.exit_code == 1
        assert "Invalid workspace name" in result.output

    def test_remove_workspace_confirmation_abort(self) -> None:
        result = runner.invoke(
            workspace_commands.workspace, ["remove", "test-workspace"], input="n\n"
        )

        assert result.exit_code == 0
        assert "Aborted" in result.output


class TestConfigEditWithContent:
    def test_config_edit_with_content_returned(self) -> None:
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("click.edit") as mock_edit,
        ):
            mock_edit.return_value = "new content"
            result = runner.invoke(workspace_commands.workspace, ["config", "--edit"])
            assert result.exit_code == 0
            assert "Configuration updated" in result.output
