# Plan de Arquitectura - fork_agent

## Visión General

Establecer un sistema de desarrollo robusto con **Clean Architecture**, **Functional Programming**, **uv** para gestión de dependencias, **pytest** con coverage >90%, **mypy** para type checking, y **pre-commit hooks** con severidad progresiva.

---

## Estructura de Archivos

```
/workspaces/fork_agent/
├── pyproject.toml              # Configuración uv + herramientas
├── Makefile                    # Comandos de desarrollo
├── Makefile.help               # Documentación de comandos
├── .pre-commit-config.yaml     # Pre-commit hooks
├── .mypy.ini                   # Configuración mypy
├── .python-version             # Versión de Python
│
├── src/                        # Código fuente (Clean Architecture)
│   ├── __init__.py
│   ├── application/            # Casos de uso (services, use_cases)
│   │   ├── __init__.py
│   │   ├── use_cases/
│   │   │   ├── __init__.py
│   │   │   └── fork_terminal.py
│   │   └── services/
│   │       ├── __init__.py
│   │       └── terminal/
│   │           ├── __init__.py
│   │           └── linux.py
│   ├── domain/                 # Entidades y reglas de negocio
│   │   ├── __init__.py
│   │   ├── entities/
│   │   │   ├── __init__.py
│   │   │   └── terminal.py
│   │   └── exceptions/
│   │       ├── __init__.py
│   │       └── terminal.py
│   ├── infrastructure/         # Implementaciones externas
│   │   ├── __init__.py
│   │   ├── platform/
│   │   │   ├── __init__.py
│   │   │   ├── macos.py
│   │   │   ├── windows.py
│   │   │   └── linux.py
│   │   └── config/
│   │       ├── __init__.py
│   │       └── settings.py
│   └── interfaces/             # CLI, API, etc.
│       ├── __init__.py
│       └── cli/
│           ├── __init__.py
│           └── fork.py
│
├── tests/                      # Tests (mirrors src structure)
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── domain/
│   │   │   └── test_entities.py
│   │   └── application/
│   │       └── test_use_cases.py
│   ├── integration/
│   │   └── __init__.py
│   └── fixtures/
│       └── __init__.py
│
├── docs/                       # Documentación
│   ├── agents.md              # GUÍA PRINCIPAL DE MÉTODO DE TRABAJO
│   ├── architecture.md         # Decisiones de arquitectura
│   └── ...
│
└── plans/                      # Planes de implementación
    └── plan_001.md
```

---

## Componentes del Plan

### 1. pyproject.toml

```toml
[project]
name = "fork_agent"
version = "0.1.0"
description = "Plataforma agéntica avanzada para terminal"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "python-dotenv>=1.0.0",
    "pydantic>=2.0.0",  # Para validación y tipos
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=5.0.0",
    "pytest-mock>=3.12.0",
    "mypy>=1.8.0",
    "pre-commit>=3.6.0",
    "ruff>=0.3.0",  # Linter + formatter
    "black>=24.0.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = "-v --tb=short -p no:warnings"

[tool.coverage.run]
source = ["src"]
branch = true
omit = ["tests/*", "**/__init__.py"]

[tool.coverage.report]
exclude_lines = ["pragma: no cover", "if TYPE_CHECKING:", "@abstractmethod"]
show_missing = true
fail_under = 90

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.ruff]
target-version = "py311"
line-length = 100
select = ["E", "W", "F", "I", "UP", "B"]
ignore = ["E501"]  # Line length handled by formatter

[tool.black]
line-length = 100
target-version = ["py311"]
```

### 2. Makefile

