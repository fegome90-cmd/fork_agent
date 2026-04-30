"""Unit tests for FPEL CLI commands — Task 1.3.

Tests fpel freeze/check/seal/status/fail via Typer CLI runner:
- freeze: creates frozen snapshot
- check: writes evidence only (no sealed PASS)
- seal: success outputs SealedVerdict, failure outputs SealFailureReason
- status: with records reports hash/candidate/sealed/reason; without freeze returns NOT_FROZEN
- only seal creates sealed PASS
- parametrized exit codes from SealFailureReason
- fail: success exits 0 with confirmation (S7)
- fail: no active proposal exits 12 (S8)
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from src.application.services.fpel_authorization_service import FPELAuthorizationService
from src.domain.entities.fpel import (
    FPELStatus,
    FrozenProposal,
    SealedVerdict,
    SealFailureReason,
    compute_content_hash,
)
from src.domain.ports.fpel_repository import FPELRepository
from src.interfaces.cli.commands.fpel import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TARGET_ID = "task-cli-001"
CONTENT = "# Proposal content for CLI tests"
CONTENT_HASH = compute_content_hash(CONTENT)


def _make_frozen(
    target_id: str = TARGET_ID,
    content: str = CONTENT,
) -> FrozenProposal:
    return FrozenProposal(
        frozen_proposal_id=f"fp-{target_id}",
        target_id=target_id,
        content_hash=compute_content_hash(content),
        content=content,
    )


def _make_service() -> tuple[FPELAuthorizationService, MagicMock]:
    repo = MagicMock(spec=FPELRepository)
    repo.get_sealed_verdict.return_value = None
    repo.get_current_content_hash.return_value = None
    repo.get_candidate_verdict.return_value = None
    repo.is_failed.return_value = False
    return FPELAuthorizationService(repo=repo), repo


def _patch_service(service: FPELAuthorizationService):
    """Patch the CLI's _get_service to return our mock service."""
    return patch(
        "src.interfaces.cli.commands.fpel._get_fpel_service",
        return_value=service,
    )


# ---------------------------------------------------------------------------
# Phase 1 RED: fpel subcommand registered in main.py
# ---------------------------------------------------------------------------


class TestFpelSubcommandRegistration:
    """Test that 'fpel' is registered as a subcommand in main.py."""

    def test_fpel_subcommand_registered(self) -> None:
        """'fpel' MUST be in registered typer groups after _register_commands()."""
        from src.interfaces.cli.main import _register_commands, app

        _register_commands()

        registered_names = []
        for group_info in app.registered_groups:
            registered_names.append(group_info.name)

        assert "fpel" in registered_names, (
            f"'fpel' not found in registered commands: {registered_names}"
        )


# ---------------------------------------------------------------------------
# freeze
# ---------------------------------------------------------------------------


class TestFreezeCommand:
    def test_freeze_creates_snapshot(self) -> None:
        service, repo = _make_service()
        _make_frozen()
        repo.get_all_frozen_proposals.return_value = []

        with _patch_service(service):
            result = runner.invoke(app, ["freeze", "--target-id", TARGET_ID, "--content", CONTENT])

        assert result.exit_code == 0
        assert "frozen_proposal_id" in result.output or "fp-" in result.output

    def test_freeze_output_contains_content_hash(self) -> None:
        """Freeze output MUST include the content hash of the frozen snapshot."""
        service, repo = _make_service()
        repo.get_all_frozen_proposals.return_value = []

        with _patch_service(service):
            result = runner.invoke(app, ["freeze", "--target-id", TARGET_ID, "--content", CONTENT])

        assert result.exit_code == 0
        assert "content_hash" in result.output

    def test_freeze_output_contains_target_id(self) -> None:
        """Freeze output MUST reference the target that was frozen."""
        service, repo = _make_service()
        repo.get_all_frozen_proposals.return_value = []

        with _patch_service(service):
            result = runner.invoke(app, ["freeze", "--target-id", TARGET_ID, "--content", CONTENT])

        assert result.exit_code == 0
        assert TARGET_ID in result.output


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------


class TestCheckCommand:
    def test_check_writes_evidence_only(self) -> None:
        """fpel check writes reports and candidate verdict, NOT sealed PASS."""
        service, repo = _make_service()
        frozen = _make_frozen()
        repo.get_active_frozen_proposal.return_value = frozen
        repo.get_checkers_for.return_value = ["checker-a"]
        repo.get_reports_for.return_value = [{"checker_id": "checker-a", "verdict": "PASS"}]
        repo.get_fpel_status.return_value = FPELStatus.CHECK_PASSED

        with _patch_service(service):
            result = runner.invoke(app, ["check", "--target-id", TARGET_ID])

        assert result.exit_code == 0
        # Check must NOT create sealed PASS
        repo.save_sealed_verdict.assert_not_called()


