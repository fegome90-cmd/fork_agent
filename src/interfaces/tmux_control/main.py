"""tmux-control sidecar API.

Secure tmux control via UDS with API key auth and command allowlist.
"""

from __future__ import annotations

import hmac
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration
SOCKET_PATH = os.environ.get("TMUX_CONTROL_SOCKET", "/var/run/fork-agent/tmux.sock")
API_KEY = os.environ.get("TMUX_CONTROL_API_KEY", "")
COMMAND_TIMEOUT = 30  # seconds

# Command allowlist (whitelist)
ALLOWED_COMMANDS = {
    "send-keys",
    "capture-pane",
    "new-session",
    "kill-session",
    "list-sessions",
    "list-panes",
    "new-window",
    "kill-window",
    "select-window",
    "split-window",
    "resize-pane",
    "has-session",
    "display-message",
}


app = FastAPI(title="tmux-control", version="1.0.0")


# Models
class CreateSessionRequest(BaseModel):
    session_name: str
    command: str | None = None
    detached: bool = False


class SendKeysRequest(BaseModel):
    session_name: str
    pane: str = "."  # default to active pane
    keys: str


class SendKeysResponse(BaseModel):
    success: bool
    output: str = ""


class CapturePaneRequest(BaseModel):
    session_name: str
    pane: str = "."
    capture_all: bool = False


class SessionInfo(BaseModel):
    name: str
    windows: int = 0
    panes: int = 0


class ErrorResponse(BaseModel):
    detail: str


def verify_api_key(x_api_key: str = Header(...)) -> str:
    """Verify API key."""
    if not API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API key not configured",
        )

    if not hmac.compare_digest(x_api_key, API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return x_api_key


def run_tmux(args: list[str], timeout: int = COMMAND_TIMEOUT) -> tuple[int, str, str]:
    """Run tmux command with timeout and shell=False."""
    cmd = ["tmux"] + args

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,  # SECURITY: Never use shell=True
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=504,
            detail=f"Command timed out after {timeout}s",
        ) from None
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="tmux not found",
        ) from None
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Command failed: {e}",
        ) from None


def validate_command(command: str) -> str:
    """Validate command is in allowlist."""
    # Extract the tmux subcommand (first argument after "tmux")
    parts = command.split()
    if not parts:
        raise HTTPException(status_code=400, detail="Empty command")

    subcommand = parts[0]

    if subcommand not in ALLOWED_COMMANDS:
        raise HTTPException(
            status_code=403,
            detail=f"Command '{subcommand}' not allowed. Allowed: {ALLOWED_COMMANDS}",
        )

    return command


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "socket": SOCKET_PATH}


@app.post("/sessions", status_code=status.HTTP_201_CREATED)
async def create_session(
    request: CreateSessionRequest,
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """Create a new tmux session."""
    # Validate session name
    if not request.session_name or "/" in request.session_name:
        raise HTTPException(
            status_code=400,
            detail="Invalid session name",
        )

    # Build command
    args = ["new-session", "-d"] if request.detached else ["new-session"]
    args.extend(["-s", request.session_name])

    if request.command:
        args.extend(["-d", request.command])  # Run command in background

    returncode, stdout, stderr = run_tmux(args)

    if returncode != 0:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to create session: {stderr or stdout}",
        )

    return {
        "session_name": request.session_name,
        "created": True,
    }


@app.delete("/sessions/{session_name}")
async def destroy_session(
    session_name: str,
    _: str = Depends(verify_api_key),
) -> dict[str, str | bool]:
    """Destroy a tmux session."""""
    returncode, stdout, stderr = run_tmux(["kill-session", "-t", session_name])

    if returncode != 0:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {stderr or stdout}",
        )

    return {"session_name": session_name, "destroyed": True}


@app.get("/sessions")
async def list_sessions(
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """List all tmux sessions."""
    returncode, stdout, stderr = run_tmux(["list-sessions", "-F", "#{session_name}"])

    if returncode != 0 and "no sessions" in stderr.lower():
        return {"sessions": []}

    if returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list sessions: {stderr}",
        )

    sessions = [s.strip() for s in stdout.strip().split("\n") if s.strip()]

    return {"sessions": sessions}


@app.post("/sessions/{session_name}/send")
async def send_keys(
    session_name: str,
    request: SendKeysRequest,
    _: str = Depends(verify_api_key),
) -> SendKeysResponse:
    """Send keys to a tmux pane."""
    # Build send-keys command
    args = ["send-keys", "-t", f"{session_name}:{request.pane}"]

    # The keys are sent as separate arguments
    for char in request.keys:
        args.append(char)

    returncode, stdout, stderr = run_tmux(args)

    if returncode != 0:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to send keys: {stderr or stdout}",
        )

    return SendKeysResponse(success=True)


@app.post("/sessions/{session_name}/capture")
async def capture_pane(
    session_name: str,
    request: CapturePaneRequest,
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """Capture pane output."""
    args = ["capture-pane", "-t", f"{session_name}:{request.pane}", "-p"]

    if not request.capture_all:
        args.extend(["-S", "-10"])  # Last 10 lines

    returncode, stdout, stderr = run_tmux(args)

    if returncode != 0:
        raise HTTPException(
            status_code=404,
            detail=f"Session/pane not found: {stderr or stdout}",
        )

    return {
        "session_name": session_name,
        "pane": request.pane,
        "output": stdout,
    }


def main() -> None:
    """Run the server."""
    # Ensure socket directory exists
    socket_dir = Path(SOCKET_PATH).parent
    socket_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Starting tmux-control on {SOCKET_PATH}")
    logger.info(f"Allowed commands: {ALLOWED_COMMANDS}")

    uvicorn.run(
        app,
        uds=SOCKET_PATH,
        log_level="info",
    )


if __name__ == "__main__":
    main()
