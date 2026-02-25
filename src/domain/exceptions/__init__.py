"""Excepciones del dominio."""

from src.domain.exceptions.terminal import PlatformNotSupportedError, TerminalError

__all__ = ["TerminalError", "PlatformNotSupportedError"]
