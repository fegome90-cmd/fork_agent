"""Rutas para agentes."""

import hashlib
import json
import logging
import re
import uuid
from datetime import datetime
from pathlib import Path
from threading import Lock, Semaphore

from fastapi import APIRouter, Depends, HTTPException, status

from src.infrastructure.agent_backends import get_backend, list_all_backends
from src.infrastructure.tmux_orchestrator import TmuxOrchestrator
from src.interfaces.api.dependencies import verify_api_key
from src.interfaces.api.models import (
    AgentSession,
    AgentSessionCreate,
    AgentSessionResponse,
    GcStatusResponse,
    SessionListResponse,
)

logger = logging.getLogger(__name__)


def _get_lifecycle_service():
    """Get the AgentLaunchLifecycleService (lazy, singleton)."""
    from src.infrastructure.persistence.container import get_lifecycle_service

    return get_lifecycle_service()


def _determine_status(tmux_error: str | None, agent_error: str | None) -> str:
    """Determine session status based on errors."""
    if tmux_error:
        return "tmux_failed"
    if agent_error:
        return "agent_failed"
    return "running"


router = APIRouter(prefix="/agents", tags=["agents"])


def _validate_session_id(session_id: str) -> bool:
    """BUG FIX: Validate session_id to prevent path traversal attacks.

    Only allows alphanumeric characters, hyphens, and underscores.
    """
    return bool(re.match(r"^[\w-]+$", session_id))


# Singleton for tmux orchestrator
_tmux_orchestrator: TmuxOrchestrator | None = None
_tmux_lock = Lock()


def get_tmux_orchestrator() -> TmuxOrchestrator:
    """Get or create TmuxOrchestrator instance (thread-safe)."""
    global _tmux_orchestrator
    if _tmux_orchestrator is not None:
        return _tmux_orchestrator

    with _tmux_lock:
        if _tmux_orchestrator is None:
            _tmux_orchestrator = TmuxOrchestrator(safety_mode=False)
        return _tmux_orchestrator


# Concurrency guard for agent sessions
_max_concurrent_sessions = 5
_session_semaphore = Semaphore(_max_concurrent_sessions)

# Thread-safe in-memory store for agent sessions
_sessions: dict[str, AgentSession] = {}
_sessions_lock = Lock()

# Persistence path
_sessions_dir = Path(".claude/api-sessions")


def _load_session_from_disk(session_id: str) -> AgentSession | None:
    """Load session from disk."""
    # BUG FIX: Validate session_id before constructing path
    if not _validate_session_id(session_id):
        logger.warning(f"Invalid session_id format rejected: {session_id}")
        return None

    session_file = _sessions_dir / f"{session_id}.json"
    if not session_file.exists():
        return None
    try:
        data = json.loads(session_file.read_text())
        return AgentSession(
            session_id=data["session_id"],
            agent_type=data["agent_type"],
            status=data.get("status", "unknown"),
            started_at=datetime.fromisoformat(data["started_at"]),
            tmux_session=data.get("tmux_session"),
            hooks=data.get("hooks", []),
        )
    except Exception as e:
        logger.warning(f"Failed to load session from disk for {session_id}: {e}")
        return None


def _save_session_to_disk(session: AgentSession) -> bool:
    """Persist session to disk.

    BUG FIX: Returns success status instead of silently failing.
    Returns True on success, False on failure.
    """
    # BUG FIX: Validate session_id before constructing path
    if not _validate_session_id(session.session_id):
        logger.error(f"Invalid session_id format: {session.session_id}")
        return False

    _sessions_dir.mkdir(parents=True, exist_ok=True)
    session_file = _sessions_dir / f"{session.session_id}.json"
    try:
        data = {
            "session_id": session.session_id,
            "agent_type": session.agent_type,
            "status": session.status,
            "started_at": session.started_at.isoformat(),
            "tmux_session": session.tmux_session,
            "hooks": session.hooks,
        }
        session_file.write_text(json.dumps(data, indent=2))
        logger.info(f"Persisted session to disk: {session.session_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to persist session {session.session_id}: {e}", exc_info=True)
        return False


