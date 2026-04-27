"""Tests for GitHub Actions workflow invariants."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def _load_workflow(name: str) -> dict[str, Any]:
    workflow_path = Path(__file__).resolve().parent.parent.parent / ".github/workflows" / name
    with workflow_path.open() as f:
        return yaml.safe_load(f)


def _load_ci_workflow() -> dict[str, Any]:
    return _load_workflow("ci.yml")


def _workflow_on(workflow: dict[str, Any]) -> Any:
    """Return the GitHub Actions `on` key even if PyYAML treats it as boolean True."""

    return workflow.get("on", workflow.get(True))


class TestSecurityWorkflow:
    """The security job must use Bandit's supported report formats."""

    def test_bandit_uses_json_artifact_not_unsupported_sarif_upload(self) -> None:
        workflow = _load_ci_workflow()
        steps = workflow["jobs"]["security"]["steps"]

        bandit_step = next(step for step in steps if step.get("name") == "Run bandit")
        assert bandit_step["run"] == (
            "uv run --extra dev bandit -r src/ -ll -f json -o bandit-report.json"
        )

        upload_step = next(step for step in steps if step.get("name") == "Upload bandit report")
        assert upload_step["uses"] == "actions/upload-artifact@v4"
        assert upload_step["if"] == "always()"
        assert upload_step["with"] == {
            "name": "bandit-report",
            "path": "bandit-report.json",
            "retention-days": 7,
        }

        security_job_text = "\n".join(
            str(step.get("run", "")) + "\n" + str(step.get("uses", "")) for step in steps
        )
        assert "-f sarif" not in security_job_text
        assert "github/codeql-action/upload-sarif" not in security_job_text


class TestRuntimeWorkflowSplit:
    """Runtime-dependent checks must stay out of default CI."""

    RUNTIME_COMMANDS = ("tmux", "opencode", "pi")

    def test_runtime_integration_workflow_is_manual_only(self) -> None:
        workflow = _load_workflow("runtime-integration.yml")

        triggers = _workflow_on(workflow)
        assert set(triggers) == {"workflow_dispatch"}
        assert workflow["jobs"]["runtime-integration"]["runs-on"] == "self-hosted"

    def test_runtime_integration_workflow_documents_explicit_prerequisites(self) -> None:
        workflow_path = (
            Path(__file__).resolve().parent.parent.parent
            / ".github/workflows/runtime-integration.yml"
        )
        workflow_text = workflow_path.read_text()

        for command in self.RUNTIME_COMMANDS:
            assert command in workflow_text
            assert f"command -v {command}" in workflow_text

    def test_default_ci_does_not_install_or_execute_runtime_dependencies(self) -> None:
        workflow = _load_ci_workflow()
        step_text = "\n".join(
            "\n".join(
                (
                    str(step.get("name", "")),
                    str(step.get("run", "")),
                    str(step.get("uses", "")),
                )
            )
            for job in workflow["jobs"].values()
            for step in job.get("steps", [])
        )

        forbidden_fragments = (
            "apt-get install tmux",
            "brew install tmux",
            "command -v tmux",
            "tmux ",
            "command -v opencode",
            "opencode ",
            "command -v pi",
            "pi ",
        )
        for fragment in forbidden_fragments:
            assert fragment not in step_text
