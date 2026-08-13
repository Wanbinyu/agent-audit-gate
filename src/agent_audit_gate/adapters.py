from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from .heuristics import (
    coerce_bool,
    coerce_exit_code,
    command_to_text,
    infer_category,
    looks_like_verification,
)
from .io_util import read_text_source
from .models import RunTrajectory, TaskMeta, ToolEvent


def parse_tool_events_jsonl(text: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at line {line_no}: {exc}") from exc
        if not isinstance(item, dict):
            raise ValueError(f"line {line_no}: event must be a JSON object")
        events.append(item)
    return events


def normalize_tool_event(raw: dict[str, Any], *, auto_verify: bool = True) -> ToolEvent:
    name = str(raw.get("name") or raw.get("tool") or raw.get("tool_name") or "unknown")
    category = infer_category(name, raw)

    command = raw.get("command", raw.get("cmd", raw.get("argv")))
    if isinstance(command, str) and command.strip().startswith("["):
        try:
            maybe = json.loads(command)
            if isinstance(maybe, list):
                command = maybe
        except json.JSONDecodeError:
            pass

    exit_code = coerce_exit_code(raw.get("exit_code", raw.get("status_code")))
    if "ok" in raw:
        ok = coerce_bool(raw.get("ok"))
    elif exit_code is not None:
        ok = exit_code == 0
    elif "success" in raw:
        ok = coerce_bool(raw.get("success"))
    elif "error" in raw and raw.get("error"):
        ok = False
    else:
        # Missing outcome is not evidence of success.
        ok = False

    path = raw.get("path") or raw.get("file") or raw.get("file_path")
    if path is not None:
        path = str(path)

    verification = coerce_bool(raw.get("verification"), default=False)
    if not verification and auto_verify:
        if looks_like_verification(command, name=name):
            verification = True

    summary = raw.get("summary") or raw.get("result") or raw.get("message")
    if summary is not None:
        summary = str(summary)

    return ToolEvent(
        name=name,
        ok=ok,
        category=category,
        path=path,
        command=command,
        exit_code=exit_code,
        verification=verification,
        summary=summary,
    )


def events_to_trajectory(
    events: list[dict[str, Any]],
    *,
    run_id: str | None = None,
    claimed_status: str = "unknown",
    summary: str = "",
    requires_verification: bool | None = None,
    model_claims: list[str] | None = None,
    notes: str | None = None,
    auto_verify: bool = True,
    source: str = "tool-events-jsonl",
) -> RunTrajectory:
    tools = [normalize_tool_event(e, auto_verify=auto_verify) for e in events]
    files_changed: list[str] = []
    for t in tools:
        if t.category == "write" and t.ok and t.path:
            if t.path not in files_changed:
                files_changed.append(t.path)

    for raw in events:
        for key in ("files_changed", "changed_files"):
            val = raw.get(key)
            if isinstance(val, list):
                for p in val:
                    sp = str(p)
                    if sp not in files_changed:
                        files_changed.append(sp)

    task = TaskMeta(
        summary=summary,
        requires_verification=requires_verification,
    )
    return RunTrajectory(
        schema_version="1",
        run_id=run_id or f"run-{uuid4().hex[:12]}",
        claimed_status=claimed_status,  # type: ignore[arg-type]
        task=task,
        tools=tools,
        files_changed=files_changed,
        model_claims=model_claims or [],
        notes=notes,
        source=source,
    )


def load_events_source(source: str | Path) -> list[dict[str, Any]]:
    text = read_text_source(source)
    stripped = text.strip()
    if not stripped:
        return []
    if stripped.startswith("["):
        data = json.loads(stripped)
        if not isinstance(data, list):
            raise ValueError("JSON array expected for events list")
        out: list[dict[str, Any]] = []
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                raise ValueError(f"events[{i}] must be an object")
            out.append(item)
        return out
    return parse_tool_events_jsonl(text)


def adapt_events_file(
    path: str | Path,
    **kwargs: Any,
) -> RunTrajectory:
    events = load_events_source(path)
    return events_to_trajectory(events, **kwargs)


def trajectory_template(
    *,
    run_id: str = "my-run-1",
    summary: str = "Describe the task here",
) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "run_id": run_id,
        "claimed_status": "completed",
        "task": {
            "summary": summary,
            "requires_verification": True,
            "risk": "standard",
        },
        "tools": [
            {
                "name": "edit_file",
                "ok": True,
                "category": "write",
                "path": "src/example.py",
            },
            {
                "name": "run_command",
                "ok": True,
                "category": "command",
                "command": ["python", "-m", "pytest", "-q"],
                "exit_code": 0,
                "verification": True,
                "summary": "replace with your real test command result",
            },
        ],
        "files_changed": ["src/example.py"],
        "model_claims": ["done"],
        "notes": "Fill tools from real agent/tool logs. Model claims alone are never enough.",
    }


def command_summary_line(tool: ToolEvent) -> str:
    return command_to_text(tool.command) or tool.name