def _delete_session_from_disk(session_id: str) -> bool:
    """Delete session from disk.

    BUG FIX: Returns success status instead of silently failing.
    """
    # BUG FIX: Validate session_id before constructing path
    if not _validate_session_id(session_id):
        logger.warning(f"Invalid session_id format rejected: {session_id}")
        return False

    session_file = _sessions_dir / f"{session_id}.json"
    if session_file.exists():
        try:
            session_file.unlink()
            logger.info(f"Deleted session from disk: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete session from disk: {e}", exc_info=True)
            return False
    return True  # File didn't exist, consider it success


class SessionStore:
    """Thread-safe session storage with disk persistence."""

    @staticmethod
    def get(session_id: str) -> AgentSession | None:
        with _sessions_lock:
            # First try memory
            session = _sessions.get(session_id)
            if session is not None:
                return session
            # Fall back to disk
            return _load_session_from_disk(session_id)

    @staticmethod
    def set(session_id: str, session: AgentSession) -> bool:
        """Store session. Returns True if persisted successfully."""
        with _sessions_lock:
            _sessions[session_id] = session
            # Persist to disk - BUG FIX: Track persistence status
            return _save_session_to_disk(session)

    @staticmethod
    def delete(session_id: str) -> AgentSession | None:
        with _sessions_lock:
            session = _sessions.pop(session_id, None)
            # Delete from disk - BUG FIX: Track deletion status
            _delete_session_from_disk(session_id)
            return session

    @staticmethod
    def list() -> list[AgentSession]:
        with _sessions_lock:
            return list(_sessions.values())

    @staticmethod
    def exists(session_id: str) -> bool:
        with _sessions_lock:
            return session_id in _sessions


def _restore_sessions_from_disk() -> int:
    """Load all persisted sessions from disk into SessionStore at startup.

    Called before any GC to ensure sessions persisted to disk are not
    incorrectly marked as orphans.

    Returns:
        Number of sessions restored.
    """
    if not _sessions_dir.exists():
        return 0
    count = 0
    for f in _sessions_dir.glob("*.json"):
        session_id = f.stem
        if SessionStore.exists(session_id):
            continue  # Already in memory
        session = _load_session_from_disk(session_id)
        if session:
            SessionStore.set(session_id, session)
            count += 1
    if count > 0:
        logger.info("gc: sessions restored from disk", extra={"count": count})
    return count


@router.get("/sessions/gc/status", response_model=GcStatusResponse)
async def get_gc_status(_: str = Depends(verify_api_key)) -> GcStatusResponse:
    """Get GC (garbage collector) status.

    Returns information about the last GC run, including counts of cleaned/failed sessions,
    timing, and current GC configuration.
    """
    from src.interfaces.api.main import GC_INTERVAL_SECONDS, GC_MIN_AGE_SECONDS, get_gc_state

    state = get_gc_state()

    if state.last_run_at is None:
        gc_status = "never_run"
    elif state.failed_count > 0 and state.cleaned_count == 0:
        gc_status = "all_failed"
    elif state.failed_count > 0:
        gc_status = "partial_failure"
    else:
        gc_status = "ok"

    return GcStatusResponse(
        last_run_at=state.last_run_at,
        cleaned_count=state.cleaned_count,
        failed_count=state.failed_count,
        last_duration_ms=state.last_duration_ms,
        gc_interval_seconds=GC_INTERVAL_SECONDS,
        gc_min_age_seconds=GC_MIN_AGE_SECONDS,
        status=gc_status,
    )


