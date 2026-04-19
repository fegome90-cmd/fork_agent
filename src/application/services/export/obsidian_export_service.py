"""Export observations to external formats (Obsidian, etc)."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import yaml

from src.domain.entities.observation import Observation


class ObsidianExportService:
    """Export observations as Obsidian-compatible markdown files."""

    def export(self, observations: list[Observation], output_dir: Path) -> list[Path]:
        """Export observations to output_dir. Returns list of created file paths."""
        output_dir.mkdir(parents=True, exist_ok=True)
        created: list[Path] = []
        seen_paths: dict[Path, int] = {}
        for obs in observations:
            path = self._build_path(obs, output_dir)
            if path in seen_paths:
                seen_paths[path] += 1
                path = path.with_stem(path.stem + f"_{obs.id[:8]}")
            else:
                seen_paths[path] = 0
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(self._render(obs), encoding="utf-8")
            created.append(path)
        return created

    def _build_path(self, obs: Observation, base: Path) -> Path:
        if obs.topic_key:
            parts = obs.topic_key.split("/")
            sanitized = [self._sanitize(p) for p in parts if p]
            if not sanitized:
                sanitized = ["_root"]
            path = base.joinpath(*sanitized).with_suffix(".md")
            # Security: verify path stays within output directory
            try:
                path.resolve().relative_to(base.resolve())
            except ValueError:
                return base / "_orphans" / f"{obs.id[:8]}.md"
            return path
        return base / "_orphans" / f"{obs.id[:8]}.md"

    def _render(self, obs: Observation) -> str:
        frontmatter = {
            "id": obs.id,
            "type": obs.type,
            "project": obs.project,
            "topic_key": obs.topic_key,
            "created": (
                datetime.fromtimestamp(obs.timestamp / 1000).isoformat() if obs.timestamp else None
            ),
            "revision_count": obs.revision_count,
            "tags": self._build_tags(obs),
        }
        fm = yaml.dump(
            {k: v for k, v in frontmatter.items() if v is not None},
            default_flow_style=False,
            allow_unicode=True,
        )
        title = obs.title or obs.topic_key or obs.id[:8]
        return f"---\n{fm}---\n# {title}\n\n{obs.content}\n"

    def _build_tags(self, obs: Observation) -> list[str]:
        tags: list[str] = []
        if obs.type:
            tags.append(obs.type)
        if obs.topic_key:
            tags.extend(p for p in obs.topic_key.split("/") if p)
        return tags

    @staticmethod
    def _sanitize(segment: str) -> str:
        sanitized = re.sub(r"[^\w\-.]", "_", segment)
        if sanitized in (".", ".."):
            sanitized = "_"
        return sanitized
