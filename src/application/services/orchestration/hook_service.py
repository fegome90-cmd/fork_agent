"""Hook integration service."""

from __future__ import annotations

from pathlib import Path

from src.application.services.orchestration.dispatcher import EventDispatcher
from src.infrastructure.orchestration.rule_loader import RuleLoader
from src.infrastructure.orchestration.shell_action_runner import ShellActionRunner


class HookService:
    """Service that loads hooks and provides an event dispatcher."""

    def __init__(self, config_path: Path | None = None) -> None:
        if config_path is None:
            config_path = Path(".hooks/hooks.json")
        self._config_path = config_path
        self._dispatcher: EventDispatcher | None = None

    @property
    def config_path(self) -> Path:
        return self._config_path

    def load_dispatcher(self) -> EventDispatcher:
        if self._dispatcher is None:
            rules = RuleLoader.load(self._config_path)
            hooks_dir = self._config_path.parent
            runner = ShellActionRunner(hooks_dir)
            self._dispatcher = EventDispatcher(rules, runner)
        return self._dispatcher

    def dispatch(self, event: object) -> None:
        dispatcher = self.load_dispatcher()
        dispatcher.dispatch(event)

    def reload(self) -> None:
        self._dispatcher = None