@router.post("/sessions", response_model=AgentSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: AgentSessionCreate,
    _: str = Depends(verify_api_key),
) -> AgentSessionResponse:
    """Crea una nueva sesión de agente (with concurrency guard and lifecycle dedup)."""
    # Check concurrency limit
    acquired = _session_semaphore.acquire(blocking=False)
    if not acquired:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Max concurrent sessions ({_max_concurrent_sessions}) reached. Try again later.",
        )

    tmux_session_name: str | None = None
    tmux_error: str | None = None
    agent_error: str | None = None

    try:
        logger.info(f"Creating agent session: agent_type={request.agent_type}")

        # Get the backend for the requested agent type
        backend = get_backend(request.agent_type)
        if backend is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown agent type: {request.agent_type}. "
                f"Available: {', '.join(list_all_backends())}",
            )

        # Check if backend is available
        if not backend.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Agent backend '{request.agent_type}' is not installed. "
                f"Please install {backend.display_name} to use this agent type.",
            )

        session_id = f"fork-{request.agent_type}-{uuid.uuid4().hex[:12]}"

        # Claim canonical launch slot via lifecycle service
        task_prefix = (
            hashlib.sha256(request.task.encode()).hexdigest()[:12]
            if request.task
            else "untitled"
        )
        canonical_key = f"api:{request.agent_type}:{task_prefix}"
        lifecycle_launch_id: str | None = None
        lifecycle = _get_lifecycle_service()
        attempt = lifecycle.request_launch(
            canonical_key=canonical_key,
            surface="api",
            owner_type="session",
            owner_id=session_id,
        )
        if attempt.decision == "suppressed":
            # Return existing session info instead of creating a duplicate
            logger.info(
                "API launch suppressed for task %s: %s",
                request.task[:50],
                attempt.reason or "already active",
            )
            existing = attempt.existing_launch
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "A session is already active for this task.",
                    "existing_launch_id": existing.launch_id if existing else None,
                    "existing_status": existing.status.value if existing else None,
                    "existing_tmux_session": existing.tmux_session if existing else None,
                },
            )
        if attempt.decision == "error":
            logger.error(
                "Lifecycle registry error for API session %s: %s",
                session_id,
                attempt.reason,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Launch registry unavailable: {attempt.reason}",
            )
        if attempt.launch is not None:
            lifecycle_launch_id = attempt.launch.launch_id

        # Notify lifecycle that spawn is starting
        if lifecycle_launch_id is not None:
            ok = lifecycle.confirm_spawning(lifecycle_launch_id)
            if not ok:
                logger.warning(
                    "CAS failed for launch %s during spawning — split-brain risk",
                    lifecycle_launch_id,
                )

        # Create tmux session if requested
        if request.tmux:
            try:
                tmux = get_tmux_orchestrator()
                # Create session with agent type as name prefix
                tmux_session_name = f"fork-{request.agent_type}-{uuid.uuid4().hex[:6]}"
                tmux.create_session(tmux_session_name)
                logger.info(f"Created tmux session: {tmux_session_name}")

                # Launch agent with task if provided
                if request.task:
                    success = tmux.launch_agent(
                        session=tmux_session_name,
                        window=0,
                        backend=backend,
                        task=request.task,
                        model=request.model,
                    )
                    if success:
                        logger.info(
                            f"Launched {backend.display_name} in tmux session: {tmux_session_name}"
                        )
                        # Confirm active in lifecycle registry
                        if lifecycle_launch_id is not None:
                            ok = lifecycle.confirm_active(
                                lifecycle_launch_id,
                                backend="tmux",
                                termination_handle_type="tmux-session",
                                termination_handle_value=tmux_session_name,
                                tmux_session=tmux_session_name,
                            )
                            if not ok:
                                logger.warning(
                                    "CAS failed for launch %s during confirm_active — split-brain risk",
                                    lifecycle_launch_id,
                                )
                    else:
                        agent_error = f"Failed to launch agent in {tmux_session_name}"
                        logger.warning(agent_error)
                        if lifecycle_launch_id is not None:
                            lifecycle.mark_failed(lifecycle_launch_id, agent_error)
            except Exception as e:
                logger.error(f"Failed to create tmux session: {e}", exc_info=True)
                # Expose error in response instead of silently failing
                tmux_error = str(e)
                tmux_session_name = None
                if lifecycle_launch_id is not None:
                    lifecycle.mark_failed(lifecycle_launch_id, f"tmux error: {e}")

        # Track hooks if requested
        hooks = []
        if request.hooks:
            hooks = [
                {"type": "workspace-init", "status": "pending"},
                {"type": "tmux-session-per-agent", "status": "pending"},
            ]

        session = AgentSession(
            session_id=session_id,
            agent_type=request.agent_type,
            status=_determine_status(tmux_error, agent_error),
            started_at=datetime.now(),
            tmux_session=tmux_session_name,
            hooks=hooks,
        )

        SessionStore.set(session_id, session)
        logger.info(f"Agent session created: session_id={session_id}")

        # Include errors in response if present
        if tmux_error:
            logger.warning(f"Session {session_id} created with tmux error: {tmux_error}")
        if agent_error:
            logger.warning(f"Session {session_id} created with agent error: {agent_error}")

        return AgentSessionResponse(data=session)

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.exception(f"Failed to create agent session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {e}",
        ) from e
    finally:
        if acquired:
            _session_semaphore.release()


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    _: str = Depends(verify_api_key),
) -> SessionListResponse:
    """Lista todas las sesiones de agentes."""
    logger.info("Listing agent sessions")
    sessions = SessionStore.list()
    return SessionListResponse(data=sessions)


