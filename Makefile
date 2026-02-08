# fork_agent - Comandos de Desarrollo
# ================================

# Colores para output
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
BLUE := \033[0;34m
NC := \033[0m

.PHONY: help install dev test test-cov lint format typecheck precommit prePR clean deps

#默认目标
all: help

help:
	@echo -e "$(BLUE)╔════════════════════════════════════════════════════════╗$(NC)"
	@echo -e "$(BLUE)║           fork_agent - Comandos de Desarrollo          ║$(NC)"
	@echo -e "$(BLUE)╚════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo -e "$(GREEN)📦 Instalación$(NC)"
	@echo "   make deps        - Instalar/actualizar uv"
	@echo "   make install     - Instalar paquete con dependencias"
	@echo "   make dev         - Instalar dependencias de desarrollo"
	@echo ""
	@echo -e "$(GREEN)🧪 Testing$(NC)"
	@echo "   make test        - Ejecutar tests con pytest"
	@echo "   make test-cov    - Ejecutar tests con coverage"
	@echo "   make test-fast   - Tests sin coverage (más rápido)"
	@echo ""
	@echo -e "$(GREEN)🔍 Calidad de Código$(NC)"
	@echo "   make lint        - Ejecutar ruff linter"
	@echo "   make format      - Formatear código (ruff + black)"
	@echo "   make typecheck   - Ejecutar mypy"
	@echo ""
	@echo -e "$(GREEN)🔧 Git Hooks$(NC)"
	@echo "   make precommit   - Ejecutar pre-commit hooks"
	@echo "   make prePR       - Checks completos antes de PR"
	@echo ""
	@echo -e "$(GREEN)🧹 Mantenimiento$(NC)"
	@echo "   make clean       - Limpiar archivos temporales"
	@echo "   make deps-check  - Verificar dependencias desactualizadas"
	@echo ""

deps:
	@echo -e "$(YELLOW)Instalando uv...$(NC)"
	curl -LsSf https://astral.sh/uv/install.sh | sh
	source $$HOME/.cargo/env 2>/dev/null || true
	@echo -e "$(GREEN)✅ uv instalado$(NC)"

install:
	@echo -e "$(YELLOW)Instalando dependencias...$(NC)"
	uv pip install -e .
	@echo -e "$(GREEN)✅ Dependencias instaladas$(NC)"

dev:
	@echo -e "$(YELLOW)Instalando dependencias de desarrollo...$(NC)"
	uv pip install -e ".[dev]"
	@echo -e "$(GREEN)✅ Dependencias de desarrollo instaladas$(NC)"

test:
	@echo -e "$(YELLOW)🧪 Ejecutando tests...$(NC)"
	pytest tests/ -v --tb=short

test-cov:
	@echo -e "$(YELLOW)📊 Ejecutando tests con coverage...$(NC)"
	pytest tests/ --cov=src --cov-report=term-missing --cov-report=html
	@echo -e "$(GREEN)✅ Coverage report generado en htmlcov/$(NC)"

test-fast:
	@echo -e "$(YELLOW)🧪 Ejecutando tests rápidos (sin coverage)...$(NC)"
	pytest tests/ -v --tb=short --no-cov

lint:
	@echo -e "$(YELLOW)🔍 Ejecutando linter (ruff)...$(NC)"
	ruff check src/ tests/
	@echo -e "$(GREEN)✅ Linting completado$(NC)"

format:
	@echo -e "$(YELLOW)🎨 Formateando código...$(NC)"
	ruff format src/ tests/
	black src/ tests/
	@echo -e "$(GREEN)✅ Formateo completado$(NC)"

typecheck:
	@echo -e "$(YELLOW)🔎 Ejecutando type checker (mypy)...$(NC)"
	mypy src/
	@echo -e "$(GREEN)✅ Type checking completado$(NC)"

precommit:
	@echo -e "$(YELLOW)🪝 Ejecutando pre-commit hooks...$(NC)"
	pre-commit run --all-files --show-diff-on-failure

prePR: lint format typecheck test-cov
	@echo ""
	@echo -e "$(GREEN)╔════════════════════════════════════════════════════════╗$(NC)"
	@echo -e "$(GREEN)║          ✅ Todos los checks pasaron                   ║$(NC)"
	@echo -e "$(GREEN)╚════════════════════════════════════════════════════════╝$(NC)"

clean:
	@echo -e "$(YELLOW)🧹 Limpiando archivos temporales...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type f -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache/ .mypy_cache/ htmlcov/ .tox/ .benchmarks/ 2>/dev/null || true
	find . -name "*.py.bak" -delete 2>/dev/null || true
	@echo -e "$(GREEN)✅ Limpieza completada$(NC)"

deps-check:
	@echo -e "$(YELLOW)🔍 Verificando dependencias...$(NC)"
	uv pip list --outdated
