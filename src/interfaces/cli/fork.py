"""CLI para bifurcar terminals.

Este módulo proporciona una CLI para bifurcar sesiones de terminal
utilizando Dependency Injection para mejor testabilidad.
"""

import sys
from typing import Callable

from src.domain.entities.terminal import TerminalResult


# Tipo para la función de bifurcación
ForkTerminalFn = Callable[[str], TerminalResult]


def create_fork_cli(
    fork_terminal: ForkTerminalFn,
) -> Callable[[], int]:
    """Factory function para crear la CLI con dependencias inyectadas.
    
    Args:
        fork_terminal: Función que ejecuta el fork de terminal.
        
    Returns:
        Función main lista para ejecutar.
    """
    def main() -> int:
        """Punto de entrada principal de la CLI.
        
        Returns:
            Código de salida (0 para éxito, 1 para error).
        """
        if len(sys.argv) < 2:
            print("Uso: fork <comando>")
            return 1
        
        command = " ".join(sys.argv[1:])
        
        try:
            result = fork_terminal(command)
            print(result.output)
            return result.exit_code
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
    
    return main


def run_cli() -> int:
    """Ejecuta la CLI con las implementaciones por defecto.
    
    Returns:
        Código de salida.
    """
    from src.application.services.terminal.platform_detector import PlatformDetectorImpl
    from src.application.services.terminal.terminal_spawner import TerminalSpawnerImpl
    from src.application.use_cases.fork_terminal import fork_terminal_use_case
    
    # Dependency Injection manual
    platform_detector = PlatformDetectorImpl()
    terminal_spawner = TerminalSpawnerImpl()
    fork_terminal = fork_terminal_use_case(platform_detector, terminal_spawner)
    
    cli = create_fork_cli(fork_terminal)
    return cli()


if __name__ == "__main__":
    sys.exit(run_cli())
