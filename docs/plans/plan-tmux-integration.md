# Tmux System Integration Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a stable tmux orchestration system in fork_agent with session/window management, agent messaging, scheduling, and monitoring capabilities.

**Architecture:** Follow Clean Architecture principles with new domain entities (TmuxSession, TmuxWindow) and application services (TmuxSessionManager, AgentMessenger, SchedulerService). Integrate with existing terminal_spawner.py using dependency injection while maintaining backward compatibility.

**Tech Stack:** Python 3.11+, tmux API (via subprocess), frozen dataclasses, type hints, pytest for testing.

---

## 1. Executive Summary

### 1.1 Goal and Scope
Integrate tmux orchestration capabilities from Tmux-Orchestrator into fork_agent, creating a comprehensive terminal management system that supports:
- Session and window management
- Agent communication across sessions
- Task scheduling with context preservation
- Monitoring and observability

### 1.2 Key Deliverables
1. New domain entities for tmux sessions and windows
2. Application services for tmux management, messaging, and scheduling
3. CLI commands for tmux operations
4. Comprehensive test coverage (90%+)
5. Integration with existing terminal_spawner.py

### 1.3 Success Criteria
- All tmux operations work on macOS and Linux
- Backward compatibility with existing terminal_spawner
- 90%+ test coverage
- Clean Architecture compliance
- Type hints (mypy compatible)
- Frozen dataclasses for immutability

---

## 2. Architecture Design

### 2.1 File Structure

```
src/
├── domain/
│   ├── entities/
│   │   ├── terminal.py      # Existing: TerminalResult, TerminalConfig
│   │   └── tmux.py          # New: TmuxSession, TmuxWindow, TmuxMessage
│   └── exceptions/
│       ├── terminal.py      # Existing: TerminalError, etc.
│       └── tmux.py          # New: TmuxError, SessionNotFoundError, etc.
├── application/
│   ├── services/
│   │   ├── terminal/
│   │   │   ├── terminal_spawner.py  # Existing: TerminalSpawner
│   │   │   └── platform_detector.py # Existing: Platform detection
│   │   └── tmux/
│   │       ├── tmux_session_manager.py    # Session management
│   │       ├── tmux_window_manager.py    # Window management
│   │       ├── agent_messenger.py       # Agent communication
│   │       └── scheduler_service.py     # Task scheduling
│   └── use_cases/
│       ├── fork_terminal.py            # Existing: Fork terminal use case
│       └── tmux/
│           ├── list_sessions.py
│           ├── create_session.py
│           ├── send_command.py
│           ├── capture_window.py
│           └── schedule_task.py
├── infrastructure/
│   ├── platform/
│   │   └── tmux/
│   │       └── tmux_command_executor.py  # tmux CLI execution
│   └── config/
│       └── config.py                    # Add tmux config options
└── interfaces/
    └── cli/
        ├── fork.py                      # Existing: Main CLI
        └── tmux.py                      # New: Tmux subcommands
```

### 2.2 Domain Entities (src/domain/entities/tmux.py)

```python
"""Tmux domain entities."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class TmuxSession:
    """Represents a tmux session entity.
    
    Immutable entity containing session metadata.
    """
    session_id: str
    name: str
    windows: List['TmuxWindow']
    is_attached: bool
    creation_time: datetime
    
    def __post_init__(self) -> None:
        """Validate session state."""
        if not self.session_id:
            raise ValueError("session_id cannot be empty")
        if not self.name:
            raise ValueError("name cannot be empty")


@dataclass(frozen=True)
class TmuxWindow:
    """Represents a tmux window entity.
    
    Immutable entity containing window metadata.
    """
    window_id: str
    index: int
    name: str
    pane_count: int
    current_path: str
    last_activity: datetime
    
    def __post_init__(self) -> None:
        """Validate window state."""
        if not self.window_id:
            raise ValueError("window_id cannot be empty")
        if self.index < 0:
            raise ValueError("index cannot be negative")


@dataclass(frozen=True)
class TmuxMessage:
    """Represents a message between agents.
    
    Immutable entity for agent communication.
    """
    message_id: str
    sender_id: str
    recipient_id: str
    content: str
    timestamp: datetime
    context: Optional[Dict[str, Any]] = None
    
    def __post_init__(self) -> None:
        """Validate message state."""
        if not self.message_id:
            raise ValueError("message_id cannot be empty")
        if not self.sender_id:
            raise ValueError("sender_id cannot be empty")
        if not self.content:
            raise ValueError("content cannot be empty")


@dataclass(frozen=True)
class TmuxSnapshot:
    """Represents a snapshot of tmux state.
    
    Immutable entity for monitoring purposes.
    """
    snapshot_id: str
    timestamp: datetime
    sessions: List[TmuxSession]
    system_info: Dict[str, Any]
```

