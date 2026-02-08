"""Entidades relacionadas con terminal."""

from dataclasses import dataclass
from enum import Enum


class PlatformType(Enum):
    """Tipos de plataforma soportados."""

    DARWIN = "Darwin"
    WINDOWS = "Windows"
    LINUX = "Linux"


@dataclass(frozen=True)
class TerminalResult:
    """Resultado de una operación de terminal.

    Entidad inmutable que representa el resultado de ejecutar
    un comando en una terminal bifurcada.
    """

    success: bool
    output: str
    exit_code: int

    def __post_init__(self) -> None:
        """Valida el estado del resultado."""
        if not isinstance(self.success, bool):
            raise TypeError("success debe ser un booleano")
        if not isinstance(self.output, str):
            raise TypeError("output debe ser un string")
        if not isinstance(self.exit_code, int):
            raise TypeError("exit_code debe ser un entero")


@dataclass(frozen=True)
class TerminalConfig:
    """Configuración para la creación de una terminal.

    Entidad inmutable que contiene la configuración necesaria
    para abrir una nueva ventana de terminal.
    """

    terminal: str | None
    platform: PlatformType

    def __post_init__(self) -> None:
        """Valida la configuración."""
        if self.terminal is not None and not isinstance(self.terminal, str):
            raise TypeError("terminal debe ser un string o None")
        if not isinstance(self.platform, PlatformType):
            raise TypeError("platform debe ser un PlatformType")


@dataclass(frozen=True)
class TerminalInfo:
    """Información sobre el ejecutable de terminal encontrado."""

    name: str
    path: str | None
    is_available: bool

    def __post_init__(self) -> None:
        """Valida la información."""
        if not isinstance(self.name, str):
            raise TypeError("name debe ser un string")
        if self.path is not None and not isinstance(self.path, str):
            raise TypeError("path debe ser un string o None")
        if not isinstance(self.is_available, bool):
            raise TypeError("is_available debe ser un booleano")
