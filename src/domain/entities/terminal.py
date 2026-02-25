"""Entidades relacionadas con terminal."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


def _validate_type(
    value: Any,
    name: str,
    expected: type,
    type_name: str | None = None,
    allow_none: bool = False,
) -> None:
    if allow_none and value is None:
        return
    if not isinstance(value, expected):
        display_name = type_name or expected.__name__
        if allow_none:
            display_name = f"{display_name} o None"
        raise TypeError(f"{name} debe ser un {display_name}")


class PlatformType(Enum):
    """Tipos de plataforma soportados."""

    DARWIN = "Darwin"
    WINDOWS = "Windows"
    LINUX = "Linux"


@dataclass(frozen=True, slots=True)
class TerminalResult:
    """Resultado de una operación de terminal.

    Entidad inmutable que representa el resultado de ejecutar
    un comando en una terminal bifurcada.
    """

    success: bool
    output: str
    exit_code: int

    def __post_init__(self) -> None:
        _validate_type(self.success, "success", bool, "booleano")
        _validate_type(self.output, "output", str, "string")
        _validate_type(self.exit_code, "exit_code", int, "entero")


@dataclass(frozen=True, slots=True)
class TerminalConfig:
    """Configuración para la creación de una terminal."""

    terminal: str | None
    platform: PlatformType

    def __post_init__(self) -> None:
        _validate_type(self.terminal, "terminal", str, "string", allow_none=True)
        _validate_type(self.platform, "platform", PlatformType, "PlatformType")


@dataclass(frozen=True, slots=True)
class TerminalInfo:
    """Información sobre el ejecutable de terminal encontrado."""

    name: str
    path: str | None
    is_available: bool

    def __post_init__(self) -> None:
        _validate_type(self.name, "name", str, "string")
        _validate_type(self.path, "path", str, "string", allow_none=True)
        _validate_type(self.is_available, "is_available", bool, "booleano")
