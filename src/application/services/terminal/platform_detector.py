"""Servicio para detectar la plataforma del sistema."""

import platform
from abc import ABC, abstractmethod


class PlatformDetector(ABC):
    """Interfaz abstracta para detectar la plataforma."""

    @abstractmethod
    def detect(self) -> str:
        """Detecta el sistema operativo actual.

        Returns:
            Nombre del sistema operativo (Darwin, Windows, Linux).
        """
        ...


class PlatformDetectorImpl(PlatformDetector):
    """Implementación concreta de PlatformDetector."""

    def detect(self) -> str:
        """Detecta el sistema operativo actual.

        Returns:
            Nombre del sistema operativo.
        """
        system_name: str = platform.system()
        return system_name
