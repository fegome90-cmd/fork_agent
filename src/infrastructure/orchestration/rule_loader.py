"""RuleLoader infrastructure for loading hooks.json config."""

from __future__ import annotations

import json
from pathlib import Path

from src.application.services.orchestration.actions import (
    OnFailurePolicy,
    ShellCommandAction,
)
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
                        
                        on_failure_str = hook.get("on_failure", "abort")
                        try:
                            on_failure = OnFailurePolicy(on_failure_str)
                        except ValueError:
                            on_failure = OnFailurePolicy.ABORT
                        
                        action = ShellCommandAction(
                            command=hook["command"],
                            timeout=hook.get("timeout", 30),
                            critical=hook.get("critical", True),
                            on_failure=on_failure,
                        )
                        rules.append(Rule(spec=spec, action=action))

        return rules
