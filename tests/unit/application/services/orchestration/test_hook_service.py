"""Tests for HookService."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from src.application.services.orchestration.hook_service import HookService


class TestHookService:
    """Tests for HookService."""

    def test_default_config_path(self) -> None:
        service = HookService()
        assert service.config_path == Path(".hooks/hooks.json")

    def test_custom_config_path(self, tmp_path: Path) -> None:
        config = tmp_path / "custom.json"
        service = HookService(config_path=config)
        assert service.config_path == config

    def test_load_dispatcher(self, tmp_path: Path) -> None:
        config = tmp_path / "hooks.json"
        config.write_text('{"hooks": {}}')

        service = HookService(config_path=config)
        dispatcher = service.load_dispatcher()

        assert dispatcher is not None

    def test_dispatch_calls_dispatcher(self, tmp_path: Path) -> None:
        config = tmp_path / "hooks.json"
        config.write_text('{"hooks": {}}')

        service = HookService(config_path=config)
        mock_event = MagicMock()

        service.dispatch(mock_event)

    def test_reload_clears_dispatcher(self, tmp_path: Path) -> None:
        config = tmp_path / "hooks.json"
        config.write_text('{"hooks": {}}')

        service = HookService(config_path=config)
        dispatcher1 = service.load_dispatcher()
        service.reload()
        dispatcher2 = service.load_dispatcher()

        assert dispatcher1 is not dispatcher2
