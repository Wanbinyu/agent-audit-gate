"""Resolve cc-usage-gate session event logs for `audit-gate from-session`."""
from __future__ import annotations

import json
import re
from pathlib import Path


def _safe_session_id(session_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", session_id or "unknown")[:80]


def usage_gate_roots(explicit: Path | None = None) -> list[Path]:
    if explicit is not None:
        return [Path(explicit)]
    return [
        Path.cwd() / ".claude" / "usage-gate",
        Path.home() / ".claude" / "usage-gate",
    ]


def resolve_usage_gate_events(
    *,
    session: str | None = None,
    events_dir: Path | None = None,
) -> Path:
    """Find a usage-gate `*.events.jsonl`.

    Order: --dir if given, else project `./.claude/usage-gate`, else `~/.claude/usage-gate`.
    Session omitted → `latest_session.json` → that session's events file.
    """
    last_error = "no usage-gate event log found"
    for root in usage_gate_roots(events_dir):
        if session:
            candidate = root / f"{_safe_session_id(session)}.events.jsonl"
            if candidate.is_file():
                return candidate
            last_error = f"no events for session {session!r} under {root}"
            continue

        latest = root / "latest_session.json"
        if latest.is_file():
            try:
                data = json.loads(latest.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                last_error = f"invalid {latest}: {exc}"
                continue
            events_path = Path(str(data.get("events_path") or ""))
            if events_path.is_file():
                return events_path
            sid = str(data.get("session_id") or "")
            if sid:
                fallback = root / f"{_safe_session_id(sid)}.events.jsonl"
                if fallback.is_file():
                    return fallback
            last_error = f"{latest} does not point at an existing events file"
            continue

        last_error = f"no latest_session.json under {root}"

    raise FileNotFoundError(
        f"{last_error}. Run Claude Code with cc-usage-gate, or pass --dir."
    )