```makefile
.PHONY: help install dev test lint format typecheck precommit prePR clean

# Colores para output
GREEN = \033[0;32m
YELLOW = \033[1;33m
RED = \033[0;31m
NC = \033[0m

help:
	@echo -e "$(GREEN)fork_agent - Comandos de Desarrollo$(NC)"
	@echo ""
	@echo "make install      - Instalar dependencias con uv"
	@echo "make dev          - Instalar dependencias de desarrollo"
	@echo "make test         - Ejecutar tests con pytest"
	@echo "make test-cov     - Ejecutar tests con coverage"
	@echo "make lint         - Ejecutar ruff linter"
	@echo "make format       - Formatear código con black"
	@echo "make typecheck    - Ejecutar mypy"
	@echo "make precommit    - Ejecutar pre-commit hooks"
	@echo "make prePR        - Ejecutar checks completos antes de PR"
	@echo "make clean        - Limpiar archivos temporales"

install:
	@echo -e "$(YELLOW)Instalando dependencias...$(NC)"
	uv pip install -e .

dev:
	@echo -e "$(YELLOW)Instalando dependencias de desarrollo...$(NC)"
	uv pip install -e ".[dev]"

test:
	@echo -e "$(YELLOW)Ejecutando tests...$(NC)"
	pytest tests/

test-cov:
	@echo -e "$(YELLOW)Ejecutando tests con coverage...$(NC)"
	pytest tests/ --cov=src --cov-report=term-missing --cov-report=html

lint:
	@echo -e "$(YELLOW)Ejecutando linter...$(NC)"
	ruff check src/ tests/

format:
	@echo -e "$(YELLOW)Formateando código...$(NC)"
	ruff format src/ tests/
	black src/ tests/

typecheck:
	@echo -e "$(YELLOW)Ejecutando type checker...$(NC)"
	mypy src/

precommit:
	@echo -e "$(YELLOW)Ejecutando pre-commit hooks...$(NC)"
	pre-commit run --all-files

prePR: lint format typecheck test-cov
	@echo -e "$(GREEN)✅ Todos los checks pasaron$(NC)"

clean:
	@echo -e "$(YELLOW)Limpiando archivos temporales...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	rm -rf .pytest_cache/ .mypy_cache/ htmlcov/ .tox/ 2>/dev/null || true
	@echo -e "$(GREEN)Limpieza completada$(NC)"
```

### 3. .pre-commit-config.yaml

```yaml
# Pre-commit hooks con severidad progresiva
# https://pre-commit.com/

repos:
  # Nivel INFO - Rápidos y seguros
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: ['--maxkb=1000']

  # Nivel WARN - Formateo
  - repo: https://github.com/psf/black
    rev: 24.2.0
    hooks:
      - id: black
        language_version: python3.11

  # Nivel ERROR - Linting estricto
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: [--fix]

  # Nivel ERROR - Type checking
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic>=2.0.0]
        args: [--strict, --ignore-missing-imports]

# Configuración de severidad
fail_fast: false
verbose: true
```

---

## Principios de Functional Programming

### Convenciones para el Código

1. **Funciones puras siempre que sea posible**
   - Sin efectos secundarios
   - Mismo input = mismo output
   - Tipado estricto con type hints

2. **Inmutabilidad**
   - Usar `dataclasses` con `frozen=True` para entidades
   - Devolver copias en lugar de mutar

3. **Composición de funciones**
   - Pipe/Chain de funciones para flujos de datos
   - Evitar nesting profundo de if/else

4. **Tratamiento de errores con Either/Maybe**
   - Usar excepciones controladas o Result types
   - No usar excepciones para control de flujo

### Estructura de Entidades (Functional Style)

```python
from dataclasses import dataclass
from typing import NamedTuple

@dataclass(frozen=True)
class TerminalResult:
    """Entidad inmutable para resultado de terminal."""
    success: bool
    output: str
    exit_code: int

@dataclass(frozen=True)
class PlatformConfig:
    """Configuración de plataforma."""
    system: str
    terminal: str | None
```

### Patrón de Use Case (Functional)

```python
from typing import Callable, TypeVar

T = TypeVar('T')
R = TypeVar('R')

def compose(*functions: Callable[[T], R]) -> Callable[[T], R]:
    """Componer funciones de derecha a izquierda."""
    def composed(x: T) -> R:
        result = x
        for func in reversed(functions):
            result = func(result)
        return result
    return composed

def fork_terminal_use_case(
    platform_detector: Callable[[], str],
    terminal_spawner: Callable[[str], TerminalResult],
) -> Callable[[str], TerminalResult]:
    """Use case como función pura."""
    def execute(command: str) -> TerminalResult:
        platform = platform_detector()
        return terminal_spawner(command)
    return execute
```

