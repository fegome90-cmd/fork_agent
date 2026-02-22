# Tmux System Integration Plan v2 — cmux Enhanced

> **Versión:** 2.0 (cmux Enhanced)
> **Base:** Tmux-Orchestrator + cmux integration
> **Goal:** Implementar un sistema de orquestación tmux estable con capacidades de git worktree, hooks personalizados, y autocompletado.

---

## 1. Análisis de Ingeniería de cmux

### 1.1 Killer Features Extraídas

| Feature | Descripción | Valor para fork_agent |
|---------|-------------|----------------------|
| **Git Worktree Lifecycle** | Gestión completa de worktrees para aislar agentes | Aislación de sesiones de trabajo |
| **Multi-layout Support** | nested, outer-nested, sibling layouts | Flexibilidad en estructura de directorios |
| **Setup/Teardown Hooks** | Scripts de inicialización y limpieza por proyecto | Automatización de setup por entorno |
| **Auto-detection** | Detecta worktree actual desde `$PWD` | Context-awareness sin args |
| **Idempotent Operations** | `cmux new` reutiliza worktrees existentes | Sin errores por ejecuciones repetidas |
| **Branch Sanitization** | `feature/foo` → `feature-foo` | Nombres seguros para directorios |
| **Tab Completion** | Completado automático para bash/zsh | DX mejorado |
| **Auto-update** | Verificación de versiones en background | Mantenimiento automático |
| **Claude Integration** | Lanza Claude Code en worktrees | Integración con agente AI |

### 1.2 Patrones de Diseño en cmux

```bash
# Estructura de funciones
cmux()              # Dispatcher público
_cmux_<cmd>()       # Funciones privadas: new, start, cd, ls, merge, rm, init
_cmux_helper_*()    # Helpers: repo_root, safe_name, worktree_dir, spinner

# Convenciones
- 2-space indentación
- Prefijo _cmux_ para funciones internas
- Zsh compatibility: setopt localoptions nomonitor
- Sin set -e (es sourced, no ejecutado)
- QA obligatorio: source + test antes de considerar tarea completa
```

---

## 2. Gap Analysis: fork_agent vs cmux

### 2.1 Lo que fork_agent NO tiene actualmente

| Gap | cmux lo resuelve | Impacto |
|-----|------------------|---------|
| **Aislamiento de entornos** | Git worktrees | Crítico - permite múltiples agentes en mismo repo |
| **Setup hooks** | `.cmux/setup` script | Alto - automatización de dependencias |
| **Teardown hooks** | `.cmux/teardown` script | Medio - limpieza de recursos |
| **Auto-detección de contexto** | Detecta worktree desde `$PWD` | Alto - UX sin args obligatorios |
| **Idempotencia** | Reutiliza worktrees existentes | Alto - operaciones seguras |
| **Layouts configurables** | nested/outer-nested/sibling | Medio - flexibilidad organizativa |
| **Tab completion** | bash/zsh built-in | Medio - DX mejorado |
| **Branch sanitization** | Sanitiza nombres para directorios | Bajo - naming seguro |

### 2.2 Lo que cmux NO tiene (y fork_agent sí)

| fork_agent tiene | Beneficio |
|------------------|-----------|
| Clean Architecture | Mantenibilidad, testabilidad |
| Type hints (mypy) | Type safety |
| Frozen dataclasses | Inmutabilidad |
| Dependency Injection | Testabilidad, extensibilidad |
| Test coverage (90%+) | Confiabilidad |
| Multi-platform (macOS/Linux/Windows) | Soporte amplio |

---

## 3. Propuesta de Actualización Arquitectónica

### 3.1 Nuevas Entidades de Dominio

#### Workspace Entity (Nuevo)

