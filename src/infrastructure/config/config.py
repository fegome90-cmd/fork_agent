"""Configuración del proyecto."""

from pathlib import Path
from typing import Any

from dotenv import load_dotenv


class ConfigError(Exception):
    """Error de configuración."""

    pass


class ConfigLoader:
    """Carga y valida configuración del proyecto."""

    def __init__(self, env_path: Path | None = None) -> None:
        """Inicializa el loader de configuración.

        Args:
            env_path: Ruta al archivo .env. Si es None, usa .env en la raíz.
        """
        self._env_path = env_path or Path(__file__).parent.parent.parent / ".env"
        self._config: dict[str, Any] = {}

    def load(self) -> dict[str, Any]:
        """Carga variables de entorno desde el archivo .env.

        Returns:
            Diccionario con la configuración cargada.

        Raises:
            ConfigError: Si hay errores al cargar la configuración.
        """
        if self._env_path.exists():
            load_dotenv(self._env_path)

        self._config = {
            "fork_agent_debug": self._get_bool("FORK_AGENT_DEBUG", False),
            "fork_agent_shell": self._get_str("FORK_AGENT_SHELL", "bash"),
            "fork_agent_default_terminal": self._get_str("FORK_AGENT_DEFAULT_TERMINAL", ""),
        }

        return self._config

    def _get_str(self, key: str, default: str) -> str:
        """Obtiene un valor de entorno como string.

        Args:
            key: Nombre de la variable de entorno.
            default: Valor por defecto si no existe.

        Returns:
            El valor de la variable o el valor por defecto.
        """
        import os

        return os.environ.get(key, default)

    def _get_bool(self, key: str, default: bool) -> bool:
        """Obtiene un valor de entorno como booleano.

        Args:
            key: Nombre de la variable de entorno.
            default: Valor por defecto si no existe.

        Returns:
            True si el valor es "true" (case insensitive), False en caso contrario.
        """
        import os

        value = os.environ.get(key, str(default))
        return value.lower() == "true"

    def get(self, key: str, default: Any = None) -> Any:
        """Obtiene un valor de la configuración.

        Args:
            key: Clave a obtener.
            default: Valor por defecto si no existe.

        Returns:
            El valor configurado o el valor por defecto.
        """
        return self._config.get(key, default)

    def get_required(self, key: str) -> Any:
        """Obtiene un valor requerido de la configuración.

        Args:
            key: Clave a obtener.

        Returns:
            El valor configurado.

        Raises:
            ConfigError: Si la clave no existe en la configuración.
        """
        if key not in self._config:
            raise ConfigError(f"Configuración requerida '{key}' no encontrada")
        return self._config[key]


# Instancia global para uso común
_config_loader: ConfigLoader | None = None


def get_config() -> ConfigLoader:
    """Obtiene la instancia global del ConfigLoader.

    Returns:
        Instancia configurada del ConfigLoader.
    """
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
        _config_loader.load()
    return _config_loader


def reload_config(env_path: Path | None = None) -> ConfigLoader:
    """Recarga la configuración desde un nuevo archivo.

    Args:
        env_path: Ruta opcional al nuevo archivo .env.

    Returns:
        Nueva instancia del ConfigLoader.
    """
    global _config_loader
    _config_loader = ConfigLoader(env_path)
    _config_loader.load()
    return _config_loader