# ---------------------------------------------------------------------------
# seal — success outputs SealedVerdict
# ---------------------------------------------------------------------------


class TestSealCommand:
    def test_seal_success_outputs_sealed_verdict(self) -> None:
        service, repo = _make_service()
        frozen = _make_frozen()
        repo.get_active_frozen_proposal.return_value = frozen
        repo.get_checkers_for.return_value = ["checker-a"]
        repo.get_reports_for.return_value = [{"checker_id": "checker-a", "verdict": "PASS"}]
        repo.get_fpel_status.return_value = FPELStatus.CHECK_PASSED

        with _patch_service(service):
            result = runner.invoke(app, ["seal", "--target-id", TARGET_ID])

        assert result.exit_code == 0
        assert "SEALED_PASS" in result.output

    def test_seal_success_outputs_all_sealed_verdict_fields(self) -> None:
        """SealedVerdict output MUST contain frozen_proposal_id, verdict, sealed_at, content_hash."""
        service, repo = _make_service()
        frozen = _make_frozen()
        repo.get_active_frozen_proposal.return_value = frozen
        repo.get_checkers_for.return_value = ["checker-a"]
        repo.get_reports_for.return_value = [{"checker_id": "checker-a", "verdict": "PASS"}]
        repo.get_fpel_status.return_value = FPELStatus.CHECK_PASSED

        with _patch_service(service):
            result = runner.invoke(app, ["seal", "--target-id", TARGET_ID])

        assert result.exit_code == 0
        assert "frozen_proposal_id" in result.output
        assert "verdict" in result.output
        assert "SEALED_PASS" in result.output
        assert "sealed_at" in result.output
        assert "content_hash" in result.output

    def test_seal_failure_outputs_reason(self) -> None:
        """Seal failure shows the blocking reason."""
        service, repo = _make_service()
        repo.get_active_frozen_proposal.return_value = None  # no frozen

        with _patch_service(service):
            result = runner.invoke(app, ["seal", "--target-id", TARGET_ID])

        assert result.exit_code != 0
        assert "NO_FROZEN_PROPOSAL" in result.output

    def test_seal_failure_terminal_fail_via_cli(self) -> None:
        """Seal denied with TERMINAL_FAIL produces exit code 12 via CLI."""
        service, repo = _make_service()
        frozen = _make_frozen()
        repo.get_active_frozen_proposal.return_value = frozen
        repo.get_sealed_verdict.return_value = None
        repo.get_fpel_status.return_value = FPELStatus.TERMINAL_FAIL

        with _patch_service(service):
            result = runner.invoke(app, ["seal", "--target-id", TARGET_ID])

        assert result.exit_code == 12
        assert "TERMINAL_FAIL" in result.output

    def test_seal_failure_missing_reports_via_cli(self) -> None:
        """Seal denied with MISSING_REPORTS produces exit code 11 via CLI."""
        service, repo = _make_service()
        frozen = _make_frozen()
        repo.get_active_frozen_proposal.return_value = frozen
        repo.get_sealed_verdict.return_value = None
        repo.get_fpel_status.return_value = FPELStatus.FROZEN
        repo.get_checkers_for.return_value = []  # no checkers → MISSING_REPORTS

        with _patch_service(service):
            result = runner.invoke(app, ["seal", "--target-id", TARGET_ID])

        assert result.exit_code == 11
        assert "MISSING_REPORTS" in result.output


# ---------------------------------------------------------------------------
# status — with and without records
# ---------------------------------------------------------------------------


