
# Análisis Arquitectónico del Kernel y Plan de Integración V4

## Resumen Ejecutivo

Este documento detalla la ingeniería inversa del repositorio `claudikins-kernel` y presenta un plan de arquitectura evolucionado (V4) para integrar su lógica de orquestación de manera pura y desacoplada en nuestro ecosistema. El objetivo es adoptar su potente sistema de `hooks` basado en eventos sin comprometer nuestros principios de Arquitectura Limpia.

## Versión Superior del Plan (V4): Arquitectura de Orquestación Pura

Este diseño eleva el plan original a una arquitectura de componentes puros, componibles y desacoplados, donde las dependencias fluyen estrictamente hacia abstracciones.

### Arquitectura Refinada (Entidades, Puertos y Servicios)

1.  **Dominio (El Núcleo Inmutable y Abstracto):**
    *   **`Event` (Protocolo Marcador):** Un `Protocol` vacío para identificar objetos de evento.
    *   **`Action` (Protocolo Marcador):** Un `Protocol` vacío para identificar objetos de acción.
    *   **`ISpecification` (Protocolo):** Define el contrato para la lógica de `matching`.
        *   `is_satisfied_by(self, event: Event) -> bool:`
    *   **`Rule` (Frozen Dataclass):** Una asociación inmutable entre una `Especificación` y una `Acción`.
        *   `spec: ISpecification`
        *   `action: Action`

2.  **Capa de Aplicación (El Orquestador Agnóstico):**
    *   **`IActionRunner` (Puerto):** El `Protocol` que el `EventDispatcher` usará para ejecutar una `Acción`. Define la frontera con el mundo impuro.
        *   `run(self, action: Action) -> None:`
    *   **`EventDispatcher` (Servicio):** Orquesta el flujo. No tiene estado y sus dependencias son abstractas.
        *   `__init__(self, rules: list[Rule], runner: IActionRunner)`
        *   `dispatch(self, event: Event) -> None:`

3.  **Infraestructura (El Mundo Concreto y los Efectos Secundarios):**
    *   **Eventos Concretos:** `dataclasses` que implementan el protocolo `Event`.
        *   `UserCommandEvent(command_name: str, args: tuple[str, ...])`
        *   `FileWrittenEvent(path: str)`
        *   `ToolPreExecutionEvent(tool_name: str)`
    *   **Acciones Concretas:** `dataclasses` que implementan el protocolo `Action`.
        *   `ShellCommandAction(command: str, timeout: int)`
    *   **Especificaciones Concretas:** Clases que implementan `ISpecification`.
        *   `EventTypeSpec(event_type: type[Event])`
        *   `CommandNameSpec(name_pattern: str)` (puede usar regex)
    *   **`ShellActionRunner` (Adaptador):** Implementación de `IActionRunner` que ejecuta `ShellCommandAction` usando `subprocess`.
    *   **`RuleLoader` (Fábrica):** Carga `hooks.json` y lo transforma en una `list[Rule]`, construyendo los objetos concretos de `Especificación` y `Acción`.

### Protocolos de Interfaz (Definición Exacta)

```python
from typing import Protocol
from dataclasses import dataclass

# 1. Protocolos del Dominio
class Event(Protocol):
    """Protocolo marcador para cualquier evento del sistema."""
    pass

class Action(Protocol):
    """Protocolo marcador para cualquier acción a ejecutar."""
    pass

class ISpecification(Protocol):
    """Define una especificación que puede ser satisfecha por un evento."""
    def is_satisfied_by(self, event: Event) -> bool:
        ...

@dataclass(frozen=True)
class Rule:
    """Asocia una Especificación a una Acción."""
    spec: ISpecification
    action: Action

# 2. Puerto de la Capa de Aplicación
class IActionRunner(Protocol):
    """Puerto para ejecutar acciones, separando la aplicación de la infraestructura."""
    def run(self, action: Action) -> None:
        ...
```

### Suite de Pruebas de Contrato (Red Phase)

Estos tests deben escribirse primero y deben fallar. Definen el contrato de éxito antes de cualquier implementación.

```python
import pytest
from unittest.mock import Mock

# Mocks y Stubs para las pruebas
class FakeEvent(Event): pass
class FakeAction(Action): pass

def test_dispatcher_runs_action_when_spec_is_satisfied(mocker):
    """
    GIVEN un EventDispatcher con una Regla y un ActionRunner
    WHEN se despacha un Evento que satisface la Especificación de la Regla
    THEN el ActionRunner debe ejecutar la Acción de la Regla.
    """
    # ARRANGE
    mock_runner = mocker.MagicMock(spec=IActionRunner)
    
    spec_satisfied = mocker.MagicMock(spec=ISpecification)
    spec_satisfied.is_satisfied_by.return_value = True
    
    action_to_run = FakeAction()
    rule = Rule(spec=spec_satisfied, action=action_to_run)
    
    dispatcher = EventDispatcher(rules=[rule], runner=mock_runner)
    event = FakeEvent()

    # ACT
    dispatcher.dispatch(event)

    # ASSERT
    mock_runner.run.assert_called_once_with(action_to_run)

def test_dispatcher_does_nothing_when_spec_is_not_satisfied(mocker):
    """
    GIVEN un EventDispatcher con una Regla y un ActionRunner
    WHEN se despacha un Evento que NO satisface la Especificación de la Regla
    THEN el ActionRunner NO debe ser llamado.
    """
    # ARRANGE
    mock_runner = mocker.MagicMock(spec=IActionRunner)
    
    spec_not_satisfied = mocker.MagicMock(spec=ISpecification)
    spec_not_satisfied.is_satisfied_by.return_value = False
    
    rule = Rule(spec=spec_not_satisfied, action=FakeAction())
    
    dispatcher = EventDispatcher(rules=[rule], runner=mock_runner)
    event = FakeEvent()

    # ACT
    dispatcher.dispatch(event)

    # ASSERT
    mock_runner.run.assert_not_called()

def test_shell_action_runner_throws_if_action_is_not_shell_command():
    """

    GIVEN un ShellActionRunner
    WHEN se intenta ejecutar una Acción que no es una ShellCommandAction
    THEN debe levantar un TypeError.
    """
    # ARRANGE
    runner = ShellActionRunner()
    wrong_action = FakeAction()

    # ACT & ASSERT
    with pytest.raises(TypeError):
        runner.run(wrong_action)

def test_command_name_spec_is_satisfied_by_matching_event():
    """
    GIVEN una CommandNameSpec inicializada con un patrón
    WHEN se prueba contra un UserCommandEvent con un nombre que coincide
    THEN la especificación debe ser satisfecha.
    """
    # ARRANGE
    spec = CommandNameSpec(name_pattern="ship")
    event = UserCommandEvent(command_name="ship", args=())

    # ACT
    result = spec.is_satisfied_by(event)

    # ASSERT
    assert result is True
```
