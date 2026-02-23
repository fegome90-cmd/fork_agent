"""RuleLoader infrastructure for loading hooks.json config."""

from __future__ import annotations

import json
from pathlib import Path

from src.application.services.orchestration.actions import ShellCommandAction
from src.application.services.orchestration.specs import RegexMatcherSpec
from src.domain.entities.rule import Rule


class RuleLoader:
    """Loads hooks.json and transforms into list[Rule].

    Supports the claudikins-kernel hooks.json format with event types,
    matchers, and hook configurations.
    """

    @staticmethod
    def load(config_path: Path) -> list[Rule]:
        """Load rules from hooks.json config file.

        Args:
            config_path: Path to the hooks.json file.

        Returns:
            List of Rule objects, empty if file doesn't exist or is empty.
        """
        if not config_path.exists():
            return []

        with config_path.open() as f:
            data = json.load(f)

        rules: list[Rule] = []
        hooks_config = data.get("hooks", {})

        for event_type, matchers in hooks_config.items():
            for matcher_config in matchers:
                pattern = matcher_config.get("matcher", ".*")
                if pattern == "*":
                    pattern = ".*"

                for hook in matcher_config.get("hooks", []):
                    if hook.get("type") == "command":
                        spec = RegexMatcherSpec(
                            event_type=event_type,
                            matcher=pattern,
                        )
                        action = ShellCommandAction(
                            command=hook["command"],
                            timeout=hook.get("timeout", 30),
                        )
                        rules.append(Rule(spec=spec, action=action))

        return rules