### 2.3 Domain Exceptions (src/domain/exceptions/tmux.py)

```python
"""Tmux-specific exceptions."""

from src.domain.exceptions.terminal import TerminalError


class TmuxError(TerminalError):
    """Base exception for tmux-related errors."""
    pass


class SessionNotFoundError(TmuxError):
    """Exception when a tmux session is not found."""
    
    def __init__(self, session_id: str):
        message = f"Session '{session_id}' not found"
        super().__init__(message, {"session_id": session_id})


class WindowNotFoundError(TmuxError):
    """Exception when a tmux window is not found."""
    
    def __init__(self, window_id: str):
        message = f"Window '{window_id}' not found"
        super().__init__(message, {"window_id": window_id})


class TmuxCommandError(TmuxError):
    """Exception when a tmux command fails."""
    
    def __init__(self, command: str, exit_code: int, output: str):
        message = f"Tmux command '{command}' failed with code {exit_code}"
        super().__init__(message, {
            "command": command,
            "exit_code": exit_code,
            "output": output
        })


class TmuxNotInstalledError(TmuxError):
    """Exception when tmux is not installed or available."""
    
    def __init__(self):
        message = "tmux is not installed or available in PATH"
        super().__init__(message)
```

### 2.4 Application Services

#### TmuxSessionManager (src/application/services/tmux/tmux_session_manager.py)

```python
"""Service for managing tmux sessions."""

from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.entities.tmux import TmuxSession
from src.domain.exceptions.tmux import SessionNotFoundError, TmuxCommandError


class TmuxSessionManager(ABC):
    """Abstract interface for tmux session management."""
    
    @abstractmethod
    def list_sessions(self) -> List[TmuxSession]:
        """List all active tmux sessions.
        
        Returns:
            List of TmuxSession objects.
        """
        ...
    
    @abstractmethod
    def create_session(self, name: str, command: Optional[str] = None) -> TmuxSession:
        """Create a new tmux session.
        
        Args:
            name: Session name.
            command: Initial command to execute.
        
        Returns:
            Created TmuxSession.
        """
        ...
    
    @abstractmethod
    def kill_session(self, session_id: str) -> bool:
        """Kill a tmux session.
        
        Args:
            session_id: Session ID to kill.
        
        Returns:
            True if session was killed successfully.
        
        Raises:
            SessionNotFoundError: If session not found.
        """
        ...
    
    @abstractmethod
    def find_session(self, session_id: str) -> Optional[TmuxSession]:
        """Find a session by ID.
        
        Args:
            session_id: Session ID to find.
        
        Returns:
            TmuxSession if found, None otherwise.
        """
        ...
```

#### TmuxWindowManager (src/application/services/tmux/tmux_window_manager.py)

```python
"""Service for managing tmux windows."""

from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.entities.tmux import TmuxWindow
from src.domain.exceptions.tmux import WindowNotFoundError


class TmuxWindowManager(ABC):
    """Abstract interface for tmux window management."""
    
    @abstractmethod
    def list_windows(self, session_id: str) -> List[TmuxWindow]:
        """List all windows in a session.
        
        Args:
            session_id: Session ID.
        
        Returns:
            List of TmuxWindow objects.
        """
        ...
    
    @abstractmethod
    def capture_window(self, window_id: str) -> str:
        """Capture window contents.
        
        Args:
            window_id: Window ID to capture.
        
        Returns:
            Window contents as string.
        
        Raises:
            WindowNotFoundError: If window not found.
        """
        ...
    
    @abstractmethod
    def send_command(self, window_id: str, command: str) -> bool:
        """Send command to window.
        
        Args:
            window_id: Window ID.
            command: Command to send.
        
        Returns:
            True if command sent successfully.
        
        Raises:
            WindowNotFoundError: If window not found.
        """
        ...
    
    @abstractmethod
    def find_window(self, window_id: str) -> Optional[TmuxWindow]:
        """Find a window by ID.
        
        Args:
            window_id: Window ID to find.
        
        Returns:
            TmuxWindow if found, None otherwise.
        """
        ...
```

