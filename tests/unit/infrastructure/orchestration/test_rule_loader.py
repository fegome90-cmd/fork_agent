"""Tests for RuleLoader infrastructure.

TDD Red Phase - Tests written before implementation.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


class TestRuleLoader:
    """Tests for RuleLoader."""

    def test_load_valid_hooks_json(self, tmp_path: Path) -> None:
        """Should load valid hooks.json file."""
        from src.infrastructure.orchestration.rule_loader import RuleLoader

        hooks_file = tmp_path / "hooks.json"
        hooks_file.write_text(
            json.dumps(
                {
                    "hooks": {
                        "UserCommand": [
                            {
                                "matcher": "test-.*",
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": "echo test",
                                        "timeout": 10,
                                    }
                                ],
                            }
                        ]
                    }
                }
            )
        )

        rules = RuleLoader.load(hooks_file)

        assert len(rules) == 1

    def test_load_empty_file_returns_empty_list(self, tmp_path: Path) -> None:
        """Should return empty list for empty JSON file."""
        from src.infrastructure.orchestration.rule_loader import RuleLoader

        hooks_file = tmp_path / "hooks.json"
        hooks_file.write_text("{}")

        rules = RuleLoader.load(hooks_file)

        assert rules == []

    def test_load_missing_file_returns_empty_list(self, tmp_path: Path) -> None:
        """Should return empty list if file does not exist."""
        from src.infrastructure.orchestration.rule_loader import RuleLoader

        nonexistent = tmp_path / "nonexistent.json"

        rules = RuleLoader.load(nonexistent)

        assert rules == []

    def test_load_multiple_hooks_per_event(self, tmp_path: Path) -> None:
        """Should load multiple hooks for a single event type."""
        from src.infrastructure.orchestration.rule_loader import RuleLoader

        hooks_file = tmp_path / "hooks.json"
        hooks_file.write_text(
            json.dumps(
                {
                    "hooks": {
                        "UserCommand": [
                            {
                                "matcher": "cmd1",
                                "hooks": [
                                    {"type": "command", "command": "echo 1"},
                                    {"type": "command", "command": "echo 2"},
                                ],
                            }
                        ]
                    }
                }
            )
        )

        rules = RuleLoader.load(hooks_file)

        assert len(rules) == 2

    def test_load_multiple_matchers(self, tmp_path: Path) -> None:
        """Should load multiple matchers for different event types."""
        from src.infrastructure.orchestration.rule_loader import RuleLoader

        hooks_file = tmp_path / "hooks.json"
        hooks_file.write_text(
            json.dumps(
                {
                    "hooks": {
                        "UserCommand": [
                            {
                                "matcher": "cmd1",
                                "hooks": [{"type": "command", "command": "echo 1"}],
                            }
                        ],
                        "FileWritten": [
                            {
                                "matcher": ".*\\.py",
                                "hooks": [{"type": "command", "command": "echo py"}],
                            }
                        ],
                    }
                }
            )
        )

        rules = RuleLoader.load(hooks_file)

        assert len(rules) == 2

    def test_load_ignores_non_command_hooks(self, tmp_path: Path) -> None:
        """Should ignore hooks that are not type 'command'."""
        from src.infrastructure.orchestration.rule_loader import RuleLoader

        hooks_file = tmp_path / "hooks.json"
        hooks_file.write_text(
            json.dumps(
                {
                    "hooks": {
                        "UserCommand": [
                            {
                                "matcher": "test",
                                "hooks": [
                                    {"type": "command", "command": "echo cmd"},
                                    {"type": "webhook", "url": "http://example.com"},
                                ],
                            }
                        ]
                    }
                }
            )
        )

        rules = RuleLoader.load(hooks_file)

        assert len(rules) == 1

    def test_load_uses_default_timeout(self, tmp_path: Path) -> None:
        """Should use default timeout (30) if not specified."""
        from src.infrastructure.orchestration.rule_loader import RuleLoader

        hooks_file = tmp_path / "hooks.json"
        hooks_file.write_text(
            json.dumps(
                {
                    "hooks": {
                        "UserCommand": [
                            {
                                "matcher": "test",
                                "hooks": [{"type": "command", "command": "echo test"}],
                            }
                        ]
                    }
                }
            )
        )

        rules = RuleLoader.load(hooks_file)

        assert rules[0].action.timeout == 30

    def test_load_uses_wildcard_matcher(self, tmp_path: Path) -> None:
        """Should treat '*' matcher as match-all pattern."""
        from src.infrastructure.orchestration.rule_loader import RuleLoader

        hooks_file = tmp_path / "hooks.json"
        hooks_file.write_text(
            json.dumps(
                {
                    "hooks": {
                        "UserCommand": [
                            {
                                "matcher": "*",
                                "hooks": [{"type": "command", "command": "echo all"}],
                            }
                        ]
                    }
                }
            )
        )

        rules = RuleLoader.load(hooks_file)

        assert len(rules) == 1