```python
"""Workspace domain entity - representa un entorno de trabajo aislado."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Sequence
from enum import Enum, auto


class LayoutType(Enum):
    """Tipos de layout para worktrees."""
    NESTED = auto()       # .worktrees/<branch>/
    OUTER_NESTED = auto() # ../<repo>.worktrees/<branch>/
    SIBLING = auto()      # ../<repo>-<branch>/


class WorktreeState(Enum):
    """Estados de un worktree."""
    ACTIVE = auto()
    MERGED = auto()
    REMOVED = auto()


@dataclass(frozen=True)
class Workspace:
    """Entidad que representa un workspace aislado (git worktree).
    
    Equivalente a lo que cmux llama "worktree" pero con validación
    de dominio y tipos estrictos.
    """
    workspace_id: str
    name: str                          # Branch name original
    safe_name: str                     # Branch sanitized (feature/foo → feature-foo)
    path: str                          # Ruta absoluta del worktree
    layout: LayoutType
    repo_root: str                     # Ruta al repo principal
    created_at: datetime
    last_accessed: Optional[datetime] = None
    setup_hook_executed: bool = False
    teardown_hook_executed: bool = False
    
    def __post_init__(self) -> None:
        """Validar estado del workspace."""
        if not self.workspace_id:
            raise ValueError("workspace_id cannot be empty")
        if not self.name:
            raise ValueError("name cannot be empty")
        if not self.path:
            raise ValueError("path cannot be empty")
        if self.safe_name != self._sanitize(self.name):
            raise ValueError(f"safe_name '{self.safe_name}' doesn't match sanitized '{self.name}'")
    
    @staticmethod
    def _sanitize(name: str) -> str:
        """Sanitizar nombre para directorio: feature/foo → feature-foo"""
        return name.replace("/", "-")
    
    @property
    def is_active(self) -> bool:
        """Check if workspace is active (not merged/removed)."""
        return True  # State management handled by service


@dataclass(frozen=True)
class WorkspaceHook:
    """Configuración de hooks para un workspace."""
    workspace_id: str
    setup_path: Optional[str] = None
    teardown_path: Optional[str] = None
    environment: tuple[tuple[str, str], ...] = ()  # Env vars as (key, value) pairs
    
    def __post_init__(self) -> None:
        """Validate hook paths exist."""
        # Validation deferred to application layer


@dataclass(frozen=True)
class WorkspaceConfig:
    """Configuración global de workspaces para un proyecto."""
    repo_root: str
    layout: LayoutType
    base_directory: str
    hooks_enabled: bool = True
    auto_cleanup: bool = False
    max_workspaces: Optional[int] = None
```

### 3.2 Nuevos Servicios de Aplicación

#### WorkspaceManager (Nuevo)

