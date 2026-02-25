"""Entidades relacionadas con workspace management."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class LayoutType(Enum):
    """Tipos de layout para worktrees."""

    NESTED = ".worktrees/<branch>/"
    OUTER_NESTED = "../<repo>.worktrees/<branch>/"
    SIBLING = "../<repo>-<branch>/"


class WorktreeState(Enum):
    """Estados posibles de un worktree."""

    ACTIVE = "active"
    MERGED = "merged"
    REMOVED = "removed"


@dataclass(frozen=True)
class Workspace:
    """Entidad inmutable que representa un workspace (worktree).

    Representa un directorio de trabajo git asociado a una rama,
    gestionado a través de git worktree.
    """

    name: str
    path: Path
    layout: LayoutType
    state: WorktreeState
    repo_root: Path
    last_setup_hook: HookResult | None = None
    last_teardown_hook: HookResult | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str):
            raise TypeError("name debe ser un string")
        if not isinstance(self.path, Path):
            raise TypeError("path debe ser un Path")
        if not isinstance(self.layout, LayoutType):
            raise TypeError("layout debe ser un LayoutType")
        if not isinstance(self.state, WorktreeState):
            raise TypeError("state debe ser un WorktreeState")
        if not isinstance(self.repo_root, Path):
            raise TypeError("repo_root debe ser un Path")
        if self.last_setup_hook is not None and not isinstance(self.last_setup_hook, HookResult):
            raise TypeError("last_setup_hook debe ser un HookResult o None")
        if self.last_teardown_hook is not None and not isinstance(
            self.last_teardown_hook, HookResult
        ):
            raise TypeError("last_teardown_hook debe ser un HookResult o None")


@dataclass(frozen=True)
class WorkspaceConfig:
    """Configuración para la gestión de workspaces.

    Entidad inmutable que contiene la configuración necesaria
    para operar con workspaces y worktrees.
    """

    default_layout: LayoutType
    auto_cleanup: bool
    hooks_dir: Path | None

    def __post_init__(self) -> None:
        if not isinstance(self.default_layout, LayoutType):
            raise TypeError("default_layout debe ser un LayoutType")
        if not isinstance(self.auto_cleanup, bool):
            raise TypeError("auto_cleanup debe ser un booleano")
        if self.hooks_dir is not None and not isinstance(self.hooks_dir, Path):
            raise TypeError("hooks_dir debe ser un Path o None")


@dataclass(frozen=True)
class HookResult:
    """Result of a hook execution.

    Immutable dataclass containing the result of executing a hook script.
    """

    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int

    def __post_init__(self) -> None:
        if not isinstance(self.success, bool):
            raise TypeError("success debe ser un booleano")
        if not isinstance(self.exit_code, int):
            raise TypeError("exit_code debe ser un entero")
        if not isinstance(self.stdout, str):
            raise TypeError("stdout debe ser un string")
        if not isinstance(self.stderr, str):
            raise TypeError("stderr debe ser un string")
        if not isinstance(self.duration_ms, int):
            raise TypeError("duration_ms debe ser un entero")


@dataclass(frozen=True)
class WorkspaceHook:
    """Configuración de hooks para un workspace.

    Entidad inmutable que define las rutas de scripts de setup
    y teardown, junto con variables de entorno opcionales.
    """

    workspace_id: str
    setup_path: Path | None = None
    teardown_path: Path | None = None
    environment: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.workspace_id, str):
            raise TypeError("workspace_id debe ser un string")
        if self.setup_path is not None and not isinstance(self.setup_path, Path):
            raise TypeError("setup_path debe ser un Path o None")
        if self.teardown_path is not None and not isinstance(self.teardown_path, Path):
            raise TypeError("teardown_path debe ser un Path o None")
        if not isinstance(self.environment, tuple):
            raise TypeError("environment debe ser una tupla")
        for item in self.environment:
            if not isinstance(item, tuple) or len(item) != 2:
                raise TypeError("environment debe ser tupla de tuplas (key, value)")
