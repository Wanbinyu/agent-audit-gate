from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from agent_audit_gate.cli import app
from agent_audit_gate.version import __version__

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
runner = CliRunner()


def test_demo() -> None:
    result = runner.invoke(app, ["demo"])
    assert result.exit_code == 0
    assert "run_completed.json" in result.stdout
    assert "ok" in result.stdout


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_check_completed() -> None:
    result = runner.invoke(app, ["check", str(EXAMPLES / "run_completed.json")])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["status"] == "completed"


def test_check_blocked_exit_3() -> None:
    result = runner.invoke(app, ["check", str(EXAMPLES / "run_blocked_no_test.json")])
    assert result.exit_code == 3
    data = json.loads(result.stdout)
    assert data["status"] == "blocked"


def test_check_stdin() -> None:
    payload = (EXAMPLES / "run_readonly_ok.json").read_text(encoding="utf-8")
    result = runner.invoke(app, ["check", "-"], input=payload)
    assert result.exit_code == 0


def test_from_events() -> None:
    result = runner.invoke(
        app,
        [
            "from-events",
            str(EXAMPLES / "tool_events_ok.jsonl"),
            "--claimed",
            "completed",
            "--pretty",
        ],
    )
    assert result.exit_code == 0
    assert "COMPLETED" in result.stdout


def test_init_and_validate(tmp_path: Path) -> None:
    path = tmp_path / "t.json"
    result = runner.invoke(app, ["init", str(path)])
    assert result.exit_code == 0
    assert path.exists()
    result = runner.invoke(app, ["validate", str(path)])
    assert result.exit_code == 0
    assert "ok" in result.stdout


def test_rules_and_schema() -> None:
    assert runner.invoke(app, ["rules"]).exit_code == 0
    result = runner.invoke(app, ["schema"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["required"] == ["schema_version", "run_id", "tools"]


def test_from_session_latest(tmp_path: Path) -> None:
    gate = tmp_path / ".claude" / "usage-gate"
    gate.mkdir(parents=True)
    events = gate / "sess-demo.events.jsonl"
    events.write_text(
        '{"name": "Edit", "ok": true, "category": "write", "path": "a.py"}\n'
        '{"name": "Bash", "ok": true, "category": "command", '
        '"command": "python -m pytest -q", "exit_code": 0, "verification": true}\n',
        encoding="utf-8",
    )
    (gate / "latest_session.json").write_text(
        json.dumps(
            {
                "session_id": "sess-demo",
                "events_path": str(events),
            }
        ),
        encoding="utf-8",
    )
    result = runner.invoke(app, ["from-session", "--dir", str(gate), "--quiet"])
    assert result.exit_code == 0


def test_from_session_partial_when_not_claimed(tmp_path: Path) -> None:
    gate = tmp_path / ".claude" / "usage-gate"
    gate.mkdir(parents=True)
    events = gate / "sess-wip.events.jsonl"
    events.write_text(
        '{"name": "Edit", "ok": true, "category": "write", "path": "a.py"}\n',
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        ["from-session", "sess-wip", "--dir", str(gate), "--claimed", "unknown"],
    )
    assert result.exit_code == 2
    data = json.loads(result.stdout)
    assert data["status"] == "partial"


def test_quiet_still_sets_exit() -> None:
    result = runner.invoke(
        app,
        ["check", str(EXAMPLES / "run_blocked_no_test.json"), "--quiet"],
    )
    assert result.exit_code == 3
    assert result.stdout.strip() == ""
