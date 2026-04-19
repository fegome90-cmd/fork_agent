"""Tests for ObsidianExportService."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.domain.entities.observation import Observation


@pytest.fixture()
def sample_obs() -> Observation:
    return Observation(
        id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        timestamp=1740000000000,
        content="Test observation content for export.",
        title="Test Export",
        type="decision",
        project="g10",
        topic_key="g10/test-export",
        revision_count=1,
    )


@pytest.fixture()
def orphan_obs() -> Observation:
    return Observation(
        id="11111111-2222-3333-4444-555555555555",
        timestamp=1740000000000,
        content="Orphan observation without topic_key.",
        type="learning",
    )


class TestBuildPath:
    """Tests for _build_path."""

    def test_topic_key_creates_nested_path(self, sample_obs: Observation) -> None:
        from src.application.services.export.obsidian_export_service import ObsidianExportService

        svc = ObsidianExportService()
        path = svc._build_path(sample_obs, Path("/output"))
        assert path == Path("/output/g10/test-export.md")

    def test_no_topic_key_creates_orphan_path(self, orphan_obs: Observation) -> None:
        from src.application.services.export.obsidian_export_service import ObsidianExportService

        svc = ObsidianExportService()
        path = svc._build_path(orphan_obs, Path("/output"))
        assert path == Path("/output/_orphans/11111111.md")

    def test_deep_topic_key(self) -> None:
        from src.application.services.export.obsidian_export_service import ObsidianExportService

        svc = ObsidianExportService()
        obs = Observation(
            id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            timestamp=1000,
            content="deep",
            topic_key="a/b/c/d",
        )
        path = svc._build_path(obs, Path("/output"))
        assert path == Path("/output/a/b/c/d.md")

    def test_special_chars_in_topic_key_sanitized(self) -> None:
        from src.application.services.export.obsidian_export_service import ObsidianExportService

        svc = ObsidianExportService()
        obs = Observation(
            id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            timestamp=1000,
            content="special",
            topic_key="hello-world/bad@char",
        )
        path = svc._build_path(obs, Path("/output"))
        assert path == Path("/output/hello-world/bad_char.md")


class TestRender:
    """Tests for _render."""

    def test_frontmatter_contains_required_fields(self, sample_obs: Observation) -> None:
        from src.application.services.export.obsidian_export_service import ObsidianExportService

        svc = ObsidianExportService()
        result = svc._render(sample_obs)

        assert result.startswith("---\n")
        assert result.endswith("\n")

        # Parse YAML between --- markers
        parts = result.split("---")
        fm = yaml.safe_load(parts[1])
        assert fm["id"] == sample_obs.id
        assert fm["type"] == "decision"
        assert fm["project"] == "g10"
        assert fm["topic_key"] == "g10/test-export"
        assert fm["revision_count"] == 1

    def test_title_uses_obs_title(self, sample_obs: Observation) -> None:
        from src.application.services.export.obsidian_export_service import ObsidianExportService

        svc = ObsidianExportService()
        result = svc._render(sample_obs)
        assert "# Test Export\n" in result

    def test_title_falls_back_to_topic_key(self) -> None:
        from src.application.services.export.obsidian_export_service import ObsidianExportService

        svc = ObsidianExportService()
        obs = Observation(
            id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            timestamp=1000,
            content="fallback",
            topic_key="some/topic",
        )
        result = svc._render(obs)
        assert "# some/topic\n" in result

    def test_title_falls_back_to_id_short(self, orphan_obs: Observation) -> None:
        from src.application.services.export.obsidian_export_service import ObsidianExportService

        svc = ObsidianExportService()
        result = svc._render(orphan_obs)
        assert "# 11111111\n" in result

    def test_content_included_after_frontmatter(self, sample_obs: Observation) -> None:
        from src.application.services.export.obsidian_export_service import ObsidianExportService

        svc = ObsidianExportService()
        result = svc._render(sample_obs)
        assert sample_obs.content in result


class TestBuildTags:
    """Tests for _build_tags."""

    def test_tags_include_type_and_topic(self, sample_obs: Observation) -> None:
        from src.application.services.export.obsidian_export_service import ObsidianExportService

        svc = ObsidianExportService()
        tags = svc._build_tags(sample_obs)
        assert "decision" in tags
        assert "g10" in tags
        assert "test-export" in tags

    def test_tags_only_type_when_no_topic(self, orphan_obs: Observation) -> None:
        from src.application.services.export.obsidian_export_service import ObsidianExportService

        svc = ObsidianExportService()
        tags = svc._build_tags(orphan_obs)
        assert tags == ["learning"]

    def test_tags_empty_when_no_type_no_topic(self) -> None:
        from src.application.services.export.obsidian_export_service import ObsidianExportService

        svc = ObsidianExportService()
        obs = Observation(
            id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            timestamp=1000,
            content="no tags",
        )
        tags = svc._build_tags(obs)
        assert tags == []


class TestSanitize:
    """Tests for _sanitize static method."""

    def test_alphanumeric_preserved(self) -> None:
        from src.application.services.export.obsidian_export_service import ObsidianExportService

        assert ObsidianExportService._sanitize("hello-world_123") == "hello-world_123"

    def test_spaces_replaced(self) -> None:
        from src.application.services.export.obsidian_export_service import ObsidianExportService

        assert ObsidianExportService._sanitize("hello world") == "hello_world"

    def test_special_chars_removed(self) -> None:
        from src.application.services.export.obsidian_export_service import ObsidianExportService

        assert ObsidianExportService._sanitize("bad@char!") == "bad_char_"

    def test_dot_segments_sanitized_to_underscore(self) -> None:
        from src.application.services.export.obsidian_export_service import ObsidianExportService

        assert ObsidianExportService._sanitize(".") == "_"
        assert ObsidianExportService._sanitize("..") == "_"

    def test_dot_in_filename_preserved(self) -> None:
        from src.application.services.export.obsidian_export_service import ObsidianExportService

        assert ObsidianExportService._sanitize("v1.0") == "v1.0"


class TestExport:
    """Integration tests for the full export flow."""

    def test_export_creates_files(self, tmp_path: Path, sample_obs: Observation) -> None:
        from src.application.services.export.obsidian_export_service import ObsidianExportService

        svc = ObsidianExportService()
        created = svc.export([sample_obs], tmp_path)

        assert len(created) == 1
        assert created[0].exists()
        content = created[0].read_text(encoding="utf-8")
        assert sample_obs.content in content

    def test_export_orphans(self, tmp_path: Path, orphan_obs: Observation) -> None:
        from src.application.services.export.obsidian_export_service import ObsidianExportService

        svc = ObsidianExportService()
        created = svc.export([orphan_obs], tmp_path)

        assert len(created) == 1
        assert "_orphans" in str(created[0])

    def test_export_multiple(self, tmp_path: Path, sample_obs: Observation, orphan_obs: Observation) -> None:
        from src.application.services.export.obsidian_export_service import ObsidianExportService

        svc = ObsidianExportService()
        created = svc.export([sample_obs, orphan_obs], tmp_path)

        assert len(created) == 2
        assert all(p.exists() for p in created)

    def test_export_empty_list(self, tmp_path: Path) -> None:
        from src.application.services.export.obsidian_export_service import ObsidianExportService

        svc = ObsidianExportService()
        created = svc.export([], tmp_path)
        assert created == []

    def test_export_creates_parent_dirs(self, tmp_path: Path) -> None:
        from src.application.services.export.obsidian_export_service import ObsidianExportService

        svc = ObsidianExportService()
        obs = Observation(
            id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            timestamp=1000,
            content="nested",
            topic_key="deep/nested/path",
        )
        created = svc.export([obs], tmp_path)
        assert created[0].parent.exists()
        assert created[0].exists()

    def test_export_deduplicates_same_path(self, tmp_path: Path) -> None:
        from src.application.services.export.obsidian_export_service import ObsidianExportService

        svc = ObsidianExportService()
        obs1 = Observation(
            id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            timestamp=1000,
            content="first",
            topic_key="same/path",
        )
        obs2 = Observation(
            id="11111111-2222-3333-4444-555555555555",
            timestamp=1000,
            content="second",
            topic_key="same/path",
        )
        created = svc.export([obs1, obs2], tmp_path)
        assert len(created) == 2
        assert created[0].stem == "path"
        assert "11111111" in created[1].stem

    def test_export_three_deduplicates(self, tmp_path: Path) -> None:
        from src.application.services.export.obsidian_export_service import ObsidianExportService

        svc = ObsidianExportService()
        obs = Observation(
            id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            timestamp=1000,
            content="c",
            topic_key="dup/key",
        )
        created = svc.export([obs, obs, obs], tmp_path)
        assert len(created) == 3
        # First: dup/key.md, second: dup/key_aaaaaaaa.md, third: dup/key_aaaaaaaa.md (same ID)
        assert created[0].name == "key.md"
        assert "aaaaaaaa" in created[1].name


class TestPathTraversal:
    """Security tests for path traversal prevention (G10)."""

    def test_double_dot_sanitized_no_traversal(self) -> None:
        from src.application.services.export.obsidian_export_service import ObsidianExportService

        svc = ObsidianExportService()
        obs = Observation(
            id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            timestamp=1000,
            content="traversal",
            topic_key="../../../etc/passwd",
        )
        path = svc._build_path(obs, Path("/output"))
        # .. is sanitized to _ by _sanitize(), resulting in /output/_/_/_/etc/passwd.md
        # Verify no .. in resolved path and stays within output
        assert ".." not in str(path)
        path.resolve().relative_to(Path("/output").resolve())

    def test_absolute_like_topic_stays_within(self) -> None:
        from src.application.services.export.obsidian_export_service import ObsidianExportService

        svc = ObsidianExportService()
        obs = Observation(
            id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            timestamp=1000,
            content="abs",
            topic_key="/etc/shadow",
        )
        path = svc._build_path(obs, Path("/output"))
        # The leading / gets sanitized to _, so path becomes /output/_etc/shadow.md
        assert str(path).startswith("/output/")


class TestEmptySegments:
    """Tests for empty topic_key segments (M1, M2)."""

    def test_empty_segments_filtered(self) -> None:
        from src.application.services.export.obsidian_export_service import ObsidianExportService

        svc = ObsidianExportService()
        obs = Observation(
            id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            timestamp=1000,
            content="empty",
            topic_key="a///b",
        )
        path = svc._build_path(obs, Path("/output"))
        assert path == Path("/output/a/b.md")

    def test_only_slashes_falls_to_root(self) -> None:
        from src.application.services.export.obsidian_export_service import ObsidianExportService

        svc = ObsidianExportService()
        obs = Observation(
            id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            timestamp=1000,
            content="slashes",
            topic_key="///",
        )
        path = svc._build_path(obs, Path("/output"))
        assert path == Path("/output/_root.md")

    def test_trailing_slash_no_empty_tag(self) -> None:
        from src.application.services.export.obsidian_export_service import ObsidianExportService

        svc = ObsidianExportService()
        obs = Observation(
            id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            timestamp=1000,
            content="trailing",
            topic_key="a/b/",
        )
        tags = svc._build_tags(obs)
        assert tags == ["a", "b"]
        assert "" not in tags