#### AgentMessenger (src/application/services/tmux/agent_messenger.py)

```python
"""Service for agent communication via tmux."""

from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.entities.tmux import TmuxMessage


class AgentMessenger(ABC):
    """Abstract interface for agent communication."""
    
    @abstractmethod
    def send_message(
        self,
        sender_id: str,
        recipient_id: str,
        content: str,
        context: Optional[dict] = None
    ) -> TmuxMessage:
        """Send a message between agents.
        
        Args:
            sender_id: Sender agent ID.
            recipient_id: Recipient agent ID.
            content: Message content.
            context: Optional context/d metadata.
        
        Returns:
            Sent TmuxMessage.
        """
        ...
    
    @abstractmethod
    def receive_messages(self, agent_id: str) -> List[TmuxMessage]:
        """Receive messages for an agent.
        
        Args:
            agent_id: Agent ID to receive messages for.
        
        Returns:
            List of TmuxMessage objects.
        """
        ...
    
    @abstractmethod
    def mark_message_read(self, message_id: str) -> bool:
        """Mark a message as read.
        
        Args:
            message_id: Message ID to mark as read.
        
        Returns:
            True if message was marked as read.
        """
        ...
```

#### SchedulerService (src/application/services/tmux/scheduler_service.py)

```python
"""Service for scheduling tasks with context preservation."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, List, Optional

from src.domain.entities.tmux import TmuxSession


class SchedulerService(ABC):
    """Abstract interface for task scheduling."""
    
    @abstractmethod
    def schedule_task(
        self,
        session: TmuxSession,
        task_name: str,
        command: str,
        scheduled_time: datetime,
        context: Optional[dict] = None
    ) -> str:
        """Schedule a task to run in a session.
        
        Args:
            session: Target TmuxSession.
            task_name: Task name.
            command: Command to execute.
            scheduled_time: Time to execute task.
            context: Optional task context.
        
        Returns:
            Task ID.
        """
        ...
    
    @abstractmethod
    def list_scheduled_tasks(self, session: Optional[TmuxSession] = None) -> List[dict]:
        """List scheduled tasks.
        
        Args:
            session: Optional session filter.
        
        Returns:
            List of scheduled tasks.
        """
        ...
    
    @abstractmethod
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task.
        
        Args:
            task_id: Task ID to cancel.
        
        Returns:
            True if task was cancelled.
        """
        ...
```

---

## 3. Implementation Phases

### Phase 1: Core Tmux Operations (Session/Window Management)
**Goal:** Implement basic tmux session and window management.

#### Tasks:
1. Create domain entities and exceptions
2. Implement tmux command executor
3. Implement TmuxSessionManager with list/create/kill operations
4. Implement TmuxWindowManager with list/capture/send operations
5. Create use cases for session and window management
6. Add CLI commands
7. Write comprehensive tests

**Files:**
- Create: `src/domain/entities/tmux.py`
- Create: `src/domain/exceptions/tmux.py`
- Create: `src/infrastructure/platform/tmux/tmux_command_executor.py`
- Create: `src/application/services/tmux/tmux_session_manager.py`
- Create: `src/application/services/tmux/tmux_window_manager.py`
- Create: `src/application/use_cases/tmux/list_sessions.py`
- Create: `src/application/use_cases/tmux/create_session.py`
- Create: `src/application/use_cases/tmux/send_command.py`
- Create: `src/application/use_cases/tmux/capture_window.py`
- Create: `src/interfaces/cli/tmux.py`
- Create: `tests/unit/domain/test_tmux_entities.py`
- Create: `tests/unit/domain/test_tmux_exceptions.py`
- Create: `tests/unit/application/services/test_tmux_session_manager.py`
- Create: `tests/unit/application/services/test_tmux_window_manager.py`