```python
"""Servicio para gestión de workspaces (git worktrees)."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Sequence

from src.domain.entities.workspace import Workspace, WorkspaceConfig, LayoutType


class WorkspaceManager(ABC):
    """Interfaz abstracta para gestión de workspaces.
    
    Equivalente a la lógica principal de cmux pero en Python
    con Clean Architecture.
    """
    
    @abstractmethod
    def create_workspace(
        self,
        name: str,
        config: WorkspaceConfig,
        run_setup: bool = True,
    ) -> Workspace:
        """Crear nuevo workspace (worktree + branch).
        
        Es idempotente: si el worktree existe, lo reutiliza.
        
        Args:
            name: Nombre de la rama (ej: feature/auth)
            config: Configuración del workspace
            run_setup: Si ejecutar hook de setup
            
        Returns:
            Workspace creado o reutilizado
            
        Raises:
            WorkspaceExistsError: Si el workspace ya existe (idempotent behavior)
            GitError: Si falla el comando git
        """
        ...
    
    @abstractmethod
    def start_workspace(
        self,
        name: str,
        config: WorkspaceConfig,
        prompt: Optional[str] = None,
    ) -> Workspace:
        """Continuar trabajo en un workspace existente.
        
        Args:
            name: Nombre de la rama
            config: Configuración del workspace
            prompt: Prompt inicial para el agente
            
        Returns:
            Workspace encontrado
            
        Raises:
            WorkspaceNotFoundError: Si el workspace no existe
        """
        ...
    
    @abstractmethod
    def list_workspaces(self, config: WorkspaceConfig) -> Sequence[Workspace]:
        """Listar todos los workspaces activos."""
        ...
    
    @abstractmethod
    def remove_workspace(
        self,
        name: str,
        config: WorkspaceConfig,
        force: bool = False,
        run_teardown: bool = True,
    ) -> bool:
        """Eliminar workspace y su rama.
        
        Args:
            name: Nombre del workspace
            config: Configuración
            force: Forzar eliminación aunque haya cambios sin commit
            run_teardown: Si ejecutar hook de teardown
            
        Returns:
            True si se eliminó correctamente
        """
        ...
    
    @abstractmethod
    def merge_workspace(
        self,
        name: str,
        config: WorkspaceConfig,
        squash: bool = False,
    ) -> bool:
        """Hacer merge del workspace al repo principal.
        
        Args:
            name: Nombre del workspace
            config: Configuración
            squash: Si hacer squash merge
            
        Returns:
            True si el merge fue exitoso
        """
        ...
    
    @abstractmethod
    def detect_workspace(self, config: WorkspaceConfig) -> Optional[Workspace]:
        """Detectar workspace actual desde $PWD.
        
        Returns:
            Workspace actual o None si no hay trabajo en un workspace
        """
        ...


class WorkspaceManagerImpl(WorkspaceManager):
    """Implementación de WorkspaceManager usando git worktree."""
    
    def __init__(
        self,
        git_executor: 'GitCommandExecutor',
        hook_runner: 'HookRunner',
    ):
        self._git = git_executor
        self._hooks = hook_runner
    
    def create_workspace(
        self,
        name: str,
        config: WorkspaceConfig,
        run_setup: bool = True,
    ) -> Workspace:
        safe_name = self._sanitize(name)
        worktree_path = self._resolve_path(config, safe_name)
        
        # Idempotent: check if exists
        if Path(worktree_path).exists():
            workspace = self._load_workspace(name, config)
            return workspace
        
        # Create worktree + branch
        self._git.worktree_add(worktree_path, name)
        
        # Run setup hook
        if run_setup:
            self._hooks.run_setup(worktree_path, config)
        
        return Workspace(
            workspace_id=str(uuid.uuid4()),
            name=name,
            safe_name=safe_name,
            path=worktree_path,
            layout=config.layout,
            repo_root=config.repo_root,
            created_at=datetime.now(),
            setup_hook_executed=run_setup,
        )
    
    # ... implementation details
```

#### HookRunner (Nuevo)

```python
"""Servicio para ejecutar hooks de setup/teardown."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class HookRunner(ABC):
    """Interfaz abstracta para ejecución de hooks."""
    
    @abstractmethod
    def run_setup(self, workspace_path: str, config: 'WorkspaceConfig') -> bool:
        """Ejecutar hook de setup.
        
        Busca .cmux/setup en:
        1. workspace_path/.cmux/setup
        2. repo_root/.cmux/setup
        """
        ...
    
    @abstractmethod
    def run_teardown(self, workspace_path: str, config: 'WorkspaceConfig') -> bool:
        """Ejecutar hook de teardown."""
        ...


class HookRunnerImpl(HookRunner):
    """Implementación de HookRunner."""
    
    def run_setup(self, workspace_path: str, config: 'WorkspaceConfig') -> bool:
        # Check local .cmux/setup
        local_hook = Path(workspace_path) / ".cmux" / "setup"
        repo_hook = Path(config.repo_root) / ".cmux" / "setup"
        
        hook_to_run = None
        if local_hook.exists() and local_hook.is_file():
            hook_to_run = local_hook
        elif repo_hook.exists() and repo_hook.is_file():
            hook_to_run = repo_hook
        
        if hook_to_run:
            return self._execute_hook(hook_to_run, workspace_path)
        
        return False
    
    def _execute_hook(self, hook_path: Path, cwd: str) -> bool:
        """Ejecutar hook con manejo de errores."""
        import subprocess
        try:
            result = subprocess.run(
                [str(hook_path)],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 min timeout
            )
            return result.returncode == 0
        except Exception:
            return False
```

#### LayoutResolver (Nuevo)

