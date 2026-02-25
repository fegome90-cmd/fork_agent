"""Servicios de aplicación."""

from src.application.services.terminal.platform_detector import PlatformDetector
from src.application.services.terminal.terminal_spawner import TerminalSpawner

__all__ = ["PlatformDetector", "TerminalSpawner"]