### Phase 2: Agent Messaging and Communication
**Goal:** Implement agent communication across tmux sessions.

#### Tasks:
1. Implement AgentMessenger service
2. Create use case for sending/receiving messages
3. Add CLI commands for messaging
4. Write tests for messaging functionality

**Files:**
- Create: `src/application/services/tmux/agent_messenger.py`
- Create: `src/application/use_cases/tmux/send_message.py`
- Create: `src/application/use_cases/tmux/receive_messages.py`
- Modify: `src/interfaces/cli/tmux.py`
- Create: `tests/unit/application/services/test_agent_messenger.py`

### Phase 3: Scheduling and Automation
**Goal:** Implement task scheduling with context preservation.

#### Tasks:
1. Implement SchedulerService
2. Create use case for scheduling tasks
3. Add CLI commands for scheduling
4. Write tests for scheduler functionality

**Files:**
- Create: `src/application/services/tmux/scheduler_service.py`
- Create: `src/application/use_cases/tmux/schedule_task.py`
- Create: `src/application/use_cases/tmux/list_tasks.py`
- Create: `src/application/use_cases/tmux/cancel_task.py`
- Modify: `src/interfaces/cli/tmux.py`
- Create: `tests/unit/application/services/test_scheduler_service.py`

### Phase 4: Monitoring and Observability
**Goal:** Implement monitoring and snapshot capabilities.

#### Tasks:
1. Create TmuxSnapshot entity
2. Implement monitoring service
3. Add CLI commands for snapshots and monitoring
4. Write tests for monitoring functionality

**Files:**
- Modify: `src/domain/entities/tmux.py` (add TmuxSnapshot)
- Create: `src/application/services/tmux/monitoring_service.py`
- Create: `src/application/use_cases/tmux/create_snapshot.py`
- Create: `src/application/use_cases/tmux/list_snapshots.py`
- Modify: `src/interfaces/cli/tmux.py`
- Create: `tests/unit/application/services/test_monitoring_service.py`

---

## 4. Technical Specifications

### 4.1 API Design

#### TmuxSessionManagerImpl

```python
"""Implementation of TmuxSessionManager."""

import subprocess
from datetime import datetime
from typing import List, Optional

from src.application.services.tmux.tmux_session_manager import TmuxSessionManager
from src.domain.entities.tmux import TmuxSession, TmuxWindow
from src.domain.exceptions.tmux import (
    SessionNotFoundError,
    TmuxCommandError,
    TmuxNotInstalledError,
)
from src.infrastructure.platform.tmux.tmux_command_executor import (
    TmuxCommandExecutor,
)


class TmuxSessionManagerImpl(TmuxSessionManager):
    """Implementation of tmux session management."""
    
    def __init__(self, command_executor: TmuxCommandExecutor):
        """Initialize session manager.
        
        Args:
            command_executor: Tmux command executor.
        """
        self._executor = command_executor
    
    def list_sessions(self) -> List[TmuxSession]:
        """List all active tmux sessions."""
        output = self._executor.execute(["list-sessions", "-F", "#{session_id} #{session_name} #{session_attached} #{session_created}"])
        
        sessions = []
        for line in output.strip().split("\n"):
            if line.strip():
                session_id, name, is_attached, created = line.split(maxsplit=3)
                sessions.append(
                    TmuxSession(
                        session_id=session_id,
                        name=name,
                        windows=self._list_session_windows(session_id),
                        is_attached=is_attached == "1",
                        creation_time=datetime.fromtimestamp(int(created)),
                    )
                )
        return sessions
    
    def create_session(self, name: str, command: Optional[str] = None) -> TmuxSession:
        """Create a new tmux session."""
        args = ["new-session", "-d", "-s", name]
        if command:
            args.append(command)
        
        self._executor.execute(args)
        return self.find_session(name)
    
    # ... other methods implementation
```

#### TmuxCommandExecutor

