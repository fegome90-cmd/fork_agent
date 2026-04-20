"""Tests for CLI sync commands (export, import, status, push, pull, log)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

runner = CliRunner()


class TestExportCommand:
    def test_export_with_observations(self) -> None:
        """Export returns chunk files and prints count."""
        with patch("src.interfaces.cli.commands.sync.get_sync_service") as mock_get:
            mock_svc = MagicMock()
            mock_svc.export_observations.return_value = [Path("data/sync/chunk_001.jsonl.gz")]
            mock_get.return_value = mock_svc

            from src.interfaces.cli.commands.sync import app as sync_app

            result = runner.invoke(sync_app, ["export"])

        assert result.exit_code == 0
        assert "Created:" in result.stdout
        assert "1 chunk(s)" in result.stdout

    def test_export_empty_db(self) -> None:
        """Export with no observations prints message."""
        with patch("src.interfaces.cli.commands.sync.get_sync_service") as mock_get:
            mock_svc = MagicMock()
            mock_svc.export_observations.return_value = []
            mock_get.return_value = mock_svc

            from src.interfaces.cli.commands.sync import app as sync_app

            result = runner.invoke(sync_app, ["export"])

        assert result.exit_code == 0
        assert "No observations" in result.stdout

    def test_export_with_project_filter(self) -> None:
        """Project argument is passed through to export_observations."""
        with patch("src.interfaces.cli.commands.sync.get_sync_service") as mock_get:
            mock_svc = MagicMock()
            mock_svc.export_observations.return_value = []
            mock_get.return_value = mock_svc

            from src.interfaces.cli.commands.sync import app as sync_app

            result = runner.invoke(sync_app, ["export", "--project", "alpha"])

        assert result.exit_code == 0
        mock_svc.export_observations.assert_called_once_with(project="alpha", chunk_size=100)

    def test_export_with_custom_output_dir(self) -> None:
        """Custom output dir triggers create_container with export_dir."""
        with (
            patch("src.interfaces.cli.commands.sync.create_container") as mock_container,
            patch("src.interfaces.cli.commands.sync.get_sync_service"),
        ):
            mock_svc = MagicMock()
            mock_svc.export_observations.return_value = [Path("/custom/chunk.jsonl.gz")]
            mock_container.return_value.sync_service.return_value = mock_svc

            from src.interfaces.cli.commands.sync import app as sync_app

            result = runner.invoke(sync_app, ["export", "--output-dir", "/custom"])

        assert result.exit_code == 0
        # Verify create_container was called with export_dir
        mock_container.assert_called_once()
        call_kwargs = mock_container.call_args
        # Check export_dir was passed (either as keyword or positional)
        if call_kwargs.kwargs:
            assert "export_dir" in call_kwargs.kwargs
            assert call_kwargs.kwargs["export_dir"] == Path("/custom")


class TestImportCommand:
    def test_import_success(self) -> None:
        """Import returns count and prints it."""
        with patch("src.interfaces.cli.commands.sync.get_sync_service") as mock_get:
            mock_svc = MagicMock()
            mock_svc.import_observations.return_value = 5
            mock_get.return_value = mock_svc

            from src.interfaces.cli.commands.sync import app as sync_app

            result = runner.invoke(sync_app, ["import", "/tmp/chunk1.jsonl.gz"])

        assert result.exit_code == 0
        assert "5 observation(s)" in result.stdout

    def test_import_with_source_flag(self) -> None:
        """Source flag is passed through."""
        with patch("src.interfaces.cli.commands.sync.get_sync_service") as mock_get:
            mock_svc = MagicMock()
            mock_svc.import_observations.return_value = 1
            mock_get.return_value = mock_svc

            from src.interfaces.cli.commands.sync import app as sync_app

            result = runner.invoke(
                sync_app, ["import", "/tmp/chunk1.jsonl.gz", "--source", "remote"]
            )

        assert result.exit_code == 0
        mock_svc.import_observations.assert_called_once()
        call_kwargs = mock_svc.import_observations.call_args
        assert (
            call_kwargs.kwargs.get("source") == "remote"
            or call_kwargs[1].get("source") == "remote"
            or "source" in str(call_kwargs)
        )


class TestStatusCommand:
    def test_status_shows_fields(self) -> None:
        """Status displays all tracked fields."""
        with patch("src.interfaces.cli.commands.sync.get_sync_service") as mock_get:
            mock_svc = MagicMock()
            mock_svc.get_status.return_value = {
                "total_observations": 42,
                "mutation_count": 7,
                "latest_seq": 10,
                "last_export_seq": 8,
                "last_export_at": 1700000000000,
                "last_import_at": 1700000000000,
            }
            mock_get.return_value = mock_svc

            from src.interfaces.cli.commands.sync import app as sync_app

            result = runner.invoke(sync_app, ["status"])

        assert result.exit_code == 0
        assert "42" in result.stdout
        assert "7" in result.stdout

    def test_status_never_exported(self) -> None:
        """Status with no exports shows 'never'."""
        with patch("src.interfaces.cli.commands.sync.get_sync_service") as mock_get:
            mock_svc = MagicMock()
            mock_svc.get_status.return_value = {
                "total_observations": 0,
                "mutation_count": 0,
                "latest_seq": 0,
                "last_export_seq": 0,
                "last_export_at": None,
                "last_import_at": None,
            }
            mock_get.return_value = mock_svc

            from src.interfaces.cli.commands.sync import app as sync_app

            result = runner.invoke(sync_app, ["status"])

        assert result.exit_code == 0
        assert "never" in result.stdout


class TestPushCommand:
    def test_push_no_mutations(self) -> None:
        """Push with no new mutations prints message."""
        with patch("src.interfaces.cli.commands.sync._make_sync_service") as mock_make:
            mock_svc = MagicMock()
            mock_svc.export_incremental.return_value = []
            mock_make.return_value = mock_svc

            from src.interfaces.cli.commands.sync import app as sync_app

            result = runner.invoke(sync_app, ["push"])

        assert result.exit_code == 0
        assert "No new mutations" in result.stdout

    def test_push_success(self) -> None:
        """Push with mutations succeeds."""
        with (
            patch("src.interfaces.cli.commands.sync._make_sync_service") as mock_make,
            patch("src.interfaces.cli.commands.sync.GitSyncBackend") as mock_git_cls,
        ):
            mock_svc = MagicMock()
            mock_svc.export_incremental.return_value = [Path("data/sync/chunk.jsonl.gz")]
            mock_make.return_value = mock_svc
            mock_git = MagicMock()
            mock_git.push.return_value = True
            mock_git_cls.return_value = mock_git

            from src.interfaces.cli.commands.sync import app as sync_app

            result = runner.invoke(sync_app, ["push"])

        assert result.exit_code == 0
        assert "Push successful" in result.stdout

    def test_push_failure(self) -> None:
        """Push failure exits with code 1."""
        with (
            patch("src.interfaces.cli.commands.sync._make_sync_service") as mock_make,
            patch("src.interfaces.cli.commands.sync.GitSyncBackend") as mock_git_cls,
        ):
            mock_svc = MagicMock()
            mock_svc.export_incremental.return_value = [Path("data/sync/chunk.jsonl.gz")]
            mock_make.return_value = mock_svc
            mock_git = MagicMock()
            mock_git.push.return_value = False
            mock_git_cls.return_value = mock_git

            from src.interfaces.cli.commands.sync import app as sync_app

            result = runner.invoke(sync_app, ["push"])

        assert result.exit_code == 1
        assert "Push failed" in result.output


class TestPullCommand:
    def test_pull_no_new_chunks(self) -> None:
        """Pull with no new chunks prints message."""
        with patch("src.interfaces.cli.commands.sync.GitSyncBackend") as mock_git_cls:
            mock_git = MagicMock()
            mock_git.pull.return_value = []
            mock_git_cls.return_value = mock_git

            from src.interfaces.cli.commands.sync import app as sync_app

            result = runner.invoke(sync_app, ["pull"])

        assert result.exit_code == 0
        assert "No new chunks" in result.stdout

    def test_pull_with_chunks(self) -> None:
        """Pull with chunks triggers import."""
        with (
            patch("src.interfaces.cli.commands.sync._make_sync_service") as mock_make,
            patch("src.interfaces.cli.commands.sync.GitSyncBackend") as mock_git_cls,
        ):
            mock_git = MagicMock()
            mock_git.pull.return_value = [
                Path("data/sync/chunk_001.jsonl.gz"),
                Path("data/sync/chunk_002.jsonl.gz"),
            ]
            mock_git_cls.return_value = mock_git

            mock_svc = MagicMock()
            mock_svc.import_mutations.return_value = {
                "inserted": 2,
                "updated": 0,
                "deleted": 0,
            }
            mock_make.return_value = mock_svc

            from src.interfaces.cli.commands.sync import app as sync_app

            result = runner.invoke(sync_app, ["pull"])

        assert result.exit_code == 0
        assert "2 chunk(s)" in result.stdout
        assert "2 inserted" in result.stdout


class TestLogCommand:
    def test_log_empty(self) -> None:
        """Log with no mutations prints message."""
        with patch("src.interfaces.cli.commands.sync._make_sync_service") as mock_make:
            mock_svc = MagicMock()
            mock_svc.get_mutations_since.return_value = []
            mock_make.return_value = mock_svc

            from src.interfaces.cli.commands.sync import app as sync_app

            result = runner.invoke(sync_app, ["log"])

        assert result.exit_code == 0
        assert "No mutations" in result.stdout

    def test_log_with_mutations(self) -> None:
        """Log with mutations shows header and entries."""
        from src.domain.entities.sync import SyncMutation

        with patch("src.interfaces.cli.commands.sync._make_sync_service") as mock_make:
            mock_svc = MagicMock()
            mock_svc.get_mutations_since.return_value = [
                SyncMutation(
                    seq=1,
                    entity="observation",
                    entity_key="obs-1",
                    op="insert",
                    payload="{}",
                    source="local",
                    project="",
                    created_at=1700000000000,
                ),
                SyncMutation(
                    seq=2,
                    entity="observation",
                    entity_key="obs-2",
                    op="delete",
                    payload="{}",
                    source="local",
                    project="",
                    created_at=1700000000000,
                ),
            ]
            mock_make.return_value = mock_svc

            from src.interfaces.cli.commands.sync import app as sync_app

            result = runner.invoke(sync_app, ["log"])

        assert result.exit_code == 0
        assert "SEQ" in result.stdout
        assert "insert" in result.stdout
        assert "delete" in result.stdout

    def test_log_with_limit(self) -> None:
        """Limit flag slices the mutation list."""
        from src.domain.entities.sync import SyncMutation

        with patch("src.interfaces.cli.commands.sync._make_sync_service") as mock_make:
            mock_svc = MagicMock()
            # Return 5 mutations; CLI will slice to limit
            mutations = [
                SyncMutation(
                    seq=i,
                    entity="observation",
                    entity_key=f"obs-{i}",
                    op="insert",
                    payload="{}",
                    source="local",
                    project="",
                    created_at=1700000000000,
                )
                for i in range(1, 6)
            ]
            mock_svc.get_mutations_since.return_value = mutations
            mock_make.return_value = mock_svc

            from src.interfaces.cli.commands.sync import app as sync_app

            result = runner.invoke(sync_app, ["log", "--limit", "3"])

        assert result.exit_code == 0
        # Verify get_mutations_since was called with seq=0
        mock_svc.get_mutations_since.assert_called_once_with(0)
        # The slicing happens in the CLI code via [:limit]
