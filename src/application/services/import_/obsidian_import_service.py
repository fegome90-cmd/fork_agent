"""Import observations from external formats (Obsidian, etc)."""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ImportResult:
    """Immutable result of an import operation."""

    total_files: int
    imported: int
    skipped: int
    errors: list[str] = field(default_factory=list)
    imported_ids: list[str] = field(default_factory=list)


class ObsidianImportService:
    """Import Obsidian-compatible markdown files as observations."""

    def __init__(self) -> None:
        self._yaml_pattern = re.compile(
            r"^---\s*\n(.*?)\n---\s*\n?(.*)",
            re.DOTALL,
        )
        self._h1_pattern = re.compile(r"^#\s+.+\n\n?", re.MULTILINE)

    def import_from_dir(
        self,
        input_dir: Path,
        memory_save_fn: Callable[..., str],
        existing_ids: set[str] | None = None,
        dry_run: bool = False,
        project_override: str | None = None,
        skip_duplicates: bool = False,
    ) -> ImportResult:
        """Import all .md files from input_dir tree.

        Args:
            input_dir: Root directory containing exported .md files.
            memory_save_fn: Callable matching MemoryService.save() signature.
                Must accept (content, **kwargs) and return observation ID.
            existing_ids: Set of observation IDs already in DB (for duplicate check).
            dry_run: Preview mode — no writes.
            project_override: Override project for all imported observations.
            skip_duplicates: Skip files whose id already exists in DB.

        Returns:
            ImportResult with counts and details.
        """
        if existing_ids is None:
            existing_ids = set()

        input_dir = input_dir.resolve()
        if not input_dir.is_dir():
            return ImportResult(total_files=0, imported=0, skipped=0)

        md_files = sorted(input_dir.rglob("*.md"))

        imported_ids: list[str] = []
        skipped = 0
        errors: list[str] = []

        for md_path in md_files:
            # Path traversal protection: resolved path must be within input_dir
            try:
                md_path.resolve().relative_to(input_dir)
            except ValueError:
                errors.append(f"Path traversal blocked: {md_path}")
                continue

            # Skip non-regular files (symlinks, etc.)
            if not md_path.is_file():
                continue

            # Skip binary files
            if self._is_binary(md_path):
                continue

            # Parse the file
            parsed = self._parse_file(md_path)
            if parsed is None:
                errors.append(f"No frontmatter: {md_path.name}")
                continue

            frontmatter, body = parsed

            # Validate and extract ID
            obs_id = frontmatter.get("id", "")
            if not obs_id or not self._is_valid_id(obs_id):
                obs_id = str(uuid.uuid4())

            # Skip duplicates
            if skip_duplicates and obs_id in existing_ids:
                skipped += 1
                continue

            # Derive topic_key from path if missing
            topic_key = frontmatter.get("topic_key")
            if not topic_key:
                rel = md_path.relative_to(input_dir)
                topic_key = str(rel.with_suffix(""))

            # Extract content from body (strip H1 title if present)
            content = self._strip_h1_title(body).strip()
            if not content:
                errors.append(f"Empty content: {md_path.name}")
                continue

            # Extract title from first H1
            title = self._extract_h1_title(body)

            # Extract type
            obs_type = frontmatter.get("type")
            if not obs_type:
                obs_type = None

            # Determine project
            project = project_override or frontmatter.get("project")

            # Build metadata from tags
            metadata: dict[str, Any] = {}
            tags = frontmatter.get("tags")
            if isinstance(tags, list):
                metadata["tags"] = tags
            revision_count = frontmatter.get("revision_count", 1)
            if isinstance(revision_count, int) and revision_count > 0:
                metadata["revision_count"] = revision_count

            # Dry run: don't write
            if dry_run:
                continue

            # Save via the provided save function
            try:
                new_id = memory_save_fn(
                    content=content,
                    title=title,
                    topic_key=topic_key,
                    project=project,
                    type=obs_type,
                    metadata=metadata if metadata else None,
                )
                imported_ids.append(new_id)
            except Exception as exc:
                errors.append(f"Save failed {md_path.name}: {exc}")

        total_files = len([f for f in md_files if f.is_file() and not self._is_binary(f)])
        return ImportResult(
            total_files=total_files,
            imported=len(imported_ids),
            skipped=skipped,
            errors=errors,
            imported_ids=imported_ids,
        )

    def _parse_file(self, path: Path) -> tuple[dict[str, Any], str] | None:
        """Parse a markdown file into (frontmatter_dict, body_text).

        Returns None if no valid frontmatter found.
        """
        try:
            raw = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            return None

        match = self._yaml_pattern.match(raw)
        if not match:
            return None

        try:
            frontmatter = yaml.safe_load(match.group(1))
        except yaml.YAMLError:
            return None

        if not isinstance(frontmatter, dict):
            return None

        body = match.group(2)
        return frontmatter, body

    @staticmethod
    def _is_valid_id(obs_id: str) -> bool:
        """Check if ID looks like a valid UUID."""
        try:
            uuid.UUID(obs_id)
            return True
        except (ValueError, AttributeError):
            return False

    @staticmethod
    def _parse_timestamp(created: Any) -> int:
        """Parse ISO datetime string to Unix timestamp in ms."""
        if not created:
            return 0
        if isinstance(created, (int, float)):
            return int(created * 1000) if created < 1e12 else int(created)
        if isinstance(created, str):
            try:
                dt = datetime.fromisoformat(created)
                return int(dt.timestamp() * 1000)
            except (ValueError, TypeError):
                return 0
        return 0

    def _strip_h1_title(self, body: str) -> str:
        """Remove leading '# Title\\n\\n' from body if present."""
        return self._h1_pattern.sub("", body, count=1)

    @staticmethod
    def _extract_h1_title(body: str) -> str | None:
        """Extract the first H1 title from body."""
        for line in body.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
        return None

    @staticmethod
    def _is_binary(path: Path) -> bool:
        """Heuristic: check if file appears to be binary."""
        try:
            chunk = path.read_bytes()[:512]
            return b"\x00" in chunk
        except OSError:
            return True
