"""Use case para bifurcar una terminal."""

from typing import Callable

from src.domain.entities.terminal import (
    TerminalConfig,
    TerminalResult,
    PlatformType,
)
from src.application.services.terminal.platform_detector import PlatformDetector
from src.application.services.terminal.terminal_spawner import TerminalSpawner


# Tipo para la función de detección de plataforma
DetectPlatformFn = Callable[[], str]

# Tipo para la función de spawn de terminal
SpawnTerminalFn = Callable[[str], TerminalResult]


def fork_terminal_use_case(
    platform_detector: PlatformDetector,
    terminal_spawner: TerminalSpawner,
) -> Callable[[str], TerminalResult]:
    """Crea un use case para bifurcar terminal.

    Este use case sigue los principios de Functional Programming:
    - Es una función pura que compone otras funciones
    - No tiene efectos secundarios
    - Retorna una función que ejecuta el caso de uso

    Args:
        platform_detector: Servicio para detectar la plataforma.
        terminal_spawner: Servicio para abrir terminales.

    Returns:
        Función que ejecuta el comando en una nueva terminal.
    """

    def execute(command: str) -> TerminalResult:
        """Ejecuta el comando en una nueva terminal.

        Args:
            command: Comando a ejecutar.

        Returns:
            Resultado de la ejecución.
        """
        platform_str = platform_detector.detect()
        platform = PlatformType(platform_str)
        config = TerminalConfig(terminal=None, platform=platform)
        return terminal_spawner.spawn(command, config)

    return execute


def create_fork_terminal_use_case(
    detect_platform: DetectPlatformFn,
    spawn_terminal: SpawnTerminalFn,
) -> Callable[[str], TerminalResult]:
    """Factory function para crear use case con funciones puras.

    Esta versión acepta funciones puras en lugar de servicios,
    facilitando el testing y la composición.

    Args:
        detect_platform: Función que detecta la plataforma.
        spawn_terminal: Función que abre una terminal.

    Returns:
        Use case listo para usar.
    """

    def execute(command: str) -> TerminalResult:
        """Ejecuta el comando en una nueva terminal."""
        platform_str = detect_platform()
        platform = PlatformType(platform_str)
        config = TerminalConfig(terminal=None, platform=platform)
        return spawn_terminal(command)

    return execute