```python
"""Servicio para resolver paths de worktrees según layout."""

from src.domain.entities.workspace import LayoutType


class LayoutResolver:
    """Resuelve paths de worktrees según configuración de layout."""
    
    @staticmethod
    def resolve_path(repo_root: str, branch_name: str, layout: LayoutType) -> str:
        """Resolver path del worktree según layout.
        
        Args:
            repo_root: Ruta al repo principal
            branch_name: Nombre de la rama (sanitized o no)
            layout: Tipo de layout
            
        Returns:
            Ruta absoluta al worktree
        """
        import os
        
        safe_name = branch_name.replace("/", "-")
        
        match layout:
            case LayoutType.OUTER_NESTED:
                repo_name = os.path.basename(repo_root)
                parent = os.path.dirname(repo_root)
                base = os.path.join(parent, f"{repo_name}.worktrees")
                return os.path.join(base, safe_name)
            
            case LayoutType.SIBLING:
                repo_name = os.path.basename(repo_root)
                parent = os.path.dirname(repo_root)
                return os.path.join(parent, f"{repo_name}-{safe_name}")
            
            case LayoutType.NESTED:
            default:
                return os.path.join(repo_root, ".worktrees", safe_name)
    
    @staticmethod
    def detect_layout(worktree_path: str, repo_root: str) -> LayoutType:
        """Detectar layout desde un path de worktree."""
        import os
        
        worktree_path = os.path.abspath(worktree_path)
        repo_root = os.path.abspath(repo_root)
        
        # Check outer-nested
        if ".worktrees/" in worktree_path and repo_root not in worktree_path:
            if os.path.basename(repo_root) + ".worktrees" in worktree_path:
                return LayoutType.OUTER_NESTED
        
        # Check sibling
        repo_name = os.path.basename(repo_root)
        if worktree_path.startswith(os.path.dirname(repo_root)) and \
           f"{repo_name}-" in os.path.basename(worktree_path):
            return LayoutType.SIBLING
        
        # Default: nested
        return LayoutType.NESTED
```

### 3.3 Nuevas Excepciones de Dominio

```python
"""Workspace-specific exceptions."""

from src.domain.exceptions.tmux import TmuxError


class WorkspaceError(TmuxError):
    """Base exception for workspace operations."""
    pass


class WorkspaceExistsError(WorkspaceError):
    """Raised when workspace already exists."""
    
    def __init__(self, name: str, path: str):
        message = f"Workspace '{name}' already exists at {path}"
        super().__init__(message, {"name": name, "path": path})


class WorkspaceNotFoundError(WorkspaceError):
    """Raised when workspace doesn't exist."""
    
    def __init__(self, name: str):
        message = f"Workspace '{name}' not found"
        super().__init__(message, {"name": name})


class WorkspaceNotCleanError(WorkspaceError):
    """Raised when workspace has uncommitted changes."""
    
    def __init__(self, name: str, path: str):
        message = f"Workspace '{name}' at {path} has uncommitted changes"
        super().__init__(message, {"name": name, "path": path})


class HookExecutionError(WorkspaceError):
    """Raised when hook execution fails."""
    
    def __init__(self, hook_path: str, exit_code: int):
        message = f"Hook '{hook_path}' failed with exit code {exit_code}"
        super().__init__(message, {"hook_path": hook_path, "exit_code": exit_code})


class InvalidLayoutError(WorkspaceError):
    """Raised when layout configuration is invalid."""
    
    def __init__(self, layout: str):
        message = f"Invalid layout type: {layout}"
        super().__init__(message, {"layout": layout})
```

### 3.4 Adaptadores e Inyección de Dependencias

#### Actualización de terminal_spawner.py