@router.get("/sessions/{session_id}", response_model=AgentSessionResponse)
async def get_session(
    session_id: str,
    _: str = Depends(verify_api_key),
) -> AgentSessionResponse:
    """Obtiene una sesión por ID."""
    logger.info(f"Getting session: session_id={session_id}")

    session = SessionStore.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return AgentSessionResponse(data=session)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    _: str = Depends(verify_api_key),
) -> None:
    """Elimina una sesión de agente."""
    logger.info(f"Delete session requested: session_id={session_id}")

    session = SessionStore.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Clean up tmux session if exists
    if session.tmux_session:
        try:
            tmux = get_tmux_orchestrator()
            tmux.kill_session(session.tmux_session)
            logger.info(f"Killed tmux session: {session.tmux_session}")
        except Exception as e:
            # Log at ERROR level - don't silently continue
            logger.error(f"Failed to kill tmux session {session.tmux_session}: {e}", exc_info=True)

    # Terminate lifecycle record if lifecycle service is available
    try:
        lifecycle = _get_lifecycle_service()
        active = lifecycle.get_active_launch(f"api:{session_id}")
        if active is not None:
            lifecycle.begin_termination(active.launch_id)
            lifecycle.confirm_terminated(active.launch_id)
    except Exception as e:
        logger.error("Lifecycle termination failed for session %s: %s", session_id, e)

    # Remove from store
    SessionStore.delete(session_id)
    logger.info(f"Session deleted: session_id={session_id}")


@router.get("/launches/status")
async def get_launch_status(
    _: str = Depends(verify_api_key),
) -> dict:
    """Get launch registry status summary for operator triage.

    Returns counts by status, active launches, and quarantined launches
    so operators can distinguish started/suppressed/quarantined/failed decisions.
    """
    try:
        lifecycle = _get_lifecycle_service()
        summary = lifecycle.get_status_summary()
        active = lifecycle.list_active_launches()
        quarantined = lifecycle.list_quarantined_launches()

        return {
            "counts_by_status": summary,
            "active_launches": [
                {
                    "launch_id": l.launch_id,
                    "canonical_key": l.canonical_key,
                    "surface": l.surface,
                    "owner_type": l.owner_type,
                    "owner_id": l.owner_id,
                    "status": l.status.value,
                    "backend": l.backend,
                    "tmux_session": l.tmux_session,
                    "created_at": l.created_at,
                    "lease_expires_at": l.lease_expires_at,
                }
                for l in active
            ],
            "quarantined_launches": [
                {
                    "launch_id": l.launch_id,
                    "canonical_key": l.canonical_key,
                    "surface": l.surface,
                    "quarantine_reason": l.quarantine_reason,
                    "created_at": l.created_at,
                }
                for l in quarantined
            ],
        }
    except Exception as e:
        logger.error("Failed to get launch status: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Launch registry unavailable: {e}",
        ) from e
