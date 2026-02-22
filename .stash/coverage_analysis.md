# Coverage Analysis Report

**Generated:** 2026-02-22  
**Current Coverage:** 92.20%  
**Target Coverage:** 95%  
**Gap:** 2.80 percentage points  

---

## Summary

| File | Current | Missing Lines | Priority |
|------|---------|---------------|----------|
| `src/domain/entities/terminal.py` | 53.19% | 30, 32, 34, 51, 53, 66-71 | **CRITICAL** |
| `src/interfaces/cli/fork.py` | 69.70% | 57-67, 71 | HIGH |
| `src/application/services/terminal/terminal_spawner.py` | 89.04% | 62, 148, 190-196 | MEDIUM |
| `src/infrastructure/persistence/database.py` | 97.06% | 84 | LOW |
| `src/infrastructure/persistence/migrations.py` | 97.47% | 95 | LOW |

---

## Detailed Analysis

### 1. CRITICAL: `src/domain/entities/terminal.py` (53.19%)

**Missing Lines:** 30, 32, 34, 51, 53, 66-71

#### Gap 1: Type Validation in `TerminalResult.__post_init__`
```python
# Lines 29-34
def __post_init__(self) -> None:
    if not isinstance(self.success, bool):
        raise TypeError("success debe ser un booleano")  # Line 30 - NOT COVERED
    if not isinstance(self.output, str):
        raise TypeError("output debe ser un string")     # Line 32 - NOT COVERED
    if not isinstance(self.exit_code, int):
        raise TypeError("exit_code debe ser un entero")  # Line 34 - NOT COVERED
```

**Missing Tests:**
- `test_terminal_result_invalid_success_type` - pass non-bool `success`
- `test_terminal_result_invalid_output_type` - pass non-str `output`
- `test_terminal_result_invalid_exit_code_type` - pass non-int `exit_code`

#### Gap 2: Type Validation in `TerminalConfig.__post_init__`
```python
# Lines 50-53
if self.terminal is not None and not isinstance(self.terminal, str):
    raise TypeError("terminal debe ser un string o None")  # Line 51 - NOT COVERED
if not isinstance(self.platform, PlatformType):
    raise TypeError("platform debe ser un PlatformType")   # Line 53 - NOT COVERED
```

**Missing Tests:**
- `test_terminal_config_invalid_terminal_type` - pass non-str/non-None `terminal`
- `test_terminal_config_invalid_platform_type` - pass non-PlatformType `platform`

#### Gap 3: Entire `TerminalInfo` Class Untested (Lines 56-71)
```python
@dataclass(frozen=True)
class TerminalInfo:
    """Información sobre el ejecutable de terminal encontrado."""
    name: str
    path: str | None
    is_available: bool

    def __post_init__(self) -> None:
        if not isinstance(self.name, str):
            raise TypeError("name debe ser un string")
        if self.path is not None and not isinstance(self.path, str):
            raise TypeError("path debe ser un string o None")
        if not isinstance(self.is_available, bool):
            raise TypeError("is_available debe ser un booleano")
```

**Missing Tests:**
- `test_create_terminal_info_with_path`
- `test_create_terminal_info_without_path`
- `test_terminal_info_immutability`
- `test_terminal_info_invalid_name_type`
- `test_terminal_info_invalid_path_type`
- `test_terminal_info_invalid_is_available_type`

---

### 2. HIGH: `src/interfaces/cli/fork.py` (69.70%)

**Missing Lines:** 57-67, 71

#### Gap: `run_cli()` Function Untested
```python
# Lines 57-67
def run_cli() -> int:
    from src.application.services.terminal.platform_detector import PlatformDetectorImpl
    from src.application.services.terminal.terminal_spawner import TerminalSpawnerImpl
    from src.application.use_cases.fork_terminal import fork_terminal_use_case
    
    platform_detector = PlatformDetectorImpl()
    terminal_spawner = TerminalSpawnerImpl()
    fork_terminal = fork_terminal_use_case(platform_detector, terminal_spawner)
    
    cli = create_fork_cli(fork_terminal)
    return cli()
```

**Missing Tests:**
- `test_run_cli_returns_int` - integration test for `run_cli()`
- Note: Line 71 (`if __name__ == "__main__"`) is typically excluded from coverage as it's the script entry point.

