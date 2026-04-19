"""Pytest fixtures para tests de API."""
import pytest
from fastapi.testclient import TestClient
import os

# Set env to use REAL database
os.environ["API_KEY"] = "559f4341b1277fe62ca2bab328370959c6f622e7d1dd1a10a80160f031ac7897"
os.environ["DATABASE_URL"] = "data/memory.db"
os.environ["TESTING"] = "1"

# Import and setup before creating app
from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
from src.infrastructure.persistence.repositories.promise_repository import PromiseContractRepository

# Create real repository instance
config = DatabaseConfig(db_path="data/memory.db")
db = DatabaseConnection(config=config)
promise_repo = PromiseContractRepository(connection=db)

# Inject via canonical container path
from src.infrastructure.persistence import container as _container
_container._container_cache.clear()

from src.interfaces.api.main import app
from src.interfaces.api.config import set_test_mode, clear_api_settings_cache

set_test_mode(True)
clear_api_settings_cache()

API_KEY = "559f4341b1277fe62ca2bab328370959c6f622e7d1dd1a10a80160f031ac7897"


@pytest.fixture
def client():
    """Client de test para la API."""
    return TestClient(app)


@pytest.fixture
def api_key():
    """API key para tests."""
    return API_KEY


@pytest.fixture
def auth_headers(api_key):
    """Headers de autenticación."""
    return {"X-API-Key": api_key}
