
# fork_agent

Colección de skills, prompts y herramientas para construir agentes que interactúan con la terminal y flujos de desarrollo.

Ver `idea.md` para la visión y roadmap.

Quick start:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # si aplica
python skills/tools/fork_terminal.py --cmd "echo Hola" --dry-run
```

Estructura principal:

- `skills/` — skills y utilities.
- `prompts/` — plantillas y prompts reutilizables.
- `cookbook/` — recetas y patrones.

Contribuciones: abrir issues y PRs pequeñas con tests o instrucciones de verificación.