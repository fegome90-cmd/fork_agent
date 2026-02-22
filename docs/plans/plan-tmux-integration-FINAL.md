# Tmux Integration Technical Specification - FINAL

> **Document Version:** 3.0 (Final Consolidation)  
> **Date:** 2026-02-22  
> **Status:** CONDITIONAL_APPROVED (with fixes incorporated)  
> **Based On:** plan-tmux-integration-v2-cmux-enhanced.md + Code Review Feedback

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Fixes Incorporated](#2-fixes-incorporated)
3. [Architecture (3-Phase Plan)](#3-architecture-3-phase-plan)
4. [Component Specifications](#4-component-specifications)
5. [Security Requirements](#5-security-requirements)
6. [Boundaries](#7. [Implementation Checklist6-boundaries)
](#7-implementation-checklist)

---

## 1. Executive Summary

### 1.1 Project Overview

This technical specification defines the integration of git worktree-based workspace management capabilities into the fork_agent project. The integration draws inspiration from cmux, a bash-based tool for managing git worktrees with tmux sessions, while leveraging fork_agent's existing Clean Architecture principles, type safety, and testability.

The primary goal is to enable isolated workspace environments for multi-agent workflows, where each agent can work in its own git worktree without interfering with others. This provides:

- **Code Isolation**: Each workspace has its own working directory via git worktree
- **Branch Management**: Automatic branch creation and cleanup
- **Hook Automation**: Setup and teardown scripts for environment initialization
- **Layout Flexibility**: Multiple directory organization strategies
- **Context Awareness**: Auto-detection of current workspace from `$PWD`

### 1.2 Verdict

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│                    C O N D I T I O N A L                            │
│                    A P P R O V E D                                  │
│                                                                     │
│   This plan is APPROVED subject to the mandatory fixes listed       │
│   in Section 2. All Pre-Commit fixes MUST be implemented before     │
│   the first commit, and all Pre-Alpha fixes MUST be implemented     │
│   before the alpha release.                                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.3 Key Metrics

| Metric | Value |
|--------|-------|
| Total Issues Identified | 11 |
| Critical (Pre-Commit) | 5 |
| Major (Pre-Alpha) | 4 |
| Minor (Post-MVP) | 2 |
| Implementation Phases | 3 |
| Estimated Duration | 5-6 weeks |

---

## 2. Fixes Incorporated

This section documents all fixes identified during code review and their incorporation into this specification.

### 2.1 Pre-Commit Fixes (MUST Before First Commit)

The following five critical issues MUST be resolved before any implementation commit:

#### C-01: Workspace Entities in Application Layer (NOT Domain)

**Issue:** Entities were incorrectly placed in `src/domain/entities/` when they belong in the application layer.

**Fix Applied:** All workspace entities are now specified to reside in `src/application/services/workspace/`:

```python
# CORRECT: Application layer location
src/application/services/workspace/
├── __init__.py
├── entities.py          # Workspace, WorkspaceHook, WorkspaceConfig
├── exceptions.py        # WorkspaceError hierarchy
├── workspace_manager.py # WorkspaceManager interface + impl
├── hook_runner.py      # HookRunner interface + impl
└── layout_resolver.py  # LayoutResolver utility
```

**Rationale:** Per Clean Architecture principles:
- Domain entities must be immutable and free of application logic
- Workspace entities contain business logic (sanitization, validation)
- Application services orchestrate domain entities
- This separation maintains the dependency inversion principle

#### C-02: HookRunnerImpl Includes Path Sanitization

**Issue:** Hook execution lacked input validation, creating security vulnerabilities.

**Fix Applied:** The specification now mandates `_sanitize_path()` implementation:

```python
class HookRunnerImpl(HookRunner):
    """Implementation of HookRunner with security measures."""
    
    def _sanitize_path(self, path: str) -> Path:
        """Sanitize and validate hook path to prevent attacks.
        
        Security measures:
        1. Resolve to absolute path
        2. Block path traversal attempts (..)
        3. Verify path exists and is a file
        4. Verify executable permissions
        
        Args:
            path: Raw path string from user/config
            
        Returns:
            Validated Path object
            
        Raises:
            SecurityError: If path is invalid or dangerous
        """
        # Resolve to absolute path
        abs_path = Path(path).resolve()
        
        # Block path traversal
        if ".." in str(path):
            raise SecurityError(f"Path traversal attempt detected: {path}")
        
        # Must be a file
        if not abs_path.is_file():
            raise SecurityError(f"Hook path is not a file: {path}")
        
        # Verify executable permission
        if not os.access(abs_path, os.X_OK):
            raise SecurityError(f"Hook is not executable: {path}")
        
        return abs_path
    
    def _execute_hook(self, hook_path: Path, cwd: str) -> bool:
        """Execute hook with security validation."""
        # Validate hook path before execution
        safe_path = self._sanitize_path(str(hook_path))
        
        # Validate working directory
        safe_cwd = Path(cwd).resolve()
        if not safe_cwd.is_dir():
            raise SecurityError(f"Working directory does not exist: {cwd}")
        
        try:
            result = subprocess.run(
                [str(safe_path)],
                cwd=str(safe_cwd),
                capture_output=True,
                text=True,
                timeout=self._config.hook_timeout,  # Configurable
                env=self._get_sanitized_env(),       # Sanitized environment
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            raise HookExecutionError(str(hook_path), -1, "Timeout exceeded")
        except Exception as e:
            raise HookExecutionError(str(hook_path), -1, str(e))
```

#### C-03: GitCommandExecutor Includes Version Verification

**Issue:** Git availability was assumed but not verified.

**Fix Applied:** The specification now includes mandatory git version verification:

```python
class GitCommandExecutor:
    """Executor for git commands with version verification."""
    
    MINIMUM_GIT_VERSION = "2.20"  # Git worktree introduced in 2.20
    
    def __init__(self) -> None:
        """Initialize and verify git availability."""
        self._verify_git_available()
        self._verify_git_version()
    
    def _verify_git_available(self) -> None:
        """Verify git is installed and accessible.
        
        Raises:
            GitNotFoundError: If git is not installed
        """
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                raise GitNotFoundError("git command not found")
        except FileNotFoundError:
            raise GitNotFoundError("git is not installed")
    
    def _verify_git_version(self) -> None:
        """Verify git version meets minimum requirement.
        
        Git worktree feature was introduced in version 2.20.
        
        Raises:
            GitVersionError: If git version is insufficient
        """
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        
        # Parse version from "git version 2.43.0"
        version_str = result.stdout.strip().split()[-1]
        version_parts = version_str.split(".")
        
        # Compare major.minor
        required = self.MINIMUM_GIT_VERSION.split(".")
        actual = version_parts[:2]
        
        if actual < required:
            raise GitVersionError(
                f"Git {self.MINIMUM_GIT_VERSION}+ required, "
                f"found {version_str}"
            )
    
    def worktree_add(self, path: str, branch: str) -> bool:
        """Add a git worktree.
        
        Args:
            path: Absolute path for the worktree
            branch: Branch name to create
            
        Returns:
            True if successful
            
        Raises:
            GitError: If command fails
        """
        result = subprocess.run(
            ["git", "worktree", "add", path, branch],
            capture_output=True,
            text=True,
            timeout=60,
        )
        
        if result.returncode != 0:
            raise GitError(f"Failed to create worktree: {result.stderr}")
        
        return True
```

**Requirements Documentation:**
```markdown
### System Requirements
- Git >= 2.20 (for git worktree support)
- Verifiable with: `git --version`
```

#### C-04: Exceptions Inherit from Base Exception Class

**Issue:** Workspace exceptions incorrectly inherited from `TmuxError`.

**Fix Applied:** All workspace exceptions now inherit from the base `Exception` class:

```python
# src/application/services/workspace/exceptions.py

class WorkspaceError(Exception):
    """Base exception for all workspace operations.
    
    All workspace-specific exceptions inherit from this class
    to maintain independence from tmux-related error handling.
    """
    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        """Convert exception to dictionary for serialization."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


class WorkspaceExistsError(WorkspaceError):
    """Raised when attempting to create a workspace that already exists.
    
    This is NOT an error in idempotent operations - the caller
    should handle this case gracefully and return the existing workspace.
    """
    def __init__(self, name: str, path: str):
        super().__init__(
            f"Workspace '{name}' already exists at {path}",
            {"name": name, "path": path}
        )


class WorkspaceNotFoundError(WorkspaceError):
    """Raised when a requested workspace does not exist."""
    def __init__(self, name: str):
        super().__init__(
            f"Workspace '{name}' not found",
            {"name": name}
        )


class WorkspaceNotCleanError(WorkspaceError):
    """Raised when workspace has uncommitted changes.
    
    This prevents accidental data loss during workspace removal.
    """
    def __init__(self, name: str, path: str):
        super().__init__(
            f"Workspace '{name}' at {path} has uncommitted changes",
            {"name": name, "path": path}
        )


class HookExecutionError(WorkspaceError):
    """Raised when a hook script fails during execution."""
    def __init__(self, hook_path: str, exit_code: int, details: str = ""):
        super().__init__(
            f"Hook '{hook_path}' failed with exit code {exit_code}: {details}",
            {"hook_path": hook_path, "exit_code": exit_code, "details": details}
        )


class InvalidLayoutError(WorkspaceError):
    """Raised when an invalid layout type is specified."""
    def __init__(self, layout: str):
        super().__init__(
            f"Invalid layout type: {layout}",
            {"layout": layout}
        )


class SecurityError(WorkspaceError):
    """Raised when a security constraint is violated."""
    def __init__(self, message: str):
        super().__init__(message, {"type": "security_violation"})


class GitError(WorkspaceError):
    """Raised when a git command fails."""
    def __init__(self, message: str, command: str | None = None):
        super().__init__(
            message,
            {"command": command} if command else {}
        )


class GitNotFoundError(GitError):
    """Raised when git is not installed or not in PATH."""
    def __init__(self, message: str = "git is not installed"):
        super().__init__(message, "git --version")


class GitVersionError(GitError):
    """Raised when git version is below minimum requirement."""
    def __init__(self, message: str):
        super().__init__(message, "git --version")
```

#### C-05: safe_name Uses Regex Whitelist Validation

**Issue:** The original sanitization only replaced `/` with `-`, which was insufficient.

**Fix Applied:** Comprehensive regex-based sanitization:

```python
import re

@dataclass(frozen=True)
class Workspace:
    """Workspace entity with secure name validation."""
    
    workspace_id: str
    name: str                          # Original branch name
    safe_name: str                     # Sanitized for filesystem
    path: str                          # Absolute worktree path
    layout: LayoutType
    repo_root: str                     # Root of main repository
    created_at: datetime
    last_accessed: datetime | None = None
    setup_hook_executed: bool = False
    teardown_hook_executed: bool = False
    
    def __post_init__(self) -> None:
        """Validate workspace after creation."""
        if not self.workspace_id:
            raise ValueError("workspace_id cannot be empty")
        if not self.name:
            raise ValueError("name cannot be empty")
        if not self.path:
            raise ValueError("path cannot be empty")
        
        # Verify safe_name matches sanitized name
        expected_safe = self._sanitize(self.name)
        if self.safe_name != expected_safe:
            raise ValueError(
                f"safe_name '{self.safe_name}' doesn't match "
                f"sanitized '{self.name}' (expected '{expected_safe}')"
            )
    
    @staticmethod
    def _sanitize(name: str) -> str:
        """Sanitize branch name for use as filesystem directory name.
        
        Security measures:
        1. Replace forward slashes with hyphens
        2. Remove ALL characters except alphanumerics, hyphens, underscores
        3. Collapse multiple hyphens into one
        4. Remove leading/trailing hyphens
        
        Examples:
            feature/auth → feature-auth
            feature/foo-bar → feature-foo-bar
            bug/fix../..etc → bugfixetc (attack blocked)
            my branch name → my-branch-name
        
        Args:
            name: Original branch name
            
        Returns:
            Sanitized name safe for filesystem use
        """
        # Step 1: Replace forward slashes (common in branch names)
        result = name.replace("/", "-")
        
        # Step 2: Whitelist only allowed characters
        result = re.sub(r'[^a-zA-Z0-9_-]', '', result)
        
        # Step 3: Collapse multiple hyphens
        result = re.sub(r'-+', '-', result)
        
        # Step 4: Remove leading/trailing hyphens
        result = result.strip('-')
        
        # Step 5: Ensure not empty
        if not result:
            raise ValueError(f"Branch name '{name}' produces empty safe name")
        
        return result
```

### 2.2 Pre-Alpha Fixes (MUST Before Alpha Release)

The following four major issues MUST be resolved before the alpha release:

#### M-01: Timeout Configurable (Default 10 Minutes)

**Issue:** Fixed 5-minute timeout was insufficient for large operations.

**Fix Applied:** Timeout is now configurable with a sensible default:

```python
# Configuration schema
@dataclass(frozen=True)
class WorkspaceConfig:
    """Configuration for workspace operations."""
    
    repo_root: str
    layout: LayoutType
    base_directory: str
    hooks_enabled: bool = True
    auto_cleanup: bool = False
    max_workspaces: int | None = None
    hook_timeout: int = 600  # 10 minutes default
    
    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.hook_timeout < 60:
            raise InvalidConfigError(
                "hook_timeout must be at least 60 seconds"
            )
        if self.hook_timeout > 3600:
            raise InvalidConfigError(
                "hook_timeout must not exceed 1 hour"
            )


# In HookRunnerImpl
class HookRunnerImpl(HookRunner):
    def __init__(self, config: WorkspaceConfig | None = None):
        self._config = config or WorkspaceConfig(
            repo_root=".",
            layout=LayoutType.NESTED,
            base_directory=".worktrees",
            hook_timeout=600,  # 10 minutes default
        )
    
    def _execute_hook(self, hook_path: Path, cwd: str) -> bool:
        """Execute hook with configurable timeout."""
        result = subprocess.run(
            [str(hook_path)],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=self._config.hook_timeout,  # Now configurable!
        )
        return result.returncode == 0
```

#### M-02: worktree_is_valid() for Idempotency

**Issue:** Idempotent creation didn't verify worktree integrity.

**Fix Applied:** Implement integrity validation:

```python
class GitCommandExecutor:
    """Executor for git commands with validation."""
    
    def worktree_is_valid(self, worktree_path: str, branch_name: str) -> bool:
        """Verify a worktree exists and is valid.
        
        This method checks:
        1. The worktree directory exists
        2. It's a valid git worktree (not just a regular directory)
        3. The branch exists in the worktree
        
        Args:
            worktree_path: Absolute path to worktree
            branch_name: Expected branch name
            
        Returns:
            True if worktree is valid and healthy
        """
        path = Path(worktree_path)
        
        # Check directory exists
        if not path.exists() or not path.is_dir():
            return False
        
        # Check it's a git worktree (not regular directory)
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=str(path),
            capture_output=True,
            text=True,
            timeout=5,
        )
        
        if result.returncode != 0:
            return False  # Not a git repository
        
        # Verify branch exists
        result = subprocess.run(
            ["git", "rev-parse", "--verify", f"refs/heads/{branch_name}"],
            cwd=str(path),
            capture_output=True,
            text=True,
            timeout=5,
        )
        
        return result.returncode == 0
    
    def list_worktrees(self) -> list[dict]:
        """List all worktrees in the repository.
        
        Returns:
            List of worktree dictionaries with path and branch info
        """
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        
        if result.returncode != 0:
            return []
        
        worktrees = []
        current = {}
        
        for line in result.stdout.splitlines():
            if line.startswith("worktree "):
                if current:
                    worktrees.append(current)
                current = {"path": line[9:]}  # Remove "worktree " prefix
            elif line.startswith("HEAD "):
                current["head"] = line[5:]
            elif line.startswith("branch "):
                current["branch"] = line[7:]
        
        if current:
            worktrees.append(current)
        
        return worktrees


# Usage in WorkspaceManagerImpl
class WorkspaceManagerImpl(WorkspaceManager):
    def create_workspace(
        self,
        name: str,
        config: WorkspaceConfig,
        run_setup: bool = True,
    ) -> Workspace:
        safe_name = self._sanitize(name)
        worktree_path = self._resolve_path(config, safe_name)
        
        # Idempotent: check if exists AND is valid
        if Path(worktree_path).exists():
            # Verify integrity before returning
            if self._git.worktree_is_valid(worktree_path, name):
                workspace = self._load_workspace(name, config)
                return workspace
            
            # Worktree exists but is corrupted - attempt recovery
            # or raise error depending on configuration
            raise WorkspaceCorruptedError(
                name, worktree_path,
                "Worktree exists but is invalid"
            )
        
        # Proceed with creation...
```

#### M-03: Reduced to 3 Phases Maximum

**Issue:** Original 6-phase plan was too extensive.

**Fix Applied:** Consolidated to 3 phases (detailed in Section 3):

| Original | Consolidated |
|----------|--------------|
| Phase 1: Core Infrastructure | **Phase 1: Core** (Weeks 1-2) |
| Phase 2: Worktree Manager | |
| Phase 3: Hook System | **Phase 2: Integration** (Weeks 3-4) |
| Phase 4: Layout System | |
| Phase 5: Terminal Integration | **Phase 3: UX** (Weeks 5-6) |
| Phase 6: CLI & Completion | |

#### M-04: Clear Boundaries with TerminalSpawner

**Issue:** Overlap between workspace management and terminal spawning.

**Fix Applied:** Clear separation defined (detailed in Section 6):

- **TerminalSpawner**: Spawns terminal sessions in existing directories
- **WorkspaceManager**: Manages git worktree lifecycle
- **No circular dependencies**: WorkspaceManager does NOT spawn terminals
- **Cooperative integration**: TerminalSpawner uses WorkspaceManager to prepare environments

---

## 3. Architecture (3-Phase Plan)

### 3.1 Phase Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    IMPLEMENTATION ROADMAP                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Phase 1: CORE (Weeks 1-2)                                         │
│  ├── WorktreeManager: create, list, remove                        │
│  ├── GitCommandExecutor: git worktree commands                    │
│  ├── Basic Workspace entity and exceptions                        │
│  └── Milestone: Can create/list/remove worktrees programmatically │
│                                                                     │
│  Phase 2: INTEGRATION (Weeks 3-4)                                  │
│  ├── HookRunner with sanitization                                  │
│  ├── Layout management (NESTED, SIBLING, OUTER_NESTED)            │
│  ├── WorkspaceConfig validation                                    │
│  └── Milestone: Hooks run on setup/teardown                        │
│                                                                     │
│  Phase 3: UX (Weeks 5-6)                                           │
│  ├── CLI commands with completion                                 │
│  ├── Auto-detect existing worktrees                               │
│  ├── Configuration file support                                    │
│  └── Milestone: End-to-end user experience                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Phase 1: Core (Weeks 1-2)

#### Objectives
- Establish git worktree management foundation
- Implement core entities and exceptions
- Create GitCommandExecutor with validation

#### Deliverables

**1.1 Workspace Entities** (`src/application/services/workspace/entities.py`)
```python
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Optional

class LayoutType(Enum):
    """Worktree directory layout strategies."""
    NESTED = auto()       # .worktrees/<branch>/
    OUTER_NESTED = auto() # ../<repo>.worktrees/<branch>/
    SIBLING = auto()      # ../<repo>-<branch>/

class WorktreeState(Enum):
    """Worktree lifecycle states."""
    ACTIVE = auto()
    MERGED = auto()
    REMOVED = auto()

@dataclass(frozen=True)
class Workspace:
    """Isolated work environment based on git worktree."""
    workspace_id: str
    name: str
    safe_name: str
    path: str
    layout: LayoutType
    repo_root: str
    created_at: datetime
    last_accessed: Optional[datetime] = None
    setup_hook_executed: bool = False
    teardown_hook_executed: bool = False

@dataclass(frozen=True)
class WorkspaceConfig:
    """Configuration for workspace creation."""
    repo_root: str
    layout: LayoutType
    base_directory: str
    hooks_enabled: bool = True
    auto_cleanup: bool = False
    max_workspaces: Optional[int] = None
    hook_timeout: int = 600
```

**1.2 GitCommandExecutor** (`src/infrastructure/platform/git/`)
```python
# Responsibilities:
# - Execute git worktree commands
# - Verify git availability and version
# - Validate worktree integrity
# - List existing worktrees
```

**1.3 WorkspaceManager Interface** 
```python
class WorkspaceManager(ABC):
    @abstractmethod
    def create_workspace(
        self,
        name: str,
        config: WorkspaceConfig,
        run_setup: bool = True,
    ) -> Workspace: ...
    
    @abstractmethod
    def list_workspaces(self, config: WorkspaceConfig) -> list[Workspace]: ...
    
    @abstractmethod
    def remove_workspace(
        self,
        name: str,
        config: WorkspaceConfig,
        force: bool = False,
    ) -> bool: ...
```

#### Exit Criteria
- [ ] Unit tests for all components (90%+ coverage)
- [ ] Integration tests for git commands
- [ ] Can create worktree programmatically
- [ ] Can list existing worktrees
- [ ] Can remove worktrees cleanly

### 3.3 Phase 2: Integration (Weeks 3-4)

#### Objectives
- Implement hook execution with security
- Add layout management
- Create configuration validation

#### Deliverables

**2.1 HookRunner with Security**
```python
class HookRunner(ABC):
    @abstractmethod
    def run_setup(self, workspace_path: str, config: WorkspaceConfig) -> bool: ...
    
    @abstractmethod
    def run_teardown(self, workspace_path: str, config: WorkspaceConfig) -> bool: ...


class HookRunnerImpl(HookRunner):
    """Secure hook execution implementation."""
    
    def __init__(self, config: WorkspaceConfig):
        self._config = config
    
    def _sanitize_path(self, path: str) -> Path:
        # Security validation (see C-02)
        ...
    
    def _execute_hook(self, hook_path: Path, cwd: str) -> bool:
        # Secure execution with timeout
        ...
```

**2.2 LayoutResolver**
```python
class LayoutResolver:
    """Resolves worktree paths based on layout type."""
    
    @staticmethod
    def resolve_path(repo_root: str, branch_name: str, layout: LayoutType) -> str: ...
    
    @staticmethod
    def detect_layout(worktree_path: str, repo_root: str) -> LayoutType: ...
```

**2.3 WorkspaceConfig Validation**
- Validate all paths exist
- Check layout compatibility
- Verify hook timeout bounds

#### Exit Criteria
- [ ] Hooks execute securely with timeout
- [ ] All three layout types work correctly
- [ ] Configuration validation prevents invalid states
- [ ] Security tests pass

### 3.4 Phase 3: UX (Weeks 5-6)

#### Objectives
- CLI command interface
- Auto-detection of current workspace
- Configuration file support

#### Deliverables

**3.1 CLI Commands**
```
fork workspace create <branch>     # Create new workspace
fork workspace list                 # List all workspaces
fork workspace remove <branch>     # Remove workspace
fork workspace detect             # Detect current workspace
fork workspace config <key> <value>  # Manage configuration
```

**3.2 Auto-Detection**
```python
class WorkspaceDetector:
    """Detects workspace from current directory."""
    
    def detect(self, current_path: str | None = None) -> Workspace | None:
        """Detect workspace from $PWD.
        
        Args:
            current_path: Path to check (defaults to cwd)
            
        Returns:
            Workspace if current directory is within a worktree
        """
        ...
```

**3.3 Configuration File**
- `.fork_agent.yaml` in repo root
- Default layout preference
- Hook paths
- Timeout settings

#### Exit Criteria
- [ ] All CLI commands functional
- [ ] Auto-detection works from any worktree directory
- [ ] Configuration file is loaded and respected
- [ ] End-to-end integration tests pass

---

## 4. Component Specifications

This section defines each major component with responsibility, public API, dependencies, and error handling.

### 4.1 WorktreeManager

**Responsibility:** Orchestrates git worktree lifecycle (create, list, remove, merge).

**Public API:**
```python
class WorkspaceManager(ABC):
    def create_workspace(
        self,
        name: str,
        config: WorkspaceConfig,
        run_setup: bool = True,
    ) -> Workspace:
        """Create or reuse a workspace.
        
        Idempotent: returns existing workspace if valid worktree exists.
        
        Raises:
            WorkspaceError: On failure
        """
        ...
    
    def start_workspace(
        self,
        name: str,
        config: WorkspaceConfig,
    ) -> Workspace:
        """Continue work in existing workspace.
        
        Raises:
            WorkspaceNotFoundError: If workspace doesn't exist
        """
        ...
    
    def list_workspaces(self, config: WorkspaceConfig) -> list[Workspace]:
        """List all known workspaces."""
        ...
    
    def remove_workspace(
        self,
        name: str,
        config: WorkspaceConfig,
        force: bool = False,
        run_teardown: bool = True,
    ) -> bool:
        """Remove workspace and optionally its branch.
        
        Raises:
            WorkspaceNotFoundError: If workspace doesn't exist
            WorkspaceNotCleanError: If uncommitted changes and not forced
        """
        ...
    
    def merge_workspace(
        self,
        name: str,
        config: WorkspaceConfig,
        squash: bool = False,
    ) -> bool:
        """Merge workspace branch into main."""
        ...
    
    def detect_workspace(self, config: WorkspaceConfig) -> Workspace | None:
        """Detect current workspace from $PWD."""
        ...
```

**Dependencies:**
- `GitCommandExecutor`: Git operations
- `HookRunner`: Setup/teardown execution
- `LayoutResolver`: Path resolution

**Error Handling:**
- All operations return typed results or raise specific exceptions
- Idempotent operations return existing workspace if valid
- Non-idempotent operations fail if resource doesn't exist

### 4.2 GitCommandExecutor

**Responsibility:** Executes git commands with validation and error handling.

**Public API:**
```python
class GitCommandExecutor:
    def __init__(self) -> None:
        """Initialize with git version verification."""
        ...
    
    def worktree_add(self, path: str, branch: str) -> bool:
        """Create a new worktree."""
        ...
    
    def worktree_remove(self, path: str, force: bool = False) -> bool:
        """Remove a worktree."""
        ...
    
    def worktree_list(self) -> list[dict]:
        """List all worktrees."""
        ...
    
    def worktree_is_valid(self, path: str, branch: str) -> bool:
        """Verify worktree integrity."""
        ...
    
    def branch_create(self, name: str, start_point: str = "HEAD") -> bool:
        """Create a new branch."""
        ...
    
    def branch_delete(self, name: str, force: bool = False) -> bool:
        """Delete a branch."""
        ...
    
    def get_repo_root(self) -> str:
        """Get root of current repository."""
        ...
```

**Dependencies:**
- subprocess (stdlib)

**Error Handling:**
- `GitNotFoundError`: Git not installed
- `GitVersionError`: Version below minimum
- `GitError`: Command execution failure

### 4.3 HookRunner

**Responsibility:** Securely executes setup and teardown hooks.

**Public API:**
```python
class HookRunner(ABC):
    def run_setup(self, workspace_path: str, config: WorkspaceConfig) -> bool:
        """Execute setup hook.
        
        Searches in order:
        1. workspace_path/.cmux/setup
        2. repo_root/.cmux/setup
        """
        ...
    
    def run_teardown(self, workspace_path: str, config: WorkspaceConfig) -> bool:
        """Execute teardown hook."""
        ...
```

**Implementation Requirements:**
- Path sanitization (mandatory)
- Timeout enforcement
- Environment variable filtering
- Output capture

**Dependencies:**
- `WorkspaceConfig`: Configuration and timeout
- subprocess (stdlib)

**Error Handling:**
- `SecurityError`: Invalid path or path traversal attempt
- `HookExecutionError`: Hook script failure
- Graceful degradation if hook not found

### 4.4 LayoutResolver

**Responsibility:** Resolves and detects worktree directory layouts.

**Public API:**
```python
class LayoutResolver:
    @staticmethod
    def resolve_path(repo_root: str, branch_name: str, layout: LayoutType) -> str:
        """Calculate worktree path for given layout."""
        ...
    
    @staticmethod
    def detect_layout(worktree_path: str, repo_root: str) -> LayoutType:
        """Detect layout type from existing worktree."""
        ...
    
    @staticmethod
    def get_default_layout() -> LayoutType:
        """Return default layout (NESTED)."""
        ...
```

**Layout Types:**
```python
class LayoutType(Enum):
    NESTED = auto()       # .worktrees/feature-foo/
    OUTER_NESTED = auto() # ../myrepo.worktrees/feature-foo/
    SIBLING = auto()      # ../myrepo-feature-foo/
```

### 4.5 Workspace Entity

**Location:** `src/application/services/workspace/entities.py`

**Responsibility:** Immutable representation of a workspace.

**Public API:**
```python
@dataclass(frozen=True)
class Workspace:
    workspace_id: str
    name: str
    safe_name: str
    path: str
    layout: LayoutType
    repo_root: str
    created_at: datetime
    last_accessed: datetime | None
    setup_hook_executed: bool
    teardown_hook_executed: bool
    
    @property
    def is_active(self) -> bool:
        """Check if workspace is active."""
        ...
```

**Constraints:**
- Immutable (frozen=True)
- Validated on creation
- No business logic (only data)

---

## 5. Security Requirements

### 5.1 Path Traversal Prevention

All paths must be validated before use:

```python
def _validate_path(self, path: str, base_dir: str) -> Path:
    """Validate path is within expected base directory.
    
    Prevents:
    - Path traversal attacks (../)
    - Symbolic link escapes
    - Invalid characters
    """
    resolved = Path(path).resolve()
    base = Path(base_dir).resolve()
    
    # Check path doesn't escape base
    try:
        resolved.relative_to(base)
    except ValueError:
        raise SecurityError(f"Path escapes base directory: {path}")
    
    return resolved
```

### 5.2 Hook Security

**Requirements:**
1. Hook must be a regular file (no symlinks to outside)
2. Hook must be executable
3. Hook runs in validated working directory
4. Environment is sanitized (no sensitive variables)
5. Timeout is enforced

```python
def _get_sanitized_env(self) -> dict:
    """Get sanitized environment for hook execution.
    
    Removes sensitive variables while preserving safe ones.
    """
    import os
    
    # Start with minimal safe environment
    safe_env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", ""),
        "USER": os.environ.get("USER", ""),
        "LANG": os.environ.get("LANG", "en_US.UTF-8"),
    }
    
    # Explicitly block sensitive variables
    blocked = {
        "GIT_TOKEN", "GH_TOKEN", "GITHUB_TOKEN",
        "SSH_AUTH_SOCK", "SSH_AGENT_PID",
    }
    
    for key in blocked:
        if key in os.environ:
            safe_env[key] = "[REDACTED]"
    
    return safe_env
```

### 5.3 Git Version Requirements

**Minimum:** Git 2.20 (introduced git worktree)

Verification at startup:
```python
def _verify_git_version(self) -> None:
    """Verify git meets minimum version requirement."""
    result = subprocess.run(
        ["git", "--version"],
        capture_output=True,
        text=True,
    )
    
    version = result.stdout.split()[-1]  # "2.43.0"
    major, minor = map(int, version.split(".")[:2])
    
    if major < 2 or (major == 2 and minor < 20):
        raise GitVersionError(
            f"Git 2.20+ required, found {version}"
        )
```

---

## 6. Boundaries

### 6.1 Separation from TerminalSpawner

The workspace management system MUST NOT interfere with terminal spawning:

| Concern | TerminalSpawner | WorkspaceManager |
|---------|-----------------|------------------|
| Terminal sessions | ✅ Manages | ❌ Not allowed |
| Process spawning | ✅ Own implementation | ❌ Delegates |
| Working directory | ✅ Accepts any path | ✅ Creates paths |
| Worktree lifecycle | ❌ Not aware of | ✅ Full control |
| Branch management | ❌ Not aware of | ✅ Full control |

### 6.2 Integration Points

```python
class TerminalSpawnerImpl(TerminalSpawner):
    """Enhanced terminal spawner with workspace support."""
    
    def __init__(self, config: ConfigLoader):
        super().__init__(config)
        # Workspace services injected, not created
        self._workspace_manager: WorkspaceManager = None
    
    def spawn_in_workspace(
        self,
        command: str,
        workspace_name: str,
    ) -> TerminalResult:
        """Spawn terminal in a workspace.
        
        1. Use WorkspaceManager to prepare environment
        2. Pass resulting path to parent spawn() method
        """
        workspace = self._workspace_manager.create_workspace(
            name=workspace_name,
            config=self._workspace_config,
        )
        
        # Delegate actual terminal spawning to parent
        return self.spawn(command, working_directory=workspace.path)
```

### 6.3 No Circular Dependencies

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DEPENDENCY GRAPH                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   domain/                    application/                           │
│   ├── entities/             ├── services/workspace/               │
│   │   └── terminal.py      │   ├── entities.py  ←── NEW         │
│   └── exceptions/          │   ├── exceptions.py ←── NEW         │
│       └── terminal.py      │   ├── workspace_manager.py          │
│                            │   ├── hook_runner.py                │
│   interfaces/              │   └── layout_resolver.py            │
│   └── cli/                 │                                      │
│       └── fork.py          infrastructure/                        │
│                            └── platform/git/                       │
│                                └── git_command_executor.py ← NEW │
│                                                                     │
│   arrows point toward dependencies                                 │
│   domain ← application ← interfaces ← infrastructure              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.4 Domain Layer Purity

The domain layer remains pure and unchanged:

- **No new domain entities**: Workspace entities live in application layer
- **No workspace exceptions in domain**: Exceptions are in application layer
- **Clean boundaries**: Infrastructure (GitCommandExecutor) implements application interfaces

---

## 7. Implementation Checklist

### Pre-Commit (Mandatory)

- [ ] **C-01:** Workspace entities in `src/application/services/workspace/`
- [ ] **C-02:** HookRunnerImpl includes `_sanitize_path()` method
- [ ] **C-03:** GitCommandExecutor includes `git --version` verification
- [ ] **C-04:** All exceptions inherit from base `Exception` class
- [ ] **C-05:** `safe_name` uses regex whitelist: `re.sub(r'[^a-zA-Z0-9_-]', '', name.replace("/", "-"))`

### Pre-Alpha (Mandatory)

- [ ] **M-01:** Timeout configurable via `WorkspaceConfig.hook_timeout` (default 600s)
- [ ] **M-02:** `worktree_is_valid()` implemented for idempotency verification
- [ ] **M-03:** Plan reduced to exactly 3 phases
- [ ] **M-04:** Boundaries documented and enforced

### Post-MVP (Optional)

- [ ] **m-01:** Scope prioritized (core vs nice-to-have)
- [ ] **m-02:** Dependencies documented in package

---

## Appendix A: File Structure

```
src/application/services/workspace/
├── __init__.py
├── entities.py           # Workspace, WorkspaceConfig, LayoutType
├── exceptions.py         # WorkspaceError hierarchy
├── workspace_manager.py  # Abstract interface + implementation
├── hook_runner.py        # HookRunner interface + implementation
└── layout_resolver.py    # Layout resolution utilities

src/infrastructure/platform/git/
├── __init__.py
└── git_command_executor.py  # Git command execution

src/interfaces/cli/
└── workspace_commands.py    # CLI entry points
```

---

## Appendix B: Configuration Schema

```yaml
# .fork_agent.yaml
workspace:
  # Layout strategy: nested | outer-nested | sibling
  layout: nested
  
  # Base directory for worktrees (relative to repo root)
  base_directory: .worktrees
  
  # Enable/disable hooks
  hooks_enabled: true
  
  # Hook timeout in seconds
  hook_timeout: 600
  
  # Auto-cleanup merged branches
  auto_cleanup: false
  
  # Maximum concurrent workspaces
  max_workspaces: 10
```

---

**Document Version:** 3.0 (Final)  
**Status:** CONDITIONAL_APPROVED  
**Last Updated:** 2026-02-22