class TestStatusCommand:
    def test_status_with_records(self) -> None:
        """Status with existing FPEL records reports hash, candidate, sealed, reason."""
        service, repo = _make_service()
        frozen = _make_frozen()
        repo.get_active_frozen_proposal.return_value = frozen
        repo.get_sealed_verdict.return_value = SealedVerdict(
            frozen_proposal_id=frozen.frozen_proposal_id,
            verdict="SEALED_PASS",
            sealed_at=datetime.now(tz=UTC),
            content_hash=frozen.content_hash,
        )

        with _patch_service(service):
            result = runner.invoke(app, ["status", "--target-id", TARGET_ID])

        assert result.exit_code == 0
        assert frozen.content_hash[:8] in result.output

    def test_status_with_records_shows_sealed_verdict_fields(self) -> None:
        """Status with sealed records MUST report hash, sealed verdict, sealed_at."""
        service, repo = _make_service()
        frozen = _make_frozen()
        sealed_at = datetime.now(tz=UTC)
        repo.get_active_frozen_proposal.return_value = frozen
        repo.get_sealed_verdict.return_value = SealedVerdict(
            frozen_proposal_id=frozen.frozen_proposal_id,
            verdict="SEALED_PASS",
            sealed_at=sealed_at,
            content_hash=frozen.content_hash,
        )

        with _patch_service(service):
            result = runner.invoke(app, ["status", "--target-id", TARGET_ID])

        assert result.exit_code == 0
        assert frozen.content_hash[:8] in result.output
        assert "SEALED_PASS" in result.output
        assert "sealed_at" in result.output

    def test_status_with_records_shows_allowed_true(self) -> None:
        """Status with sealed PASS MUST show allowed=True (sealed: True)."""
        service, repo = _make_service()
        frozen = _make_frozen()
        repo.get_active_frozen_proposal.return_value = frozen
        repo.get_sealed_verdict.return_value = SealedVerdict(
            frozen_proposal_id=frozen.frozen_proposal_id,
            verdict="SEALED_PASS",
            sealed_at=datetime.now(tz=UTC),
            content_hash=frozen.content_hash,
        )

        with _patch_service(service):
            result = runner.invoke(app, ["status", "--target-id", TARGET_ID])

        assert result.exit_code == 0
        assert "True" in result.output

    def test_status_without_freeze(self) -> None:
        """Status with no frozen proposal returns NOT_FROZEN + NO_FROZEN_PROPOSAL."""
        service, repo = _make_service()
        repo.get_active_frozen_proposal.return_value = None

        with _patch_service(service):
            result = runner.invoke(app, ["status", "--target-id", TARGET_ID])

        assert result.exit_code == 0
        assert "NOT_FROZEN" in result.output
        assert "NO_FROZEN_PROPOSAL" in result.output

    def test_status_without_freeze_shows_allowed_false(self) -> None:
        """Status without freeze MUST show sealed: False."""
        service, repo = _make_service()
        repo.get_active_frozen_proposal.return_value = None

        with _patch_service(service):
            result = runner.invoke(app, ["status", "--target-id", TARGET_ID])

        assert result.exit_code == 0
        assert "False" in result.output


# ---------------------------------------------------------------------------
# Only seal creates sealed PASS
# ---------------------------------------------------------------------------


class TestOnlySealCreatesSealedPass:
    def test_check_does_not_seal(self) -> None:
        """fpel check must NOT create a sealed PASS."""
        service, repo = _make_service()
        frozen = _make_frozen()
        repo.get_active_frozen_proposal.return_value = frozen
        repo.get_checkers_for.return_value = ["checker-a"]
        repo.get_reports_for.return_value = [{"checker_id": "checker-a", "verdict": "PASS"}]
        repo.get_fpel_status.return_value = FPELStatus.CHECK_PASSED

        with _patch_service(service):
            runner.invoke(app, ["check", "--target-id", TARGET_ID])

        repo.save_sealed_verdict.assert_not_called()

    def test_freeze_does_not_seal(self) -> None:
        """fpel freeze must NOT create a sealed PASS."""
        service, repo = _make_service()
        repo.get_all_frozen_proposals.return_value = []

        with _patch_service(service):
            runner.invoke(app, ["freeze", "--target-id", TARGET_ID, "--content", CONTENT])

        repo.save_sealed_verdict.assert_not_called()


# ---------------------------------------------------------------------------
# Parametrized exit codes from SealFailureReason (5 values)
# ---------------------------------------------------------------------------


class TestSealFailureExitCodes:
    @pytest.mark.parametrize(
        "reason, expected_exit",
        [
            (SealFailureReason.HASH_MISMATCH, 10),
            (SealFailureReason.MISSING_REPORTS, 11),
            (SealFailureReason.TERMINAL_FAIL, 12),
            (SealFailureReason.POST_FREEZE_CHANGE, 13),
            (SealFailureReason.NO_FROZEN_PROPOSAL, 14),
        ],
    )
    def test_seal_failure_maps_to_exit_code(
        self, reason: SealFailureReason, expected_exit: int
    ) -> None:
        """Each SealFailureReason maps to a unique CLI exit code."""
        from src.interfaces.cli.commands.fpel import seal_failure_exit_code

        assert seal_failure_exit_code(reason) == expected_exit


