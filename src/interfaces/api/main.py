"""Main entry point for fork_agent API."""

import logging
import signal
import sys
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.interfaces.api.config import get_api_settings
from src.interfaces.api.middleware.rate_limit import RateLimitMiddleware
from src.interfaces.api.routes import (
    agents,
    discovery,
    memory,
    processes,
    system,
    webhooks,
    workflow,
)

logger = logging.getLogger(__name__)

_shutdown_event = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _shutdown_event
    import asyncio

    _shutdown_event = asyncio.Event()

    def signal_handler(signum, _frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown")
        if _shutdown_event:
            _shutdown_event.set()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logger.info("Fork Agent API starting up")
    settings = get_api_settings()
    logging.basicConfig(
        level=logging.INFO if not settings.debug else logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    yield

    logger.info("Fork Agent API shutting down")


app = FastAPI(
    title="Fork Agent API",
    description="API REST para gestionar procesos fork_agent via PM2",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_api_settings()
cors_origins = settings.cors_origins if settings.cors_origins else ["http://localhost:3000"]

app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.rate_limit)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

app.include_router(processes.router, prefix="/api/v1")
app.include_router(agents.router, prefix="/api/v1")
app.include_router(workflow.router, prefix="/api/v1")
app.include_router(memory.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")
app.include_router(discovery.router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Fork Agent API", "version": "1.0.0", "docs": "/docs"}


def main() -> None:
    import uvicorn

    settings = get_api_settings()
    uvicorn.run(
        "src.interfaces.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
