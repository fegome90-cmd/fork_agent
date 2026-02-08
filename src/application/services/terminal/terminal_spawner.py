"""Servicio para abrir terminales."""

import shutil
import subprocess
import uuid
from abc import ABC, abstractmethod
from typing import Final

from src.domain.entities.terminal import TerminalConfig, TerminalResult
from src.domain.exceptions.terminal import TerminalNotFoundError


# Terminales soportados en Linux
LINUX_TERMINALS: Final[list[str]] = [
    "gnome-terminal",
    "x-terminal-emulator", 
    "xterm",
    "konsole",
    "xfce4-terminal",
]


class TerminalSpawner(ABC):
    """Interfaz abstracta para abrir terminales."""

    @abstractmethod
    def spawn(self, command: str, config: TerminalConfig) -> TerminalResult:
        """Abre una terminal y ejecuta un comando.

        Args:
            command: Comando a ejecutar.
            config: Configuración de la terminal.

        Returns:
            Resultado de la ejecución.
        """
        ...


class TerminalSpawnerImpl(TerminalSpawner):
    """Implementación de TerminalSpawner."""

    def spawn(self, command: str, config: TerminalConfig) -> TerminalResult:
        """Abre una terminal y ejecuta un comando.

        Args:
            command: Comando a ejecutar.
            config: Configuración de la terminal.

        Returns:
            Resultado de la ejecución.
        """
        platform = config.platform.value

        if platform == "Darwin":
            return self._spawn_macos(command)
        elif platform == "Windows":
            return self._spawn_windows(command)
        elif platform == "Linux":
            return self._spawn_linux(command)
        else:
            raise TerminalNotFoundError(platform, [])

    def _spawn_macos(self, command: str) -> TerminalResult:
        """Abre terminal en macOS.

        Args:
            command: Comando a ejecutar.

        Returns:
            Resultado de la ejecución.
        """
        # Escapar comillas en el comando para prevenir inyección
        escaped_command = command.replace('"', '\\"')
        
        result = subprocess.run(
            ["osascript", "-e", f'tell application "Terminal" to do script "{escaped_command}"'],
            capture_output=True,
            text=True,
        )
        return TerminalResult(
            success=result.returncode == 0,
            output=result.stdout.strip(),
            exit_code=result.returncode,
        )

    def _spawn_windows(self, command: str) -> TerminalResult:
        """Abre terminal en Windows.

        Args:
            command: Comando a ejecutar.

        Returns:
            Resultado de la ejecución.
        """
        # Sanitizar comando para Windows antes de ejecutar
        # La sanitización básica es necesaria porque 'start' de cmd requiere shell=True
        sanitized_command = self._sanitize_windows_command(command)
        
        # Usar shell=True pero con comando sanitizado
        # En Windows, 'start' requiere shell=True para funcionar correctamente
        subprocess.Popen(
            ["cmd", "/c", "start", "cmd", "/k", sanitized_command],
        )
        return TerminalResult(
            success=True,
            output="New terminal window opened on Windows.",
            exit_code=0,
        )

    def _sanitize_windows_command(self, command: str) -> str:
        """Sanitiza comando para Windows.
        
        Args:
            command: Comando original.
            
        Returns:
            Comando sanitizado.
        """
        # Remover caracteres que podrían causar inyección
        dangerous_chars = ["&", "|", ";", "`", "$", "(", ")", "{", "}", "<", ">"]
        sanitized = command
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, "")
        return sanitized.strip()

    def _spawn_linux(self, command: str) -> TerminalResult:
        """Abre terminal en Linux.

        Args:
            command: Comando a ejecutar.

        Returns:
            Resultado de la ejecución.
        """
        found_terminal: str | None = None

        for term in LINUX_TERMINALS:
            if shutil.which(term):
                found_terminal = term
                break

        if found_terminal:
            return self._spawn_with_terminal(found_terminal, command)

        # Fallback to tmux
        if shutil.which("tmux"):
            return self._spawn_with_tmux(command)

        raise TerminalNotFoundError("Linux", LINUX_TERMINALS)

    def _spawn_with_terminal(self, terminal: str, command: str) -> TerminalResult:
        """Abre terminal específica en Linux.

        Args:
            terminal: Nombre del terminal.
            command: Comando a ejecutar.

        Returns:
            Resultado de la ejecución.
        """
        # Sanitizar comando para Linux
        sanitized_command = command.replace("'", "'\\''")
        
        if terminal == "gnome-terminal":
            subprocess.Popen(
                [terminal, "--", "bash", "-c", f"{sanitized_command}; exec bash"]
            )
        else:
            subprocess.Popen(
                [terminal, "-e", f"bash -c '{sanitized_command}; exec bash'"]
            )

        return TerminalResult(
            success=True,
            output=f"New terminal window opened on Linux using {terminal}.",
            exit_code=0,
        )

    def _spawn_with_tmux(self, command: str) -> TerminalResult:
        """Abre sesión de tmux en Linux.

        Args:
            command: Comando a ejecutar.

        Returns:
            Resultado de la ejecución.
        """
        # Sanitizar comando para tmux
        sanitized_command = command.replace("'", "'\\''")
        session_name = f"fork_term_{str(uuid.uuid4())[:8]}"
        
        subprocess.run(
            ["tmux", "new-session", "-d", "-s", session_name, f"{sanitized_command}; read -p 'Press enter to close...'"]
        )
        return TerminalResult(
            success=True,
            output=f"New terminal session opened in tmux (session: {session_name}).",
            exit_code=0,
        )