```python
"""tmux CLI command executor."""

import subprocess
from typing import List, Optional

from src.domain.exceptions.tmux import TmuxCommandError, TmuxNotInstalledError


class TmuxCommandExecutor:
    """Executes tmux CLI commands."""
    
    def __init__(self):
        """Check if tmux is available on initialization."""
        try:
            subprocess.run(
                ["tmux", "-V"],
                capture_output=True,
                text=True,
                check=True,
            )
        except FileNotFoundError:
            raise TmuxNotInstalledError()
    
    def execute(self, args: List[str], check: bool = True) -> str:
        """Execute a tmux command.
        
        Args:
            args: Command arguments.
            check: Whether to check for command success.
        
        Returns:
            Command output.
        
        Raises:
            TmuxCommandError: If command fails and check=True.
        """
        command = ["tmux"] + args
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
        )
        
        if check and result.returncode != 0:
            raise TmuxCommandError(
                command=" ".join(command),
                exit_code=result.returncode,
                output=result.stderr.strip(),
            )
        
        return result.stdout.strip()
```

### 4.2 Error Handling Strategy

1. **TmuxNotInstalledError**: Raised when tmux command not found in PATH
2. **SessionNotFoundError**: Raised when attempting to operate on non-existent session
3. **WindowNotFoundError**: Raised when attempting to operate on non-existent window
4. **TmuxCommandError**: Raised when tmux command execution fails

All exceptions inherit from `TerminalError` for compatibility with existing error handling.

### 4.3 Testing Strategy (TDD)

Tests follow AAA (Arrange, Act, Assert) pattern:

```python
"""Tests for TmuxSessionManagerImpl."""

import pytest
from unittest.mock import Mock, patch

from src.application.services.tmux.tmux_session_manager import TmuxSessionManagerImpl
from src.domain.exceptions.tmux import SessionNotFoundError, TmuxNotInstalledError
from src.infrastructure.platform.tmux.tmux_command_executor import (
    TmuxCommandExecutor,
)


class TestTmuxSessionManagerImpl:
    """Tests for TmuxSessionManagerImpl."""
    
    def test_list_sessions_empty(self):
        """Test listing sessions when none exist."""
        # Arrange
        mock_executor = Mock(TmuxCommandExecutor)
        mock_executor.execute.return_value = ""
        manager = TmuxSessionManagerImpl(mock_executor)
        
        # Act
        sessions = manager.list_sessions()
        
        # Assert
        assert len(sessions) == 0
        mock_executor.execute.assert_called_once()
    
    def test_create_session(self):
        """Test creating a new session."""
        # Arrange
        mock_executor = Mock(TmuxCommandExecutor)
        mock_executor.execute.return_value = ""
        manager = TmuxSessionManagerImpl(mock_executor)
        
        # Act
        session = manager.create_session("test-session")
        
        # Assert
        assert session.name == "test-session"
        mock_executor.execute.assert_called_once()
    
    def test_kill_non_existent_session(self):
        """Test killing a non-existent session raises exception."""
        # Arrange
        mock_executor = Mock(TmuxCommandExecutor)
        mock_executor.execute.side_effect = Exception("Session not found")
        manager = TmuxSessionManagerImpl(mock_executor)
        
        # Act & Assert
        with pytest.raises(SessionNotFoundError):
            manager.kill_session("non-existent")
```

---

## 5. CLI Commands

### New CLI Structure

```
fork tmux [command] [options]

Commands:
  list          List all active tmux sessions
  create        Create a new tmux session
  kill          Kill a tmux session
  windows       List windows in a session
  capture       Capture window contents
  send          Send command to a window
  message       Send message to an agent
  schedule      Schedule a task
  tasks         List scheduled tasks
  snapshot      Create tmux state snapshot
```

### Example Commands

```bash
# List all sessions
fork tmux list

# Create new session
fork tmux create --name "my-session" --command "python3 app.py"

# Send command to window
fork tmux send --window-id "%12" --command "ls -la"

# Capture window contents
fork tmux capture --window-id "%12" > output.txt

# Schedule a task
fork tmux schedule --session "my-session" --task "backup" \
  --command "backup.sh" --time "2024-01-01 02:00"
```

