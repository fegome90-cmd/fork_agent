"""Configuración de la API."""

from pydantic_settings import BaseSettings


class APISettings(BaseSettings):
    """Configuración de la API."""

    api_key: str = ""
    host: str = "0.0.0.0"
    port: int = 8080
    debug: bool = False
    pm2_host: str = "localhost"
    pm2_port: int = 9615
    database_url: str = "./data/memory.db"
    rate_limit: int = 100
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:8080"]

    model_config = {"frozen": True, "env_prefix": "API_"}

    def validate_api_key(self) -> None:
        if not self.api_key:
            import warnings

            warnings.warn(
                "API_KEY not set. API will return 503 for authenticated endpoints. "
                "Set API_KEY environment variable.",
                UserWarning,
                stacklevel=2,
            )


api_settings = APISettings()
api_settings.validate_api_key()
