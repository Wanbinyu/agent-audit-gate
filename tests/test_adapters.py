from __future__ import annotations

from pathlib import Path

from agent_audit_gate import adapt_events_file, audit_run
from agent_audit_gate.adapters import events_to_trajectory, normalize_tool_event
from agent_audit_gate.heuristics import looks_like_verification

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_from_events_ok() -> None:
    run = adapt_events_file(
        EXAMPLES / "tool_events_ok.jsonl",
        claimed_status="completed",
        summary="fix parser",
    )
    assert run.has_write()
    assert any(t.verification for t in run.tools)
    report = audit_run(run)
    assert report.status == "completed"
    assert report.exit_code() == 0


def test_from_events_failed_test() -> None:
    run = adapt_events_file(
        EXAMPLES / "tool_events_blocked.jsonl",
        claimed_status="completed",
    )
    report = audit_run(run)
    assert report.status == "blocked"
    assert report.exit_code() == 3


def test_auto_verify_pytest() -> None:
    assert looks_like_verification(["python", "-m", "pytest", "-q"])
    event = normalize_tool_event(
        {
            "name": "run_command",
            "command": ["npm", "test"],
            "exit_code": 0,
        }
    )
    assert event.verification is True
    assert event.ok is True


def test_build_is_not_verification() -> None:
    assert not looks_like_verification(["npm", "run", "build"])
    event = normalize_tool_event(
        {
            "name": "run_command",
            "command": ["npm", "run", "build"],
            "exit_code": 0,
        }
    )
    assert event.verification is False


def test_missing_ok_is_not_success() -> None:
    event = normalize_tool_event({"name": "edit_file", "path": "a.py"})
    assert event.ok is False
    assert event.category == "write"


def test_exit_code_implies_ok() -> None:
    event = normalize_tool_event({"name": "bash", "command": "true", "exit_code": 1})
    assert event.ok is False


def test_events_array_json(tmp_path: Path) -> None:
    path = tmp_path / "events.json"
    path.write_text(
        """[
          {"name": "read_file", "ok": true, "path": "a.py"},
          {"name": "edit_file", "ok": true, "path": "a.py"},
          {"name": "run_command", "command": ["pytest", "-q"], "exit_code": 0}
        ]""",
        encoding="utf-8",
    )
    run = adapt_events_file(path, claimed_status="completed")
    assert audit_run(run).status == "completed"


def test_no_auto_verify_blocks_without_flag() -> None:
    run = events_to_trajectory(
        [
            {"name": "edit_file", "ok": True, "path": "a.py"},
            {
                "name": "run_command",
                "command": ["python", "-m", "pytest", "-q"],
                "exit_code": 0,
            },
        ],
        claimed_status="completed",
        auto_verify=False,
    )
    assert not any(t.verification for t in run.tools)
    assert audit_run(run).status == "blocked"