### CLI Implementation (src/interfaces/cli/tmux.py)

```python
"""CLI for tmux operations."""

import sys
from typing import Callable, List, Optional

import click

from src.application.services.tmux.tmux_session_manager import (
    TmuxSessionManager,
    TmuxSessionManagerImpl,
)
from src.application.services.tmux.tmux_window_manager import (
    TmuxWindowManager,
    TmuxWindowManagerImpl,
)
from src.infrastructure.platform.tmux.tmux_command_executor import (
    TmuxCommandExecutor,
)


@click.group()
@click.pass_context
def tmux(ctx):
    """Manage tmux sessions and windows."""
    ctx.ensure_object(dict)
    executor = TmuxCommandExecutor()
    ctx.obj["session_manager"] = TmuxSessionManagerImpl(executor)
    ctx.obj["window_manager"] = TmuxWindowManagerImpl(executor)


@tmux.command()
@click.pass_context
def list(ctx):
    """List all active tmux sessions."""
    session_manager = ctx.obj["session_manager"]
    sessions = session_manager.list_sessions()
    
    for session in sessions:
        click.echo(f"{session.session_id} - {session.name}")
        for window in session.windows:
            click.echo(f"  {window.window_id} - {window.name}")


@tmux.command()
@click.option("--name", required=True, help="Session name")
@click.option("--command", help="Initial command to execute")
@click.pass_context
def create(ctx, name: str, command: Optional[str]):
    """Create a new tmux session."""
    session_manager = ctx.obj["session_manager"]
    try:
        session = session_manager.create_session(name, command)
        click.echo(f"Session created: {session.session_id} - {session.name}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@tmux.command()
@click.option("--session-id", required=True, help="Session ID to kill")
@click.pass_context
def kill(ctx, session_id: str):
    """Kill a tmux session."""
    session_manager = ctx.obj["session_manager"]
    try:
        success = session_manager.kill_session(session_id)
        if success:
            click.echo("Session killed successfully")
        else:
            click.echo("Failed to kill session")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@tmux.command()
@click.option("--window-id", required=True, help="Window ID")
@click.option("--command", required=True, help="Command to send")
@click.pass_context
def send(ctx, window_id: str, command: str):
    """Send command to a window."""
    window_manager = ctx.obj["window_manager"]
    try:
        success = window_manager.send_command(window_id, command)
        if success:
            click.echo("Command sent successfully")
        else:
            click.echo("Failed to send command")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@tmux.command()
@click.option("--window-id", required=True, help="Window ID")
@click.pass_context
def capture(ctx, window_id: str):
    """Capture window contents."""
    window_manager = ctx.obj["window_manager"]
    try:
        content = window_manager.capture_window(window_id)
        click.echo(content)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def create_tmux_cli() -> Callable[[], int]:
    """Create the tmux CLI."""
    return tmux


if __name__ == "__main__":
    tmux()
```

---

## 6. Migration Path

### 6.1 From Current terminal_spawner.py

The existing `TerminalSpawner` will be extended to support tmux as a backend option, maintaining compatibility with existing functionality.

### Changes to terminal_spawner.py

```python
"""Updated TerminalSpawner with tmux support."""

from src.application.services.tmux.tmux_session_manager import (
    TmuxSessionManager,
    TmuxSessionManagerImpl,
)
from src.domain.entities.terminal import TerminalConfig, TerminalResult
from src.infrastructure.platform.tmux.tmux_command_executor import (
    TmuxCommandExecutor,
)


class TerminalSpawnerImpl(TerminalSpawner):
    """Updated implementation with tmux support."""
    
    def spawn(self, command: str, config: TerminalConfig) -> TerminalResult:
        """Abre una terminal y ejecuta un comando."""
        platform = config.platform.value
        
        if config.terminal == "tmux" or (platform == "Linux" and not self._find_terminal()):
            return self._spawn_with_tmux(command)
        
        # Existing platform-specific logic
        if platform == "Darwin":
            return self._spawn_macos(command)
        elif platform == "Windows":
            return self._spawn_windows(command)
        elif platform == "Linux":
            return self._spawn_linux(command)
        else:
            raise TerminalNotFoundError(platform, [])
    
    def _spawn_with_tmux(self, command: str) -> TerminalResult:
        """Spawn terminal using tmux (enhanced version)."""
        try:
            executor = TmuxCommandExecutor()
            session_manager = TmuxSessionManagerImpl(executor)
            session = session_manager.create_session(
                name=f"fork_term_{str(uuid.uuid4())[:8]}",
                command=command
            )
            return TerminalResult(
                success=True,
                output=f"New terminal session opened in tmux (session: {session.name}).",
                exit_code=0,
            )
        except Exception as e:
            raise TerminalNotFoundError("tmux", ["tmux"])
```

