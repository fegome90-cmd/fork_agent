"""Configuración de la API."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class APISettings(BaseSettings):
    """Configuración de la API."""

    api_key: str = ""
    # SECURITY: Default to localhost. Set HOST=0.0.0.0 explicitly for public binding.
    host: str = "127.0.0.1"
    port: int = 8080
    debug: bool = False
    pm2_host: str = "localhost"
    pm2_port: int = 9615
    database_url: str = "./data/memory.db"
    rate_limit: int = 100
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:8080"]

    model_config = {"frozen": True}

    def validate_api_key(self) -> None:
        if not self.api_key:
            import warnings

            warnings.warn(
                "API_KEY not set. API will return 503 for authenticated endpoints. "
                "Set API_KEY environment variable.",
                UserWarning,
                stacklevel=2,
            )


# Flag to control caching behavior
_test_mode = False


@lru_cache
def _cached_api_settings() -> APISettings:
    """Internal cached version for production use."""
    return APISettings()


def get_api_settings() -> APISettings:
    """Get API settings. Always reads fresh env vars in test mode."""
    if _test_mode:
        # In test mode, always read fresh from environment
        settings = APISettings()
        settings.validate_api_key()
        return settings
    # In production, use cached version
    return _cached_api_settings()


def set_test_mode(enabled: bool = True) -> None:
    """Enable test mode to always read fresh env vars."""
    global _test_mode
    _test_mode = enabled


def clear_api_settings_cache() -> None:
    """Clear the API settings cache."""
    _cached_api_settings.cache_clear()
