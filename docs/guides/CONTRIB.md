# Contributing Guide

> fork_agent contribution guidelines. Last updated: 2026-02-25

---

## Development Workflow

### Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.11+ | Required |
| uv | latest | Package manager |
| tmux | latest | For session isolation |

### Setup

```bash
# 1. Clone repository
git clone <repo-url>
cd tmux_fork

# 2. Install uv (if not present)
make deps

# 3. Install dependencies
make install

# 4. Install dev dependencies
make dev
```

---

## Available Scripts

### Installation

| Command | Description |
|---------|-------------|
| `make deps` | Install/upgrade uv package manager |
| `make install` | Install package with all dependencies |
| `make dev` | Install development dependencies |

### Testing

| Command | Description |
|---------|-------------|
| `make test` | Run pytest with verbose output |
| `make test-cov` | Run tests with coverage report (htmlcov/) |
| `make test-fast` | Run tests without coverage (faster) |

### Code Quality

| Command | Description |
|---------|-------------|
| `make lint` | Run ruff linter |
| `make format` | Format code with ruff + black |
| `make typecheck` | Run mypy type checker |

### Git Hooks

| Command | Description |
|---------|-------------|
| `make precommit` | Run pre-commit hooks |
| `make prePR` | Run all checks before PR (lint + format + typecheck + test-cov) |

### Maintenance

| Command | Description |
|---------|-------------|
| `make clean` | Clean temporary files |
| `make deps-check` | Check outdated dependencies |

### Alternative: uv commands

```bash
# Run tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=term-missing

# Run linter
uv run ruff check src/ tests/

# Format code
uv run ruff format src/ tests/

# Type check
uv run mypy src/

# Run pre-commit
uv run pre-commit run --all-files
```

---

## Environment Setup

### Required Variables

Create a `.env` file from the template:

```bash
cp .env.sample .env
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | No | OpenAI API key for agent interactions |
| `CLAUDE_API_KEY` | No | Anthropic API key for Claude Code |
| `MEMORY_DB_PATH` | No | Path to SQLite database (default: `data/memory.db`) |

---

## Testing Procedures

### Running Tests

```bash
# All tests with coverage
make test-cov

# Fast tests (no coverage)
make test-fast

# Specific test file
uv run pytest tests/unit/domain/ -v

# With specific markers
uv run pytest tests/ -v -m "not slow"
```

### Coverage Requirements

- Minimum coverage: **72%**
- Run `make test-cov` before submitting PR
- Coverage report generated in `htmlcov/`

### Code Quality Gates

Before submitting a PR, run:

```bash
make prePR
```

This executes:
1. `make lint` - Ruff checks
2. `make format` - Code formatting
3. `make typecheck` - Mypy strict mode
4. `make test-cov` - Tests with 95% coverage

---

## Project Structure

```
tmux_fork/
├── src/
│   ├── domain/           # Entities, Ports (interfaces)
│   ├── application/      # Use Cases, Services
│   ├── infrastructure/   # DB, Platform-specific
│   └── interfaces/       # CLI, API
├── tests/
│   ├── unit/            # Unit tests
│   ├── integration/     # Integration tests
│   └── e2e/             # End-to-end tests
├── .hooks/              # Git hooks
├── .claude/             # Claude Code state
├── docs/                # Documentation
└── pyproject.toml       # Project config
```

---

## CLI Commands

### Memory Commands

```bash
# Save observation
memory save "text to remember"

# Search observations
memory search "query"

# List all
memory list

# Get by ID
memory get <id>

# Delete
memory delete <id>
```

### Workflow Commands

```bash
# Create plan
memory workflow outline "task description"

# Execute plan
memory workflow execute

# Verify (runs tests)
memory workflow verify

# Ship (requires verify)
memory workflow ship

# Status
memory workflow status
```

### Fork Commands

```bash
# Health check
fork doctor status

# Reconcile sessions
fork doctor reconcile

# Cleanup orphans
fork doctor cleanup-orphans --no-dry-run
```

---

## Code Standards

### Type Hints

- **Required** on all functions
- Use `X | None` instead of `Optional[X]`

### Formatting

- Line length: 100 characters
- Use ruff + black (auto-run via `make format`)

### Imports Order

```python
from __future__ import annotations  # 1. Future imports
import sys                          # 2. Standard library
import typer                        # 3. Third-party
from src.domain.entities import X   # 4. Local
```

### Anti-Patterns

```python
# ❌ NO - Type suppression
value = get_value() as any

# ❌ NO - Mutating arguments
def process(items: list) -> None:
    items.append("new")

# ❌ NO - Empty catch blocks
try:
    do_something()
except:
    pass

# ❌ NO - Redundant docstrings
def add(a: int, b: int) -> int:
    """Add two numbers."""  # Delete this
    return a + b
```

---

## Commit Guidelines

### Allowed Git Commands

The project uses `git-branch-guard.sh` which blocks dangerous operations:

| Allowed | Blocked |
|---------|---------|
| `git add` | `git checkout` |
| `git commit` | `git push` |
| `git status` | `git rebase` |
| `git diff` | `git merge` |
| `git log` | `git reset` |
| `git show` | `git stash` |
| `git blame` | `git clean` |
| `git branch` | `git cherry-pick` |
| `git fetch` | `git pull` |

---

## Getting Help

| Resource | Description |
|----------|-------------|
| `make help` | Show available make commands |
| `docs/runbook/` | Operational runbooks |
| `docs/informes/` | Architecture decisions |
| `.claude/sessions/` | Session history |
