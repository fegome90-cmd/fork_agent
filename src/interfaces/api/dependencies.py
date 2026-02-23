"""Dependencies para la API."""

from fastapi import Header, HTTPException, status


async def verify_api_key(x_api_key: str = Header(...)) -> str:
    """Verifica la API key."""
    from src.interfaces.api.config import api_settings

    if not api_settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API key not configured",
        )

    if x_api_key != api_settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return x_api_key
