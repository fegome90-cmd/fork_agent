"""Servicio para detectar la plataforma del sistema."""

import platform
from abc import ABC, abstractmethod

from src.domain.entities.terminal import PlatformType


class PlatformDetector(ABC):
    """Interfaz abstracta para detectar la plataforma."""

    @abstractmethod
    def detect(self) -> PlatformType:
        """Detecta el sistema operativo actual.

        Returns:
            Tipo de plataforma detectada.
        """
        ...


class PlatformDetectorImpl(PlatformDetector):

    def detect(self) -> PlatformType:
        """Detecta el sistema operativo actual.

        Returns:
            Plataforma detectada.
        """
        system_name: str = platform.system()
        return PlatformType(system_name)
