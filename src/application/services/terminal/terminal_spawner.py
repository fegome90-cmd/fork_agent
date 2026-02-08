"""Servicio para abrir terminales."""

import shutil
from abc import ABC, abstractmethod

from src.domain.entities.terminal import TerminalConfig, TerminalResult
from src.domain.exceptions.terminal import TerminalNotFoundError


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
        """Abre terminal en macOS."""
        import subprocess

        result = subprocess.run(
            ["osascript", "-e", f'tell application "Terminal" to do script "{command}"'],
            capture_output=True,
            text=True,
        )
        return TerminalResult(
            success=result.returncode == 0,
            output=result.stdout.strip(),
            exit_code=result.returncode,
        )

    def _spawn_windows(self, command: str) -> TerminalResult:
        """Abre terminal en Windows."""
        import subprocess

        subprocess.Popen(["cmd", "/c", "start", "cmd", "/k", command], shell=True)
        return TerminalResult(
            success=True,
            output="New terminal window opened on Windows.",
            exit_code=0,
        )

    def _spawn_linux(self, command: str) -> TerminalResult:
        """Abre terminal en Linux."""
        import subprocess

        terminals = ["gnome-terminal", "x-terminal-emulator", "xterm", "konsole", "xfce4-terminal"]
        found_terminal = None

        for term in terminals:
            if shutil.which(term):
                found_terminal = term
                break

        if found_terminal:
            if found_terminal == "gnome-terminal":
                subprocess.Popen([found_terminal, "--", "bash", "-c", f"{command}; exec bash"])
            else:
                subprocess.Popen([found_terminal, "-e", f"bash -c '{command}; exec bash'"])

            return TerminalResult(
                success=True,
                output=f"New terminal window opened on Linux using {found_terminal}.",
                exit_code=0,
            )

        # Fallback to tmux
        if shutil.which("tmux"):
            import uuid

            session_name = f"fork_term_{str(uuid.uuid4())[:8]}"
            subprocess.run(
                ["tmux", "new-session", "-d", "-s", session_name, f"{command}; read -p 'Press enter to close...'"]
            )
            return TerminalResult(
                success=True,
                output=f"New terminal session opened in tmux (session: {session_name}).",
                exit_code=0,
            )

        raise TerminalNotFoundError("Linux", terminals)