### Configuration Updates (src/infrastructure/config/config.py)

```python
"""Updated config with tmux options."""

class ConfigLoader:
    """Updated config loader with tmux options."""
    
    def load(self) -> dict:
        """Load configuration with tmux options."""
        self._config = {
            "fork_agent_debug": self._get_bool("FORK_AGENT_DEBUG", False),
            "fork_agent_shell": self._get_str("FORK_AGENT_SHELL", "bash"),
            "fork_agent_default_terminal": self._get_str("FORK_AGENT_DEFAULT_TERMINAL", ""),
            "fork_agent_tmux_enabled": self._get_bool("FORK_AGENT_TMUX_ENABLED", True),
            "fork_agent_tmux_default_session": self._get_str("FORK_AGENT_TMUX_DEFAULT_SESSION", "fork-default"),
        }
        return self._config
```

---

## 7. Risks and Mitigations

### 7.1 Platform-Specific Issues

**Windows Support:** Tmux is not natively available on Windows. We'll check platform support before using tmux operations.

```python
"""Platform detection for tmux support."""

from src.domain.entities.terminal import PlatformType


def is_tmux_supported(platform: PlatformType) -> bool:
    """Check if tmux is supported on the platform."""
    return platform in [PlatformType.DARWIN, PlatformType.LINUX]
```

### 7.2 Tmux Version Compatibility

Different tmux versions may have incompatible CLI options. We'll test against popular versions (3.0+).

```python
"""Version detection and compatibility handling."""

import subprocess


def get_tmux_version() -> str:
    """Get tmux version."""
    try:
        result = subprocess.run(
            ["tmux", "-V"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip().split(" ")[1]
    except Exception as e:
        raise TmuxNotInstalledError()
```

### 7.3 Testing Challenges

Testing tmux operations requires a running tmux server. We'll use mock objects and integration tests.

```python
"""Test utilities for tmux operations."""

from unittest.mock import Mock

from src.application.services.tmux.tmux_session_manager import (
    TmuxSessionManagerImpl,
)
from src.infrastructure.platform.tmux.tmux_command_executor import (
    TmuxCommandExecutor,
)


def create_mock_session_manager():
    """Create a session manager with mock executor."""
    mock_executor = Mock(TmuxCommandExecutor)
    return TmuxSessionManagerImpl(mock_executor)
```

---

## 8. Execution Timeline

### Milestone 1: Phase 1 Complete (Core Operations) - 5 days
- Domain entities and exceptions
- Session and window managers
- Basic CLI commands
- Tests

### Milestone 2: Phase 2 Complete (Messaging) - 3 days
- AgentMessenger implementation
- Messaging CLI commands
- Tests

### Milestone 3: Phase 3 Complete (Scheduling) - 3 days
- SchedulerService implementation
- Scheduling CLI commands
- Tests

### Milestone 4: Phase 4 Complete (Monitoring) - 2 days
- Monitoring service
- Snapshot functionality
- Tests

### Total: 13 days

---

## 9. Success Metrics

- All 4 phases implemented and tested
- 90%+ test coverage
- All CLI commands functional
- Backward compatibility maintained
- Works on macOS and Linux
- No critical bugs

---

## 10. Next Steps

1. Execute Phase 1: Core Tmux Operations
2. Run tests to verify functionality
3. Review and iterate based on feedback
4. Execute remaining phases sequentially
5. Perform final integration testing
6. Update documentation
