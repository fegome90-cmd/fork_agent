"""CLI para bifurcar terminals."""

import sys

from src.application.services.terminal.platform_detector import PlatformDetectorImpl
from src.application.services.terminal.terminal_spawner import TerminalSpawnerImpl
from src.application.use_cases.fork_terminal import fork_terminal_use_case


def main() -> None:
    """Punto de entrada principal."""
    if len(sys.argv) < 2:
        print("Uso: fork <comando>")
        sys.exit(1)

    command = " ".join(sys.argv[1:])

    # Crear dependencias
    platform_detector = PlatformDetectorImpl()
    terminal_spawner = TerminalSpawnerImpl()

    # Crear use case
    fork_terminal = fork_terminal_use_case(platform_detector, terminal_spawner)

    # Ejecutar
    result = fork_terminal(command)

    print(result.output)
    sys.exit(result.exit_code)


if __name__ == "__main__":
    main()
