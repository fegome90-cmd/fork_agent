# Detailed Implementation Plan - Tmux Integration Project

> **Document Version:** 1.0  
> **Date:** 2026-02-22  
> **Status:** Implementation Guide  
> **Based On:** plan-tmux-integration-FINAL.md

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Phase 1: CORE (Weeks 1-2)](#2-phase-1-core-weeks-1-2)
3. [Phase 2: INTEGRATION (Weeks 3-4)](#3-phase-2-integration-weeks-3-4)
4. [Phase 3: UX (Weeks 5-6)](#4-phase-3-ux-weeks-5-6)
5. [Cross-Phase Dependencies](#5-cross-phase-dependencies)
6. [Risk Assessment](#6-risk-assessment)

---

## 1. Executive Summary

### 1.1 Project Overview

This implementation plan defines the roadmap for integrating git worktree-based workspace management into fork_agent. The project enables isolated workspace environments for multi-agent workflows where each agent works in its own git worktree without interfering with others.

### 1.2 Goals

- **Code Isolation**: Each workspace has its own working directory via git worktree
- **Branch Management**: Automatic branch creation and cleanup
- **Hook Automation**: Setup and teardown scripts for environment initialization
- **Layout Flexibility**: Multiple directory organization strategies
- **Context Awareness**: Auto-detection of current workspace from `$PWD`

### 1.3 Key Metrics

| Metric | Value |
|--------|-------|
| Total Implementation Phases | 3 |
| Estimated Duration | 6 weeks |
| Pre-Commit Fixes | 5 (C-01 through C-05) |
| Pre-Alpha Fixes | 4 (M-01 through M-04) |

### 1.4 Mandatory Fixes Summary

| Code | Description | Phase |
|------|-------------|-------|
| C-01 | Entities in `src/application/services/workspace/` | Phase 1 |
| C-02 | `HookRunnerImpl._sanitize_path()` | Phase 2 |
| C-03 | `GitCommandExecutor` with git version check (>= 2.20) | Phase 1 |
| C-04 | Exceptions inherit from base `Exception` | Phase 1 |
| C-05 | `safe_name` uses regex: `re.sub(r'[^a-zA-Z0-9_-]', '', name.replace("/", "-"))` | Phase 1 |

---

## 2. Phase 1: CORE (Weeks 1-2)

**Objective:** Establish git worktree management foundation with core entities, exceptions, and GitCommandExecutor.

### Subtask 1.1: Set Up Project Structure and Dependencies

**Description:** Create the directory structure for workspace management and configure dependencies.

**Location:** `src/application/services/workspace/` and `src/infrastructure/platform/git/`

**Estimated Complexity:** 2/5

**Estimated Time:** 2 hours

**Dependencies:** None

**Recommended Mode:** code

**Verification Step:**
```bash
# Verify structure exists
ls -la src/application/services/workspace/
ls -la src/infrastructure/platform/git/
```

---

### Subtask 1.2: Create Domain Entities (Workspace, WorkspaceConfig, LayoutType)

**Description:** Implement the core entities in the application layer per C-01 fix requirement.

**Location:** `src/application/services/workspace/entities.py`

**Code Requirements:**
- `LayoutType` enum: NESTED, OUTER_NESTED, SIBLING
- `WorktreeState` enum: ACTIVE, MERGED, REMOVED
- `Workspace` dataclass (frozen=True): workspace_id, name, safe_name, path, layout, repo_root, created_at, last_accessed, setup_hook_executed, teardown_hook_executed
- `WorkspaceConfig` dataclass (frozen=True): repo_root, layout, base_directory, hooks_enabled, auto_cleanup, max_workspaces, hook_timeout

**Estimated Complexity:** 3/5

**Estimated Time:** 4 hours

**Dependencies:** None

**Recommended Mode:** code

**Verification Step:**
```python
# Run entity tests
pytest tests/unit/application/services/workspace/test_entities.py -v
```

---

### Subtask 1.3: Create Exception Hierarchy

**Description:** Implement workspace exceptions per C-04 fix requirement (all inherit from base Exception).

**Location:** `src/application/services/workspace/exceptions.py`

**Code Requirements:**
- `WorkspaceError(Exception)` - Base exception
- `WorkspaceExistsError(WorkspaceError)`
- `WorkspaceNotFoundError(WorkspaceError)`
- `WorkspaceNotCleanError(WorkspaceError)`
- `HookExecutionError(WorkspaceError)`
- `InvalidLayoutError(WorkspaceError)`
- `SecurityError(WorkspaceError)`
- `GitError(WorkspaceError)`
- `GitNotFoundError(GitError)`
- `GitVersionError(GitError)`

**Estimated Complexity:** 2/5

**Estimated Time:** 2 hours

**Dependencies:** None

**Recommended Mode:** code

**Verification Step:**
```python
# Verify exception hierarchy
from src.application.services.workspace.exceptions import WorkspaceError
assert issubclass(WorkspaceError, Exception)
```

---

### Subtask 1.4: Implement GitCommandExecutor with Git Version Check

**Description:** Implement git command executor with C-03 (git >= 2.20 verification) and M-02 (worktree_is_valid).

**Location:** `src/infrastructure/platform/git/git_command_executor.py`

**Code Requirements:**
- `_verify_git_available()` - Verify git is installed
- `_verify_git_version()` - Verify git >= 2.20 (C-03)
- `worktree_add(path, branch)` - Create worktree
- `worktree_remove(path, force)` - Remove worktree
- `worktree_list()` - List all worktrees
- `worktree_is_valid(path, branch)` - Verify worktree integrity (M-02)
- `branch_create(name, start_point)` - Create branch
- `branch_delete(name, force)` - Delete branch
- `get_repo_root()` - Get repository root

**Estimated Complexity:** 4/5

**Estimated Time:** 6 hours

**Dependencies:** 1.3 (exceptions needed for error handling)

**Recommended Mode:** code

**Verification Step:**
```bash
# Verify git version check works
python -c "from src.infrastructure.platform.git.git_command_executor import GitCommandExecutor; GitCommandExecutor()"
```

---

### Subtask 1.5: Implement WorkspaceManager Interface and Implementation

**Description:** Create the WorkspaceManager abstract interface and concrete implementation.

**Location:** `src/application/services/workspace/workspace_manager.py`

**Code Requirements:**
- `WorkspaceManager(ABC)` interface with methods:
  - `create_workspace(name, config, run_setup) -> Workspace`
  - `start_workspace(name, config) -> Workspace`
  - `list_workspaces(config) -> list[Workspace]`
  - `remove_workspace(name, config, force, run_teardown) -> bool`
  - `merge_workspace(name, config, squash) -> bool`
  - `detect_workspace(config) -> Workspace | None`
- `WorkspaceManagerImpl(WorkspaceManager)` implementation

**Estimated Complexity:** 4/5

**Estimated Time:** 8 hours

**Dependencies:** 1.2 (entities), 1.3 (exceptions), 1.4 (GitCommandExecutor)

**Recommended Mode:** code

**Verification Step:**
```python
# Run workspace manager tests
pytest tests/unit/application/services/workspace/test_workspace_manager.py -v
```

---

### Subtask 1.6: Write Unit Tests for Phase 1 Components

**Description:** Achieve 90%+ code coverage for all Phase 1 components.

**Location:** `tests/unit/application/services/workspace/`

**Test Coverage Requirements:**
- Entities: 100%
- Exceptions: 100%
- GitCommandExecutor: 90%+
- WorkspaceManager: 90%+

**Estimated Complexity:** 3/5

**Estimated Time:** 6 hours

**Dependencies:** 1.2, 1.3, 1.4, 1.5 (all Phase 1 components)

**Recommended Mode:** code

**Verification Step:**
```bash
# Run tests with coverage
pytest tests/unit/application/services/workspace/ --cov=src/application/services/workspace --cov-report=term-missing
```

---

### Phase 1 Verification Criteria

| Criterion | Method | Success Condition |
|-----------|--------|-------------------|
| Project structure | Manual inspection | All directories exist |
| Entities created | Unit tests | All entities instantiable |
| Exceptions hierarchy | Import test | All exceptions inherit from Exception |
| GitCommandExecutor | Integration test | Git version verified |
| WorkspaceManager | Unit tests | Core operations functional |
| Test coverage | Coverage report | >= 90% |

---

## 3. Phase 2: INTEGRATION (Weeks 3-4)

**Objective:** Implement hook execution with security, layout management, and idempotency verification.

### Subtask 2.1: Implement HookRunner with Security

**Description:** Implement HookRunner with C-02 (_sanitize_path) and M-01 (configurable timeout).

**Location:** `src/application/services/workspace/hook_runner.py`

**Code Requirements:**
- `HookRunner(ABC)` interface:
  - `run_setup(workspace_path, config) -> bool`
  - `run_teardown(workspace_path, config) -> bool`
- `HookRunnerImpl(HookRunner)` implementation:
  - `_sanitize_path(path) -> Path` - Path traversal prevention (C-02)
  - `_execute_hook(hook_path, cwd) -> bool` - With configurable timeout (M-01)
  - `_get_sanitized_env() -> dict` - Environment sanitization
  - Hook search paths: workspace_path/.cmux/setup, repo_root/.cmux/setup

**Security Requirements:**
- Block path traversal attempts (..)
- Verify path exists and is a file
- Verify executable permissions
- Enforce timeout from config
- Sanitize environment variables

**Estimated Complexity:** 5/5

**Estimated Time:** 8 hours

**Dependencies:** 1.2 (WorkspaceConfig), 1.3 (HookExecutionError, SecurityError)

**Recommended Mode:** code

**Verification Step:**
```python
# Test path sanitization blocks traversal
from src.application.services.workspace.hook_runner import HookRunnerImpl
runner = HookRunnerImpl(config)
try:
    runner._sanitize_path("../etc/passwd")
    assert False, "Should have raised SecurityError"
except SecurityError:
    pass
```

---

### Subtask 2.2: Implement LayoutResolver for Path Resolution

**Description:** Implement layout type resolution for worktree paths.

**Location:** `src/application/services/workspace/layout_resolver.py`

**Code Requirements:**
- `LayoutResolver` class:
  - `resolve_path(repo_root, branch_name, layout) -> str` - Calculate worktree path
  - `detect_layout(worktree_path, repo_root) -> LayoutType` - Detect layout type
  - `get_default_layout() -> LayoutType` - Return NESTED

**Layout Types:**
- NESTED: `.worktrees/<branch>/`
- OUTER_NESTED: `../<repo>.worktrees/<branch>/`
- SIBLING: `../<repo>-<branch>/`

**Estimated Complexity:** 3/5

**Estimated Time:** 4 hours

**Dependencies:** 1.2 (LayoutType enum)

**Recommended Mode:** code

**Verification Step:**
```python
# Test layout resolution
from src.application.services.workspace.layout_resolver import LayoutResolver
from src.application.services.workspace.entities import LayoutType

path = LayoutResolver.resolve_path("/repo", "feature/test", LayoutType.NESTED)
assert ".worktrees/feature-test" in path
```

---

### Subtask 2.3: Add worktree_is_valid() Idempotency Verification

**Description:** Integrate worktree validation into WorkspaceManager for idempotent operations.

**Location:** `src/application/services/workspace/workspace_manager.py` (extend Subtask 1.5)

**Code Requirements:**
- In `create_workspace()`: Check if worktree exists AND is valid before creating
- If worktree exists but invalid: raise `WorkspaceCorruptedError`
- If worktree exists and valid: return existing workspace (idempotent)

**Estimated Complexity:** 3/5

**Estimated Time:** 3 hours

**Dependencies:** 1.4 (worktree_is_valid method), 1.5 (WorkspaceManager)

**Recommended Mode:** code

**Verification Step:**
```python
# Test idempotent creation
workspace1 = manager.create_workspace("feature/test", config)
workspace2 = manager.create_workspace("feature/test", config)
assert workspace1.workspace_id == workspace2.workspace_id
```

---

### Subtask 2.4: Integrate WorkspaceManager with HookRunner

**Description:** Wire HookRunner into WorkspaceManager for setup/teardown execution.

**Location:** `src/application/services/workspace/workspace_manager.py`

**Code Requirements:**
- Inject HookRunner into WorkspaceManagerImpl
- Call `run_setup()` after worktree creation (if run_setup=True)
- Call `run_teardown()` before worktree removal (if run_teardown=True)
- Track hook execution status in Workspace entity

**Estimated Complexity:** 3/5

**Estimated Time:** 4 hours

**Dependencies:** 1.5 (WorkspaceManager), 2.1 (HookRunner)

**Recommended Mode:** code

**Verification Step:**
```python
# Integration test
workspace = manager.create_workspace("feature/test", config, run_setup=True)
assert workspace.setup_hook_executed is True
```

---

### Subtask 2.5: Write Integration Tests

**Description:** Create integration tests for Phase 2 components.

**Location:** `tests/integration/`

**Test Requirements:**
- HookRunner security tests (path traversal, env sanitization)
- LayoutResolver tests (all three layouts)
- Idempotency tests
- End-to-end workspace creation with hooks

**Estimated Complexity:** 3/5

**Estimated Time:** 5 hours

**Dependencies:** 2.1, 2.2, 2.3, 2.4 (all Phase 2 components)

**Recommended Mode:** code

**Verification Step:**
```bash
# Run integration tests
pytest tests/integration/ -v --cov=src/application/services/workspace
```

---

### Phase 2 Verification Criteria

| Criterion | Method | Success Condition |
|-----------|--------|-------------------|
| HookRunner security | Security tests | Path traversal blocked |
| Configurable timeout | Unit test | Timeout from config used |
| LayoutResolver | Unit tests | All layouts resolve correctly |
| Idempotency | Integration test | Valid worktree returns existing |
| Hook integration | Integration test | Setup/teardown executes |
| Integration tests | Test run | All pass |

---

## 4. Phase 3: UX (Weeks 5-6)

**Objective:** CLI commands, auto-detection, and configuration file support.

### Subtask 3.1: Implement CLI Commands

**Description:** Create CLI commands for workspace management.

**Location:** `src/interfaces/cli/workspace_commands.py`

**Command Requirements:**
```
fork workspace create <branch>     # Create new workspace
fork workspace list                 # List all workspaces
fork workspace remove <branch>     # Remove workspace
fork workspace detect             # Detect current workspace
fork workspace config <key> <value>  # Manage configuration
```

**Estimated Complexity:** 3/5

**Estimated Time:** 6 hours

**Dependencies:** 1.5 (WorkspaceManager)

**Recommended Mode:** code

**Verification Step:**
```bash
# Test CLI commands
fork workspace --help
fork workspace list
```

---

### Subtask 3.2: Implement Auto-Detection from $PWD

**Description:** Implement workspace detection from current working directory.

**Location:** `src/application/services/workspace/workspace_detector.py`

**Code Requirements:**
- `WorkspaceDetector` class:
  - `detect(current_path=None) -> Workspace | None`
  - Check if current directory is within a worktree
  - Use `git worktree list` to identify worktrees
  - Match against known workspaces

**Estimated Complexity:** 3/5

**Estimated Time:** 4 hours

**Dependencies:** 1.4 (GitCommandExecutor)

**Recommended Mode:** code

**Verification Step:**
```python
# Test auto-detection
from src.application.services.workspace.workspace_detector import WorkspaceDetector
detector = WorkspaceDetector()
workspace = detector.detect()
# Should return None if not in worktree, or Workspace if in worktree
```

---

### Subtask 3.3: Create Configuration File Support

**Description:** Implement .fork_agent.yaml configuration file loading.

**Location:** `src/infrastructure/config/`

**Configuration Schema:**
```yaml
# .fork_agent.yaml
workspace:
  layout: nested
  base_directory: .worktrees
  hooks_enabled: true
  hook_timeout: 600
  auto_cleanup: false
  max_workspaces: 10
```

**Code Requirements:**
- `ConfigLoader` class:
  - `load_config(repo_root) -> WorkspaceConfig`
  - `save_config(config, repo_root)`
  - Search paths: repo_root/.fork_agent.yaml, ~/.config/fork_agent.yaml

**Estimated Complexity:** 2/5

**Estimated Time:** 3 hours

**Dependencies:** 1.2 (WorkspaceConfig)

**Recommended Mode:** code

**Verification Step:**
```python
# Test config loading
from src.infrastructure.config.config_loader import ConfigLoader
config = ConfigLoader().load_config("/repo")
assert config.layout == LayoutType.NESTED
```

---

### Subtask 3.4: End-to-End Testing

**Description:** Comprehensive E2E tests for the complete workflow.

**Location:** `tests/e2e/`

**Test Scenarios:**
1. Create workspace from CLI
2. List workspaces
3. Auto-detect current workspace
4. Remove workspace via CLI
5. Configuration file loading
6. Hook execution verification

**Estimated Complexity:** 4/5

**Estimated Time:** 6 hours

**Dependencies:** 3.1, 3.2, 3.3 (all Phase 3 components)

**Recommended Mode:** code

**Verification Step:**
```bash
# Run E2E tests
pytest tests/e2e/ -v
```

---

### Phase 3 Verification Criteria

| Criterion | Method | Success Condition |
|-----------|--------|-------------------|
| CLI commands | Manual test | All commands functional |
| Auto-detection | E2E test | Detects from $PWD |
| Config file | E2E test | Loads and applies settings |
| E2E tests | Test run | All pass |

---

## 5. Cross-Phase Dependencies

### Dependency Matrix

| Subtask | Depends On | Blocking |
|---------|------------|----------|
| 1.1 | - | 1.2, 1.3, 1.4, 1.5, 1.6 |
| 1.2 | 1.1 | 1.4, 1.5, 1.6, 2.2 |
| 1.3 | 1.1 | 1.4, 1.5, 1.6 |
| 1.4 | 1.1, 1.3 | 1.5, 1.6, 2.3, 3.2 |
| 1.5 | 1.1, 1.2, 1.3, 1.4 | 1.6, 2.3, 2.4, 3.1 |
| 1.6 | 1.1, 1.2, 1.3, 1.4, 1.5 | - |
| 2.1 | 1.2, 1.3 | 2.4, 2.5 |
| 2.2 | 1.2 | 2.5 |
| 2.3 | 1.4, 1.5 | 2.5 |
| 2.4 | 1.5, 2.1 | 2.5 |
| 2.5 | 1.6, 2.1, 2.2, 2.3, 2.4 | - |
| 3.1 | 1.5 | 3.4 |
| 3.2 | 1.4 | 3.4 |
| 3.3 | 1.2 | 3.4 |
| 3.4 | 3.1, 3.2, 3.3, 2.5 | - |

### Critical Path

```
1.1 → 1.2 → 1.4 → 1.5 → 2.1 → 2.4 → 2.5 → 3.1 → 3.4
        ↓       ↓       ↓       ↓
       1.3    1.5    2.2    2.3
        ↓       ↓       ↓
       1.4    1.6    2.5
```

---

## 6. Risk Assessment

### High Priority Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Git version check fails | Medium | High | Provide clear error message with upgrade instructions |
| Path traversal bypass | Low | Critical | Security-first code review, fuzz testing |
| Worktree corruption | Low | High | M-02 validation before operations |
| Hook timeout issues | Medium | Medium | M-01 configurable timeout, safe defaults |

### Medium Priority Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Layout detection fails | Low | Medium | Graceful fallback to NESTED |
| Config file not found | Medium | Low | Use sensible defaults |
| Branch name conflicts | Medium | Medium | Validate branch names before creation |

### Low Priority Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Test coverage gaps | Low | Low | Automated coverage reporting |
| CLI usability issues | Low | Low | User feedback iterations |

---

## Appendix A: Implementation Schedule

| Week | Phase | Subtasks |
|------|-------|----------|
| 1 | Phase 1 | 1.1, 1.2, 1.3, 1.4 |
| 2 | Phase 1 | 1.5, 1.6 |
| 3 | Phase 2 | 2.1, 2.2, 2.3 |
| 4 | Phase 2 | 2.4, 2.5 |
| 5 | Phase 3 | 3.1, 3.2, 3.3 |
| 6 | Phase 3 | 3.4, Final Verification |

---

## Appendix B: Verification Commands

```bash
# Phase 1 verification
make test-cov TARGET=tests/unit/application/services/workspace/

# Phase 2 verification  
make test TARGET=tests/integration/

# Phase 3 verification
make test TARGET=tests/e2e/

# Full verification
make prePR
```

---

**Document Version:** 1.0  
**Status:** Implementation Guide  
**Last Updated:** 2026-02-22
