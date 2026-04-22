"""Formatter for diff results — text (ANSI) and JSON output."""

from __future__ import annotations

import json
from typing import Any

from src.application.services.diff_service import DiffResult

# ANSI color codes
_GREEN = "\033[32m"
_RED = "\033[31m"
_YELLOW = "\033[33m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


class DiffFormatter:
    """Format DiffResult as colored text or structured JSON."""

    _CONTENT_PREVIEW_LENGTH = 80

    @staticmethod
    def format_text(result: DiffResult) -> str:
        """Format diff result as human-readable colored text.

        Uses ANSI colors: green for added, red for removed, yellow for modified.
        Includes a summary line at the end.
        """
        total = (
            result.summary.get("added", 0)
            + result.summary.get("modified", 0)
            + result.summary.get("removed", 0)
        )

        lines: list[str] = []
        lines.append(f"{_BOLD}Diff: {result.reference_label} -> {result.target_label}{_RESET}")

        if total == 0:
            lines.append("\nNo differences found")
            return "\n".join(lines)

        lines.append("")

        for entry in result.entries:
            preview = entry.content[: DiffFormatter._CONTENT_PREVIEW_LENGTH]
            if entry.status == "added":
                lines.append(f"  {_GREEN}[+] {_RESET}{entry.topic_key}")
                lines.append(f"      {preview}")
            elif entry.status == "removed":
                lines.append(f"  {_RED}[-] {_RESET}{entry.topic_key}")
                lines.append(f"      {preview}")
            elif entry.status == "modified":
                prev_preview = (entry.previous_content or "")[
                    : DiffFormatter._CONTENT_PREVIEW_LENGTH
                ]
                lines.append(f"  {_YELLOW}[~] {_RESET}{entry.topic_key}")
                lines.append(f"      {_RED}- {prev_preview}{_RESET}")
                lines.append(f"      {_GREEN}+ {preview}{_RESET}")
            lines.append("")

        # Summary line
        parts: list[str] = []
        added = result.summary.get("added", 0)
        removed = result.summary.get("removed", 0)
        modified = result.summary.get("modified", 0)
        if added:
            parts.append(f"{_GREEN}{added} added{_RESET}")
        if modified:
            parts.append(f"{_YELLOW}{modified} modified{_RESET}")
        if removed:
            parts.append(f"{_RED}{removed} removed{_RESET}")

        summary_line = ", ".join(parts)
        lines.append(f"{summary_line} ({total} total)")

        return "\n".join(lines)

    @staticmethod
    def format_json(result: DiffResult) -> str:
        """Format diff result as structured JSON.

        Produces valid JSON matching the spec:
        {
          "reference": {"label": "..."},
          "target": {"label": "..."},
          "summary": {"added": N, "removed": N, "modified": N},
          "diffs": [{"status": "...", "topic_key": "...", "content_preview": "..."}]
        }
        """
        diffs: list[dict[str, Any]] = []
        for entry in result.entries:
            item: dict[str, Any] = {
                "status": entry.status,
                "topic_key": entry.topic_key,
                "content_preview": entry.content[: DiffFormatter._CONTENT_PREVIEW_LENGTH],
            }
            if entry.previous_content is not None:
                item["previous_content"] = entry.previous_content[
                    : DiffFormatter._CONTENT_PREVIEW_LENGTH
                ]
            if entry.observation_id is not None:
                item["observation_id"] = entry.observation_id
            diffs.append(item)

        output: dict[str, Any] = {
            "reference": {"label": result.reference_label},
            "target": {"label": result.target_label},
            "summary": {
                "added": result.summary.get("added", 0),
                "removed": result.summary.get("removed", 0),
                "modified": result.summary.get("modified", 0),
            },
            "diffs": diffs,
        }

        return json.dumps(output, indent=2)
