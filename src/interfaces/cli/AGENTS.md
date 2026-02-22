# CLI Layer - AGENTS.md

> Capa de interfaces CLI (Typer)

---

## OVERVIEW

CLI de memoria usando Typer. Comandos: save, search, list, get, delete. Expuesto como `memory` via pyproject.toml console_scripts.

---

## STRUCTURE

```
src/interfaces/cli/
├── main.py              # Entry point, Typer app
├── dependencies.py      # DI helpers (get_memory_service)
├── commands/            # Subcomandos
│   ├── save.py
│   ├── search.py
│   ├── list.py
│   ├── get.py
│   └── delete.py
└── workspace_commands.py # Comandos workspace (no memoria)
```

---

## WHERE TO LOOK

| Task | File |
|------|------|
| Añadir comando memoria | `commands/*.py` |
| Cambiar entry point | `main.py` |
| Modificar DI | `dependencies.py` |
| Comandos workspace | `workspace_commands.py` |

---

## CONVENTIONS (CLI-SPECIFIC)

### ctx.obj Pattern
```python
# main.py establece el servicio
ctx.obj = get_memory_service(Path(db_path))

# commands lo consumen
memory_service = ctx.obj
observation = memory_service.save(content=content)
```

### Comando Template
```python
import typer

app = typer.Typer()

@app.command()
def my_command(
    ctx: typer.Context,
    arg: str = typer.Argument(...),
    option: str | None = typer.Option(None, "--opt", "-o"),
) -> None:
    service = ctx.obj
    result = service.do_something(arg)
    typer.echo(f"Result: {result}")
```

### Test Pattern
```python
from unittest.mock import MagicMock
from typer.testing import CliRunner

runner = CliRunner()

def test_command() -> None:
    mock_service = MagicMock()
    mock_service.method.return_value = expected_value
    
    result = runner.invoke(app, ["arg"], obj=mock_service)
    
    assert result.exit_code == 0
    mock_service.method.assert_called_once()
```

---

## ANTI-PATTERNS (CLI)

- ❌ NO instanciar MemoryService directamente en comandos
- ❌ NO usar db_path en ctx.obj (usar MemoryService)
- ❌ NO llamar repository desde comandos (usar MemoryService)

---

## ENTRY POINT

```toml
# pyproject.toml
[project.scripts]
memory = "src.interfaces.cli.main:app"
```

---

## NOTES

- Comandos de memoria usan MemoryService (no Use Cases ni Repository)
- Workspace commands tienen su propia lógica (no usan MemoryService)
- Tests mockean MemoryService directamente
