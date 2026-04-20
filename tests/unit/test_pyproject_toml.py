"""Tests that pyproject.toml does not contain dead tooling config or dependencies."""

from __future__ import annotations

import tomllib
from pathlib import Path


def _load_pyproject() -> dict:
    pyproject_path = Path(__file__).resolve().parent.parent.parent / "pyproject.toml"
    with pyproject_path.open("rb") as f:
        return tomllib.load(f)


class TestNoDeadBlackDependency:
    """black is dead: ruff-format replaced it in pre-commit and CI."""

    def test_black_not_in_dev_dependencies(self) -> None:
        config = _load_pyproject()
        dev_deps = config["project"]["optional-dependencies"]["dev"]
        names = [d.split(">=")[0].split("==")[0].split("~=")[0].lower() for d in dev_deps]
        assert "black" not in names, "black should not be in dev dependencies"

    def test_no_tool_black_section(self) -> None:
        config = _load_pyproject()
        assert "black" not in config.get("tool", {}), (
            "[tool.black] config section should be removed"
        )


class TestNoDeadIsortDependency:
    """isort is dead: ruff handles import sorting (I001)."""

    def test_isort_not_in_dev_dependencies(self) -> None:
        config = _load_pyproject()
        dev_deps = config["project"]["optional-dependencies"]["dev"]
        names = [d.split(">=")[0].split("==")[0].split("~=")[0].lower() for d in dev_deps]
        assert "isort" not in names, "isort should not be in dev dependencies"

    def test_no_tool_isort_section(self) -> None:
        config = _load_pyproject()
        assert "isort" not in config.get("tool", {}), (
            "[tool.isort] config section should be removed"
        )


class TestRuffIsTheFormatter:
    """Verify ruff is the sole formatter/linter configured."""

    def test_ruff_in_dev_dependencies(self) -> None:
        config = _load_pyproject()
        dev_deps = config["project"]["optional-dependencies"]["dev"]
        names = [d.split(">=")[0].split("==")[0].split("~=")[0].lower() for d in dev_deps]
        assert "ruff" in names, "ruff must be in dev dependencies"

    def test_tool_ruff_section_exists(self) -> None:
        config = _load_pyproject()
        assert "ruff" in config.get("tool", {}), "[tool.ruff] config section must exist"