---

### 3. MEDIUM: `src/application/services/terminal/terminal_spawner.py` (89.04%)

**Missing Lines:** 62, 148, 190-196

#### Gap 1: Unsupported Platform Branch (Line 62)
```python
# Lines 60-62
elif platform == "Linux":
    return self._spawn_linux(command)
else:
    raise TerminalNotFoundError(platform, [])  # Line 62 - NOT COVERED
```

**Missing Test:**
- `test_spawn_unsupported_platform` - pass a platform value that isn't Darwin/Windows/Linux

#### Gap 2: tmux Fallback Branch (Line 148)
```python
# Lines 146-150
if shutil.which("tmux"):
    return self._spawn_with_tmux(command)  # Line 148 - NOT COVERED

raise TerminalNotFoundError("Linux", LINUX_TERMINALS)
```

**Missing Test:**
- `test_spawn_linux_fallback_to_tmux` - mock `shutil.which` to return False for terminals but True for tmux

#### Gap 3: `_spawn_with_tmux` Method (Lines 180-200)
```python
def _spawn_with_tmux(self, command: str) -> TerminalResult:
    sanitized_command = command.replace("'", "'\\''")
    session_name = f"fork_term_{str(uuid.uuid4())[:8]}"
    
    subprocess.run(
        ["tmux", "new-session", "-d", "-s", session_name, f"{sanitized_command}; read -p 'Press enter to close...'"]
    )
    return TerminalResult(
        success=True,
        output=f"New terminal session opened in tmux (session: {session_name}).",
        exit_code=0,
    )
```

**Missing Test:**
- Covered by tmux fallback test above

---

### 4. LOW: `src/infrastructure/persistence/database.py` (97.06%)

**Missing Line:** 84

```python
# Lines 82-84
def __exit__(self, ...):
    if self._connection is None:
        return  # Line 84 - NOT COVERED
```

**Analysis:** This is a defensive check. In normal usage, `__exit__` is only called after `__enter__` has set `_connection`. This line is extremely difficult to test without abusing the class internals.

**Recommendation:** Consider using `# pragma: no cover` comment for this line, or leave as-is given the near-100% coverage.

---

### 5. LOW: `src/infrastructure/persistence/migrations.py` (97.47%)

**Missing Line:** 95

```python
# Lines 93-95
def load_migrations(migrations_dir: Path) -> list[Migration]:
    if not migrations_dir.exists():
        return []  # Line 95 - NOT COVERED
```

**Missing Test:**
- `test_load_migrations_nonexistent_directory` - pass a path that doesn't exist

---

## Suggested Tests (Priority Order)

### Priority 1: terminal.py (Biggest Impact)

Add to `tests/unit/domain/test_entities.py`:

```python
import pytest
from src.domain.entities.terminal import TerminalResult, TerminalConfig, TerminalInfo, PlatformType


class TestTerminalResultValidation:
    """Tests for TerminalResult type validation."""

    def test_terminal_result_invalid_success_type(self) -> None:
        """Test that non-bool success raises TypeError."""
        with pytest.raises(TypeError, match="success debe ser un booleano"):
            TerminalResult(success="yes", output="test", exit_code=0)  # type: ignore

    def test_terminal_result_invalid_output_type(self) -> None:
        """Test that non-str output raises TypeError."""
        with pytest.raises(TypeError, match="output debe ser un string"):
            TerminalResult(success=True, output=123, exit_code=0)  # type: ignore

    def test_terminal_result_invalid_exit_code_type(self) -> None:
        """Test that non-int exit_code raises TypeError."""
        with pytest.raises(TypeError, match="exit_code debe ser un entero"):
            TerminalResult(success=True, output="test", exit_code="0")  # type: ignore


class TestTerminalConfigValidation:
    """Tests for TerminalConfig type validation."""

    def test_terminal_config_invalid_terminal_type(self) -> None:
        """Test that non-str/non-None terminal raises TypeError."""
        with pytest.raises(TypeError, match="terminal debe ser un string o None"):
            TerminalConfig(terminal=123, platform=PlatformType.LINUX)  # type: ignore

    def test_terminal_config_invalid_platform_type(self) -> None:
        """Test that non-PlatformType platform raises TypeError."""
        with pytest.raises(TypeError, match="platform debe ser un PlatformType"):
            TerminalConfig(terminal="xterm", platform="Linux")  # type: ignore


class TestTerminalInfo:
    """Tests for TerminalInfo entity."""

    def test_create_terminal_info_with_path(self) -> None:
        """Test creating terminal info with a path."""
        info = TerminalInfo(name="gnome-terminal", path="/usr/bin/gnome-terminal", is_available=True)
        assert info.name == "gnome-terminal"
        assert info.path == "/usr/bin/gnome-terminal"
        assert info.is_available is True

    def test_create_terminal_info_without_path(self) -> None:
        """Test creating terminal info without a path."""
        info = TerminalInfo(name="unknown-terminal", path=None, is_available=False)
        assert info.name == "unknown-terminal"
        assert info.path is None
        assert info.is_available is False

    def test_terminal_info_immutability(self) -> None:
        """Test that TerminalInfo is immutable."""
        info = TerminalInfo(name="test", path=None, is_available=True)
        with pytest.raises(Exception):
            info.name = "changed"  # type: ignore

    def test_terminal_info_invalid_name_type(self) -> None:
        """Test that non-str name raises TypeError."""
        with pytest.raises(TypeError, match="name debe ser un string"):
            TerminalInfo(name=123, path=None, is_available=True)  # type: ignore

    def test_terminal_info_invalid_path_type(self) -> None:
        """Test that non-str/non-None path raises TypeError."""
        with pytest.raises(TypeError, match="path debe ser un string o None"):
            TerminalInfo(name="test", path=123, is_available=True)  # type: ignore

    def test_terminal_info_invalid_is_available_type(self) -> None:
        """Test that non-bool is_available raises TypeError."""
        with pytest.raises(TypeError, match="is_available debe ser un booleano"):
            TerminalInfo(name="test", path=None, is_available="yes")  # type: ignore
```

### Priority 2: migrations.py

Add to `tests/unit/infrastructure/test_migrations.py`:

```python
def test_load_migrations_nonexistent_directory(self, tmp_path: Path) -> None:
    """Test that nonexistent directory returns empty list."""
    nonexistent = tmp_path / "does_not_exist"
    result = load_migrations(nonexistent)
    assert result == []
```

### Priority 3: terminal_spawner.py

Fix existing failing tests and add:

```python
def test_spawn_unsupported_platform(self) -> None:
    """Test that unsupported platform raises TerminalNotFoundError."""
    from unittest.mock import MagicMock
    from src.domain.entities.terminal import TerminalConfig, PlatformType
    
    spawner = TerminalSpawnerImpl()
    config = MagicMock()
    config.platform.value = "FreeBSD"  # Unsupported platform
    
    with pytest.raises(TerminalNotFoundError):
        spawner.spawn("echo test", config)
```

### Priority 4: fork.py

Add integration test:

```python
def test_run_cli_returns_int(self) -> None:
    """Test that run_cli returns an integer."""
    from src.interfaces.cli.fork import run_cli
    from unittest.mock import patch
    
    with patch("sys.argv", ["fork", "echo", "test"]):
        result = run_cli()
        assert isinstance(result, int)
```

---

## Estimated Impact

| Tests Added | Coverage Gain | New Total |
|-------------|---------------|-----------|
| TerminalInfo class (6 tests) | +8% | ~61% on terminal.py |
| Type validations (5 tests) | +20% | ~81% on terminal.py |
| migrations.py (1 test) | +0.5% | ~98% on migrations.py |
| terminal_spawner.py (1-2 tests) | +5% | ~94% on terminal_spawner.py |
| fork.py (1 test) | +15% | ~85% on fork.py |

**Expected final coverage:** ~95%+

---

## Pre-existing Test Failures

The following test failures exist in the codebase and are unrelated to coverage:

1. **Platform Detector Tests** - Return `PlatformType` enum instead of string
2. **Terminal Spawner Tests** - Mock configuration issues for tmux fallback
3. **Config Test** - Environment variable mismatch

These should be fixed separately as they are test bugs, not coverage issues.