```python
"""Enhanced TerminalSpawner with workspace support."""

from src.application.services.tmux.workspace_manager import (
    WorkspaceManager,
    WorkspaceManagerImpl,
)
from src.application.services.tmux.hook_runner import HookRunner, HookRunnerImpl
from src.infrastructure.platform.git.git_command_executor import GitCommandExecutor
from src.infrastructure.config.config import ConfigLoader


class TerminalSpawnerImpl(TerminalSpawner):
    """Enhanced terminal spawner with workspace management."""
    
    def __init__(self, config: ConfigLoader):
        super().__init__(config)
        # New dependencies for workspace management
        self._git_executor = GitCommandExecutor()
        self._hook_runner = HookRunnerImpl()
        self._workspace_manager = WorkspaceManagerImpl(
            self._git_executor,
            self._hook_runner,
        )
    
    def spawn_with_workspace(
        self,
        command: str,
        workspace_name: str,
        layout: LayoutType = LayoutType.NESTED,
        run_setup: bool = True,
    ) -> TerminalResult:
        """Spawn terminal in a workspace.
        
        Creates or reuses a workspace (git worktree) and spawns
        a terminal session within it.
        """
        config = self._config.load()
        repo_root = self._git_executor.get_repo_root()
        
        workspace_config = WorkspaceConfig(
            repo_root=repo_root,
            layout=layout,
            base_directory=self._resolve_workspace_base(repo_root, layout),
        )
        
        # Create or reuse workspace (idempotent)
        workspace = self._workspace_manager.create_workspace(
            name=workspace_name,
            config=workspace_config,
            run_setup=run_setup,
        )
        
        # Spawn terminal in workspace
        terminal_config = TerminalConfig(
            platform=PlatformType.LINUX,  # or detect
            terminal="tmux",
            working_directory=workspace.path,
        )
        
        return self.spawn(command, terminal_config)
```

#### DI Container Configuration

```python
"""Dependency injection configuration for workspace services."""

from src.infrastructure.config.config import ConfigLoader
from src.infrastructure.platform.git.git_command_executor import GitCommandExecutor
from src.application.services.tmux.workspace_manager import (
    WorkspaceManager,
    WorkspaceManagerImpl,
)
from src.application.services.tmux.hook_runner import HookRunner, HookRunnerImpl
from src.application.services.tmux.layout_resolver import LayoutResolver


def create_workspace_services(config: ConfigLoader) -> dict:
    """Factory function for workspace services."""
    
    git_executor = GitCommandExecutor()
    hook_runner = HookRunnerImpl()
    workspace_manager = WorkspaceManagerImpl(git_executor, hook_runner)
    layout_resolver = LayoutResolver()
    
    return {
        "workspace_manager": workspace_manager,
        "hook_runner": hook_runner,
        "layout_resolver": layout_resolver,
        "git_executor": git_executor,
    }
```

---

## 4. Actualización del Executive Summary

### 4.1 Key Deliverables (Versión Actualizada)

| # | Deliverable | Descripción | Prioridad |
|---|-------------|-------------|-----------|
| 1 | **Domain Entities** | TmuxSession, TmuxWindow, TmuxMessage, TmuxSnapshot, **Workspace**, **WorkspaceConfig** | Alta |
| 2 | **TmuxSessionManager** | Gestión de sesiones tmux (list, create, kill, find) | Alta |
| 3 | **TmuxWindowManager** | Gestión de ventanas (list, capture, send, rename) | Alta |
| 4 | **AgentMessenger** | Comunicación entre agentes via tmux | Media |
| 5 | **SchedulerService** | Programación de tareas con preservación de contexto | Media |
| 6 | **MonitoringService** | Snapshots y monitoreo de estado | Media |
| 7 | **WorkspaceManager** | Gestión de git worktrees (cmux-style) | **Alta** |
| 8 | **HookRunner** | Ejecución de setup/teardown hooks | **Alta** |
| 9 | **LayoutResolver** | Resolución de paths según layout | **Media** |
| 10 | **CLI Commands** | `fork tmux` + `fork workspace` commands | Alta |
| 11 | **Tab Completion** | Auto-completado bash/zsh para CLI | Baja |
| 12 | **Test Coverage** | 90%+ coverage con pytest | Alta |

### 4.2 Nuevos CLI Commands

