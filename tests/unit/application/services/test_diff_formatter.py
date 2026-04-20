"""Tests for DiffFormatter."""

from __future__ import annotations

import json

from src.application.services.diff_formatter import DiffFormatter
from src.application.services.diff_service import DiffEntry, DiffResult


def _make_entry(
    status: str = "added",
    topic_key: str = "test-topic",
    content: str = "test content",
    previous_content: str | None = None,
) -> DiffEntry:
    return DiffEntry(
        status=status,  # type: ignore[arg-type]
        topic_key=topic_key,
        content=content,
        previous_content=previous_content,
    )


def _make_result(
    ref: str = "ref",
    target: str = "target",
    entries: tuple[DiffEntry, ...] = (),
    summary: dict[str, int] | None = None,
) -> DiffResult:
    return DiffResult(
        reference_label=ref,
        target_label=target,
        entries=entries,
        summary=summary or {"added": 0, "removed": 0, "modified": 0, "unchanged": 0},
    )


class TestDiffFormatterFormatText:
    """Tests for DiffFormatter.format_text()."""

    def test_empty_diff(self) -> None:
        result = _make_result()
        output = DiffFormatter.format_text(result)
        assert "No differences found" in output

    def test_added_entry_shows_plus(self) -> None:
        entry = _make_entry(status="added", content="new content")
        result = _make_result(
            entries=(entry,), summary={"added": 1, "removed": 0, "modified": 0, "unchanged": 0}
        )
        output = DiffFormatter.format_text(result)
        assert "[+]" in output
        assert "added" in output.lower()

    def test_removed_entry_shows_minus(self) -> None:
        entry = _make_entry(status="removed", content="old content")
        result = _make_result(
            entries=(entry,), summary={"added": 0, "removed": 1, "modified": 0, "unchanged": 0}
        )
        output = DiffFormatter.format_text(result)
        assert "[-]" in output
        assert "removed" in output.lower()

    def test_modified_entry_shows_tilde(self) -> None:
        entry = _make_entry(status="modified", content="new", previous_content="old")
        result = _make_result(
            entries=(entry,), summary={"added": 0, "removed": 0, "modified": 1, "unchanged": 0}
        )
        output = DiffFormatter.format_text(result)
        assert "[~]" in output
        assert "modified" in output.lower()

    def test_summary_line(self) -> None:
        result = _make_result(
            entries=(
                _make_entry(status="added"),
                _make_entry(status="added"),
                _make_entry(status="removed"),
            ),
            summary={"added": 2, "removed": 1, "modified": 0, "unchanged": 0},
        )
        output = DiffFormatter.format_text(result)
        assert "2 added" in output
        assert "1 removed" in output

    def test_content_preview_truncated(self) -> None:
        long_content = "x" * 200
        entry = _make_entry(status="added", content=long_content)
        result = _make_result(
            entries=(entry,), summary={"added": 1, "removed": 0, "modified": 0, "unchanged": 0}
        )
        output = DiffFormatter.format_text(result)
        # Content should be truncated in preview
        assert len(output) < len(long_content) + 100

    def test_uses_ansi_colors(self) -> None:
        entry = _make_entry(status="added", content="colored")
        result = _make_result(
            entries=(entry,), summary={"added": 1, "removed": 0, "modified": 0, "unchanged": 0}
        )
        output = DiffFormatter.format_text(result)
        assert "\033[" in output  # ANSI escape sequence

    def test_reference_and_target_labels(self) -> None:
        result = _make_result(ref="session:abc", target="session:def")
        output = DiffFormatter.format_text(result)
        assert "session:abc" in output
        assert "session:def" in output


class TestDiffFormatterFormatJson:
    """Tests for DiffFormatter.format_json()."""

    def test_valid_json(self) -> None:
        result = _make_result()
        output = DiffFormatter.format_json(result)
        parsed = json.loads(output)
        assert "reference" in parsed
        assert "target" in parsed
        assert "summary" in parsed
        assert "diffs" in parsed

    def test_reference_and_target(self) -> None:
        result = _make_result(ref="id:o1", target="id:o2")
        output = DiffFormatter.format_json(result)
        parsed = json.loads(output)
        assert parsed["reference"]["label"] == "id:o1"
        assert parsed["target"]["label"] == "id:o2"

    def test_summary_counts(self) -> None:
        result = _make_result(
            summary={"added": 3, "removed": 1, "modified": 2, "unchanged": 5},
        )
        output = DiffFormatter.format_json(result)
        parsed = json.loads(output)
        assert parsed["summary"]["added"] == 3
        assert parsed["summary"]["removed"] == 1
        assert parsed["summary"]["modified"] == 2

    def test_diffs_entries(self) -> None:
        entry = _make_entry(status="added", topic_key="bugfix/auth", content="fix auth")
        result = _make_result(
            entries=(entry,),
            summary={"added": 1, "removed": 0, "modified": 0, "unchanged": 0},
        )
        output = DiffFormatter.format_json(result)
        parsed = json.loads(output)
        assert len(parsed["diffs"]) == 1
        assert parsed["diffs"][0]["status"] == "added"
        assert parsed["diffs"][0]["topic_key"] == "bugfix/auth"
        assert parsed["diffs"][0]["content_preview"] == "fix auth"

    def test_content_preview_truncated_to_80(self) -> None:
        long_content = "x" * 200
        entry = _make_entry(status="added", content=long_content)
        result = _make_result(
            entries=(entry,),
            summary={"added": 1, "removed": 0, "modified": 0, "unchanged": 0},
        )
        output = DiffFormatter.format_json(result)
        parsed = json.loads(output)
        assert len(parsed["diffs"][0]["content_preview"]) <= 80

    def test_modified_has_previous_content(self) -> None:
        entry = _make_entry(status="modified", content="new", previous_content="old")
        result = _make_result(
            entries=(entry,),
            summary={"added": 0, "removed": 0, "modified": 1, "unchanged": 0},
        )
        output = DiffFormatter.format_json(result)
        parsed = json.loads(output)
        assert parsed["diffs"][0]["previous_content"] == "old"

    def test_empty_diffs(self) -> None:
        result = _make_result()
        output = DiffFormatter.format_json(result)
        parsed = json.loads(output)
        assert parsed["diffs"] == []
        assert parsed["summary"]["added"] == 0
