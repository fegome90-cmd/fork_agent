"""Excepciones relacionadas con terminal."""


class TerminalError(Exception):
    """Excepción base para errores de terminal."""

    def __init__(
        self, message: str, details: dict | None = None
    ) -> None:
        """Inicializa el error de terminal.

        Args:
            message: Mensaje descriptivo del error.
            details: Información adicional sobre el error.
        """
        super().__init__(message)
        self.message = message
        self.details = details if details is not None else {}


class PlatformNotSupportedError(TerminalError):
    """Excepción cuando la plataforma no está soportada."""

    def __init__(self, platform: str) -> None:
        """Inicializa el error de plataforma no soportada.

        Args:
            platform: Nombre de la plataforma no soportada.
        """
        message = f"Plataforma '{platform}' no está soportada"
        super().__init__(message, {"platform": platform})


class TerminalNotFoundError(TerminalError):
    """Excepción cuando no se encuentra un emulador de terminal."""

    def __init__(self, platform: str, terminals_tried: list[str]) -> None:
        """Inicializa el error de terminal no encontrado.

        Args:
            platform: Nombre de la plataforma.
            terminals_tried: Lista de terminales intentados.
        """
        message = f"No se encontró emulador de terminal en {platform}"
        super().__init__(message, {
            "platform": platform,
            "terminals_tried": terminals_tried
        })


class CommandExecutionError(TerminalError):
    """Excepción cuando falla la ejecución de un comando."""

    def __init__(
        self, command: str, exit_code: int, output: str
    ) -> None:
        """Inicializa el error de ejecución de comando.

        Args:
            command: Comando que falló.
            exit_code: Código de salida del comando.
            output: Salida del comando.
        """
        message = f"Comando '{command}' falló con código {exit_code}"
        super().__init__(message, {
            "command": command,
            "exit_code": exit_code,
            "output": output
        })
