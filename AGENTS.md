# fork_agent - Guía de Trabajo y Convenciones

## 📋 Tabla de Contenidos

1. [Introducción](#introducción)
2. [Stack Tecnológico](#stack-tecnológico)
3. [Arquitectura](#arquitectura)
4. [Convenciones de Código](#convenciones-de-código)
5. [Flujo de Desarrollo](#flujo-de-desarrollo)
6. [Testing](#testing)
7. [Comandos de Desarrollo](#comandos-de-desarrollo)
8. [Contribución](#contribución)

---

## Introducción

**fork_agent** es una plataforma agéntica avanzada diseñada para transformar y optimizar la interacción con tu terminal. Su capacidad central reside en la habilidad `fork_terminal`, que permite "bifurcar" (fork) tu sesión actual a nuevas ventanas o sesiones de terminal paralelas.

Esta guía documenta el **método de trabajo** establecido para mantener un código de alta calidad, testeable y mantenible.

---

## Stack Tecnológico

| Componente | Herramienta | Propósito |
|------------|-------------|-----------|
| **Lenguaje** | Python 3.11+ | Lenguaje principal |
| **Gestor de dependencias** | uv | Instalación rápida de paquetes |
| **Type checking** | mypy | Verificación estática de tipos |
| **Linting** | ruff | Linter rápido y moderno |
| **Formateo** | black + ruff format | Consistencia de código |
| **Testing** | pytest | Framework de testing |
| **Coverage** | pytest-cov | Métricas de cobertura |
| **Pre-commit** | pre-commit | Git hooks automatizados |
| **Gestor de proyecto** | pyproject.toml | Configuración unificada |

---

## Arquitectura

### Clean Architecture

El proyecto sigue los principios de **Clean Architecture** con una estructura modular:

```
src/
├── domain/                    # ✅ innermost layer
│   ├── entities/             # Entidades del dominio (inmutables)
│   └── exceptions/           # Excepciones específicas del dominio
├── application/              # 📋 Casos de uso y servicios
│   ├── use_cases/           # Lógica de negocio orquestada
│   └── services/            # Servicios de aplicación
├── infrastructure/           # 🌐 Implementaciones externas
│   ├── platform/            # Detalles específicos de plataforma
│   └── config/              # Configuración
└── interfaces/               # 🎯 Adaptadores de entrada/salida
    └── cli/                 # Interfaz de línea de comandos
```

### Principios Fundamentales

1. **Dependencias pointing inward**: Las capas internas no conocen las externas
2. **Inmutabilidad**: Las entidades son inmutables (`@dataclass(frozen=True)`)
3. **Single Responsibility**: Cada módulo tiene una única responsabilidad
4. **Dependency Injection**: Las dependencias se inyectan, no se crean internamente

---

## Convenciones de Código

### Functional Programming

Este proyecto adopta un enfoque de **Functional Programming** cuando es apropiado:

#### ✅ Sí hacer:

```python
# Funciones puras
def calculate_total(price: float, tax_rate: float) -> float:
    return price * (1 + tax_rate)

# Entidades inmutables
@dataclass(frozen=True)
class User:
    id: int
    name: str

# Type hints obligatorios
def process_data(data: list[str]) -> dict[str, int]:
    ...
```

#### ❌ No hacer:

```python
# Evitar efectos secundarios
def bad_function(items: list) -> None:
    items.append("new")  # ❌ Mutación

# Evitar None checks excesivos
if x is not None:
    if y is not None:
        ...
```

### Nombrado

| Elemento | Convención | Ejemplo |
|----------|------------|---------|
| **Archivos** | snake_case | `fork_terminal.py` |
| **Clases** | PascalCase | `TerminalSpawner` |
| **Funciones** | snake_case | `spawn_terminal` |
| **Constantes** | UPPER_SNAKE_CASE | `MAX_RETRIES` |
| **Variables** | snake_case | `terminal_config` |

### Type Hints

Los **type hints son obrigatorios** para todas las funciones y variables:

```python
from typing import Callable, TypeVar

T = TypeVar('T')
R = TypeVar('R')

def compose(func1: Callable[[T], R], func2: Callable[[R], T]) -> Callable[[T], T]:
    """Componer funciones."""
    def composed(x: T) -> T:
        return func2(func1(x))
    return composed
```

---

## Flujo de Desarrollo

### 1. Configuración Inicial

```bash
# Instalar uv si no está instalado
make deps

# Instalar dependencias
make dev

# Configurar pre-commit hooks
pre-commit install
```

### 2. Crear Nueva Feature

```bash
# Crear branch desde main
git checkout -b feature/nueva-caracteristica

# Desarrollo...

# Ejecutar checks antes de commit
make precommit

# Commit con mensaje descriptivo
git commit -m "feat: agregar nueva característica"
```

### 3. Antes de Pull Request

```bash
# Ejecutar todos los checks
make prePR

# Si todo pasa: abrir PR
```

### Conventional Commits

Usamos **Conventional Commits** para mensajes de commit:

| Tipo | Descripción |
|------|-------------|
| `feat:` | Nueva característica |
| `fix:` | Corrección de bug |
| `docs:` | Cambios en documentación |
| `style:` | Formateo, sin cambio de código |
| `refactor:` | Reestructuración de código |
| `test:` | Agregar/modificar tests |
| `chore:` | Tareas de mantenimiento |

---

## Testing

### Estructura de Tests

```
tests/
├── conftest.py              # Fixtures compartidos
├── unit/                   # Tests unitarios
│   ├── domain/
│   └── application/
├── integration/             # Tests de integración
└── fixtures/               # Datos de prueba
```

### Convenciones de Testing

1. **命名** (Naming): `test_<funcion>_<escenario>`
2. **Coverage mínimo**: 90%
3. **AAA Pattern**: Arrange, Act, Assert
4. **Idempotencia**: Tests no deben depender de estado externo

### Ejemplo de Test

```python
from src.domain.entities.terminal import TerminalResult


class TestTerminalResult:
    """Tests para TerminalResult."""

    def test_create_successful_result(self) -> None:
        """Test creación de resultado exitoso."""
        # Arrange
        output = "echo hello"
        exit_code = 0

        # Act
        result = TerminalResult(
            success=True,
            output=output,
            exit_code=exit_code
        )

        # Assert
        assert result.success is True
        assert result.output == output
        assert result.exit_code == exit_code

    def test_result_immutability(self) -> None:
        """Test de inmutabilidad."""
        result = TerminalResult(
            success=True,
            output="test",
            exit_code=0
        )
        with pytest.raises(Exception):
            result.success = False
```

---

## Comandos de Desarrollo

### Makefile

| Comando | Descripción |
|---------|-------------|
| `make deps` | Instalar uv |
| `make install` | Instalar dependencias |
| `make dev` | Instalar dependencias de desarrollo |
| `make test` | Ejecutar tests |
| `make test-cov` | Tests con coverage |
| `make lint` | Ejecutar ruff |
| `make format` | Formatear código |
| `make typecheck` | Ejecutar mypy |
| `make precommit` | Pre-commit hooks |
| `make prePR` | Checks completos |
| `make clean` | Limpiar archivos temporales |

### Pre-commit Hooks

Los hooks se ejecutan automáticamente antes de cada commit:

1. **INFO** (rápido): trailing whitespace, YAML, archivos grandes
2. **WARN**: Formateo con black y ruff format
3. **ERROR**: Linting con ruff y type checking con mypy

Si algún hook falla, el commit se bloquea.

---

## Contribución

### Code Review

1. Todos los PRs requieren al menos un approval
2. Los checks deben pasar (lint, typecheck, tests)
3. Coverage no debe disminuir

### Mejores Prácticas

- ✅ Escribir tests antes o durante el desarrollo
- ✅ Usar type hints en todo el código
- ✅ Mantener funciones pequeñas (< 30 líneas)
- ✅ Documentar funciones públicas con docstrings
- ✅ hacer uso de immutable data structures
- ✅ Preferir composición sobre herencia

---

## Recursos Adicionales

- [PEP 8 - Style Guide](https://peps.python.org/pep-0008/)
- [mypy Documentation](https://mypy.readthedocs.io/)
- [pytest Documentation](https://docs.pytest.org/)
- [Clean Architecture - Uncle Bob](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
