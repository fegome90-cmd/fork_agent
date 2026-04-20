"""End-to-end tests for configuration loading.

Tests:
- Create config file
- Load config
- Verify values are correct
- Test default values
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.infrastructure.config.workspace_config import (
    ForkAgentConfig,
    TmuxConfigModel,
    WorkspaceConfigModel,
)


class TestConfigLoadingE2E:
    """E2E tests for configuration loading."""

    def test_load_config_from_file(self, tmp_path: Path) -> None:
        """Test loading configuration from a YAML file."""
        # Create config file
        config_file = tmp_path / ".fork_agent.yaml"
        config_data = {
            "workspace": {
                "default_layout": "SIBLING",
                "auto_cleanup": True,
                "hooks_dir": "/tmp/hooks",
            },
            "tmux": {
                "session_prefix": "test-",
                "attach_on_create": False,
            },
        }

        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        # Load config
        config = ForkAgentConfig.load(config_file)

        # Verify values
        assert config.workspace.default_layout == "SIBLING"
        assert config.workspace.auto_cleanup is True
        assert config.workspace.hooks_dir == Path("/tmp/hooks")
        assert config.tmux.session_prefix == "test-"
        assert config.tmux.attach_on_create is False

    def test_load_config_with_defaults(self, tmp_path: Path) -> None:  # noqa: ARG002
        """Test loading config returns defaults when no file exists."""
        # Load config without file
        config = ForkAgentConfig.load(None)

        # Verify defaults
        assert config.workspace.default_layout == "NESTED"
        assert config.workspace.auto_cleanup is False
        assert config.workspace.hooks_dir is None
        assert config.tmux.session_prefix == "fork-"
        assert config.tmux.attach_on_create is True

    def test_load_config_validates_layout(self, tmp_path: Path) -> None:
        """Test that invalid layout is corrected to valid one."""
        config_file = tmp_path / ".fork_agent.yaml"
        config_data = {
            "workspace": {
                "default_layout": "INVALID_LAYOUT",
            },
        }

        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        # Load config - should use default due to validation
        config = ForkAgentConfig.load(config_file)

        # The validator should raise an error or use default
        # Based on implementation, it should return defaults on error
        assert config.workspace.default_layout in {"NESTED", "OUTER_NESTED", "SIBLING"}

    def test_save_and_load_config(self, tmp_path: Path) -> None:
        """Test saving and loading configuration."""
        # Create initial config
        config = ForkAgentConfig(
            workspace=WorkspaceConfigModel(
                default_layout="OUTER_NESTED",
                auto_cleanup=True,
                hooks_dir=Path("/custom/hooks"),
            ),
            tmux=TmuxConfigModel(
                session_prefix="custom-",
                attach_on_create=False,
            ),
        )

        # Save config
        config_file = tmp_path / "saved_config.yaml"
        config.save(config_file)

        # Verify file exists
        assert config_file.exists()

        # Load it back
        loaded_config = ForkAgentConfig.load(config_file)

        # Verify values match
        assert loaded_config.workspace.default_layout == "OUTER_NESTED"
        assert loaded_config.workspace.auto_cleanup is True
        assert loaded_config.workspace.hooks_dir == Path("/custom/hooks")
        assert loaded_config.tmux.session_prefix == "custom-"
        assert loaded_config.tmux.attach_on_create is False

    def test_load_config_with_nested_layout(self, tmp_path: Path) -> None:
        """Test loading config with NESTED layout."""
        config_file = tmp_path / ".fork_agent.yaml"
        config_data = {
            "workspace": {
                "default_layout": "NESTED",
            },
        }

        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        config = ForkAgentConfig.load(config_file)

        assert config.workspace.default_layout == "NESTED"

    def test_load_config_with_outer_nested_layout(self, tmp_path: Path) -> None:
        """Test loading config with OUTER_NESTED layout."""
        config_file = tmp_path / ".fork_agent.yaml"
        config_data = {
            "workspace": {
                "default_layout": "OUTER_NESTED",
            },
        }

        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        config = ForkAgentConfig.load(config_file)

        assert config.workspace.default_layout == "OUTER_NESTED"

    def test_load_config_creates_parent_directories(self, tmp_path: Path) -> None:
        """Test that save creates parent directories."""
        config = ForkAgentConfig()

        config_file = tmp_path / "subdir" / "nested" / ".fork_agent.yaml"

        # Save should create parent directories
        config.save(config_file)

        assert config_file.exists()
        assert config_file.parent.exists()

    def test_load_config_nonexistent_file_returns_defaults(self, tmp_path: Path) -> None:
        """Test loading non-existent file returns defaults."""
        config_file = tmp_path / "nonexistent.yaml"

        # File doesn't exist
        assert not config_file.exists()

        config = ForkAgentConfig.load(config_file)

        # Should return defaults
        assert config.workspace.default_layout == "NESTED"
        assert config.workspace.auto_cleanup is False

    def test_config_is_immutable(self, tmp_path: Path) -> None:  # noqa: ARG002
        """Test that loaded config is immutable (frozen)."""
        config = ForkAgentConfig()

        # Try to modify - should raise error
        with pytest.raises(
            (TypeError, ValueError)
        ):  # pydantic validates on init, frozen prevents mutation
            config.workspace.default_layout = "SIBLING"  # type: ignore

    def test_load_config_with_partial_values(self, tmp_path: Path) -> None:
        """Test loading config with only some values specified."""
        config_file = tmp_path / ".fork_agent.yaml"
        config_data = {
            "workspace": {
                "default_layout": "SIBLING",
            },
            # tmux section omitted
        }

        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        config = ForkAgentConfig.load(config_file)

        # Specified value
        assert config.workspace.default_layout == "SIBLING"

        # Defaults for unspecified
        assert config.workspace.auto_cleanup is False
        assert config.tmux.session_prefix == "fork-"
