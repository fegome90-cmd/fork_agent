"""End-to-end tests for workspace config command.

Tests:
- Config shows workspace configuration
- Config command exits cleanly
- Config edit with existing file
- Config edit without existing file returns error
"""

from __future__ import annotations

from click.testing import CliRunner

from src.interfaces.cli import workspace_commands

runner = CliRunner()


class TestConfigWorkspaceE2E:
    """E2E tests for workspace config command."""

    def test_config_shows_workspace_configuration(self) -> None:
        """Test that config command shows configuration output."""
        result = runner.invoke(workspace_commands.workspace, ["config"])

        assert result.exit_code == 0
        assert "Workspace Configuration" in result.output
        assert "Default Layout" in result.output
        assert "Auto Cleanup" in result.output
        assert "Hooks Dir" in result.output

    def test_config_shows_nested_as_default_layout(self) -> None:
        """Test that config shows nested layout pattern as default."""
        result = runner.invoke(workspace_commands.workspace, ["config"])

        assert result.exit_code == 0
        assert ".worktrees" in result.output

    def test_config_edit_with_nonexistent_file(self) -> None:
        """Test that config --edit returns error when no config file exists."""
        with runner.isolated_filesystem():
            result = runner.invoke(workspace_commands.workspace, ["config", "--edit"])

            assert result.exit_code == 1
            assert "No configuration file found" in result.output

    def test_config_edit_with_existing_file(self) -> None:
        """Test that config --edit opens editor when config file exists."""
        from unittest.mock import patch

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("click.edit") as mock_edit,
        ):
            mock_edit.return_value = None
            result = runner.invoke(workspace_commands.workspace, ["config", "--edit"])

        assert result.exit_code == 0

    def test_config_edit_saves_changes(self) -> None:
        """Test that config --edit reports update when editor returns content."""
        from unittest.mock import patch

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("click.edit") as mock_edit,
        ):
            mock_edit.return_value = "NEW_CONFIG=value"
            result = runner.invoke(workspace_commands.workspace, ["config", "--edit"])

        assert result.exit_code == 0
        assert "Configuration updated" in result.output

    def test_config_output_is_structured(self) -> None:
        """Test that config output follows key-value structure."""
        result = runner.invoke(workspace_commands.workspace, ["config"])

        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        config_lines = [line for line in lines if ":" in line]
        assert len(config_lines) >= 3

    def test_config_auto_cleanup_default(self) -> None:
        """Test that config shows auto_cleanup default value."""
        result = runner.invoke(workspace_commands.workspace, ["config"])

        assert result.exit_code == 0
        assert "Auto Cleanup:" in result.output
