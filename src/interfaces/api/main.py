"""Main entry point for fork_agent API."""

import asyncio
import logging
import os
import signal
import sys
import time
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Lock

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.interfaces.api.config import get_api_settings
from src.interfaces.api.middleware.rate_limit import RateLimitMiddleware
from src.interfaces.api.routes import (
    agents,
    discovery,
    integrations,
    memory,
    processes,
    system,
    webhooks,
    workflow,
)

logger = logging.getLogger(__name__)

# GC configuration
GC_INTERVAL_SECONDS = int(os.getenv("GC_INTERVAL_SECONDS", "60"))
GC_MIN_AGE_SECONDS = int(os.getenv("GC_MIN_AGE_SECONDS", "300"))


@dataclass
class _GcState:
    """Mutable state for GC status tracking."""
    last_run_at: datetime | None = None
    cleaned_count: int = 0
    failed_count: int = 0
    last_duration_ms: int = 0


_gc_state = _GcState()
_gc_state_lock = Lock()


def _update_gc_state(cleaned: int, failed: int, duration_ms: int) -> None:
    """Update GC state atomically."""
    with _gc_state_lock:
        _gc_state.last_run_at = datetime.now()
        _gc_state.cleaned_count = cleaned
        _gc_state.failed_count = failed
        _gc_state.last_duration_ms = duration_ms


def get_gc_state() -> _GcState:
    """Get current GC state (thread-safe copy)."""
    with _gc_state_lock:
        return _GcState(
            last_run_at=_gc_state.last_run_at,
            cleaned_count=_gc_state.cleaned_count,
            failed_count=_gc_state.failed_count,
            last_duration_ms=_gc_state.last_duration_ms,
        )


def _run_gc(min_age_seconds: int = GC_MIN_AGE_SECONDS) -> tuple[int, int]:
    """Run a single GC cycle.

    Args:
        min_age_seconds: Only clean sessions older than this.

    Returns:
        Tuple of (cleaned_count, failed_count)
    """
    from src.application.services.agent.agent_manager import get_agent_manager

    t0 = time.monotonic()
    manager = get_agent_manager()
    result = manager.cleanup_orphans(dry_run=False, min_age_seconds=min_age_seconds)
    duration_ms = int((time.monotonic() - t0) * 1000)

    _update_gc_state(
        cleaned=len(result.cleaned_sessions),
        failed=len(result.failed_sessions),
        duration_ms=duration_ms,
    )

    if result.cleaned_sessions:
        logger.warning(
            "gc: zombie sessions cleaned",
            extra={
                "count": len(result.cleaned_sessions),
                "sessions": result.cleaned_sessions,
                "duration_ms": duration_ms,
            },
        )
    if result.failed_sessions:
        logger.error(
            "gc: failed to clean sessions",
            extra={
                "count": len(result.failed_sessions),
                "sessions": result.failed_sessions,
                "duration_ms": duration_ms,
            },
        )
    return len(result.cleaned_sessions), len(result.failed_sessions)


async def _gc_loop() -> None:
    """Background task that periodically runs GC."""
    while True:
        await asyncio.sleep(GC_INTERVAL_SECONDS)
        try:
            _run_gc(min_age_seconds=GC_MIN_AGE_SECONDS)
        except Exception:
            logger.exception("gc: error in gc loop")

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

    # 1. Restore persisted sessions from disk before any GC
    from src.interfaces.api.routes.agents import _restore_sessions_from_disk
    restored = _restore_sessions_from_disk()
    if restored > 0:
        logger.info("gc: startup restore complete", extra={"restored_count": restored})

    # 2. Startup sweep: clean historical zombie accumulation (no min_age)
    try:
        cleaned, failed = _run_gc(min_age_seconds=0)
        logger.info(
            "gc: startup sweep complete",
            extra={"cleaned": cleaned, "failed": failed},
        )
    except Exception:
        logger.exception("gc: error during startup sweep")

    # 3. Start periodic GC loop
    gc_task = asyncio.create_task(_gc_loop())

    yield  # API serving requests

    # Shutdown: cancel GC loop
    gc_task.cancel()
    with suppress(asyncio.CancelledError):
        await gc_task

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
    allow_headers=["Content-Type", "X-API-Key", "Authorization"],
)

app.include_router(processes.router, prefix="/api/v1")
app.include_router(agents.router, prefix="/api/v1")
app.include_router(workflow.router, prefix="/api/v1")
app.include_router(memory.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")
app.include_router(discovery.router, prefix="/api/v1")
app.include_router(integrations.router, prefix="/api/v1")


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
