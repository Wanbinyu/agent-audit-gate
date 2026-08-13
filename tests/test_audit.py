from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from agent_audit_gate import audit_run, load_run
from agent_audit_gate.models import RunTrajectory, TaskMeta, ToolEvent

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


@pytest.mark.parametrize(
    "name,expected_status,expected_exit",
    [
        ("run_completed.json", "completed", 0),
        ("run_blocked_no_test.json", "blocked", 3),
        ("run_blocked_failed_test.json", "blocked", 3),
        ("run_readonly_ok.json", "completed", 0),
        ("run_partial.json", "partial", 2),
    ],
)
def test_examples(name: str, expected_status: str, expected_exit: int) -> None:
    run = load_run(EXAMPLES / name)
    report = audit_run(run)
    assert report.status == expected_status
    assert report.exit_code() == expected_exit
    assert report.gate_version


def test_claims_cannot_complete_without_tools() -> None:
    run = load_run(EXAMPLES / "run_blocked_no_test.json")
    report = audit_run(run)
    assert "green_verification_command" in report.missing_evidence
    assert any(f.code == "claim_conflict" for f in report.findings)


def test_failed_verification_veto() -> None:
    run = load_run(EXAMPLES / "run_blocked_failed_test.json")
    report = audit_run(run)
    assert report.status == "blocked"
    assert any(f.code == "verification_failed" for f in report.findings)


def test_writes_without_claim_are_partial() -> None:
    run = load_run(EXAMPLES / "run_partial.json")
    report = audit_run(run)
    assert report.status == "partial"
    assert report.exit_code() == 2
    assert any(f.code == "write_without_verification" for f in report.findings)
    assert "agent_claimed_completed_without_evidence" not in report.risks


def test_readonly_requires_verification() -> None:
    run = RunTrajectory(
        schema_version="1",
        run_id="ro-verify",
        claimed_status="completed",
        task=TaskMeta(requires_verification=True),
        tools=[
            ToolEvent(name="read_file", ok=True, category="read", path="a.py"),
        ],
    )
    report = audit_run(run)
    assert report.status == "blocked"
    assert any(f.code == "verification_required" for f in report.findings)

    run = run.model_copy(update={"claimed_status": "unknown"})
    report = audit_run(run)
    assert report.status == "partial"


def test_unsupported_schema() -> None:
    with pytest.raises(ValidationError):
        RunTrajectory.model_validate(
            {
                "schema_version": "99",
                "run_id": "x",
                "tools": [],
            }
        )
