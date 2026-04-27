"""E2E tests for memory CLI commands — full CRUD lifecycle against real SQLite database."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner, Result

from src.interfaces.cli.main import cli

runner = CliRunner()


class TestMemoryCommandsE2E:
    """E2E tests exercising all CLI commands against a real temp SQLite database."""

    def _invoke(self, db_path: str, args: list[str]) -> Result:
        """Helper: invoke CLI with --db flag pointing to temp database."""
        return runner.invoke(cli, ["--db", db_path, *args])

    def test_save_and_get(self, tmp_path: Path) -> None:
        db = str(tmp_path / "test.db")

        # Save
        result = self._invoke(db, ["save", "hello world"])
        assert result.exit_code == 0
        assert "Saved:" in result.stdout
        obs_id = result.stdout.split("Saved:")[1].strip()

        # Get
        result = self._invoke(db, ["get", obs_id])
        assert result.exit_code == 0
        assert "hello world" in result.stdout

    def test_save_with_all_options(self, tmp_path: Path) -> None:
        db = str(tmp_path / "test.db")

        result = self._invoke(
            db,
            [
                "save",
                "structured observation",
                "--type",
                "decision",
                "--project",
                "myproj",
                "--topic-key",
                "arch-decision",
            ],
        )
        assert result.exit_code == 0
        assert "Saved:" in result.stdout
        obs_id = result.stdout.split("Saved:")[1].strip()

        # Get and verify fields
        result = self._invoke(db, ["get", obs_id])
        assert result.exit_code == 0
        assert "structured observation" in result.stdout

    def test_search(self, tmp_path: Path) -> None:
        db = str(tmp_path / "test.db")

        self._invoke(db, ["save", "python testing patterns"])
        self._invoke(db, ["save", "golang concurrency model"])

        result = self._invoke(db, ["search", "python"])
        assert result.exit_code == 0
        assert "python" in result.stdout.lower()

    def test_list_with_type_filter(self, tmp_path: Path) -> None:
        db = str(tmp_path / "test.db")

        self._invoke(db, ["save", "a bugfix entry", "--type", "bugfix"])
        self._invoke(db, ["save", "a decision entry", "--type", "decision"])

        result = self._invoke(db, ["list", "--type", "bugfix"])
        assert result.exit_code == 0
        assert "bugfix entry" in result.stdout

    def test_update_content(self, tmp_path: Path) -> None:
        db = str(tmp_path / "test.db")

        result = self._invoke(db, ["save", "original content"])
        assert result.exit_code == 0
        obs_id = result.stdout.split("Saved:")[1].strip()

        result = self._invoke(db, ["update", obs_id, "--content", "updated content"])
        assert result.exit_code == 0
        assert "Updated:" in result.stdout

        result = self._invoke(db, ["get", obs_id])
        assert "updated content" in result.stdout

    def test_update_type_and_topic_key(self, tmp_path: Path) -> None:
        db = str(tmp_path / "test.db")

        result = self._invoke(db, ["save", "some observation"])
        assert result.exit_code == 0
        obs_id = result.stdout.split("Saved:")[1].strip()

        result = self._invoke(
            db, ["update", obs_id, "--type", "pattern", "--topic-key", "my-pattern"]
        )
        assert result.exit_code == 0
        assert "Updated:" in result.stdout

    def test_delete(self, tmp_path: Path) -> None:
        db = str(tmp_path / "test.db")

        result = self._invoke(db, ["save", "to be deleted"])
        assert result.exit_code == 0
        obs_id = result.stdout.split("Saved:")[1].strip()

        result = self._invoke(db, ["delete", obs_id, "--force"])
        assert result.exit_code == 0
        assert "Deleted" in result.stdout

        result = self._invoke(db, ["get", obs_id])
        assert result.exit_code == 1

    def test_context_command(self, tmp_path: Path) -> None:
        db = str(tmp_path / "test.db")

        self._invoke(db, ["save", "first context item"])
        self._invoke(db, ["save", "second context item"])
        self._invoke(db, ["save", "third context item"])

        result = self._invoke(db, ["context"])
        assert result.exit_code == 0
        assert "context item" in result.stdout

    def test_save_duplicate_topic_key_upserts(self, tmp_path: Path) -> None:
        db = str(tmp_path / "test.db")

        result = self._invoke(db, ["save", "version one", "--topic-key", "unique-key"])
        assert result.exit_code == 0

        result = self._invoke(db, ["save", "version two", "--topic-key", "unique-key"])
        assert result.exit_code == 0
        second_id = result.stdout.split("Saved:")[1].strip()

        # Upsert: same topic_key should produce same or new ID but content should be version two
        result = self._invoke(db, ["get", second_id])
        assert "version two" in result.stdout

    def test_save_with_all_types(self, tmp_path: Path) -> None:
        db = str(tmp_path / "test.db")

        valid_types = [
            "decision",
            "bugfix",
            "discovery",
            "pattern",
            "config",
            "preference",
            "architecture",
            "security",
            "performance",
            "learning",
        ]

        for obs_type in valid_types:
            result = self._invoke(db, ["save", f"test {obs_type}", "--type", obs_type])
            assert result.exit_code == 0, f"Failed for type={obs_type}: {result.output}"
