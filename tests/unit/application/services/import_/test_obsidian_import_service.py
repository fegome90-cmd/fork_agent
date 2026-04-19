"""Tests for ObsidianImportService."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.application.services.import_.obsidian_import_service import (
    ObsidianImportService,
)


def _write_obsidian_md(
    path: Path,
    *,
    id: str = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    type: str = "decision",
    project: str = "test-proj",
    topic_key: str = "test/topic",
    created: str = "2026-04-18T12:00:00",
    revision_count: int = 1,
    tags: list[str] | None = None,
    title: str | None = None,
    content: str = "Observation content here.",
) -> None:
    """Write a well-formed Obsidian markdown file."""
    frontmatter: dict = {
        "id": id,
        "type": type,
        "project": project,
        "topic_key": topic_key,
        "created": created,
        "revision_count": revision_count,
    }
    if tags is not None:
        frontmatter["tags"] = tags

    fm_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
    body = ""
    body = f"# {title}\n\n{content}\n" if title else f"{content}\n"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{fm_str}---\n{body}", encoding="utf-8")


@pytest.fixture()
def import_service() -> ObsidianImportService:
    return ObsidianImportService()


class TestImportSingleFile:
    """test_import_single_file - basic happy path."""

    def test_happy_path(self, tmp_path: Path, import_service: ObsidianImportService) -> None:
        _write_obsidian_md(
            tmp_path / "test" / "topic.md",
            content="Hello world",
            title="My Title",
        )
        result = import_service.import_from_dir(
            input_dir=tmp_path,
            memory_save_fn=_fake_save,
            existing_ids=set(),
        )
        assert result.total_files == 1
        assert result.imported == 1
        assert result.skipped == 0
        assert len(result.errors) == 0
        assert len(result.imported_ids) == 1


class TestImportNestedDirs:
    """test_import_nested_dirs - topic_key from directory structure."""

    def test_nested_dirs_imported(self, tmp_path: Path, import_service: ObsidianImportService) -> None:
        _write_obsidian_md(
            tmp_path / "compact" / "session-summary.md",
            topic_key="compact/session-summary",
            content="Session summary content",
        )
        _write_obsidian_md(
            tmp_path / "project" / "decision-1.md",
            topic_key="project/decision-1",
            content="A decision",
        )
        result = import_service.import_from_dir(
            input_dir=tmp_path,
            memory_save_fn=_fake_save,
            existing_ids=set(),
        )
        assert result.total_files == 2
        assert result.imported == 2


class TestImportNoFrontmatter:
    """test_import_no_frontmatter - skip with error."""

    def test_skip_no_frontmatter(self, tmp_path: Path, import_service: ObsidianImportService) -> None:
        (tmp_path / "no-frontmatter.md").write_text(
            "# Just a regular markdown\n\nNo frontmatter here.\n", encoding="utf-8"
        )
        result = import_service.import_from_dir(
            input_dir=tmp_path,
            memory_save_fn=_fake_save,
            existing_ids=set(),
        )
        assert result.total_files == 1
        assert result.imported == 0
        assert result.skipped == 0
        assert len(result.errors) == 1
        assert "no-frontmatter.md" in result.errors[0]


class TestImportInvalidYaml:
    """test_import_invalid_yaml - skip with error."""

    def test_skip_invalid_yaml(self, tmp_path: Path, import_service: ObsidianImportService) -> None:
        path = tmp_path / "bad-yaml.md"
        path.write_text(
            "---\nid: abc\n: broken yaml [[[\n---\ncontent\n", encoding="utf-8"
        )
        result = import_service.import_from_dir(
            input_dir=tmp_path,
            memory_save_fn=_fake_save,
            existing_ids=set(),
        )
        assert result.total_files == 1
        assert result.imported == 0
        assert len(result.errors) == 1


class TestImportDuplicateSkip:
    """test_import_duplicate_skip - --skip-duplicates behavior."""

    def test_skip_existing_id(self, tmp_path: Path, import_service: ObsidianImportService) -> None:
        _write_obsidian_md(
            tmp_path / "dup.md",
            id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            content="Duplicate",
        )
        result = import_service.import_from_dir(
            input_dir=tmp_path,
            memory_save_fn=_fake_save,
            existing_ids={"aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"},
            skip_duplicates=True,
        )
        assert result.total_files == 1
        assert result.imported == 0
        assert result.skipped == 1
        assert len(result.errors) == 0

    def test_overwrite_when_not_skipping(self, tmp_path: Path, import_service: ObsidianImportService) -> None:
        _write_obsidian_md(
            tmp_path / "dup.md",
            id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            content="Will overwrite",
        )
        result = import_service.import_from_dir(
            input_dir=tmp_path,
            memory_save_fn=_fake_save,
            existing_ids={"aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"},
            skip_duplicates=False,
        )
        assert result.imported == 1
        assert result.skipped == 0


class TestImportProjectOverride:
    """test_import_project_override - --project flag."""

    def test_project_override(self, tmp_path: Path, import_service: ObsidianImportService) -> None:
        saved_project: str | None = None

        def capture_save(content: str, **kwargs: object) -> str:
            nonlocal saved_project
            saved_project = kwargs.get("project")  # type: ignore[assignment]
            return "fake-id"

        _write_obsidian_md(
            tmp_path / "test.md",
            project="original-project",
            content="Test",
        )
        import_service.import_from_dir(
            input_dir=tmp_path,
            memory_save_fn=capture_save,
            existing_ids=set(),
            project_override="override-project",
        )
        assert saved_project == "override-project"


class TestImportDryRun:
    """test_import_dry_run - no writes, returns preview."""

    def test_dry_run_no_writes(self, tmp_path: Path, import_service: ObsidianImportService) -> None:
        _write_obsidian_md(tmp_path / "test.md", content="Preview only")

        called = False

        def save_should_not_call(_content: str, **_kwargs: object) -> str:
            nonlocal called
            called = True
            return "fake-id"

        result = import_service.import_from_dir(
            input_dir=tmp_path,
            memory_save_fn=save_should_not_call,
            existing_ids=set(),
            dry_run=True,
        )
        assert result.total_files == 1
        assert result.imported == 0
        assert result.skipped == 0
        assert not called


class TestImportDerivesTopicKeyFromPath:
    """test_import_derives_topic_key_from_path - when frontmatter missing topic_key."""

    def test_derives_from_path(self, tmp_path: Path, import_service: ObsidianImportService) -> None:
        saved_topic: str | None = None

        def capture_save(content: str, **kwargs: object) -> str:
            nonlocal saved_topic
            saved_topic = kwargs.get("topic_key")  # type: ignore[assignment]
            return "fake-id"

        path = tmp_path / "deep" / "nested" / "path.md"
        _write_obsidian_md(path, topic_key="", content="Nested content")
        # Remove topic_key from frontmatter
        raw = path.read_text(encoding="utf-8")
        # Remove the topic_key line from YAML
        lines = raw.split("\n")
        filtered = [ln for ln in lines if not ln.startswith("topic_key:")]
        path.write_text("\n".join(filtered), encoding="utf-8")

        import_service.import_from_dir(
            input_dir=tmp_path,
            memory_save_fn=capture_save,
            existing_ids=set(),
        )
        assert saved_topic == "deep/nested/path"


class TestImportStripsH1Title:
    """test_import_strips_h1_title - body starts with # Title\\n\\n."""

    def test_strips_h1_from_content(self, tmp_path: Path, import_service: ObsidianImportService) -> None:
        saved_content: str | None = None

        def capture_save(content: str, **_kwargs: object) -> str:
            nonlocal saved_content
            saved_content = content
            return "fake-id"

        _write_obsidian_md(
            tmp_path / "with-title.md",
            title="Some Title",
            content="Real content body.",
        )
        import_service.import_from_dir(
            input_dir=tmp_path,
            memory_save_fn=capture_save,
            existing_ids=set(),
        )
        assert saved_content == "Real content body."
        assert "# Some Title" not in (saved_content or "")