---

## Estructura de Tests

### Unit Tests (src/tests/unit/)

```python
# tests/unit/domain/test_entities.py
from src.domain.entities.terminal import TerminalConfig

def test_terminal_config_creation():
    """Test de creación de entidad."""
    config = TerminalConfig(terminal="gnome-terminal")
    assert config.terminal == "gnome-terminal"

def test_terminal_config_immutability():
    """Test de inmutabilidad."""
    config = TerminalConfig(terminal="xterm")
    try:
        config.terminal = "konsole"
        assert False, "Should not be mutable"
    except Exception:
        pass
```

### Integration Tests (src/tests/integration/)

```python
# tests/integration/test_fork_terminal.py
import pytest
from src.application.use_cases.fork_terminal import fork_terminal

def test_fork_terminal_linux_integration(tmp_path):
    """Test de integración para Linux."""
    # Arrange
    command = "echo 'test'"
    
    # Act
    result = fork_terminal(command)
    
    # Assert
    assert result.success is True
```

---

## Documentación (agents.md)

El archivo `docs/agents.md` contendrá:

1. **Introducción al Proyecto**
   - Propósito y objetivos
   - Stack tecnológico

2. **Método de Trabajo**
   - Flujo de desarrollo
   - Commits y branches
   - Code review

3. **Convenciones de Código**
   - Functional Programming rules
   - Clean Architecture layers
   - Type hints obrigatorios

4. **Comandos de Desarrollo**
   - Referencia al Makefile
   - Scripts de utilidad

5. **Testing**
   - Cobertura > 90%
   - Tipos de tests
   - Fixtures

6. **CI/CD**
   - Pre-commit hooks
   - Pre-PR checks
   - Severidad progresiva

---

## Próximos Pasos

1. [ ] Crear `.python-version` con Python 3.11+
2. [ ] Crear `pyproject.toml` con uv
3. [ ] Crear `Makefile` y `Makefile.help`
4. [ ] Crear `.pre-commit-config.yaml`
5. [ ] Crear `.mypy.ini`
6. [ ] Crear estructura de directorios `src/`
7. [ ] Crear estructura de directorios `tests/`
8. [ ] Migrar código existente a Clean Architecture
9. [ ] Crear `docs/agents.md`
10. [ ] Configurar CI/CD si es necesario

---

## Plan de Extraccion MCP (paso a paso)

### Etapa 0: Alcance
- Definir que es "core" (protocolos, storage, locks) vs "runtime/UI" (tmux, panes).
- Entregable: lista priorizada de modulos a extraer.

### Etapa 1: Top-level y empaquetado
- Revisar `README`, `pyproject.toml`, `LICENSE`.
- Entregable: mapa de herramientas MCP, requisitos, entrypoint.

### Etapa 2: Modelos y contratos de datos
- Revisar `models.py`.
- Entregable: schema JSON (Team/Member/Task/Inbox + payloads).

### Etapa 3: Persistencia y concurrencia
- Revisar `teams.py`, `tasks.py`, `messaging.py`.
- Entregable: reglas de storage, locks, writes atomicos y validaciones.

### Etapa 4: API MCP
- Revisar `server.py`.
- Entregable: especificacion de herramientas (inputs/outputs, errores).

### Etapa 5: Spawner (sin tmux)
- Revisar `spawner.py` para flags, env vars y prompt inicial.
- Entregable: contrato minimo para runtime alternativo (PID, backend_type, health).

### Etapa 6: Tests y edge cases
- Revisar `tests/` y `stress_test_lifecycle.py`.
- Entregable: checklist de validaciones y casos limite.

### Etapa 7: Gap analysis con fork_agent
- Comparar lo extraido con este repo.
- Entregable: backlog por capas (core protocol, MCP, runtime).