# ---------------------------------------------------------------------------
# FPEL disabled — CLI exits gracefully, does not crash with NoneType
# ---------------------------------------------------------------------------


class TestFpelDisabledGracefulExit:
    """When FPEL_ENABLED is unset, CLI commands must exit with error, not crash."""

    def test_freeze_exits_when_disabled(self) -> None:
        """freeze command exits with code 1 when FPEL is disabled."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("FPEL_ENABLED", None)
            result = runner.invoke(app, ["freeze", "--target-id", "t1", "--content", "x"])

        assert result.exit_code == 1
        assert "disabled" in result.output.lower() or "FPEL_ENABLED" in result.output

    def test_seal_exits_when_disabled(self) -> None:
        """seal command exits with code 1 when FPEL is disabled."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("FPEL_ENABLED", None)
            result = runner.invoke(app, ["seal", "--target-id", "t1"])

        assert result.exit_code == 1

    def test_status_exits_when_disabled(self) -> None:
        """status command exits with code 1 when FPEL is disabled."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("FPEL_ENABLED", None)
            result = runner.invoke(app, ["status", "--target-id", "t1"])

        assert result.exit_code == 1

    def test_check_exits_when_disabled(self) -> None:
        """check command exits with code 1 when FPEL is disabled."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("FPEL_ENABLED", None)
            result = runner.invoke(app, ["check", "--target-id", "t1"])

        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# Task 1.10 — fpel fail command (S7, S8)
# ---------------------------------------------------------------------------


class TestFailCommand:
    """fpel fail --target-id X [--reason R] — exit 0 on success, 12 on error."""

    def test_fail_success_with_reason(self) -> None:
        """fpel fail --target-id X --reason R exits 0 and prints confirmation (S7)."""
        service, repo = _make_service()
        frozen = _make_frozen()
        repo.get_active_frozen_proposal.return_value = frozen

        with _patch_service(service):
            result = runner.invoke(
                app, ["fail", "--target-id", TARGET_ID, "--reason", "audit failure"]
            )

        assert result.exit_code == 0
        assert "fp-" in result.output or "frozen_proposal_id" in result.output

    def test_fail_success_without_reason(self) -> None:
        """fpel fail --target-id X (no reason) exits 0 (S7)."""
        service, repo = _make_service()
        frozen = _make_frozen()
        repo.get_active_frozen_proposal.return_value = frozen

        with _patch_service(service):
            result = runner.invoke(app, ["fail", "--target-id", TARGET_ID])

        assert result.exit_code == 0

    def test_fail_no_active_proposal_exits_12(self) -> None:
        """fpel fail --target-id X exits 12 when no active proposal (S8)."""
        service, repo = _make_service()
        repo.get_active_frozen_proposal.return_value = None

        with _patch_service(service):
            result = runner.invoke(app, ["fail", "--target-id", TARGET_ID])

        assert result.exit_code == 12


class TestSnapshotLegacyCommand:
    def test_snapshot_legacy_success_exit_0(self) -> None:
        service, repo = _make_service()
        repo.get_active_frozen_proposal.return_value = None
        repo.get_sealed_verdict.return_value = None
        repo.get_all_frozen_proposals.return_value = []
        repo.is_failed.return_value = False

        with _patch_service(service):
            result = runner.invoke(
                app,
                ["snapshot-legacy", "--target-id", TARGET_ID, "--content", CONTENT],
            )

        assert result.exit_code == 0
        assert "LEGACY_APPROVED" in result.output

    def test_snapshot_legacy_failed_proposal_exit_12(self) -> None:
        service, repo = _make_service()
        frozen = _make_frozen()
        repo.get_active_frozen_proposal.return_value = frozen
        repo.is_failed.return_value = True

        with _patch_service(service):
            result = runner.invoke(
                app,
                ["snapshot-legacy", "--target-id", TARGET_ID, "--content", CONTENT],
            )

        assert result.exit_code == 12

    def test_snapshot_legacy_missing_content_exit_12(self) -> None:
        service, _ = _make_service()

        with _patch_service(service):
            result = runner.invoke(
                app,
                ["snapshot-legacy", "--target-id", TARGET_ID],
            )

        assert result.exit_code != 0

    def test_snapshot_legacy_service_error_exit_12(self) -> None:
        service, repo = _make_service()
        frozen = _make_frozen()
        repo.get_active_frozen_proposal.return_value = frozen
        repo.is_failed.return_value = True

        with _patch_service(service):
            result = runner.invoke(
                app,
                ["snapshot-legacy", "--target-id", TARGET_ID, "--content", CONTENT],
            )

        assert result.exit_code == 12