```bash
# Workspace commands (cmux-style)
fork workspace new <branch>              # Create worktree + branch, run setup, launch
fork workspace start <branch>            # Continue in existing worktree
fork workspace cd [branch]               # cd into worktree (no args = repo root)
fork workspace ls                        # List active worktrees
fork workspace merge [branch] [--squash] # Merge worktree branch to main
fork workspace rm [branch] [--force]     # Remove worktree + branch
fork workspace init                      # Generate .cmux/setup hook
fork workspace config                     # View/set worktree layout config

# Tmux commands (enhanced)
fork tmux list                           # List tmux sessions
fork tmux create --name                  # Create tmux session
fork tmux send --session --command       # Send command to session
fork tmux capture --session              # Capture session output
```

---

## 5. Fases de Implementación (Actualizadas)

### Fase 1: Core Tmux Operations
- Domain entities: TmuxSession, TmuxWindow, TmuxMessage, TmuxSnapshot
- TmuxSessionManager, TmuxWindowManager
- Basic CLI commands
- Tests (90%+)

### Fase 2: Workspace Management (NUEVO)
- **Workspace entity and config**
- **WorkspaceManager implementation**
- **HookRunner implementation**
- **LayoutResolver**
- Workspace CLI commands
- Integration with terminal_spawner.py

### Fase 3: Agent Messaging
- AgentMessenger service
- Messaging CLI commands
- Tests

### Fase 4: Scheduling and Automation
- SchedulerService
- Scheduling CLI commands
- Tests

### Fase 5: Monitoring and Observability
- MonitoringService
- Snapshot functionality
- Tests

### Fase 6: DX Enhancements (NUEVO)
- Tab completion (bash/zsh)
- Auto-update mechanism
- Workspace detection from $PWD
- Idempotent operation validation

---

## 6. Comparación de Arquitecturas

```
 fork_agent actual:              fork_agent v2 (cmux enhanced):
 ┌─────────────────┐            ┌─────────────────────────────────┐
 │ terminal.py     │            │ terminal.py                     │
 │ terminal_spawner│            │ terminal_spawner (enhanced)     │
 └─────────────────┘            │   ├─→ workspace_manager          │
                                │   ├─→ hook_runner               │
                                │   └─→ layout_resolver           │
                                └─────────────────────────────────┘
                                        │
     ┌─────────────────────────┐        │        ┌────────────────────┐
     │ application/services/   │        │        │ application/       │
     │   terminal/             │               │   services/tmux/   │
     │   ├─ session_manager   │               │   ├─ workspace_mgr  │
     │   └─ window_manager   │               │   ├─ hook_runner    │
     └─────────────────────────┘               │   ├─ session_mgr   │
                                └───────────────┤   ├─ window_mgr   │
                                                │   ├─ messenger    │
                                                │   └─ scheduler   │
                                                └────────────────────┘
                                        │
     ┌─────────────────────────┐        │        ┌────────────────────┐
     │ domain/entities/        │        │        │ domain/entities/   │
     │   ├─ terminal.py       │        │        │   ├─ tmux.py       │
     │   └─ (others)          │        │        │   ├─ workspace.py  │ ← NUEVO
     └─────────────────────────┘        │        │   └─ (others)    │
                                └───────────────┴────────────────────┘
```

---

## 7. Riesgos y Mitigaciones (Actualizados)

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Git worktree conflicts | Alto | Idempotent operations, force flag |
| Hook execution failures | Medio | Timeout, error handling, skip option |
| Layout detection edge cases | Medio | Comprehensive Path resolution |
| Cross-platform worktree paths | Alto | Platform-specific path handling |
| tmux + worktree integration | Alto | Careful state management |

---

## 8. Métricas de Éxito

- [ ] 90%+ test coverage
- [ ] All workspace operations idempotent
- [ ] Setup/teardown hooks execute correctly
- [ ] All 3 layouts work (nested, outer-nested, sibling)
- [ ] Auto-detection from $PWD works
- [ ] Tab completion functional
- [ ] Backward compatibility with terminal_spawner.py
- [ ] Works on macOS and Linux

---

## 9. Referencias

- [cmux Repository](https://github.com/craigsc/cmux)
- [Tmux-Orchestrator Repository](https://github.com/Jedward23/Tmux-Orchestrator)
- [Git Worktree Documentation](https://git-scm.com/docs/git-worktree)
