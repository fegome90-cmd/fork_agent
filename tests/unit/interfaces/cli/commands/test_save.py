"""Tests for CLI save command."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from src.domain.entities.observation import Observation

runner = CliRunner()


@pytest.fixture(autouse=True)
def _mock_git_detection_none() -> None:
    """Default: mock git project detection to return None (no side effects)."""
    with patch("src.interfaces.cli.commands.save._detect_git_project", return_value=None):
        yield


class TestSaveCommand:
    """Tests for save command."""

    def test_save_content_success(self) -> None:
        from src.interfaces.cli.commands.save import app

        mock_memory = MagicMock()
        mock_memory.save.return_value = Observation(
            id="test-id-123",
            timestamp=1000,
            content="test content",
        )

        result = runner.invoke(app, ["test content"], obj=mock_memory)

        assert result.exit_code == 0
        assert "Saved:" in result.stdout
        mock_memory.save.assert_called_once_with(content="test content", metadata=None, topic_key=None, project=None, type=None, title=None)

    def test_save_with_metadata_json(self) -> None:
        from src.interfaces.cli.commands.save import app

        mock_memory = MagicMock()
        mock_memory.save.return_value = Observation(
            id="test-id-123",
            timestamp=1000,
            content="test content",
        )

        result = runner.invoke(
            app,
            ["test content", "--metadata", '{"key": "value"}'],
            obj=mock_memory,
        )

        assert result.exit_code == 0
        mock_memory.save.assert_called_once_with(content="test content", metadata={"key": "value"}, topic_key=None, project=None, type=None, title=None)

    def test_save_invalid_metadata_json(self) -> None:
        from src.interfaces.cli.commands.save import app

        mock_memory = MagicMock()

        result = runner.invoke(
            app,
            ["test content", "--metadata", "not json"],
            obj=mock_memory,
        )

        assert result.exit_code == 1
        assert "Invalid JSON" in result.output

    def test_save_empty_content_fails(self) -> None:
        from src.interfaces.cli.commands.save import app

        mock_memory = MagicMock()

        result = runner.invoke(app, [""], obj=mock_memory)

        assert result.exit_code == 1

    def test_save_metadata_type_extracted_and_validated(self) -> None:
        """BUG-8: type from metadata JSON is extracted and passed to save()."""
        from src.interfaces.cli.commands.save import app

        mock_memory = MagicMock()
        mock_memory.save.return_value = Observation(
            id="test-id-123",
            timestamp=1000,
            content="test content",
        )

        result = runner.invoke(
            app,
            ["test content", "--metadata", '{"type": "decision"}'],
            obj=mock_memory,
        )

        assert result.exit_code == 0
        call_kwargs = mock_memory.save.call_args
        assert call_kwargs.kwargs["type"] == "decision"
        # type should be removed from metadata dict to avoid duplication
        assert call_kwargs.kwargs["metadata"] is None or "type" not in call_kwargs.kwargs["metadata"]

    def test_save_metadata_invalid_type_rejected(self) -> None:
        """BUG-8: Invalid type in metadata JSON is rejected."""
        from src.interfaces.cli.commands.save import app

        mock_memory = MagicMock()

        result = runner.invoke(
            app,
            ["test content", "--metadata", '{"type": "INVALID"}'],
            obj=mock_memory,
        )

        assert result.exit_code == 1
        assert "Invalid type" in result.output

    def test_save_metadata_topic_key_extracted(self) -> None:
        """BUG-9: topic_key from metadata JSON is extracted and passed."""
        from src.interfaces.cli.commands.save import app

        mock_memory = MagicMock()
        mock_memory.save.return_value = Observation(
            id="test-id-123",
            timestamp=1000,
            content="test content",
        )

        result = runner.invoke(
            app,
            ["test content", "--metadata", '{"topic_key": "test/meta"}'],
            obj=mock_memory,
        )

        assert result.exit_code == 0
        call_kwargs = mock_memory.save.call_args
        assert call_kwargs.kwargs["topic_key"] == "test/meta"
        assert call_kwargs.kwargs["metadata"] is None or "topic_key" not in call_kwargs.kwargs["metadata"]

    def test_save_metadata_project_extracted(self) -> None:
        """BUG-9: project from metadata JSON is extracted and passed."""
        from src.interfaces.cli.commands.save import app

        mock_memory = MagicMock()
        mock_memory.save.return_value = Observation(
            id="test-id-123",
            timestamp=1000,
            content="test content",
        )

        result = runner.invoke(
            app,
            ["test content", "--metadata", '{"project": "myapp"}'],
            obj=mock_memory,
        )

        assert result.exit_code == 0
        call_kwargs = mock_memory.save.call_args
        assert call_kwargs.kwargs["project"] == "myapp"
        assert call_kwargs.kwargs["metadata"] is None or "project" not in call_kwargs.kwargs["metadata"]


class TestSaveGitAutoDetection:
    """G5: Auto-detect project from git remote."""

    def test_save_auto_detects_project_from_git_remote(self) -> None:
        """When project is None and git remote exists, auto-detect project."""
        from src.interfaces.cli.commands.save import app

        mock_memory = MagicMock()
        mock_memory.save.return_value = Observation(
            id="test-id-123",
            timestamp=1000,
            content="test content",
        )

        with patch(
            "src.interfaces.cli.commands.save._detect_git_project", return_value="my-repo"
        ):
            result = runner.invoke(app, ["test content"], obj=mock_memory)

        assert result.exit_code == 0
        call_kwargs = mock_memory.save.call_args
        assert call_kwargs.kwargs["project"] == "my-repo"

    def test_save_cli_project_overrides_git_detection(self) -> None:
        """--project flag wins over git remote detection."""
        from src.interfaces.cli.commands.save import app

        mock_memory = MagicMock()
        mock_memory.save.return_value = Observation(
            id="test-id-123",
            timestamp=1000,
            content="test content",
        )

        with patch(
            "src.interfaces.cli.commands.save._detect_git_project", return_value="git-repo"
        ):
            result = runner.invoke(
                app, ["test content", "-p", "cli-project"], obj=mock_memory
            )

        assert result.exit_code == 0
        call_kwargs = mock_memory.save.call_args
        assert call_kwargs.kwargs["project"] == "cli-project"

    def test_save_metadata_project_overrides_git_detection(self) -> None:
        """project from --metadata JSON wins over git detection."""
        from src.interfaces.cli.commands.save import app

        mock_memory = MagicMock()
        mock_memory.save.return_value = Observation(
            id="test-id-123",
            timestamp=1000,
            content="test content",
        )

        with patch(
            "src.interfaces.cli.commands.save._detect_git_project", return_value="git-repo"
        ):
            result = runner.invoke(
                app, ["test content", "-m", '{"project":"meta-proj"}'], obj=mock_memory
            )

        assert result.exit_code == 0
        call_kwargs = mock_memory.save.call_args
        assert call_kwargs.kwargs["project"] == "meta-proj"

    def test_save_no_git_falls_back_gracefully(self) -> None:
        """When git detection fails, project stays None."""
        from src.interfaces.cli.commands.save import app

        mock_memory = MagicMock()
        mock_memory.save.return_value = Observation(
            id="test-id-123",
            timestamp=1000,
            content="test content",
        )

        with patch(
            "src.interfaces.cli.commands.save._detect_git_project",
            side_effect=Exception("git not found"),
        ):
            result = runner.invoke(app, ["test content"], obj=mock_memory)

        assert result.exit_code == 0
        call_kwargs = mock_memory.save.call_args
        assert call_kwargs.kwargs["project"] is None

    def test_save_no_remote_returns_none_project(self) -> None:
        """When git remote returns None, project stays None."""
        from src.interfaces.cli.commands.save import app

        mock_memory = MagicMock()
        mock_memory.save.return_value = Observation(
            id="test-id-123",
            timestamp=1000,
            content="test content",
        )

        with patch(
            "src.interfaces.cli.commands.save._detect_git_project", return_value=None
        ):
            result = runner.invoke(app, ["test content"], obj=mock_memory)

        assert result.exit_code == 0
        call_kwargs = mock_memory.save.call_args
        assert call_kwargs.kwargs["project"] is None

    def test_save_cli_flags_override_metadata(self) -> None:
        """BUG-9: CLI flags take precedence over metadata JSON fields."""
        from src.interfaces.cli.commands.save import app

        mock_memory = MagicMock()
        mock_memory.save.return_value = Observation(
            id="test-id-123",
            timestamp=1000,
            content="test content",
        )

        result = runner.invoke(
            app,
            [
                "test content",
                "--metadata", '{"topic_key": "meta/key", "project": "meta-proj"}',
                "--topic-key", "cli/key",
                "--project", "cli-proj",
            ],
            obj=mock_memory,
        )

        assert result.exit_code == 0
        call_kwargs = mock_memory.save.call_args
        # CLI flags should win
        assert call_kwargs.kwargs["topic_key"] == "cli/key"
        assert call_kwargs.kwargs["project"] == "cli-proj"
        # Metadata fields should NOT be duplicated
        meta = call_kwargs.kwargs["metadata"]
        assert meta is None or "topic_key" not in meta
        assert meta is None or "project" not in meta

    def test_save_metadata_all_entity_fields_extracted(self) -> None:
        """BUG-8/9: All entity fields extracted from metadata in one call."""
        from src.interfaces.cli.commands.save import app

        mock_memory = MagicMock()
        mock_memory.save.return_value = Observation(
            id="test-id-123",
            timestamp=1000,
            content="test content",
        )

        result = runner.invoke(
            app,
            [
                "test content",
                "--metadata", '{"type": "bugfix", "topic_key": "test/meta", "project": "meta-proj"}',
            ],
            obj=mock_memory,
        )

        assert result.exit_code == 0
        call_kwargs = mock_memory.save.call_args
        assert call_kwargs.kwargs["type"] == "bugfix"
        assert call_kwargs.kwargs["topic_key"] == "test/meta"
        assert call_kwargs.kwargs["project"] == "meta-proj"
        # None of these should leak into metadata
        meta = call_kwargs.kwargs["metadata"]
        assert meta is None or "type" not in meta
        assert meta is None or "topic_key" not in meta
        assert meta is None or "project" not in meta
