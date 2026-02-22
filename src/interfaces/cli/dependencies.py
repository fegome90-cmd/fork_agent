"""CLI dependencies for dependency injection."""

from __future__ import annotations

from pathlib import Path

from src.infrastructure.persistence.container import Container, create_container
from src.infrastructure.persistence.database import DatabaseConfig


def get_container(db_path: Path | None = None) -> Container:
    return create_container(db_path)


def get_repository(db_path: Path | None = None):
    container = get_container(db_path)
    return container.observation_repository()