class TestImportPathTraversalBlocked:
    """test_import_path_traversal_blocked - malicious paths rejected."""

    def test_traversal_in_file_path(self, tmp_path: Path, import_service: ObsidianImportService) -> None:
        # Create a symlink or actual path outside the input dir
        outside = tmp_path.parent / "evil.md"
        outside.write_text(
            "---\nid: evil-id\ntype: bugfix\n---\nstolen content\n", encoding="utf-8"
        )
        try:
            (tmp_path / "symlink.md").symlink_to(outside)
        except OSError:
            pytest.skip("symlink creation not supported")

        result = import_service.import_from_dir(
            input_dir=tmp_path,
            memory_save_fn=_fake_save,
            existing_ids=set(),
        )
        # Symlink should be blocked (path traversal or not a regular file)
        assert result.imported == 0
        assert len(result.errors) >= 1


class TestImportMissingTypeDefaults:
    """Missing type defaults to 'note'."""

    def test_default_type(self, tmp_path: Path, import_service: ObsidianImportService) -> None:
        saved_type: str | None = None

        def capture_save(content: str, **kwargs: object) -> str:
            nonlocal saved_type
            saved_type = kwargs.get("type")  # type: ignore[assignment]
            return "fake-id"

        _write_obsidian_md(
            tmp_path / "notype.md",
            type="",
            content="No type",
        )
        # Remove type from frontmatter
        path = tmp_path / "notype.md"
        raw = path.read_text(encoding="utf-8")
        lines = raw.split("\n")
        filtered = [ln for ln in lines if not ln.startswith("type:")]
        path.write_text("\n".join(filtered), encoding="utf-8")

        import_service.import_from_dir(
            input_dir=tmp_path,
            memory_save_fn=capture_save,
            existing_ids=set(),
        )
        assert saved_type is None  # save() accepts None, the Observation defaults handle it


class TestImportBinaryFileSkipped:
    """Binary files are skipped."""

    def test_binary_skipped(self, tmp_path: Path, import_service: ObsidianImportService) -> None:
        (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
        result = import_service.import_from_dir(
            input_dir=tmp_path,
            memory_save_fn=_fake_save,
            existing_ids=set(),
        )
        assert result.total_files == 0


class TestImportEmptyDir:
    """Empty directory returns zero results."""

    def test_empty_dir(self, tmp_path: Path, import_service: ObsidianImportService) -> None:
        result = import_service.import_from_dir(
            input_dir=tmp_path,
            memory_save_fn=_fake_save,
            existing_ids=set(),
        )
        assert result.total_files == 0
        assert result.imported == 0


# --- Helpers ---


def _fake_save(content: str, **_kwargs: object) -> str:
    return "fake-id"
