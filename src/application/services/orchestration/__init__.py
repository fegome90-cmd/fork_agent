"""Orchestration services for event-driven hook management."""

from __future__ import annotations

from pathlib import Path

from src.application.services.orchestration.dispatcher import EventDispatcher
from src.domain.entities.rule import Rule
from src.infrastructure.orchestration.rule_loader import RuleLoader
from src.infrastructure.orchestration.shell_action_runner import ShellActionRunner

__all__ = ["EventDispatcher", "create_event_dispatcher"]


def create_event_dispatcher(
    hooks_config: Path | None = None,
    hooks_dir: Path | None = None,
    extra_rules: list[Rule] | None = None,
) -> EventDispatcher:
    """Factory function to create a fully wired EventDispatcher.

    Loads rules from hooks.json config file and/or programmatic rules.
    Creates ShellActionRunner with security features.

    Args:
        hooks_config: Path to hooks.json config file.
        hooks_dir: Directory for hook scripts (passed to executed commands).
        extra_rules: Additional programmatic rules to include.

    Returns:
        Configured EventDispatcher ready to dispatch events.
    """
    rules: list[Rule] = []

    if hooks_config and hooks_config.exists():
        rules.extend(RuleLoader.load(hooks_config))

    if extra_rules:
        rules.extend(extra_rules)

    runner = ShellActionRunner(
        hooks_dir=hooks_dir or Path(".hooks"),
    )

    return EventDispatcher(rules=rules, runner=runner)
