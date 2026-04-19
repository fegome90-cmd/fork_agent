"""Tests for CLI export command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from src.domain.entities.observation import Observation

runner = CliRunner()


@pytest.fixture()
def sample_observations() -> list[Observation]:
    return [
        Observation(
            id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            timestamp=1740000000000,
            content="Decision content",
            title="Test Decision",
            type="decision",
            project="g10",
            topic_key="g10/test-export",
        ),
        Observation(
            id="11111111-2222-3333-4444-555555555555",
            timestamp=1740000000000,
            content="Orphan content",
            type="learning",
        ),
    ]


@pytest.fixture()
def mock_service(sample_observations: list[Observation]) -> MagicMock:
    svc = MagicMock()
    svc.get_recent.return_value = sample_observations
    return svc


class TestExportObsidianDryRun:
    """Tests for export obsidian --dry-run."""

    def test_dry_run_shows_count(self, mock_service: MagicMock) -> None:
        from src.interfaces.cli.commands.export import app

        result = runner.invoke(app, ["--dry-run"], obj=mock_service)

        assert result.exit_code == 0
        assert "Would export 2 observations" in result.stdout

    def test_dry_run_shows_first_ten(self, mock_service: MagicMock) -> None:
        from src.interfaces.cli.commands.export import app

        obs_list = [
            Observation(id=f"id-{i}", timestamp=1000, content=f"obs {i}", type="decision")
            for i in range(15)
        ]
        mock_service.get_recent.return_value = obs_list

        result = runner.invoke(app, ["--dry-run"], obj=mock_service)

        assert result.exit_code == 0
        assert "... and 5 more" in result.stdout


class TestExportObsidianFilters:
    """Tests for filter options."""

    def test_filter_by_project(self, mock_service: MagicMock) -> None:
        from src.interfaces.cli.commands.export import app

        result = runner.invoke(app, ["--dry-run", "--project", "g10"], obj=mock_service)

        assert result.exit_code == 0
        assert "Would export 1 observations" in result.stdout

    def test_filter_by_type(self, mock_service: MagicMock) -> None:
        from src.interfaces.cli.commands.export import app

        result = runner.invoke(app, ["--dry-run", "--type", "decision"], obj=mock_service)

        assert result.exit_code == 0
        assert "Would export 1 observations" in result.stdout

    def test_filter_by_topic_key_prefix(self, mock_service: MagicMock) -> None:
        from src.interfaces.cli.commands.export import app

        result = runner.invoke(
            app, ["--dry-run", "--topic-key", "g10/"], obj=mock_service
        )

        assert result.exit_code == 0
        assert "Would export 1 observations" in result.stdout

    def test_filter_no_match(self, mock_service: MagicMock) -> None:
        from src.interfaces.cli.commands.export import app

        result = runner.invoke(
            app, ["--dry-run", "--project", "nonexistent"], obj=mock_service
        )

        assert result.exit_code == 0
        assert "Would export 0 observations" in result.stdout


class TestExportObsidianActual:
    """Tests for actual file export."""

    def test_export_writes_files(self, mock_service: MagicMock, tmp_path: Path) -> None:
        from src.interfaces.cli.commands.export import app

        result = runner.invoke(app, ["-o", str(tmp_path)], obj=mock_service)

        assert result.exit_code == 0
        assert "Exported 2 observations" in result.stdout
        assert (tmp_path / "g10" / "test-export.md").exists()
        assert (tmp_path / "_orphans" / "11111111.md").exists()
